"""Closed finite hosted proof schemas. Private raw evidence never leaves the runner."""
import hashlib,json,math,re,shutil,tarfile,zipfile
from pathlib import Path

TEST_NAMES=(
 'dictionary-canonical-pin',
 'valid-complete-bound-worker-receipt',
 'receipt-missing-schema','receipt-missing-complete','receipt-missing-nonce',
 'receipt-missing-scenario','receipt-missing-phase','receipt-missing-session',
 'receipt-missing-port','receipt-missing-pid','receipt-missing-outcome',
 'receipt-missing-reason','receipt-missing-cleanStop','receipt-missing-storeClosed',
 'receipt-missing-nextSender','receipt-missing-nextTarget','receipt-missing-delivered',
 'receipt-missing-gapRequestDeliveryCount',
 'receipt-invalid-schema','receipt-invalid-complete','receipt-invalid-nonce',
 'receipt-invalid-scenario','receipt-invalid-phase','receipt-invalid-session',
 'receipt-invalid-port','receipt-invalid-pid','receipt-invalid-outcome',
 'receipt-invalid-reason','receipt-invalid-cleanStop','receipt-invalid-storeClosed',
 'receipt-invalid-nextSender','receipt-invalid-nextTarget','receipt-invalid-delivered',
 'receipt-invalid-gapRequestDeliveryCount','receipt-invalid-extra',
 'receipt-empty','receipt-truncated','receipt-extra-object','receipt-duplicate','receipt-oversized',
 'fragmented-frame-uses-upstream-parser','coalesced-two-frames','unframed-cap-before-parser-append',
 'incomplete-advertised-huge-body-remains-bounded','leading-garbage-cannot-silently-pass',
 'wrong-session-rejected','invalid-checksum-cannot-pass','completed-frame-byte-cap','frame-count-cap',
 'scenario-byte-budget-shared-by-connections','fresh-output-and-marker-preserved',
 'all-controls-and-line-separators-in-every-path-position','network-paths-refused',
 'store-exclusivity-required','missing-store-not-recovered-or-invented',
 'real-owned-child-empty-never-clean-pass','real-owned-child-invalid-never-clean-pass',
 'real-owned-child-stdout-never-clean-pass','real-owned-child-stderr-never-clean-pass',
 'real-owned-child-exit-never-clean-pass','real-owned-child-hang-never-clean-pass',
 'strict-process-diagnostic-bindings-and-nullable-exit',
 'process-sidecar-collision-preserves-original-cause','all-four-real-loopback-scenarios-and-raw-hashes',
 'gapfill-wrong-newseqno-is-completed-fail2','report-collision-overrides-pass',
 'no-import-or-destination-option---host','no-import-or-destination-option---port',
 'no-import-or-destination-option---settings','no-import-or-destination-option---dictionary',
 'no-import-or-destination-option---message','no-import-or-destination-option---reset',
 'no-import-or-destination-option---order','symlink-output-refused')
CONSUMER_CHECKS=(
 'package-manifest-dictionary-licenses-and-document-links','version','demo',
 'actual-scenario-gap','actual-scenario-resend','actual-scenario-restart','actual-scenario-gapfill',
 'refuse-existing','refuse-host','refuse-settings','refuse-dictionary','refuse-order',
 'worker-without-authority')
FACTS=('tests','consumer','kernel','subprocessMembership','terminal')
OFFLINE_TEST_IDS=(
 'release_candidate_test.PublicationGateTests.test_asset_size_and_identity_must_match',
 'release_candidate_test.PublicationGateTests.test_duplicate_json_fields_fail',
 'release_candidate_test.PublicationGateTests.test_mismatched_gate_never_publishes',
 'release_candidate_test.PublicationGateTests.test_missing_native_proof_fails',
 'release_candidate_test.PublicationGateTests.test_path_traversal_is_not_an_asset_name',
 'release_candidate_test.PublicationGateTests.test_public_release_cannot_enter_signing',
 'release_candidate_test.PublicationGateTests.test_signature_or_extra_asset_collision_is_not_clobbered')
TEST_SCOPE='Synthetic fixed News/admin loopback only; no production/crash/exactly-once/performance guarantee'
CONSUMER_SCOPE='Only fixed synthetic News/admin loopback. Existing hosts, not cleanOS or production/crash/exactlyonce/performance proof.'
LIMITS='Only fixed synthetic News/admin; fresh hosted run. Not old local proof, cleanOS/production/crash/performance proof.'
SKIP_REASON='Local Windows symbolic-link privilege unavailable'
CONSUMER_STATUS='ACTUAL_SELF_CONTAINED_FIXED_FIX_HARNESS_PACKAGE_PASS'

def closed(value,keys):
 assert type(value) is dict and set(value)==set(keys),'Closed proof schema'
def integer(value,low,high):
 assert type(value) is int and low<=value<=high,'Integer proof field'
def text(value,pattern):
 assert type(value) is str and re.fullmatch(pattern,value),'Text proof field'
def sha(value):text(value,'[0-9a-f]{64}')
def identity(value):text(value,'sha256:[0-9a-f]{64}')
def pairs(values):
 output={}
 for key,value in values:
  assert key not in output,'Duplicate receipt field'
  output[key]=value
 return output
def reject_constant(value):raise AssertionError('Nonfinite JSON')
def finite_float(value):
 result=float(value);assert math.isfinite(result),'Nonfinite JSON'
 return result
def loads(data):return json.loads(data,object_pairs_hook=pairs,parse_constant=reject_constant,parse_float=finite_float)
def read(path):
 assert path.is_file() and not path.is_symlink() and path.stat().st_size<=131072
 return loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_tests(tests,rid,public):
 closed(tests,('passed','failed','skipped','observations') if public else
        ('passed','failed','skipped','observations','scope'))
 if not public:assert tests['scope']==TEST_SCOPE
 assert len(TEST_NAMES)==len(set(TEST_NAMES))==74
 for key in ('passed','failed','skipped'):integer(tests[key],0,74)
 rows=tests['observations'];assert type(rows) is list and len(rows)==74
 names=[];counts={'pass':0,'fail':0,'skip':0}
 for row in rows:
  assert type(row) is dict
  result=row.get('result')
  assert type(result) is str and result in ('pass','skip'),'Only successful fixed suite'
  closed(row,('name','result','reason') if result=='skip' and not public else ('name','result'))
  assert type(row['name']) is str and row['name'] in TEST_NAMES
  names.append(row['name']);counts[result]+=1
  if result=='skip':
   assert rid=='win-x64' and row['name']=='symlink-output-refused'
   if not public:assert row['reason']==SKIP_REASON
 assert len(set(names))==74 and set(names)==set(TEST_NAMES),'Complete literal suite'
 assert tests['passed']==counts['pass'] and tests['failed']==counts['fail']==0
 assert tests['skipped']==counts['skip'] and tests['passed']+tests['skipped']==74
 assert tests['skipped'] in ((0,1) if rid=='win-x64' else (0,))

def validate_facts(facts,rid,commit,public):
 assert rid in ('win-x64','linux-x64');text(commit,'[0-9a-f]{40}')
 closed(facts,FACTS)
 tests,consumer,kernel,member,terminal=(facts[k] for k in FACTS)
 validate_tests(tests,rid,public)
 closed(consumer,('status','commit','rid','consumerPid','checkCount','checks','manifestSha256') if public else
        ('status','commit','rid','consumerPid','checkCount','checks','manifestSha256','scope'))
 assert consumer['status']==CONSUMER_STATUS and consumer['commit']==commit and consumer['rid']==rid
 if not public:assert consumer['scope']==CONSUMER_SCOPE
 integer(consumer['checkCount'],13,13)
 assert type(consumer['checks']) is list and len(consumer['checks'])==13
 assert all(type(x) is str for x in consumer['checks'])
 assert len(set(consumer['checks']))==13 and set(consumer['checks'])==set(CONSUMER_CHECKS)
 sha(consumer['manifestSha256'])
 scope='job' if rid=='win-x64' else 'membership'
 closed(member,('project','nonce','pid','member','mechanism',scope) if public else
        ('project','nonce','pid','startIdentity','member','mechanism',scope))
 closed(terminal,('project','nonce','exitCode','terminal') if public else
        ('project','nonce','phase','commit','exitCode','terminal'))
 assert member['project']==terminal['project']=='08' and member['member'] is True
 assert terminal['terminal'] is True;integer(terminal['exitCode'],0,0)
 assert member['nonce']==terminal['nonce'] and member['pid']==consumer['consumerPid']
 if public:
  identity(member['nonce']);identity(member['pid']);identity(member[scope])
 else:
  text(member['nonce'],'[0-9a-f]{32}');integer(member['pid'],1,4294967295)
  text(member['startIdentity'],'[1-9][0-9]{0,19}')
  assert terminal['phase']=='consumer' and terminal['commit']==commit
 validate_kernel(kernel,member,rid,public)

def validate_kernel(kernel,member,rid,public):
 if rid=='win-x64':
  closed(kernel,('mechanism','job','memoryBytes','processLimit','cpuAffinity','threadLimitClaim'))
  assert kernel['mechanism']==member['mechanism']=='windows-job' and kernel['job']==member['job']
  integer(kernel['memoryBytes'],2147483648,2147483648);integer(kernel['processLimit'],256,256)
  integer(kernel['cpuAffinity'],1,18446744073709551615)
  assert kernel['cpuAffinity'].bit_count()==2 and kernel['threadLimitClaim'] is False
  if not public:assert kernel['job']=='Local\\project08-'+member['nonce']
 else:
  closed(kernel,('mechanism','membership','limits') if public else ('mechanism','group','membership','limits'))
  assert kernel['mechanism']==member['mechanism']=='cgroup-v2' and kernel['membership']==member['membership']
  if not public:
   text(kernel['membership'],r'/(?:[A-Za-z0-9_.:@-]+/)*project08-'+member['nonce']+r'\.service')
   assert kernel['group']=='/sys/fs/cgroup'+kernel['membership']
  values=kernel['limits'];closed(values,('cpu.max','memory.max','memory.swap.max','pids.max'))
  text(values['cpu.max'],r'[1-9][0-9]{0,11} [1-9][0-9]{0,11}')
  quota,period=map(int,values['cpu.max'].split());assert quota<=2*period
  for key,maximum in (('memory.max',2147483648),('pids.max',256)):
   text(values[key],r'[1-9][0-9]{0,11}');assert int(values[key])<=maximum
  assert type(values['memory.swap.max']) is str and values['memory.swap.max']=='0'

def validate_envelope(proof,commit,tree,run_id,rid,source,received):
 closed(proof,('schema','identityEncoding','commit','sourceTree','workflowRunId','rid','sdk','runtime',
  'outcome','fourCases','offlineReleaseGuards','kernelAdmitted','terminal','files',
  'sourceEvidenceCommitmentEncoding','sourceEvidenceHashes','privateSdkInputCommitmentSha256',
  'profileSha256','adapterSha256','limits','os','workflowRunAttempt','sdkInput','qualification','producer','offlineTests'))
 assert proof['schema']=='project08-native-proof-v1'
 assert proof['identityEncoding']=='project08-native-proof-identity-sha256-v1'
 assert proof['sourceEvidenceCommitmentEncoding']=='sha256-private-phase-nonce-v1'
 text(tree,'[0-9a-f]{40}');text(str(run_id),'[1-9][0-9]{0,19}')
 assert proof['commit']==commit and proof['sourceTree']==tree and proof['rid']==rid
 integer(proof['workflowRunId'],1,99999999999999999999);assert str(proof['workflowRunId'])==str(run_id)
 assert proof['sdk']=='10.0.404' and proof['runtime']=='10.0.15' and proof['outcome']=='pass'
 assert all(proof[k] is True for k in ('fourCases','offlineReleaseGuards','kernelAdmitted','terminal'))
 assert proof['limits']==LIMITS
 closed(proof['files'],FACTS);closed(proof['sourceEvidenceHashes'],FACTS)
 for key in FACTS:
  item=proof['files'][key];closed(item,('path','sha256'))
  assert item['path']==key+'.json';sha(item['sha256']);sha(proof['sourceEvidenceHashes'][key])
 for key in ('privateSdkInputCommitmentSha256','profileSha256','adapterSha256'):sha(proof[key])
 assert proof['profileSha256']==source['profileSha256'] and proof['adapterSha256']==source['adapterSha256']
 assert proof['os']==('Windows' if rid=='win-x64' else 'Linux');integer(proof['workflowRunAttempt'],1,1)
 validate_sdk_input(proof['sdkInput'],source,rid)
 closed(proof['qualification'],('sdk','runtime','versionExitCode','runtimeExitCode','terminal','kernelAdmitted','invocations'))
 q=proof['qualification'];assert q['sdk']=='10.0.404' and q['runtime']=='10.0.15'
 integer(q['versionExitCode'],0,0);integer(q['runtimeExitCode'],0,0);integer(q['invocations'],2,2)
 assert q['terminal'] is True and q['kernelAdmitted'] is True
 validate_offline(proof['offlineTests'])
 producer=proof['producer']
 closed(producer,('phase','commit','sourceTree','rid','terminal','exitCode','archive','archiveSha256','archiveBytes','manifestSha256','packageHelperSha256','payloadFiles'))
 assert producer['phase']=='package' and producer['commit']==commit and producer['sourceTree']==tree and producer['rid']==rid
 assert producer['terminal'] is True;integer(producer['exitCode'],0,0)
 assert producer['packageHelperSha256']==source['packageHelperSha256']
 for key in ('archiveSha256','manifestSha256','packageHelperSha256'):sha(producer[key])
 integer(producer['archiveBytes'],1,48*1024*1024);integer(producer['payloadFiles'],1,511)
 assert producer['archive']==archive_name(rid)
 for key in ('archiveSha256','archiveBytes','manifestSha256','payloadFiles'):assert producer[key]==received[key]
 assert received['commit']==commit and received['sourceTree']==tree and received['rid']==rid

def validate_bundle(directory,commit,tree,run_id,rid,source,received):
 assert directory.is_dir() and not directory.is_symlink()
 assert {p.name for p in directory.iterdir()}=={'native-proof.json',*(key+'.json' for key in FACTS)}
 assert sum(p.stat().st_size for p in directory.iterdir())<=1024*1024
 proof=read(directory/'native-proof.json')
 validate_envelope(proof,commit,tree,run_id,rid,source,received)
 facts={}
 for key in FACTS:
  path=directory/(key+'.json');assert digest(path)==proof['files'][key]['sha256']
  facts[key]=read(path)
 validate_facts(facts,rid,commit,True)
 assert facts['consumer']['manifestSha256']==received['manifestSha256']==proof['producer']['manifestSha256']
 return proof

def validate_offline(value):
 closed(value,('success','testsRun','expectedCount','expectedTestIds','completedTestIds','failed','errors','skipped'))
 assert value['success'] is True
 integer(value['testsRun'],7,7);integer(value['expectedCount'],7,7)
 for key in ('failed','errors','skipped'):integer(value[key],0,0)
 for key in ('expectedTestIds','completedTestIds'):
  rows=value[key];assert type(rows) is list and len(rows)==7 and all(type(x) is str for x in rows)
  assert len(set(rows))==7 and set(rows)==set(OFFLINE_TEST_IDS)

def source_data(profile_bytes,adapter_bytes,member_bytes,package_bytes):
 profile=loads(profile_bytes.decode('utf-8'))
 assert profile['sdk']=='10.0.404' and profile['runtime']=='10.0.15'
 assert profile['memberManifest']=='tools/project08-sdk404-members.jsonl'
 assert profile['memberManifestSha256']==hashlib.sha256(member_bytes).hexdigest()=='1c34bc1465bfa261878db2d9b10d1a2f0a18ad0ea95f3b6acedb92e23eda52c1'
 assert profile['accepted06InventorySha256']=='dbac0e467b75f6b6ac5a5a2d8eba5561cd97dda287a9044f2555fc43ebe3187d'
 assert profile['artifactBudget']['maxSourceArchiveMiB']==1
 return {'profile':profile,'profileSha256':hashlib.sha256(profile_bytes).hexdigest(),
  'adapterSha256':hashlib.sha256(adapter_bytes).hexdigest(),'packageHelperSha256':hashlib.sha256(package_bytes).hexdigest()}
def source_at_root(root):
 return source_data(*((root/path).read_bytes() for path in
  ('tools/project08-hosted-profile.json','tools/project08_hosted.py','tools/project08-sdk404-members.jsonl','tools/package.py')))

def validate_context(ctx,root,source):
 closed(ctx,('schema','project','rid','commit','tree','runId','runAttempt','os','profileSha256','adapterSha256','root'))
 assert ctx['schema']=='project08-hosted-context-v1' and ctx['project']=='08'
 assert ctx['rid'] in ('win-x64','linux-x64') and ctx['os']==('Windows' if ctx['rid']=='win-x64' else 'Linux')
 text(ctx['commit'],'[0-9a-f]{40}');text(ctx['tree'],'[0-9a-f]{40}');text(ctx['runId'],'[1-9][0-9]{0,19}')
 assert type(ctx['runAttempt']) is str and ctx['runAttempt']=='1'
 assert type(ctx['root']) is str and ctx['root']==str(root)
 assert ctx['profileSha256']==source['profileSha256'] and ctx['adapterSha256']==source['adapterSha256']

def context_record(value,ctx,schema,extras):
 closed(value,set(ctx)|set(extras))
 for key,expected in ctx.items():
  assert value[key]==(schema if key=='schema' else expected)
def phase_terminal(state,phase,ctx):
 context=read(state/phase/'phase-context.json');closed(context,('context','nonce','deadlineMonotonic'))
 assert context['context']==ctx;text(context['nonce'],'[0-9a-f]{32}')
 deadline=context['deadlineMonotonic']
 assert type(deadline) in (float,int) and math.isfinite(deadline) and deadline>0
 terminal=read(state/phase/'terminal.json');closed(terminal,('project','nonce','phase','commit','exitCode','terminal'))
 assert terminal['project']=='08' and terminal['nonce']==context['nonce'] and terminal['phase']==phase and terminal['commit']==ctx['commit']
 integer(terminal['exitCode'],0,0);assert terminal['terminal'] is True
 return terminal

def admitted_phase(state,phase,ctx):
 terminal=phase_terminal(state,phase,ctx)
 member=read(state/phase/'self-membership.json')
 scope='job' if ctx['rid']=='win-x64' else 'membership'
 closed(member,('project','nonce','pid','startIdentity','member','mechanism',scope))
 assert member['project']=='08' and member['member'] is True and member['nonce']==terminal['nonce']
 integer(member['pid'],1,4294967295);text(member['startIdentity'],'[1-9][0-9]{0,19}')
 validate_kernel(read(state/phase/'kernel.json'),member,ctx['rid'],False)
 return terminal

def validate_sdk_input(value,source,rid):
 closed(value,('archive','archiveBytes','archiveSha256','archiveSha512','memberManifestSha256',
  'regularFiles','expandedBytes','hostSha256','sdkOrAppExecuted','terminal','kernelAdmitted'))
 pin=source['profile']['inputs'][rid]
 assert value['archive']==pin['archive']
 for key,source_key in (('archiveBytes','bytes'),('regularFiles','regularFiles'),('expandedBytes','expandedBytes')):
  integer(value[key],1,1024*1024*1024);assert value[key]==pin[source_key]
 for key,source_key in (('archiveSha256','sha256'),('archiveSha512','sha512'),('hostSha256','hostSha256')):
  text(value[key],'[0-9a-f]{128}' if key=='archiveSha512' else '[0-9a-f]{64}')
  assert value[key]==pin[source_key]
 assert value['memberManifestSha256']==source['profile']['memberManifestSha256']
 assert value['sdkOrAppExecuted'] is False and value['terminal'] is True and value['kernelAdmitted'] is True

def observed_sdk(state,ctx,source):
 raw=read(state/'sdk-input.json')
 keys=('sdk','runtime','archive','archiveBytes','archiveSha256','archiveSha512','memberManifestSha256',
  'files','expandedBytes','hostSha256','sdkOrAppExecuted')
 context_record(raw,ctx,'project08-hosted-sdk-input-v1',keys)
 assert raw['sdk']=='10.0.404' and raw['runtime']=='10.0.15'
 admitted_phase(state,'materialize',ctx)
 value={key:raw[key] for key in ('archive','archiveBytes','archiveSha256','archiveSha512','memberManifestSha256','expandedBytes','hostSha256','sdkOrAppExecuted')}
 value.update(regularFiles=raw['files'],terminal=True,kernelAdmitted=True)
 validate_sdk_input(value,source,ctx['rid'])
 terminal=admitted_phase(state,'qualify',ctx)
 for index,operation in enumerate(('--version','--list-runtimes')):
  item=read(state/'qualify'/(str(index)+'-invocation.json'))
  keys=('nonce','index','pid','commandKind','operation','kernelBeforeInvocation','membership','exitCode','exitObserved','stdoutSha256','stderrSha256','deadlineExpired')
  context_record(item,ctx,'project08-hosted-invocation-v1',keys)
  assert item['nonce']==terminal['nonce'] and item['commandKind']=='sdk' and item['operation']==operation
  integer(item['index'],index,index);integer(item['pid'],1,4294967295);integer(item['exitCode'],0,0)
  assert item['exitObserved'] is True and item['deadlineExpired'] is False
  member=item['membership'];scope='job' if ctx['rid']=='win-x64' else 'membership'
  extras=('observedThreadCount','threadObservation') if ctx['rid']=='win-x64' else ()
  closed(member,('schema','project','nonce','pid','mechanism','member',scope,*extras))
  assert member['schema']=='project08-child-membership-v1' and member['project']=='08'
  assert member['nonce']==terminal['nonce'] and member['pid']==item['pid'] and member['member'] is True
  if extras:
   assert member['observedThreadCount'] is None and member['threadObservation']=='UNKNOWN; active-process cap is not a thread cap'
  validate_kernel(item['kernelBeforeInvocation'],member,ctx['rid'],False)
  for stream in ('stdout','stderr'):
   path=state/'qualify'/(str(index)+'-'+stream+'.bin')
   assert path.is_file() and not path.is_symlink() and path.stat().st_size<=131072
   sha(item[stream+'Sha256']);assert digest(path)==item[stream+'Sha256']
  assert (state/'qualify'/(str(index)+'-stderr.bin')).read_bytes()==b''
  output=(state/'qualify'/(str(index)+'-stdout.bin')).read_bytes().decode('utf-8')
  if index==0:assert output.strip()=='10.0.404'
  else:assert any(line.startswith('Microsoft.NETCore.App 10.0.15 ') for line in output.splitlines())
 return value,{'sdk':'10.0.404','runtime':'10.0.15','versionExitCode':0,'runtimeExitCode':0,'terminal':True,'kernelAdmitted':True,'invocations':2}

def archive_name(rid):
 return 'fix-session-recovery-harness-v0.1.0-preview.3-'+rid+('.zip' if rid=='win-x64' else '.tar.gz')
def archive_identity(path,rid):
 assert rid in ('win-x64','linux-x64')
 assert path.name==archive_name(rid) and path.is_file() and not path.is_symlink()
 integer(path.stat().st_size,1,48*1024*1024)
 prefix='fix-session-recovery-harness-v0.1.0-preview.3-'+rid+'/'
 seen=set();folded=set();expanded=0;manifest_bytes=None
 def accept(name,size,regular,read_manifest):
  nonlocal expanded,manifest_bytes
  assert type(name) is str and name.startswith(prefix) and regular
  relative=name[len(prefix):]
  assert relative and not relative.startswith('/') and '\\' not in relative and ':' not in relative
  assert all(part not in ('','..','.') for part in relative.split('/')) and not any(ord(c)<32 for c in name)
  assert name not in seen and name.casefold() not in folded and len(seen)<512
  integer(size,0,64*1024*1024);expanded+=size;assert expanded<=256*1024*1024
  seen.add(name);folded.add(name.casefold())
  if relative=='BUILD-MANIFEST.json':
   assert size<=131072;manifest_bytes=read_manifest()
 if rid=='win-x64':
  with zipfile.ZipFile(path) as bundle:
   for item in bundle.infolist():
    accept(item.filename,item.file_size,not item.is_dir() and (item.external_attr>>16)&0o170000 in (0,0o100000),lambda i=item:bundle.read(i))
 else:
  with tarfile.open(path,'r:gz') as bundle:
   for item in bundle:
    accept(item.name,item.size,item.isfile(),lambda i=item:bundle.extractfile(i).read())
 assert manifest_bytes is not None
 manifest=loads(manifest_bytes.decode('utf-8'))
 integer(manifest['schema'],1,1)
 assert manifest['rid']==rid and manifest['version']=='0.1.0-preview.3'
 assert manifest['selfContained'] is True and manifest['localCandidate'] is False
 assert manifest['sdkVersion']=='10.0.404' and manifest['runtimeVersion']=='10.0.15'
 assert manifest['originalLicense']=='present' and manifest['buildHost']['os']==('Windows' if rid=='win-x64' else 'Linux')
 text(manifest['sourceCommit'],'[0-9a-f]{40}');text(manifest['sourceTree'],'[0-9a-f]{40}')
 assert type(manifest['files']) is list and len(manifest['files'])==len(seen)-1
 return {'archiveSha256':digest(path),'archiveBytes':path.stat().st_size,'manifestSha256':hashlib.sha256(manifest_bytes).hexdigest(),
  'payloadFiles':len(manifest['files']),'commit':manifest['sourceCommit'],'sourceTree':manifest['sourceTree'],'rid':rid}

def observed_producer(state,root,ctx,source,consumer):
 admitted_phase(state,'package',ctx)
 value=read(state/'package/build/archive.json')
 closed(value,('sourceTree','packageHelperSha256','archive','bytes','sha256','commit','rid','payloadFiles','localCandidate'))
 path=state/'package/delivery'/archive_name(ctx['rid'])
 assert value['archive']==str(path.resolve()) and value['sourceTree']==ctx['tree'] and value['commit']==ctx['commit'] and value['rid']==ctx['rid']
 assert value['localCandidate'] is False and value['packageHelperSha256']==source['packageHelperSha256']
 received=archive_identity(path,ctx['rid'])
 assert value['sha256']==received['archiveSha256'] and value['bytes']==received['archiveBytes'] and value['payloadFiles']==received['payloadFiles']
 integer(value['bytes'],1,48*1024*1024);integer(value['payloadFiles'],1,511)
 assert received['commit']==ctx['commit'] and received['sourceTree']==ctx['tree'] and received['rid']==ctx['rid']
 assert consumer['manifestSha256']==received['manifestSha256']
 extracted=state/'consumer/extracted'/('fix-session-recovery-harness-v0.1.0-preview.3-'+ctx['rid'])/'BUILD-MANIFEST.json'
 assert digest(extracted)==received['manifestSha256']
 return {'phase':'package','commit':ctx['commit'],'sourceTree':ctx['tree'],'rid':ctx['rid'],'terminal':True,'exitCode':0,
  'archive':path.name,**{key:received[key] for key in ('archiveSha256','archiveBytes','manifestSha256','payloadFiles')},
  'packageHelperSha256':source['packageHelperSha256']},received

def emit(state,root,profile,ctx):
 source=source_at_root(root);validate_context(ctx,root,source)
 paths={'tests':state/'tests/tests/receipt.json','consumer':state/'consumer/consumer/receipt.json',
  'kernel':state/'consumer/kernel.json','subprocessMembership':state/'consumer/self-membership.json',
  'terminal':state/'consumer/terminal.json'}
 raw={key:read(path) for key,path in paths.items()}
 offline=read(state/'tests/offline-release-tests.json');validate_offline(offline)
 validate_facts(raw,ctx['rid'],ctx['commit'],False)
 tests,consumer,kernel,member,terminal=(raw[k] for k in FACTS)
 admitted_phase(state,'tests',ctx)
 actual_terminal=phase_terminal(state,'consumer',ctx);assert terminal==actual_terminal
 sdk_input,qualification=observed_sdk(state,ctx,source)
 producer,received=observed_producer(state,root,ctx,source,consumer)
 def token(kind,value):
  return 'sha256:'+hashlib.sha256((ctx['commit']+'|'+ctx['runId']+'|'+ctx['rid']+'|'+member['nonce']+'|'+kind+'|'+str(value)).encode()).hexdigest()
 pid=token('pid',member['pid']);nonce=token('nonce',member['nonce'])
 exported={
  'tests':{'passed':tests['passed'],'failed':tests['failed'],'skipped':tests['skipped'],
   'observations':[{'name':x['name'],'result':x['result']} for x in tests['observations']]},
  'consumer':{key:consumer[key] for key in ('status','commit','rid','checkCount','checks','manifestSha256')},
  'subprocessMembership':{'project':'08','nonce':nonce,'pid':pid,'member':True,'mechanism':member['mechanism']},
  'terminal':{'project':'08','nonce':nonce,'exitCode':0,'terminal':True}}
 exported['consumer']['consumerPid']=pid
 if ctx['rid']=='win-x64':
  scope=token('job',kernel['job'])
  exported['kernel']={'mechanism':'windows-job','job':scope,'memoryBytes':kernel['memoryBytes'],
   'processLimit':kernel['processLimit'],'cpuAffinity':kernel['cpuAffinity'],'threadLimitClaim':False}
  exported['subprocessMembership']['job']=scope
 else:
  scope=token('cgroup',kernel['membership'])
  exported['kernel']={'mechanism':'cgroup-v2','membership':scope,
   'limits':{key:kernel['limits'][key] for key in ('cpu.max','memory.max','memory.swap.max','pids.max')}}
  exported['subprocessMembership']['membership']=scope
 validate_facts(exported,ctx['rid'],ctx['commit'],True)
 encoded={key:(json.dumps(value,indent=2)+'\n').encode('utf-8') for key,value in exported.items()}
 assert all(len(value)<=131072 for value in encoded.values())
 files={key:{'path':key+'.json','sha256':hashlib.sha256(value).hexdigest()} for key,value in encoded.items()}
 proof={'schema':'project08-native-proof-v1','identityEncoding':'project08-native-proof-identity-sha256-v1',
  'commit':ctx['commit'],'sourceTree':ctx['tree'],'workflowRunId':int(ctx['runId']),'workflowRunAttempt':1,'rid':ctx['rid'],'os':ctx['os'],
  'sdk':'10.0.404','runtime':'10.0.15','outcome':'pass','fourCases':True,'offlineReleaseGuards':True,'kernelAdmitted':True,'terminal':True,
  'files':files,'sourceEvidenceCommitmentEncoding':'sha256-private-phase-nonce-v1',
  'sourceEvidenceHashes':{key:hashlib.sha256(member['nonce'].encode()+b'\\0'+path.read_bytes()).hexdigest() for key,path in paths.items()},
  'privateSdkInputCommitmentSha256':hashlib.sha256(member['nonce'].encode()+b'\\0'+(state/'sdk-input.json').read_bytes()).hexdigest(),
  'sdkInput':sdk_input,'qualification':qualification,'producer':producer,'offlineTests':offline,'profileSha256':ctx['profileSha256'],
  'adapterSha256':ctx['adapterSha256'],'limits':LIMITS}
 validate_envelope(proof,ctx['commit'],ctx['tree'],ctx['runId'],ctx['rid'],source,received)
 proof_bytes=(json.dumps(proof,indent=2)+'\n').encode('utf-8')
 assert len(proof_bytes)<=131072 and len(proof_bytes)+sum(map(len,encoded.values()))<=1024*1024
 archive=state/'package/delivery'/archive_name(ctx['rid'])
 assert list((state/'package/delivery').iterdir())==[archive]
 destination=root/'artifacts/native-proofs'/ctx['rid'];assert not destination.exists()
 delivery=root/'artifacts/delivery';assert not (delivery/archive.name).exists()
 destination.mkdir(parents=True,exist_ok=False)
 for key,value in encoded.items():
  with (destination/(key+'.json')).open('xb') as stream:stream.write(value)
 with (destination/'native-proof.json').open('xb') as stream:stream.write(proof_bytes)
 validate_bundle(destination,ctx['commit'],ctx['tree'],ctx['runId'],ctx['rid'],source,received)
 delivery.mkdir(parents=True,exist_ok=True)
 shutil.copy2(archive,delivery/archive.name)

# Carrier-only delta. The reviewed H1/H2/H3 functions above are unchanged.
import base64,datetime
TRANSPORT_REPO='pouriajamali/fix-session-recovery-harness'
TRANSPORT_PIN='55cc8345863c7cc4c66a329aec7e433d2d1c52a9'
PROOF_NAMES=('native-proof.json',*(key+'.json' for key in FACTS))
FRAME_PREFIX='P08F1 '
CHUNK=3072
RAW_LIMIT=1024*1024
FRAME_LIMIT=2*1024*1024
JOB_LOG_LIMIT=32*1024*1024
CACHE_ENTRY_LIMIT=56*1024*1024
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def log_context(commit,tree,run_id,rid,job='verify'):
 text(commit,'[0-9a-f]{40}');text(tree,'[0-9a-f]{40}');text(str(run_id),'[1-9][0-9]{0,19}')
 assert (job=='verify' and rid in ('win-x64','linux-x64')) or (job=='release' and rid=='both')
 return {'repository':TRANSPORT_REPO,'commit':commit,'sourceTree':tree,'runId':str(run_id),
  'attempt':1,'job':job,'jobName':'Native '+rid if job=='verify' else 'Release aggregate','rid':rid}
def validate_log_context(value):
 closed(value,('repository','commit','sourceTree','runId','attempt','job','jobName','rid'))
 expected=log_context(value['commit'],value['sourceTree'],value['runId'],value['rid'],value['job'])
 integer(value['attempt'],1,1);assert value==expected
def proof_bytes(directory):
 assert directory.is_dir() and not directory.is_symlink()
 assert {path.name for path in directory.iterdir()}==set(PROOF_NAMES)
 output={}
 for name in PROOF_NAMES:
  path=directory/name
  assert path.is_file() and not path.is_symlink();integer(path.stat().st_size,1,131072)
  output[name]=path.read_bytes()
 assert sum(map(len,output.values()))<=RAW_LIMIT
 return output
def validate_proof_bytes(files,context,source,received):
 validate_log_context(context);assert context['job']=='verify'
 closed(files,PROOF_NAMES);assert sum(map(len,files.values()))<=RAW_LIMIT
 assert all(type(value) is bytes and 0<len(value)<=131072 for value in files.values())
 proof=loads(files['native-proof.json'].decode('utf-8'))
 validate_envelope(proof,context['commit'],context['sourceTree'],context['runId'],context['rid'],source,received)
 facts={}
 for key in FACTS:
  assert hashlib.sha256(files[key+'.json']).hexdigest()==proof['files'][key]['sha256']
  facts[key]=loads(files[key+'.json'].decode('utf-8'))
 validate_facts(facts,context['rid'],context['commit'],True)
 assert facts['consumer']['manifestSha256']==received['manifestSha256']
 return proof
def framed(files,context,kind):
 validate_log_context(context)
 assert (kind=='native' and tuple(files)==PROOF_NAMES and context['job']=='verify') or (kind=='draft' and tuple(files)==('DRAFT-STAGE.json',) and context['job']=='release')
 assert all(type(value) is bytes and 0<len(value)<=131072 for value in files.values())
 assert sum(map(len,files.values()))<=RAW_LIMIT
 inventory=[{'name':name,'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in files.items()]
 records=[]
 def add(value):
  record={'version':1,'kind':kind,'context':context,'index':len(records),**value}
  records.append(FRAME_PREFIX.encode()+canonical(record)+b'\n')
 add({'type':'begin','files':inventory,'rawBytes':sum(map(len,files.values())),'chunkBytes':CHUNK})
 for fi,(name,value) in enumerate(files.items()):
  count=(len(value)+CHUNK-1)//CHUNK
  for ci in range(count):
   chunk=value[ci*CHUNK:(ci+1)*CHUNK]
   add({'type':'data','fileIndex':fi,'chunkIndex':ci,'chunkCount':count,'bytes':len(chunk),
    'sha256':hashlib.sha256(chunk).hexdigest(),'data':base64.b64encode(chunk).decode('ascii')})
 add({'type':'end','recordCount':len(records)+1,'recordsSha256':hashlib.sha256(b''.join(records)).hexdigest()})
 output=b''.join(records);assert len(output)<=FRAME_LIMIT
 return output
def service_lines(log):
 assert type(log) is bytes and len(log)<=JOB_LOG_LIMIT
 if FRAME_PREFIX.encode() in log:assert log.endswith(b'\n')
 output=[]
 for line in log.decode('utf-8',errors='strict').splitlines():
  # Only a finite GitHub service timestamp may precede our protocol.
  if re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T',line):
   match=re.match(r'^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,7})?Z) (.*)$',line)
   assert match and len(match[1])<=28
   datetime.datetime.fromisoformat(match[1].replace('Z','+00:00'))
   line=match[2]
  output.append(line)
 return output
def unframe(log,expected,kind):
 validate_log_context(expected)
 names=PROOF_NAMES if kind=='native' else ('DRAFT-STAGE.json',)
 assert kind in ('native','draft')
 lines=[];records=[]
 for line in service_lines(log):
  if FRAME_PREFIX.strip() in line:
   assert line.startswith(FRAME_PREFIX) and len(line)<=8192
   value=loads(line[len(FRAME_PREFIX):])
   assert type(value) is dict and value.get('version')==1 and type(value['version']) is int
   validate_log_context(value['context'])
   assert value.get('context')==expected and value.get('kind')==kind and value.get('index')==len(records)
   integer(value['index'],0,1024)
   records.append(value);lines.append((line+'\n').encode())
 assert records and sum(map(len,lines))<=FRAME_LIMIT
 common=('version','kind','context','index','type')
 begin=records[0];closed(begin,(*common,'files','rawBytes','chunkBytes'))
 assert begin['type']=='begin' and type(begin['chunkBytes']) is int and begin['chunkBytes']==CHUNK
 assert type(begin['files']) is list and len(begin['files'])==len(names)
 expected_data=0
 for item,name in zip(begin['files'],names):
  closed(item,('name','bytes','sha256'));assert item['name']==name;integer(item['bytes'],1,131072);sha(item['sha256'])
  expected_data+=(item['bytes']+CHUNK-1)//CHUNK
 integer(begin['rawBytes'],1,RAW_LIMIT);assert begin['rawBytes']==sum(item['bytes'] for item in begin['files'])
 assert len(records)==expected_data+2
 end=records[-1];closed(end,(*common,'recordCount','recordsSha256'))
 assert end['type']=='end' and type(end['recordCount']) is int and end['recordCount']==len(records)
 assert end['recordsSha256']==hashlib.sha256(b''.join(lines[:-1])).hexdigest()
 output={};ri=1
 for fi,item in enumerate(begin['files']):
  chunks=[];count=(item['bytes']+CHUNK-1)//CHUNK
  for ci in range(count):
   value=records[ri];ri+=1
   closed(value,(*common,'fileIndex','chunkIndex','chunkCount','bytes','sha256','data'))
   assert value['type']=='data'
   for key,want in (('fileIndex',fi),('chunkIndex',ci),('chunkCount',count)):
    integer(value[key],want,want)
   assert type(value['data']) is str
   chunk=base64.b64decode(value['data'],validate=True)
   assert base64.b64encode(chunk).decode()==value['data']
   want=min(CHUNK,item['bytes']-ci*CHUNK);integer(value['bytes'],want,want)
   assert len(chunk)==want and hashlib.sha256(chunk).hexdigest()==value['sha256']
   chunks.append(chunk)
  data=b''.join(chunks);assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
  output[item['name']]=data
 return output
def handoff(files,archive,context):
 validate_log_context(context);assert context['job']=='verify'
 assert archive.name==archive_name(context['rid']) and archive.is_file() and not archive.is_symlink()
 integer(archive.stat().st_size,1,48*1024*1024);closed(files,PROOF_NAMES)
 assert sum(map(len,files.values()))<=RAW_LIMIT
 inventory=[{'name':archive.name,'bytes':archive.stat().st_size,'sha256':digest(archive)}]
 inventory.extend({'name':name,'bytes':len(files[name]),'sha256':hashlib.sha256(files[name]).hexdigest()} for name in PROOF_NAMES)
 value={'schema':'project08-same-run-handoff-v1','context':context,'files':inventory,
  'rawBytes':sum(row['bytes'] for row in inventory),'nativeProofSha256':inventory[1]['sha256']}
 return value
def validate_handoff(value,context):
 closed(value,('schema','context','files','rawBytes','nativeProofSha256'));validate_log_context(context)
 validate_log_context(value['context'])
 assert value['schema']=='project08-same-run-handoff-v1' and value['context']==context and context['job']=='verify'
 names=(archive_name(context['rid']),*PROOF_NAMES)
 assert type(value['files']) is list and len(value['files'])==7
 for index,(row,name) in enumerate(zip(value['files'],names)):
  closed(row,('name','bytes','sha256'));assert row['name']==name;sha(row['sha256'])
  integer(row['bytes'],1,48*1024*1024 if index==0 else 131072)
 assert sum(row['bytes'] for row in value['files'][1:])<=RAW_LIMIT
 integer(value['rawBytes'],1,49*1024*1024);assert value['rawBytes']==sum(row['bytes'] for row in value['files'])
 assert value['nativeProofSha256']==value['files'][1]['sha256']
 return hashlib.sha256(canonical(value)).hexdigest()
def handoff_key(value,context):
 sha256=validate_handoff(value,context)
 return 'project08-v1-'+TRANSPORT_REPO.replace('/','-')+'-'+context['commit']+'-'+context['runId']+'-attempt1-'+context['rid']+'-'+sha256
def encode_handoff(value):
 validate_handoff(value,value['context'])
 return base64.b64encode(canonical(value)).decode('ascii')
def decode_handoff(encoded,context):
 assert type(encoded) is str and len(encoded)<=8192
 data=base64.b64decode(encoded,validate=True);value=loads(data.decode('ascii'))
 assert canonical(value)==data;validate_handoff(value,context)
 return value
def exact_cache_outputs(hit,primary,matched,expected):
 assert type(hit) is str and hit=='true' and type(primary) is str and type(matched) is str
 assert primary==matched==expected
def validate_carrier(directory,expected,context,source):
 # expected MUST originate from trusted needs.verify.outputs, never restored bytes.
 validate_handoff(expected,context)
 assert directory.is_dir() and not directory.is_symlink()
 assert {path.name for path in directory.iterdir()}=={row['name'] for row in expected['files']}
 for row in expected['files']:
  path=directory/row['name']
  assert path.is_file() and not path.is_symlink() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256']
 files={name:(directory/name).read_bytes() for name in PROOF_NAMES}
 received=archive_identity(directory/archive_name(context['rid']),context['rid'])
 validate_proof_bytes(files,context,source,received)
 return files,received
def affirmative_save(log,expected_key):
 lines=service_lines(log)
 assert sum(line=='Cache saved with key: '+expected_key for line in lines)==1,'Affirmative actual save absent/ambiguous'
 assert sum(line=='Cache found and can be restored from key: '+expected_key for line in lines)==1,'Exact post-save availability absent'
def cache_entry(value,expected_key,expected_ref):
 assert type(expected_ref) is str and expected_ref=='refs/tags/v0.1.0-preview.3'
 # Raw API body remains private; only selected typed fields are used.
 assert type(value) is dict and type(value.get('actions_caches')) is list
 integer(value.get('total_count'),1,8);assert value['total_count']==len(value['actions_caches'])
 rows=[row for row in value['actions_caches'] if type(row) is dict and row.get('key')==expected_key]
 assert len(rows)==1
 row=rows[0];integer(row.get('id'),1,99999999999999999999)
 assert type(row.get('ref')) is str and row['ref'] in ('refs/tags/v0.1.0-preview.3','refs/heads/refs/tags/v0.1.0-preview.3')
 text(row.get('version'),'[0-9a-f]{64}')
 integer(row.get('size_in_bytes'),1,CACHE_ENTRY_LIMIT)
 return row['size_in_bytes']
def validate_draft_stage(value,commit,tree,run_id):
 closed(value,('schema','repository','tag','commit','sourceTree','workflowRunId','sdk','runtime','reportSchema','nativeProofs','assets','releaseId','stageAssetIds'))
 assert value['schema']=='project08-draft-stage-v1' and value['repository']==TRANSPORT_REPO
 assert value['tag']=='v0.1.0-preview.3' and value['commit']==commit and value['sourceTree']==tree
 integer(value['workflowRunId'],1,99999999999999999999);assert str(value['workflowRunId'])==str(run_id)
 assert value['sdk']=='10.0.404' and value['runtime']=='10.0.15' and value['reportSchema']=='fix-session-harness-report-v2'
 closed(value['nativeProofs'],('win-x64','linux-x64'))
 for rid,native in value['nativeProofs'].items():
  closed(native,('commit','outcome','fourCases','kernelAdmitted','receiptSha256','fileHashes'))
  assert native['commit']==commit and native['outcome']=='pass' and native['fourCases'] is True and native['kernelAdmitted'] is True
  sha(native['receiptSha256']);closed(native['fileHashes'],FACTS)
  for item in native['fileHashes'].values():sha(item)
 names=(archive_name('win-x64'),archive_name('linux-x64'),'fix-session-recovery-harness-v0.1.0-preview.3-source.zip','SHA256SUMS.txt','SIGNING-PUBLIC-KEY.pub')
 closed(value['assets'],names);closed(value['stageAssetIds'],names)
 ids=[]
 for name,asset in value['assets'].items():
  closed(asset,('bytes','sha256'));sha(asset['sha256'])
  maximum=48*1024*1024 if name.endswith(('.tar.gz','win-x64.zip')) else 1024*1024 if name.endswith('source.zip') else 65536
  integer(asset['bytes'],1,maximum);integer(value['stageAssetIds'][name],1,99999999999999999999);ids.append(value['stageAssetIds'][name])
 assert len(set(ids))==5;integer(value['releaseId'],1,99999999999999999999)

def carrier_directory(root,rid):
 assert rid in ('win-x64','linux-x64')
 root=root.resolve()
 for path in (root/'artifacts',root/'artifacts/project08-handoff',root/'artifacts/project08-handoff'/rid):
  assert not path.is_symlink() and path.resolve().is_relative_to(root)
 return root/'artifacts/project08-handoff'/rid

def native_log(files,context,source,received):
 validate_proof_bytes(files,context,source,received)
 return framed(files,context,'native')
def recovered_native_log(log,context,source):
 files=unframe(log,context,'native')
 value=loads(files['native-proof.json'].decode('utf-8'))
 producer=value['producer']
 received={key:producer[key] for key in ('archiveSha256','archiveBytes','manifestSha256','payloadFiles')}
 received.update(commit=producer['commit'],sourceTree=producer['sourceTree'],rid=producer['rid'])
 validate_proof_bytes(files,context,source,received)
 # This validates authenticated producer observations, not downloaded archive bytes.
 return files
def draft_log(value,context):
 validate_log_context(context);assert context['job']=='release'
 validate_draft_stage(value,context['commit'],context['sourceTree'],context['runId'])
 return framed({'DRAFT-STAGE.json':canonical(value)},context,'draft')
def recovered_draft_log(log,context):
 files=unframe(log,context,'draft')
 value=loads(files['DRAFT-STAGE.json'].decode('ascii'))
 validate_draft_stage(value,context['commit'],context['sourceTree'],context['runId'])
 return value
