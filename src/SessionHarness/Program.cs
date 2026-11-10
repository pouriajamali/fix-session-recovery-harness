using System.Text;
using System.Text.Json;

namespace SessionHarness;
internal static class Program
{
    internal static Action<string>? BeforeReportForTests = null;
    public static async Task<int> Main(string[] args)
    {
        try
        {
            if (args is ["--version"])
            {
                Console.WriteLine("FIX Session Recovery Harness " + Contract.Version);
                return 0;
            }

            if (args is ["--owned-worker", var folder, var nonce, var scenario, var phase, var portText])
            {
                Contract.Nonce(nonce);
                if (Environment.GetEnvironmentVariable("SESSION_HARNESS_TOKEN") != nonce || !int.TryParse(portText, System.Globalization.NumberStyles.None, System.Globalization.CultureInfo.InvariantCulture, out int port))
                    throw new Problem("WORKER_ARGUMENT_INVALID");
                var receipt = await EngineWorker.Run(Safe.Normalize(folder), nonce, scenario, phase, port);
                Console.WriteLine(JsonSerializer.Serialize(receipt, Contract.Json));
                return 0;
            }

            if (args is not ["demo", var destination])
                throw new Problem("CLI_INVALID");
            Contract.DictionaryPath();
            string root = Safe.Normalize(destination), run = Guid.NewGuid().ToString("N");
            Safe.Fresh(root, run);
            List<ScenarioReceipt> results = [];
            foreach (string name in new[]
            {
                "gap",
                "resend",
                "restart"
            }

            )
                results.Add(await Scenarios.Run(root, name, run));
            bool complete = results.All(r => r.Complete);
            string outcome = results.All(r => r.Outcome == "pass") ? "pass" : complete ? "fail" : "incomplete";
            int exit = outcome == "pass" ? 0 : complete ? 2 : 1;
            BeforeReportForTests?.Invoke(root);
            Safe.Owned(root, run);
            var report = new
            {
                schema = "fix-session-harness-report-v1",
                version = Contract.Version,
                toolBuild = System.Reflection.CustomAttributeExtensions.GetCustomAttribute<System.Reflection.AssemblyInformationalVersionAttribute>(typeof(Program).Assembly)?.InformationalVersion ?? "UNAVAILABLE",
                complete,
                outcome,
                exitCode = exit,
                runNonce = run,
                engine = "QuickFIXn1.14.1",
                upstreamSource = "44c111acdb253335fd3c035589795468ff60c400",
                dictionarySha256 = Contract.DictionaryHash,
                endpoint = "127.0.0.1 only; ephemeral listener owned by parent",
                scope = "Three synthetic News/admin cases only; no orders/broker/production/crash-durability/performance/exactly-once guarantee",
                scenarios = results
            };
            using (var f = new FileStream(Path.Combine(root, "summary.txt.pending"), FileMode.CreateNew, FileAccess.Write))
                f.Write(Encoding.UTF8.GetBytes("FIX Session Recovery Harness: " + outcome + "\n" + string.Join("\n", results.Select(r => r.Scenario + ": " + r.Outcome + " / " + r.Reason)) + "\nOnly controlled stops; no crash durability or production guarantee.\n"));
            using (var f = new FileStream(Path.Combine(root, "summary.json.pending"), FileMode.CreateNew, FileAccess.Write))
                f.Write(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(report, Contract.Json) + "\n"));
            File.Move(Path.Combine(root, "summary.txt.pending"), Path.Combine(root, "summary.txt"));
            File.Move(Path.Combine(root, "summary.json.pending"), Path.Combine(root, "summary.json"));
            Console.WriteLine(JsonSerializer.Serialize(report, Contract.Json));
            return exit;
        }
        catch (Exception e)when (e is not OutOfMemoryException)
        {
            Console.WriteLine(JsonSerializer.Serialize(new { complete = false, outcome = "incomplete", exitCode = 1, reason = e is Problem p ? p.Code : "IO_PROCESS_OR_CONFIGURATION_FAILURE" }, Contract.Json));
            return 1;
        }
    }
}
