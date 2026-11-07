# Three-case contract v1

Supported action: `session-harness demo <fresh-directory>`. Fixed synthetic FIX4.4
News/admin scripts, parent-owned127.0.0.1 listener, pinned QuickFIX/n1.14.1 child
initiator and public dictionary. No external configuration, message, dictionary,
endpoint or existing user store import. Source/package pins are recorded in README,
NOTICE, lockfiles and release build manifests.

1. **gap**: peer logon1, News3, observe a ResendRequest covering2, supply News2 with
   valid PossDup/OrigSendingTime. A TestRequest4/Heartbeat barrier follows. Repeat
   accepted News2, then TestRequest5/Heartbeat barrier and Logout6. Receipt must
   report no app callback at first resend request, and exactly GAP2,GAP3 in order
   after both barriers. No broad exactly-once-effects claim.
2. **resend**: engine logon1 then fixed News2/3, peer requests exact range2..3.
   Replays must preserve each body and original sequence, PossDupFlag=Y and original
   SendingTime in OrigSendingTime. Controlled logout and process stop follow.
3. **restart**: first engine process logon1/News2; peer closes socket. Normal stop,
   real process exit, bounded stdout/stderr drain and exclusive store-handle checks
   must complete before the second child starts. Same parent listener/owned fresh
   store/session nonce. Peer/engine logons continue persisted target/sender sequence;
   request stored News2, verify replay metadata/body, then logout/normal stop.
   Timeout/kill is incomplete, never a clean-restart success. No crash durability.

Typed SettingsDictionary setters fix reset-on-logon/logout/disconnect=N,
PersistMessages=Y, NonStopSession=Y, SocketIgnoreProxy=Y, literal127.0.0.1,
HeartBtInt30, ReconnectInterval60, LogonTimeout5 and LogoutTimeout2. The long automatic
reconnect interval prevents an old child opening a second connection before its
controlled stop; the second process's initial connection is the observed restart.

Upstream Parser/Message/dictionary own frame serialization and validation. Use
ConstructString to create length/checksum fields; never disable checksum/length
validation to make a case pass. Retain a bounded copy of raw unconsumed bytes and
compare each parser output against its exact prefix, detecting discarded garbage.
Enforce accumulation cap before append, even for huge/incomplete BodyLength.

Limits:3cases,32frames/connection,8KiB/frame,16KiB unframed accumulation,256KiB shared
total bytes per scenario (both directions and restart connections),10-second
network waits,30-second scenario deadline. Separate stop8seconds/drain3seconds/
failure termination3seconds handling; filesystem/native memory are not hard-timed
security bounds. Only owned process handles may be terminated. Bounded raw byte
buffers are separate from bounded frame-event lists; fragmented packets do not
produce unlimited diagnostics.

Worker receipt exact fields: schema,complete,nonce,scenario,phase,session,port,pid,
outcome,reason,cleanStop,storeClosed,nextSender,nextTarget,delivered,
gapRequestDeliveryCount. Schema1, complete=true, pass/CONTROLLED_PROCESS_STOP,
matching parent bindings and small allowlisted field values required. Duplicate,
missing/extra fields, wrong nonce/PID/phase/endpoint, oversize/incomplete/truncated
output, stderr, overflow, exit17 or exit0-empty cannot pass. No user-provided binary
or test-probe flag exists in the shipped CLI. Test-host dispatch/probes are excluded.

Raw synthetic sent/received wire, readable validated events, full bounded worker
output, per-scenario hashes, JSON and summary.txt retained. Frames in reports count
successful sends/validated receives; failed raw input remains in byte transcripts.
Clean-stop evidence counts only receipts after real exit/drain and exclusive handles.
Fresh files only, JSON summary last; disk/power/process loss may leave partial files.
Any I/O/report failure is incomplete. Only complete final JSON plus exit0 signifies
all three bounded observations, not safety, production, performance or legal rights.

Public baseline:
[upstream gap/resend acceptance case](https://github.com/connamara/quickfixn/blob/44c111acdb253335fd3c035589795468ff60c400/AcceptanceTest/definitions/server/fix44/20_SimultaneousResendRequest.def),
[store tests](https://github.com/connamara/quickfixn/blob/44c111acdb253335fd3c035589795468ff60c400/UnitTests/FileStoreTests.cs),
[configuration](https://quickfixengine.org/n/documentation/configuration.html).
This guided News-only wrapper does not copy/execute the upstream order fixtures.
