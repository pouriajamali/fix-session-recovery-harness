# CI resource policy

This workflow policy separates documentation checks from unchanged runtime builds. It does not change application behavior, dependencies, release versions, published assets, account budgets or repository protection.

- Push validation targets the default `main` branch; pull requests retain validation without an extra feature-branch push run. Existing tag patterns are preserved. Manual dispatch always requests full native checks.
- A narrow documentation allowlist gets real UTF-8/framing, Markdown fence/relative-link and frozen-evidence JSON checks, plus policy contract tests and pinned actionlint. It does not run .NET/C++ builds or upload native artifacts. This is not an exhaustive prose/security audit.
- Runtime/configuration/fixtures/licenses/provenance/pipeline changes and unknown/failed Git comparisons always require the original native checks. Source, Windows/Linux execution, native package inspection and release/provenance commands remain present. Tags and manual runs cannot take the docs-only route.
- Lightweight checks also statically read the explicit source-package inventories where present, without importing the packager. A new unallowlisted document, symlink mode or computed/unknown inventory cannot hide behind docs-only success.
- Main, tag and manual runs have unique concurrency groups. A docs push cannot replace an earlier pending source run. Only superseded PR runs may be cancelled; classification uses the complete PR delta from its merge base.
- Matrix native jobs use `max-parallel: 1`; Book Replay keeps its two separately defined platform jobs. This is a per-workflow limit, not an account-wide cap. Rollouts are staged rather than starting fourteen heavy runs together.
- Existing native job timeouts remain. Previously unbounded native and comparison/release jobs receive finite timeouts. No source test is replaced by an artificial green check.
- Project08 source/PR jobs still build, extract and execute fresh native packages, then emit the complete finite proof through framed job logs. They perform no artifact upload or cache save. Tag/manual runs transport only the same-run native archive and finite proof through an exact committed cache key; they never cache SDK/NuGet inputs or reuse execution.
- No Actions artifact uploads remain in this workflow. Cache lifecycle stays at the platform default; no retention, cache limit, deletion, paid capacity, account security or budget setting is changed. Existing published assets remain immutable.

The lightweight job uses only the standard Ubuntu runner, Python's standard library, and actionlint 1.7.12 downloaded from its official release with an exact archive SHA256. It does not claim optional external ShellCheck/Pyflakes results. Current account storage usage is not inferred from one repository's artifact byte count.

## Preview3 recovery candidate route

The local contract grants no CI event. Exact candidate source/tag/draft staging
must be approved first. Maximum reservation:four events/160runner-min,226MiB
total new cache bytes including compressed-envelope overhead. Source CI uses log proofs only.
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

## Hosted404 producer and native proof route

The hosted source/CI amendment is a separate gate from the private local
qualification. SDK10.0.404/runtime10.0.15 are fixed; SDK11 and project04 are not
dependencies. Only the SDK404 archive/member identities accepted in project06
are reused as data pins. Every hosted job acquires its own official HTTPS
archive, verifies size/SHA256/SHA512 and each regular member before SDK execution.
No existing E tree, local admission, installer, global PATH or uncapped
setup-dotnet step is consumed.

tools/project08_hosted.py runs only for this repository's exact GitHub
run/head/tree and matching x64 OS/RID. Its pure tools/project08_kernel.py control
primitives contain no local paths, admission or ledgers. Each fresh phase proves
actual Job/cgroup caps and its own membership before SDK/app launch, and each
SDK/app child is checked by owned handle/PID before its result can be accepted.
Bootstrap qualification is subject to the same controls. Application-owned
workers inherit that non-breakaway Job/cgroup and retain their strict actual
PID/nonce/start/exit/store checks in private consumer evidence.

Windows uses suspended creation, Job assignment,2CPU affinity,2GiB and256
processes with no breakaway. Linux uses a fresh systemd transient cgroup with
User equal to the actual runner UID,2CPU quota,2GiB,swap0 and256 tasks. An
unavailable sudo/systemd/cgroup or failed actual control proof is HOLD, not an
uncapped fallback. No local UID1000 assumption or service configuration is used.

SDK data materialization and qualification precede locked RID restore, build,
custom regressions, package and extracted consumer. The whole chain has the
900s native ceiling and the same fixed per-phase limits. Native matrices remain
max-parallel1/15min; policy and draft aggregation jobs remain5min each. No
unchanged duplicate event, automatic retry or extra hosted producer job is added.

The only exported proof is project08-native-proof-v1 with identityEncoding
project08-native-proof-identity-sha256-v1, exact run/head/tree/OS/RID,SDK/runtime,
all-four-case result and five explicit fact files. PID,nonce,Job and cgroup
identities are domain-separated hashes salted by the PRIVATE phase nonce;
cross-file bindings survive without publishing raw low-entropy PIDs. Raw source bytes and SHA256 values remain private; public source commitments
are also nonce-salted so a small PID space cannot be recovered from their hashes. Raw stdout/stderr,wire/events,sidecars,ports,
worker stores and absolute runner paths remain in RUNNER_TEMP and are not uploaded.

Each matrix job emits exactly native-proof.json plus five approved finite facts
in deterministic P08F1 begin/data/end records. Original UTF-8 bytes, lengths,
SHA256, source/tree/repository/run/attempt1/job/jobName/RID and every chunk/index
are bound. Complete raw proof is <=1MiB/RID, framed records <=2MiB/RID and the
complete authenticated job log <=32MiB. Recovery rejects missing, duplicate,
unknown, reordered, truncated, corrupt, private or cross-run facts and accepts
only bounded GitHub timestamps. Source CI never saves cache or artifacts.

Only tag/manual jobs create artifacts/project08-handoff/<rid>, exactly one
<=48MiB native archive and those six proof files. The canonical finite handoff
digest, archive identity and all proof hashes go through trusted per-RID workflow
job outputs OUTSIDE the cache. That digest is part of the exact repository/
source/run/attempt1/RID key. Rewritten self-consistent cached metadata cannot
replace the expected commitment. The cache contains no separate metadata,
scripts, SDK, dependency, raw log, worker store, PID, nonce or credential file.

Save and restore use actions/cache at55cc8345863c7cc4c66a329aec7e433d2d1c52a9,
identical relative paths and enableCrossOsArchive:true. GNU tar and zstd must
actually be available; there is no install or gzip fallback. Restore requires
fail-on-cache-miss:true, literal cache-hit true, and matched==primary==expected;
restore-keys are absent. No cached file is executed.

Save has no outputs and green alone is insufficient. Before tag draft staging,
aggregation reads the exact completed producer job's authenticated bounded log,
requires its exact Cache saved with key line and post-save exact availability,
and compares the full recovered proof with the trusted job-output commitment.
A bounded current-run jobs/cache metadata read uses release-only actions:read
on the existing ephemeral GITHUB_TOKEN; no account or security setting changes.
The exact cache entry's actual compressed size must fit its reservation. Missing
save evidence, read-only/disabled cache, miss, eviction, malformed API response or
uncertain availability is HOLD. Raw API/error/SAS bodies stay private.

After exact restore, aggregation verifies every externally committed byte and
H1/H2/H3 before copying archive/proof into the unchanged release checks. It never
promotes local bb406/4abce proof to this new CI source identity.

The authorized technical envelope is at most4 events/160runner-min/226MiB aggregate.
Each RID archive is at most48MiB and its finite proof bundle at most1MiB.
The source archive retains the existing at most1MiB cap; staging receipt/SUMS/key reserve is1MiB.
Source CI uses zero new cache bytes. The failed preview2 tag and new preview3 tag each reserve two
compressed entries of at most56MiB, including their envelope overhead: four
entries <=224MiB plus2MiB envelope reserve fit226MiB. Raw data remains <=49MiB/
RID (48archive+1proof). Actual entry size is checked from authenticated metadata;
fresh repository usage and coordinated in-flight reservations remain event gates.
The configured cache limit remains UNKNOWN and operational availability is not
proven by this design. No paid override, cleanup, settings mutation or retry.

The release job verifies already-executed archives, creates exact Git source and
SUMS, stages five actual draft assets and binds their IDs/sizes/digests in
a strictly typed finite DRAFT-STAGE log frame, without the raw release API body.
Only the manager signs SUMS through the known-key agent, verifies all
six actual draft assets, obtains the exact public gate, publishes and
re-downloads them. This source proposal authorizes none of those events.

Any future CI source SHA proves its own native/distributable bytes. Old local
proofs keep their real bb406 or4abce labels and local ledgers are not migrated
or reset. Unchanged core/SDK/graph evidence may support a scoped equivalence
review, never a fabricated execution of the new commit.

The proof producer and release consumer share closed field/type/value schemas.
Unknown fields in raw or exported facts, nested kernel limits, or the proof
envelope reject. The fixed 74 observation names must each occur once, with
counts matching results; only symlink-output-refused may skip on Windows for
the named privilege limitation, and Linux permits no skip. All 13 fixed own
consumer check names must occur once with checkCount13. These checks preserve
the private raw identities and salted public cross-bindings; synthetic schema
checks alone do not establish hosted qualification.

Offline regression discovery captures all expected identifiers before execution
and requires the same complete seven-test result without failure, error or skip.
Proof records attempt1 and native OS, finite SDK archive/member/host/count and
existing capped qualification observations, and the successful fixed package
producer's archive hash/size and consumer manifest hash. Aggregation hashes the
same-commit profile, adapter, member inventory and packager Git blobs, then
compares proof identities to the received archive and manifest bytes. Private
nonce-salted commitments are labelled separately and are not publicly inspectable
SDK input or independent execution proof. No additional SDK call is made.

## Preview3 exact-ref recovery

Preview2 run43624690595 attempt1 finished both native jobs (74passed/0failed/
0skipped,13own consumer checks,7offline regressions and six finite proof files
perRID). Aggregate failed before cache restoration or draft creation because
the strict reader rejected the observed cache metadata ref representation.
This is an unsupported representation in our reader; it does not establish a
native failure or a provider defect. No preview2 draft/signature/public release
was produced by that run. Old tag/source/cache/log/evidence bytes remain intact.

For preview3, expectedRef must have exact type str and equal
refs/tags/v0.1.0-preview.3. A cache row ref must have exact type str and equal only
refs/tags/v0.1.0-preview.3 or refs/heads/refs/tags/v0.1.0-preview.3.
There is no normalization, prefix stripping, branch equivalence or scope bypass.
The original authenticated private metadata is retained without rewriting.
Every outside-cache key/source/run/attempt1/RID/digest, unique entry, version/
size cap, affirmative save, exact hit triplet and archive/proof check remains.

Two events and80 runner-minutes remain charged/reserved. New source event3
and new tag event4 each reserve40minutes; no refund/reset, manual contingency
or automatic fifth event is granted. Cache226MiB remains failedTag112 plus
newTag112 plus2reserve; actual failed-tag cache usage was72866260bytes. Ordinary
source CI still writes no artifacts/cache. PerRID900s/2CPU/2GiB/256tasks or
processes/Linuxswap0 and SDK404/runtime15 remain fixed. Each future source/tag/
draft/sign/public step needs its own exact gate; this contract grants no event.
