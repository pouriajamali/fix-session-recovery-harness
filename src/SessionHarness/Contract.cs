using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace SessionHarness;

internal sealed class Problem(string code,bool failed=false):Exception(code)
{public string Code{get;}=code;public bool Failed{get;}=failed;}
internal static partial class Contract
{
    public const string Version="0.1.0-preview.1",DictionaryHash="a8111ec59d33053b45be975bbb7d6d1e9f2b6f4a160d832853fa0d8c627ea434";
    public static readonly JsonSerializerOptions Json=new(){PropertyNamingPolicy=JsonNamingPolicy.CamelCase,WriteIndented=true};
    [GeneratedRegex(@"\A[a-f0-9]{32}\z")]private static partial Regex NoncePattern();
    public static void Nonce(string value){if(!NoncePattern().IsMatch(value))throw new Problem("NONCE_INVALID");}
    public static string Engine(string nonce)=>"E"+nonce[..12];
    public static string Peer(string nonce)=>"P"+nonce[..12];
    public static string Session(string nonce)=>"FIX.4.4:"+Engine(nonce)+"->"+Peer(nonce);
    public static string DictionaryPath()
    {
        string path=Path.Combine(AppContext.BaseDirectory,"FIX44.xml");Safe.NoLinks(path);
        if(new FileInfo(path).Length!=340702 || Hash(path)!=DictionaryHash)throw new Problem("DICTIONARY_PIN_MISMATCH");return path;
    }
    public static string Hash(string p){using var stream=File.OpenRead(p);return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();}
}
internal static class Safe
{
    public static void NoLinks(string path)
    {
        string? p=Path.GetFullPath(path);
        while(p!=null)
        {
            FileSystemInfo f=Directory.Exists(p)?new DirectoryInfo(p):new FileInfo(p);
            if(f.LinkTarget!=null||(f.Exists&&(f.Attributes&FileAttributes.ReparsePoint)!=0))throw new Problem("LINK_UNSUPPORTED");p=Path.GetDirectoryName(p);
        }
    }
    public static string Normalize(string path)
    {
        if(path.Any(c=>char.IsControl(c)||c is '\u2028' or '\u2029' or '\ufeff')||path.StartsWith("//")||path.StartsWith(@"\\")||(!OperatingSystem.IsWindows()&&path.Contains('\\')))throw new Problem("PATH_UNSUPPORTED");
        string full=Path.TrimEndingDirectorySeparator(Path.GetFullPath(path));if(full.Length>384)throw new Problem("PATH_LIMIT");
        if(OperatingSystem.IsWindows()&&new DriveInfo(Path.GetPathRoot(full)!).DriveType==DriveType.Network)throw new Problem("NETWORK_PATH_UNSUPPORTED");NoLinks(full);return full;
    }
    public static void Fresh(string path,string nonce)
    {
        NoLinks(path);if(Directory.Exists(path)||File.Exists(path))throw new Problem("OUTPUT_EXISTS");Directory.CreateDirectory(path);NoLinks(path);
        using var stream=new FileStream(Path.Combine(path,".harness-owned"),FileMode.CreateNew,FileAccess.Write);stream.Write(System.Text.Encoding.ASCII.GetBytes(nonce));
    }
    public static void Owned(string path,string nonce)
    {
        NoLinks(path);string marker=Path.Combine(path,".harness-owned");NoLinks(marker);
        if(new FileInfo(marker).Length!=32||File.ReadAllText(marker)!=nonce)throw new Problem("OWNERSHIP_INVALID");
    }
    public static void StoreClosed(string store)
    {
        NoLinks(store);if(!Directory.Exists(store))throw new Problem("STORE_MISSING");
        int count=0;long bytes=0;
        foreach(string p in Directory.EnumerateFiles(store))
        {
            NoLinks(p);if(++count>8||(bytes+=new FileInfo(p).Length)>1024*1024)throw new Problem("STORE_LIMIT");
            using var held=new FileStream(p,FileMode.Open,FileAccess.ReadWrite,FileShare.None);
        }
        if(count!=4||Directory.EnumerateDirectories(store).Any())throw new Problem("STORE_SHAPE");
    }
}
internal sealed record WorkerReceipt(int Schema,bool Complete,string Nonce,string Scenario,string Phase,string Session,int Port,int Pid,string Outcome,string Reason,bool CleanStop,bool StoreClosed,ulong NextSender,ulong NextTarget,string[] Delivered,int GapRequestDeliveryCount);
internal sealed record ScenarioReceipt(string Scenario,string Outcome,bool Complete,string Reason,int Connections,int Frames,string[] Delivered,string StopBoundary,Dictionary<string,string> ArtifactHashes);
