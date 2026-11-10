using QuickFix;
using QuickFix.Fields;
using QuickFix.Logger;
using QuickFix.Store;
using QuickFix.Transport;

namespace SessionHarness;
internal sealed class LabApplication(string role) : IApplication
{
    public readonly TaskCompletionSource LoggedOn = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly List<string> Received = [];
    private int GapCount = -1;
    private string Fault = "";
    public void OnCreate(SessionID id)
    {
    }

    public void OnLogon(SessionID id) => LoggedOn.TrySetResult();
    public void OnLogout(SessionID id)
    {
    }

    public void ToAdmin(Message m, SessionID id)
    {
        if (m.Header.GetString(Tags.MsgType) == "2")
            lock (Received)
            {
                if (GapCount < 0)
                    GapCount = Received.Count;
            }
    }

    public void FromAdmin(Message m, SessionID id)
    {
    }

    public void ToApp(Message m, SessionID id)
    {
        if (m.Header.GetString(Tags.MsgType) != "B")
            throw new DoNotSend();
    }

    public void FromApp(Message m, SessionID id)
    {
        lock (Received)
        {
            if (m.Header.GetString(Tags.MsgType) != "B" || role != "gap" || Received.Count >= 8)
            {
                Fault = "APPLICATION_MESSAGE_UNEXPECTED";
                throw new UnsupportedMessageType();
            }

            string headline = m.GetString(Tags.Headline);
            if (headline is not ("GAP2" or "GAP3"))
            {
                Fault = "APPLICATION_ID_UNEXPECTED";
                throw new UnsupportedMessageType();
            }

            Received.Add(headline);
        }
    }

    public (string[] Delivered, int Gap, string Fault) Snapshot()
    {lock(Received)return(Received.ToArray(),GapCount,Fault);}
}

internal static class EngineWorker
{
    public static async Task<WorkerReceipt> Run(string folder, string nonce, string scenario, string phase, int port)
    {
        Contract.Nonce(nonce);
        Safe.Owned(folder, nonce);
        if (port is < 1 or > 65535 || scenario is not ("gap" or "resend" or "restart") || !(phase == "single" && scenario != "restart" || scenario == "restart" && phase is "first" or "second"))
            throw new Problem("WORKER_ARGUMENT_INVALID");
        string role = scenario == "restart" ? phase : scenario;
        string store = Path.Combine(folder, "store");
        Safe.NoLinks(store);
        if (phase == "second")
            Safe.StoreClosed(store);
        var app = new LabApplication(scenario);
        var id = new SessionID("FIX.4.4", Contract.Engine(nonce), Contract.Peer(nonce));
        var d = new SettingsDictionary();
        d.SetString(SessionSettings.CONNECTION_TYPE, "initiator");
        d.SetString(SessionSettings.BEGINSTRING, "FIX.4.4");
        d.SetString(SessionSettings.SENDERCOMPID, Contract.Engine(nonce));
        d.SetString(SessionSettings.TARGETCOMPID, Contract.Peer(nonce));
        d.SetString(SessionSettings.SOCKET_CONNECT_HOST, "127.0.0.1");
        d.SetLong(SessionSettings.SOCKET_CONNECT_PORT, port);
        d.SetBool(SessionSettings.SOCKET_IGNORE_PROXY, true);
        d.SetBool(SessionSettings.NON_STOP_SESSION, true);
        d.SetLong(SessionSettings.HEARTBTINT, 30);
        d.SetLong(SessionSettings.RECONNECT_INTERVAL, 60);
        d.SetLong(SessionSettings.LOGON_TIMEOUT, 5);
        d.SetLong(SessionSettings.LOGOUT_TIMEOUT, 2);
        d.SetBool(SessionSettings.RESET_ON_LOGON, false);
        d.SetBool(SessionSettings.RESET_ON_LOGOUT, false);
        d.SetBool(SessionSettings.RESET_ON_DISCONNECT, false);
        d.SetBool(SessionSettings.PERSIST_MESSAGES, true);
        d.SetBool(SessionSettings.CME_ENHANCED_RESEND, false);
        d.SetBool(SessionSettings.USE_DATA_DICTIONARY, true);
        d.SetString(SessionSettings.DATA_DICTIONARY, Contract.DictionaryPath());
        d.SetString(SessionSettings.FILE_STORE_PATH, store);
        var settings = new SessionSettings();
        settings.Set(id, d);
        var initiator = new SocketInitiator(app, new FileStoreFactory(settings), settings, new NullLogFactory(), new QuickFix.FIX44.MessageFactory());
        bool clean = false, closed = false;
        ulong sender = 0, target = 0;
        try
        {
            initiator.Start();
            await app.LoggedOn.Task.WaitAsync(TimeSpan.FromSeconds(10));
            foreach (string headline in role == "resend" ? new[]
            {
                "RESEND_A",
                "RESEND_B"
            }

            : role == "first" ? new[]
            {
                "RESTART_NEWS"
            }

            : Array.Empty<string>())
                if (!Session.SendToTarget(new QuickFix.FIX44.News(new Headline(headline)), id))
                    throw new Problem("SEND_NOT_ACCEPTED");
            async Task<string> Command()
            {
                char[] b = new char[1];
                var text = new System.Text.StringBuilder();
                while (text.Length < 64)
                {
                    int n = await Console.In.ReadAsync(b);
                    if (n == 0)
                        throw new Problem("STOP_COMMAND_INVALID");
                    if (b[0] == '\n')
                        return text.ToString();
                    text.Append(b[0]);
                }

                throw new Problem("STOP_COMMAND_INVALID");
            }

            string command = await Command().WaitAsync(TimeSpan.FromSeconds(20));
            if (command != "STOP " + nonce)
                throw new Problem("STOP_COMMAND_INVALID");
            initiator.Stop();
            initiator.Dispose();
            Safe.StoreClosed(store);
            // Stop disposes/unregisters sessions. Read persisted state through the
            // pinned store API only after all original handles have been released.
            using (var persisted = new FileStore(store, id))
            {
                sender = persisted.NextSenderMsgSeqNum;
                target = persisted.NextTargetMsgSeqNum;
            }

            Safe.StoreClosed(store);
            clean = closed = true;
        }
        finally
        {
            if (!closed)
                initiator.Dispose();
        }

        var observed = app.Snapshot();
        if (observed.Fault.Length > 0)
            throw new Problem(observed.Fault, true);
        return new(1, true, nonce, scenario, phase, Contract.Session(nonce), port, Environment.ProcessId, "pass", "CONTROLLED_PROCESS_STOP", clean, closed, sender, target, observed.Delivered, observed.Gap);
    }
}
