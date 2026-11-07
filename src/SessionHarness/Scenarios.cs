using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using QuickFix;
using QuickFix.Fields;

namespace SessionHarness;

internal static class Scenarios
{
    private static void Require(bool condition,string code){if(!condition)throw new Problem(code,true);}
    private static async Task Logon(Wire wire,string nonce,int seq,int expected,CancellationToken token)
    {
        var first=await wire.Need("A",token);Require(first.Header.GetULong(Tags.MsgSeqNum)==(ulong)expected,"LOGON_SEQUENCE_MISMATCH");
        Require(!first.IsSetField(Tags.ResetSeqNumFlag)||!first.GetBoolean(Tags.ResetSeqNumFlag),"UNEXPECTED_RESET");
        var answer=Wire.Message("A",seq,nonce);answer.SetField(new EncryptMethod(0));answer.SetField(new HeartBtInt(30));await wire.Send(answer,token);
    }
    private static Message News(string nonce,int seq,string headline,DateTime? original=null)
    {
        var m=Wire.Message("B",seq,nonce);m.SetField(new Headline(headline));
        if(original.HasValue){m.Header.SetField(new PossDupFlag(true));m.Header.SetField(new OrigSendingTime(original.Value));}return m;
    }
    private static async Task Barrier(Wire wire,string nonce,int seq,string id,CancellationToken token)
    {var request=Wire.Message("1",seq,nonce);request.SetField(new TestReqID(id));await wire.Send(request,token);await wire.Need("0",token,id);}
    private static async Task Logout(Wire wire,string nonce,int seq,CancellationToken token)
    {await wire.Send(Wire.Message("5",seq,nonce),token);await wire.Need("5",token);}
    private static void Replay(Message original,Message replay,string headline)
    {
        Require(original.GetString(Tags.Headline)==headline&&replay.GetString(Tags.Headline)==headline,"REPLAY_BODY_MISMATCH");
        Require(original.Header.GetULong(Tags.MsgSeqNum)==replay.Header.GetULong(Tags.MsgSeqNum)&&replay.Header.GetBoolean(Tags.PossDupFlag)&&replay.Header.GetString(Tags.OrigSendingTime)==original.Header.GetString(Tags.SendingTime),"REPLAY_METADATA_MISMATCH");
        Require(original.Select(f=>new{f.Key,Value=f.Value.ToString()}).SequenceEqual(replay.Select(f=>new{f.Key,Value=f.Value.ToString()})),"REPLAY_BODY_MISMATCH");
    }
    public static async Task<ScenarioReceipt> Run(string root,string scenario,string nonce)
    {
        string folder=Path.Combine(root,scenario);Safe.Fresh(folder,nonce);List<WireEvent> events=[];List<WorkerReceipt> workers=[];int frames=0,connections=0;bool complete=false;string outcome="incomplete",reason="NOT_COMPLETED";
        using var deadline=new CancellationTokenSource(TimeSpan.FromSeconds(30));var listener=new TcpListener(IPAddress.Loopback,0);listener.Start(2);
        int port=((IPEndPoint)listener.LocalEndpoint).Port;var budget=new WireBudget();var trace=new WireTrace();
        try
        {
            string phase=scenario=="restart"?"first":"single";
            using(var child=new OwnedChild(folder,nonce,scenario,phase,port))
            using(var wire=new Wire(await listener.AcceptTcpClientAsync(deadline.Token),nonce,events,budget,trace))
            {
                connections++;await Logon(wire,nonce,1,1,deadline.Token);
                if(scenario=="gap")
                {
                    DateTime orig=DateTime.UtcNow.AddSeconds(-1);await wire.Send(News(nonce,3,"GAP3"),deadline.Token);
                    var request=await wire.Need("2",deadline.Token);ulong begin=request.GetULong(Tags.BeginSeqNo),end=request.GetULong(Tags.EndSeqNo);
                    Require(begin==2&&(end==0||end>=2),"RESEND_RANGE_MISMATCH");
                    await wire.Send(News(nonce,2,"GAP2",orig),deadline.Token);await Barrier(wire,nonce,4,"AFTER_GAP",deadline.Token);
                    await wire.Send(News(nonce,2,"GAP2",orig),deadline.Token);await Barrier(wire,nonce,5,"AFTER_DUPLICATE",deadline.Token);
                    await Logout(wire,nonce,6,deadline.Token);
                }
                else if(scenario=="resend")
                {
                    var a=await wire.Need("B",deadline.Token);var b=await wire.Need("B",deadline.Token);
                    Require(a.Header.GetULong(Tags.MsgSeqNum)==2&&b.Header.GetULong(Tags.MsgSeqNum)==3,"ORIGINAL_SEQUENCE_MISMATCH");
                    var request=Wire.Message("2",2,nonce);request.SetField(new BeginSeqNo(a.Header.GetULong(Tags.MsgSeqNum)));request.SetField(new EndSeqNo(b.Header.GetULong(Tags.MsgSeqNum)));await wire.Send(request,deadline.Token);
                    Replay(a,await wire.Need("B",deadline.Token),"RESEND_A");Replay(b,await wire.Need("B",deadline.Token),"RESEND_B");await Logout(wire,nonce,3,deadline.Token);
                }
                else
                {
                    var original=await wire.Need("B",deadline.Token);Require(original.GetString(Tags.Headline)=="RESTART_NEWS","RESTART_ORIGINAL_MISMATCH");
                    // Retain the original validated message for the second process comparison.
                    using(var originalFile=new FileStream(Path.Combine(folder,"original.fix"),FileMode.CreateNew,FileAccess.Write))originalFile.Write(Encoding.Latin1.GetBytes(original.ToString()));
                    wire.Dispose(); // Deliberate socket loss followed by a clean owned-process stop.
                }
                frames+=wire.FrameCount;workers.Add(await child.Stop(deadline.Token));
            }
            if(scenario=="gap")Require(workers[0].Delivered.SequenceEqual(new[]{"GAP2","GAP3"})&&workers[0].GapRequestDeliveryCount==0,"CALLBACK_ORDER_OR_DUPLICATE_MISMATCH");
            else Require(workers[0].Delivered.Length==0,"UNEXPECTED_APPLICATION_CALLBACK");
            if(scenario=="restart")
            {
                Safe.StoreClosed(Path.Combine(folder,"store")); // Parent independently holds exclusive handles before next start.
                var prior=workers[0];Require(prior.NextSender<100&&prior.NextTarget<100,"SEQUENCE_LIMIT");
                using var child=new OwnedChild(folder,nonce,scenario,"second",port);
                using var wire=new Wire(await listener.AcceptTcpClientAsync(deadline.Token),nonce,events,budget,trace);connections++;
                await Logon(wire,nonce,(int)prior.NextTarget,(int)prior.NextSender,deadline.Token);
                var request=Wire.Message("2",(int)prior.NextTarget+1,nonce);request.SetField(new BeginSeqNo(2));request.SetField(new EndSeqNo(2));await wire.Send(request,deadline.Token);
                var original=new Message(File.ReadAllText(Path.Combine(folder,"original.fix"),Encoding.Latin1),new QuickFix.DataDictionary.DataDictionary(Contract.DictionaryPath()),new QuickFix.DataDictionary.DataDictionary(Contract.DictionaryPath()),true);
                Replay(original,await wire.Need("B",deadline.Token),"RESTART_NEWS");await Logout(wire,nonce,(int)prior.NextTarget+2,deadline.Token);frames+=wire.FrameCount;workers.Add(await child.Stop(deadline.Token));
                Require(workers[1].Delivered.Length==0,"UNEXPECTED_APPLICATION_CALLBACK");
            }
            complete=true;outcome="pass";reason="BOUNDED_SCENARIO_OBSERVED";
        }
        catch(Problem p){complete=p.Failed;outcome=p.Failed?"fail":"incomplete";reason=p.Code;}
        catch(Exception e) when(e is not OutOfMemoryException)
        {complete=false;outcome="incomplete";reason="IO_PROCESS_OR_PROTOCOL_FAILURE";}
        finally{listener.Stop();}
        Safe.Owned(folder,nonce);
        Dictionary<string,string> hashes=[];
        void Write(string name,byte[] bytes){using var f=new FileStream(Path.Combine(folder,name),FileMode.CreateNew,FileAccess.Write);f.Write(bytes);f.Close();hashes[name]=Contract.Hash(Path.Combine(folder,name));}
        Write("peer-to-engine.fix",trace.Outgoing.ToArray());Write("engine-to-peer.fix",trace.Incoming.ToArray());
        trace.Incoming.Dispose();trace.Outgoing.Dispose();
        Write("workers.json",Encoding.UTF8.GetBytes(JsonSerializer.Serialize(workers,Contract.Json)+"\n"));
        Write("events.json",Encoding.UTF8.GetBytes(JsonSerializer.Serialize(events.Select(e=>new{e.Direction,Wire=e.Raw.Replace('\x01','|')}),Contract.Json)+"\n"));
        foreach(string name in new[]{"single-stdout.json","single-stderr.bin","first-stdout.json","first-stderr.bin","second-stdout.json","second-stderr.bin","original.fix"})
            if(File.Exists(Path.Combine(folder,name))){Safe.NoLinks(Path.Combine(folder,name));hashes[name]=Contract.Hash(Path.Combine(folder,name));}
        frames=events.Count; // Successful sent / validated received frames, including on a partial run.
        return new(scenario,outcome,complete,reason,connections,frames,workers.SelectMany(w=>w.Delivered).ToArray(),$"Verified clean process stops: {workers.Count}/{(scenario=="restart"?2:1)}; failure teardown is not counted; no crash durability proof",hashes);
    }
}
