"""Finite affected HTTP/diagnostic/readiness tests. No SDK/native or real I/O transport.
Private historical replay is optional in CI and mandatory in the owner's bound packet.
"""
import ast,base64,contextlib,copy,hashlib,http.client,importlib.util,io,json,os,re,socket,ssl,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
import check_release as target
import project08_hosted_proof as proof
CTX={'schema':'project08-hosted-context-v1','project':'08','commit':'c'*40,'tree':'d'*40,'runId':'222','runAttempt':'1','rid':'linux-x64','os':'Linux','root':str(ROOT)}
TOKEN='SYNTHETIC_PRIVATE_TOKEN'
REF='refs/tags/v0.1.0-preview.5'
BASE=target.HTTP_BASE
META=131072
class Clock:
 def __init__(self):self.now=0.0
 def __call__(self):return self.now
class Wire:
 def __init__(self):self.timeouts=[]
 def settimeout(self,value):assert 0<value<=10;self.timeouts.append(value)
class Reply:
 def __init__(self,status=200,body=b'{}',headers=None,error=None,onread=None):
  self.status=status;self.body=body;self.headers=[('Content-Length',str(len(body)))] if headers is None else headers
  self.error=error;self.onread=onread;self.position=0;self.reads=0
 def getheaders(self):return self.headers
 def read(self,size):
  self.reads+=1
  if self.onread:self.onread()
  if self.error:raise self.error
  data=self.body[self.position:self.position+size];self.position+=len(data);return data
class Backend:
 def __init__(self,routes=None,close_error=False):
  self.routes=routes or {};self.requests=[];self.responses=[];self.connections=[];self.close_error=close_error
 def connection(self,host,timeout,context=None):
  backend=self
  class Connection:
   def __init__(self):self.sock=Wire();self.closed=False;backend.connections.append(self)
   def connect(self):pass
   def request(self,method,path,headers):
    assert method=='GET'
    self.path=path;backend.requests.append((host,method,path,dict(headers),timeout,context))
   def getresponse(self):
    value=backend.routes[(host,self.path)]
    if isinstance(value,list):value=value.pop(0)
    if isinstance(value,Exception):raise value
    response=value() if callable(value) else copy.deepcopy(value)
    backend.responses.append(response);return response
   def close(self):
    self.closed=True
    if backend.close_error:raise OSError('SYNTHETIC_PRIVATE_ERROR')
  return Connection()
def diagnostic(mode='aggregate',ctx=None,clock=None,progress=False):
 return target.TransportDiagnostic('EXPECT_CARRIERS' if mode=='aggregate' else 'READ_ONLY_TRANSPORT_PREFLIGHT',ctx or CTX,clock,progress)
def reader(backend,mode='aggregate',ctx=None,clock=None,progress=False):
 value=target.TransportHTTP(ctx or CTX,TOKEN,diagnostic(mode,ctx,clock,progress),mode,clock)
 value._connection=backend.connection
 return value
def body(value):return json.dumps(value,separators=(',',':')).encode()
def source():
 baseline=Path(os.environ.get('PROJECT08_TEST_BASELINE_ROOT',str(ROOT)))
 return proof.source_data((ROOT/'tools/project08-hosted-profile.json').read_bytes(),(ROOT/'tools/project08_hosted.py').read_bytes(),
  (baseline/'tools/project08-sdk404-members.jsonl').read_bytes(),(baseline/'tools/package.py').read_bytes())
def job(rid='win-x64',run=222,job_id=501,commit=None):
 return {'id':job_id,'run_id':run,'run_attempt':1,'head_sha':commit or CTX['commit'],'name':'Native '+rid,'status':'completed','conclusion':'success'}
def native_fixture(src,rid,run):
 identity=proof.log_context(CTX['commit'],CTX['tree'],str(run),rid)
 token=lambda digit:'sha256:'+digit*64
 scope='job' if rid=='win-x64' else 'membership'
 kernel=({'mechanism':'windows-job','job':token('3'),'memoryBytes':2147483648,'processLimit':256,'cpuAffinity':3,'threadLimitClaim':False}
  if rid=='win-x64' else {'mechanism':'cgroup-v2','membership':token('3'),'limits':{'cpu.max':'200000 100000','memory.max':'2147483648','memory.swap.max':'0','pids.max':'256'}})
 facts={'tests':{'passed':74,'failed':0,'skipped':0,'observations':[{'name':name,'result':'pass'} for name in proof.TEST_NAMES]},
  'consumer':{'status':proof.CONSUMER_STATUS,'commit':CTX['commit'],'rid':rid,'checkCount':13,'checks':list(proof.CONSUMER_CHECKS),'manifestSha256':'4'*64,'consumerPid':token('1')},
  'kernel':kernel,'subprocessMembership':{'project':'08','nonce':token('2'),'pid':token('1'),'member':True,'mechanism':kernel['mechanism'],scope:token('3')},
  'terminal':{'project':'08','nonce':token('2'),'exitCode':0,'terminal':True}}
 encoded={key+'.json':body(facts[key]) for key in proof.FACTS}
 pin=src['profile']['inputs'][rid]
 document={'schema':'project08-native-proof-v1','identityEncoding':'project08-native-proof-identity-sha256-v1','commit':CTX['commit'],'sourceTree':CTX['tree'],
  'workflowRunId':run,'workflowRunAttempt':1,'rid':rid,'os':'Windows' if rid=='win-x64' else 'Linux','sdk':'10.0.404','runtime':'10.0.15','outcome':'pass',
  'fourCases':True,'offlineReleaseGuards':True,'kernelAdmitted':True,'terminal':True,
  'files':{key:{'path':key+'.json','sha256':hashlib.sha256(encoded[key+'.json']).hexdigest()} for key in proof.FACTS},
  'sourceEvidenceCommitmentEncoding':'sha256-private-phase-nonce-v1','sourceEvidenceHashes':{key:'5'*64 for key in proof.FACTS},
  'privateSdkInputCommitmentSha256':'6'*64,'profileSha256':src['profileSha256'],'adapterSha256':src['adapterSha256'],'limits':proof.LIMITS,
  'sdkInput':{'archive':pin['archive'],'archiveBytes':pin['bytes'],'archiveSha256':pin['sha256'],'archiveSha512':pin['sha512'],'memberManifestSha256':src['profile']['memberManifestSha256'],'regularFiles':pin['regularFiles'],'expandedBytes':pin['expandedBytes'],'hostSha256':pin['hostSha256'],'sdkOrAppExecuted':False,'terminal':True,'kernelAdmitted':True},
  'qualification':{'sdk':'10.0.404','runtime':'10.0.15','versionExitCode':0,'runtimeExitCode':0,'terminal':True,'kernelAdmitted':True,'invocations':2},
  'producer':{'phase':'package','commit':CTX['commit'],'sourceTree':CTX['tree'],'rid':rid,'terminal':True,'exitCode':0,'archive':proof.archive_name(rid),'archiveSha256':'8'*64,'archiveBytes':123,'manifestSha256':'4'*64,'packageHelperSha256':src['packageHelperSha256'],'payloadFiles':1},
  'offlineTests':{'success':True,'testsRun':7,'expectedCount':7,'expectedTestIds':list(proof.OFFLINE_TEST_IDS),'completedTestIds':list(proof.OFFLINE_TEST_IDS),'failed':0,'errors':0,'skipped':0}}
 files={'native-proof.json':body(document),**encoded}
 inventory=[{'name':proof.archive_name(rid),'bytes':123,'sha256':'8'*64}]+[{'name':name,'bytes':len(files[name]),'sha256':hashlib.sha256(files[name]).hexdigest()} for name in proof.PROOF_NAMES]
 handoff={'schema':'project08-same-run-handoff-v1','context':identity,'files':inventory,'rawBytes':sum(row['bytes'] for row in inventory),'nativeProofSha256':inventory[1]['sha256']}
 key=proof.handoff_key(handoff,identity)
 return files,proof.framed(files,identity,'native'),handoff,key
def add_log(routes,job_id,log):
 location='https://productionresultssa0.blob.core.windows.net/job-'+str(job_id)+'?sig=SYNTHETIC_SAS'
 routes[('api.github.com','/'+BASE+'jobs/'+str(job_id)+'/logs')]=Reply(302,headers=[('Location',location)])
 routes[('productionresultssa0.blob.core.windows.net','/job-'+str(job_id)+'?sig=SYNTHETIC_SAS')]=Reply(200,log)
def aggregate_fixture(src):
 routes={};env={'GITHUB_REF':REF};data={}
 jobs={'total_count':2,'jobs':[job(),job('linux-x64',job_id=502)]}
 routes[('api.github.com','/'+BASE+'runs/222/attempts/1/jobs?per_page=100')]=Reply(body=body(jobs))
 for index,rid in enumerate(('win-x64','linux-x64')):
  files,log,handoff,key=native_fixture(src,rid,222);p='WIN' if index==0 else 'LINUX'
  env[p+'_AVAILABLE']='true';env[p+'_COMMITMENT']=proof.encode_handoff(handoff)
  log+=('Cache saved with key: '+key+'\nCache found and can be restored from key: '+key+'\n').encode()
  add_log(routes,501+index,log)
  cache={'total_count':1,'actions_caches':[{'id':701+index,'key':key,'ref':REF if index==0 else 'refs/heads/'+REF,'version':'a'*64,'size_in_bytes':1024}]}
  path='/'+BASE+'caches?key='+key+'&per_page=100'
  routes[('api.github.com',path)]=Reply(body=body(cache))
  data[rid]={'files':files,'key':key,'cache_path':path,'cache':cache}
 return routes,env,data
def readiness_fixture(src):
 routes={};run={'id':111,'run_attempt':1,'head_sha':CTX['commit'],'head_branch':'main','event':'push','status':'completed','conclusion':'success','path':'.github/workflows/verify.yml','repository':{'full_name':target.HTTP_REPO}}
 runs_path='/'+BASE+'workflows/verify.yml/runs?branch=main&event=push&status=success&head_sha='+CTX['commit']+'&per_page=20'
 routes[('api.github.com',runs_path)]=Reply(body=body({'total_count':1,'workflow_runs':[run]}))
 jobs_path='/'+BASE+'runs/111/attempts/1/jobs?per_page=100'
 routes[('api.github.com',jobs_path)]=Reply(body=body({'total_count':2,'jobs':[job(run=111),job('linux-x64',111,502)]}))
 files,log,_,_=native_fixture(src,'win-x64',111);add_log(routes,501,log)
 usage_path='/'+BASE+'cache/usage';routes[('api.github.com',usage_path)]=Reply(body=body({'active_caches_size_in_bytes':145760489,'active_caches_count':4}))
 return routes,run,runs_path,jobs_path,usage_path,files
class SealedTest(unittest.TestCase):
 def setUp(self):
  self.real=[]
  def no_real(*args,**kwargs):self.real.append(1);raise RuntimeError('SYNTHETIC_PRIVATE_NO_REAL_OPERATION')
  self.patches=[patch.object(subprocess,'run',no_real),patch.object(subprocess,'Popen',no_real),patch.object(http.client,'HTTPSConnection',no_real),patch.object(socket,'create_connection',no_real)]
  for item in self.patches:item.start()
 def tearDown(self):
  for item in reversed(self.patches):item.stop()
  self.assertEqual(self.real,[])
 def failure(self,fn,d,stage=None,reason=None,status=None):
  out=io.StringIO();err=io.StringIO()
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
   try:fn()
   except Exception:d.record('ASSERTION');d.emit()
   else:self.fail('Expected bounded HOLD')
  value=d.first
  self.assertIsNotNone(value)
  if stage:self.assertEqual(value['stage'],stage)
  if reason:self.assertEqual(value['reason'],reason)
  if status is not None:self.assertEqual(value['httpStatus'],status)
  self.assertEqual(set(value),{'schema','version','operation','stage','reason','sourceSHA','workflowRunId','attempt','httpStatus'})
  self.assertTrue(len(out.getvalue().encode())<2048)
  self.assertNotIn('SYNTHETIC_PRIVATE',out.getvalue()+err.getvalue())
  self.assertNotIn('sig=',out.getvalue()+err.getvalue())
  self.assertNotIn('https://',out.getvalue()+err.getvalue())
  self.assertLessEqual(len(out.getvalue().split('PROJECT08_HTTP_DIAGNOSTIC ')[-1].encode()),1024)
  return value
class HTTPTests(SealedTest):
 def metadata(self,reply,clock=None,progress=False):
  endpoint=BASE+'runs/222/attempts/1/jobs?per_page=100'
  backend=Backend({('api.github.com','/'+endpoint):reply})
  value=reader(backend,clock=clock,progress=progress)
  return value,backend,endpoint
 def test_200_complete_no_content_length(self):
  value,backend,path=self.metadata(Reply(body=b'{"ok":true}',headers=[]))
  self.assertEqual(value.json(path),{'ok':True});self.assertTrue(all(c.closed for c in backend.connections))
  self.assertEqual(backend.requests[0][3]['Authorization'],'Bearer '+TOKEN)
 def test_declared_length_complete(self):
  value,_,path=self.metadata(Reply(body=b'{}'));self.assertEqual(value.json(path),{})
 def test_non200_no_body_or_retry(self):
  for status in (201,401,403,404,415,500):
   with self.subTest(status=status):
    value,backend,path=self.metadata(Reply(status,b'SYNTHETIC_PRIVATE_ERROR_BODY'))
    self.failure(lambda:value.get(path),value.diagnostic,'HTTP_STATUS','HTTP_STATUS',status)
    self.assertEqual(len(backend.requests),1);self.assertEqual(backend.responses[0].reads,0)
 def test_declared_length_bad_mismatch_truncated_limit(self):
  cases=[([('Content-Length','x')],b'{}','BODY_LENGTH'),([('Content-Length','1'),('Content-Length','1')],b'{}','BODY_LENGTH'),
   ([('Content-Length','1')],b'{}','BODY_LENGTH'),([('Content-Length','3')],b'{}','BODY_TRUNCATED'),
   ([('Content-Length',str(META+1))],b'','BODY_LIMIT')]
  for headers,payload,reason in cases:
   with self.subTest(reason=reason):
    value,_,path=self.metadata(Reply(body=payload,headers=headers))
    self.failure(lambda:value.get(path),value.diagnostic,reason=reason,status=200)
 def test_unknown_length_body_limit(self):
  value,_,path=self.metadata(Reply(body=b'123456789',headers=[]))
  self.failure(lambda:value.get(path,8),value.diagnostic,'BODY','BODY_LIMIT',200)
 def test_invalid_utf8_duplicate_nonfinite_json(self):
  for data in (b'\xff',b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'{'):
   with self.subTest(data=data):
    value,_,path=self.metadata(Reply(body=data))
    self.failure(lambda:value.json(path),value.diagnostic,'JSON','JSON_INVALID',200)
 def test_timeout_expiry_incomplete_and_transport(self):
  value,_,path=self.metadata(Reply(error=TimeoutError('SYNTHETIC_PRIVATE_TIMEOUT')))
  self.failure(lambda:value.get(path),value.diagnostic,'BODY','TIMEOUT',200)
  value,_,path=self.metadata(Reply(error=http.client.IncompleteRead(b'SYNTHETIC_PRIVATE')))
  self.failure(lambda:value.get(path),value.diagnostic,'BODY','BODY_TRUNCATED',200)
  value,backend,path=self.metadata(OSError('SYNTHETIC_PRIVATE_TRANSPORT'))
  self.failure(lambda:value.get(path),value.diagnostic,'API_REQUEST','HTTP_TRANSPORT')
  clock=Clock();value,_,path=self.metadata(Reply(onread=lambda:setattr(clock,'now',60.0)),clock)
  self.failure(lambda:value.get(path),value.diagnostic,reason='DEADLINE')
 def test_expired_before_request_and_call_cap(self):
  clock=Clock();value,backend,path=self.metadata(Reply(),clock);clock.now=60
  self.failure(lambda:value.get(path),value.diagnostic,reason='DEADLINE');self.assertEqual(backend.requests,[])
  value,backend,path=self.metadata(Reply())
  for _ in range(5):value.get(path)
  self.failure(lambda:value.get(path),value.diagnostic,reason='INPUT');self.assertEqual(len(backend.requests),5)
 def test_new_request_and_redirect_hop_status_is_not_stale(self):
  for error,reason in ((OSError('SYNTHETIC_PRIVATE_CONNECT'),'HTTP_TRANSPORT'),(TimeoutError('SYNTHETIC_PRIVATE_TIMEOUT'),'TIMEOUT')):
   value,backend,path=self.metadata(Reply())
   self.assertEqual(value.get(path),b'{}')
   def failed_connection(*args):raise error
   value._connection=failed_connection
   event=self.failure(lambda:value.get(path),value.diagnostic,'API_REQUEST',reason)
   self.assertIsNone(event['httpStatus']);self.assertEqual(len(backend.requests),1)
  value,backend,path=self.metadata(Reply());value.get(path)
  event=self.failure(lambda:value.get(path+'&invalid=1'),value.diagnostic,reason='INPUT')
  self.assertIsNone(event['httpStatus'])
  value,backend,path=self.log_reader('https://productionresultssa0.blob.core.windows.net/log?sig=SYNTHETIC_SAS')
  original=value._connection
  def failed_storage(host,timeout):
   if host!='api.github.com':raise OSError('SYNTHETIC_PRIVATE_STORAGE_CONNECT')
   return original(host,timeout)
  value._connection=failed_storage
  event=self.failure(lambda:value.get(path,32*1024*1024),value.diagnostic,'API_REQUEST','HTTP_TRANSPORT')
  self.assertIsNone(event['httpStatus'])
 def test_typed_fixed_endpoints_ids_keys_token(self):
  value,backend,path=self.metadata(Reply())
  for bad in ('https://api.github.com/'+path,'/'+path,path+'&other=1',path.replace('222','333'),'repos/foreign/repo/actions/cache/usage'):
   with self.subTest(path=bad):
    d=diagnostic();v=target.TransportHTTP(CTX,TOKEN,d);v._connection=backend.connection
    self.failure(lambda:v.get(bad),d,reason='INPUT')
  self.assertEqual(backend.requests,[])
  for token in ('',None,True,'bad\n'):
   d=diagnostic();self.failure(lambda:target.TransportHTTP(CTX,token,d),d,'TOKEN','TOKEN')
  for ctx in ({},dict(CTX,runAttempt=True),dict(CTX,runId=True),[]):
   d=diagnostic();self.failure(lambda:target.TransportHTTP(ctx,TOKEN,d),d,'INPUT','INPUT')
 def log_reader(self,location,status=302,storage=None,mode='aggregate'):
  path=BASE+'jobs/501/logs'
  routes={('api.github.com','/'+path):Reply(status,headers=[('Location',location),('Set-Cookie','SYNTHETIC_PRIVATE_COOKIE')])}
  if storage is not None:routes[('productionresultssa0.blob.core.windows.net','/log?sig=SYNTHETIC_SAS')]=storage
  backend=Backend(routes);value=reader(backend,mode)
  if mode=='readiness':value.bind_source_run(222)
  value.bind_job(job())
  return value,backend,path
 def test_one_redirect_no_auth_cookie(self):
  value,backend,path=self.log_reader('https://productionresultssa0.blob.core.windows.net/log?sig=SYNTHETIC_SAS',storage=Reply(body=b'original log'))
  # Observed API415 regression: log endpoint redirects only for API JSON Accept.
  location='https://productionresultssa0.blob.core.windows.net/log?sig=SYNTHETIC_SAS'
  def api_accept_response():
   if backend.requests[-1][3].get('Accept')!='application/vnd.github+json':
    return Reply(415,b'SYNTHETIC_PRIVATE_ERROR_BODY')
   return Reply(302,headers=[('Location',location)])
  backend.routes[('api.github.com','/'+path)]=api_accept_response
  self.assertEqual(value.get(path,32*1024*1024),b'original log')
  self.assertEqual(value.redirect_calls,1)
  self.assertEqual(backend.requests[0][3]['Accept'],'application/vnd.github+json')
  self.assertEqual(backend.requests[1][3]['Accept'],'application/octet-stream')
  self.assertIn('Authorization',backend.requests[0][3])
  self.assertNotIn('Cookie',backend.requests[0][3])
  self.assertNotIn('Authorization',backend.requests[1][3]);self.assertNotIn('Cookie',backend.requests[1][3])
 def test_redirect_rejects_host_userinfo_port_fragment_scheme_second(self):
  for url in ('http://productionresultssa0.blob.core.windows.net/log','https://evil.example/log','https://u@productionresultssa0.blob.core.windows.net/log','https://productionresultssa0.blob.core.windows.net:444/log','https://productionresultssa100.blob.core.windows.net/log','https://productionresultssa0.blob.core.windows.net/log#x','https://productionresultssa0.blob.core.windows.net/log\n'):
   with self.subTest(url=url):
    value,backend,path=self.log_reader(url)
    self.failure(lambda:value.get(path,32*1024*1024),value.diagnostic,'REDIRECT','REDIRECT',302)
    self.assertEqual(len(backend.requests),1)
  value,backend,path=self.log_reader('https://productionresultssa0.blob.core.windows.net/log?sig=SYNTHETIC_SAS',storage=Reply(302,headers=[('Location','https://evil.example/')]))
  self.failure(lambda:value.get(path,32*1024*1024),value.diagnostic,'REDIRECT','REDIRECT',302)
  self.assertEqual(len(backend.requests),2)
 def test_redirect_not_metadata_and_log_cap(self):
  value,backend,path=self.metadata(Reply(302,headers=[('Location','https://productionresultssa0.blob.core.windows.net/log')]))
  self.failure(lambda:value.get(path),value.diagnostic,'REDIRECT','REDIRECT',302)
  value,backend,path=self.log_reader('https://productionresultssa0.blob.core.windows.net/log?sig=SYNTHETIC_SAS',storage=Reply(headers=[('Content-Length',str(32*1024*1024+1))]))
  self.failure(lambda:value.get(path,32*1024*1024),value.diagnostic,reason='BODY_LIMIT')
 def test_cleanup_preserves_first_and_progress_is_only_enum(self):
  value,backend,path=self.metadata(Reply(403,b'SYNTHETIC_PRIVATE_BODY'),progress=True);backend.close_error=True
  event=self.failure(lambda:value.get(path),value.diagnostic,'HTTP_STATUS','HTTP_STATUS',403)
  self.assertEqual(event,value.diagnostic.first)
 def test_default_factory_verified_tls(self):
  endpoint=BASE+'runs/222/attempts/1/jobs?per_page=100'
  backend=Backend({('api.github.com','/'+endpoint):Reply()})
  context=types.SimpleNamespace(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
  with patch.object(target.ssl,'create_default_context',lambda:context),patch.object(target.http.client,'HTTPSConnection',backend.connection):
   value=target.TransportHTTP(CTX,TOKEN,diagnostic());self.assertEqual(value.get(endpoint),b'{}')
  self.assertIs(backend.requests[0][5],context)
 def test_timer_bound_and_restore_without_real_signal(self):
  calls=[];handlers={}
  fake=types.SimpleNamespace(SIGALRM=14,ITIMER_REAL=0,getitimer=lambda key:(0,0),getsignal=lambda key:'previous',
   signal=lambda key,value:handlers.__setitem__(key,value),setitimer=lambda *args:calls.append(args))
  value=target.TransportHTTP(CTX,TOKEN,diagnostic())
  with patch.object(target,'signal',fake):
   with target._hard_http_window(value):pass
  self.assertTrue(0<calls[0][1]<=60);self.assertEqual(calls[-1],(0,0));self.assertEqual(handlers[14],'previous')
 def test_entry_never_echoes_exception_or_invalid_argument(self):
  out=io.StringIO();err=io.StringIO()
  env={'GITHUB_SHA':CTX['commit'],'GITHUB_RUN_ID':'222','GITHUB_RUN_ATTEMPT':'1'}
  def bad(*args):raise RuntimeError('SYNTHETIC_PRIVATE_TOKEN https://bad/?sig=SYNTHETIC_SAS')
  with patch.dict(os.environ,env),patch.object(sys,'argv',['check_release.py','transport','expect-carriers']),patch.object(target,'transport_main',bad),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
   self.assertEqual(target._entry(),1)
  self.assertNotIn('SYNTHETIC_PRIVATE',out.getvalue()+err.getvalue());self.assertNotIn('sig=',out.getvalue()+err.getvalue())
  self.assertIn('PROJECT08_HTTP_DIAGNOSTIC',out.getvalue())
class ConsumingPathTests(SealedTest):
 @classmethod
 def setUpClass(cls):cls.source=source()
 def aggregate(self,routes=None,env=None):
  original,environment,data=aggregate_fixture(self.source);backend=Backend(routes or original)
  return reader(backend),backend,env or environment,data
 def test_synthetic_v4_five_response_whole_aggregate(self):
  value,backend,env,data=self.aggregate();outputs={}
  with tempfile.TemporaryDirectory() as directory:
   private=Path(directory)/'expected'
   target.expect_carriers(proof,CTX,self.source,env,private,lambda k,v:outputs.__setitem__(k,v),value)
   self.assertEqual(set(outputs),{'win_key','linux_key'})
   self.assertEqual({p.name for p in private.iterdir()},{'win-x64.json','linux-x64.json'})
  self.assertEqual(value.api_calls,5);self.assertEqual(value.redirect_calls,2);self.assertEqual(len(backend.requests),7)
 def test_first_existing_guards_outputs_handoff_jobs_run_save_frame(self):
  for kind in ('outputs','handoff','jobs','run','save','frame'):
   routes,env,data=aggregate_fixture(self.source)
   if kind=='outputs':env['WIN_AVAILABLE']='false'
   if kind=='handoff':env['WIN_COMMITMENT']='bad'
   if kind in ('jobs','run'):
    key=('api.github.com','/'+BASE+'runs/222/attempts/1/jobs?per_page=100');obj=json.loads(routes[key].body)
    if kind=='jobs':obj['jobs']=[];obj['total_count']=0
    else:obj['jobs'][0]['head_sha']='f'*40
    routes[key]=Reply(body=body(obj))
   if kind in ('save','frame'):
    key=('productionresultssa0.blob.core.windows.net','/job-501?sig=SYNTHETIC_SAS')
    log=routes[key].body
    log=log.replace(b'Cache saved with key:',b'NOT saved with key:') if kind=='save' else log.replace(b'P08F1 ',b'BADF1 ',1)
    routes[key]=Reply(body=log)
   value,backend,env,_=self.aggregate(routes,env)
   with tempfile.TemporaryDirectory() as directory:
    self.failure(lambda:target.expect_carriers(proof,CTX,self.source,env,Path(directory)/'expected',lambda *args:None,value),value.diagnostic,
     {'outputs':'OUTPUTS','handoff':'HANDOFF','jobs':'JOBS','run':'RUN','save':'SAVE','frame':'LOG_FRAME'}[kind])
 def test_precise_cache_key_ref_version_size_guards(self):
  for field,bad,stage in (('key','foreign','CACHE_KEY'),('ref','refs/tags/v0.1.0-preview.3','CACHE_REF'),('version','bad','CACHE_VERSION'),('size_in_bytes',True,'CACHE_SIZE'),('size_in_bytes',56*1024*1024+1,'CACHE_SIZE')):
   routes,env,data=aggregate_fixture(self.source);path=data['win-x64']['cache_path'];cache=copy.deepcopy(data['win-x64']['cache']);cache['actions_caches'][0][field]=bad
   routes[('api.github.com',path)]=Reply(body=body(cache))
   value,_,env,_=self.aggregate(routes,env)
   with tempfile.TemporaryDirectory() as directory:
    self.failure(lambda:target.expect_carriers(proof,CTX,self.source,env,Path(directory)/'expected',lambda *args:None,value),value.diagnostic,stage,status=200)
 def test_missing_and_ambiguous_cache_first_stage(self):
  for kind in ('missing','ambiguous'):
   routes,env,data=aggregate_fixture(self.source)
   cache=copy.deepcopy(data['win-x64']['cache'])
   if kind=='missing':cache={'total_count':0,'actions_caches':[]}
   else:cache['actions_caches'].append(copy.deepcopy(cache['actions_caches'][0]));cache['total_count']=2
   routes[('api.github.com',data['win-x64']['cache_path'])]=Reply(body=body(cache))
   value,_,env,_=self.aggregate(routes,env)
   with tempfile.TemporaryDirectory() as directory:
    self.failure(lambda:target.expect_carriers(proof,CTX,self.source,env,Path(directory)/'expected',lambda *args:None,value),value.diagnostic,'CACHE_KEY',status=200)
 def test_statewrite_and_existing_state_are_observable(self):
  value,backend,env,_=self.aggregate()
  with tempfile.TemporaryDirectory() as directory:
   private=Path(directory)/'expected';private.mkdir()
   self.failure(lambda:target.expect_carriers(proof,CTX,self.source,env,private,lambda *args:None,value),value.diagnostic,'STATE_WRITE')
   self.assertEqual(backend.requests,[])
  value,_,env,_=self.aggregate()
  with tempfile.TemporaryDirectory() as directory,patch.object(Path,'open',side_effect=OSError('SYNTHETIC_PRIVATE_PATH')):
   self.failure(lambda:target.expect_carriers(proof,CTX,self.source,env,Path(directory)/'expected',lambda *args:None,value),value.diagnostic,'STATE_WRITE')
 def readiness(self,routes=None):
  original,*metadata=readiness_fixture(self.source);backend=Backend(routes or original)
  return reader(backend,'readiness'),backend,metadata
 def test_synthetic_v4_readiness_original_source_frames_no_writes(self):
  value,backend,_=self.readiness()
  env={'GITHUB_REF':REF,'GITHUB_EVENT_NAME':'push','GITHUB_JOB':'ci_policy'}
  self.assertTrue(target.transport_readiness(proof,CTX,self.source,env,value))
  self.assertEqual(value.api_calls,4);self.assertEqual(value.redirect_calls,1);self.assertEqual(len(backend.requests),5)
  self.assertIsNone(value.diagnostic.first)
 def test_readiness_missing_ambiguous_foreign_run(self):
  for kind in ('missing','ambiguous','source','attempt','workflow','repository'):
   routes,run,path,_,_,_=readiness_fixture(self.source);obj={'total_count':1,'workflow_runs':[run]}
   if kind=='missing':obj={'total_count':0,'workflow_runs':[]}
   elif kind=='ambiguous':obj={'total_count':2,'workflow_runs':[run,dict(run,id=112)]}
   else:run[{'source':'head_sha','attempt':'run_attempt','workflow':'path','repository':'repository'}[kind]]={'source':'f'*40,'attempt':True,'workflow':'other.yml','repository':{'full_name':'foreign/repo'}}[kind]
   routes[('api.github.com',path)]=Reply(body=body(obj));value,backend,_=self.readiness(routes)
   self.failure(lambda:target.transport_readiness(proof,CTX,self.source,{'GITHUB_REF':REF,'GITHUB_EVENT_NAME':'push','GITHUB_JOB':'ci_policy'},value),value.diagnostic,'RUN')
   self.assertEqual(value.api_calls,1)
 def test_readiness_missing_duplicate_foreign_job_and_pruned_log(self):
  for kind in ('missing','duplicate','source','pruned'):
   routes,run,_,path,_,_=readiness_fixture(self.source);obj=json.loads(routes[('api.github.com',path)].body)
   if kind=='missing':obj={'total_count':0,'jobs':[]}
   elif kind=='duplicate':obj['jobs'].append(copy.deepcopy(obj['jobs'][0]));obj['total_count']=3
   elif kind=='source':obj['jobs'][0]['head_sha']='f'*40
   routes[('api.github.com',path)]=Reply(body=body(obj))
   if kind=='pruned':routes[('api.github.com','/'+BASE+'jobs/501/logs')]=Reply(404,b'SYNTHETIC_PRIVATE_BODY')
   value,_,_=self.readiness(routes)
   self.failure(lambda:target.transport_readiness(proof,CTX,self.source,{'GITHUB_REF':REF,'GITHUB_EVENT_NAME':'push','GITHUB_JOB':'ci_policy'},value),value.diagnostic,
    'HTTP_STATUS' if kind=='pruned' else 'RUN' if kind=='source' else 'JOBS')
 def test_readiness_cache_permission_and_typed_usage(self):
  for kind in ('permission','type','limit'):
   routes,_,_,_,path,_=readiness_fixture(self.source)
   routes[('api.github.com',path)]=Reply(403,b'SYNTHETIC_PRIVATE_BODY') if kind=='permission' else Reply(body=body({'active_caches_size_in_bytes':True if kind=='type' else 450*1024*1024+1,'active_caches_count':4}))
   value,_,_=self.readiness(routes)
   self.failure(lambda:target.transport_readiness(proof,CTX,self.source,{'GITHUB_REF':REF,'GITHUB_EVENT_NAME':'push','GITHUB_JOB':'ci_policy'},value),value.diagnostic,'HTTP_STATUS' if kind=='permission' else 'CACHE_SIZE')
 def test_source_and_pr_cli_never_construct_reader_or_read_token(self):
  for ref,event in (('refs/heads/main','push'),('refs/pull/1/merge','pull_request')):
   env={'GITHUB_REF':ref,'GITHUB_EVENT_NAME':event,'GITHUB_JOB':'ci_policy','GITHUB_RUN_ATTEMPT':'1','RUNNER_DEBUG':''}
   stub=types.SimpleNamespace(context=lambda:({},CTX,Path('unused')))
   class GuardedEnvironment(dict):
    def get(self,key,default=None):
     if key=='GH_TOKEN':raise AssertionError('token must not be read')
     return super().get(key,default)
   with patch.object(target.os,'environ',GuardedEnvironment(env)),patch.dict(sys.modules,{'project08_hosted':stub}),patch.object(proof,'source_at_root',lambda root:self.source),patch.object(target,'TransportHTTP',side_effect=AssertionError('reader must not exist')):
    target.transport_main(['transport-readiness'])
 @unittest.skipUnless(os.environ.get('P08_HISTORICAL_TAG3_FIXTURES'),'private historical capture not supplied; synthetic tests only')
 def test_historical_tag3_five_captured_bodies_old_unchanged_validators(self):
  directory=Path(os.environ['P08_HISTORICAL_TAG3_FIXTURES'])
  legacy=Path(os.environ['P08_HISTORICAL_TAG3_VALIDATORS'])
  active=Path(os.environ['PROJECT08_TEST_BASELINE_ROOT'])
  spec=importlib.util.spec_from_file_location('p08_old_tag3_proof',legacy/'tools/project08_hosted_proof.py');oldproof=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldproof)
  captured_jobs=json.loads((directory/'actual-attempt1-jobs.private.json').read_text(encoding='utf-8'))
  contexts=json.loads((directory/'win-x64/native-proof.json').read_text(encoding='utf-8'))
  oldctx=dict(CTX,commit=contexts['commit'],tree=contexts['sourceTree'],runId=str(contexts['workflowRunId']),runAttempt='1',root=str(active))
  failure=(directory/'failure-132563567911.log').read_text(encoding='utf-8')
  env={'GITHUB_JOB':'release','GITHUB_RUN_ATTEMPT':'1','GITHUB_REF':'refs/tags/v0.1.0-preview.3','GITHUB_EVENT_NAME':'push','RUNNER_DEBUG':''}
  for name in ('WIN_COMMITMENT','LINUX_COMMITMENT','WIN_AVAILABLE','LINUX_AVAILABLE'):
   matches=re.findall(r'^.*Z\s+'+name+r': ([A-Za-z0-9+/=]+)$',failure,re.M);self.assertEqual(len(matches),1);env[name]=matches[0]
  routes={};endpoints=[]
  jobs_path=BASE+'runs/'+oldctx['runId']+'/attempts/1/jobs?per_page=100'
  routes[('api.github.com','/'+jobs_path)]=Reply(body=(directory/'actual-attempt1-jobs.private.json').read_bytes())
  for rid in ('win-x64','linux-x64'):
   metadata=json.loads((directory/(rid+'-key-cache.private.json')).read_text(encoding='utf-8'))
   cachekey=metadata['actions_caches'][0]['key']
   routes[('api.github.com','/'+BASE+'caches?key='+cachekey+'&per_page=100')]=Reply(body=(directory/(rid+'-key-cache.private.json')).read_bytes())
   row=next(j for j in captured_jobs['jobs'] if j['name']=='Native '+rid)
   add_log(routes,row['id'],(directory/(rid+'-job.log')).read_bytes())
  backend=Backend(routes);value=reader(backend,ctx=oldctx)
  def bridge(endpoint,limit):
   endpoints.append(endpoint)
   if re.search(r'/jobs/[0-9]+/logs$',endpoint):
    identifier=int(endpoint.rsplit('/',2)[1]);value.bind_job(next(j for j in captured_jobs['jobs'] if j['id']==identifier))
   if '/caches?key=' in endpoint:value.bind_key(endpoint.split('?key=',1)[1].split('&',1)[0])
   return value.get(endpoint,limit)
  # Exactly the old transport-body seam is replaced; every old validator/statement stays.
  tree=ast.parse((legacy/'tools/check_release.py').read_text(encoding='utf-8'))
  class Swap(ast.NodeTransformer):
   def visit_FunctionDef(self,node):
    if node.name=='gh_private':node.body=ast.parse('return _bridge(endpoint,limit)').body;return node
    return self.generic_visit(node)
  tree=ast.fix_missing_locations(Swap().visit(tree))
  namespace={'__name__':'p08_historical_tag3_release','__file__':str(legacy/'tools/check_release.py'),'_bridge':bridge}
  exec(compile(tree,'<unchanged-tag3-validator-with-new-reader-seam>','exec'),namespace)
  namespace['ROOT']=active
  stub=types.SimpleNamespace(context=lambda:({},oldctx,Path('unused')))
  with tempfile.TemporaryDirectory() as temporary:
   env.update(RUNNER_TEMP=temporary,GITHUB_OUTPUT=str(Path(temporary)/'outputs'))
   with patch.dict(os.environ,env),patch.dict(sys.modules,{'project08_hosted_proof':oldproof,'project08_hosted':stub}):
    namespace['transport_main'](['expect-carriers'])
   self.assertTrue((Path(temporary)/'outputs').is_file())
  prior=json.loads((directory/'OFFLINE-AGGREGATE-REPLAY-02.json').read_text(encoding='utf-8'))
  self.assertEqual(endpoints,prior['calls']);self.assertEqual(value.api_calls,5);self.assertEqual(value.redirect_calls,2)
  self.assertEqual(namespace['ROOT'],active)
if __name__=='__main__':unittest.main()
