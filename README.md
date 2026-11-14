# FIX Session Recovery Harness

Four guided **synthetic loopback** cases around pinned QuickFIX/n1.14.1. See what
happens to a sequence gap, a duplicate and a stored resend, then inspect the raw
wire and worker receipts. This wraps an existing engine; it is not a new FIX engine.

| Engineering decision | Observable proof in the demo |
| --- | --- |
| Hold an out-of-sequence News until its gap is filled | ResendRequest covering2, callback order GAP2 then GAP3 |
| Repeating an accepted News must not trigger another callback in this case | Valid PossDup/OrigSendingTime repeat plus a subsequent session barrier; callbacks remain exactly those two |
| A resend preserves the original application body and sequence | News2/3 replay, PossDupFlag=Y and original SendingTime retained as OrigSendingTime |
| An admin GapFill skips a missing slot without inventing News | GapFill2 to3, callbacks GAPFILL3 then GAPFILL5, persisted nextTarget8 |
| A controlled process restart must use released, persisted state | First child exits and drains, parent acquires exclusive store handles, second child continues sequence and replays prior News |

These are observations of four fixed cases, not a general exactly-once, crash
durability, counterparty certification or production guarantee. The
[decision/test map](docs/CASE-STUDY.md) identifies the tests and limitations.

Source candidate: **0.1.0-preview.2**, SDK10.0.404/runtime10.0.15, report-v2.
Native qualification and signed publication of this candidate are pending; no release claim follows from source preparation.

Frozen published preview: **v0.1.0-preview.1** (three cases/runtime14). [Downloads](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.1)
and [checksum/signature verification](PROVENANCE.md). A missing release/signature
is incomplete publication; do not bypass verification.

## Try it

Extract the complete self-contained bundle and keep its files together. No
installed .NET SDK/runtime is needed; supported native OS prerequisites still
apply. Existing-host/CI tests are not empty-OS installation proof.

Windows x64:

```powershell
.\session-harness.exe --version
.\session-harness.exe demo "new demo output"
```

Ubuntu24.04/glibc x64:

```sh
./session-harness --version
./session-harness demo "new demo output"
```

The directory must not exist. Read `summary.txt` and `summary.json`. Each scenario
has raw `peer-to-engine.fix` / `engine-to-peer.fix`, a readable `events.json`,
complete worker receipts and hashes. Raw received bytes are retained even when
they do not form a valid frame; events list only successfully sent/validated
received frames. Fragmentation does not create an unbounded event list.

| Exit | Meaning |
| --- | --- |
| 0 | All four complete expected observations passed (candidate) |
| 2 | A completed bounded expectation failed; no successful demo claim |
| 1 | Incomplete/unsupported/I/O, deadline, process, protocol or report-write failure |

Always read overall outcome, `complete` and the reason; child exit0 alone is
insufficient. Kill/timeout failure teardown is never counted as a clean stop.
Reports publish JSON last, but the pair is not power-loss-atomic. Missing/invalid
JSON or a nonzero process exit must not be treated as success.

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

Candidate source pins SDK10.0.404 and runtime10.0.15. Local execution first requires the
manager's exact input/profile admission. The fixed project08 launcher enforces the
approved phase, owned E outputs, canonical lane and actual Job/cgroup limits; no
uncapped fallback or direct SDK probe/bootstrap is supported. Windows256processes
and Linux256tasks are different limits, not an equal thread-cap claim.

Private local qualification uses its separately admitted fixed launcher.
Hosted qualification uses `tools/project08_hosted.py`, the SDK404 archive/member
pins and a fresh actual matching-OS Job/cgroup proof; it does not reuse a local
workspace admission or SDK11. Source/CI authorization is a separate gate.
The equivalent bounded source commands inside an admitted phase are:

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

[CI resource policy](docs/CI-POLICY.md): documentation-only changes get real lightweight document/pipeline checks; source, tag and manual runs retain native validation. Published runtime tags and release assets remain unchanged.

## Source readability

The current source expands compact C# layout for review. The published preview links identify its frozen runtime release. Formatting preserves complete syntax, token text and values, comments and directives; it does not introduce a runtime behavior or performance claim.

To reproduce a published package, use its exact original runtime source: [v0.1.0-preview.1 source](https://github.com/pouriajamali/fix-session-recovery-harness/tree/330ae8f927395564937ed1043510d60a87b9987d) (`330ae8f927395564937ed1043510d60a87b9987d`). Later `main` layout is reviewed separately from those frozen release commits.

## Candidate process diagnostics

Each worker phase adds a bounded `<phase>-process.json` with schema
`fix-session-harness-process-v1`, bound nonce/scenario/phase/session/port/PID/start
identity, observed nullable exit code, drain and forced-cleanup state. The strict
worker receipt remains schema1 and the aggregate report is
`fix-session-harness-report-v2`. An unobserved exit is unknown; cleanup never
proves cleanStop/storeClosed. Diagnostic/report-write failure makes the run
incomplete and preserves the original cause where output remains writable.

The test-only NewSeqNo4 variant must finish barriers/logout and produce a
completed semantic failure/exit2. Timeout, bad frame or child/protocol failure is
incomplete/exit1 and cannot pass that negative test. No negative fixture option is
available in the consumer CLI. Source preparation alone proves none of these results.

Hosted proof acceptance requires the complete fixed 74 test observations and
13 own package consumer checks, plus the complete seven-test offline release
suite. Only the named Windows symlink privilege case may skip. Producer and
release aggregation validate closed finite schemas, attempt1/source/OS/RID,
same-commit SDK404 member/source pins, observed capped SDK404/runtime15 results,
and actual package archive/manifest byte identities. Public finite observations
are separate from nonce-salted commitments to private source evidence; those
commitments are not inspectable SDK input or independent execution proof.

Source CI exports the six finite native-proof files through bounded framed logs,
with no artifact or cache writes. Tag/manual transport uses only an exact
same-run cache handoff; its expected digest and file hashes come from trusted
producer outputs outside the cache. Aggregation requires authenticated actual
save evidence, exact availability/key outputs and actual archive/proof byte
bindings before draft staging. DRAFT-STAGE is a typed finite log frame. No SDK or
execution result is reused from cache. The configured cache limit is UNKNOWN;
availability and the <=226MiB envelope remain actual-event gates.
