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
 assert tag=='v0.1.0-preview.3' and re.fullmatch('[1-9][0-9]{0,19}',run_id) and re.fullmatch('[0-9a-f]{40}',commit)
 from project08_hosted_proof import validate_bundle,source_data,archive_identity,archive_name
 source=source_data(*(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT) for name in
  ('tools/project08-hosted-profile.json','tools/project08_hosted.py','tools/project08-sdk404-members.jsonl','tools/package.py')))
 tree=subprocess.check_output(['git','rev-parse',commit+'^{tree}'],cwd=ROOT,text=True).strip()
 native={}
 for rid in ('win-x64','linux-x64'):
  path=proof_root/rid/'native-proof.json'
  received=archive_identity(directory/archive_name(rid),rid)
  proof=validate_bundle(path.parent,commit,tree,run_id,rid,source,received)
  native[rid]={'commit':commit,'outcome':'pass','fourCases':True,'kernelAdmitted':True,
               'receiptSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
               'fileHashes':{key:item['sha256'] for key,item in proof['files'].items()}}
 names=[f'fix-session-recovery-harness-{tag}-{suffix}' for suffix in ('win-x64.zip','linux-x64.tar.gz','source.zip')]
 assets={name:{'bytes':(directory/name).stat().st_size,'sha256':hashlib.sha256((directory/name).read_bytes()).hexdigest()} for name in names+['SHA256SUMS.txt']}
 key=ROOT/'SIGNING-PUBLIC-KEY.pub'
 assert hashlib.sha256(key.read_bytes()).hexdigest()=='a59fbecc53a0b3109212b70a3a51247dbd3529512d189ac2462a27a057dad671'
 assets[key.name]={'bytes':key.stat().st_size,'sha256':hashlib.sha256(key.read_bytes()).hexdigest()}
 result={'schema':'project08-draft-stage-v1','repository':'pouriajamali/fix-session-recovery-harness',
         'tag':tag,'commit':commit,'sourceTree':subprocess.check_output(['git','rev-parse',commit+'^{tree}'],cwd=ROOT,text=True).strip(),
         'workflowRunId':int(run_id),'sdk':'10.0.404','runtime':'10.0.15',
         'reportSchema':'fix-session-harness-report-v2','nativeProofs':native,'assets':assets}
 with output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')

def bind_draft(stage_path,draft_path,output):
 stage=bounded_json(stage_path);draft=bounded_json(draft_path)
 assert stage['schema']=='project08-draft-stage-v1' and draft['draft'] is True and draft['prerelease'] is True
 assert draft['tag_name']==stage['tag']=='v0.1.0-preview.3'
 assert len(draft['assets'])==5 and {v['name'] for v in draft['assets']}==set(stage['assets'])
 assert len({v['id'] for v in draft['assets']})==5
 for item in draft['assets']:
  expected=stage['assets'][item['name']]
  assert item['size']==expected['bytes'] and item['digest']=='sha256:'+expected['sha256'] and item['state']=='uploaded'
 stage['releaseId']=draft['id']
 stage['stageAssetIds']={v['name']:v['id'] for v in draft['assets']}
 with output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(stage,stream,indent=2);stream.write('\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--tag',required=True);p.add_argument('--proof-root',type=Path);p.add_argument('--run-id');p.add_argument('--stage-receipt',type=Path);p.add_argument('--stage-input',type=Path);p.add_argument('--bind-draft',type=Path);a=p.parse_args()
 if a.bind_draft:
  assert a.stage_input and a.stage_receipt
  bind_draft(a.stage_input,a.bind_draft,a.stage_receipt);return
 assert (ROOT/'LICENSE').is_file(),'Valid original-source license required'
 expected={f'fix-session-recovery-harness-{a.tag}-win-x64.zip':'win-x64',f'fix-session-recovery-harness-{a.tag}-linux-x64.tar.gz':'linux-x64'}
 assert {p.name for p in a.directory.iterdir()}==set(expected)
 source_tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.commit+'^{tree}'],text=True).strip()
 trees=set();receipts=[]
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


# Fixed carrier commands: only data, current-run read APIs and owned file handoffs.
def transport_main(arguments):
 import os,shutil,sys,tempfile,time
 import project08_hosted_proof as proof
 parser=argparse.ArgumentParser()
 parser.add_argument('operation',choices=('native-log','prepare-carrier','producer-available','tools','expect-carriers','accept-carrier','draft-log'))
 parser.add_argument('--rid',choices=('win-x64','linux-x64'));args=parser.parse_args(arguments)
 operation=args.operation
 from project08_hosted import context
 profile,ctx,state=context()
 assert os.environ.get('RUNNER_DEBUG')!='1'
 assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
 source=proof.source_at_root(ROOT)
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
 def gh_private(endpoint,limit):
  # gh follows GitHub's log redirect privately; no API/SAS/error body reaches stdout.
  assert os.environ.get('GH_TOKEN') and endpoint.startswith('repos/'+proof.TRANSPORT_REPO+'/actions/')
  assert '\n' not in endpoint and len(endpoint)<1024
  with tempfile.TemporaryDirectory(prefix='project08-api-',dir=os.environ['RUNNER_TEMP']) as temporary:
   out=Path(temporary)/'body';err=Path(temporary)/'error'
   with out.open('xb') as stdout,err.open('xb') as stderr:
    child=subprocess.Popen(['gh','api','--hostname','github.com',endpoint],cwd=ROOT,
     env=dict(os.environ,GH_HOST='github.com'),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    deadline=time.monotonic()+60
    try:
     while child.poll() is None:
      assert time.monotonic()<deadline and out.stat().st_size<=limit and err.stat().st_size<=131072
      time.sleep(0.05)
     assert child.returncode==0 and out.stat().st_size<=limit and err.stat().st_size<=131072
    finally:
     if child.poll() is None:child.kill();child.wait(timeout=3)
   return out.read_bytes()
 if operation=='tools':
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
  received=proof.archive_identity(archive,rid);files=proof.proof_bytes(directory)
  proof.validate_proof_bytes(files,context,source,received)
  if operation=='native-log':
   sys.stdout.buffer.write(proof.native_log(files,context,source,received));return
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
  assert os.environ['CACHE_SAVE_OUTCOME']=='success'
  exact_triplet(key)
  # Availability is affirmative; actual save is independently verified in producer log before draft.
  output(prefix(rid)+'_available','true');return
 assert os.environ['GITHUB_JOB']=='release'
 data_event()
 if operation=='expect-carriers':
  assert not private_root().exists();private_root().mkdir()
  jobs=proof.loads(gh_private('repos/'+proof.TRANSPORT_REPO+'/actions/runs/'+ctx['runId']+'/attempts/1/jobs?per_page=100',131072).decode('utf-8'))
  assert type(jobs) is dict and type(jobs.get('jobs')) is list
  proof.integer(jobs.get('total_count'),1,8);assert jobs['total_count']==len(jobs['jobs'])
  entries=[];compressed=[]
  for rid in ('win-x64','linux-x64'):
   p=prefix(rid);context=lc(rid)
   assert os.environ[p.upper()+'_AVAILABLE']=='true'
   value=proof.decode_handoff(os.environ[p.upper()+'_COMMITMENT'],context);key=proof.handoff_key(value,context)
   rows=[job for job in jobs['jobs'] if job.get('name')==context['jobName']]
   assert len(rows)==1;job=rows[0]
   proof.integer(job.get('id'),1,99999999999999999999)
   proof.integer(job.get('run_id'),1,99999999999999999999)
   assert str(job['run_id'])==ctx['runId'] and type(job.get('run_attempt')) is int and job['run_attempt']==1
   assert job.get('head_sha')==ctx['commit'] and job.get('status')=='completed' and job.get('conclusion')=='success'
   # Bind actual save line and complete finite proof to this authenticated exact job.
   log=gh_private('repos/'+proof.TRANSPORT_REPO+'/actions/jobs/'+str(job['id'])+'/logs',proof.JOB_LOG_LIMIT)
   proof.affirmative_save(log,key);files=proof.recovered_native_log(log,context,source)
   for row in value['files'][1:]:
    assert len(files[row['name']])==row['bytes'] and hashlib.sha256(files[row['name']]).hexdigest()==row['sha256']
   cache=proof.loads(gh_private('repos/'+proof.TRANSPORT_REPO+'/actions/caches?key='+key+'&per_page=100',131072).decode('utf-8'))
   size=proof.cache_entry(cache,key,os.environ['GITHUB_REF']);compressed.append(size)
   entries.append((rid,value,key,size))
  assert sum(compressed)<=2*proof.CACHE_ENTRY_LIMIT and 4*proof.CACHE_ENTRY_LIMIT<=226*1024*1024
  for rid,value,key,size in entries:
   write_private(private_root()/(rid+'.json'),{'context':lc(rid),'expected':value,'key':key,'actualSaveVerified':True,'cacheBytes':size})
   output(prefix(rid)+'_key',key)
  return
 if operation=='accept-carrier':
  assert args.rid
  rid=args.rid;context=lc(rid)
  private=proof.read(private_root()/(rid+'.json'))
  proof.closed(private,('context','expected','key','actualSaveVerified','cacheBytes'))
  assert private['context']==context and private['actualSaveVerified'] is True
  proof.integer(private['cacheBytes'],1,proof.CACHE_ENTRY_LIMIT)
  key=proof.handoff_key(private['expected'],context);assert key==private['key'];exact_triplet(key)
  files,received=proof.validate_carrier(carrier(rid),private['expected'],context,source)
  directory=ROOT/'artifacts/native-proofs'/rid;assert not directory.exists();directory.mkdir(parents=True)
  for name,data in files.items():
   with (directory/name).open('xb') as stream:stream.write(data)
  destination=ROOT/'artifacts/release';destination.mkdir(parents=True,exist_ok=True)
  with (destination/proof.archive_name(rid)).open('xb') as stream:stream.write((carrier(rid)/proof.archive_name(rid)).read_bytes())
  return
 assert operation=='draft-log'
 path=ROOT/'artifacts/DRAFT-STAGE.json'
 value=proof.read(path)
 sys.stdout.buffer.write(proof.draft_log(value,lc('both','release')))

if __name__=='__main__':
 import sys
 try:
  if len(sys.argv)>1 and sys.argv[1]=='transport':transport_main(sys.argv[2:])
  else:main()
 except Exception:
  print('PROJECT08_DATA_OR_TRANSPORT_HOLD',file=sys.stderr);sys.exit(1)
