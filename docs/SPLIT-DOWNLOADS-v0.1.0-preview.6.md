# Join and verify preview6 downloads

The Windows ZIP and Linux tar.gz are transported as five binary parts per OS,
each at most 8MiB. Download all five parts for your OS and the seven small
verification files listed below into a fresh directory. The source ZIP is an
optional separate direct download. Full native ZIP/tar.gz download assets are
not present; the commands join the parts into the original tested archives.

The runtime, original signed checksums, source ZIP and signed tag remain bound to
commit 5bb0931151ddf1f09ad17f80a752fdeabe041950 and tree
0615747afcd933692aa8b7aca64b236abd1f4e32. This later documentation change
only describes transport. Native BUILD-MANIFEST.json retains that exact runtime
source identity. The source ZIP intentionally contains the tested commit's
original documentation; use this current guide for split transport.

The expected SSH key fingerprint is
SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU.
Confirm it through an independently trusted maintainer channel or trusted
checkout before accepting the downloaded key. See [provenance](../PROVENANCE.md).
SSH file signatures authenticate bytes under that key; they are not Authenticode
or runtime/production certification. Stop on any failed check.

| Bundle | Download all five parts |
| --- | --- |
| Ubuntu x64 | [1](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part001) · [2](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part002) · [3](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part003) · [4](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part004) · [5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part005) |
| Windows x64 | [1](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part001) · [2](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part002) · [3](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part003) · [4](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part004) · [5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part005) |

[fix-session-recovery-harness-v0.1.0-preview.6-source.zip](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-source.zip), [SHA256SUMS.txt](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SHA256SUMS.txt), [SHA256SUMS.txt.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SHA256SUMS.txt.sig), [SIGNING-PUBLIC-KEY.pub](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SIGNING-PUBLIC-KEY.pub), [PARTS-MANIFEST.json](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-MANIFEST.json), [PARTS-MANIFEST.json.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-MANIFEST.json.sig), [PARTS-SHA256SUMS.txt](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-SHA256SUMS.txt), [PARTS-SHA256SUMS.txt.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-SHA256SUMS.txt.sig)

## Windows: PowerShell 7 and existing OpenSSH

After downloading the files, run in that fresh directory. This verifies all
three signed metadata files, all five selected part hashes, the manifest hash
and the original joined archive hash before extraction.

~~~powershell
$ErrorActionPreference = 'Stop'
$archive = 'fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip'
$info = @(& ssh-keygen -lf ./SIGNING-PUBLIC-KEY.pub)
if ($LASTEXITCODE -ne 0 -or $info.Count -ne 1 -or
    ($info[0].Trim() -split '\s+')[1] -cne 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU') {
    throw 'Untrusted signing key'
}
$key = (Get-Content -LiteralPath ./SIGNING-PUBLIC-KEY.pub -Raw).Trim()
[IO.File]::WriteAllText((Join-Path $PWD 'allowed-signers'), "pouriajamali $key`n", [Text.UTF8Encoding]::new($false))
function Verify-Signature([string]$name) {
    $start = [Diagnostics.ProcessStartInfo]::new('ssh-keygen')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    foreach ($arg in @('-Y','verify','-f','allowed-signers','-I','pouriajamali','-n','file','-s',"$name.sig")) {
        $start.ArgumentList.Add($arg)
    }
    $process = [Diagnostics.Process]::Start($start)
    $bytes = [IO.File]::ReadAllBytes((Join-Path $PWD $name))
    $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
    $process.StandardInput.Close()
    $process.WaitForExit()
    $code = $process.ExitCode
    $process.Dispose()
    if ($code -ne 0) { throw "Signature failed: $name" }
}
foreach ($name in @('SHA256SUMS.txt','PARTS-SHA256SUMS.txt','PARTS-MANIFEST.json')) {
    Verify-Signature $name
}
function Verify-Hash([string]$name, [string]$list) {
    $pattern = '^([0-9a-f]{64})  ' + [regex]::Escape($name) + '$'
    $rows = @(Get-Content -LiteralPath $list | Where-Object { $_ -cmatch $pattern })
    if ($rows.Count -ne 1 -or
        (Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash.ToLowerInvariant() -cne $rows[0].Substring(0,64)) {
        throw "Hash failed: $name"
    }
}
Verify-Hash 'PARTS-MANIFEST.json' 'PARTS-SHA256SUMS.txt'
$parts = 1..5 | ForEach-Object { '{0}.part{1:000}' -f $archive, $_ }
foreach ($part in $parts) { Verify-Hash $part 'PARTS-SHA256SUMS.txt' }
$out = [IO.File]::Open((Join-Path $PWD $archive), [IO.FileMode]::CreateNew)
try {
    foreach ($part in $parts) {
        $inputFile = [IO.File]::OpenRead((Join-Path $PWD $part))
        try { $inputFile.CopyTo($out) } finally { $inputFile.Dispose() }
    }
} finally { $out.Dispose() }
Verify-Hash $archive 'SHA256SUMS.txt'
Write-Output "Verified original archive: $archive"
# Only after success:
Expand-Archive -LiteralPath $archive -DestinationPath ./verified-win-x64
~~~

## Ubuntu: shell, existing OpenSSH and GNU sha256sum

~~~sh
set -eu
archive='fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz'
expected='SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
test "$(ssh-keygen -lf SIGNING-PUBLIC-KEY.pub | awk '{print $2}')" = "$expected"
printf 'pouriajamali %s\n' "$(cat SIGNING-PUBLIC-KEY.pub)" > allowed-signers
for name in SHA256SUMS.txt PARTS-SHA256SUMS.txt PARTS-MANIFEST.json; do
  ssh-keygen -Y verify -f allowed-signers -I pouriajamali -n file -s "$name.sig" < "$name"
done
test -f PARTS-MANIFEST.json
for suffix in 001 002 003 004 005; do test -f "$archive.part$suffix"; done
sha256sum --check --strict --ignore-missing PARTS-SHA256SUMS.txt
test ! -e "$archive" && test ! -L "$archive"
cat "$archive.part001" "$archive.part002" "$archive.part003" \
    "$archive.part004" "$archive.part005" > "$archive"
test "$(awk -v name="$archive" '$2 == name { count++ } END { print count+0 }' SHA256SUMS.txt)" -eq 1
sha256sum --check --strict --ignore-missing SHA256SUMS.txt
# Only after success:
mkdir verified-linux-x64
tar -xzf "$archive" -C verified-linux-x64
~~~

The selected joined archive must report OK. Missing other-OS files are ignored,
but all five explicitly named selected parts are mandatory. The direct source
ZIP, when downloaded, is also covered by the original SHA256SUMS.txt.
Keep extracted bundle files together; no installed .NET runtime/SDK is needed.
See [Try it](../README.md#try-it) for the existing native prerequisites and demo.

