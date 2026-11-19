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
