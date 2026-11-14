# Adapted from Pouria Jamali's public MIT sqlite-recovery-drill (003b700d); see NOTICE.md.
"""Exact clean-commit self-contained bundles; no publication or rebuilding in aggregation."""
import argparse,base64,hashlib,json,os,platform,shutil,subprocess,tarfile,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def runtime_pin(rid, assets):
 folders=[Path(f) for f in assets['packageFolders']]
 identity='Microsoft.NETCore.App.Runtime.'+rid
 directory=next((folder/identity.lower()/'10.0.15' for folder in folders if (folder/identity.lower()/'10.0.15').is_dir()),None)
 assert directory is not None,'Pinned runtime15 NuGet pack absent'
 archive=directory/(identity.lower()+'.10.0.15.nupkg')
 assert archive.is_file(),'Actual runtime package bytes required'
 content=base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
 metadata=(directory/(identity.lower()+'.10.0.15.nupkg.sha512')).read_text().strip()
 assert content==metadata,'Runtime package content identity'
 notices={f.name:sha(f) for f in sorted(directory.iterdir()) if f.is_file() and
          (f.name.upper().startswith('LICENSE') or f.name.upper().startswith('THIRD-PARTY-NOTICES'))}
 assert any(n.upper().startswith('LICENSE') for n in notices) and any(n.upper().startswith('THIRD-PARTY-NOTICES') for n in notices)
 return {'schema':'project08-runtime-packs-v1','sdk':'10.0.404','runtime':'10.0.15','rid':rid,
         'packs':[{'id':identity,'version':'10.0.15','nugetContentSha512':content,'notices':notices}],
         'apphostTrust':'SDK404 producer inventory plus exact published apphost member hash; runtime NuGet lock is not apphost build proof'}

def validate_graph(assets):
 expected={'QuickFIXn.Core':'1.14.1','QuickFIXn.FIX44':'1.14.1',
           'Microsoft.Extensions.Logging.Abstractions':'8.0.3',
           'Microsoft.Extensions.DependencyInjection.Abstractions':'8.0.2'}
 packages={key.split('/')[0]:key.split('/')[1] for key,value in assets['libraries'].items() if value['type']=='package'}
 for key,version in expected.items():assert packages.get(key)==version,(key,packages.get(key))
 allowed_runtime={name for name in packages if name in {
  'Microsoft.NETCore.App.Runtime.win-x64','Microsoft.NETCore.App.Runtime.linux-x64',
  'Microsoft.NETCore.App.Host.win-x64','Microsoft.NETCore.App.Host.linux-x64'} and packages[name]=='10.0.15'}
 assert set(packages)==set(expected)|allowed_runtime,'Unexpected managed dependency delta'

 # Filtering unused framework downloads must not hide a genuinely required framework.
 frameworks=assets['project']['frameworks']
 assert frameworks and all(set(value.get('frameworkReferences',{}))=={'Microsoft.NETCore.App'} for value in frameworks.values()),'Unexpected required framework: HOLD'
 for target in assets['targets'].values():
  for item in target.values():
   assert set(item.get('frameworkReferences',[]))<={'Microsoft.NETCore.App'},'New transitive framework: HOLD'


def guard(condition, reason):
 if not condition:raise RuntimeError(reason)

def regular_input(path, base=None):
 path=Path(path)
 if base is not None:guard(path.absolute().is_relative_to(Path(base).absolute()),'Input path escape')
 guard(not any(p.is_symlink() or
               (getattr(p.stat(follow_symlinks=False),'st_file_attributes',0)&0x400)
               for p in (path,*path.parents)),'Linked/reparse input: HOLD')
 guard(path.is_file() and path.stat().st_size<=65536,'Bounded regular input required')
 return path

def validate_rid_outputs(rid):
 guard(rid in ('win-x64','linux-x64'),'Fixed RID only')
 roots={'src/SessionHarness':'43320ad83f8a56fa6d50a2a54e23132115f05dcad6d93e9e50b6af8696eb4ce2',
        'tests/SessionHarness.Tests':'2d49a858c78ebec44dec9c9185e5e4d38faec8fc0c547392f6353711ade65a34'}
 identities={}
 app_assets=None
 for project,expected_root in roots.items():
  baseline_path=regular_input(ROOT/project/'packages.lock.json',ROOT)
  guard(sha(baseline_path)==expected_root,'Managed root lock changed: HOLD')
  baseline=json.loads(baseline_path.read_text(encoding='utf-8-sig'))
  name=Path(project).name
  target=regular_input(ROOT/'locks/runtime'/rid/(name+'.lock.json'),ROOT)
  lock=json.loads(target.read_text(encoding='utf-8-sig'))
  guard(lock['version']==baseline['version']==1,'Lock schema')
  guard(set(baseline['dependencies'])=={'net10.0'},'Root target delta')
  guard(set(lock['dependencies'])=={'net10.0','net10.0/'+rid},'RID target identity')
  guard(lock['dependencies']['net10.0']==baseline['dependencies']['net10.0'],'Managed graph/content hash delta')
  guard(lock['dependencies']['net10.0/'+rid]=={},'Unexpected RID dependency graph')
  assets_path=regular_input(ROOT/project/'obj/project.assets.json',ROOT)
  assets=json.loads(assets_path.read_text(encoding='utf-8-sig'))
  validate_graph(assets)
  guard(set(assets['targets'])=={'net10.0','net10.0/'+rid},'Mixed/portable assets cannot qualify RID')
  restore=assets['project']['restore']
  guard(Path(restore['projectPath']).resolve()==(ROOT/project/(name+'.csproj')).resolve(),'Assets project identity')
  audit=restore['restoreAuditProperties']
  guard(audit['enableAudit']=='true' and audit['auditMode']=='all','Audit must remain enabled/all')
  for package,dependency in baseline['dependencies']['net10.0'].items():
   if dependency['type']!='Project':
    guard(assets['libraries'][package+'/'+dependency['resolved']]['sha512']==dependency['contentHash'],'Assets/lock content mismatch')
  identities[name+'.lock.json']={'bytes':target.stat().st_size,'sha256':sha(target)}
  if name=='SessionHarness':app_assets=assets
 pin_path=regular_input(ROOT/'locks/runtime'/rid/'RUNTIME-PACKS.json',ROOT)
 pin=json.loads(pin_path.read_text(encoding='utf-8-sig'))
 guard(pin==runtime_pin(rid,app_assets),'Actual RID runtime pack/notices pin delta')
 identities['RUNTIME-PACKS.json']={'bytes':pin_path.stat().st_size,'sha256':sha(pin_path)}
 return identities

def validate_reconciled_windows_outputs():
 # Historical identity only. Never qualifies current native assets or a fresh build.
 rid='win-x64'
 preserved=ROOT.parents[1]/'chat-fix-recovery-roadmap/outputs/wave3-m1-20261114/native-qualification/win-x64/routing-reconciliation-01'
 receipt=regular_input(preserved/'RECONCILIATION.json',preserved)
 guard(sha(receipt)=='7e922c423a063e50b1aa678a028a8f8e13bd6d108d63c783b74a23f1443a5c63','Exact historical reconciliation required')
 historical_assets={
  'SessionHarness':('app-project.assets.json','566d5cc7efed3980dda8383abb2bb5c731d587f8421aae482bf58aeb2a9ee2c3'),
  'SessionHarness.Tests':('test-project.assets.json','a2765e8d675a05bc80ab320487ca0f9c4c1d5786ec224ede1eb8c110c06762c1')}
 roots={'src/SessionHarness':'43320ad83f8a56fa6d50a2a54e23132115f05dcad6d93e9e50b6af8696eb4ce2',
        'tests/SessionHarness.Tests':'2d49a858c78ebec44dec9c9185e5e4d38faec8fc0c547392f6353711ade65a34'}
 identities={}
 app_assets=None
 for project,expected_root in roots.items():
  baseline_path=regular_input(ROOT/project/'packages.lock.json',ROOT)
  guard(sha(baseline_path)==expected_root,'Managed root lock changed: HOLD')
  baseline=json.loads(baseline_path.read_text(encoding='utf-8-sig'))
  name=Path(project).name
  target=regular_input(ROOT/'locks/runtime'/rid/(name+'.lock.json'),ROOT)
  lock=json.loads(target.read_text(encoding='utf-8-sig'))
  guard(lock['version']==baseline['version']==1,'Lock schema')
  guard(set(baseline['dependencies'])=={'net10.0'},'Root target delta')
  guard(set(lock['dependencies'])=={'net10.0','net10.0/'+rid},'RID target identity')
  guard(lock['dependencies']['net10.0']==baseline['dependencies']['net10.0'],'Managed graph/content hash delta')
  guard(lock['dependencies']['net10.0/'+rid]=={},'Unexpected RID dependency graph')
  filename,expected_asset=historical_assets[name]
  assets_path=regular_input(preserved/filename,preserved)
  guard(sha(assets_path)==expected_asset,'Preserved historical assets identity changed')
  assets=json.loads(assets_path.read_text(encoding='utf-8-sig'))
  validate_graph(assets)
  guard(set(assets['targets'])=={'net10.0','net10.0/'+rid},'Historical assets must have exact Windows target set')
  restore=assets['project']['restore']
  guard(Path(restore['projectPath']).resolve()==(ROOT/project/(name+'.csproj')).resolve(),'Assets project identity')
  audit=restore['restoreAuditProperties']
  guard(audit['enableAudit']=='true' and audit['auditMode']=='all','Audit must remain enabled/all')
  for package,dependency in baseline['dependencies']['net10.0'].items():
   if dependency['type']!='Project':
    guard(assets['libraries'][package+'/'+dependency['resolved']]['sha512']==dependency['contentHash'],'Assets/lock content mismatch')
  identities[name+'.lock.json']={'bytes':target.stat().st_size,'sha256':sha(target)}
  if name=='SessionHarness':app_assets=assets
 pin_path=regular_input(ROOT/'locks/runtime'/rid/'RUNTIME-PACKS.json',ROOT)
 pin=json.loads(pin_path.read_text(encoding='utf-8-sig'))
 guard(pin==runtime_pin(rid,app_assets),'Historical Windows runtime pack/notices pin delta')
 identities['RUNTIME-PACKS.json']={'bytes':pin_path.stat().st_size,'sha256':sha(pin_path)}
 return identities

def main():
 p=argparse.ArgumentParser();p.add_argument('--rid',choices=['win-x64','linux-x64'],required=True);p.add_argument('--commit',required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--dotnet',default='dotnet');p.add_argument('--source',action='append');p.add_argument('--local-candidate',action='store_true');p.add_argument('--write-runtime-pins',action='store_true');a=p.parse_args()
 assets=json.loads((ROOT/'src/SessionHarness/obj/project.assets.json').read_text(encoding='utf-8')) if a.write_runtime_pins else None
 if a.write_runtime_pins:
  # Metadata-only: consumes prior admitted restore assets/cache bytes; never invokes a.dotnet.
  validate_graph(assets);pin=runtime_pin(a.rid,assets)
  target=ROOT/'locks/runtime'/a.rid/'RUNTIME-PACKS.json';target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('x',encoding='utf-8',newline='\n') as output:json.dump(pin,output,indent=2);output.write('\n')
  validate_rid_outputs(a.rid)
  return
 assert json.loads((ROOT/'global.json').read_text())['sdk']=={'version':'10.0.404','rollForward':'disable','allowPrerelease':False}
 assert git('rev-parse','HEAD')==a.commit and not git('status','--porcelain'),'Clean exact source required'
 assert platform.machine().lower() in {'amd64','x86_64'}
 assert platform.system() in {'Windows','Linux'},'Supported build hosts are Windows and Linux'
 if not a.local_candidate:assert platform.system()==('Windows' if a.rid=='win-x64' else 'Linux'),'Public releases require matching build OS'
 version=ET.parse(ROOT/'Directory.Build.props').findtext('.//Version');assert version
 assert (ROOT/'LICENSE').is_file(),'Explicit original-source license required before distribution'
 work=a.work.resolve();work.mkdir(parents=True,exist_ok=False);a.out.mkdir(parents=True,exist_ok=True)
 validate_rid_outputs(a.rid)
 published=work/'published';command=[a.dotnet,'publish','src/SessionHarness/SessionHarness.csproj','-c','Release','-p:RuntimeIdentifier='+a.rid,'--self-contained','true','-p:RestoreLockedMode=true','-p:NuGetAuditMode=all','-p:DisableTransitiveFrameworkReferenceDownloads=true','-m:1','-p:BuildInParallel=false','-p:UseSharedCompilation=false','-nodeReuse:false','-p:RuntimeFrameworkVersion=10.0.15','-p:PublishTrimmed=false','-p:PublishAot=false','-p:PublishReadyToRun=false','-p:DebugType=None','-p:DebugSymbols=false','-p:SourceRevisionId='+a.commit,'-o',str(published)]
 if a.source:
  for source in a.source:command+=['--source',source]
 # Audit remains enabled even with an explicitly admitted feed.
 with (work/'publish.log').open('wb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=210)
 validate_rid_outputs(a.rid)
 assert not git('status','--porcelain'),'Build modified source'
 name=f'fix-session-recovery-harness-v{version}-{a.rid}';package=work/name;shutil.copytree(published,package)
 assert a.commit.encode() in (package/'session-harness.dll').read_bytes(),'Source revision missing'
 for f in ['README.md','PROVENANCE.md','SIGNING-PUBLIC-KEY.pub','NOTICE.md']:shutil.copy2(ROOT/f,package/f)
 shutil.copy2(ROOT/'LICENSE',package/'LICENSE')
 shutil.copy2(ROOT/'CONTRIBUTING.md',package/'CONTRIBUTING.md')
 shutil.copytree(ROOT/'docs',package/'docs');shutil.copytree(ROOT/'vendor',package/'vendor')
 licenses=package/'licenses';licenses.mkdir()
 assets=json.loads((ROOT/'src/SessionHarness/obj/project.assets.json').read_text(encoding='utf-8'))
 validate_graph(assets)
 pins=ROOT/'locks/runtime'/a.rid/'RUNTIME-PACKS.json'
 assert json.loads(pins.read_text())==runtime_pin(a.rid,assets),'Runtime pack or notices differ from sealed pins'
 lock_paths=[ROOT/'locks/runtime'/a.rid/(name+'.lock.json') for name in ('SessionHarness','SessionHarness.Tests')]
 assert all(path.is_file() for path in lock_paths),'Both native RID locks required'
 shutil.copy2(pins,package/'RUNTIME-PACKS.json')
 locks=package/'runtime-locks';locks.mkdir()
 for path in lock_paths:shutil.copy2(path,locks/path.name)
 folders=[Path(f) for f in assets['packageFolders']];dependencies=[]
 for identity,entry in sorted(assets['libraries'].items()):
  if entry['type']!='package':continue
  package_id,version_id=identity.split('/')
  directory=next(folder/package_id.lower()/version_id for folder in folders if (folder/package_id.lower()/version_id).is_dir())
  nuspec=ET.parse(next(directory.glob('*.nuspec'))).find('{*}metadata');assert nuspec is not None
  license_element=nuspec.find('{*}license');assert license_element is not None
  license_id=license_element.text
  if package_id.lower() in {'quickfixn.core','quickfixn.fix44'}:
   assert version_id=='1.14.1' and license_element.attrib.get('type')=='file' and license_id=='LICENSE'
   assert sha(directory/license_id)=='dcc5ff99d3d63cc29cfc6e9d885641bf814acfb485d1f4893623b1a24819de30'
   license_id='QuickFIX Software License 1.0 (see complete bundled LICENSE)'
  else:assert license_element.attrib.get('type')=='expression' and license_id in {'MIT','Apache-2.0'},(identity,license_id)
  dependencies.append({'id':package_id,'version':version_id,'license':license_id,'copyright':nuspec.findtext('{*}copyright',default=''),'nugetContentHash':entry.get('sha512')})
  for f in directory.iterdir():
   if f.is_file() and (f.name.upper().startswith('LICENSE') or f.name.upper().startswith('THIRD-PARTY-NOTICES')):shutil.copy2(f,licenses/(package_id+'-'+f.name))
 # SDK runtime packs are download dependencies and may be absent from libraries.
 runtime_id='Microsoft.NETCore.App.Runtime.'+a.rid
 runtime_pack=next(folder/runtime_id.lower()/'10.0.15' for folder in folders if (folder/runtime_id.lower()/'10.0.15').is_dir())
 notices=[f for f in runtime_pack.iterdir() if f.is_file() and (f.name.upper().startswith('LICENSE') or f.name.upper().startswith('THIRD-PARTY-NOTICES'))]
 assert any(f.name.upper().startswith('LICENSE') for f in notices) and any(f.name.upper().startswith('THIRD-PARTY-NOTICES') for f in notices),'Runtime redistribution notices required'
 for f in notices:shutil.copy2(f,licenses/(runtime_id+'-'+f.name))
 if runtime_id.lower() not in {d['id'].lower() for d in dependencies}:dependencies.append({'id':runtime_id,'version':'10.0.15','license':'MIT','copyright':'.NET Foundation and contributors; see bundled runtime notices'})
 (package/'DEPENDENCIES.json').write_text(json.dumps({'packages':dependencies,'runtime':'Bundled .NET runtime retains Microsoft/.NET Foundation notices.'},indent=2)+'\n',encoding='utf-8')
 config=json.loads((package/'session-harness.runtimeconfig.json').read_text(encoding='utf-8'))['runtimeOptions'];assert 'includedFrameworks' in config and 'frameworks' not in config
 files=[]
 for f in sorted(package.rglob('*')):
  assert not f.is_symlink()
  if not f.is_file():continue
  path=f.relative_to(package).as_posix();assert not path.lower().endswith(('.pdb','.sqlite','.db')) and '.tests' not in path.lower()
  files.append({'path':path,'bytes':f.stat().st_size,'sha256':sha(f)})
 assert sha(package/'FIX44.xml')=='a8111ec59d33053b45be975bbb7d6d1e9f2b6f4a160d832853fa0d8c627ea434'
 assert b'This product includes software developed by quickfixengine.org' in (package/'README.md').read_bytes()
 manifest={'schema':1,'version':version,'rid':a.rid,'sourceCommit':a.commit,'sourceTree':git('rev-parse','HEAD^{tree}'),'selfContained':True,'sdkVersion':'10.0.404','runtimeVersion':'10.0.15','runtimePackPinsSha256':sha(pins),'runtimeLockHashes':{path.name:sha(path) for path in lock_paths},'localCandidate':a.local_candidate,'originalLicense':'present' if (package/'LICENSE').exists() else 'PENDING_OWNER_DECISION','buildHost':{'os':platform.system(),'architecture':platform.machine()},'runtimeConfig':config,'files':files}
 (package/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 archive=a.out/(name+('.zip' if a.rid=='win-x64' else '.tar.gz'));assert not archive.exists()
 if a.rid=='win-x64':
  with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
   for f in sorted(package.rglob('*')):
    if f.is_file():z.write(f,f.relative_to(work).as_posix())
 else:
  with tarfile.open(archive,'x:gz') as t:
   for f in sorted(package.rglob('*')):
    if f.is_file():
     info=t.gettarinfo(str(f),arcname=f.relative_to(work).as_posix());info.mode=0o755 if f.name in {'session-harness','createdump'} else 0o644;info.uid=info.gid=0;info.uname=info.gname=''
     with f.open('rb') as stream:t.addfile(info,stream)
 result={'archive':str(archive.resolve()),'bytes':archive.stat().st_size,'sha256':sha(archive),'commit':a.commit,'rid':a.rid,'payloadFiles':len(files),'localCandidate':a.local_candidate}
 (work/'archive.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
