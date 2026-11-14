"""Fixed project08 draft signing/publication handoff. Manager operator only.
No new key/secret, no --clobber, no rebuild, no unsigned-public fallback.
"""
import argparse, hashlib, io, json, os, stat, subprocess, tarfile, threading, urllib.request, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPO = 'pouriajamali/fix-session-recovery-harness'
TAG = 'v0.1.0-preview.2'
PREFIX = 'fix-session-recovery-harness-' + TAG
ARCHIVES = {PREFIX + '-win-x64.zip', PREFIX + '-linux-x64.tar.gz', PREFIX + '-source.zip'}
INITIAL = ARCHIVES | {'SHA256SUMS.txt', 'SIGNING-PUBLIC-KEY.pub'}
FINAL = INITIAL | {'SHA256SUMS.txt.sig'}
KEY_SHA = 'a59fbecc53a0b3109212b70a3a51247dbd3529512d189ac2462a27a057dad671'
FINGERPRINT = 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
MANAGER = '01a1a0df-6c77-7bb0-b900-c3b3501198f3'
MANAGEMENT = Path('E:/Codex WorkSpace/Git Projects/portfolio-management/development-management-20261110/wave3-state')

def require(value, cause):
    if not value: raise ValueError(cause)

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result

def read(path):
    path = Path(path)
    require(not path.is_symlink() and path.stat().st_size <= 131072, 'Bounded receipt required')
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_pairs)

def write(path, value):
    payload = (json.dumps(value, indent=2) + '\n').encode()
    require(len(payload) <= 131072, 'Receipt limit')
    with Path(path).open('xb') as stream: stream.write(payload)

def run(command, input_bytes=None, timeout=30):
    result = subprocess.run(command, cwd=ROOT, input=input_bytes, capture_output=True, timeout=timeout)
    require(result.returncode == 0, 'Operator command failed: ' + command[0])
    require(len(result.stdout) <= 131072 and len(result.stderr) <= 131072, 'Operator output limit')
    return result.stdout

class Github:
    def api(self, path):
        return json.loads(run(['gh', 'api', path]).decode(), object_pairs_hook=unique_pairs)
    def release(self, release_id):
        return self.api('repos/' + REPO + '/releases/' + str(release_id))
    def download(self, asset, destination):
        limit = limit_for(asset['name'])
        command = ['gh', 'api', 'repos/' + REPO + '/releases/assets/' + str(asset['id']),
                   '-H', 'Accept: application/octet-stream']
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        timer = threading.Timer(30, process.kill)
        timer.start()
        try:
            copy_bounded(process.stdout, destination, limit)
            require(process.wait(timeout=30) == 0, 'Authenticated asset download failed')
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
    def upload_signature(self, path):
        run(['gh', 'release', 'upload', TAG, str(path), '--repo', REPO])
    def publish(self):
        run(['gh', 'release', 'edit', TAG, '--repo', REPO,
             '--draft=false', '--prerelease', '--latest=false', '--verify-tag'])

def limit_for(name):
    if name in ARCHIVES:
        return 1048576 if name.endswith('-source.zip') else 64 * 1024 * 1024
    return 16384

def copy_bounded(source, path, limit):
    total = 0
    with Path(path).open('xb') as output:
        while True:
            chunk = source.read(65536)
            if not chunk: break
            total += len(chunk)
            require(total <= limit, 'Asset exceeded limit')
            output.write(chunk)

def fresh(path):
    path = Path(path).resolve()
    base = Path('E:/Codex WorkSpace/Git Projects/fix-session-recovery-harness/chat-fix-recovery-roadmap/outputs')
    require(path.is_relative_to(base.resolve()) and path != base.resolve(), 'Owned E operator output required')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Links refused')
    path.mkdir(parents=True, exist_ok=False)
    return path

def assets_by_name(release, expected, draft):
    require(release['draft'] is draft and release['prerelease'] is True and
            release['tag_name'] == TAG, 'Wrong release state')
    entries = release['assets']
    require(len(entries) == len(expected) and {a['name'] for a in entries} == expected, 'Exact asset set')
    require(len({a['id'] for a in entries}) == len(entries), 'Duplicate asset identity')
    for asset in entries:
        require(0 < asset['size'] <= limit_for(asset['name']) and asset['state'] == 'uploaded', 'Asset size/state')
    return {a['name']: a for a in entries}

def check_stage(stage):
    require(stage['schema'] == 'project08-draft-stage-v1' and stage['repository'] == REPO and
            stage['tag'] == TAG and len(stage['commit']) == 40 and
            stage['sdk'] == '10.0.404' and stage['runtime'] == '10.0.15' and
            stage['reportSchema'] == 'fix-session-harness-report-v2', 'Stage identity')
    require(set(stage['nativeProofs']) == {'win-x64', 'linux-x64'} and
            set(stage['assets']) == INITIAL, 'Missing native/stage identities')
    for proof in stage['nativeProofs'].values():
        require(proof['commit'] == stage['commit'] and proof['outcome'] == 'pass' and
                proof['fourCases'] is True and proof['kernelAdmitted'] is True and
                len(proof['receiptSha256']) == 64, 'Actual native proof binding')
    require(stage['assets']['SIGNING-PUBLIC-KEY.pub']['sha256'] == KEY_SHA, 'Trusted key changed')

def authorization(path, expected_sha, stage, purpose):
    path = Path(path).resolve()
    require(path.is_relative_to(MANAGEMENT.resolve()) and sha(path) == expected_sha, 'Trusted manager gate identity')
    gate = read(path)
    require(gate['schema'] == 'project08-operator-authorization-v1' and gate['status'] == 'APPROVED' and
            gate['operatorThreadId'] == MANAGER and gate['purpose'] == purpose and
            gate['repository'] == REPO and gate['tag'] == TAG and
            gate['candidateCommit'] == stage['commit'] and gate['releaseId'] == stage['releaseId'] and
            gate['workflowRunId'] == stage['workflowRunId'], 'Exact operator gate missing')
    return gate

def archive_members(path):
    payload = {}
    total = 0
    def add(name, size, stream):
        nonlocal total
        parts = PurePosixPath(name)
        require(not parts.is_absolute() and '..' not in parts.parts and '\\\\' not in name and
                name not in payload and 0 <= size < 64 * 1024 * 1024, 'Unsafe member')
        total += size
        require(total < 256 * 1024 * 1024 and len(payload) < 512, 'Expanded archive limit')
        value = stream.read(size + 1)
        require(len(value) == size, 'Member size mismatch')
        payload[name] = value
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                require(not stat.S_ISLNK(info.external_attr >> 16), 'Zip symlink')
                if not info.is_dir(): add(info.filename, info.file_size, archive.open(info))
    else:
        with tarfile.open(path, 'r:gz') as archive:
            for info in archive:
                require(info.isfile(), 'Only regular tar entries')
                add(info.name, info.size, archive.extractfile(info))
    roots = {PurePosixPath(name).parts[0] for name in payload}
    require(len(roots) == 1, 'Archive root')
    prefix = next(iter(roots)) + '/'
    return {name[len(prefix):]: value for name, value in payload.items()}

def verify_native(path, stage, rid):
    members = archive_members(path)
    manifest = json.loads(members.pop('BUILD-MANIFEST.json'), object_pairs_hook=unique_pairs)
    require(manifest['sourceCommit'] == stage['commit'] and manifest['sourceTree'] == stage['sourceTree'] and
            manifest['rid'] == rid and manifest['version'] == '0.1.0-preview.2' and
            manifest['selfContained'] and not manifest['localCandidate'] and
            manifest['sdkVersion'] == '10.0.404' and manifest['runtimeVersion'] == '10.0.15', 'Native identity')
    require(set(members) == {f['path'] for f in manifest['files']}, 'Member manifest')
    for item in manifest['files']:
        body = members[item['path']]
        require(len(body) == item['bytes'] and hashlib.sha256(body).hexdigest() == item['sha256'], 'Native member changed')
    require(stage['commit'].encode() in members['session-harness.dll'], 'Embedded source identity')
    require(members['SIGNING-PUBLIC-KEY.pub'] == (ROOT / 'SIGNING-PUBLIC-KEY.pub').read_bytes(), 'Bundled key identity')
    config = json.loads(members['session-harness.runtimeconfig.json'])['runtimeOptions']
    require(config['includedFrameworks'] == [{'name': 'Microsoft.NETCore.App', 'version': '10.0.15'}] and
            'frameworks' not in config, 'Runtime identity')

def verify_bytes(directory, stage, expected, asset_metadata):
    identities = {}
    for name in expected:
        path = directory / name
        value = {'bytes': path.stat().st_size, 'sha256': sha(path)}
        require(value['bytes'] == asset_metadata[name]['size'], 'Actual asset size')
        if name in INITIAL:
            require(value == stage['assets'][name], 'Actual bytes differ from CI stage')
        identities[name] = {**value, 'id': asset_metadata[name]['id']}
    canonical = ''.join(sha(directory / name) + '  ' + name + '\n' for name in sorted(ARCHIVES)).encode()
    require((directory / 'SHA256SUMS.txt').read_bytes() == canonical, 'Noncanonical checksum entries')
    require(sha(directory / 'SIGNING-PUBLIC-KEY.pub') == KEY_SHA, 'Independent public key pin')
    verify_native(directory / (PREFIX + '-win-x64.zip'), stage, 'win-x64')
    verify_native(directory / (PREFIX + '-linux-x64.tar.gz'), stage, 'linux-x64')
    # Source bytes were produced by exact git archive and independently bound by native-stage receipt.
    require('global.json' in archive_members(directory / (PREFIX + '-source.zip')), 'Source archive incomplete')
    return identities

def trusted_key():
    key = ROOT / 'SIGNING-PUBLIC-KEY.pub'
    require(sha(key) == KEY_SHA, 'Known key bytes')
    require(run(['ssh-keygen', '-lf', str(key)], timeout=15).decode().split()[1] == FINGERPRINT,
            'Known fingerprint mismatch')
    return key

def verify_signature(directory):
    key = ROOT / 'SIGNING-PUBLIC-KEY.pub'
    require(sha(key) == KEY_SHA, 'Local trusted key changed')
    fingerprint = run(['ssh-keygen', '-lf', str(key)], timeout=15).decode().split()[1]
    require(fingerprint == FINGERPRINT, 'Known fingerprint mismatch')
    signers = directory / 'allowed-signers'
    with signers.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('pouriajamali ' + key.read_text().strip() + '\n')
    run(['ssh-keygen', '-Y', 'verify', '-f', str(signers), '-I', 'pouriajamali',
         '-n', 'file', '-s', str(directory / 'SHA256SUMS.txt.sig')],
         input_bytes=(directory / 'SHA256SUMS.txt').read_bytes(), timeout=15)

def sign_draft(stage, gate, work, github):
    require(gate['stageReceiptSha256'] == sha(Path(gate['stageReceiptPath'])), 'Bound stage receipt')
    first = work / 'stage-download'; first.mkdir()
    release = github.release(stage['releaseId'])
    initial = assets_by_name(release, INITIAL, True)
    for asset in initial.values(): github.download(asset, first / asset['name'])
    verify_bytes(first, stage, INITIAL, initial)
    # The -f argument is PUBLIC key only. OpenSSH must use the existing agent.
    trusted_key()
    run(['ssh-keygen', '-Y', 'sign', '-f', str(ROOT / 'SIGNING-PUBLIC-KEY.pub'),
         '-n', 'file', str(first / 'SHA256SUMS.txt')], input_bytes=b'', timeout=15)
    verify_signature(first)
    github.upload_signature(first / 'SHA256SUMS.txt.sig')
    second = work / 'actual-signed-draft'; second.mkdir()
    release = github.release(stage['releaseId'])
    actual = assets_by_name(release, FINAL, True)
    for asset in actual.values(): github.download(asset, second / asset['name'])
    identities = verify_bytes(second, stage, FINAL, actual)
    verify_signature(second)
    require(sha(second / 'SHA256SUMS.txt.sig') == sha(first / 'SHA256SUMS.txt.sig'), 'Uploaded signature changed')
    verified = {'schema': 'project08-draft-verified-v1', 'repository': REPO, 'tag': TAG,
                'commit': stage['commit'], 'sourceTree': stage['sourceTree'],
                'workflowRunId': stage['workflowRunId'], 'releaseId': stage['releaseId'],
                'assets': identities, 'fingerprint': FINGERPRINT, 'stage': stage}
    write(work / 'DRAFT-VERIFIED.json', verified)

def publish(verified, gate, work, github):
    stage = verified['stage']
    require(verified['schema'] == 'project08-draft-verified-v1' and verified['fingerprint'] == FINGERPRINT and
            gate['verifiedReceiptSha256'] == sha(Path(gate['verifiedReceiptPath'])) and
            gate['assets'] == verified['assets'], 'Exact six-asset public gate')
    live = assets_by_name(github.release(stage['releaseId']), FINAL, True)
    for name, asset in live.items():
        require(asset['id'] == verified['assets'][name]['id'] and asset['size'] == verified['assets'][name]['bytes'],
                'Draft metadata changed after review')
        require(asset.get('digest') == 'sha256:' + verified['assets'][name]['sha256'], 'Draft digest changed')
    github.publish()
    public = assets_by_name(github.release(stage['releaseId']), FINAL, False)
    for name, asset in public.items():
        require(asset['id'] == verified['assets'][name]['id'], 'Published asset changed')
        url = 'https://github.com/' + REPO + '/releases/download/' + TAG + '/' + name
        with urllib.request.urlopen(url, timeout=30) as response:
            copy_bounded(response, work / name, limit_for(name))
    identities = verify_bytes(work, stage, FINAL, public)
    verify_signature(work)
    require(identities == verified['assets'], 'Published bytes differ from approved draft')
    write(work / 'FINAL-DOWNLOAD-VERIFIED.json', {'status': 'PUBLIC_BYTES_SIGNATURE_VERIFIED',
          'repository': REPO, 'tag': TAG, 'commit': stage['commit'], 'releaseId': stage['releaseId'],
          'assets': identities, 'fingerprint': FINGERPRINT,
          'landingPageReadback': 'REQUIRED_SEPARATELY_BY_MANAGER_BEFORE_FINAL_ACCEPTANCE'})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['sign-draft', 'publish'])
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--authorization-sha256', required=True)
    parser.add_argument('--work', required=True)
    args = parser.parse_args()
    require(os.name == 'nt', 'Existing manager Windows-agent operator only; no agent bridge/config')
    receipt = read(args.receipt)
    stage = receipt if args.mode == 'sign-draft' else receipt['stage']
    check_stage(stage)
    gate = authorization(args.authorization, args.authorization_sha256, stage,
                         'SIGN_DRAFT' if args.mode == 'sign-draft' else 'PUBLISH')
    require(run(['git', 'rev-parse', 'HEAD']).decode().strip() == stage['commit'] and
            not run(['git', 'status', '--porcelain']).strip(), 'Exact clean trusted operator source')
    require(gate['stageReceiptSha256'] == sha(args.receipt) if args.mode == 'sign-draft'
            else gate['verifiedReceiptSha256'] == sha(args.receipt), 'Operator input identity')
    work = fresh(args.work)
    if args.mode == 'sign-draft': sign_draft(stage, gate, work, Github())
    else: publish(receipt, gate, work, Github())

if __name__ == '__main__':
    main()
