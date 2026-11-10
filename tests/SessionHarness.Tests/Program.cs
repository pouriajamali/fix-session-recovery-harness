using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using QuickFix;
using QuickFix.Fields;
using SessionHarness;
using App = SessionHarness.Program;

internal static class Program
{
    private static string Root = "";
    private static int Index, Passed, Failed, Skipped;
    private static readonly List<object> Observations = [];
    private const string Nonce = "00112233445566778899aabbccddeeff";
    private static void Require(bool b, string detail = "Expectation failed")
    {if(!b)throw new InvalidOperationException(detail);}

    private static string Fresh(string label) => Path.Combine(Root, (++Index).ToString("D3") + " " + label);
    private static async Task Case(string name, Func<Task> action)
    {
        try
        {
            await action();
            Passed++;
            Observations.Add(new { name, result = "pass" });
            Console.WriteLine("PASS " + name);
        }
        catch (Exception e)
        {
            Failed++;
            Observations.Add(new { name, result = "fail", error = e.GetType().Name, message = e.Message });
            Console.WriteLine("FAIL " + name + " " + e.GetType().Name + " " + e.Message);
        }
    }

    private static void Reject(Action action, string? reason = null)
    {
        try
        {
            action();
            throw new InvalidOperationException("Unexpected acceptance");
        }
        catch (Problem p)
        {
            Require(reason == null || p.Code == reason, p.Code);
        }
    }

    private static async Task WireCase(string name, Func<Wire, Task> action)
    {
        await Case(name, async () =>
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start(1);
            try
            {
                using var peer = new TcpClient();
                var accept = listener.AcceptTcpClientAsync();
                await peer.ConnectAsync(IPAddress.Loopback, ((IPEndPoint)listener.LocalEndpoint).Port);
                using var wire = new Wire(await accept, Nonce, []);
                await action(wire);
            }
            finally
            {
                listener.Stop();
            }
        });
    }

    private static byte[] Heartbeat(int seq = 1)
    {
        var m = Wire.Message("0", seq, Nonce);
        m.Header.SetField(new SenderCompID(Contract.Engine(Nonce)));
        m.Header.SetField(new TargetCompID(Contract.Peer(Nonce)));
        return Encoding.Latin1.GetBytes(m.ConstructString());
    }

    private static WorkerReceipt Valid() => new(1, true, Nonce, "gap", "single", Contract.Session(Nonce), 12345, 1234, "pass", "CONTROLLED_PROCESS_STOP", true, true, 6, 7, ["GAP2", "GAP3"], 0);
    private static WorkerReceipt Parse(byte[] b) => OwnedChild.Parse(b, Nonce, "gap", "single", 12345, 1234);
    public static async Task<int> Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--owned-worker")
        {
            switch (Environment.GetEnvironmentVariable("HARNESS_TEST_PROBE"))
            {
                case "empty":
                    return 0;
                case "invalid":
                    Console.WriteLine("{}");
                    return 0;
                case "stdout":
                    Console.Write(new string ('x', 100_000));
                    return 0;
                case "stderr":
                    Console.Error.Write(new string ('x', 100_000));
                    return 0;
                case "exit":
                    return 17;
                case "hang":
                    await Task.Delay(30_000);
                    return 0;
            }

            return await App.Main(args);
        }

        if (args is not ["--work", var requested])
            return 2;
        Root = Safe.Normalize(requested);
        if (Directory.Exists(Root) || File.Exists(Root))
            return 2;
        Directory.CreateDirectory(Root);
        await Case("dictionary-canonical-pin", () =>
        {
            Require(Contract.Hash(Contract.DictionaryPath()) == Contract.DictionaryHash);
            return Task.CompletedTask;
        });
        await Case("valid-complete-bound-worker-receipt", () =>
        {
            Require(Parse(JsonSerializer.SerializeToUtf8Bytes(Valid(), Contract.Json)).Complete);
            return Task.CompletedTask;
        });
        foreach (string field in new[]
        {
            "schema",
            "complete",
            "nonce",
            "scenario",
            "phase",
            "session",
            "port",
            "pid",
            "outcome",
            "reason",
            "cleanStop",
            "storeClosed",
            "nextSender",
            "nextTarget",
            "delivered",
            "gapRequestDeliveryCount"
        }

        )
            await Case("receipt-missing-" + field, () =>
            {
                var node = JsonSerializer.SerializeToNode(Valid(), Contract.Json)!.AsObject();
                node.Remove(field);
                Reject(() => Parse(Encoding.UTF8.GetBytes(node.ToJsonString())), "WORKER_PROTOCOL");
                return Task.CompletedTask;
            });
        foreach (var(field, value)in new (string, JsonNode? )[]
        {
            ("schema", 2),
            ("complete", false),
            ("nonce", new string ('f', 32)),
            ("scenario", "restart"),
            ("phase", "second"),
            ("session", "OTHER"),
            ("port", 12346),
            ("pid", 999),
            ("outcome", "incomplete"),
            ("reason", "OTHER"),
            ("cleanStop", false),
            ("storeClosed", false),
            ("nextSender", 0),
            ("nextTarget", 101),
            ("delivered", new JsonArray("UNKNOWN")),
            ("gapRequestDeliveryCount", 9),
            ("extra", 1)
        }

        )
            await Case("receipt-invalid-" + field, () =>
            {
                var node = JsonSerializer.SerializeToNode(Valid(), Contract.Json)!;
                node[field] = value?.DeepClone();
                Reject(() => Parse(Encoding.UTF8.GetBytes(node.ToJsonString())), "WORKER_PROTOCOL");
                return Task.CompletedTask;
            });
        string valid = JsonSerializer.Serialize(Valid(), Contract.Json);
        foreach (var(name, raw)in new[]
        {
            ("empty", ""),
            ("truncated", valid[..^1]),
            ("extra-object", valid + "{}"),
            ("duplicate", valid.Replace("\"schema\": 1", "\"schema\": 1,\"schema\": 1")),
            ("oversized", new string ('x', 16385))
        }

        )
            await Case("receipt-" + name, () =>
            {
                Require(raw != valid);
                Reject(() => Parse(Encoding.UTF8.GetBytes(raw)), "WORKER_PROTOCOL");
                return Task.CompletedTask;
            });
        await WireCase("fragmented-frame-uses-upstream-parser", wire =>
        {
            var b = Heartbeat();
            foreach (byte x in b)
                wire.Feed([x]);
            Require(wire.Take()?.Header.GetString(Tags.MsgType) == "0" && wire.Take() == null);
            return Task.CompletedTask;
        });
        await WireCase("coalesced-two-frames", wire =>
        {
            wire.Feed(Heartbeat().Concat(Heartbeat(2)).ToArray());
            Require(wire.Take()?.Header.GetULong(Tags.MsgSeqNum) == 1 && wire.Take()?.Header.GetULong(Tags.MsgSeqNum) == 2 && wire.Take() == null);
            return Task.CompletedTask;
        });
        await WireCase("unframed-cap-before-parser-append", wire =>
        {
            wire.Feed(new byte[Wire.AccumulationLimit]);
            Reject(() => wire.Feed([1]), "UNFRAMED_LIMIT");
            return Task.CompletedTask;
        });
        await WireCase("incomplete-advertised-huge-body-remains-bounded", wire =>
        {
            wire.Feed("8=FIX.4.4\x01"u8);
            wire.Feed("9=2147483647\x01"u8);
            Require(wire.Take() == null);
            Reject(() => wire.Feed(new byte[Wire.AccumulationLimit]), "UNFRAMED_LIMIT");
            return Task.CompletedTask;
        });
        await WireCase("leading-garbage-cannot-silently-pass", wire =>
        {
            wire.Feed(new byte[] { 88 }.Concat(Heartbeat()).ToArray());
            Reject(() => wire.Take(), "FRAMING_GARBAGE");
            return Task.CompletedTask;
        });
        await WireCase("wrong-session-rejected", wire =>
        {
            byte[] b = Heartbeat();
            string raw = Encoding.Latin1.GetString(b).Replace(Contract.Engine(Nonce), "Z" + Nonce[..12]);
            var m = new Message();
            m.FromString(raw, false, null, null);
            wire.Feed(Encoding.Latin1.GetBytes(m.ConstructString()));
            Reject(() => wire.Take(), "SESSION_MISMATCH");
            return Task.CompletedTask;
        });
        await WireCase("invalid-checksum-cannot-pass", wire =>
        {
            string raw = Encoding.Latin1.GetString(Heartbeat());
            int pos = raw.LastIndexOf("10=", StringComparison.Ordinal);
            wire.Feed(Encoding.Latin1.GetBytes(raw[..(pos + 3)] + "999\x01"));
            try
            {
                wire.Take();
                throw new InvalidOperationException("Bad checksum accepted");
            }
            catch (InvalidMessage)
            {
            }

            return Task.CompletedTask;
        });
        await WireCase("completed-frame-byte-cap", wire =>
        {
            var m = Wire.Message("B", 1, Nonce);
            m.Header.SetField(new SenderCompID(Contract.Engine(Nonce)));
            m.Header.SetField(new TargetCompID(Contract.Peer(Nonce)));
            m.SetField(new Headline(new string ('X', 9000)));
            wire.Feed(Encoding.Latin1.GetBytes(m.ConstructString()));
            Reject(() => wire.Take(), "FRAME_LIMIT");
            return Task.CompletedTask;
        });
        await WireCase("frame-count-cap", wire =>
        {
            wire.Feed(Enumerable.Range(1, 33).SelectMany(i => Heartbeat(i)).ToArray());
            for (int i = 0; i < 32; i++)
                Require(wire.Take() != null);
            Reject(() => wire.Take(), "FRAME_COUNT_LIMIT");
            return Task.CompletedTask;
        });
        await Case("scenario-byte-budget-shared-by-connections", () =>
        {
            var b = new WireBudget();
            b.Add(Wire.ByteLimit - 1);
            b.Add(1);
            Reject(() => b.Add(1), "WIRE_BYTE_LIMIT");
            Require(b.Remaining == 0);
            return Task.CompletedTask;
        });
        await Case("fresh-output-and-marker-preserved", () =>
        {
            string p = Fresh("owned");
            Safe.Fresh(p, Nonce);
            Safe.Owned(p, Nonce);
            Reject(() => Safe.Fresh(p, Nonce), "OUTPUT_EXISTS");
            Reject(() => Safe.Owned(p, new string ('f', 32)), "OWNERSHIP_INVALID");
            Require(File.ReadAllText(Path.Combine(p, ".harness-owned")) == Nonce);
            return Task.CompletedTask;
        });
        await Case("all-controls-and-line-separators-in-every-path-position", () =>
        {
            string basis = Path.Combine(Root, "child");
            foreach (int c in Enumerable.Range(0, 32).Concat(Enumerable.Range(127, 33)).Concat(new[] { 0x2028, 0x2029, 0xfeff }))
                for (int i = 0; i <= basis.Length; i++)
                    Reject(() => Safe.Normalize(basis.Insert(i, ((char)c).ToString())), "PATH_UNSUPPORTED");
            return Task.CompletedTask;
        });
        await Case("network-paths-refused", () =>
        {
            Reject(() => Safe.Normalize("//server/share"), "PATH_UNSUPPORTED");
            Reject(() => Safe.Normalize(@"\\server\share"), "PATH_UNSUPPORTED");
            return Task.CompletedTask;
        });
        await Case("store-exclusivity-required", () =>
        {
            string p = Fresh("store");
            Directory.CreateDirectory(p);
            for (int i = 0; i < 4; i++)
                File.WriteAllText(Path.Combine(p, "part" + i), "owned");
            Safe.StoreClosed(p);
            using var held = new FileStream(Path.Combine(p, "part0"), FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            try
            {
                Safe.StoreClosed(p);
                throw new InvalidOperationException("Held store accepted");
            }
            catch (IOException)
            {
            }

            return Task.CompletedTask;
        });
        await Case("missing-store-not-recovered-or-invented", () =>
        {
            Reject(() => Safe.StoreClosed(Fresh("missing")), "STORE_MISSING");
            return Task.CompletedTask;
        });
        foreach (string probe in new[]
        {
            "empty",
            "invalid",
            "stdout",
            "stderr",
            "exit",
            "hang"
        }

        )
            await Case("real-owned-child-" + probe + "-never-clean-pass", async () =>
            {
                string p = Fresh("probe");
                Safe.Fresh(p, Nonce);
                var listener = new TcpListener(IPAddress.Loopback, 0);
                listener.Start(1);
                Environment.SetEnvironmentVariable("HARNESS_TEST_PROBE", probe);
                try
                {
                    using var child = new OwnedChild(p, Nonce, "gap", "single", ((IPEndPoint)listener.LocalEndpoint).Port);
                    using var cancel = new CancellationTokenSource(probe == "hang" ? 300 : 5000);
                    var watch = Stopwatch.StartNew();
                    try
                    {
                        await child.Stop(cancel.Token);
                        throw new InvalidOperationException("Fault child accepted");
                    }
                    catch (Exception e)when (e is Problem or IOException or OperationCanceledException)
                    {
                    }

                    Require(watch.Elapsed < TimeSpan.FromSeconds(7));
                }
                finally
                {
                    Environment.SetEnvironmentVariable("HARNESS_TEST_PROBE", null);
                    listener.Stop();
                }
            });
        await Case("all-three-real-loopback-scenarios-and-raw-hashes", async () =>
        {
            string p = Fresh("actual demo");
            Require(await App.Main(["demo", p]) == 0, "Demo did not pass");
            using var doc = JsonDocument.Parse(File.ReadAllBytes(Path.Combine(p, "summary.json")));
            var root = doc.RootElement;
            Require(root.GetProperty("complete").GetBoolean() && root.GetProperty("scenarios").GetArrayLength() == 3);
            foreach (var s in root.GetProperty("scenarios").EnumerateArray())
            {
                string name = s.GetProperty("scenario").GetString()!;
                Require(s.GetProperty("outcome").GetString() == "pass");
                foreach (var hash in s.GetProperty("artifactHashes").EnumerateObject())
                    Require(Contract.Hash(Path.Combine(p, name, hash.Name)) == hash.Value.GetString());
                if (name == "gap")
                    Require(s.GetProperty("delivered").EnumerateArray().Select(x => x.GetString()).SequenceEqual(new[] { "GAP2", "GAP3" }));
                if (name == "restart")
                {
                    Require(s.GetProperty("connections").GetInt32() == 2);
                    using var workers = JsonDocument.Parse(File.ReadAllBytes(Path.Combine(p, name, "workers.json")));
                    Require(workers.RootElement.GetArrayLength() == 2 && workers.RootElement.EnumerateArray().All(w => w.GetProperty("cleanStop").GetBoolean() && w.GetProperty("storeClosed").GetBoolean()));
                }
            }
        });
        await Case("report-collision-overrides-pass", async () =>
        {
            string p = Fresh("blocked report");
            App.BeforeReportForTests = folder => File.WriteAllText(Path.Combine(folder, "summary.json"), "sentinel");
            try
            {
                Require(await App.Main(["demo", p]) == 1 && File.ReadAllText(Path.Combine(p, "summary.json")) == "sentinel");
            }
            finally
            {
                App.BeforeReportForTests = null;
            }
        });
        foreach (string option in new[]
        {
            "--host",
            "--port",
            "--settings",
            "--dictionary",
            "--message",
            "--reset",
            "--order"
        }

        )
            await Case("no-import-or-destination-option-" + option, async () =>
            {
                Require(await App.Main([option, "not-used"]) == 1);
            });
        try
        {
            string target = Fresh("link target"), link = Fresh("link");
            Directory.CreateDirectory(target);
            Directory.CreateSymbolicLink(link, target);
            await Case("symlink-output-refused", () =>
            {
                Reject(() => Safe.Normalize(link), "LINK_UNSUPPORTED");
                return Task.CompletedTask;
            });
        }
        catch (Exception e)when (OperatingSystem.IsWindows() && (e is UnauthorizedAccessException || e is IOException && e.HResult == unchecked((int)0x80070522)))
        {
            Skipped++;
            Observations.Add(new { name = "symlink-output-refused", result = "skip", reason = "Local Windows symbolic-link privilege unavailable" });
        }

        File.WriteAllText(Path.Combine(Root, "receipt.json"), JsonSerializer.Serialize(new { passed = Passed, failed = Failed, skipped = Skipped, observations = Observations, scope = "Synthetic fixed News/admin loopback only; no production/crash/exactly-once/performance guarantee" }, Contract.Json));
        Console.WriteLine($"SUMMARY passed={Passed} failed={Failed} skipped={Skipped}");
        return Failed == 0 ? 0 : 1;
    }
}
