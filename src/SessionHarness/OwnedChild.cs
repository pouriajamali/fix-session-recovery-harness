using System.Diagnostics;
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
    public OwnedChild(string folder, string nonce, string scenario, string phase, int port)
    {
        Folder = folder;
        Nonce = nonce;
        Scenario = scenario;
        Phase = phase;
        Port = port;
        string host = Environment.ProcessPath ?? throw new Problem("OWN_HOST_MISSING");
        var start = new ProcessStartInfo(host)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        if (Path.GetFileNameWithoutExtension(host).Equals("dotnet", StringComparison.OrdinalIgnoreCase))
            start.ArgumentList.Add(typeof(OwnedChild).Assembly.Location);
        foreach (string arg in new[]
        {
            "--owned-worker",
            folder,
            nonce,
            scenario,
            phase,
            port.ToString(System.Globalization.CultureInfo.InvariantCulture)
        }

        )
            start.ArgumentList.Add(arg);
        start.Environment["SESSION_HARNESS_TOKEN"] = nonce;
        Process = new()
        {
            StartInfo = start
        };
        if (!Process.Start())
            throw new Problem("WORKER_START_FAILED");
        async Task<byte[]> Drain(Stream stream, int limit)
        {
            using var stored = new MemoryStream();
            byte[] b = new byte[512];
            int n;
            while ((n = await stream.ReadAsync(b)) > 0)
            {
                if (stored.Length + n > limit)
                {
                    Overflow.TrySetResult();
                    continue;
                }

                stored.Write(b, 0, n);
            }

            return stored.ToArray();
        }

        Stdout = Drain(Process.StandardOutput.BaseStream, 16 * 1024);
        Stderr = Drain(Process.StandardError.BaseStream, 4 * 1024);
    }

    public async Task<WorkerReceipt> Stop(CancellationToken token)
    {
        if (!Process.HasExited)
        {
            byte[] stop = Encoding.ASCII.GetBytes("STOP " + Nonce + "\n");
            await Process.StandardInput.BaseStream.WriteAsync(stop, token);
            Process.StandardInput.Close();
        }

        Task exited = Process.WaitForExitAsync(token);
        Task deadline = Task.Delay(TimeSpan.FromSeconds(8), token);
        if (await Task.WhenAny(exited, deadline, Overflow.Task) != exited)
            throw new Problem(Overflow.Task.IsCompleted ? "WORKER_OUTPUT_LIMIT" : "WORKER_STOP_TIMEOUT");
        await exited;
        await Task.WhenAll(Stdout, Stderr).WaitAsync(TimeSpan.FromSeconds(3), token);
        Safe.Owned(Folder, Nonce);
        foreach (var pair in new[]
        {
            (Phase + "-stdout.json", Stdout.Result),
            (Phase + "-stderr.bin", Stderr.Result)
        }

        )
        {
            using var saved = new FileStream(Path.Combine(Folder, pair.Item1), FileMode.CreateNew, FileAccess.Write);
            saved.Write(pair.Item2);
        }

        if (Overflow.Task.IsCompleted || Stderr.Result.Length != 0 || Process.ExitCode != 0)
            throw new Problem("WORKER_EXIT_OR_PIPE_INVALID");
        WorkerReceipt receipt = Parse(Stdout.Result, Nonce, Scenario, Phase, Port, Process.Id);
        Safe.Owned(Folder, Nonce);
        Safe.StoreClosed(Path.Combine(Folder, "store"));
        return receipt;
    }

    internal static WorkerReceipt Parse(byte[] bytes, string nonce, string scenario, string phase, int port, int pid)
    {
        try
        {
            if (bytes.Length > 16 * 1024)
                throw new Problem("WORKER_PROTOCOL");
            using var d = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 8 });
            var r = d.RootElement;
            if (r.ValueKind != JsonValueKind.Object)
                throw new Problem("WORKER_PROTOCOL");
            string[] fields = ["schema", "complete", "nonce", "scenario", "phase", "session", "port", "pid", "outcome", "reason", "cleanStop", "storeClosed", "nextSender", "nextTarget", "delivered", "gapRequestDeliveryCount"];
            HashSet<string> seen = new(StringComparer.Ordinal);
            foreach (var p in r.EnumerateObject())
                if (!seen.Add(p.Name))
                    throw new Problem("WORKER_PROTOCOL");
            if (!seen.SetEquals(fields))
                throw new Problem("WORKER_PROTOCOL");
            var value = JsonSerializer.Deserialize<WorkerReceipt>(bytes, Contract.Json) ?? throw new Problem("WORKER_PROTOCOL");
            if (value.Schema != 1 || !value.Complete || value.Nonce != nonce || value.Scenario != scenario || value.Phase != phase || value.Session != Contract.Session(nonce) || value.Port != port || value.Pid != pid || value.Outcome != "pass" || value.Reason != "CONTROLLED_PROCESS_STOP" || !value.CleanStop || !value.StoreClosed || value.NextSender is 0 or > 100 || value.NextTarget is 0 or > 100 || value.Delivered == null || value.Delivered.Length > 8 || value.Delivered.Any(s => s is not ("GAP2" or "GAP3")) || value.GapRequestDeliveryCount is < -1 or > 8)
                throw new Problem("WORKER_PROTOCOL");
            return value;
        }
        catch (Exception e)when (e is JsonException or InvalidOperationException or ArgumentException or Problem)
        {
            throw new Problem("WORKER_PROTOCOL");
        }
    }

    public void Dispose()
    {
        // Failure teardown is never a successful clean-stop observation.
        try
        {
            if (!Process.HasExited)
                Process.Kill(entireProcessTree: true);
            Process.WaitForExit(3000);
        }
        catch (InvalidOperationException)
        {
        }

        Process.Dispose();
    }
}
