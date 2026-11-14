"""Draft-list/ID reader only. Mocked I/O; no SDK/native/network or release mutation."""
import contextlib,copy,http.client,importlib.util,io,json,os,socket,ssl,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('project08_draft_metadata',ROOT/'tools/project08_draft_metadata.py')
target=importlib.util.module_from_spec(spec);spec.loader.exec_module(target)
LIST='repos/'+target.REPO+'/releases?per_page=10&page='
def release(aid=445623737):
 assets=[]
 for index,name in enumerate(sorted(target.NAMES)):
  assets.append({'id':748900000+index,'name':name,'size':112 if name=='SIGNING-PUBLIC-KEY.pub' else 376 if name=='SHA256SUMS.txt' else 1000,'digest':'sha256:'+(target.KEY_SHA if name=='SIGNING-PUBLIC-KEY.pub' else 'a'*64),'state':'uploaded','ignored_url':'PRIVATE_UNUSED'})
 return {'id':aid,'tag_name':target.TAG,'draft':True,'prerelease':True,'assets':assets,'private_unused':'PRIVATE_UNUSED'}
class Fetch:
 def __init__(self,listed=None,actual=None):self.listed=[release()] if listed is None else listed;self.actual=release() if actual is None else actual;self.calls=[]
 def __call__(self,path):
  self.calls.append(path)
  if path==LIST+'1':return copy.deepcopy(self.listed)
  if path==LIST+'2':return []
  if path=='repos/'+target.REPO+'/releases/445623737':return copy.deepcopy(self.actual)
  raise AssertionError('Unexpected endpoint')
class Reply:
 def __init__(self,status=200,body=b'[]',headers=None,error=None):
  self.status=status;self.body=body;self.pos=0;self.reads=0;self.error=error;self.headers=[('Content-Length',str(len(body)))] if headers is None else headers
 def getheaders(self):return self.headers
 def read(self,size):
  self.reads+=1
  if self.error:raise self.error
  data=self.body[self.pos:self.pos+size];self.pos+=len(data);return data
class Wire:
 def settimeout(self,value):assert 0<value<=10
class Connection:
 def __init__(self,reply):self.reply=reply;self.sock=Wire();self.requests=[];self.closed=False
 def connect(self):pass
 def request(self,method,path,headers):self.requests.append((method,path,headers))
 def getresponse(self):return self.reply
 def close(self):self.closed=True
class Tests(unittest.TestCase):
 def setUp(self):
  self.real=[]
  def forbidden(*a,**k):self.real.append(1);raise AssertionError('Real operation forbidden')
  self.patches=[patch.object(socket,'create_connection',forbidden),patch.object(http.client,'HTTPSConnection',forbidden),patch.object(subprocess,'run',forbidden),patch.object(subprocess,'Popen',forbidden)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.assertEqual(self.real,[])
 def held(self,fn,code=None):
  with self.assertRaises(target.Hold) as caught:fn()
  if code:self.assertEqual(caught.exception.code,code)
  return caught.exception
 def reader(self,reply):
  reader=target.Reader('SYNTHETIC_PRIVATE_TOKEN');connection=Connection(reply);reader.connection=lambda:connection
  return reader,connection
 def test_unique_list_then_id_filtered(self):
  fetch=Fetch();actual=target.lookup(fetch,expected_id=445623737)
  self.assertEqual(actual['id'],445623737);self.assertEqual(len(actual['assets']),5)
  self.assertNotIn('private_unused',actual);self.assertTrue(all('ignored_url' not in a for a in actual['assets']))
  self.assertEqual(fetch.calls,[LIST+'1','repos/'+target.REPO+'/releases/445623737'])
  self.assertTrue(all('/releases/tags/' not in path for path in fetch.calls))
 def test_second_page_exhaustive(self):
  others=[{'id':i+1,'tag_name':'old'+str(i)} for i in range(10)]
  calls=[]
  def fetch(path):
   calls.append(path)
   return others if path==LIST+'1' else [release()] if path==LIST+'2' else release()
  self.assertEqual(target.lookup(fetch)['id'],445623737);self.assertEqual(len(calls),3)
 def test_missing_and_ambiguous(self):
  self.held(lambda:target.lookup(Fetch([])),'NOT_FOUND')
  self.held(lambda:target.lookup(Fetch([release(),release(2)])),'AMBIGUOUS')
 def test_pagination_exhaustion(self):
  self.held(lambda:target.lookup(lambda p:[{'tag_name':'old'}]*10),'PAGINATION')
 def test_release_type_state_and_id(self):
  for key,value in [('id',True),('tag_name','v0.1.0-preview.4'),('draft',False),('prerelease',False),('assets',{})]:
   with self.subTest(key=key):
    bad=release();bad[key]=value
    self.held(lambda:target.filtered(bad))
  self.held(lambda:target.lookup(Fetch(),expected_id=True),'INPUT')
 def test_assets_strict_and_unique(self):
  for key,value in [('id',True),('name','foreign.zip'),('size',True),('size',64*1048576),('digest','sha256:bad'),('state','new')]:
   with self.subTest(key=key):
    bad=release();bad['assets'][0][key]=value;self.held(lambda:target.filtered(bad),'ASSET')
  for field in ('name','id'):
   bad=release();bad['assets'][1][field]=bad['assets'][0][field];self.held(lambda:target.filtered(bad),'ASSET')
  bad=release();next(a for a in bad['assets'] if a['name']=='SIGNING-PUBLIC-KEY.pub')['digest']='sha256:'+'b'*64;self.held(lambda:target.filtered(bad),'ASSET')
 def test_id_snapshot_drift(self):
  self.held(lambda:target.lookup(Fetch(),expected_id=1),'DRIFT')
  bad=release();bad['assets'][0]['size']+=1;self.held(lambda:target.lookup(Fetch(actual=bad)),'DRIFT')
 def test_stage_identity_and_hashes(self):
  r=release();stage={'tag':target.TAG,'commit':'c'*40,'sourceTree':'d'*40,'assets':{a['name']:{'bytes':a['size'],'sha256':a['digest'][7:]} for a in r['assets']}}
  self.assertEqual(target.lookup(Fetch(),stage=stage)['id'],r['id'])
  for field,value in [('commit','bad'),('sourceTree',True),('tag','v0.1.0-preview.4'),('assets',{})]:
   bad=dict(stage);bad[field]=value;self.held(lambda:target.lookup(Fetch(),stage=bad),'STAGE')
  bad=copy.deepcopy(stage);bad['assets'][r['assets'][0]['name']]['sha256']='0'*64;self.held(lambda:target.lookup(Fetch(),stage=bad),'STAGE')
 def test_duplicate_invalid_and_nonfinite_json(self):
  for body in (b'{"id":1,"id":2}',b'{"x":NaN}',b'\xff',b'{'):
   self.held(lambda:target.loads(body),'JSON')
 def test_api_headers_method_complete_body(self):
  r,c=self.reader(Reply(body=b'[]'));self.assertEqual(r.get(LIST+'1'),[])
  method,path,headers=c.requests[0]
  self.assertEqual((method,path),('GET','/'+LIST+'1'))
  self.assertEqual(headers['Accept'],'application/vnd.github+json');self.assertIn('Authorization',headers)
  self.assertNotIn('Cookie',headers);self.assertTrue(c.closed)
 def test_non200_redirect_no_retry_or_error_body(self):
  for status in (301,302,401,403,404,415,500):
   reply=Reply(status,b'SYNTHETIC_PRIVATE_RESPONSE');r,c=self.reader(reply)
   hold=self.held(lambda:r.get(LIST+'1'),'HTTP')
   self.assertEqual(hold.status,status);self.assertEqual(reply.reads,0);self.assertEqual(len(c.requests),1)
 def test_body_length_limit_and_incomplete(self):
  cases=[Reply(body=b'[]',headers=[('Content-Length','3')]),Reply(body=b'[]',headers=[('Content-Length','1')]),Reply(body=b'[]',headers=[('Content-Length','2'),('Content-Length','2')]),Reply(body=b'[]',headers=[('Content-Length',str(target.LIMIT+1))]),Reply(body=b'X'*(target.LIMIT+1),headers=[]),Reply(error=http.client.IncompleteRead(b'x',2))]
  for reply in cases:
   r,_=self.reader(reply);self.held(lambda:r.get(LIST+'1'),'BODY')
  r,_=self.reader(Reply(body=b'[]',headers=[]));self.assertEqual(r.get(LIST+'1'),[])
 def test_timeout_deadline_and_call_bound(self):
  r,_=self.reader(Reply(error=TimeoutError()));self.held(lambda:r.get(LIST+'1'),'TIMEOUT')
  r=target.Reader('synthetic',clock=lambda:0);r.clock=lambda:61;self.held(r.remaining,'DEADLINE')
  r,_=self.reader(Reply());r.calls=3;self.held(lambda:r.get(LIST+'1'),'INPUT')
 def test_foreign_endpoints_and_token(self):
  for endpoint in ('https://evil.test','repos/foreign/repo/releases?per_page=10&page=1','repos/'+target.REPO+'/releases/tags/'+target.TAG,LIST+'3','repos/'+target.REPO+'/releases/-1'):
   r,c=self.reader(Reply());self.held(lambda:r.get(endpoint),'INPUT');self.assertFalse(c.requests)
  for token in (None,'','secret\n',True):self.held(lambda:target.Reader(token),'AUTH')
 def test_default_tls_factory(self):
  calls=[]
  with patch.object(http.client,'HTTPSConnection',lambda *a,**k:calls.append((a,k)) or 'INERT'):
   r=target.Reader('synthetic');self.assertEqual(r.connection(),'INERT')
  args,kwargs=calls[0];self.assertEqual(args[0],'api.github.com');self.assertTrue(kwargs['context'].check_hostname);self.assertEqual(kwargs['context'].verify_mode,ssl.CERT_REQUIRED)
 def test_cli_collision_private_error_and_bad_tag(self):
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)/'metadata.json';path.write_text('keep')
   with patch.dict(os.environ,{'RUNNER_TEMP':temporary,'GH_TOKEN':'SYNTHETIC_PRIVATE_TOKEN'}):
    out=io.StringIO()
    with contextlib.redirect_stdout(out):code=target.main(['--tag',target.TAG,'--output',str(path)])
    self.assertEqual(code,1);self.assertEqual(path.read_text(),'keep');self.assertNotIn('SYNTHETIC_PRIVATE',out.getvalue())
    with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(target.main(['--tag','foreign','--output',str(path)]),1)
 def test_cli_filtered_output_and_positive(self):
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)/'metadata.json';fake=type('R',(),{'get':staticmethod(Fetch())})
   with patch.dict(os.environ,{'RUNNER_TEMP':temporary,'GH_TOKEN':'synthetic'}),patch.object(target,'Reader',lambda t:fake()),patch.object(target,'window',lambda r:contextlib.nullcontext()):
    out=io.StringIO()
    with contextlib.redirect_stdout(out):code=target.main(['--tag',target.TAG,'--output',str(path),'--expected-id','445623737'])
    self.assertEqual(code,0);self.assertEqual(json.loads(path.read_text()),target.filtered(release()));self.assertNotIn('PRIVATE_UNUSED',out.getvalue())
if __name__=='__main__':unittest.main()

