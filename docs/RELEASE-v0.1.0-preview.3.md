# v0.1.0-preview.3 — bounded recovery preview

This recovery preview repairs the aggregate cache-metadata ref reader and advances the
application/package/archive version to preview3. The fixed four News/admin
loopback cases, report-v2/process-v1 contracts, QuickFIX/n1.14.1, dictionary,
SDK10.0.404/runtime10.0.15 and containment limits remain unchanged.

[Preview2 tag CI](https://github.com/pouriajamali/fix-session-recovery-harness/actions/runs/43624690595)
finished Windows and Linux native jobs with74passed/0failed/0skipped,
13own package consumer checks and7offline regressions each. Aggregate then
failed before cache restore/draft: our strict reader did not accept the observed
cache API ref representation. No draft, signature or public release resulted
from that run. Those native results are scoped to the immutable preview2
source/tag; they are not preview3 execution or independent release downloads.

Preview3 requires expectedRef to be exactly refs/tags/v0.1.0-preview.3 and accepts
only that exact row ref or refs/heads/refs/tags/v0.1.0-preview.3. It preserves
external producer commitments, exact same-run keys/hits, affirmative actual
save, byte/hash/source/native-proof checks and the known-key release pipeline.
It performs no ref normalization or cache scope alteration.

Use the [preview3 release page](https://github.com/pouriajamali/fix-session-recovery-harness/releases/tag/v0.1.0-preview.3)
for availability, signed downloads and actual release evidence. Install only
from a published release containing `SHA256SUMS.txt`, `SHA256SUMS.txt.sig` and
the pinned public key. Source, a tag or CI success alone does not establish
publication. If the release page or signature is missing, publication is
incomplete; do not bypass verification.

Publication requires its own exact signed source and <=1MiB source ZIP,
complete new native proofs, actual same-run archive/manifest bytes, known-key
checksums/signature, exact six-asset approval and verified public downloads. The recovery contract allocated a4event/160minute technical envelope, including
the two prior charged events/80minutes, under the unchanged226MiB cache cap.
That allocation grants no automatic execution or spend permission.

Published preview1 and failed preview2 tags/notes/source/evidence remain
immutable. No orders, live counterparty, engine rewrite, crash durability,
general exactly-once effects or performance/security/production claim is added.
