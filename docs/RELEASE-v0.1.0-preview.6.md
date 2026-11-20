# v0.1.0-preview.6 - .NET11 technology maintenance

SDK11.0.100, self-contained runtime11.0.0, net11.0 and stable C#15 replace the
preview5 toolchain. QuickFIX/n.Core/FIX44 remain1.14.1 with the same two QuickFIX
package versions/content hashes and fixed FIX44 dictionary. .NET11 supplies
Logging/DI abstractions in its base runtime; SDK11 prunes the old8.x NuGet entries,
and the runtime package pin binds the actual replacement assembly hashes. Portable/RID locks
and runtime redistribution notices are generated/verified by the actual SDK.
No trimming, AOT, ReadyToRun or new product capability is enabled.

All four synthetic News/admin scenarios and report-v2/process-v1 retain their
contracts. GapFill, wrongNewSeqNo completed semantic failure2 versus incomplete1,
clean exit/store closure versus forced cleanup and actual extracted consumers
remain mandatory checks. Local source/test/package receipts identify exact
source and observed results; the release body records the final per-OS counts.

Actual local execution uses serial own CPU2/2GiB Windows Job/Linux cgroup phases,
256processes-or-tasks, Linuxswap0 and the original900s/RID cumulative ceiling.
SDK input identities are reused; current host/PID/kernel/terminal observations
are collected separately. Windows11 26H2 vendor support remains unconfirmed;
local compatibility evidence must not be described as vendor certification.
Linux execution uses the existing Ubuntu24.04 WSL2 host. x64 requires x86-64-v2
and existing native OS prerequisites; no clean-machine proof is claimed.

GitHub Actions CI was not run, per owner instruction. Valid matching-OS local
build/tests/package/consumer checks, known-key signing and direct publication
replace Actions. The historical preview5 whole tag CI failure and independently
completed release remain historical facts, separate from this local release.

Install only from a published release with exact archives, SHA256SUMS.txt,
SHA256SUMS.txt.sig and the pinned public key. A source commit, tag or missing
release page/signature is not publication. Verify [provenance](../PROVENANCE.md).
Old tags, assets, signatures, upstream licenses, dictionary and notices remain
immutable. No counterparty, market, production, performance or durability claim.

[Official .NET11 framework-provided Extensions compatibility change](https://learn.microsoft.com/en-us/dotnet/core/compatibility/extensions/11/extensions-in-shared-framework) explains this necessary SDK-generated graph delta.

## Native validation and split delivery

The signed runtime/source commit is 5bb0931151ddf1f09ad17f80a752fdeabe041950.
Windows:73 passed,0 failed,1 allowed symlink-privilege skip.
Ubuntu:74 passed,0 failed,0 skipped. Each RID passed13 original extracted consumer
checks and7 publication guards. Original cumulative native budgets consumed
170.828s on Windows and284.398s on Linux, each within900s/RID.
No SDK/build/test replay or Actions was used for this transport-only follow-up.

Each native archive uses five <=8MiB binary transport parts. Joining them recovers
the exact originally tested and signed ZIP/tar.gz. Original SUMS/SIG remain
unchanged. Separate manifest/checksums and known-key signatures authenticate the
parts; the small source ZIP remains a direct download. The signed tag/source ZIP
retain the runtime commit. Later documentation on main does not change that runtime commit.

Follow [Windows/Linux join and verification](SPLIT-DOWNLOADS-v0.1.0-preview.6.md).

| Bundle | Download all five parts |
| --- | --- |
| Ubuntu x64 | [1](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part001) · [2](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part002) · [3](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part003) · [4](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part004) · [5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-linux-x64.tar.gz.part005) |
| Windows x64 | [1](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part001) · [2](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part002) · [3](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part003) · [4](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part004) · [5](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-win-x64.zip.part005) |

[fix-session-recovery-harness-v0.1.0-preview.6-source.zip](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/fix-session-recovery-harness-v0.1.0-preview.6-source.zip), [SHA256SUMS.txt](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SHA256SUMS.txt), [SHA256SUMS.txt.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SHA256SUMS.txt.sig), [SIGNING-PUBLIC-KEY.pub](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/SIGNING-PUBLIC-KEY.pub), [PARTS-MANIFEST.json](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-MANIFEST.json), [PARTS-MANIFEST.json.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-MANIFEST.json.sig), [PARTS-SHA256SUMS.txt](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-SHA256SUMS.txt), [PARTS-SHA256SUMS.txt.sig](https://github.com/pouriajamali/fix-session-recovery-harness/releases/download/v0.1.0-preview.6/PARTS-SHA256SUMS.txt.sig)

## Toolchain qualification context

The November19,2026 technology upgrade retains QuickFIX/n1.14.1, its dictionary,
all four fixed scenarios, wire/report/process contracts and bounded native controls.
.NET11 is an [active supported release through November14,2028](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core);
SDK11.0.100/runtime11.0.0 is the [current servicing pair](https://dotnet.microsoft.com/en-us/download/dotnet/11.0).
NuGet signatures are required and auditing remains enabled for all dependencies.
Qualification, tests and consumer checks use actual local Windows/Ubuntu processes;
GitHub Actions CI was not run, by owner instruction. See the
[these maintenance notes](RELEASE-v0.1.0-preview.6.md) for host and provenance limits.

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
