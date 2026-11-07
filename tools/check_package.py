"""Execute only own extracted app against its fixed synthetic loopback scenarios."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--commit',required=True);parser.add_argument('--local-candidate',action='store_true');a=parser.parse_args()
 package=a.package.resolve();work=a.work.resolve();work.mkdir(parents=True,exist_ok=False);m=json.loads((package/'BUILD-MANIFEST.json').read_text(encoding='utf-8'))
 assert m['sourceCommit']==a.commit and m['selfContained'] and m['originalLicense']=='present' and m['rid']==('win-x64' if os.name=='nt' else 'linux-x64')
 if not a.local_candidate:assert not m['localCandidate']
 assert {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}=={f['path'] for f in m['files']}|{'BUILD-MANIFEST.json'}
 for f in m['files']:
  p=package/f['path'];assert not p.is_symlink() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
 assert a.commit.encode() in (package/'session-harness.dll').read_bytes() and sha(package/'FIX44.xml')=='a8111ec59d33053b45be975bbb7d6d1e9f2b6f4a160d832853fa0d8c627ea434'
 assert sha(package/'vendor/QUICKFIX-LICENSE')=='dcc5ff99d3d63cc29cfc6e9d885641bf814acfb485d1f4893623b1a24819de30'
 for name in ['CONTRIBUTING.md','docs/CONTRACT.md','docs/CASE-STUDY.md','PROVENANCE.md','LICENSE']:assert (package/name).is_file()
 assert 'This product includes software developed by quickfixengine.org' in (package/'README.md').read_text(encoding='utf-8')
 config=json.loads((package/'session-harness.runtimeconfig.json').read_text(encoding='utf-8'))['runtimeOptions'];assert 'includedFrameworks' in config and 'frameworks' not in config
 checks=['package-manifest-dictionary-licenses-and-document-links'];exe=package/('session-harness.exe' if os.name=='nt' else 'session-harness')
 env=dict(os.environ,DOTNET_ROOT=str(work/'no-installed-dotnet'),DOTNET_ROOT_X64=str(work/'no-installed-dotnet'),DOTNET_MULTILEVEL_LOOKUP='0')
 def run(name,args,code):
  p=subprocess.run([str(exe),*map(str,args)],cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
  (work/(name+'.json')).write_text(json.dumps({'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'command':[str(exe),*map(str,args)]},indent=2)+'\n',encoding='utf-8')
  assert p.returncode==code and not p.stderr,(name,p.returncode,p.stderr);checks.append(name);return p.stdout
 assert m['version'] in run('version',['--version'],0)
 demo=work/'demo with spaces';report=json.loads(run('demo',['demo',demo],0));assert report['complete'] and report['outcome']=='pass' and len(report['scenarios'])==3 and a.commit in report['toolBuild']
 nonce=report['runNonce']
 for s in report['scenarios']:
  name=s['scenario'];folder=demo/name;assert s['complete'] and s['outcome']=='pass'
  for f,h in s['artifactHashes'].items():assert sha(folder/f)==h
  workers=json.loads((folder/'workers.json').read_text(encoding='utf-8'));assert len(workers)==(2 if name=='restart' else 1)
  assert all(w['nonce']==nonce and w['scenario']==name and w['session']=='FIX.4.4:E'+nonce[:12]+'->P'+nonce[:12] and w['cleanStop'] and w['storeClosed'] and w['complete'] for w in workers)
  received=(folder/'engine-to-peer.fix').read_bytes();sent=(folder/'peer-to-engine.fix').read_bytes();assert len(received)+len(sent)<=256*1024
  if name=='gap':assert s['delivered']==['GAP2','GAP3'] and workers[0]['gapRequestDeliveryCount']==0 and sent.count(b'148=GAP2\x01')==2 and sent.count(b'148=GAP3\x01')==1 and b'112=AFTER_DUPLICATE\x01' in received
  if name=='resend':assert s['delivered']==[] and received.count(b'148=RESEND_A\x01')==2 and received.count(b'148=RESEND_B\x01')==2 and received.count(b'43=Y\x01')==2 and received.count(b'122=')==2
  if name=='restart':assert s['connections']==2 and [w['phase'] for w in workers]==['first','second'] and received.count(b'35=A\x01')==2 and received.count(b'148=RESTART_NEWS\x01')==2 and received.count(b'43=Y\x01')==1 and workers[1]['nextSender']>workers[0]['nextSender']
  checks.append('actual-scenario-'+name)
 existing=work/'existing';existing.mkdir();(existing/'sentinel').write_text('untouched',encoding='utf-8')
 assert json.loads(run('refuse-existing',['demo',existing],1))['reason']=='OUTPUT_EXISTS' and (existing/'sentinel').read_text(encoding='utf-8')=='untouched'
 for option in ['--host','--settings','--dictionary','--order']:assert json.loads(run('refuse-'+option[2:],[option,'not-used'],1))['reason']=='CLI_INVALID'
 assert json.loads(run('worker-without-authority',['--owned-worker',str(work/'none'),'0'*32,'gap','single','1'],1))['reason']=='WORKER_ARGUMENT_INVALID'
 assert len(checks)==12
 receipt={'status':'ACTUAL_SELF_CONTAINED_FIXED_FIX_HARNESS_PACKAGE_PASS','commit':a.commit,'rid':m['rid'],'checkCount':len(checks),'checks':checks,'manifestSha256':sha(package/'BUILD-MANIFEST.json'),'scope':'Only fixed synthetic News/admin loopback. Existing hosts, not cleanOS or production/crash/exactlyonce/performance proof.'}
 (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':receipt['status'],'checks':len(checks),'rid':m['rid']}))
if __name__=='__main__':main()
