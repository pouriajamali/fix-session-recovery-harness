# Preview5 independent draft metadata recovery

The runtime/source remains v0.1.0-preview.5 at1064b609564ff9df44cf08b273685e418eef2d4a.
Source CI43645342809 succeeded. Tag CI43646245026 completed actual Actions-token
READY, both native74/13/7 jobs, exact cache restores and archive/source checks.
It created five draft assets, then failed by-tag metadata lookup. The whole
tag CI remains FAILURE; no original bound DRAFT-STAGE was emitted.

GitHub documents by-tag lookup for published releases. Draft recovery uses
authenticated bounded list -> unique exact draft/tag -> numeric ID.
See [GitHub release API](https://docs.github.com/en/rest/releases/releases).
The new helper performs fixed GETs only, preserves stage checks and writes
filtered private metadata; missing/ambiguous/drift/permission/limit failures HOLD.

Independent recovery must receive all five actual files, verify hashes/sizes,
native manifests/full members/source1064/RID/SDK404/runtime15, all53 exact source
Git blobs, SUMS and the pinned key. Original tag-native proofs stay on their
original run. Original pure stage/bind validators derive a stage with a separate
INDEPENDENT_MANAGER_RECOVERY sidecar, never original CI output or a rewritten
CI-success result.

Release-tooling fixes have a separate checkout/main commit and exact successful
CI with affected tests plus real readonly Actions-token metadata lookup.
New-head CI binaries/source archives are nonpromoted. The frozen runtime tag
and five assets remain immutable; no runtime version is added for this defect.

Signing requires a new actual stage/provenance/assets authorization. Publishing
requires separate exact six-asset approval and stable downloads, known-key
signature and README/About/homepage/release readback. Install only actual
published signed assets; source or CI alone is insufficient.

Event9 adds40runner-min within9events/360minutes and unchanged450MiB cache cap.
No artifact/cache writes, newtag/draft, automatic tenth event, paid usage,
settings change or deletion is authorized.
