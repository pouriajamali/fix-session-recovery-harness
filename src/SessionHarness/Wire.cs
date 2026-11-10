using System.Net;
using System.Net.Sockets;
using System.Text;
using QuickFix;
using QuickFix.Fields;
using DD = QuickFix.DataDictionary.DataDictionary;

namespace SessionHarness;
internal sealed record WireEvent(string Direction, string Raw);
internal sealed class WireTrace
{
    public readonly MemoryStream Incoming = new();
    public readonly MemoryStream Outgoing = new();
}

internal sealed class WireBudget
{
    public int Bytes { get; private set; }
    public int Remaining => Wire.ByteLimit - Bytes;

    public void Add(int n)
    {
        if (n < 0 || n > Remaining)
            throw new Problem("WIRE_BYTE_LIMIT");
        Bytes += n;
    }
}

internal sealed class Wire : IDisposable
{
    public const int FrameLimit = 8192, AccumulationLimit = 16 * 1024, ByteLimit = 256 * 1024, FrameCountLimit = 32;
    private readonly TcpClient Client;
    private readonly Parser Parser = new(Encoding.Latin1);
    private readonly List<byte> Pending = [];
    private readonly DD Dictionary;
    private readonly string Nonce;
    private int Frames;
    private readonly List<WireEvent> Events;
    private readonly WireBudget Budget;
    private readonly WireTrace Trace;
    public Wire(TcpClient client, string nonce, List<WireEvent> events, WireBudget? budget = null, WireTrace? trace = null)
    {
        if (client.Client.RemoteEndPoint is not IPEndPoint remote || !IPAddress.IsLoopback(remote.Address))
            throw new Problem("PEER_ENDPOINT_INVALID");
        Client = client;
        Client.NoDelay = true;
        Nonce = nonce;
        Events = events;
        Budget = budget ?? new();
        Trace = trace ?? new();
        Dictionary = new(Contract.DictionaryPath());
    }

    public static Message Message(string type, int seq, string nonce)
    {
        var m = new Message();
        m.Header.SetField(new BeginString("FIX.4.4"));
        m.Header.SetField(new MsgType(type));
        m.Header.SetField(new SenderCompID(Contract.Peer(nonce)));
        m.Header.SetField(new TargetCompID(Contract.Engine(nonce)));
        m.Header.SetField(new MsgSeqNum((ulong)seq));
        m.Header.SetField(new SendingTime(DateTime.UtcNow));
        return m;
    }

    public async Task Send(Message m, CancellationToken token)
    {
        string raw = m.ConstructString();
        byte[] b = Encoding.Latin1.GetBytes(raw);
        if (b.Length > FrameLimit)
            throw new Problem("FRAME_LIMIT");
        Count(b.Length);
        if (++Frames > FrameCountLimit)
            throw new Problem("FRAME_COUNT_LIMIT");
        await Client.GetStream().WriteAsync(b, token);
        Trace.Outgoing.Write(b);
        Events.Add(new("peer-to-engine", raw));
    }

    private void Count(int n) => Budget.Add(n);
    internal void Feed(ReadOnlySpan<byte> bytes)
    {
        if (Pending.Count + bytes.Length > AccumulationLimit)
            throw new Problem("UNFRAMED_LIMIT"); // Before upstream parser allocation.
        Count(bytes.Length);
        foreach (byte b in bytes)
            Pending.Add(b);
        Parser.AddToStream(bytes);
    }

    internal Message? Take()
    {
        if (!Parser.ReadFixMessage(out string raw))
            return null;
        byte[] b = Encoding.Latin1.GetBytes(raw);
        if (b.Length > FrameLimit)
            throw new Problem("FRAME_LIMIT");
        if (Pending.Count < b.Length || !Pending.Take(b.Length).SequenceEqual(b))
            throw new Problem("FRAMING_GARBAGE");
        Pending.RemoveRange(0, b.Length);
        if (++Frames > FrameCountLimit)
            throw new Problem("FRAME_COUNT_LIMIT");
        var m = new Message();
        m.FromString(raw, true, Dictionary, Dictionary, new QuickFix.FIX44.MessageFactory());
        string type = m.Header.GetString(Tags.MsgType);
        DD.Validate(m, Dictionary, Dictionary, "FIX.4.4", type);
        if (m.Header.GetString(Tags.BeginString) != "FIX.4.4" || m.Header.GetString(Tags.SenderCompID) != Contract.Engine(Nonce) || m.Header.GetString(Tags.TargetCompID) != Contract.Peer(Nonce))
            throw new Problem("SESSION_MISMATCH", true);
        if (type is not ("A" or "0" or "1" or "2" or "5" or "B"))
            throw new Problem("UNEXPECTED_MESSAGE_TYPE", true);
        Events.Add(new("engine-to-peer-frame", raw));
        return m;
    }

    public async Task<Message> Read(CancellationToken token)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
        deadline.CancelAfter(TimeSpan.FromSeconds(10));
        while (true)
        {
            Message? ready = Take();
            if (ready != null)
                return ready;
            if (Budget.Remaining == 0)
                throw new Problem("WIRE_BYTE_LIMIT");
            byte[] b = new byte[Math.Min(1024, Budget.Remaining)];
            int n = await Client.GetStream().ReadAsync(b, deadline.Token);
            if (n == 0)
                throw new Problem("EARLY_DISCONNECT");
            Trace.Incoming.Write(b, 0, n);
            Feed(b.AsSpan(0, n));
        }
    }

    public async Task<Message> Need(string type, CancellationToken token, string? barrier = null)
    {
        for (int i = 0; i < FrameCountLimit; i++)
        {
            var m = await Read(token);
            string got = m.Header.GetString(Tags.MsgType);
            if (got == type && (barrier == null || (m.IsSetField(Tags.TestReqID) && m.GetString(Tags.TestReqID) == barrier)))
                return m;
            if (got != "0")
                throw new Problem("UNEXPECTED_PROTOCOL_STEP", true);
        }

        throw new Problem("FRAME_COUNT_LIMIT");
    }

    public int FrameCount => Frames;

    public void Dispose() => Client.Dispose();
}
