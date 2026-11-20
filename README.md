# FIX Session Recovery Harness

Inspect how a FIX session handles sequence 3 arriving before 2, a duplicate,
a stored resend and a restart from saved state. Four guided **synthetic loopback**
cases use pinned QuickFIX/n 1.14.1; raw wire traces and worker receipts show what
happened. This wraps the existing engine.

[Signed preview6 downloads](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.6)
· [Exact runtime source: 5bb09311](https://github.com/pouriajamali/fix-session-recovery-harness/tree/5bb0931151ddf1f09ad17f80a752fdeabe041950)
· [Join and verify the split downloads](docs/SPLIT-DOWNLOADS-v0.1.0-preview.6.md)

Version **0.1.0-preview.6**: self-contained runtime 11.0.0, SDK 11.0.100/C#15
for source builds, report-v2. These are four fixed News/admin cases; they do not
establish general exactly-once behavior, crash durability, counterparty
certification or a production guarantee.

## Try it

1. Download all **five parts for your OS** and the seven small verification files
   from the [release](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.6).
   Follow the [Windows/Ubuntu join and signature checks](docs/SPLIT-DOWNLOADS-v0.1.0-preview.6.md)
   before extracting.
2. Keep the extracted self-contained bundle together and open a terminal there.
   No installed .NET SDK/runtime is needed; native OS prerequisites still apply.
   Existing-host checks are not empty-OS installation proof.
3. Run the existing four-case demo. The output directory must not exist.

Windows x64:

```powershell
.\session-harness.exe demo "new demo output"
Get-Content ".\new demo output\summary.txt"
```

Ubuntu24.04/glibc x64:

```sh
./session-harness demo "new demo output"
cat "new demo output/summary.txt"
```

A successful run exits 0 and starts the generated `summary.txt` with:

```text
FIX Session Recovery Harness: pass
```

The aggregate `summary.json` has `complete=true`, `outcome="pass"` and `exitCode=0`.
Its four cases are gap, resend, restart and gapfill. For example, the gap case
requests the missing sequence 2 and delivers GAP2 then GAP3; the GapFill case
skips a slot without fabricating News2.

Each scenario retains raw `peer-to-engine.fix` / `engine-to-peer.fix`, `events.json`,
worker receipts and hashes. Raw received bytes are retained even when they do
not form a valid frame; events list only successfully sent/validated received
frames. Fragmentation does not create an unbounded event list.

| Exit | Meaning |
| --- | --- |
| 0 | All four complete expected observations passed (candidate) |
| 2 | A completed bounded expectation failed; no successful demo claim |
| 1 | Incomplete/unsupported/I/O, deadline, process, protocol or report-write failure |

Always read overall outcome, `complete` and the reason; child exit0 alone is
insufficient. Kill/timeout failure teardown is never counted as a clean stop.
Reports publish JSON last, but the pair is not power-loss-atomic. Missing/invalid
JSON or a nonzero process exit must not be treated as success.

## What the demo checks

| Engineering decision | Observable proof in the demo |
| --- | --- |
| Hold an out-of-sequence News until its gap is filled | ResendRequest covering 2, callback order GAP2 then GAP3 |
| Repeating an accepted News must not trigger another callback in this case | Valid PossDup/OrigSendingTime repeat plus a subsequent session barrier; callbacks remain exactly those two |
| A resend preserves the original application body and sequence | News2/3 replay, PossDupFlag=Y and original SendingTime retained as OrigSendingTime |
| An admin GapFill skips a missing slot without inventing News | GapFill2 to3, callbacks GAPFILL3 then GAPFILL5, persisted nextTarget8 |
| A controlled process restart must use released, persisted state | First child exits and drains, parent acquires exclusive store handles, second child continues sequence and replays prior News |

See the [decision/test map](docs/CASE-STUDY.md) and [four-case contract](docs/CONTRACT.md) for assertions and limits.

## Downloads and verification

Native downloads use **five binary parts per OS, at most 8MiB each**.
[Join and verify on Windows or Ubuntu](docs/SPLIT-DOWNLOADS-v0.1.0-preview.6.md)
before extracting. The joined archives retain the tested runtime source
5bb0931151ddf1f09ad17f80a752fdeabe041950; source ZIP and signed tag are unchanged.
The original checksum/signature files are preserved, with separately signed
PARTS-MANIFEST.json and PARTS-SHA256SUMS.txt for transport.

| Bundle | Download all five parts |
| --- | --- |
| Ubuntu x64 | [1](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part001) · [2](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part002) · [3](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part003) · [4](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part004) · [5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part005) |
| Windows x64 | [1](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part001) · [2](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part002) · [3](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part003) · [4](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part004) · [5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part005) |

[fix-session-recovery-harness-v0.1.0-preview.6-source.zip](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-source.zip), [SHA256SUMS.txt](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SHA256SUMS.txt), [SHA256SUMS.txt.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SHA256SUMS.txt.sig), [SIGNING-PUBLIC-KEY.pub](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SIGNING-PUBLIC-KEY.pub), [PARTS-MANIFEST.json](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-MANIFEST.json), [PARTS-MANIFEST.json.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-MANIFEST.json.sig), [PARTS-SHA256SUMS.txt](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-SHA256SUMS.txt), [PARTS-SHA256SUMS.txt.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-SHA256SUMS.txt.sig)

Install only from a published release containing `SHA256SUMS.txt`,
`SHA256SUMS.txt.sig` and the pinned public key; follow
[checksum/signature verification](PROVENANCE.md). Source, a tag or CI success
alone does not establish publication. If the release page or signature is
missing, publication is incomplete; do not bypass verification.

## Boundaries

- Application messages are fixed FIX4.4 **News** with synthetic Headline labels;
  only logon/heartbeat/test-request/resend/logout admin messages are scripted.
  No order, quote, execution, broker, exchange, account or credentials are used.
- Parent binds literal127.0.0.1, port0, retaining ownership of that listener.
  Its owned child initiator connects only to that exact endpoint; per-run session
  IDs bind the peer. There is no public host/port/settings/dictionary/message
  import, proxy, TLS credential, arbitrary executable, plugin or store-reset option.
- QuickFIX/n owns session behavior and framing/validation. The peer is a fixed
  test script, not a second engine. Only the pinned bundled public FIX44 dictionary
  is accepted. Both exact NuGet package versions are locked and upstream notices
  are preserved. Source-reference pins are not independent upstream build proof.
- Reconnect is deliberately **socket loss followed by a clean process stop and
  a new process**, in the same run's fresh marked store. It is not a kill, power
  loss, live failover, arbitrary existing-store recovery or data repair experiment.
- Max32 budgeted frames per connection,8KiB/frame,16KiB unframed accumulation
  **before** adding to the upstream parser,256KiB total wire bytes across directions
  and both reconnect connections. Wire parsing does not silently discard leading
  garbage. Raw traces and frame event counts are bounded independently.
- Individual network waits10seconds; parent scenario deadline30seconds, then
  separate bounded owned-process termination/drain handling. Stdout16KiB and
  stderr4KiB drain concurrently. Native memory, disk operations, hostile local
  users/filesystem races and OS termination failures are not sandbox guarantees.
- Fresh local output only; links/reparse components, path controls, network-style
  paths and existing destinations are refused. Remote mounts are unsupported and
  not universally detectable. Owned failure evidence/store may remain. Caller
  files and unrelated processes are never reset, overwritten or recursively removed.

## Build and test

Use the pinned SDK11.0.100/runtime11.0.0 and stable C#15 for this source.
Restore requires repository-signed NuGet packages and all-package vulnerability
auditing. The release's local qualification uses independent source/input-bound
Windows Job and Ubuntu cgroup phases with actual CPU2/2GiB readbacks and a shared
serial execution lane. Windows256processes and Linux256tasks are different caps.
Source commands alone do not establish those qualification observations.

The original SDK404 launcher/profile and hosted transport tools belong to frozen
preview5 evidence. They are not an SDK11 admission or the preview6 delivery route.
GitHub Actions was not run for preview6. The source commands within the controlled
matching-OS phases are:

```sh
# Example inside the admitted phase: linux-x64; use win-x64 on Windows.
dotnet restore tests/SessionHarness.Tests -p:RuntimeIdentifier=linux-x64 -p:SelfContained=true --locked-mode --disable-parallel -p:NuGetAuditMode=all -p:DisableTransitiveFrameworkReferenceDownloads=true
dotnet build tests/SessionHarness.Tests -c Release -p:RuntimeIdentifier=linux-x64 -p:SelfContained=true --no-restore -m:1 -p:BuildInParallel=false -p:UseSharedCompilation=false -nodeReuse:false -p:DisableTransitiveFrameworkReferenceDownloads=true
dotnet run --project tests/SessionHarness.Tests -c Release -p:RuntimeIdentifier=linux-x64 -p:SelfContained=true --no-build --no-restore -- --work artifacts/tests
```

Keep the selected RID consistent through restore, build, tests, packaging and the
extracted consumer check. Complete one RID before starting the other; both use
the same source `obj` directories. Release the shared local lane between phases.
Per-RID locks are selected by the singular `RuntimeIdentifier` property; a
portable restore does not qualify them. A restore/pin is content evidence, not
successful compilation, fixture execution or an extracted-package result.

Use fresh test/demo paths. Tests cover real loopback cases, fragmented/coalesced
frames, raw accumulation/count/byte limits, malformed checksum/session/receipts,
real child hangs/pipe floods/exit0-empty/exit17, exclusive store handles, path
controls, symlink refusal and report collisions. Fault probes exist only in the
separate test assembly, excluded from consumer bundles. Windows without local
symlink privilege reports a skip; Ubuntu exercises that case. The
[matching-OS workflow](https://github.com/pouriajamali/fix-session-recovery-harness/actions/workflows/verify.yml)
also runs each actual extracted consumer package. No benchmark was performed.

See the [contract](docs/CONTRACT.md), [contribution guide](CONTRIBUTING.md) and
[notices](NOTICE.md). Use only synthetic evidence when reporting an issue.

## Existing engine and licenses

QuickFIX/n's public acceptance/unit tests already cover session recovery behavior.
This tool adds a small guided demo, explicit assertions/receipts and ready bundles;
it does not claim to invent sequencing, improve engine performance or certify FIX.

This product includes software developed by quickfixengine.org (http://www.quickfixengine.org/).

Independent synthetic wrapper created with AI assistance for Pouria Jamali,
November2026; original wrapper [MIT](LICENSE). QuickFIX/n and the public dictionary
retain the separate [QuickFIX Software License](vendor/QUICKFIX-LICENSE), copyright,
required acknowledgment and naming/non-endorsement conditions. Microsoft runtime
and dependencies retain their own notices. No private/shared/employer/customer
code, dictionary, contract or data is included. No deployment, market study,
customer, revenue, security certification or independent-skill claim is made.

[CI resource policy](docs/CI-POLICY.md) defines hosted validation scope; preview6 qualification and the current documentation delivery use the owner-authorized local route without running Actions. Published runtime tags and release assets remain immutable.

## Source readability

The current source expands compact C# layout for review. The legacy preview1 links identify its frozen runtime release. Formatting preserves complete syntax, token text and values, comments and directives; it does not introduce a runtime behavior or performance claim.

To reproduce a published package, use the exact source archive/commit identified by that release's signed checksums and provenance. The [legacy/frozen v0.1.0-preview.1 source](https://github.com/pouriajamali/fix-session-recovery-harness/tree/330ae8f927395564937ed1043510d60a87b9987d) (`330ae8f927395564937ed1043510d60a87b9987d`) belongs specifically to preview1/runtime14. Review later `main` snapshots separately from those frozen release commits.

## Qualification and release history

Preview6 used actual local Windows/Ubuntu qualification; GitHub Actions CI was
not run, by owner instruction. [Maintenance notes](docs/RELEASE-v0.1.0-preview.6.md)
retain native counts, host/resource limits, dependency decisions and process
diagnostics. Windows11 26H2 vendor support remains unconfirmed; the Ubuntu host
was existing Ubuntu24.04/WSL2.

The [frozen preview5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.5)
retains its separately qualified SDK404/runtime15 and signed assets.

The [preview5 notes](docs/RELEASE-v0.1.0-preview.5.md#archived-qualification-and-release-operations)
retain the complete historical hosted runs, failures, transport decisions and
independent recovery boundaries. These do not establish preview6 CI success.

Legacy/frozen preview: **v0.1.0-preview.1** (three cases/runtime14).
[Legacy preview1 downloads](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.1)
belong to that frozen version.
