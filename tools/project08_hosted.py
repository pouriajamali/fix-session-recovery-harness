"""Project08 hosted-only fixed SDK404/native chain. INACTIVE proposal until coordinator gate.
Never loads local E admission, local ledgers, SDK11, installers or arbitrary commands.
"""
import argparse,contextlib,hashlib,json,os,platform,secrets,subprocess,sys,tarfile,time,unittest,urllib.request,zipfile
from pathlib import Path,PurePosixPath
import project08_kernel as kernel
ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/'tools/project08-hosted-profile.json'
INDEX=0

def need(ok,reason):
 if not ok:raise RuntimeError(reason)
def read(path):
 need(path.is_file() and not path.is_symlink() and path.stat().st_size<=131072,'bounded hosted JSON')
 return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path,kind='sha256'):
 with path.open('rb') as f:return hashlib.file_digest(f,kind).hexdigest()
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 data=(json.dumps(value,indent=2)+'\n').encode()
 need(len(data)<=131072,'bounded hosted receipt')
 with path.open('xb') as f:f.write(data)
def context():
 need(os.environ.get('GITHUB_ACTIONS')=='true','hosted only; no local admission fallback')
 need(os.environ['GITHUB_REPOSITORY']=='pouriajamali/fix-session-recovery-harness','fixed repository')
 need(os.environ['GITHUB_RUN_ID'].isdigit() and os.environ['GITHUB_RUN_ATTEMPT']=='1','new approved event only; no unchanged rerun')
 need(Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT.resolve(),'actual hosted checkout')
 commit=os.environ['GITHUB_SHA']
 need(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'exact run SHA')
 actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
 need(actual==commit and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'clean exact hosted source')
 rid='win-x64' if os.name=='nt' else 'linux-x64'
 need(platform.machine().lower() in ('amd64','x86_64'),'x64 native only')
 need(platform.system()==('Windows' if rid=='win-x64' else 'Linux'),'matching actual native OS')
 p=read(PROFILE)
 need(p['sdk']=='10.0.404' and p['runtime']=='10.0.15' and p['nativeTotalSeconds']==900,'fixed net10 contract')
 state=Path(os.environ['RUNNER_TEMP']).resolve()/('project08-'+os.environ['GITHUB_RUN_ID']+'-'+rid)
 return p,{'schema':'project08-hosted-context-v1','project':'08','rid':rid,'commit':commit,
  'tree':tree,'runId':os.environ['GITHUB_RUN_ID'],'runAttempt':'1','os':platform.system(),
  'profileSha256':sha(PROFILE),'adapterSha256':sha(Path(__file__)),'root':str(ROOT)},state
def controls(nonce):
 return kernel.windows_limits(nonce) if os.name=='nt' else kernel.linux_limits(nonce)
def member_name(name):
 need(not name.startswith(('/','\\')) and '\\' not in name and ':' not in name,'unsafe archive path')
 while name.startswith('./'):name=name[2:]
 parts=PurePosixPath(name).parts
 need('..' not in parts and all(not any(ord(c)<32 for c in part) for part in parts),'archive path controls')
 return '/'.join(parts) if parts else '.'
def materialize(profile,ctx,state):
 pin=profile['inputs'][ctx['rid']]
 manifest=ROOT/profile['memberManifest']
 need(manifest.stat().st_size<=8*1024*1024 and sha(manifest)==profile['memberManifestSha256'],'accepted SDK404 member pins')
 expected={}
 with manifest.open() as f:
  for line in f:
   item=json.loads(line)
   if item['archive']==pin['archive']:
    need(item['type']=='file' and item['path'] not in expected,'unique SDK file pins')
    expected[item['path']]=item
 need(len(expected)==pin['regularFiles'],'SDK regular member count')
 archive=state/pin['archive']
 class SameOrigin(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,newurl):
   need(newurl.startswith('https://builds.dotnet.microsoft.com/'),'no alternate download origin')
   return super().redirect_request(req,fp,code,msg,headers,newurl)
 opener=urllib.request.build_opener(SameOrigin())
 count=0
 with opener.open(pin['url'],timeout=30) as source,archive.open('xb') as out:
  need(source.geturl().startswith('https://builds.dotnet.microsoft.com/'),'official HTTPS SDK input')
  while True:
   block=source.read(1024*1024)
   if not block:break
   count+=len(block);need(count<=pin['bytes'],'compressed SDK cap');out.write(block)
 need(count==pin['bytes'] and sha(archive)==pin['sha256'] and sha(archive,'sha512')==pin['sha512'],'exact official SDK archive')
 sdk=state/'sdk';sdk.mkdir()
 seen=set();expanded=0
 def copy_file(name,size,source):
  nonlocal expanded
  relative=member_name(name);need(relative in expected and relative not in seen,'unlisted/duplicate SDK member')
  item=expected[relative]
  need(size==item['bytes'] and 0<=size<=256*1024*1024,'SDK member size')
  expanded+=size;need(expanded<=pin['expandedBytes'],'SDK expanded cap')
  target=sdk/relative;need(target.resolve().is_relative_to(sdk.resolve()),'SDK path escape')
  target.parent.mkdir(parents=True,exist_ok=True)
  h=hashlib.sha256();left=size
  with target.open('xb') as out:
   while left:
    block=source.read(min(65536,left));need(block,'truncated SDK member')
    h.update(block);out.write(block);left-=len(block)
  need(h.hexdigest()==item['sha256'],'SDK member content hash')
  if os.name!='nt':target.chmod(item['mode']&0o755)
  seen.add(relative)
 if ctx['rid']=='win-x64':
  with zipfile.ZipFile(archive) as bundle:
   need(len(bundle.infolist())<=12000,'SDK ZIP count cap')
   folded=set()
   for item in bundle.infolist():
    name=member_name(item.filename)
    need(name.casefold() not in folded and (item.external_attr>>16)&0o170000!=0o120000,'SDK collision/link')
    folded.add(name.casefold())
    if item.is_dir():continue
    with bundle.open(item) as source:copy_file(item.filename,item.file_size,source)
 else:
  with tarfile.open(archive,'r:gz') as bundle:
   count=0
   for item in bundle:
    count+=1;need(count<=12000,'SDK tar count cap');member_name(item.name)
    if item.isdir():continue
    need(item.isfile(),'SDK links/devices forbidden')
    with bundle.extractfile(item) as source:copy_file(item.name,item.size,source)
 need(seen==set(expected) and expanded==pin['expandedBytes'],'complete SDK404 members')
 need(sha(sdk/pin['host'])==pin['hostSha256'],'actual admitted dotnet host bytes')
 write(state/'sdk-input.json',{**ctx,'schema':'project08-hosted-sdk-input-v1',
  'sdk':'10.0.404','runtime':'10.0.15','archive':archive.name,'archiveBytes':archive.stat().st_size,
  'archiveSha256':sha(archive),'archiveSha512':sha(archive,'sha512'),
  'memberManifestSha256':sha(manifest),'files':len(seen),'expandedBytes':expanded,
  'hostSha256':sha(sdk/pin['host']),'sdkOrAppExecuted':False})
def checked_run(command,**kwargs):
 """Only fixed SDK404 or own extracted app, inside the actual hosted Job/cgroup."""
 global INDEX
 p,ctx,state=context();phase=os.environ['PROJECT08_HOSTED_PHASE'];nonce=os.environ['PROJECT08_HOSTED_NONCE']
 folder=state/phase;record=read(folder/'phase-context.json')
 need(record['nonce']==nonce and record['context']==ctx,'phase/run/source/profile binding')
 before=controls(nonce)
 exe=Path(command[0]).resolve()
 sdk=(state/'sdk'/p['inputs'][ctx['rid']]['host']).resolve()
 if exe==sdk:
  need(sha(sdk)==p['inputs'][ctx['rid']]['hostSha256'] and command[1] in
       ('--version','--list-runtimes','restore','build','run','publish'),'fixed SDK executable/subcommand')
  need(not any('NoWarn' in str(x) or 'NuGetAudit=false' in str(x) for x in command),'no weakened audit')
 else:
  expected=state/'consumer/extracted'/('fix-session-recovery-harness-v0.1.0-preview.4-'+ctx['rid'])/('session-harness.exe' if os.name=='nt' else 'session-harness')
  need(exe==expected.resolve() and command[1] in
       ('--version','demo','--host','--settings','--dictionary','--order','--owned-worker'),'only own fixed consumer app')
  m=read(exe.parent/'BUILD-MANIFEST.json')
  need(m['sourceCommit']==ctx['commit'] and m['sourceTree']==ctx['tree'] and m['rid']==ctx['rid'],'own app source/OS/RID')
 timeout=min(float(kwargs.get('timeout',120)),record['deadlineMonotonic']-time.monotonic()-6)
 need(timeout>0,'hosted phase/cumulative deadline')
 index=INDEX;INDEX+=1;need(index<64,'bounded SDK/app invocation count')
 env=dict(os.environ);env.update(kwargs.get('env',{}))
 child=subprocess.Popen(list(map(str,command)),cwd=kwargs.get('cwd',ROOT),env=env,
   stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 membership=kernel.child_membership(child,nonce)
 try:out,err=child.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  child.kill();out,err=child.communicate(timeout=3);raise
 finally:
  # Parent Job/cgroup deadline/kill-on-close owns all descendants; no host-wide PID scan.
  pass
 need(len(out)<=131072 and len(err)<=131072,'bounded SDK/app output')
 (folder/(str(index)+'-stdout.bin')).write_bytes(out)
 (folder/(str(index)+'-stderr.bin')).write_bytes(err)
 write(folder/(str(index)+'-invocation.json'),{**ctx,'schema':'project08-hosted-invocation-v1',
  'nonce':nonce,'index':index,'pid':child.pid,'operation':command[1],'commandKind':'sdk' if exe==sdk else 'consumer',
  'kernelBeforeInvocation':before,'membership':membership,'exitCode':child.returncode,
  'exitObserved':child.poll() is not None,'stdoutSha256':hashlib.sha256(out).hexdigest(),
  'stderrSha256':hashlib.sha256(err).hexdigest(),'deadlineExpired':False})
 if kwargs.get('stdout') is not None:
  kwargs['stdout'].write(out)
  if kwargs.get('stderr')==subprocess.STDOUT:kwargs['stdout'].write(err)
 if kwargs.get('check') and child.returncode:raise subprocess.CalledProcessError(child.returncode,command,out,err)
 text=kwargs.get('text') or kwargs.get('encoding')
 return subprocess.CompletedProcess(command,child.returncode,
  out.decode(kwargs.get('encoding','utf-8')) if text else out,
  err.decode(kwargs.get('encoding','utf-8')) if text else err)
def execute(profile,ctx,state,phase,nonce):
 folder=state/phase
 os.environ.update(PROJECT08_HOSTED_PHASE=phase,PROJECT08_HOSTED_NONCE=nonce,
  DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
  DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',MSBUILDDISABLENODEREUSE='1',
  DOTNET_ROOT=str(state/'sdk'),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_CLI_HOME=str(state/'home'),NUGET_PACKAGES=str(state/'nuget'))
 for key in ('home','nuget','temp'):(state/key).mkdir(exist_ok=True)
 os.environ.update(TMP=str(state/'temp'),TEMP=str(state/'temp'),TMPDIR=str(state/'temp'))
 actual_controls=controls(nonce)
 write(folder/'kernel.json',actual_controls)
 write(folder/'self-membership.json',{'project':'08','nonce':nonce,'pid':os.getpid(),
  'startIdentity':kernel.own_start_identity(),'member':True,'mechanism':actual_controls['mechanism'],
  **({'job':actual_controls['job']} if os.name=='nt' else {'membership':actual_controls['membership']})})
 if phase=='materialize':materialize(profile,ctx,state);return
 host=str(state/'sdk'/profile['inputs'][ctx['rid']]['host'])
 common=['-p:RuntimeIdentifier='+ctx['rid'],'-p:SelfContained=true',
  '-p:RuntimeFrameworkVersion=10.0.15','-p:NuGetAuditMode=all',
  '-p:DisableTransitiveFrameworkReferenceDownloads=true']
 if phase=='qualify':
  version=checked_run([host,'--version'],text=True,check=True,timeout=30).stdout.strip()
  runtimes=checked_run([host,'--list-runtimes'],text=True,check=True,timeout=30).stdout
  need(version=='10.0.404' and any(line.startswith('Microsoft.NETCore.App 10.0.15 ') for line in runtimes.splitlines()),'real capped SDK/runtime qualification')
 elif phase=='restore':
  checked_run([host,'restore','tests/SessionHarness.Tests','--locked-mode','--disable-parallel',*common],check=True,timeout=90)
  from package import validate_rid_outputs
  validate_rid_outputs(ctx['rid'])
 elif phase=='build':
  checked_run([host,'build','tests/SessionHarness.Tests','-c','Release','--no-restore','-m:1',
   '-p:BuildInParallel=false','-p:UseSharedCompilation=false','-nodeReuse:false',*common],check=True,timeout=90)
 elif phase=='tests':
  checked_run([host,'run','--project','tests/SessionHarness.Tests','-c','Release','--no-build','--no-restore',
   *common,'--','--work',str(folder/'tests')],check=True,timeout=165)
  suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='release_candidate_test.py')
  def identifiers(item):
   if isinstance(item,unittest.TestSuite):
    return [name for nested in item for name in identifiers(nested)]
   return [item.id()]
  expected=identifiers(suite)
  from project08_hosted_proof import OFFLINE_TEST_IDS
  need(len(expected)==len(set(expected))==7 and set(expected)==set(OFFLINE_TEST_IDS),'fixed complete discovered offline suite')
  class ObservedResult(unittest.TextTestResult):
   def __init__(self,*args,**kwargs):
    super().__init__(*args,**kwargs);self.completed=[]
   def stopTest(self,test):
    self.completed.append(test.id());super().stopTest(test)
  with (folder/'offline-release-private.txt').open('x') as transcript:
   result=unittest.TextTestRunner(stream=transcript,verbosity=2,resultclass=ObservedResult).run(suite)
  receipt={'success':result.wasSuccessful(),'testsRun':result.testsRun,'expectedCount':len(expected),
   'expectedTestIds':expected,'completedTestIds':result.completed,'failed':len(result.failures),
   'errors':len(result.errors),'skipped':len(result.skipped)}
  write(folder/'offline-release-tests.json',receipt)
  from project08_hosted_proof import validate_offline
  validate_offline(receipt)
 elif phase=='package':
  import package
  sys.argv=['package.py','--rid',ctx['rid'],'--commit',ctx['commit'],'--dotnet',host,
   '--work',str(folder/'build'),'--out',str(folder/'delivery')]
  with (folder/'package-private-stdout.txt').open('x') as private_stdout,contextlib.redirect_stdout(private_stdout):package.main()
 elif phase=='consumer':
  # Use the already tested archive, no rebuild or alternate-path search.
  meta=read(state/'package/build/archive.json')
  need(meta['commit']==ctx['commit'] and meta['sourceTree']==ctx['tree'] and meta['rid']==ctx['rid'],'producer identity')
  terminal=read(state/'package/terminal.json')
  need(terminal['exitCode']==0 and terminal['terminal'] and terminal['commit']==ctx['commit'],'successful actual producer')
  filename='fix-session-recovery-harness-v0.1.0-preview.4-'+ctx['rid']+('.zip' if ctx['rid']=='win-x64' else '.tar.gz')
  archive=state/'package/delivery'/filename
  need(Path(meta['archive']).resolve()==archive.resolve() and archive.stat().st_size<=48*1024*1024 and
       sha(archive)==meta['sha256'] and archive.stat().st_size==meta['bytes'],'fixed producer bytes')
  destination=folder/'extracted';destination.mkdir()
  names=[];expanded=0;folded=set()
  if ctx['rid']=='win-x64':
   with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
     need(not item.is_dir() and (item.external_attr>>16)&0o170000!=0o120000,'consumer ZIP regular only')
     name=member_name(item.filename)
     need(name not in names and name.casefold() not in folded and item.file_size<=64*1024*1024,'consumer unique/size')
     expanded+=item.file_size;need(expanded<=256*1024*1024 and len(names)<512,'consumer total bound')
     names.append(name);folded.add(name.casefold())
     target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
     need(target.resolve().is_relative_to(destination.resolve()),'consumer path')
     with target.open('xb') as f:f.write(z.read(item))
  else:
   with tarfile.open(archive,'r:gz') as t:
    for item in t:
     need(item.isfile(),'consumer tar regular only');name=member_name(item.name)
     need(name not in names and item.size<=64*1024*1024,'consumer unique/size')
     expanded+=item.size;need(expanded<=256*1024*1024 and len(names)<512,'consumer total bound')
     names.append(name)
     target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
     need(target.resolve().is_relative_to(destination.resolve()) and item.size<=64*1024*1024,'consumer path/size')
     with t.extractfile(item) as source,target.open('xb') as f:
      left=item.size
      while left:
       block=source.read(min(65536,left));need(block,'consumer truncation');f.write(block);left-=len(block)
     target.chmod(0o755 if target.name in ('session-harness','createdump') else 0o644)
  need(len(names)<=512 and len(names)==len(set(names)),'consumer bounded unique entries')
  import check_package
  sys.argv=['check_package.py','--package',str(destination/('fix-session-recovery-harness-v0.1.0-preview.4-'+ctx['rid'])),
   '--work',str(folder/'consumer'),'--commit',ctx['commit']]
  with (folder/'consumer-private-stdout.txt').open('x') as private_stdout,contextlib.redirect_stdout(private_stdout):check_package.main()
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--inside',choices=['materialize','qualify','restore','build','tests','package','consumer'])
 parser.add_argument('--nonce',default='')
 args=parser.parse_args()
 p,ctx,state=context()
 if args.inside:
  need(len(args.nonce)==32,'internal fixed phase nonce');execute(p,ctx,state,args.inside,args.nonce);return
 need(not state.exists(),'one fresh hosted job state; no retry/reset')
 state.mkdir()
 write(state/'context.json',ctx)
 origin=time.monotonic()
 for phase,cap in p['phases'].items():
  remaining=900-(time.monotonic()-origin);need(remaining>9,'hosted900 exhausted')
  nonce=secrets.token_hex(16);folder=state/phase;folder.mkdir()
  deadline=min(origin+900,time.monotonic()+cap)
  write(folder/'phase-context.json',{'context':ctx,'nonce':nonce,'deadlineMonotonic':deadline})
  command=[sys.executable,str(Path(__file__).resolve()),'--inside',phase,'--nonce',nonce]
  if os.name=='nt':
   code,terminal=kernel.windows_start(command,ROOT,nonce,min(cap,remaining-6),folder,deadline)
  else:
   # Independent actual hosted system cgroup; never assumes local UID1000/user bus.
   invocation=['sudo','-n','systemd-run','--quiet','--wait','--pipe','--collect','--unit=project08-'+nonce,
    '--working-directory='+str(ROOT),'--property=Type=exec','--property=User='+str(os.getuid()),
    '--property=MemoryMax=2147483648','--property=MemorySwapMax=0','--property=TasksMax=256',
    '--property=CPUQuota=200%','--property=RuntimeMaxSec='+str(min(cap,remaining-6)),
    '--property=TimeoutStopSec=3','--property=KillMode=control-group']
   for key in ('GITHUB_ACTIONS','GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_WORKSPACE','RUNNER_TEMP','PATH','LD_LIBRARY_PATH'):
    if key in os.environ:invocation.append('--setenv='+key+'='+os.environ[key])
   result=subprocess.run([*invocation,*command],cwd=ROOT,timeout=min(cap,remaining-6)+6,check=False,capture_output=True)
   need(len(result.stdout)<=131072 and len(result.stderr)<=131072,'bounded private controller streams')
   (folder/'controller-stdout.bin').write_bytes(result.stdout)
   (folder/'controller-stderr.bin').write_bytes(result.stderr)
   code=result.returncode
   proof=read(folder/'kernel.json');group=Path(proof['group'])
   terminal=not group.exists() or 'populated 0' in (group/'cgroup.events').read_text()
  write(folder/'terminal.json',{'project':'08','nonce':nonce,'phase':phase,
   'commit':ctx['commit'],'exitCode':code,'terminal':terminal})
  need(code==0 and terminal and time.monotonic()-origin<=900,'real hosted phase failed/unknown/overbudget')
 from project08_hosted_proof import emit
 need(900-(time.monotonic()-origin)>=3,'reserve final finite proof/export inside900')
 emit(state,ROOT,p,ctx)
 need(time.monotonic()-origin<=900,'final hosted bookkeeping exceeded900')
if __name__=='__main__':
 try:main()
 except Exception as error:
  # Do not send raw PID/nonce/paths/wire or exception text to Actions logs.
  if os.environ.get('PROJECT08_HOSTED_PHASE'):
   try:
    p,c,s=context();write(s/os.environ['PROJECT08_HOSTED_PHASE']/'failure.json',
      {'type':type(error).__name__,'reason':str(error)[:2048],'scope':'PRIVATE_NOT_UPLOAD'})
   except Exception:pass
  print('PROJECT08_HOSTED_HOLD: bounded private evidence retained',file=sys.stderr)
  raise SystemExit(1)

