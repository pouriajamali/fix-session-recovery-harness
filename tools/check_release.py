# Adapted from Pouria Jamali's public MIT sqlite-recovery-drill (003b700d); see NOTICE.md.
"""Check exact already-tested runtime archives; source packaging only, no binary rebuild."""
import argparse,hashlib,json,subprocess,tarfile,zipfile
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
 assert tag=='v0.1.0-preview.2' and run_id.isdigit()
 native={}
 for rid in ('win-x64','linux-x64'):
  path=proof_root/rid/'native-proof.json';proof=bounded_json(path)
  assert proof['schema']=='project08-native-proof-v1' and proof['commit']==commit and proof['rid']==rid
  assert str(proof['workflowRunId'])==run_id,'Proof belongs to another CI run'
  assert proof['sdk']=='10.0.404' and proof['runtime']=='10.0.15' and proof['outcome']=='pass'
  assert proof['fourCases'] is True and proof['kernelAdmitted'] is True and proof['terminal'] is True
  # Native owner seals these concrete proof files after actual admitted execution.
  required={'tests','consumer','kernel','subprocessMembership','terminal'}
  assert set(proof['files'])==required
  for item in proof['files'].values():
   relative=PurePosixPath(item['path'])
   assert not relative.is_absolute() and '..' not in relative.parts
   actual=path.parent/item['path'];assert actual.is_file() and not actual.is_symlink()
   assert hashlib.sha256(actual.read_bytes()).hexdigest()==item['sha256']
  tests=bounded_json(path.parent/proof['files']['tests']['path'])
  consumer=bounded_json(path.parent/proof['files']['consumer']['path'])
  assert tests['failed']==0 and tests['passed']>0
  observations={v['name']:v['result'] for v in tests['observations']}
  assert all(observations.get(name)=='pass' for name in (
   'all-four-real-loopback-scenarios-and-raw-hashes','gapfill-wrong-newseqno-is-completed-fail2',
   'strict-process-diagnostic-bindings-and-nullable-exit','process-sidecar-collision-preserves-original-cause'))
  assert consumer['commit']==commit and consumer['rid']==rid and consumer['status']=='ACTUAL_SELF_CONTAINED_FIXED_FIX_HARNESS_PACKAGE_PASS'
  assert all('actual-scenario-'+name in consumer['checks'] for name in ('gap','resend','restart','gapfill'))
  terminal=bounded_json(path.parent/proof['files']['terminal']['path'])
  member=bounded_json(path.parent/proof['files']['subprocessMembership']['path'])
  assert terminal['terminal'] is True and terminal['exitCode']==0 and terminal['project']=='08'
  assert member['member'] is True and member['nonce']==terminal['nonce'] and member['project']=='08'
  assert member['pid']==consumer['consumerPid'],'Consumer/subprocess binding'
  kernel=bounded_json(path.parent/proof['files']['kernel']['path'])
  if rid=='win-x64':
   assert kernel['mechanism']=='windows-job' and member['mechanism']=='windows-job'
   assert kernel['job']==member['job'] and kernel['memoryBytes']==2147483648 and kernel['processLimit']==256
   assert int(kernel['cpuAffinity']).bit_count()==2 and kernel['threadLimitClaim'] is False
  else:
   assert kernel['mechanism']=='cgroup-v2' and kernel['membership']==member['membership']
   values=kernel['limits'];quota,period=values['cpu.max'].split()
   assert quota!='max' and int(quota)<=2*int(period) and int(values['memory.max'])<=2147483648
   assert values['memory.swap.max']=='0' and int(values['pids.max'])<=256
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
 assert draft['tag_name']==stage['tag']=='v0.1.0-preview.2'
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
if __name__=='__main__':main()
