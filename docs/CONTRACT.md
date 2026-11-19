# Four-case candidate contract v2

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

Limits:4cases,32frames/connection,8KiB/frame,16KiB unframed accumulation,256KiB shared
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
all four bounded observations, not safety, production, performance or legal rights.

Public baseline:
[upstream gap/resend acceptance case](https://github.com/connamara/quickfixn/blob/44c111acdb253335fd3c035589795468ff60c400/AcceptanceTest/definitions/server/fix44/20_SimultaneousResendRequest.def),
[store tests](https://github.com/connamara/quickfixn/blob/44c111acdb253335fd3c035589795468ff60c400/UnitTests/FileStoreTests.cs),
[configuration](https://quickfixengine.org/n/documentation/configuration.html).
This guided News-only wrapper does not copy/execute the upstream order fixtures.

## Fourth case: fixed admin GapFill

The gapfill worker uses one owned connection and a fresh store. Logon1 is followed
by peer News3/GAPFILL3. Engine ResendRequest must cover2 while callback count is0.
Peer SequenceReset2 has123=Y,36=3,43=Y and valid122<=52; no News2 is sent.
TestRequest4/AFTER_ADMIN_GAPFILL and matching heartbeat establish progress. News5/
GAPFILL5 follows, then TestRequest6/AFTER_GAPFILL_NEWS and matching heartbeat,
Logout7 and controlled real stop. Final callbacks exactlyGAPFILL3,GAPFILL5;
nextTarget8 and nextSender agrees with contiguous validated outbound sequence.

Only the custom executable test assembly enables fixed wrong36=4. It must still
finish the same barriers/logout/clean stop, deliver onlyGAPFILL5 and return
completed semantic fail2. Timeout/incomplete1 is a failing negative test.

## Process sidecar lifetime

Each phase writes at most4096UTF8 bytes under fix-session-harness-process-v1.
Exact bindings: nonce,scenario,phase,session,port,owned PID and process-start token.
The schema carries stopRequested,deadlineExpired,exitObserved,nullableexitCode,
drainComplete,bounded observed pipe counts/overflow,cleanupAttempted,
forcedTermination,cleanStopVerified,storeClosedVerified,original reason and
evidenceWriteFailure. No environment, secret, arbitrary command or exception dump.

Strict schema1 worker receipts remain distinct. A clean-stop claim requires
STOP, real exit0, drain, validated worker bindings and parent exclusive store
handles. A cleanup kill cannot produce cleanStop/storeClosed success. Missing
exit remains null; sidecar collisions never overwrite caller files. Sidecar
persistence failure retains the original in-memory cause and makes the aggregate
incomplete/exit1. If output itself is unwritable, no durable diagnostic is claimed.

## Servicing and resources

Candidate0.1.0-preview.6 pins SDK11.0.100/runtime11.0.0/net10; QuickFIX1.14.1,
dictionary and no-trim/AOT/R2R remain fixed. RID NuGet locks and separate runtime
pack content/notice pins are sealed before qualification; locked restores follow.
No .NET11 support is inferred or retargeted here.

Manager admission of tools/project08-profile.json and project08_launch.py precedes
target execution. One canonical lane;2CPU/2GiB, Linux256tasks/swap0 and Windows
256processes with actual suspended-child Job assignment. Windows process limit is
not a total-thread hardcap. Actual membership/limits/terminal proof is required;
numeric ceilings and source code are not proof. Existing tighter scenario/frame/
pipe/store limits remain. Native cumulative900s includes setup/terminal margins.
