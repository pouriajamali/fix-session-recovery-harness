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

## Preview5 API Accept correction route

The local contract grants no CI event. Exact candidate source/tag/draft staging
must be approved first. Maximum reservation:eight events/320runner-min,450MiB
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

The authorized technical envelope is at most8 events/320runner-min/450MiB aggregate.
Each RID archive is at most48MiB and its finite proof bundle at most1MiB.
The source archive retains the existing at most1MiB cap; staging receipt/SUMS/key reserve is1MiB.
Source CI uses zero new cache bytes. The failed preview2/preview3/preview4 tags retain336MiB of cumulative reservations,
including the112MiB unrealized preview4 reservation (actual new cache writes:0).
The new preview5 tag reserves112MiB: at most eight compressed entries <=448MiB
plus2MiB reserve fit450MiB. Raw data remains <=49MiB/
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

## Historical preview3 exact-ref recovery

Preview2 run43624690595 attempt1 finished both native jobs (74passed/0failed/
0skipped,13own consumer checks,7offline regressions and six finite proof files
perRID). Aggregate failed before cache restoration or draft creation because
the strict reader rejected the observed cache metadata ref representation.
This is an unsupported representation in our reader; it does not establish a
native failure or a provider defect. No preview2 draft/signature/public release
was produced by that run. Old tag/source/cache/log/evidence bytes remain intact.

For that preview3 recovery, expectedRef must have exact type str and equal
refs/tags/v0.1.0-preview.3. A cache row ref must have exact type str and equal only
refs/tags/v0.1.0-preview.3 or refs/heads/refs/tags/v0.1.0-preview.3.
There is no normalization, prefix stripping, branch equivalence or scope bypass.
The original authenticated private metadata is retained without rewriting.
Every outside-cache key/source/run/attempt1/RID/digest, unique entry, version/
size cap, affirmative save, exact hit triplet and archive/proof check remains.

At the prior preview3 recovery, two events and80 runner-minutes were retained. Source event3
and new tag event4 each reserve40minutes; no refund/reset, manual contingency
or automatic fifth event is granted. That prior226MiB contract retained failedTag112 plus
newTag112 plus2reserve; actual failed-tag cache usage was72866260bytes. Ordinary
source CI still writes no artifacts/cache. PerRID900s/2CPU/2GiB/256tasks or
processes/Linuxswap0 and SDK404/runtime15 remain fixed. Each future source/tag/
draft/sign/public step needs its own exact gate; this contract grants no event.

## Preview4 bounded observable HTTPS

Preview3 source CI43631965837 succeeded and tag CI43632757157 completed both
native jobs (74tests/13consumer/7offline each), then failed expect-carriers before
restore/draft. The first failed hosted guard and earlier Actions-token response
remain UNKNOWN. Later captured actual bodies and the unchanged tag3 pure-path
replay pass do not establish that earlier cause.

The fixed repository GET reader uses only the existing ephemeral Actions
GH_TOKEN in memory. Verified HTTPS sends Authorization only to api.github.com.
Metadata is <=131072B, job logs <=32MiB, with strict JSON, complete bounded body,
declared Content-Length checks when present and one60s whole-operation deadline.
No CLI/GCM/PAT/proxy/SSL fallback or implicit retry exists. Only a selected joblog
may redirect once to productionresultssa[0-9]{1,2}.blob.core.windows.net via a
fresh noauth/nocookie request; no second redirect, raw API/error/SAS persistence
or URL/header/body diagnostics is allowed.

Only fixed preview4 push tags invoke READ_ONLY_TRANSPORT_PREFLIGHT in the
existing5min ci_policy job, after offline tests/policy/lint and before dependent
native jobs. Its scoped actions:read token reads a unique same-SHA successful
attempt1 main-source run for this workflow, one exact completed Native job and
its original six-file proof log, then typed repository cache usage. It permits
<=5API reads plus<=1unsigned redirect under60s. Source/PR runs skip this probe.
This consumes transport readiness, not another SDK run or tag-native evidence.

A <=1024B closed diagnostic identifies first operation/stage/reason, sourceSHA,
run/attempt and HTTPstatus-or-null only. Input/token/request/status/redirect/body/
deadline/JSON/run/jobs/outputs/handoff/frame/save/cachekey/ref/version/size/
statewrite failures HOLD without raw exceptions or responses. All original
source/run/key/ref/save/lookup/restore/archive/H1/H2/H3 guards remain.

At preview4, the technical envelope was6events/240runner-min/338MiB. Four events/160minutes and
four entries/224MiB remain charged/reserved; actual retained cache usage was
145760489B. New source5 and tag6 reserve40minutes each and the new tag112MiB.
There is no refund/reset, automatic seventh event, manual contingency, billing
or settings change. All native/SDK/perphase/sourceZIP limits remain unchanged.

## Preview5 API Accept correction

Preview4 tag43642620238 failed in the pre-native transport readiness probe:
READINESS_JOB_LOG/HTTP_STATUS415. SDK/native jobs and cache/draft/signing work
were skipped. Its API log endpoint incorrectly selected binary Accept when a
redirect was allowed. A paired read of the same endpoint/version/credential
changed only Accept: octet returned415 and GitHub JSON returned302. This names
the preview4 header defect; it does not prove a future Actions-token success
or reconstruct the unknown earlier tag2/tag3 hosted responses.

Every api.github.com GET now uses application/vnd.github+json, including job
log redirect endpoints. Only the fresh unsigned storage request uses
application/octet-stream. Authorization remains API-only; cookie, redirect,
TLS, byte, deadline, diagnostic, source/run/proof and cache guards are unchanged.
A mocked header-sensitive415 regression and generic415 fail-closed subcase
cover this change; historical fixtures and the seven release guards are unchanged.

The current technical envelope is8events/320runner-min/450MiB. Six events and
240minutes remain reserved;336MiB prior cumulative reservations include the
unused preview4 tag reservation without refund. Actual retained cache remains
four entries/145760489B. New source7 and tag8 reserve40minutes each; tag8 reserves
112MiB plus2MiB global margin. Source cache/artifact writes remain0, no automatic
ninth/manual/rerun is granted and the zero-dollar budget/settings are unchanged.
The same tag-only readiness must pass using its actual Actions token before
SDK/native work; source runs skip that token probe.
