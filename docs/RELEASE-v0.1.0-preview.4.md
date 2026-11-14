# v0.1.0-preview.4 - bounded observable-transport recovery preview

Version0.1.0-preview.4 replaces the opaque aggregation reader with typed bounded
stdlib HTTPS and finite first-stage diagnostics. The News/admin scenarios,
report-v2/process-v1, QuickFIX/n1.14.1, dictionary, SDK10.0.404/runtime10.0.15,
native containment and phase limits remain unchanged.

Preview3 source CI43631965837 succeeded. Its
[tag CI43632757157](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43632757157)
completed both native jobs with74tests,13consumer checks and7offline regressions
each; aggregate expect-carriers failed before restore/draft. The first failed
hosted guard and earlier Actions-token response are UNKNOWN. A later captured
metadata/whole-path replay pass is not a reconstruction of that failed response.
This bounded replacement is not proof that an unknown earlier cause was fixed.

The reader uses only the existing Actions token at fixed GitHub GET endpoints,
verified HTTPS, bounded complete bodies, a60s whole-operation deadline and no
implicit retry. One allowed joblog redirect is unauthenticated and cookie-free.
Finite diagnostics reveal stage/reason/HTTPstatus without response, URL, path,
token or SAS data. The tag-only READ_ONLY_TRANSPORT_PREFLIGHT consumes a unique
successful same-SHA source-run log and cache-read permission before SDK/native
jobs; it is not tag-native execution evidence or cached SDK/test reuse.

Use the [preview4 release page](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.4)
for availability and actual release evidence. Install only a published release
with `SHA256SUMS.txt`, `SHA256SUMS.txt.sig` and pinned-key verification. Source,
tag or CI success alone is not publication; a missing page/signature means
incomplete publication. Exact signed source/<=1MiB ZIP, own full native proofs,
actual archive/manifest bytes, six signed assets and verified downloads remain
publication requirements.

The recovery contract allocated6events/240minutes/338MiB, retaining the four
prior charged events/160minutes and224MiB reservations, plus new112MiB and2MiB
reserve. It grants no execution/spend permission or automatic seventh event.
Old releases/tags/notes/sources/cache/proofs remain immutable. No orders, live
counterparty, engine rewrite, durability/performance/production claim is added.
