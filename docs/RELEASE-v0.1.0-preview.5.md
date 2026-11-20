# v0.1.0-preview.5 - API log Accept correction preview

This bounded correction selects application/vnd.github+json for every
api.github.com GET, including the job-log endpoint that returns a redirect.
Only unsigned storage requests use application/octet-stream. Authorization
remains API-only, with unchanged TLS, noauth/nocookie one-hop storage access,
body/deadline limits, finite diagnostics and all source/native/cache guards.

[Preview4 tag CI](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43642620238)
failed in READINESS_JOB_LOG/HTTP_STATUS415 before SDK/native/cache/draft/signing.
Its log API request selected binary Accept. A paired read of the same
endpoint/API version/root credential, changing only Accept, returned415 for
octet and302 for GitHub JSON. This identifies the preview4 header defect;
the comparison is not future Actions-token success and does not reconstruct
the unknown first hosted failures of preview2/preview3.

The strengthened mocked redirect test rejects the old header with415 and
requires API JSON/storage octet plus no forwarded credentials or cookies.
The actual tag-only READ_ONLY_TRANSPORT_PREFLIGHT still must pass before
native jobs. SDK10.0.404/runtime10.0.15, fixed four loopback scenarios,
QuickFIX/n1.14.1, dictionary, report-v2/process-v1 and containment limits
are unchanged.

Use the [preview5 release page](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.5)
for availability and actual signed assets. Install only a published release
with verified SHA256SUMS.txt, SHA256SUMS.txt.sig and the pinned key. Source,
tag, mocks or CI alone do not establish publication; missing assets/signature
mean incomplete delivery.

The technical envelope is8events/320minutes/450MiB, retaining all prior
six events/240minutes/336MiB reservations without refund. It grants no automatic
ninth event, paid usage or settings change. Old tags/releases/assets/evidence
remain immutable. No live trading, counterparty, durability, performance or
production claim is added.

## Archived qualification and release operations

The following historical details were moved from the README. Their original
source, run outcomes and uncertainty boundaries are retained.

## Legacy preview5 hosted evidence

Hosted proof acceptance for frozen preview5 requires the complete fixed 74 test observations and
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
execution result is reused from cache. The prepared profile does not establish a configured cache limit;
availability and the <=450MiB envelope remain actual-event gates.

Preview5 recovery details are described in the
[preview5 release notes](RELEASE-v0.1.0-preview.5.md).
[Preview2 tag CI](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43624690595)
completed both native jobs, then failed in aggregate expect-carriers before
restore or draft creation. Separately, the preview2 reader did not admit the observed
`refs/heads/refs/tags/v0.1.0-preview.2` representation. Preview5 admits only its
two fixed expected-ref representations and requires its own source/tag evidence.
The preview2 tag, source and evidence stay immutable. Use the
[preview5 release page](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.5)
for availability and actual release evidence. Publication must be established
by its published, verified signed assets; source/tag/CI alone is insufficient.

[Preview3 tag CI](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43632757157)
completed both native jobs, but aggregate expect-carriers failed before restore
or draft creation. Its first failed guard and earlier Actions-token HTTP/CLI
response are UNKNOWN. Later captured metadata and an offline replay pass do not
reconstruct that failure. Preview4 replaces the opaque reader with bounded
typed HTTPS and finite first-stage diagnostics; this is not proof that the
unknown earlier cause has been fixed. Its tag-only READ_ONLY_TRANSPORT_PREFLIGHT
checks same-SHA source-run log and cache-read access before SDK/native work.

[Preview4 tag CI](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43642620238)
stopped in READ_ONLY_TRANSPORT_PREFLIGHT at READINESS_JOB_LOG/HTTP_STATUS415,
before SDK/native/cache/draft/signing work. Its API log request used
Accept: application/octet-stream. A paired read using the same endpoint,
API version and root credential, varying only Accept, returned415 for octet
and302 for application/vnd.github+json. Preview5 uses JSON Accept for every
api.github.com GET, including log redirect requests; only unsigned storage
requests use octet-stream. That root-credential comparison is not future
Actions-token success, and does not determine the older tag2/tag3 failures.
Preview5 still requires its own actual Actions-token READY and native/draft/
signature/download evidence; source or mock tests alone do not establish delivery.

## Release tooling and independent draft recovery

The frozen preview5 runtime/source tag points to commit
[1064b609](https://github.com/pouriajamali/fix-session-recovery-harness/commit/1064b609564ff9df44cf08b273685e418eef2d4a).
Later release-tooling commits on main do not replace that runtime or its assets.
Its [source CI43645342809](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43645342809)
succeeded. [Tag CI43646245026](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43646245026)
passed real Actions-token readiness, both native jobs and archive/source checks,
then failed after creating the five-asset draft: the by-tag endpoint returned404
for the unpublished draft. The whole tag run remains FAILURE.

Corrected tooling uses authenticated bounded list -> unique exact draft/tag ->
numeric ID. An independently derived stage uses actual five-file downloads,
original native proofs, all53 source Git blobs and separate provenance; it is
never original CI DRAFT-STAGE or a retrospective tag-CI success claim.
[Recovery method and limits](PREVIEW5-DRAFT-METADATA-RECOVERY.md) describe
the separate exact tooling CI and signing/publication gates. New-head CI builds
validate tooling changes and are not promoted as preview5 runtime assets.
