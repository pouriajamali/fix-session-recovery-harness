# v0.1.0-preview.1 — three bounded synthetic FIX session cases

Self-contained Windows x64 and Ubuntu24.04/glibc x64 preview bundles. Verify signed
checksums first. Guided gap+duplicate callback, stored resend and controlled
two-process stop/reconnect, with raw synthetic wire, bounded worker receipts,
summary.txt/JSON and hashes. Existing QuickFIX/n1.14.1 owns session behavior;
this is a guided wrapper, not a new engine.

This product includes software developed by quickfixengine.org (http://www.quickfixengine.org/).

Original wrapper MIT; QuickFIX/n/dictionary retain their separate complete license
and required notices. No upstream endorsement. No real order, broker/exchange,
account, external endpoint, arbitrary settings/dictionary/store import, general
exactly-once, FIX certification, performance, crash durability or production claim.
Kill/timeout teardown cannot count as a clean stop; source/CI/signatures are not
runtime safety, exclusive authorship or OS binary signatures.

Matching-OS CI executes each actual archive; release aggregation does not rebuild
them. SHA256SUMS covers three archives, with known-key SSH checksum signature and
public key supplied separately. Binaries are not Authenticode-signed.
