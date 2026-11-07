# Decisions and evidence

| Boundary | Test/evidence | Limit |
| --- | --- | --- |
| Gap/duplicate/resend/restart behavior | all-three-real-loopback-scenarios-and-raw-hashes plus actual consumer demos; raw FIX, worker/PID/phase receipts | Three synthetic cases, not general exactly-once, FIX certification or crash durability |
| Do not trust child exit0 | Every missing/bad bound receipt field, duplicate/truncated/oversized/extra JSON; real owned test-child empty/invalid/flood/exit17/hang | Own processes only, not a hostile native-memory sandbox |
| Bound before parsing | Unframed cap before upstream append, huge advertised body, fragmentation/coalescing, complete-frame/count/shared-byte-budget tests | Fixed trusted local engine/scripts; OS I/O/native allocation not a hard security bound |
| No silent parser resynchronization | Leading garbage, checksum and session mismatch tests; exact raw-prefix comparison | Upstream parser/validator retained, no replacement engine |
| Only clean state can restart | Real two-process scenario, drained pipes, exclusive handle tests; persisted state read after Stop/dispose | Stop unregisters sessions; not kill/power-loss evidence |
| Caller files are preserved | Fresh marker/existing output, all controls/line separators at every path position, network/symlink refusal, report sentinel collision | No hostile filesystem race or universal remote mount detection |
| No live destination surface | No host/port/settings/dictionary/message/reset/order option; parent owns port0 listener | Not a generic trading client or configurable FIX peer |

Initial failed evidence is preserved. The first draft used ToString without
constructing BodyLength/CheckSum; strict validation rejected the peer, and the fix
uses upstream ConstructString rather than disabling checks. The next draft tried
Session.LookupSession after Stop; upstream Stop disposes/unregisters sessions.
Persisted sequence state is now read through the pinned FileStore API only after
Stop/dispose and exclusive-handle checks, and those new handles close before exit.
No failed run or forced cleanup is represented as a clean-stop success.

Package provenance is separate from this behavior: exact source, matching-OS CI,
actual already-executed runtime archives, public downloads, member/hash and SSH
checksum checks. Original wrapper MIT and upstream QuickFIX license are separate;
repository signatures are not OS signing, safety or exclusive authorship proof.
No performance measurement, customer, demand, revenue or financial claim is made.
