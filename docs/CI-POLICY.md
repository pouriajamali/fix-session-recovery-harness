# CI resource policy

This workflow policy separates documentation checks from unchanged runtime builds. It does not change application behavior, dependencies, release versions, published assets, account budgets or repository protection.

- Push validation targets the default `main` branch; pull requests retain validation without an extra feature-branch push run. Existing tag patterns are preserved. Manual dispatch always requests full native checks.
- A narrow documentation allowlist gets real UTF-8/framing, Markdown fence/relative-link and frozen-evidence JSON checks, plus policy contract tests and pinned actionlint. It does not run .NET/C++ builds or upload native artifacts. This is not an exhaustive prose/security audit.
- Runtime/configuration/fixtures/licenses/provenance/pipeline changes and unknown/failed Git comparisons always require the original native checks. Source, Windows/Linux execution, native package inspection and release/provenance commands remain present. Tags and manual runs cannot take the docs-only route.
- Lightweight checks also statically read the explicit source-package inventories where present, without importing the packager. A new unallowlisted document, symlink mode or computed/unknown inventory cannot hide behind docs-only success.
- Main, tag and manual runs have unique concurrency groups. A docs push cannot replace an earlier pending source run. Only superseded PR runs may be cancelled; classification uses the complete PR delta from its merge base.
- Matrix native jobs use `max-parallel: 1`; Book Replay keeps its two separately defined platform jobs. This is a per-workflow limit, not an account-wide cap. Rollouts are staged rather than starting fourteen heavy runs together.
- Existing native job timeouts remain. Previously unbounded native and comparison/release jobs receive finite timeouts. No source test is replaced by an artificial green check.
- Routine source/PR jobs still build, extract and execute the original native packages, but do not upload the large `bundle-*`, `binary-*` or `tested-*` archives. Finite proof receipts remain. Tag/manual runtime-review runs still upload those required archives; small `checked-source-*` pairs remain on ordinary runs because downstream byte-comparison jobs consume them. No source/native check or release gate is replaced by this upload saving.
- Future Actions uploads retain ordinary source/PR artifacts for **3 days**, and tag/manual review artifacts for **7 days**. These are temporary CI artifacts. Published release archives, checksums, signatures and keys are separate and remain immutable.
- New retention does not delete old artifacts or logs. No artifact/cache deletion, paid capacity, self-hosted runner, account permission or budget change is performed by this policy. Any historical cleanup requires a separately reviewed inventory and explicit authorization.

The lightweight job uses only the standard Ubuntu runner, Python's standard library, and actionlint 1.7.12 downloaded from its official release with an exact archive SHA256. It does not claim optional external ShellCheck/Pyflakes results. Current account storage usage is not inferred from one repository's artifact byte count.

## Preview2 candidate route

The local contract grants no CI event. Exact candidate source/tag/draft staging
must be approved first. Maximum reservation:three events/120runner-min,226MiB
aggregate proof/tag artifact storage; ordinary proof3days and tag proof/archive7days.
No paid override, extra watcher, storage cleanup or duplicate unchanged dispatch.
Actual current quota/headroom and hosted profile admission are gates.

The native matrix remains max-parallel1 with15min jobs. Custom executable tests
and all four cases on each actual extracted native archive remain mandatory.
Hosted execution must use an admitted project08 kernel profile; a missing hosted
admission fails closed before SDK execution. Local E admission is not a hosted
runner admission. Docs-only green never qualifies changed runtime/source.

The tag release job stages a draft only, preserving already-tested native archives.
The sole manager operator signs exact SUMS through its existing known-key agent,
verifies all actual draft bytes, obtains the exact six-asset public gate, then
publishes and re-downloads stable public assets. No unsigned public fallback.

## Candidate adapter and exact-source handoff

The current preview2 workflow source is deliberately blocked before hosted SDK
execution. The unconditional hosted-adapter HOLD is not a completed adapter and
must be replaced under the separate exact source/CI gate before a public
candidate is sealed. Local E admission and local native evidence cannot supply a
fresh hosted runner's input or containment admission.

The gate packet must bind the same final commit/tree for both native jobs, exact
SDK404/runtime15 producer inputs, the actual Windows Job/Linux cgroup profile,
fixed singular RID commands and the cumulative native cap. The hosted producer
and adapter must be allocated before the SDK step; there is no uncapped
`setup-dotnet` fallback. Existing healthy local control evidence is not a
hosted-control proof.

The fixed native chain is locked restore, build, custom executable regressions,
package, extract and consumer. Each step carries the same RID and commit.
Only after actual consumer exit0 and a terminal admitted tree may the native
owner emit `project08-native-proof-v1`, bound to the actual workflow run ID,
SDK/runtime, four cases, and hashes of tests, consumer, kernel, subprocess
membership and terminal records. Missing emission wiring is a source gate,
not permission to synthesize a proof from local PASS.

Use one canonical upload layout: `artifacts/native-proofs/<rid>/native-proof.json`
plus its five referenced proof files. Upload the parent
`artifacts/native-proofs` as the small `proof-<rid>` artifact; download both
with merge enabled into the same parent. Aggregation then consumes
`<proof-root>/<rid>/native-proof.json`. Raw wire/process logs, local nonces and
PID-bearing private evidence are excluded; any finite exported identity must
retain verifiable cross-file binding and its source evidence hash.

Aggregation verifies the two already-executed archives and those two exact-run
proofs, then creates the exact source archive and SUMS without rebuilding.
It stages exactly five draft assets (two native archives, source, SUMS, public
key) and binds their actual IDs/sizes/digests in DRAFT-STAGE. The sole manager
then signs SUMS, verifies the six actual draft assets, obtains the exact public
gate and publishes/re-downloads them. No signature, upload or public operation
is authorized by this document.

These adapter/proof-layout requirements must be implemented and reviewed before
the final public candidate seal; an always-HOLD workflow or absent native-proof
producer is not release readiness. If that changes source commit identity after
local qualification, the exact-candidate gate must explicitly reconcile valid
evidence and remaining budgets; it cannot silently relabel old packages.
