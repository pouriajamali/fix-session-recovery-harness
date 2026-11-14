using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;

namespace SessionHarness;

internal sealed class OwnedChild : IDisposable
{
    private readonly Process Process;
    private readonly Task<byte[]> Stdout, Stderr;
    private readonly TaskCompletionSource Overflow = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly string Nonce, Scenario, Phase, Folder;
    private readonly int Port;
    private readonly int? Pid;
    private readonly string? StartIdentity;
    private bool StopRequested, DeadlineExpired, DrainComplete, ExitObserved;
    private bool CleanupAttempted, ForcedTermination, CleanVerified, StoreVerified;
    private bool PipesSaved, DiagnosticSaved, Disposed;
    private int? ExitCode;
    private long StdoutObserved, StderrObserved;
    private string Reason = "IO_PROCESS_OR_PROTOCOL_FAILURE";
    public bool DiagnosticWriteFailed { get; private set; }
    public string OriginalFailureReason => Reason;

    public OwnedChild(string folder, string nonce, string scenario, string phase, int port)
    {
        Folder = folder; Nonce = nonce; Scenario = scenario; Phase = phase; Port = port;
        string host = Environment.ProcessPath ?? throw new Problem("OWN_HOST_MISSING");
        var start = new ProcessStartInfo(host)
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        if (Path.GetFileNameWithoutExtension(host).Equals("dotnet", StringComparison.OrdinalIgnoreCase))
            start.ArgumentList.Add(typeof(OwnedChild).Assembly.Location);
        foreach (string arg in new[] { "--owned-worker", folder, nonce, scenario, phase,
                     port.ToString(CultureInfo.InvariantCulture) })
            start.ArgumentList.Add(arg);
        start.Environment["SESSION_HARNESS_TOKEN"] = nonce;
        Process = new() { StartInfo = start };
        Stdout = Task.FromResult(Array.Empty<byte>());
        Stderr = Task.FromResult(Array.Empty<byte>());
        try
        {
            if (!Process.Start()) throw new Problem("WORKER_START_FAILED");
            Pid = Process.Id;
            StartIdentity = Process.StartTime.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture);
            Stdout = Drain(Process.StandardOutput.BaseStream, 16 * 1024, true);
            Stderr = Drain(Process.StandardError.BaseStream, 4 * 1024, false);
        }
        catch
        {
            Reason = "WORKER_START_FAILED";
            // A started handle remains owned even if metadata/drain setup failed.
            if (Pid.HasValue) Teardown();
            SaveDiagnostic();
            Process.Dispose();
            throw new Problem("WORKER_START_FAILED");
        }
    }

    private async Task<byte[]> Drain(Stream stream, int limit, bool output)
    {
        using var stored = new MemoryStream();
        byte[] buffer = new byte[512];
        int n;
        while ((n = await stream.ReadAsync(buffer)) > 0)
        {
            if (output) Interlocked.Exchange(ref StdoutObserved, Math.Min(1048576, Interlocked.Read(ref StdoutObserved) + n));
            else Interlocked.Exchange(ref StderrObserved, Math.Min(1048576, Interlocked.Read(ref StderrObserved) + n));
            if (stored.Length + n > limit)
            {
                Overflow.TrySetResult();
                continue;
            }
            stored.Write(buffer, 0, n);
        }
        return stored.ToArray();
    }

    public void NoteFailure(Exception failure)
    {
        if (Reason != "IO_PROCESS_OR_PROTOCOL_FAILURE") return;
        DeadlineExpired |= failure is OperationCanceledException or TimeoutException || failure is Problem { Code: "WORKER_STOP_TIMEOUT" };
        Reason = failure switch
        {
            OperationCanceledException or TimeoutException => "NETWORK_OR_SCENARIO_TIMEOUT",
            QuickFix.InvalidMessage => "FRAME_VALIDATION_FAILED",
            Problem p when DiagnosticReasons.Contains(p.Code) => p.Code,
            _ => "IO_PROCESS_OR_PROTOCOL_FAILURE"
        };
    }

    private static readonly HashSet<string> DiagnosticReasons =
    [
        "CONTROLLED_PROCESS_STOP", "WORKER_START_FAILED", "WORKER_OUTPUT_LIMIT",
        "WORKER_STOP_TIMEOUT", "WORKER_EXIT_OR_PIPE_INVALID", "WORKER_PROTOCOL",
        "FRAME_VALIDATION_FAILED", "NETWORK_OR_SCENARIO_TIMEOUT",
        "EARLY_DISCONNECT", "IO_PROCESS_OR_PROTOCOL_FAILURE"
    ];

    public async Task<WorkerReceipt> Stop(CancellationToken token)
    {
        try
        {
            if (!Process.HasExited)
            {
                StopRequested = true;
                byte[] stop = Encoding.ASCII.GetBytes("STOP " + Nonce + "\n");
                await Process.StandardInput.BaseStream.WriteAsync(stop, token);
                Process.StandardInput.Close();
            }
            Task exited = Process.WaitForExitAsync(token);
            Task deadline = Task.Delay(TimeSpan.FromSeconds(8), token);
            if (await Task.WhenAny(exited, deadline, Overflow.Task) != exited)
            {
                DeadlineExpired = !Overflow.Task.IsCompleted;
                throw new Problem(Overflow.Task.IsCompleted ? "WORKER_OUTPUT_LIMIT" : "WORKER_STOP_TIMEOUT");
            }
            await exited;
            ObserveExit();
            await Task.WhenAll(Stdout, Stderr).WaitAsync(TimeSpan.FromSeconds(3), token);
            DrainComplete = true;
            SavePipes();
            if (Overflow.Task.IsCompleted || Stderr.Result.Length != 0 || ExitCode != 0)
                throw new Problem("WORKER_EXIT_OR_PIPE_INVALID");
            var receipt = Parse(Stdout.Result, Nonce, Scenario, Phase, Port, Pid!.Value);
            if (!StopRequested) throw new Problem("WORKER_PROTOCOL");
            Safe.StoreClosed(Path.Combine(Folder, "store"));
            CleanVerified = StoreVerified = true;
            Reason = "CONTROLLED_PROCESS_STOP";
            SaveDiagnostic();
            if (DiagnosticWriteFailed) throw new Problem("PROCESS_DIAGNOSTIC_WRITE_FAILED");
            return receipt;
        }
        catch (Exception failure)
        {
            NoteFailure(failure);
            throw;
        }
    }

    private void ObserveExit()
    {
        if (Pid.HasValue && Process.HasExited)
        {
            ExitCode = Process.ExitCode;
            ExitObserved = true;
        }
    }

    private void SavePipes()
    {
        if (PipesSaved || !Stdout.IsCompletedSuccessfully || !Stderr.IsCompletedSuccessfully) return;
        Safe.Owned(Folder, Nonce);
        foreach (var pair in new[] { (Phase + "-stdout.json", Stdout.Result), (Phase + "-stderr.bin", Stderr.Result) })
        {
            using var saved = new FileStream(Path.Combine(Folder, pair.Item1), FileMode.CreateNew, FileAccess.Write);
            saved.Write(pair.Item2);
        }
        PipesSaved = true;
    }

    private void SaveDiagnostic()
    {
        if (DiagnosticSaved || DiagnosticWriteFailed) return;
        try
        {
            Safe.Owned(Folder, Nonce);
            var record = new ProcessDiagnostic(
                "fix-session-harness-process-v1", Nonce, Scenario, Phase,
                Contract.Session(Nonce), Port, Pid, StartIdentity, StopRequested,
                DeadlineExpired, ExitObserved, ExitCode, DrainComplete,
                Interlocked.Read(ref StdoutObserved), Interlocked.Read(ref StderrObserved),
                StdoutObserved > 16 * 1024, StderrObserved > 4 * 1024,
                CleanupAttempted, ForcedTermination, CleanVerified && !ForcedTermination,
                StoreVerified && !ForcedTermination, Reason, false);
            byte[] bytes = JsonSerializer.SerializeToUtf8Bytes(record, Contract.Json);
            ValidateDiagnostic(bytes, Nonce, Scenario, Phase, Port, Pid);
            if (bytes.Length > 4096) throw new Problem("PROCESS_DIAGNOSTIC_LIMIT");
            using var output = new FileStream(Path.Combine(Folder, Phase + "-process.json"), FileMode.CreateNew, FileAccess.Write);
            output.Write(bytes);
            DiagnosticSaved = true;
        }
        catch (Exception failure) when (failure is not OutOfMemoryException)
        {
            // Do not replace the original failure or overwrite the conflicting file.
            DiagnosticWriteFailed = true;
            CleanVerified = StoreVerified = false;
        }
    }

    internal static ProcessDiagnostic ValidateDiagnostic(byte[] bytes, string nonce, string scenario,
        string phase, int port, int? pid)
    {
        try
        {
            if (bytes.Length > 4096) throw new Problem("PROCESS_DIAGNOSTIC_PROTOCOL");
            using var doc = JsonDocument.Parse(bytes);
            var fields = typeof(ProcessDiagnostic).GetProperties()
                .Select(p => JsonNamingPolicy.CamelCase.ConvertName(p.Name)).ToHashSet(StringComparer.Ordinal);
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in doc.RootElement.EnumerateObject())
                if (!seen.Add(property.Name)) throw new Problem("PROCESS_DIAGNOSTIC_PROTOCOL");
            if (!seen.SetEquals(fields)) throw new Problem("PROCESS_DIAGNOSTIC_PROTOCOL");
            var d = JsonSerializer.Deserialize<ProcessDiagnostic>(bytes, Contract.Json)
                ?? throw new Problem("PROCESS_DIAGNOSTIC_PROTOCOL");
            if (d.Schema != "fix-session-harness-process-v1" || d.Nonce != nonce ||
                d.Scenario != scenario || d.Phase != phase || d.Port != port || d.Pid != pid ||
                d.Session != Contract.Session(nonce) || d.ExitObserved != d.ExitCode.HasValue ||
                !DiagnosticReasons.Contains(d.Reason) || d.StdoutBytesObserved is < 0 or > 1048576 ||
                d.StderrBytesObserved is < 0 or > 1048576 ||
                d.StdoutOverflow != (d.StdoutBytesObserved > 16384) ||
                d.StderrOverflow != (d.StderrBytesObserved > 4096) ||
                (d.Pid.HasValue ? d.Pid.Value <= 0 || !DateTime.TryParseExact(d.ProcessStartIdentity,
                    "O", CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out _) :
                    d.ProcessStartIdentity != null || d.ExitObserved || d.Reason != "WORKER_START_FAILED") ||
                (d.ForcedTermination && (!d.CleanupAttempted || d.CleanStopVerified || d.StoreClosedVerified)) ||
                (d.CleanStopVerified || d.StoreClosedVerified) &&
                    !(d.CleanStopVerified && d.StoreClosedVerified && d.StopRequested &&
                      d.ExitObserved && d.ExitCode == 0 && d.DrainComplete && !d.CleanupAttempted &&
                      !d.ForcedTermination && !d.EvidenceWriteFailure && d.Reason == "CONTROLLED_PROCESS_STOP"))
                throw new Problem("PROCESS_DIAGNOSTIC_PROTOCOL");
            return d;
        }
        catch (Exception failure) when (failure is JsonException or InvalidOperationException or ArgumentException or Problem)
        {
            throw new Problem("PROCESS_DIAGNOSTIC_PROTOCOL");
        }
    }

    public static WorkerReceipt Parse(byte[] bytes, string nonce, string scenario, string phase, int port, int pid)
    {
        try
        {
            if (bytes.Length is 0 or > 16384) throw new Problem("WORKER_PROTOCOL");
            using var doc = JsonDocument.Parse(bytes);
            var root = doc.RootElement;
            string[] fields = ["schema", "complete", "nonce", "scenario", "phase", "session", "port", "pid",
                "outcome", "reason", "cleanStop", "storeClosed", "nextSender", "nextTarget", "delivered", "gapRequestDeliveryCount"];
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var field in root.EnumerateObject())
                if (!seen.Add(field.Name)) throw new Problem("WORKER_PROTOCOL");
            if (!seen.SetEquals(fields)) throw new Problem("WORKER_PROTOCOL");
            var value = JsonSerializer.Deserialize<WorkerReceipt>(bytes, Contract.Json) ?? throw new Problem("WORKER_PROTOCOL");
            bool validRole = scenario is "gap" or "gapfill" or "resend" or "restart";
            bool validPhase = scenario == "restart" ? phase is "first" or "second" : phase == "single";
            if (!validRole || !validPhase || value.Schema != 1 || !value.Complete || value.Nonce != nonce ||
                value.Scenario != scenario || value.Phase != phase || value.Session != Contract.Session(nonce) ||
                value.Port != port || value.Pid != pid || value.Outcome != "pass" ||
                value.Reason != "CONTROLLED_PROCESS_STOP" || !value.CleanStop || !value.StoreClosed ||
                value.NextSender is 0 or > 100 || value.NextTarget is 0 or > 100 ||
                value.Delivered == null || value.Delivered.Length > 8 ||
                value.Delivered.Any(s => !(scenario == "gap" && s is ("GAP2" or "GAP3") ||
                    scenario == "gapfill" && s is ("GAPFILL3" or "GAPFILL5"))) ||
                value.GapRequestDeliveryCount is < -1 or > 8)
                throw new Problem("WORKER_PROTOCOL");
            return value;
        }
        catch (Exception failure) when (failure is JsonException or InvalidOperationException or ArgumentException or Problem)
        {
            throw new Problem("WORKER_PROTOCOL");
        }
    }

    private void Teardown()
    {
        CleanupAttempted = true;
        CleanVerified = StoreVerified = false;
        try
        {
            if (!Process.HasExited)
            {
                ForcedTermination = true;
                Process.Kill(entireProcessTree: true);
            }
            if (Process.WaitForExit(3000)) ObserveExit();
            DrainComplete = Task.WhenAll(Stdout, Stderr).Wait(3000);
            SavePipes();
        }
        catch (Exception failure) when (failure is InvalidOperationException or IOException or
            AggregateException or System.ComponentModel.Win32Exception)
        {
            // Original diagnostic cause and nullable unobserved exit remain intact.
        }
    }

    public void Dispose()
    {
        if (Disposed) return;
        Disposed = true;
        if (!DiagnosticSaved)
        {
            Teardown();
            SaveDiagnostic();
        }
        Process.Dispose();
    }
}
