# Adapted from Pouria Jamali's public MIT sqlite-recovery-drill (003b700d); see NOTICE.md.
"""Check exact already-tested runtime archives; source packaging only, no binary rebuild."""
import argparse,hashlib,json,re,subprocess,tarfile,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]

def bounded_json(path):
 assert path.stat().st_size<=131072 and not path.is_symlink()
 def pairs(values):
  output={}
  for key,value in values:
   assert key not in output,'Duplicate receipt field'
   output[key]=value
  return output
 return json.loads(path.read_text(encoding='utf-8-sig'),object_pairs_hook=pairs)

def stage_input(directory,proof_root,commit,tag,run_id,output):
 _stage('INPUT')
 assert tag=='v0.1.0-preview.4' and re.fullmatch('[1-9][0-9]{0,19}',run_id) and re.fullmatch('[0-9a-f]{40}',commit)
 from project08_hosted_proof import validate_bundle,source_data,archive_identity,archive_name
 _stage('SOURCE')
 source=source_data(*(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT) for name in
  ('tools/project08-hosted-profile.json','tools/project08_hosted.py','tools/project08-sdk404-members.jsonl','tools/package.py')))
 tree=subprocess.check_output(['git','rev-parse',commit+'^{tree}'],cwd=ROOT,text=True).strip()
 native={}
 for rid in ('win-x64','linux-x64'):
  path=proof_root/rid/'native-proof.json'
  _stage('ARCHIVE')
  received=archive_identity(directory/archive_name(rid),rid)
  _stage('NATIVE_PROOF')
  proof=validate_bundle(path.parent,commit,tree,run_id,rid,source,received)
  native[rid]={'commit':commit,'outcome':'pass','fourCases':True,'kernelAdmitted':True,
               'receiptSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
               'fileHashes':{key:item['sha256'] for key,item in proof['files'].items()}}
 _stage('ASSETS')
 names=[f'fix-session-recovery-harness-{tag}-{suffix}' for suffix in ('win-x64.zip','linux-x64.tar.gz','source.zip')]
 assets={name:{'bytes':(directory/name).stat().st_size,'sha256':hashlib.sha256((directory/name).read_bytes()).hexdigest()} for name in names+['SHA256SUMS.txt']}
 key=ROOT/'SIGNING-PUBLIC-KEY.pub'
 assert hashlib.sha256(key.read_bytes()).hexdigest()=='a59fbecc53a0b3109212b70a3a51247dbd3529512d189ac2462a27a057dad671'
 assets[key.name]={'bytes':key.stat().st_size,'sha256':hashlib.sha256(key.read_bytes()).hexdigest()}
 result={'schema':'project08-draft-stage-v1','repository':'pouriajamali/fix-session-recovery-harness',
         'tag':tag,'commit':commit,'sourceTree':subprocess.check_output(['git','rev-parse',commit+'^{tree}'],cwd=ROOT,text=True).strip(),
         'workflowRunId':int(run_id),'sdk':'10.0.404','runtime':'10.0.15',
         'reportSchema':'fix-session-harness-report-v2','nativeProofs':native,'assets':assets}
 _stage('STATE_WRITE')
 with output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')

def bind_draft(stage_path,draft_path,output):
 _stage('DRAFT')
 stage=bounded_json(stage_path);draft=bounded_json(draft_path)
 assert stage['schema']=='project08-draft-stage-v1' and draft['draft'] is True and draft['prerelease'] is True
 assert draft['tag_name']==stage['tag']=='v0.1.0-preview.4'
 assert len(draft['assets'])==5 and {v['name'] for v in draft['assets']}==set(stage['assets'])
 assert len({v['id'] for v in draft['assets']})==5
 for item in draft['assets']:
  expected=stage['assets'][item['name']]
  assert item['size']==expected['bytes'] and item['digest']=='sha256:'+expected['sha256'] and item['state']=='uploaded'
 stage['releaseId']=draft['id']
 stage['stageAssetIds']={v['name']:v['id'] for v in draft['assets']}
 _stage('STATE_WRITE')
 with output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(stage,stream,indent=2);stream.write('\n')

def main():
 _stage('INPUT')
 p=_FixedArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--tag',required=True);p.add_argument('--proof-root',type=Path);p.add_argument('--run-id');p.add_argument('--stage-receipt',type=Path);p.add_argument('--stage-input',type=Path);p.add_argument('--bind-draft',type=Path);a=p.parse_args()
 if a.bind_draft:
  assert a.stage_input and a.stage_receipt
  bind_draft(a.stage_input,a.bind_draft,a.stage_receipt);return
 assert (ROOT/'LICENSE').is_file(),'Valid original-source license required'
 expected={f'fix-session-recovery-harness-{a.tag}-win-x64.zip':'win-x64',f'fix-session-recovery-harness-{a.tag}-linux-x64.tar.gz':'linux-x64'}
 assert {p.name for p in a.directory.iterdir()}==set(expected)
 _stage('SOURCE')
 source_tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.commit+'^{tree}'],text=True).strip()
 trees=set();receipts=[]
 _stage('ARCHIVE')
 for name in sorted(expected):
  path=a.directory/name;payload={}
  if name.endswith('.zip'):
   with zipfile.ZipFile(path) as z:
    for info in z.infolist():
     if not info.is_dir():assert info.filename not in payload and info.file_size<64*1024*1024;payload[info.filename]=z.read(info)
  else:
   with tarfile.open(path,'r:gz') as t:
    for info in t:
     assert info.isfile(),'Only regular archive entries expected'
     assert info.name not in payload and info.size<64*1024*1024;payload[info.name]=t.extractfile(info).read()
  assert len(payload)<=512 and sum(map(len,payload.values()))<256*1024*1024
  assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in payload)
  roots={PurePosixPath(n).parts[0] for n in payload};assert len(roots)==1;prefix=roots.pop()+'/'
  files={n[len(prefix):]:v for n,v in payload.items()};m=json.loads(files.pop('BUILD-MANIFEST.json'))
  assert m['sourceCommit']==a.commit and m['version']==a.tag.removeprefix('v') and m['selfContained'] and not m['localCandidate'] and m['originalLicense']=='present'
  assert m['sdkVersion']=='10.0.404' and m['runtimeVersion']=='10.0.15'
  assert m['rid']==expected[name] and m['sourceTree']==source_tree and m['buildHost']['os']==('Windows' if m['rid']=='win-x64' else 'Linux')
  assert set(files)=={v['path'] for v in m['files']} and 'LICENSE' in files
  for item in m['files']:assert len(files[item['path']])==item['bytes'] and hashlib.sha256(files[item['path']]).hexdigest()==item['sha256']
  assert a.commit.encode() in files['session-harness.dll'];trees.add(m['sourceTree'])
  receipts.append({'archive':name,'rid':m['rid'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
 assert len(trees)==1
 _stage('SOURCE_ZIP')
 source=a.directory/f'fix-session-recovery-harness-{a.tag}-source.zip';assert not source.exists()
 subprocess.run(['git','-C',str(ROOT),'-c','core.autocrlf=false','-c','core.eol=lf','archive','--format=zip',f'--prefix=fix-session-recovery-harness-{a.tag}-source/','--output='+str(source.resolve()),a.commit],check=True)
 assert source.stat().st_size<=1024*1024,'existing source archive<=1MiB'
 with zipfile.ZipFile(source) as z:
  names=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',a.commit],text=True).splitlines();prefix=f'fix-session-recovery-harness-{a.tag}-source/'
  assert {i.filename for i in z.infolist() if not i.is_dir()}=={prefix+n for n in names}
  for n in names:assert z.read(prefix+n)==subprocess.check_output(['git','-C',str(ROOT),'show',a.commit+':'+n])
 sums=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(a.directory.iterdir()) if p.suffix in {'.zip','.gz'})
 (a.directory/'SHA256SUMS.txt').write_text(sums,encoding='utf-8',newline='\n')
 if a.stage_receipt:
  assert a.proof_root and a.run_id
  stage_input(a.directory,a.proof_root,a.commit,a.tag,a.run_id,a.stage_receipt)
 print(json.dumps({'status':'ALREADY_TESTED_RUNTIME_ARCHIVES_AND_EXACT_SOURCE_VERIFIED','archives':receipts,'sourceFiles':len(names)}))



# Observable, fixed-repository read transport. No CLI/auth fallback or response persistence.
import contextlib,http.client,os,signal,socket,ssl,sys,time
from urllib.parse import urlsplit
HTTP_REPO='pouriajamali/fix-session-recovery-harness'
HTTP_BASE='repos/'+HTTP_REPO+'/actions/'
HTTP_OPERATIONS={'INPUT','RELEASE_DATA_GUARDS','NATIVE_LOG','PREPARE_CARRIER','PRODUCER_AVAILABLE','TOOLS','EXPECT_CARRIERS','ACCEPT_CARRIER','DRAFT_LOG','READ_ONLY_TRANSPORT_PREFLIGHT'}
HTTP_STAGES={'INPUT','TOKEN','API_REQUEST','HTTP_STATUS','REDIRECT','BODY_LENGTH','BODY','DEADLINE','JSON','RUN','JOBS','OUTPUTS','HANDOFF','LOG_FRAME','SAVE','CACHE_KEY','CACHE_REF','CACHE_VERSION','CACHE_SIZE','STATE_WRITE','SOURCE','ARCHIVE','NATIVE_PROOF','ASSETS','SOURCE_ZIP','DRAFT','TOOLS','CACHE_RESTORE','READINESS','DONE','CLEANUP','AGGREGATE_JOBS','AGGREGATE_JOB_LOG','AGGREGATE_CACHE','READINESS_SOURCE_RUNS','READINESS_JOBS','READINESS_JOB_LOG','READINESS_CACHE_USAGE','UNSIGNED_LOG_FETCH'}
HTTP_REASONS={'ASSERTION','INPUT','TOKEN','HTTP_TRANSPORT','HTTP_STATUS','REDIRECT','BODY_LENGTH','BODY_LIMIT','BODY_TRUNCATED','DEADLINE','TIMEOUT','JSON_INVALID','STATE_WRITE','READY'}
_ACTIVE_DIAGNOSTIC=None
class TransportHold(Exception):
 pass
class TransportDiagnostic:
 def __init__(self,operation,identity=None,clock=None,progress=False):
  self.operation=operation if type(operation) is str and operation in HTTP_OPERATIONS else 'INPUT'
  self.progress_enabled=progress
  self.clock=clock or time.monotonic;self.deadline=None;self.current='INPUT';self.http_status=None;self.first=None
  value=identity or {}
  sha=value.get('commit',os.environ.get('GITHUB_SHA'))
  run=value.get('runId',os.environ.get('GITHUB_RUN_ID'))
  attempt=value.get('runAttempt',os.environ.get('GITHUB_RUN_ATTEMPT'))
  self.source=sha if type(sha) is str and re.fullmatch('[0-9a-f]{40}',sha) else None
  self.run=int(run) if type(run) is str and re.fullmatch('[1-9][0-9]{0,19}',run) else None
  self.attempt=1 if type(attempt) is str and attempt=='1' else None
 def stage(self,value):
  assert value in HTTP_STAGES
  self.current=value
  self.check()
 def progress(self,value):
  assert value in HTTP_STAGES
  if self.progress_enabled:sys.stdout.write('PROJECT08_HTTP_STAGE '+value+'\n')
 def check(self):
  if self.deadline is not None and self.clock()>=self.deadline:self.hold('DEADLINE')
 def record(self,reason):
  assert reason in HTTP_REASONS
  if self.first is None:
   self.first={'schema':'project08-observable-http-diagnostic-v1','version':1,
    'operation':self.operation,'stage':self.current,'reason':reason,
    'sourceSHA':self.source,'workflowRunId':self.run,'attempt':self.attempt,'httpStatus':self.http_status}
  return self.first
 def hold(self,reason):
  self.record(reason);raise TransportHold() from None
 def emit(self,reason=None):
  if reason=='READY':
   assert self.first is None
   value={'schema':'project08-observable-http-diagnostic-v1','version':1,'operation':self.operation,'stage':self.current,'reason':'READY','sourceSHA':self.source,'workflowRunId':self.run,'attempt':self.attempt,'httpStatus':self.http_status}
  else:value=self.record(reason or 'ASSERTION')
  encoded=('PROJECT08_HTTP_DIAGNOSTIC '+json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
  assert len(encoded)<=1024
  sys.stdout.write(encoded.decode('ascii'))
def _stage(value):
 if _ACTIVE_DIAGNOSTIC is not None:_ACTIVE_DIAGNOSTIC.stage(value)
@contextlib.contextmanager
def _using_diagnostic(value):
 global _ACTIVE_DIAGNOSTIC
 previous=_ACTIVE_DIAGNOSTIC;_ACTIVE_DIAGNOSTIC=value
 try:yield
 finally:_ACTIVE_DIAGNOSTIC=previous
class _FixedArgumentParser(argparse.ArgumentParser):
 def error(self,message):
  _stage('INPUT')
  if _ACTIVE_DIAGNOSTIC is not None:_ACTIVE_DIAGNOSTIC.hold('INPUT')
  raise TransportHold() from None
@contextlib.contextmanager
def _hard_http_window(reader):
 # HTTP consumers are the existing Ubuntu policy/release jobs. Unsupported timer => HOLD.
 d=reader.diagnostic;d.stage('DEADLINE')
 if not all(hasattr(signal,key) for key in ('SIGALRM','ITIMER_REAL','setitimer','getitimer')):d.hold('DEADLINE')
 old=signal.getitimer(signal.ITIMER_REAL)
 if old[0]!=0 or old[1]!=0:d.hold('DEADLINE')
 handler=signal.getsignal(signal.SIGALRM)
 def expired(signum,frame):d.hold('DEADLINE')
 signal.signal(signal.SIGALRM,expired)
 try:
  signal.setitimer(signal.ITIMER_REAL,max(0.001,reader.deadline-reader.clock()))
  yield
  d.check()
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  signal.signal(signal.SIGALRM,handler)
class TransportHTTP:
 def __init__(self,ctx,token,diagnostic,mode='aggregate',clock=None):
  self.clock=clock or time.monotonic;self.deadline=self.clock()+60.0
  self.diagnostic=diagnostic;diagnostic.clock=self.clock;diagnostic.deadline=self.deadline
  diagnostic.stage('INPUT')
  if mode not in ('aggregate','readiness'):diagnostic.hold('INPUT')
  if type(ctx) is not dict:diagnostic.hold('INPUT')
  if type(ctx.get('commit')) is not str or not re.fullmatch('[0-9a-f]{40}',ctx['commit']):diagnostic.hold('INPUT')
  if type(ctx.get('runId')) is not str or not re.fullmatch('[1-9][0-9]{0,19}',ctx['runId']):diagnostic.hold('INPUT')
  if type(ctx.get('runAttempt')) is not str or ctx['runAttempt']!='1':diagnostic.hold('INPUT')
  diagnostic.stage('TOKEN')
  if type(token) is not str or not 0<len(token)<=8192 or not all(32<ord(c)<127 for c in token):diagnostic.hold('TOKEN')
  self.ctx=ctx;self.token=token;self.mode=mode;self.api_calls=0;self.redirect_calls=0;self.metadata_bytes=0
  self.jobs_run=ctx['runId'] if mode=='aggregate' else None;self.job_ids=set();self.keys=set()
 def bind_source_run(self,value):
  self.diagnostic.stage('RUN')
  if self.mode!='readiness' or type(value) is not int or not 0<value<10**20:self.diagnostic.hold('INPUT')
  self.jobs_run=str(value)
 def bind_job(self,job):
  self.diagnostic.stage('JOBS')
  assert type(job) is dict and type(job.get('id')) is int and 0<job['id']<10**20
  self.diagnostic.stage('RUN')
  assert type(job.get('run_id')) is int and str(job['run_id'])==self.jobs_run
  assert type(job.get('run_attempt')) is int and job['run_attempt']==1
  assert job.get('head_sha')==self.ctx['commit'] and job.get('status')=='completed' and job.get('conclusion')=='success'
  self.diagnostic.stage('JOBS')
  assert job.get('name') in ('Native win-x64','Native linux-x64')
  self.job_ids.add(job['id'])
 def bind_key(self,key):
  self.diagnostic.stage('CACHE_KEY')
  assert self.mode=='aggregate' and type(key) is str
  match=re.fullmatch(r'project08-v1-pouriajamali-fix-session-recovery-harness-([0-9a-f]{40})-([1-9][0-9]{0,19})-attempt1-(win-x64|linux-x64)-([0-9a-f]{64})',key)
  assert match and match[1]==self.ctx['commit'] and match[2]==self.ctx['runId']
  self.keys.add(key)
 def _route(self,endpoint,limit):
  self.diagnostic.stage('API_REQUEST')
  if type(endpoint) is not str or len(endpoint)>1024 or type(limit) is not int or limit<=0:self.diagnostic.hold('INPUT')
  base=re.escape(HTTP_BASE)
  jobs=re.fullmatch(base+r'runs/([1-9][0-9]{0,19})/attempts/1/jobs\?per_page=100',endpoint)
  log=re.fullmatch(base+r'jobs/([1-9][0-9]{0,19})/logs',endpoint)
  cache=re.fullmatch(base+r'caches\?key=([^&]+)&per_page=100',endpoint)
  runs=re.fullmatch(base+r'workflows/verify\.yml/runs\?branch=main&event=push&status=success&head_sha=([0-9a-f]{40})&per_page=20',endpoint)
  if jobs and jobs[1]==self.jobs_run:kind='metadata';step='AGGREGATE_JOBS' if self.mode=='aggregate' else 'READINESS_JOBS'
  elif log and int(log[1]) in self.job_ids:kind='log';step='AGGREGATE_JOB_LOG' if self.mode=='aggregate' else 'READINESS_JOB_LOG'
  elif cache and self.mode=='aggregate' and cache[1] in self.keys:kind='metadata';step='AGGREGATE_CACHE'
  elif runs and self.mode=='readiness' and runs[1]==self.ctx['commit']:kind='metadata';step='READINESS_SOURCE_RUNS'
  elif endpoint==HTTP_BASE+'cache/usage' and self.mode=='readiness':kind='metadata';step='READINESS_CACHE_USAGE'
  else:self.diagnostic.hold('INPUT')
  if limit>(32*1024*1024 if kind=='log' else 131072):self.diagnostic.hold('BODY_LIMIT')
  self.diagnostic.progress(step)
  return kind
 def _connection(self,host,timeout):
  context=ssl.create_default_context()
  assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
  return http.client.HTTPSConnection(host,timeout=timeout,context=context)
 def _remaining(self):
  self.diagnostic.check();return max(0.001,min(10.0,self.deadline-self.clock()))
 def _fetch(self,host,path,api,limit,can_redirect):
  d=self.diagnostic;d.http_status=None;d.stage('API_REQUEST');connection=None
  if api:
   if host!='api.github.com':d.hold('INPUT')
  elif not re.fullmatch(r'productionresultssa[0-9]{1,2}\.blob\.core\.windows\.net',host):d.hold('REDIRECT')
  headers={'Accept':'application/vnd.github+json' if api and not can_redirect else 'application/octet-stream','User-Agent':'project08-fixed-actions-reader'}
  if api:headers.update(Authorization='Bearer '+self.token,**{'X-GitHub-Api-Version':'2026-03-10'})
  try:
   connection=self._connection(host,self._remaining());connection.connect();wire=connection.sock
   wire.settimeout(self._remaining())
   connection.request('GET',path,headers=headers)
   wire.settimeout(self._remaining());response=connection.getresponse()
   d.stage('HTTP_STATUS')
   if type(response.status) is not int or not 100<=response.status<=599:d.hold('HTTP_STATUS')
   d.http_status=response.status
   if 300<=response.status<400:
    d.stage('REDIRECT')
    if not (response.status in (302,303) and api and can_redirect):d.hold('REDIRECT')
    items=[v for k,v in response.getheaders() if k.lower()=='location']
    if len(items)!=1:d.hold('REDIRECT')
    return None,items[0]
   if response.status!=200:d.hold('HTTP_STATUS')
   d.stage('BODY_LENGTH');headers_in=response.getheaders()
   if len(headers_in)>100 or sum(len(k)+len(v) for k,v in headers_in)>16384:d.hold('BODY_LENGTH')
   lengths=[value for key,value in headers_in if key.lower()=='content-length']
   if len(lengths)>1:d.hold('BODY_LENGTH')
   declared=None
   if lengths:
    if type(lengths[0]) is not str or not re.fullmatch('[0-9]{1,12}',lengths[0]):d.hold('BODY_LENGTH')
    declared=int(lengths[0])
    if declared>limit:d.hold('BODY_LIMIT')
   parts=[];total=0;d.stage('BODY')
   while True:
    wire.settimeout(self._remaining())
    data=response.read(min(65536,limit-total+1))
    d.check()
    if type(data) is not bytes:d.hold('BODY_TRUNCATED')
    if not data:break
    total+=len(data)
    if total>limit:d.hold('BODY_LIMIT')
    if declared is not None and total>declared:d.hold('BODY_LENGTH')
    parts.append(data)
   if declared is not None and total!=declared:d.hold('BODY_TRUNCATED')
   return b''.join(parts),None
  except TransportHold:raise
  except (TimeoutError,socket.timeout):
   d.hold('DEADLINE' if self.clock()>=self.deadline else 'TIMEOUT')
  except http.client.IncompleteRead:d.hold('BODY_TRUNCATED')
  except Exception:d.hold('HTTP_TRANSPORT')
  finally:
   if connection is not None:
    try:connection.close()
    except Exception:
     if d.first is None:d.stage('CLEANUP');d.hold('HTTP_TRANSPORT')
 def get(self,endpoint,limit=131072):
  self.diagnostic.http_status=None
  kind=self._route(endpoint,limit);self.api_calls+=1
  if self.api_calls>5:self.diagnostic.hold('INPUT')
  data,location=self._fetch('api.github.com','/'+endpoint,True,limit,kind=='log')
  if location is not None:
   d=self.diagnostic;d.stage('REDIRECT')
   if type(location) is not str or len(location)>8192 or any(ord(c)<=32 or ord(c)>=127 for c in location):d.hold('REDIRECT')
   try:
    parsed=urlsplit(location)
    assert parsed.scheme=='https' and not parsed.username and not parsed.password and not parsed.fragment
    assert parsed.port in (None,443) and parsed.path.startswith('/')
    assert re.fullmatch(r'productionresultssa[0-9]{1,2}\.blob\.core\.windows\.net',parsed.hostname or '')
   except Exception:d.hold('REDIRECT')
   self.redirect_calls+=1
   if self.redirect_calls>(1 if self.mode=='readiness' else 2):d.hold('REDIRECT')
   d.progress('UNSIGNED_LOG_FETCH')
   data,again=self._fetch(parsed.hostname,parsed.path+('?' + parsed.query if parsed.query else ''),False,limit,False)
   if again is not None:d.hold('REDIRECT')
  if kind=='metadata':
   self.metadata_bytes+=len(data)
   if self.metadata_bytes>5*131072:self.diagnostic.hold('BODY_LIMIT')
  self.diagnostic.check();return data
 def json(self,endpoint):
  data=self.get(endpoint,131072);self.diagnostic.stage('JSON')
  try:
   from project08_hosted_proof import loads
   result=loads(data.decode('utf-8'))
  except TransportHold:raise
  except Exception:self.diagnostic.hold('JSON_INVALID')
  self.diagnostic.check();return result

def _checked_cache_entry(proof,value,expected_key,expected_ref):
 _stage('CACHE_REF')
 assert type(expected_ref) is str and expected_ref=='refs/tags/v0.1.0-preview.4'
 _stage('CACHE_KEY')
 assert type(value) is dict and type(value.get('actions_caches')) is list
 proof.integer(value.get('total_count'),1,8);assert value['total_count']==len(value['actions_caches'])
 rows=[row for row in value['actions_caches'] if type(row) is dict and row.get('key')==expected_key]
 assert len(rows)==1
 row=rows[0];proof.integer(row.get('id'),1,99999999999999999999)
 _stage('CACHE_REF')
 assert type(row.get('ref')) is str and row['ref'] in ('refs/tags/v0.1.0-preview.4','refs/heads/refs/tags/v0.1.0-preview.4')
 _stage('CACHE_VERSION');proof.text(row.get('version'),'[0-9a-f]{64}')
 _stage('CACHE_SIZE');proof.integer(row.get('size_in_bytes'),1,proof.CACHE_ENTRY_LIMIT)
 return proof.cache_entry(value,expected_key,expected_ref)

def transport_readiness(proof,ctx,source,environment,reader):
 with _using_diagnostic(reader.diagnostic):
  _stage('READINESS')
  if environment.get('GITHUB_REF')!='refs/tags/v0.1.0-preview.4' or environment.get('GITHUB_EVENT_NAME')!='push':return False
  assert environment.get('GITHUB_JOB')=='ci_policy'
  runs=reader.json(HTTP_BASE+'workflows/verify.yml/runs?branch=main&event=push&status=success&head_sha='+ctx['commit']+'&per_page=20')
  _stage('RUN');assert type(runs) is dict and type(runs.get('workflow_runs')) is list
  proof.integer(runs.get('total_count'),1,20);assert runs['total_count']==len(runs['workflow_runs'])==1
  run=runs['workflow_runs'][0];assert type(run) is dict
  proof.integer(run.get('id'),1,99999999999999999999)
  assert type(run.get('run_attempt')) is int and run['run_attempt']==1
  assert run.get('head_sha')==ctx['commit'] and run.get('head_branch')=='main' and run.get('event')=='push'
  assert run.get('status')=='completed' and run.get('conclusion')=='success'
  assert run.get('path')=='.github/workflows/verify.yml' and type(run.get('repository')) is dict and run['repository'].get('full_name')==HTTP_REPO
  reader.bind_source_run(run['id'])
  jobs=reader.json(HTTP_BASE+'runs/'+str(run['id'])+'/attempts/1/jobs?per_page=100')
  _stage('JOBS');assert type(jobs) is dict and type(jobs.get('jobs')) is list
  proof.integer(jobs.get('total_count'),1,8);assert jobs['total_count']==len(jobs['jobs'])
  assert all(type(job) is dict for job in jobs['jobs'])
  selected=None
  for name in ('Native win-x64','Native linux-x64'):
   rows=[job for job in jobs['jobs'] if type(job) is dict and job.get('name')==name]
   assert len(rows)<=1
   if rows and selected is None:selected=rows[0]
  assert selected is not None
  _stage('RUN');reader.bind_job(selected)
  log=reader.get(HTTP_BASE+'jobs/'+str(selected['id'])+'/logs',proof.JOB_LOG_LIMIT)
  rid='win-x64' if selected['name']=='Native win-x64' else 'linux-x64'
  context=proof.log_context(ctx['commit'],ctx['tree'],str(run['id']),rid)
  _stage('LOG_FRAME');proof.recovered_native_log(log,context,source)
  usage=reader.json(HTTP_BASE+'cache/usage')
  _stage('CACHE_SIZE');assert type(usage) is dict
  proof.integer(usage.get('active_caches_size_in_bytes'),0,338*1024*1024)
  proof.integer(usage.get('active_caches_count'),0,6)
  reader.diagnostic.check();_stage('DONE');return True

def expect_carriers(proof,ctx,source,environment,private,output,reader):
 with _using_diagnostic(reader.diagnostic):
  _stage('STATE_WRITE');assert not private.exists();private.mkdir()
  jobs=reader.json(HTTP_BASE+'runs/'+ctx['runId']+'/attempts/1/jobs?per_page=100')
  _stage('JOBS');assert type(jobs) is dict and type(jobs.get('jobs')) is list
  proof.integer(jobs.get('total_count'),1,8);assert jobs['total_count']==len(jobs['jobs'])
  entries=[];compressed=[]
  for rid in ('win-x64','linux-x64'):
   p='win' if rid=='win-x64' else 'linux'
   context=proof.log_context(ctx['commit'],ctx['tree'],ctx['runId'],rid)
   _stage('OUTPUTS');assert environment[p.upper()+'_AVAILABLE']=='true'
   _stage('HANDOFF');value=proof.decode_handoff(environment[p.upper()+'_COMMITMENT'],context);key=proof.handoff_key(value,context)
   reader.bind_key(key)
   _stage('JOBS');rows=[job for job in jobs['jobs'] if job.get('name')==context['jobName']]
   assert len(rows)==1;job=rows[0]
   proof.integer(job.get('id'),1,99999999999999999999)
   _stage('RUN');proof.integer(job.get('run_id'),1,99999999999999999999)
   assert str(job['run_id'])==ctx['runId'] and type(job.get('run_attempt')) is int and job['run_attempt']==1
   assert job.get('head_sha')==ctx['commit'] and job.get('status')=='completed' and job.get('conclusion')=='success'
   reader.bind_job(job)
   log=reader.get(HTTP_BASE+'jobs/'+str(job['id'])+'/logs',proof.JOB_LOG_LIMIT)
   _stage('SAVE');proof.affirmative_save(log,key)
   _stage('LOG_FRAME');files=proof.recovered_native_log(log,context,source)
   _stage('HANDOFF')
   for row in value['files'][1:]:
    assert len(files[row['name']])==row['bytes'] and hashlib.sha256(files[row['name']]).hexdigest()==row['sha256']
   cache=reader.json(HTTP_BASE+'caches?key='+key+'&per_page=100')
   size=_checked_cache_entry(proof,cache,key,environment['GITHUB_REF']);compressed.append(size)
   entries.append((rid,value,key,size))
  _stage('CACHE_SIZE');assert sum(compressed)<=2*proof.CACHE_ENTRY_LIMIT and 6*proof.CACHE_ENTRY_LIMIT<=338*1024*1024
  _stage('STATE_WRITE')
  for rid,value,key,size in entries:
   path=private/(rid+'.json')
   payload={'context':proof.log_context(ctx['commit'],ctx['tree'],ctx['runId'],rid),'expected':value,'key':key,'actualSaveVerified':True,'cacheBytes':size}
   with path.open('xb') as stream:stream.write(proof.canonical(payload))
   output(('win' if rid=='win-x64' else 'linux')+'_key',key)
  reader.diagnostic.check()

# Fixed carrier commands: only data, current-run read APIs and owned file handoffs.
def transport_main(arguments):
 _stage('INPUT')
 import os,shutil,sys,tempfile,time
 import project08_hosted_proof as proof
 parser=_FixedArgumentParser()
 parser.add_argument('operation',choices=('native-log','prepare-carrier','producer-available','tools','expect-carriers','accept-carrier','draft-log','transport-readiness'))
 parser.add_argument('--rid',choices=('win-x64','linux-x64'));args=parser.parse_args(arguments)
 operation=args.operation
 from project08_hosted import context
 profile,ctx,state=context()
 assert os.environ.get('RUNNER_DEBUG')!='1'
 assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
 source=proof.source_at_root(ROOT)
 if operation=='transport-readiness':
  if os.environ.get('GITHUB_REF')!='refs/tags/v0.1.0-preview.4' or os.environ.get('GITHUB_EVENT_NAME')!='push':return
  assert os.environ['GITHUB_JOB']=='ci_policy'
  diagnostic=_ACTIVE_DIAGNOSTIC or TransportDiagnostic('READ_ONLY_TRANSPORT_PREFLIGHT',ctx)
  reader=TransportHTTP(ctx,os.environ.get('GH_TOKEN'),diagnostic,'readiness')
  with _hard_http_window(reader):
   ready=transport_readiness(proof,ctx,source,os.environ,reader)
  if ready:diagnostic.stage('DONE');diagnostic.emit('READY')
  return
 def lc(rid,job='verify'):return proof.log_context(ctx['commit'],ctx['tree'],ctx['runId'],rid,job)
 def output(name,value):
  assert re.fullmatch('(win|linux)_(commitment|key|available)',name) and type(value) is str and len(value)<=8192
  assert all(32<=ord(char)<127 for char in value)
  with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8',newline='\n') as stream:stream.write(name+'='+value+'\n')
 def prefix(rid):return 'win' if rid=='win-x64' else 'linux'
 def carrier(rid):return proof.carrier_directory(ROOT,rid)
 def private_root():return Path(os.environ['RUNNER_TEMP'])/('project08-transport-'+ctx['runId'])
 def data_event():
  assert os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch' or os.environ['GITHUB_REF'].startswith('refs/tags/')
 def exact_triplet(key):
  proof.exact_cache_outputs(os.environ['CACHE_HIT'],os.environ['CACHE_PRIMARY'],os.environ['CACHE_MATCHED'],key)
 def write_private(path,value):
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as stream:stream.write(proof.canonical(value))
 if operation=='tools':
  _stage('TOOLS')
  for rid in ('win-x64','linux-x64'):assert not carrier(rid).exists()
  # Action cache v6 crossOS uses GNU tar and zstd. No install or fallback.
  tar=str(Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Git/usr/bin/tar.exe') if os.name=='nt' else shutil.which('tar')
  assert tar and Path(tar).is_file() and shutil.which('zstd')
  for command,word in (([tar,'--version'],b'GNU tar'),(['zstd','--quiet','--version'],None)):
   result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,timeout=10)
   assert result.returncode==0 and len(result.stdout)+len(result.stderr)<=4096
   if word:assert word in result.stdout
   else:assert result.stdout.strip()
  return
 if operation in ('native-log','prepare-carrier','producer-available'):
  assert os.environ['GITHUB_JOB']=='verify'
  rid=ctx['rid'];context=lc(rid);directory=ROOT/'artifacts/native-proofs'/rid
  archive=ROOT/'artifacts/delivery'/proof.archive_name(rid)
  _stage('ARCHIVE')
  received=proof.archive_identity(archive,rid);files=proof.proof_bytes(directory)
  _stage('NATIVE_PROOF')
  proof.validate_proof_bytes(files,context,source,received)
  if operation=='native-log':
   sys.stdout.buffer.write(proof.native_log(files,context,source,received));return
  _stage('HANDOFF')
  data_event();value=proof.handoff(files,archive,context);key=proof.handoff_key(value,context)
  if operation=='prepare-carrier':
   path=carrier(rid)
   assert not path.exists() and not path.is_symlink()
   path.mkdir(parents=True,exist_ok=False)
   for name,data in ((archive.name,archive.read_bytes()),*files.items()):
    with (path/name).open('xb') as stream:stream.write(data)
   proof.validate_carrier(path,value,context,source)
   output(prefix(rid)+'_commitment',proof.encode_handoff(value));output(prefix(rid)+'_key',key)
   return
  _stage('SAVE')
  assert os.environ['CACHE_SAVE_OUTCOME']=='success'
  _stage('CACHE_RESTORE')
  exact_triplet(key)
  # Availability is affirmative; actual save is independently verified in producer log before draft.
  output(prefix(rid)+'_available','true');return
 assert os.environ['GITHUB_JOB']=='release'
 data_event()
 if operation=='expect-carriers':
  diagnostic=_ACTIVE_DIAGNOSTIC or TransportDiagnostic('EXPECT_CARRIERS',ctx)
  reader=TransportHTTP(ctx,os.environ.get('GH_TOKEN'),diagnostic,'aggregate')
  with _hard_http_window(reader):
   expect_carriers(proof,ctx,source,os.environ,private_root(),output,reader)
  return
 if operation=='accept-carrier':
  _stage('CACHE_RESTORE')
  assert args.rid
  rid=args.rid;context=lc(rid)
  private=proof.read(private_root()/(rid+'.json'))
  proof.closed(private,('context','expected','key','actualSaveVerified','cacheBytes'))
  assert private['context']==context and private['actualSaveVerified'] is True
  proof.integer(private['cacheBytes'],1,proof.CACHE_ENTRY_LIMIT)
  key=proof.handoff_key(private['expected'],context);assert key==private['key'];exact_triplet(key)
  _stage('NATIVE_PROOF')
  files,received=proof.validate_carrier(carrier(rid),private['expected'],context,source)
  _stage('STATE_WRITE')
  directory=ROOT/'artifacts/native-proofs'/rid;assert not directory.exists();directory.mkdir(parents=True)
  for name,data in files.items():
   with (directory/name).open('xb') as stream:stream.write(data)
  destination=ROOT/'artifacts/release';destination.mkdir(parents=True,exist_ok=True)
  with (destination/proof.archive_name(rid)).open('xb') as stream:stream.write((carrier(rid)/proof.archive_name(rid)).read_bytes())
  return
 _stage('DRAFT')
 assert operation=='draft-log'
 path=ROOT/'artifacts/DRAFT-STAGE.json'
 value=proof.read(path)
 sys.stdout.buffer.write(proof.draft_log(value,lc('both','release')))

def _entry():
 operations={'native-log':'NATIVE_LOG','prepare-carrier':'PREPARE_CARRIER','producer-available':'PRODUCER_AVAILABLE','tools':'TOOLS','expect-carriers':'EXPECT_CARRIERS','accept-carrier':'ACCEPT_CARRIER','draft-log':'DRAFT_LOG','transport-readiness':'READ_ONLY_TRANSPORT_PREFLIGHT'}
 operation=operations.get(sys.argv[2],'INPUT') if len(sys.argv)>2 and sys.argv[1]=='transport' else 'RELEASE_DATA_GUARDS'
 diagnostic=TransportDiagnostic(operation,progress=True)
 with _using_diagnostic(diagnostic):
  try:
   if len(sys.argv)>1 and sys.argv[1]=='transport':transport_main(sys.argv[2:])
   else:main()
   return 0
  except SystemExit as error:
   if error.code in (None,0):return 0
   diagnostic.record('INPUT')
  except Exception:diagnostic.record('ASSERTION')
  diagnostic.emit()
  print('PROJECT08_DATA_OR_TRANSPORT_HOLD',file=sys.stderr)
  return 1
if __name__=='__main__':
 sys.exit(_entry())
