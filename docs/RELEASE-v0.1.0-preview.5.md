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
