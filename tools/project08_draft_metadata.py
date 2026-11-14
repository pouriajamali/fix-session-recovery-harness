"""Bounded read-only draft metadata lookup. CI Ubuntu tooling; never publishes."""
import argparse,contextlib,hashlib,http.client,json,os,re,signal,ssl,sys,time
from pathlib import Path
REPO='pouriajamali/fix-session-recovery-harness'
TAG='v0.1.0-preview.5'
PREFIX='fix-session-recovery-harness-'+TAG
NAMES={PREFIX+'-win-x64.zip',PREFIX+'-linux-x64.tar.gz',PREFIX+'-source.zip','SHA256SUMS.txt','SIGNING-PUBLIC-KEY.pub'}
KEY_SHA='a59fbecc53a0b3109212b70a3a51247dbd3529512d189ac2462a27a057dad671'
LIMIT=131072
CODES={'INPUT','AUTH','HTTP','TIMEOUT','BODY','JSON','PAGINATION','NOT_FOUND','AMBIGUOUS','RELEASE','ASSET','DRIFT','STAGE','OUTPUT','DEADLINE'}
class Hold(Exception):
 def __init__(self,code,status=None):
  assert code in CODES
  self.code=code;self.status=status if type(status) is int and 100<=status<=599 else None
def need(value,code):
 if not value:raise Hold(code)
def positive(value):return type(value) is int and 0<value<10**20
def unique(pairs):
 out={}
 for key,value in pairs:
  need(key not in out,'JSON');out[key]=value
 return out
def loads(raw):
 need(type(raw) is bytes and len(raw)<=LIMIT,'BODY')
 def bad(value):raise Hold('JSON')
 try:return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=bad)
 except Hold:raise
 except Exception:raise Hold('JSON') from None
def limit_for(name):
 return 1048576 if name.endswith('-source.zip') else 48*1048576 if name.endswith(('-win-x64.zip','-linux-x64.tar.gz')) else 16384
def filtered(value,tag=TAG):
 need(type(tag) is str and tag==TAG and type(value) is dict,'RELEASE')
 need(positive(value.get('id')) and value.get('tag_name')==tag and value.get('draft') is True and value.get('prerelease') is True,'RELEASE')
 assets=value.get('assets');need(type(assets) is list and len(assets)==5,'ASSET')
 names=set();ids=set();result=[]
 for asset in assets:
  need(type(asset) is dict,'ASSET');name=asset.get('name');aid=asset.get('id')
  need(type(name) is str and name in NAMES and name not in names and positive(aid) and aid not in ids,'ASSET')
  size=asset.get('size');digest=asset.get('digest')
  need(type(size) is int and 0<size<=limit_for(name) and asset.get('state')=='uploaded','ASSET')
  need(type(digest) is str and re.fullmatch('sha256:[0-9a-f]{64}',digest) is not None,'ASSET')
  if name=='SIGNING-PUBLIC-KEY.pub':need(digest=='sha256:'+KEY_SHA,'ASSET')
  names.add(name);ids.add(aid);result.append({key:asset[key] for key in ('id','name','size','digest','state')})
 need(names==NAMES,'ASSET')
 return {'id':value['id'],'tag_name':tag,'draft':True,'prerelease':True,'assets':sorted(result,key=lambda item:item['name'])}
def lookup(fetch,tag=TAG,expected_id=None,stage=None):
 need(type(tag) is str and tag==TAG,'INPUT')
 need(expected_id is None or positive(expected_id),'INPUT')
 rows=[];complete=False
 for page in (1,2):
  batch=fetch('repos/'+REPO+'/releases?per_page=10&page='+str(page))
  need(type(batch) is list and len(batch)<=10 and all(type(row) is dict for row in batch),'PAGINATION')
  rows.extend(batch)
  if len(batch)<10:complete=True;break
 need(complete,'PAGINATION')
 selected=[row for row in rows if row.get('tag_name')==tag]
 need(len(selected)>0,'NOT_FOUND');need(len(selected)==1,'AMBIGUOUS')
 selected=filtered(selected[0],tag)
 if expected_id is not None:need(selected['id']==expected_id,'DRIFT')
 actual=filtered(fetch('repos/'+REPO+'/releases/'+str(selected['id'])),tag)
 need(actual==selected,'DRIFT')
 if stage is not None:
  need(type(stage) is dict and stage.get('tag')==tag and type(stage.get('assets')) is dict,'STAGE')
  need(set(stage['assets'])==NAMES,'STAGE')
  need(type(stage.get('commit')) is str and re.fullmatch('[0-9a-f]{40}',stage['commit']) is not None,'STAGE')
  need(type(stage.get('sourceTree')) is str and re.fullmatch('[0-9a-f]{40}',stage['sourceTree']) is not None,'STAGE')
  for item in actual['assets']:
   expected=stage['assets'][item['name']]
   need(type(expected) is dict and type(expected.get('bytes')) is int and expected['bytes']==item['size'] and item['digest']=='sha256:'+str(expected.get('sha256')),'STAGE')
 return actual
class Reader:
 def __init__(self,token,clock=time.monotonic):
  need(type(token) is str and 0<len(token)<=8192 and all(32<ord(c)<127 for c in token),'AUTH')
  self.token=token;self.clock=clock;self.deadline=clock()+60;self.calls=0;self.total=0
 def remaining(self):
  left=self.deadline-self.clock();need(left>0,'DEADLINE');return min(10,left)
 def connection(self):
  context=ssl.create_default_context();need(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED,'HTTP')
  return http.client.HTTPSConnection('api.github.com',timeout=self.remaining(),context=context)
 def get(self,endpoint):
  allowed=(re.fullmatch(re.escape('repos/'+REPO+'/releases')+r'\?per_page=10&page=[12]',endpoint) or re.fullmatch(re.escape('repos/'+REPO+'/releases/')+r'[1-9][0-9]{0,19}',endpoint)) if type(endpoint) is str else None
  need(allowed and self.calls<3,'INPUT');self.calls+=1;connection=None
  try:
   connection=self.connection();connection.connect();wire=connection.sock;wire.settimeout(self.remaining())
   connection.request('GET','/'+endpoint,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+self.token,'X-GitHub-Api-Version':'2026-03-10','User-Agent':'project08-draft-metadata-reader'})
   wire.settimeout(self.remaining());response=connection.getresponse();self.remaining()
   if response.status!=200:raise Hold('HTTP',response.status)
   headers=response.getheaders();need(len(headers)<=100 and sum(len(k)+len(v) for k,v in headers)<=16384,'BODY')
   lengths=[v for k,v in headers if k.lower()=='content-length'];need(len(lengths)<=1,'BODY');declared=None
   if lengths:
    need(type(lengths[0]) is str and re.fullmatch('[0-9]{1,12}',lengths[0]) is not None,'BODY');declared=int(lengths[0]);need(declared<=LIMIT,'BODY')
   parts=[];size=0
   while True:
    wire.settimeout(self.remaining());part=response.read(min(65536,LIMIT-size+1));self.remaining()
    need(type(part) is bytes,'BODY')
    if not part:break
    size+=len(part);need(size<=LIMIT and (declared is None or size<=declared),'BODY');parts.append(part)
   need(declared is None or size==declared,'BODY');self.total+=size;need(self.total<=3*LIMIT,'BODY')
   return loads(b''.join(parts))
  except Hold:raise
  except (TimeoutError,):raise Hold('TIMEOUT') from None
  except http.client.IncompleteRead:raise Hold('BODY') from None
  except Exception:raise Hold('HTTP') from None
  finally:
   if connection is not None:
    try:connection.close()
    except Exception:pass
@contextlib.contextmanager
def window(reader):
 need(all(hasattr(signal,n) for n in ('SIGALRM','ITIMER_REAL','setitimer','getitimer')),'DEADLINE')
 oldtimer=signal.getitimer(signal.ITIMER_REAL);need(oldtimer==(0.0,0.0),'DEADLINE')
 oldhandler=signal.getsignal(signal.SIGALRM)
 def expired(signum,frame):raise Hold('DEADLINE')
 signal.signal(signal.SIGALRM,expired)
 try:
  signal.setitimer(signal.ITIMER_REAL,max(.001,reader.deadline-reader.clock()));yield;reader.remaining()
 finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,oldhandler)
class Parser(argparse.ArgumentParser):
 def error(self,message):raise Hold('INPUT')
def main(argv=None):
 try:
  parser=Parser();parser.add_argument('--tag',required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--stage-input',type=Path);parser.add_argument('--expected-id',type=int);args=parser.parse_args(argv)
  need(args.tag==TAG,'INPUT')
  output=args.output
  temporary=Path(os.environ.get('RUNNER_TEMP',''))
  need(bool(os.environ.get('RUNNER_TEMP')) and temporary.is_dir() and not output.is_symlink() and output.resolve().parent==temporary.resolve() and not output.exists(),'OUTPUT')
  stage=None
  if args.stage_input:
   need(args.stage_input.is_file() and not args.stage_input.is_symlink() and args.stage_input.stat().st_size<=LIMIT,'STAGE');stage=loads(args.stage_input.read_bytes())
  reader=Reader(os.environ.get('GH_TOKEN'))
  with window(reader):value=lookup(reader.get,args.tag,args.expected_id,stage)
  data=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(data)<=LIMIT,'BODY')
  with output.open('xb') as stream:stream.write(data)
  print(json.dumps({'schema':'project08-draft-metadata-read-v1','status':'PASS','tag':TAG,'assetCount':5}))
  return 0
 except Hold as error:print(json.dumps({'schema':'project08-draft-metadata-read-v1','status':'HOLD','reason':error.code,'httpStatus':error.status}));return 1
 except Exception:print(json.dumps({'schema':'project08-draft-metadata-read-v1','status':'HOLD','reason':'INPUT','httpStatus':None}));return 1
if __name__=='__main__':sys.exit(main())

