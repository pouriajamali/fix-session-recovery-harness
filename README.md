# FIX Session Recovery Harness

Three guided **synthetic loopback** cases around pinned QuickFIX/n1.14.1. See what
happens to a sequence gap, a duplicate and a stored resend, then inspect the raw
wire and worker receipts. This wraps an existing engine; it is not a new FIX engine.

| Engineering decision | Observable proof in the demo |
| --- | --- |
| Hold an out-of-sequence News until its gap is filled | ResendRequest covering2, callback order GAP2 then GAP3 |
| Repeating an accepted News must not trigger another callback in this case | Valid PossDup/OrigSendingTime repeat plus a subsequent session barrier; callbacks remain exactly those two |
| A resend preserves the original application body and sequence | News2/3 replay, PossDupFlag=Y and original SendingTime retained as OrigSendingTime |
| A controlled process restart must use released, persisted state | First child exits and drains, parent acquires exclusive store handles, second child continues sequence and replays prior News |

These are observations of three fixed cases, not a general exactly-once, crash
durability, counterparty certification or production guarantee. The
[decision/test map](docs/CASE-STUDY.md) identifies the tests and limitations.

Preview channel: **v0.1.0-preview.1**. [Downloads](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.1)
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
| 0 | All three complete expected observations passed |
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

Source requires SDK10.0.403:

```sh
dotnet restore tests/SessionHarness.Tests --locked-mode
dotnet run --project tests/SessionHarness.Tests -c Release --no-restore -- --work artifacts/tests
dotnet run --project src/SessionHarness -c Release -- demo "source demo output"
```

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
