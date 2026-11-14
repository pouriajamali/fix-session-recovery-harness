"""Fixed project08 local phases. No command forwarding, SDK install or host-wide PID scan.
Execution requires the manager's exact file-bound admission and canonical lane membership.
This source is not its own kernel qualification. No target may run on a failed guard.
"""
import time
_ENTRY_MONOTONIC = time.monotonic()
import argparse, ctypes, hashlib, json, os, platform, secrets, subprocess, sys, tarfile, threading, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'tools/project08-profile.json'
WIN_ROOT = 'E:/Codex WorkSpace/Git Projects/fix-session-recovery-harness/implementation/wave3-m1'

def native(value):
    value = str(value).replace(chr(92), '/')
    if os.name != 'nt' and value.startswith('E:/'):
        return '/mnt/e/' + value[3:]
    return value

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def require(value, why):
    if not value:
        raise RuntimeError(why)

def read(path):
    path = Path(path)
    require(path.stat().st_size <= 65536 and not path.is_symlink(), 'Bounded regular input required')
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, value):
    payload = (json.dumps(value, indent=2) + '\n').encode()
    require(len(payload) <= 65536, 'Receipt size')
    with Path(path).open('xb') as stream:
        stream.write(payload)

def load_admission(phase):
    profile = read(PROFILE)
    require(ROOT.resolve() == Path(native(WIN_ROOT)).resolve(), 'Wrong allocated project root')
    admission_path = Path(native(profile['admissionWindows']))
    admission = read(admission_path)
    require(admission['schema'] == 'project08-runtime-admission-v1' and
            admission['status'] in ('ADMITTED', 'PROFILE_PROBE_ONLY') and admission['project'] == '08', 'Manager admission pending')
    require(admission['status'] == 'ADMITTED' or phase == 'probe', 'Probe authority cannot execute target')
    require(digest(native(profile['sharedInputBindings']['path'])) == profile['sharedInputBindings']['sha256'], 'Shared inputs binding')
    require(admission['profileSha256'] == digest(PROFILE) and
            admission['launcherSha256'] == digest(__file__), 'Profile/launcher identity')
    require(admission['approvedM0Sha256'] == profile['approvedM0Sha256'] and
            admission['approvalReceiptSha256'] == profile['approvalReceiptSha256'], 'Contract identity')
    require(admission['canonicalLaneParticipant08'] is True and
            (admission['kernelQualification']['status'] == 'ADMITTED' or
             phase == 'probe' and admission['status'] == 'PROFILE_PROBE_ONLY'), 'Lane/kernel qualification')
    rid = 'win-x64' if os.name == 'nt' else 'linux-x64'
    tool = admission['inputs'][rid]
    require(tool['sdkVersion'] == '10.0.404' and tool['runtimeVersion'] == '10.0.15', 'Tool versions')
    executable = Path(native(tool['dotnetPath']))
    require(digest(executable) == tool['dotnetSha256'], 'Admitted SDK executable changed')
    producer = Path(native(tool['producerReceipt']))
    require(digest(producer) == tool['producerReceiptSha256'], 'Producer proof identity')
    require(admission['packageHelperSha256'] == digest(ROOT / 'tools/package.py'),
            'Package helper identity')
    if phase == 'recovery-lock':
        require(rid == 'win-x64', 'Recovery is Windows-only')
        binding = admission['recoveryAmendment']
        require(binding['sha256'] == profile['recoveryLock']['amendmentSha256'] and
                digest(native(binding['path'])) == binding['sha256'], 'Recovery amendment binding')
    return profile, admission, executable, rid

def fixed_commands(phase, dotnet, rid, evidence, sha, nonce):
    if phase == 'probe':
        return [[sys.executable, str(Path(__file__).resolve()), '--phase', 'probe',
                 '--commit', sha, '--evidence', str(evidence), '--witness',
                 '--nonce', nonce, '--parent-pid', str(os.getpid())]]
    tests = 'tests/SessionHarness.Tests'
    if phase in ('lock', 'recovery-lock'):
        return [[str(dotnet), 'restore', tests, '-p:RuntimeIdentifier=' + rid, '--use-lock-file',
                 '--force-evaluate', '--disable-parallel', '-p:SelfContained=true',
                 '-p:RuntimeFrameworkVersion=10.0.15', '-p:NuGetAuditMode=all', '-p:DisableTransitiveFrameworkReferenceDownloads=true'],
                [sys.executable, 'tools/package.py', '--rid', rid, '--commit', sha,
                 '--work', str(evidence / 'unused'), '--out', str(evidence / 'unused-out'), '--write-runtime-pins', '--dotnet', str(dotnet)]]
    if phase == 'restore':
        return [[str(dotnet), 'restore', tests, '-p:RuntimeIdentifier=' + rid, '-p:SelfContained=true', '--locked-mode', '--disable-parallel', '-p:NuGetAuditMode=all', '-p:DisableTransitiveFrameworkReferenceDownloads=true']]
    if phase == 'build':
        return [[str(dotnet), 'build', tests, '-c', 'Release', '-p:RuntimeIdentifier=' + rid, '-p:SelfContained=true', '--no-restore',
                 '-m:1', '-p:DisableTransitiveFrameworkReferenceDownloads=true', '-p:BuildInParallel=false', '-p:UseSharedCompilation=false', '-nodeReuse:false']]
    if phase == 'tests':
        return [[str(dotnet), 'run', '--project', tests, '-c', 'Release',
                 '-p:RuntimeIdentifier=' + rid, '-p:SelfContained=true', '--no-build', '--no-restore', '--', '--work', str(evidence / 'tests')],
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'release_candidate_test.py', '-v']]
    if phase in ('package', 'package-retry'):
        return [[sys.executable, 'tools/package.py', '--rid', rid, '--commit', sha,
                 '--dotnet', str(dotnet), '--work', str(evidence / 'build'),
                 '--out', str(evidence / 'delivery')]]
    require(phase == 'consumer', 'Unknown phase')
    # Consumer input is exact candidate's package output supplied in manager-bound handoff.
    return [[sys.executable, 'tools/check_package.py', '--package', str(evidence / 'extracted' / ('fix-session-recovery-harness-v0.1.0-preview.2-' + rid)),
             '--work', str(evidence / 'consumer'), '--commit', sha]]

def linux_limits(nonce):
    relative = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1]
    require('project08-' + nonce in relative, 'Not in owned project08 unit')
    group = Path('/sys/fs/cgroup') / relative.lstrip('/')
    values = {name: (group / name).read_text().strip() for name in
              ('cpu.max', 'memory.max', 'memory.swap.max', 'pids.max')}
    quota, period = values['cpu.max'].split()
    require(quota != 'max' and int(quota) <= 2 * int(period), 'CPU hard cap')
    require(int(values['memory.max']) <= 2147483648 and
            values['memory.swap.max'] == '0' and int(values['pids.max']) <= 256, 'Memory/task hard caps')
    return {'mechanism': 'cgroup-v2', 'group': str(group), 'membership': relative, 'limits': values}

def windows_api():
    from ctypes import wintypes as w
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    class BASIC(ctypes.Structure):
        _fields_ = [('user', ctypes.c_longlong), ('jobtime', ctypes.c_longlong),
                    ('flags', w.DWORD), ('minwork', ctypes.c_size_t), ('maxwork', ctypes.c_size_t),
                    ('processes', w.DWORD), ('affinity', ctypes.c_size_t),
                    ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ('r', 'w', 'o', 'rb', 'wb', 'ob')]
    class EXT(ctypes.Structure):
        _fields_ = [('basic', BASIC), ('io', IO), ('processmem', ctypes.c_size_t),
                    ('jobmem', ctypes.c_size_t), ('peakproc', ctypes.c_size_t), ('peakjob', ctypes.c_size_t)]
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]; k.CreateJobObjectW.restype = w.HANDLE
    k.OpenJobObjectW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]; k.OpenJobObjectW.restype = w.HANDLE
    k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    k.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
    k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    k.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
    k.GetCurrentProcess.restype = w.HANDLE
    k.GetProcessAffinityMask.argtypes = [w.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    k.CloseHandle.argtypes = [w.HANDLE]
    return k, w, EXT

def windows_limits(nonce):
    k, w, EXT = windows_api()
    job = k.OpenJobObjectW(4, False, 'Local\\project08-' + nonce)
    require(job, 'Owned Job unavailable')
    try:
        member = w.BOOL()
        require(k.IsProcessInJob(k.GetCurrentProcess(), job, ctypes.byref(member)) and member.value, 'Parent job membership')
        limits = EXT()
        require(k.QueryInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits), None), 'Job query')
        flags = limits.basic.flags
        require(flags & 0x200 and flags & 0x8 and flags & 0x10 and flags & 0x2000 and
                not flags & (0x800 | 0x1000), 'Required job flags')
        require(limits.jobmem == 2147483648 and limits.basic.processes == 256 and
                int(limits.basic.affinity).bit_count() == 2, 'Job limits')
        return {'mechanism': 'windows-job', 'job': 'Local\\project08-' + nonce,
                'memoryBytes': limits.jobmem, 'processLimit': limits.basic.processes,
                'cpuAffinity': limits.basic.affinity, 'threadLimitClaim': False}
    finally:
        k.CloseHandle(job)

def own_start_identity():
    if os.name != 'nt':
        return Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
    from ctypes import wintypes as w
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = w.HANDLE
    values = [ctypes.c_ulonglong() for _ in range(4)]
    k.GetProcessTimes.argtypes = [w.HANDLE, *([ctypes.c_void_p] * 4)]
    require(k.GetProcessTimes(k.GetCurrentProcess(), *(ctypes.byref(v) for v in values)), 'Own start identity')
    return str(values[0].value)

def windows_start(command, cwd, nonce, timeout, evidence, hard_deadline=None):
    from ctypes import wintypes as w
    k, w, EXT = windows_api()
    class STARTUP(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR),
                    ('title', w.LPWSTR), ('x', w.DWORD), ('y', w.DWORD), ('xs', w.DWORD),
                    ('ys', w.DWORD), ('xc', w.DWORD), ('yc', w.DWORD), ('fill', w.DWORD),
                    ('flags', w.DWORD), ('show', w.WORD), ('reserved2size', w.WORD),
                    ('reserved2', ctypes.c_void_p), ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]
    class PROCESS(ctypes.Structure):
        _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]
    k.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR,
                                ctypes.POINTER(STARTUP), ctypes.POINTER(PROCESS)]
    k.ResumeThread.argtypes = [w.HANDLE]; k.ResumeThread.restype = w.DWORD
    k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    k.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
    k.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
    def active_count(job):
        accounting = ctypes.create_string_buffer(48)
        require(k.QueryInformationJobObject(job, 1, accounting, 48, None), 'Owned job accounting')
        return ctypes.c_uint32.from_buffer(accounting, 40).value
    job = k.CreateJobObjectW(None, 'Local\\project08-' + nonce)
    require(job, 'Job creation')
    info = PROCESS()
    assigned = False
    try:
        process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
        require(k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(process_mask),
                                        ctypes.byref(system_mask)), 'Affinity query')
        cpus = [1 << bit for bit in range(64) if process_mask.value & (1 << bit)]
        require(len(cpus) >= 2, 'Two CPUs not available')
        limits = EXT()
        limits.basic.flags = 0x200 | 0x8 | 0x10 | 0x2000
        limits.basic.processes = 256
        limits.basic.affinity = cpus[0] | cpus[1]
        limits.jobmem = 2147483648
        require(k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)), 'Job configure')
        startup = STARTUP(); startup.cb = ctypes.sizeof(startup)
        line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
        require(k.CreateProcessW(None, line, None, None, False, 0x4 | 0x08000000, None,
                                 str(cwd), ctypes.byref(startup), ctypes.byref(info)), 'Suspended process creation')
        require(k.AssignProcessToJobObject(job, info.process), 'Suspended child assignment')
        assigned = True
        member = w.BOOL()
        require(k.IsProcessInJob(info.process, job, ctypes.byref(member)) and member.value, 'Child job membership')
        if hard_deadline is not None:
            timeout = min(timeout, hard_deadline - time.monotonic() - 6)
            require(timeout > 0, 'Whole recovery deadline before resume/wait')
        require(k.ResumeThread(info.thread) != 0xffffffff, 'Resume child')
        waited = k.WaitForSingleObject(info.process, int(timeout * 1000))
        grace_started = time.monotonic()
        deadline = grace_started + 3  # Existing reserve only; never a second grace period.
        if hard_deadline is not None:
            deadline = min(deadline, hard_deadline - 3)  # Bookkeeping stays inside90.
        samples = []
        def sample(stage):
            count = active_count(job)
            if len(samples) < 32 or stage in ('end-of-grace', 'after-deadline-cleanup'):
                samples.append({'elapsedMs': round((time.monotonic() - grace_started) * 1000, 3),
                                'activeProcesses': count, 'stage': stage})
            return count
        root_exit_observed, root_exit_code = False, None
        cleanup_requested, cleanup_succeeded = False, None
        if waited == 0:
            actual = w.DWORD()
            require(k.GetExitCodeProcess(info.process, ctypes.byref(actual)), 'Observed root exit')
            root_exit_observed, root_exit_code = True, int(actual.value)
            controller_code = root_exit_code
        else:
            # The original target deadline has already expired (or wait failed).
            controller_code = 124 if waited == 258 else 125
            cleanup_requested = True
            sample('before-root-timeout-or-wait-failure-cleanup')
            cleanup_succeeded = bool(k.TerminateJobObject(job, controller_code))

        active = sample('after-root-wait')
        while active and time.monotonic() < deadline:
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
            active = sample('cleanup-drain' if cleanup_requested else 'natural-drain')

        active = sample('end-of-grace')
        if active and not cleanup_requested:
            # A successful root exit is not yet an empty job. Observe the entire
            # existing reserve before deciding that owned-process cleanup is needed.
            cleanup_requested = True
            controller_code = 125
            cleanup_succeeded = bool(k.TerminateJobObject(job, 125))
            active = sample('after-deadline-cleanup')

        terminal = active == 0
        if not root_exit_observed and k.WaitForSingleObject(info.process, 0) == 0:
            actual = w.DWORD()
            require(k.GetExitCodeProcess(info.process, ctypes.byref(actual)), 'Observed root exit after cleanup')
            root_exit_observed, root_exit_code = True, int(actual.value)

        # Even if forced cleanup obtains an empty job, it cannot convert failure
        # into success. A still-active/unobserved tree retains its canonical lease.
        if cleanup_requested and controller_code == 0:
            controller_code = 125
        write(evidence / 'windows-job-terminal.json', {
            'schema': 'project08-job-terminal-v1', 'project': '08', 'nonce': nonce,
            'ownedRootPid': int(info.pid), 'rootWaitResult': int(waited) & 0xffffffff,
            'rootExitObserved': root_exit_observed, 'rootExitCode': root_exit_code,
            'graceLimitSeconds': 3, 'graceElapsedSeconds': time.monotonic() - grace_started,
            'samples': samples, 'cleanupRequested': cleanup_requested,
            'cleanupCallSucceeded': cleanup_succeeded, 'controllerExitCode': controller_code,
            'terminal': terminal, 'unexplainedActiveCountCause': 'UNKNOWN'})
        return controller_code, terminal
    finally:
        # If assignment failed, terminate only the exact created suspended process.
        if info.process and not assigned:
            k.TerminateProcess(info.process, 125)
            k.WaitForSingleObject(info.process, 3000)
        if info.thread: k.CloseHandle(info.thread)
        if info.process: k.CloseHandle(info.process)
        k.CloseHandle(job)

def linux_environment():
    environment = dict(os.environ)
    environment['XDG_RUNTIME_DIR'] = '/run/user/1000'
    environment['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/run/user/1000/bus'
    return environment

def child_membership(child, nonce):
    if os.name == 'nt':
        k, w, unused = windows_api()
        job = k.OpenJobObjectW(4, False, 'Local\\project08-' + nonce)
        require(job, 'Owned job unavailable for exact child membership')
        try:
            belongs = w.BOOL()
            require(k.IsProcessInJob(w.HANDLE(int(child._handle)), job, ctypes.byref(belongs)) and
                    belongs.value, 'Exact subprocess is outside admitted job')
            return {'schema': 'project08-child-membership-v1', 'project': '08', 'nonce': nonce,
                    'pid': child.pid, 'mechanism': 'windows-job', 'member': True,
                    'job': 'Local\\project08-' + nonce, 'observedThreadCount': None,
                    'threadObservation': 'UNKNOWN; active-process cap is not a thread cap'}
        finally:
            k.CloseHandle(job)
    parent = linux_limits(nonce)
    relative = (Path('/proc') / str(child.pid) / 'cgroup').read_text().strip().split('::', 1)[1]
    require(relative == parent['membership'], 'Exact subprocess is outside admitted cgroup')
    return {'schema': 'project08-child-membership-v1', 'project': '08', 'nonce': nonce,
            'pid': child.pid, 'mechanism': 'cgroup-v2', 'member': True, 'membership': relative}

def bounded_command(command, evidence, index, env, remaining, nonce):
    started = time.monotonic()
    child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    counts, overflow, errors, drains = [0, 0], [False, False], [], []
    failure, reason, kill_requested = None, 'NOT_COMPLETED', False
    def drain(stream, which, filename):
        try:
            with (evidence / filename).open('xb') as output:
                stored = 0
                while True:
                    block = stream.read(4096)
                    if not block: break
                    counts[which] = min(1048576, counts[which] + len(block))
                    take = min(len(block), 131072 - stored)
                    if take:
                        output.write(block[:take])
                        stored += take
                    if take < len(block): overflow[which] = True
        except Exception as error:
            errors.append(type(error).__name__)
    try:
        membership = child_membership(child, nonce)
        write(evidence / (str(index) + '-subprocess-membership.json'), membership)
        drains = [
            threading.Thread(target=drain, args=(child.stdout, 0, str(index) + '-stdout.log'), daemon=True),
            threading.Thread(target=drain, args=(child.stderr, 1, str(index) + '-stderr.log'), daemon=True)]
        for worker in drains: worker.start()
        code = child.wait(timeout=max(0.001, remaining - (time.monotonic() - started)))
        require(code == 0, 'Target phase failed')
        reason = 'COMPLETE'
    except Exception as error:
        failure = error
        reason = 'TARGET_TIMEOUT' if isinstance(error, subprocess.TimeoutExpired) else 'TARGET_PHASE_FAILURE'
        if child.poll() is None:
            kill_requested = True
            child.kill()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
    finally:
        # One existing three-second drain allowance shared by both streams.
        drain_deadline = time.monotonic() + 3
        for worker in drains:
            worker.join(timeout=max(0, drain_deadline - time.monotonic()))
        drain_complete = bool(drains) and not any(worker.is_alive() for worker in drains)
        if failure is None and (not drain_complete or errors or any(overflow)):
            reason = 'OUTPUT_OR_DRAIN_FAILURE'
            failure = RuntimeError(reason)
        result = {
            'schema': 'project08-target-result-v1', 'project': '08', 'nonce': nonce,
            'index': index, 'pid': child.pid, 'reason': reason, 'complete': failure is None,
            'elapsedSeconds': time.monotonic() - started,
            'exitObserved': child.poll() is not None, 'exitCode': child.returncode,
            'deadlineExpired': reason == 'TARGET_TIMEOUT', 'killRequested': kill_requested,
            'drainComplete': drain_complete, 'stdoutBytesObserved': counts[0],
            'stderrBytesObserved': counts[1], 'stdoutOverflow': overflow[0],
            'stderrOverflow': overflow[1]}
        try:
            write(evidence / (str(index) + '-subprocess-result.json'), result)
        except Exception:
            if failure is None: raise
            # Preserve the original target failure when its diagnostic cannot persist.
    if failure is not None:
        raise failure

def extract_native(evidence, rid, sha, profile, admission):
    stage = (qualified_retry_producer(profile, admission, argparse.Namespace(commit=sha))
             if rid == 'win-x64' else evidence.parent / 'package')
    metadata = read(stage / 'build/archive.json')
    require(metadata['commit'] == sha and metadata['rid'] == rid and
            metadata['localCandidate'] is False, 'Exact native archive identity')
    filename = 'fix-session-recovery-harness-v0.1.0-preview.2-' + rid
    archive = stage / 'delivery' / (filename + ('.zip' if rid == 'win-x64' else '.tar.gz'))
    require(archive.stat().st_size <= 64*1024*1024 and digest(archive) == metadata['sha256'], 'Native archive hash')
    destination = evidence / 'extracted'
    destination.mkdir()
    total, count = 0, 0
    def member(name, size, stream):
        nonlocal total, count
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and
                chr(92) not in name and path.parts[0] == filename, 'Archive path')
        total += size; count += 1
        require(total <= 256*1024*1024 and count <= 512 and size <= 64*1024*1024, 'Archive bound')
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            remaining = size
            while remaining:
                block = stream.read(min(65536, remaining))
                require(block, 'Truncated member')
                output.write(block); remaining -= len(block)
        if rid == 'linux-x64' and target.name in ('session-harness', 'createdump'):
            target.chmod(0o755)
    if rid == 'win-x64':
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                require((item.external_attr >> 16) & 0o170000 != 0o120000, 'Archive link')
                if not item.is_dir():
                    with bundle.open(item) as stream: member(item.filename, item.file_size, stream)
    else:
        with tarfile.open(archive, 'r:gz') as bundle:
            for item in bundle:
                require(item.isfile(), 'Archive nonregular member')
                with bundle.extractfile(item) as stream: member(item.name, item.size, stream)

def inside(args, profile, admission, dotnet, rid):
    evidence = Path(args.evidence)
    limits = windows_limits(args.nonce) if os.name == 'nt' else linux_limits(args.nonce)
    write(evidence / 'kernel-membership.json', limits)
    env = dict(os.environ) if os.name == 'nt' else linux_environment()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    for name in ('DOTNET_CLI_HOME', 'NUGET_PACKAGES', 'TMP', 'TEMP', 'TMPDIR'):
        target = fixed_state(profile, rid) / 'state' / name.lower()
        target.mkdir(parents=True, exist_ok=True)
        env[name] = str(target)
    env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
               DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',
               MSBUILDDISABLENODEREUSE='1', DOTNET_ROOT=str(dotnet.parent))
    start = time.monotonic()
    recovery = inside_recovery(profile, admission, args) if args.phase == 'recovery-lock' else None
    if args.phase == 'package-retry': recovery = package_retry_child(profile, args)
    if args.phase == 'consumer': extract_native(evidence, rid, args.commit, profile, admission)
    cap = profile['phases'][args.phase]
    failure = None
    try:
        for index, command in enumerate(fixed_commands(args.phase, dotnet, rid, evidence, args.commit, args.nonce)):
            remaining = cap - (time.monotonic() - start)
            if recovery is not None:
                remaining = min(remaining, recovery['deadlineMonotonic'] - time.monotonic() - 12)
            require(remaining > 0, 'Phase deadline')
            bounded_command(command, evidence, index, env, remaining, args.nonce)
        if args.phase in ('lock', 'recovery-lock', 'restore'):
            from package import validate_rid_outputs
            validate_rid_outputs(rid)
    except Exception as error:
        failure = error
    result = {'phase': args.phase, 'complete': failure is None,
              'outcome': 'pass' if failure is None else 'incomplete',
              'reason': 'COMPLETE' if failure is None else
                  ('TARGET_TIMEOUT' if isinstance(failure, subprocess.TimeoutExpired) else 'TARGET_PHASE_FAILURE'),
              'elapsedSeconds': time.monotonic() - start, 'project': '08',
              'nonce': args.nonce, 'candidate': args.commit}
    try:
        write(evidence / 'phase-result.json', result)
    except Exception:
        if failure is None: raise
    if failure is not None: raise failure
    return 0

def fixed_state(profile, rid):
    path = Path(native(profile['evidenceRootWindows'])) / 'native-qualification' / rid
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Fixed state link refused')
    path.mkdir(parents=True, exist_ok=True)
    return path

def replace_owned_json(path, value, token):
    pending = path.with_name(path.name + '.pending-' + token)
    write(pending, value)
    os.replace(pending, path)

def current_head():
    gitdir = ROOT / '.git'
    head = (gitdir / 'HEAD').read_text().strip()
    if head.startswith('ref: '):
        ref = head[5:]
        require(ref == 'refs/heads/codex/wave3-m1-20261114', 'Allocated branch identity')
        path = gitdir / ref
        if path.exists():
            head = path.read_text().strip()
        else:
            packed = gitdir / 'packed-refs'
            require(packed.stat().st_size <= 1048576, 'Packed ref metadata bound')
            matches = [line.split()[0] for line in packed.read_text().splitlines()
                       if line and not line.startswith(('#', '^')) and line.split()[-1] == ref]
            require(len(matches) == 1, 'Branch ref unavailable')
            head = matches[0]
    require(len(head) == 40 and all(c in '0123456789abcdef' for c in head), 'Source HEAD identity')
    return head

def source_snapshot(profile, commit):
    packet = Path(native(profile['approvedPacketWindows']))
    require(digest(packet) == profile['approvedM0Sha256'], 'Approved source allowance identity')
    paths = {entry['path'] for entry in read(packet)['proposal']['allowedFilesProposed']}
    paths.update(('tools/project08_launch.py', 'tools/project08-profile.json',
                  'src/SessionHarness/Wire.cs', 'src/SessionHarness/SessionHarness.csproj',
                  'tests/SessionHarness.Tests/SessionHarness.Tests.csproj',
                  'src/SessionHarness/packages.lock.json', 'tests/SessionHarness.Tests/packages.lock.json',
                  'vendor/FIX44.xml', 'vendor/QUICKFIX-LICENSE', 'LICENSE', 'SIGNING-PUBLIC-KEY.pub'))
    files = {}
    for relative in sorted(paths):
        path = ROOT / relative
        require(not path.is_symlink(), 'Source link refused')
        files[relative] = digest(path) if path.is_file() else None
    return {'commit': commit, 'fileHashes': files}

def empty_budget(profile, rid, commit):
    return {'schema': 'project08-native-budget-v2', 'project': '08', 'rid': rid,
            'candidate': commit, 'nativeCeilingSeconds': profile['nativeTotalSeconds'],
            'elapsedSeconds': 0, 'recoveryChargedSeconds': 0, 'attempts': []}

def validate_budget(budget, profile, rid):
    require(budget['schema'] == 'project08-native-budget-v2' and budget['project'] == '08' and
            budget['rid'] == rid and budget['nativeCeilingSeconds'] == 900 and
            budget['elapsedSeconds'] >= 0 and
            len(budget['attempts']) <= 16, 'Fixed RID budget identity/exhaustion')

def recovery_origin():
    require(os.name == 'nt', 'Recovery is Windows-only')
    # Include interpreter startup and all admission/setup work, mapped once to monotonic.
    created_unix = int(own_start_identity()) / 10000000 - 11644473600
    age = time.time() - created_unix
    require(age >= 0, 'Controller creation clock is ambiguous')
    return min(_ENTRY_MONOTONIC, time.monotonic() - age)

def reserve_recovery(profile, admission, args, holder, origin):
    config = profile['recoveryLock']
    require(os.name == 'nt' and config['rid'] == 'win-x64' and
            config['maxAttempts'] == 1 and config['totalAttemptSeconds'] == 90 and
            config['reservedNativeDebitSeconds'] == 90, 'Fixed one-shot recovery contract')
    state = fixed_state(profile, 'win-x64')
    marker_path = state / config['markerName']
    result_path = state / config['resultName']
    require(not marker_path.exists() and not result_path.exists(), 'Recovery already used or ambiguous; no third attempt')
    original = state / config['originalFailure']['relativeTerminal']
    require(digest(original) == config['originalFailure']['sha256'], 'Original failure identity')
    original_receipt = read(original)
    require(original_receipt['phase'] == 'lock' and original_receipt['exitCode'] == 1 and
            original_receipt['terminal'] is True, 'Original failed lock remains a failure')
    budget_path = state / config['nativeBudgetName']
    budget = read(budget_path) if budget_path.exists() else empty_budget(profile, 'win-x64', args.commit)
    validate_budget(budget, profile, 'win-x64')
    require(budget['candidate'] == args.commit and budget['recoveryChargedSeconds'] == 0 and
            budget['elapsedSeconds'] + 90 <= 900, 'Cannot reserve recovery without existing native allowance')
    admission_path = Path(native(profile['admissionWindows']))
    marker = {
        'schema': 'project08-recovery-marker-v1', 'status': 'STARTED', 'project': '08', 'rid': 'win-x64',
        'originalFailureId': 'WIN_LOCK_01', 'originalFailureSha256': digest(original),
        'originalFailedLockSecondsSpent': 180, 'amendmentSha256': config['amendmentSha256'],
        'launcherSha256': digest(__file__), 'profileSha256': digest(PROFILE),
        'packageHelperSha256': digest(ROOT / 'tools/package.py'),
        'inputAdmissionSha256': digest(admission_path),
        'sharedInputBindingSha256': profile['sharedInputBindings']['sha256'],
        'presealSource': source_snapshot(profile, args.commit),
        'nonce': holder['randomToken'], 'ownerPID': holder['ownerPID'],
        'ownerProcessStartIdentity': holder['ownerProcessStartIdentity'],
        'startedAtUnixUtc': time.time(), 'originMonotonic': origin,
        'deadlineMonotonic': origin + 90, 'totalAttemptLimitSeconds': 90,
        'reservedNativeDebitSeconds': 90, 'evidenceDirectory': str(Path(args.evidence).resolve()),
        'cacheDirectory': str(state / 'state' / 'nuget_packages')}
    # This immutable CreateNew is the opportunity. Interrupted STARTED remains USED.
    write(marker_path, marker)
    marker_sha = digest(marker_path)
    budget['elapsedSeconds'] += 90
    budget['recoveryChargedSeconds'] = 90
    budget['recoveryMarkerSha256'] = marker_sha
    budget['attempts'].append({'phase': 'recovery-lock', 'state': 'STARTED', 'reservedSeconds': 90,
                               'markerSha256': marker_sha, 'evidence': str(Path(args.evidence).resolve())})
    replace_owned_json(budget_path, budget, holder['randomToken'])
    return {'marker': marker, 'markerPath': marker_path, 'markerSha256': marker_sha,
            'budget': budget, 'budgetPath': budget_path, 'resultPath': result_path}

def inside_recovery(profile, admission, args):
    state = fixed_state(profile, 'win-x64')
    marker = read(state / profile['recoveryLock']['markerName'])
    require(marker['status'] == 'STARTED' and marker['project'] == '08' and marker['rid'] == 'win-x64' and
            marker['nonce'] == args.nonce and marker['ownerPID'] == os.getppid() and
            marker['launcherSha256'] == digest(__file__) and marker['profileSha256'] == digest(PROFILE) and
            marker['packageHelperSha256'] == digest(ROOT / 'tools/package.py') and
            marker['inputAdmissionSha256'] == digest(native(profile['admissionWindows'])) and
            marker['evidenceDirectory'] == str(Path(args.evidence).resolve()), 'Bound recovery child identity')
    require(time.monotonic() < marker['deadlineMonotonic'], 'Whole recovery window exhausted')
    return marker

def finish_recovery(context, args, terminal, code, setup_elapsed):
    marker, budget = context['marker'], context['budget']
    elapsed = time.monotonic() - marker['originMonotonic']
    charge = max(90, elapsed)
    budget['elapsedSeconds'] += charge - budget['recoveryChargedSeconds']
    budget['recoveryChargedSeconds'] = charge
    budget['recoveryElapsedSecondsObserved'] = elapsed
    budget['attempts'][-1]['state'] = 'TERMINAL_ACCOUNTING_PENDING' if terminal else 'AMBIGUOUS_USED'
    budget['attempts'][-1]['observedControllerCode'] = code
    files = {}
    for name in ('SessionHarness.lock.json', 'SessionHarness.Tests.lock.json', 'RUNTIME-PACKS.json'):
        path = ROOT / 'locks/runtime/win-x64' / name
        files[name] = {'bytes': path.stat().st_size, 'sha256': digest(path)} if path.is_file() else None
    business_pass = code == 0 and terminal and all(value is not None for value in files.values())
    result = {
        'schema': 'project08-recovery-result-v1', 'status': 'MANAGER_IDENTITY_ACCOUNTING_CLOSE_REQUIRED',
        'project': '08', 'rid': 'win-x64', 'markerSha256': context['markerSha256'],
        'amendmentSha256': marker['amendmentSha256'], 'nonce': marker['nonce'],
        'inputAdmissionSha256': marker['inputAdmissionSha256'], 'presealSource': marker['presealSource'],
        'postRecoverySource': source_snapshot(read(PROFILE), args.commit),
        'controllerCodeBeforeFinalBookkeeping': code, 'terminal': terminal, 'businessPass': business_pass,
        'observedElapsedSecondsBeforeBookkeeping': elapsed, 'setupSecondsObserved': setup_elapsed,
        'wholeAttemptLimitSeconds': 90, 'deadlineExceededObserved': elapsed > 90,
        'reservedNativeDebitSeconds': 90, 'chargedSecondsLowerBound': charge, 'windowsOutputs': files,
        'windowsOutputsScope': 'Only two Windows locks and one Windows pin; Linux is separate',
        'finalProcessExitElapsed': 'Manager must observe whole invocation including final bookkeeping/process exit; unknown/over90 is HOLD and fully charged'}
    write(context['resultPath'], result)
    replace_owned_json(context['budgetPath'], budget, marker['nonce'])
    # Include result/ledger IO in the local observation; process-exit closure is manager-owned.
    final_elapsed = time.monotonic() - marker['originMonotonic']
    if final_elapsed > budget['recoveryChargedSeconds']:
        budget['elapsedSeconds'] += final_elapsed - budget['recoveryChargedSeconds']
        budget['recoveryChargedSeconds'] = final_elapsed
        budget['recoveryElapsedSecondsObserved'] = final_elapsed
        replace_owned_json(context['budgetPath'], budget, marker['nonce'])
    return business_pass and final_elapsed <= 90

def routing_reconciliation_closed(profile, marker, result, recovery, transition, budget):
    from package import regular_input, validate_reconciled_windows_outputs
    config = profile['routingReconciliation']
    state = fixed_state(profile, 'win-x64')
    expected_amendment = 'a62a0512e1d6d1c3438d9d55b264867cbae82729f41dabdcbd055cad3ec970e2'
    expected_receipt = '7e922c423a063e50b1aa678a028a8f8e13bd6d108d63c783b74a23f1443a5c63'
    expected_nonce = '13f94171d9627c0994a1963ffd6517ee'
    require(config['amendmentSha256'] == expected_amendment and
            config['receiptSha256'] == expected_receipt and
            config['receiptRelative'] == 'routing-reconciliation-01/RECONCILIATION.json' and
            config['historicalNonce'] == expected_nonce and
            config['transitionStatus'] == 'CLOSED_FAILED_RECOVERY_RECONCILED_OUTPUTS_ACCOUNTED_SIGNED_CANDIDATE',
            'Only the named project08 routing reconciliation is admitted')
    amendment_path = regular_input(native(config['amendmentWindows']))
    reconciliation_path = regular_input(state / config['receiptRelative'], state)
    require(digest(amendment_path) == expected_amendment and
            digest(reconciliation_path) == expected_receipt, 'Exact routing authority/receipt identity')
    amendment, reconciliation = read(amendment_path), read(reconciliation_path)
    binding = transition['routingReconciliation']
    require(Path(native(binding['path'])).resolve() == reconciliation_path.resolve() and
            binding['sha256'] == expected_receipt and binding['amendmentSha256'] == expected_amendment,
            'Manager transition reconciliation binding')
    require(reconciliation['schema'] == 'project08-lock-routing-reconciliation-v1' and
            reconciliation['status'] == 'EXACT_GENERATED_OUTPUTS_IMPORTED_HISTORICAL_RECOVERY_REMAINS_FAILED' and
            reconciliation['project'] == '08' and reconciliation['rid'] == 'win-x64' and
            reconciliation['amendmentSha256'] == expected_amendment and
            reconciliation['managerVerified'] is True and
            reconciliation['sdkRestoreBuildAppInvocations'] == reconciliation['networkRequests'] == 0 and
            reconciliation['newRecoveryOpportunity'] is False, 'Data-only verified reconciliation')
    expected = amendment['exactHistoricalEvidence']
    require(reconciliation['originalEvidence'] == expected and expected['nonce'] == expected_nonce and
            expected['observedOuterExit'] == 125 and expected['businessPass'] is False and
            expected['observedWholeControllerSeconds'] == 4.4430997,
            'Exact historical failed recovery identity')
    paths = {
        'markerSha256': 'recovery-lock-marker.json',
        'recoveryResultSha256': 'recovery-lock-result.json',
        'processObserverSha256': 'recovery-lock-process-observer.json',
        'restoreSubprocessSha256': 'recovery-lock/0-subprocess-result.json',
        'metadataPinSubprocessSha256': 'recovery-lock/1-subprocess-result.json',
        'windowsJobTerminalSha256': 'recovery-lock/windows-job-terminal.json'}
    originals = {}
    for field, relative in paths.items():
        path = regular_input(state / relative, state)
        require(digest(path) == expected[field], 'Historical recovery evidence changed: ' + field)
        originals[field] = read(path)
    require(marker == originals['markerSha256'] and result == originals['recoveryResultSha256'] and
            marker['status'] == 'STARTED' and marker['nonce'] == result['nonce'] == expected_nonce and
            marker['presealSource'] == result['presealSource'] and
            marker['presealSource']['commit'] == reconciliation['presealCommit'] ==
                '47a1cb0060fed771dc47f0ca556abf180adb3280', 'Used marker/source remains historical')
    observer = originals['processObserverSha256']
    require(observer['observedControllerExit'] == 125 and observer['processExited'] is True and
            observer['externalDeadlineKill'] is False and observer['observerOutputOverflow'] is False and
            observer['actualWholeAttemptSeconds'] == 4.4430997 and
            observer['controllerPid'] == marker['ownerPID'] and
            observer['admissionSha256'] == marker['inputAdmissionSha256'] == result['inputAdmissionSha256'],
            'Actual failed whole-process identity')
    for field in ('restoreSubprocessSha256', 'metadataPinSubprocessSha256'):
        target = originals[field]
        require(target['nonce'] == expected_nonce and target['complete'] is True and
                target['exitObserved'] is True and target['exitCode'] == 0 and
                not target['deadlineExpired'] and not target['killRequested'] and target['drainComplete'] and
                not target['stdoutOverflow'] and not target['stderrOverflow'], 'Failed/ambiguous target cannot reconcile')
    job = originals['windowsJobTerminalSha256']
    require(job['nonce'] == expected_nonce and job['terminal'] is True and
            job['rootExitObserved'] is True and job['rootExitCode'] == 0 and
            job['cleanupRequested'] is False and job['controllerExitCode'] == 0,
            'Natural terminal Job required')
    require(result['businessPass'] is False and result['terminal'] is True and
            result['deadlineExceededObserved'] is False and
            result['windowsOutputs']['SessionHarness.lock.json'] is None and
            result['windowsOutputs']['SessionHarness.Tests.lock.json'] is None and
            result['windowsOutputs']['RUNTIME-PACKS.json']['sha256'] ==
                '31533794de99944c3f00e5b71483a73fda655c28419eafdf69e3ca25bc85f850' and
            recovery['observedControllerExit'] == 125 and recovery['actualWholeAttemptSeconds'] == 4.4430997 and
            reconciliation['historicalOuterExit'] == 125 and reconciliation['historicalBusinessPass'] is False and
            reconciliation['historicalNullOutputsPreserved'] is True and
            reconciliation['recoveryMarkerStillUsed'] is True, 'Original failure/null outputs are immutable')
    require(reconciliation['nativeDebitSeconds'] == 90 and
            reconciliation['beforeBudgetSha256'] == reconciliation['afterBudgetSha256'] ==
                transition['beforeBudgetSha256'] == expected['beforeBudgetSha256'] and
            budget['schema'] == 'project08-native-budget-v2' and budget['project'] == '08' and
            budget['rid'] == 'win-x64' and budget['nativeCeilingSeconds'] == 900 and
            budget['elapsedSeconds'] >= budget['recoveryChargedSeconds'] >= 90 and
            budget['recoveryChargedSeconds'] >= 90 and
            budget['recoveryMarkerSha256'] == expected['markerSha256'] and
            len([item for item in budget['attempts'] if item['phase'] == 'recovery-lock']) == 1 and
            budget['attempts'][0]['markerSha256'] == expected['markerSha256'] and
            budget['attempts'][0]['observedControllerCode'] == 0,
            'Used opportunity/full debit cannot be lost')
    before, after = reconciliation['beforeSource'], reconciliation['afterSource']
    require(before == result['postRecoverySource'], 'Reconciliation before-source closure')
    permitted = set()
    for entry in reconciliation['importedLocks']:
        permitted.update((entry['source'], entry['destination']))
        require(before['fileHashes'][entry['source']] == entry['generatedSha256'] and
                before['fileHashes'][entry['destination']] is None and
                after['fileHashes'][entry['source']] == entry['restoreRootPresealSha256'] and
                after['fileHashes'][entry['destination']] == entry['generatedSha256'],
                'Exact generated-to-RID/preseal restoration closure')
    require(before['commit'] == after['commit'] == reconciliation['presealCommit'] and
            set(before['fileHashes']) == set(after['fileHashes']) and
            all(before['fileHashes'][path] == after['fileHashes'][path]
                for path in before['fileHashes'] if path not in permitted),
            'Unrelated data-only source mutation')
    for item in reconciliation['preservedFiles']:
        path = regular_input(reconciliation_path.parent / item['name'], reconciliation_path.parent)
        require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'],
                'Preserved generated/assets/preseal evidence changed')
    outputs = validate_reconciled_windows_outputs()  # Historical receipt assets, never current obj/native PASS.
    for entry in reconciliation['importedLocks']:
        path = regular_input(ROOT / entry['destination'], ROOT)
        require(digest(path) == entry['generatedSha256'] and path.stat().st_size == entry['bytes'],
                'Reconciled RID destination changed')
    require(outputs['RUNTIME-PACKS.json']['sha256'] == reconciliation['existingPin']['sha256'] ==
            '31533794de99944c3f00e5b71483a73fda655c28419eafdf69e3ca25bc85f850',
            'Exact reconciled runtime pin required')
    return True

def bind_final_candidate(profile, admission, budget, args, rid):
    state = fixed_state(profile, rid)
    marker_path = state / profile['recoveryLock']['markerName']
    require(not (rid == 'win-x64' and budget.get('recoveryMarkerSha256') and not marker_path.exists()), 'Missing used recovery marker; HOLD')
    if rid != 'win-x64' or not marker_path.exists():
        require(budget['candidate'] == args.commit, 'Candidate budget identity')
        return budget
    marker = read(marker_path)
    result_path = state / profile['recoveryLock']['resultName']
    result = read(result_path)  # Missing/incomplete result never resets STARTED.
    binding = admission['presealBudgetTransition']
    receipt_path = Path(native(binding['path'])).resolve()
    require(receipt_path == Path(native(profile['recoveryLock']['transitionReceiptWindows'])).resolve() and
            digest(receipt_path) == binding['sha256'], 'Manager-owned one-time transition receipt')
    transition = read(receipt_path)
    recovery = transition['recovery']
    require(transition['schema'] == 'project08-preseal-budget-transition-v1' and
            transition['status'] in ('CLOSED_TERMINAL_ACCOUNTED_SIGNED_CANDIDATE',
                'CLOSED_FAILED_RECOVERY_RECONCILED_OUTPUTS_ACCOUNTED_SIGNED_CANDIDATE') and
            transition['project'] == '08' and transition['rid'] == 'win-x64' and
            recovery['markerSha256'] == digest(marker_path) and recovery['resultSha256'] == digest(result_path) and
            recovery['amendmentSha256'] == profile['recoveryLock']['amendmentSha256'] and
            recovery['originalFailureSha256'] == profile['recoveryLock']['originalFailure']['sha256'],
            'Recovery identity closure')
    ordinary = (transition['status'] == 'CLOSED_TERMINAL_ACCOUNTED_SIGNED_CANDIDATE' and
                result['businessPass'] and recovery['observedControllerExit'] == 0)
    reconciled = (transition['status'] == 'CLOSED_FAILED_RECOVERY_RECONCILED_OUTPUTS_ACCOUNTED_SIGNED_CANDIDATE' and
                  routing_reconciliation_closed(profile, marker, result, recovery, transition, budget))
    require((ordinary or reconciled) and result['terminal'] and not result['deadlineExceededObserved'] and
            recovery['terminal'] is True and 0 <= recovery['actualWholeAttemptSeconds'] <= 90 and
            recovery['chargedSeconds'] >= max(90, budget['recoveryChargedSeconds'], recovery['actualWholeAttemptSeconds'],
                                              result['chargedSecondsLowerBound']),
            'Recovery failed without exact routing reconciliation, overran or accounting is unclosed')
    require(transition['beforeSource'] == marker['presealSource'] and
            transition['afterSource'] == source_snapshot(profile, args.commit) and
            transition['finalCommit'] == args.commit and transition['finalCommit'] != marker['presealSource']['commit'] and
            transition['signedCommitVerified'] is True and
            transition['signingFingerprint'] == 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU',
            'Explicit final signed source identity closure')
    if budget.get('transitionReceiptSha256'):
        require(budget['transitionReceiptSha256'] == binding['sha256'] and
                budget['candidate'] == args.commit, 'Only one preseal-to-final transition')
    else:
        require(digest(state / 'native-budget.json') == transition['beforeBudgetSha256'] and
                budget['candidate'] == marker['presealSource']['commit'], 'Before-budget identity')
        budget['elapsedSeconds'] += recovery['chargedSeconds'] - budget['recoveryChargedSeconds']
        budget['recoveryChargedSeconds'] = recovery['chargedSeconds']
        budget['candidate'] = args.commit
        budget['transitionReceiptSha256'] = binding['sha256']
        budget['recoveryResultSha256'] = digest(result_path)
        if reconciled:
            budget['routingReconciliationSha256'] = profile['routingReconciliation']['receiptSha256']
            budget['routingOutcome'] = {'historicalOuterExit': 125, 'historicalBusinessPass': False,
                'status': 'RECONCILED_OUTPUTS_HISTORICAL_RECOVERY_REMAINS_FAILED'}

        require(budget['elapsedSeconds'] >= 90 and budget['elapsedSeconds'] <= 900, 'Recovery debit cannot disappear')
    return budget


def package_repair_authority(profile, admission, args):
    from package import regular_input
    config = profile['packageFilterRepair']
    require(config['amendmentSha256'] == '4d4fae0e466b09219414b9385f7979fae939552a466968656aa774ee10396cad' and
            config['beforeSha256'] == 'd44dfd4cef76a62505ec354df01a47095754e67aa9ac9440b9cf099131f6cbb5' and
            config['baselineCommit'] == '4abce2532eb0698c913a6c8c5c5d302b3a188a16' and
            config['baselineTree'] == '1fccfbc02a986d669ec71701832c7f5f39fa6a7a' and
            config['wholeInvocationSeconds'] == config['reservedNativeDebitSeconds'] == 210 and
            config['maxAttempts'] == 1 and config['producerRelative'] == 'package-retry',
            'Exact one-successor package repair only')
    base = Path(native(profile['evidenceRootWindows']))
    before_path = regular_input(base / 'package-filter-repair-01/BEFORE-REPAIR.json', base)
    require(config['beforeRelative'] == 'package-filter-repair-01/BEFORE-REPAIR.json' and
            digest(before_path) == config['beforeSha256'], 'Before-repair snapshot identity')
    before = read(before_path)
    require(before['source']['commit'] == config['baselineCommit'] and
            before['source']['tree'] == config['baselineTree'] and
            before['beforeBudgetSha256'] == config['beforeBudgetSha256'] ==
                '4e568bc30f671998657a087d043da3d135556b8f8aa1ac14cdcb6ffb9c58de27' and
            before['elapsedSeconds'] == 139.67300000000978 and before['recoveryDebitSeconds'] == 90 and
            len(before['fullAttempts']) == 5, 'Qualified source/full five-attempt prefix')
    for item in before['preservedFiles']:
        path = regular_input(before_path.parent / item['name'], before_path.parent)
        require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'],
                'Preserved before-repair bytes changed')
    for record in before['evidence']:
        folder = Path(native(record['attempt']['evidence']))
        require(folder.is_relative_to(base), 'Historical attempt path')
        for item in record['topLevelReceiptIdentities']:
            path = regular_input(folder / item['name'], folder)
            require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'],
                    'Original attempt evidence changed')
    binding = admission['packageFilterSuccessor']
    path = regular_input(native(binding['path']))
    require(path.resolve() == Path(native(config['successorReceiptWindows'])).resolve() and
            digest(path) == binding['sha256'], 'Manager-owned successor binding')
    receipt = read(path)
    allowed = ['tools/package.py', 'tools/project08-profile.json', 'tools/project08_launch.py']
    require(receipt['schema'] == 'project08-package-filter-successor-v1' and
            receipt['status'] == 'SIGNED_ONE_LOCAL_PACKAGE_FILTER_REPAIR_SUCCESSOR' and
            receipt['purpose'] == 'LOCAL_PACKAGE_FILTER_REPAIR' and receipt['project'] == '08' and
            receipt['amendmentSha256'] == config['amendmentSha256'] and
            receipt['beforeSnapshotSha256'] == config['beforeSha256'] and
            receipt['beforeSource'] == before['source'] and
            receipt['beforeBudgetSha256'] == before['beforeBudgetSha256'] and
            receipt['priorTransitionSha256'] == '0a665df0459ab7047494b04bb63e72d8e4c2a40ce9b6ce9fec3e8372676d0a08',
            'Named qualified-baseline-to-one-successor closure')
    after = source_snapshot(profile, args.commit)
    require(receipt['afterCommit'] == args.commit != config['baselineCommit'] and
            receipt['afterSource'] == after and
            len(receipt['afterTree']) == 40 and all(c in '0123456789abcdef' for c in receipt['afterTree']) and
            receipt['signedCommitVerified'] is True and
            receipt['signingFingerprint'] == 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU' and
            receipt['allowedChangedFiles'] == allowed and receipt['sdkInputs'] == admission['inputs'],
            'Signed successor/source/SDK identity')
    old_files, new_files = before['source']['fileHashes'], after['fileHashes']
    require(set(old_files) == set(new_files) and
            sorted(p for p in old_files if old_files[p] != new_files[p]) == allowed,
            'Only the exact three packaging repair sources may differ')
    return config, before, receipt, binding['sha256']

def bind_package_successor(profile, admission, budget, args, rid):
    config, before, receipt, receipt_sha = package_repair_authority(profile, admission, args)
    validate_budget(budget, profile, rid)
    if rid == 'win-x64':
        require(budget['elapsedSeconds'] >= before['elapsedSeconds'] and
                budget['recoveryChargedSeconds'] >= 90 and
                budget['attempts'][:5] == before['fullAttempts'] and
                json.dumps(budget['attempts'][:5], separators=(',',':')) ==
                    json.dumps(before['fullAttempts'], separators=(',',':')) and
                budget['transitionReceiptSha256'] == receipt['priorTransitionSha256'] and
                budget['recoveryMarkerSha256'] == 'd3c605bab743a192da89138c8c4a300c3f7fae0c8c10eeffa1ae74d6bb88879a',
                'No elapsed/attempt/debit/marker loss')
        if budget.get('packageFilterSuccessorReceiptSha256'):
            require(budget['packageFilterSuccessorReceiptSha256'] == receipt_sha and
                    budget['candidate'] == args.commit and len(budget['identityTransitions']) == 1,
                    'No second source succession')
        else:
            require(budget['candidate'] == config['baselineCommit'] and
                    digest(fixed_state(profile, rid) / 'native-budget.json') == before['beforeBudgetSha256'] and
                    budget['attempts'] == before['fullAttempts'] and
                    budget['elapsedSeconds'] == before['elapsedSeconds'] and
                    budget['recoveryChargedSeconds'] == 90 and not budget.get('identityTransitions'),
                    'Exact original ledger required for first successor carry')
            budget['candidate'] = args.commit
            budget['packageFilterSuccessorReceiptSha256'] = receipt_sha
            budget['identityTransitions'] = [{'purpose': 'LOCAL_PACKAGE_FILTER_REPAIR',
                'beforeCommit': config['baselineCommit'], 'afterCommit': args.commit,
                'receiptSha256': receipt_sha, 'beforeBudgetSha256': before['beforeBudgetSha256']}]
        retries = [a for a in budget['attempts'][5:] if a['phase'] == 'package-retry']
        require(len(retries) <= 1, 'No second package retry')
        if retries:
            require(budget['packageRetryChargedSeconds'] >= 210 and
                    budget['elapsedSeconds'] >= before['elapsedSeconds'] + budget['packageRetryChargedSeconds'],
                    'Retry reservation/debit cannot be lost')
    else:
        require(rid == 'linux-x64' and budget['candidate'] == args.commit, 'Original Linux RID budget/source')
        if not budget.get('packageFilterSuccessorReceiptSha256'):
            require(budget['elapsedSeconds'] == 0 and budget['attempts'] == [], 'No Linux ledger migration/reset')
            budget['packageFilterSuccessorReceiptSha256'] = receipt_sha
        require(budget['packageFilterSuccessorReceiptSha256'] == receipt_sha, 'Linux successor identity changed')
    return budget

def reserve_package_retry(profile, admission, args, holder, origin, budget):
    config, before, receipt, receipt_sha = package_repair_authority(profile, admission, args)
    state = fixed_state(profile, 'win-x64')
    require(os.name == 'nt' and args.phase == 'package-retry' and
            Path(args.evidence).resolve() == (state / 'package-retry').resolve() and
            not any(a['phase'] == 'package-retry' for a in budget['attempts']) and
            budget['attempts'] == before['fullAttempts'], 'One fixed Windows package retry only')
    marker_path, result_path = state/config['markerName'], state/config['resultName']
    require(config['markerName'] == 'package-retry-marker.json' and
            config['resultName'] == 'package-retry-result.json' and
            not marker_path.exists() and not result_path.exists(), 'Retry already USED or ambiguous')
    require(budget['elapsedSeconds'] + 210 <= 900, 'Cannot reserve whole210 inside existing native900')
    marker = {'schema': 'project08-package-retry-marker-v1', 'status': 'STARTED_USED',
        'project': '08', 'rid': 'win-x64', 'candidate': args.commit, 'sourceTree': receipt['afterTree'],
        'successorReceiptSha256': receipt_sha, 'beforeSnapshotSha256': config['beforeSha256'],
        'inputAdmissionSha256': digest(native(profile['admissionWindows'])),
        'launcherSha256': digest(__file__), 'profileSha256': digest(PROFILE),
        'packageHelperSha256': digest(ROOT/'tools/package.py'),
        'nonce': holder['randomToken'], 'ownerPID': holder['ownerPID'],
        'ownerProcessStartIdentity': holder['ownerProcessStartIdentity'],
        'originMonotonic': origin, 'deadlineMonotonic': origin+210,
        'wholeInvocationMaximumSeconds': 210, 'reservedNativeDebitSeconds': 210,
        'beforeNativeElapsedSeconds': budget['elapsedSeconds'], 'evidenceDirectory': str(state/'package-retry')}
    write(marker_path, marker)  # Interrupted STARTED is permanently USED, even before ledger completion.
    budget['elapsedSeconds'] += 210
    budget['packageRetryChargedSeconds'] = 210
    budget['packageRetryMarkerSha256'] = digest(marker_path)
    budget['attempts'].append({'phase': 'package-retry', 'state': 'STARTED_USED',
        'reservedSeconds': 210, 'markerSha256': digest(marker_path), 'candidate': args.commit,
        'successorReceiptSha256': receipt_sha, 'evidence': str(state/'package-retry')})
    replace_owned_json(state/'native-budget.json', budget, holder['randomToken'])
    return {'marker': marker, 'markerPath': marker_path, 'resultPath': result_path,
            'budget': budget, 'budgetPath': state/'native-budget.json'}

def package_retry_child(profile, args):
    config = profile['packageFilterRepair']
    marker = read(fixed_state(profile, 'win-x64')/config['markerName'])
    require(os.name == 'nt' and marker['status'] == 'STARTED_USED' and
            marker['nonce'] == args.nonce and marker['ownerPID'] == os.getppid() and
            marker['candidate'] == args.commit and marker['launcherSha256'] == digest(__file__) and
            marker['profileSha256'] == digest(PROFILE) and
            marker['packageHelperSha256'] == digest(ROOT/'tools/package.py') and
            marker['inputAdmissionSha256'] == digest(native(profile['admissionWindows'])) and
            Path(marker['evidenceDirectory']).resolve() == Path(args.evidence).resolve(),
            'Exact retry child/parent/source/admission binding')
    return marker

def retry_archive_identity(profile, admission, args, marker):
    from package import regular_input
    state = fixed_state(profile, 'win-x64')
    stage = state/'package-retry'
    metadata_path = regular_input(stage/'build/archive.json', stage)
    metadata = read(metadata_path)
    filename = 'fix-session-recovery-harness-v0.1.0-preview.2-win-x64.zip'
    archive = stage/'delivery'/filename
    # Archive is deliberately larger than the bounded JSON-input limit.
    require(not any(p.is_symlink() or (getattr(p.stat(follow_symlinks=False),'st_file_attributes',0)&0x400)
                    for p in (archive,*archive.parents)) and archive.is_file() and
            archive.stat().st_size <= 64*1024*1024, 'Fixed regular retry archive')
    require(metadata['commit'] == args.commit == marker['candidate'] and
            metadata['rid'] == 'win-x64' and metadata['localCandidate'] is False and
            metadata['sourceTree'] == marker['sourceTree'] and
            metadata['packageHelperSha256'] == marker['packageHelperSha256'] ==
                digest(ROOT/'tools/package.py') and
            Path(native(metadata['archive'])).resolve() == archive.resolve() and
            metadata['bytes'] == archive.stat().st_size and metadata['sha256'] == digest(archive),
            'Actual retry archive/source/tree/RID/member identity')
    with zipfile.ZipFile(archive) as bundle:
        info = bundle.getinfo(filename.removesuffix('.zip')+'/BUILD-MANIFEST.json')
        require(info.file_size <= 65536 and (info.external_attr >> 16) & 0o170000 != 0o120000,
                'Bounded actual retry manifest')
        manifest = json.loads(bundle.read(info))
    require(manifest['sourceCommit'] == args.commit and manifest['sourceTree'] == marker['sourceTree'] and
            manifest['rid'] == 'win-x64' and manifest['sdkVersion'] == '10.0.404' and
            manifest['runtimeVersion'] == '10.0.15' and manifest['selfContained'] is True and
            manifest['localCandidate'] is False, 'Actual archive manifest source/tree/RID')
    return {'metadataSha256': digest(metadata_path), 'archiveSha256': digest(archive),
            'archiveBytes': archive.stat().st_size, 'sourceTree': marker['sourceTree']}

def finish_package_retry(context, profile, admission, args, terminal, code):
    marker, budget = context['marker'], context['budget']
    elapsed = time.monotonic()-marker['originMonotonic']
    charge = max(210, elapsed, budget['packageRetryChargedSeconds'])
    budget['elapsedSeconds'] += charge-budget['packageRetryChargedSeconds']
    budget['packageRetryChargedSeconds'] = charge
    budget['attempts'][-1]['state'] = 'TERMINAL_OBSERVER_CLOSE_REQUIRED' if terminal else 'AMBIGUOUS_USED'
    archive, error = None, None
    if terminal and code == 0:
        try: archive = retry_archive_identity(profile, admission, args, marker)
        except Exception as failure: error = type(failure).__name__+': '+str(failure)
    business = terminal and code == 0 and archive is not None and elapsed <= 210
    result = {'schema': 'project08-package-retry-result-v1', 'project': '08', 'rid': 'win-x64',
        'status': 'ACTUAL_PROCESS_EXIT_OBSERVATION_REQUIRED', 'candidate': args.commit,
        'markerSha256': digest(context['markerPath']), 'nonce': marker['nonce'],
        'successorReceiptSha256': marker['successorReceiptSha256'],
        'controllerCodeBeforeFinalBookkeeping': code, 'terminal': terminal,
        'businessPassBeforeObservation': business, 'archive': archive, 'archiveError': error,
        'elapsedSecondsLowerBound': elapsed, 'chargedSecondsLowerBound': charge,
        'wholeInvocationMaximumSeconds': 210, 'deadlineExceededObserved': elapsed > 210}
    write(context['resultPath'], result)
    replace_owned_json(context['budgetPath'], budget, marker['nonce'])
    final_elapsed = time.monotonic()-marker['originMonotonic']
    if final_elapsed > budget['packageRetryChargedSeconds']:
        budget['elapsedSeconds'] += final_elapsed-budget['packageRetryChargedSeconds']
        budget['packageRetryChargedSeconds'] = final_elapsed
        replace_owned_json(context['budgetPath'], budget, marker['nonce'])
    return business and final_elapsed <= 210

def close_package_retry(profile, admission, args):
    from package import regular_input
    config, before, receipt, receipt_sha = package_repair_authority(profile, admission, args)
    state = fixed_state(profile, 'win-x64')
    require(os.name == 'nt' and Path(args.evidence).resolve() == (state/'package-retry').resolve(),
            'Fixed Windows data-only observer close')
    marker_path = regular_input(state/'package-retry-marker.json', state)
    observer_path = regular_input(state/'package-retry-process-observer.json', state)
    result_path = state/'package-retry-result.json'
    result_sha = digest(regular_input(result_path, state)) if result_path.exists() else None
    marker, observer = read(marker_path), read(observer_path)
    result = read(result_path) if result_sha else None
    require(marker['status'] == 'STARTED_USED' and marker['candidate'] == args.commit and
            marker['successorReceiptSha256'] == receipt_sha and
            observer['markerSha256'] == digest(marker_path) and observer['nonce'] == marker['nonce'] and
            observer['candidate'] == args.commit and observer['resultSha256'] == result_sha and
            observer['schema'] == 'project08-package-retry-process-observer-v1' and
            observer['controllerPid'] == marker['ownerPID'] and
            observer['controllerStartIdentity'] == marker['ownerProcessStartIdentity'] and
            observer['inputAdmissionSha256'] == marker['inputAdmissionSha256'] and
            observer['processExited'] is True and isinstance(observer['observedControllerExit'], int) and
            isinstance(observer['externalDeadlineKill'], bool) and
            isinstance(observer['actualWholeAttemptSeconds'], (int,float)) and
            (result['elapsedSecondsLowerBound'] if result else 0) <= observer['actualWholeAttemptSeconds'] < 1000000 and
            marker['sourceTree'] == receipt['afterTree'] and
            marker['launcherSha256'] == digest(__file__) and marker['profileSha256'] == digest(PROFILE) and
            marker['packageHelperSha256'] == digest(ROOT/'tools/package.py'),
            'Actual owned controller exit/start/duration observation required')
    budget_path = state/'native-budget.json'
    budget = bind_package_successor(profile, admission, read(budget_path), args, 'win-x64')
    require(budget['packageRetryMarkerSha256'] == digest(marker_path) and
            budget['attempts'][-1]['phase'] == 'package-retry' and
            budget['attempts'][-1]['markerSha256'] == digest(marker_path), 'Exact USED retry ledger')
    closure_path = state/'package-retry-observation-closure.json'
    require(not closure_path.exists(), 'Observation already closed; no overwrite')
    old_charge = budget['packageRetryChargedSeconds']
    charge = max(210, old_charge, result['chargedSecondsLowerBound'] if result else 210,
                 observer['actualWholeAttemptSeconds'])
    budget['elapsedSeconds'] += charge-old_charge
    budget['packageRetryChargedSeconds'] = charge
    expected = {'phase-result.json','launcher-terminal.json','0-subprocess-result.json',
                'windows-job-terminal.json','0-subprocess-membership.json','kernel-membership.json'}
    evidence_error = None
    try:
        require(set(observer['producerReceiptHashes']) <= expected, 'No arbitrary producer receipt path')
        for name, sha in observer['producerReceiptHashes'].items():
            require(digest(regular_input(state/'package-retry'/name,state)) == sha,
                    'Observed producer receipt changed')
        require(set(observer['producerReceiptHashes']) == expected and result is not None,
                'Interrupted/partial producer is failure')
        require(result['markerSha256'] == digest(marker_path) and result['nonce'] == marker['nonce'] and
                result['candidate'] == args.commit, 'Retry result binding')
    except Exception as error:
        evidence_error = type(error).__name__+': '+str(error)
    success = (evidence_error is None and result['businessPassBeforeObservation'] and result['terminal'] and
               not result['deadlineExceededObserved'] and observer['observedControllerExit'] == 0 and
               not observer['externalDeadlineKill'] and observer['actualWholeAttemptSeconds'] <= 210 and
               budget['elapsedSeconds'] <= 900)
    budget['attempts'][-1]['state'] = 'OBSERVED_TERMINAL_PASS' if success else 'OBSERVED_FAILURE_USED'
    budget['attempts'][-1]['observedWholeControllerExit'] = observer['observedControllerExit']
    budget['attempts'][-1]['actualWholeAttemptSeconds'] = observer['actualWholeAttemptSeconds']
    replace_owned_json(budget_path, budget, marker['nonce'])
    closure = {'schema': 'project08-package-retry-closure-v1',
        'status': 'OBSERVED_TERMINAL_PASS' if success else 'OBSERVED_FAILURE_USED',
        'candidate': args.commit, 'nonce': marker['nonce'], 'markerSha256': digest(marker_path),
        'resultSha256': result_sha, 'observerSha256': digest(observer_path),
        'successorReceiptSha256': receipt_sha, 'chargedSeconds': charge,
        'actualWholeAttemptSeconds': observer['actualWholeAttemptSeconds'],
        'observedControllerExit': observer['observedControllerExit'], 'evidenceError': evidence_error,
        'budgetSha256': digest(budget_path), 'archive': result['archive'] if result else None}
    write(closure_path, closure)
    return 0 if success else 125

def qualified_retry_producer(profile, admission, args):
    from package import regular_input
    config, before, receipt, receipt_sha = package_repair_authority(profile, admission, args)
    state = fixed_state(profile, 'win-x64')
    marker_path = regular_input(state/'package-retry-marker.json', state)
    result_path = regular_input(state/'package-retry-result.json', state)
    observer_path = regular_input(state/'package-retry-process-observer.json', state)
    closure = read(regular_input(state/'package-retry-observation-closure.json', state))
    marker, result, observer = read(marker_path), read(result_path), read(observer_path)
    require(closure['status'] == 'OBSERVED_TERMINAL_PASS' and
            closure['candidate'] == args.commit == marker['candidate'] and
            closure['successorReceiptSha256'] == receipt_sha == marker['successorReceiptSha256'] and
            closure['markerSha256'] == result['markerSha256'] == digest(marker_path) and
            closure['resultSha256'] == digest(result_path) and closure['observerSha256'] == digest(observer_path) and
            closure['nonce'] == marker['nonce'] == result['nonce'] == observer['nonce'] and
            closure['chargedSeconds'] >= 210 and closure['actualWholeAttemptSeconds'] <= 210 and
            closure['observedControllerExit'] == observer['observedControllerExit'] == 0 and
            observer['processExited'] is True and observer['resultSha256'] == digest(result_path) and
            observer['actualWholeAttemptSeconds'] == closure['actualWholeAttemptSeconds'] and
            observer['actualWholeAttemptSeconds'] >= result['elapsedSecondsLowerBound'] and
            observer['inputAdmissionSha256'] == marker['inputAdmissionSha256'] and
            not observer['externalDeadlineKill'] and
            observer['controllerPid'] == marker['ownerPID'] and
            observer['controllerStartIdentity'] == marker['ownerProcessStartIdentity'] and
            marker['sourceTree'] == receipt['afterTree'] and
            marker['launcherSha256'] == digest(__file__) and marker['profileSha256'] == digest(PROFILE) and
            marker['packageHelperSha256'] == digest(ROOT/'tools/package.py') and
            result['terminal'] and result['businessPassBeforeObservation'] and
            not result['deadlineExceededObserved'], 'Successful observed fixed retry producer required')
    stage = state/'package-retry'
    require(set(observer['producerReceiptHashes']) == {'phase-result.json','launcher-terminal.json',
            '0-subprocess-result.json','windows-job-terminal.json','0-subprocess-membership.json','kernel-membership.json'},
            'Observed fixed producer inventory')
    for name, sha in observer['producerReceiptHashes'].items():
        require(digest(regular_input(stage/name, stage)) == sha, 'Actual producer evidence changed')
    for relative in ('phase-result.json','launcher-terminal.json','0-subprocess-result.json','windows-job-terminal.json'):
        data = read(regular_input(stage/relative, stage))
        require(data['nonce'] == marker['nonce'], 'Producer phase/target/Job nonce')
        if relative == 'phase-result.json':
            require(data['complete'] and data['outcome'] == 'pass' and data['candidate'] == args.commit and data['phase'] == 'package-retry', 'Producer phase failed')
        elif relative == 'windows-job-terminal.json':
            require(data['terminal'] and data['rootExitObserved'] and data['rootExitCode'] == 0 and
                    not data['cleanupRequested'] and data['controllerExitCode'] == 0, 'Producer Job failed/nonterminal')
        elif relative == '0-subprocess-result.json':
            require(data['complete'] and data['exitObserved'] and data['exitCode'] == 0 and
                    data['drainComplete'] and not data['deadlineExpired'] and not data['killRequested'] and
                    not data['stdoutOverflow'] and not data['stderrOverflow'], 'Producer target failed')
        else:
            require(data['exitCode'] == 0 and data['terminal'] and data['phase'] == 'package-retry',
                    'Producer terminal failed')
    target = read(stage/'0-subprocess-result.json')
    member = read(stage/'0-subprocess-membership.json')
    kernel = read(stage/'kernel-membership.json')
    require(member['member'] and member['pid'] == target['pid'] and member['nonce'] == marker['nonce'] and
            member['mechanism'] == kernel['mechanism'] == 'windows-job' and member['job'] == kernel['job'] and
            kernel['memoryBytes'] == 2147483648 and kernel['processLimit'] == 256 and
            int(kernel['cpuAffinity']).bit_count() == 2, 'Actual retry target/kernel binding')
    archive = retry_archive_identity(profile, admission, args, marker)
    require(archive == result['archive'] == closure['archive'], 'Producer archive bytes changed')
    budget = bind_package_successor(profile, admission, read(state/'native-budget.json'), args, 'win-x64')
    require(budget['packageRetryChargedSeconds'] >= closure['chargedSeconds'] and
            any(item['phase'] == 'package-retry' and item['state'] == 'OBSERVED_TERMINAL_PASS'
                for item in budget['attempts']), 'Producer ledger reservation/closure missing')
    return stage

def require_windows_consumer_before_linux(profile, admission, args):
    qualified_retry_producer(profile, admission, args)
    state = fixed_state(profile, 'win-x64')
    phase = read(state/'consumer/phase-result.json')
    terminal = read(state/'consumer/launcher-terminal.json')
    consumer = read(state/'consumer/consumer/receipt.json')
    require(phase['complete'] and phase['outcome'] == 'pass' and phase['candidate'] == args.commit and
            phase['phase'] == terminal['phase'] == 'consumer' and
            terminal['exitCode'] == 0 and terminal['terminal'] and
            terminal['nonce'] == phase['nonce'] and consumer['commit'] == args.commit and
            consumer['rid'] == 'win-x64' and
            consumer['status'] == 'ACTUAL_SELF_CONTAINED_FIXED_FIX_HARNESS_PACKAGE_PASS' and
            all('actual-scenario-'+name in consumer['checks'] for name in ('gap','resend','restart','gapfill')),
            'Complete Windows producer/consumer before Linux native phases')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['probe', 'lock', 'recovery-lock', 'restore', 'build', 'tests', 'package', 'package-retry', 'consumer'], required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--close-package-retry', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--witness', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--parent-pid', type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--nonce', default='', help=argparse.SUPPRESS)
    args = parser.parse_args()
    origin = recovery_origin() if args.phase in ('recovery-lock','package-retry') and not args.inside and not args.close_package_retry else None
    profile, admission, dotnet, rid = load_admission(args.phase)
    require(len(args.commit) == 40 and all(c in '0123456789abcdef' for c in args.commit), 'Candidate identity')
    evidence = Path(args.evidence).resolve()
    base = Path(native(profile['evidenceRootWindows'])).resolve()
    require(evidence.is_relative_to(base) and evidence != base, 'Owned evidence path')
    require(not any(parent.is_symlink() for parent in [evidence, *evidence.parents]), 'Symlink refused')
    if args.witness:
        require(args.phase == 'probe' and not args.inside and
                len(args.nonce) == 32 and all(c in '0123456789abcdef' for c in args.nonce) and
                args.parent_pid == os.getppid() and evidence.is_dir(), 'Fixed witness binding')
        controls = windows_limits(args.nonce) if os.name == 'nt' else linux_limits(args.nonce)
        # Keep the fixed non-SDK witness alive long enough for its parent to query its exact handle/PID.
        time.sleep(0.1)
        write(evidence / 'controlled-child-witness.json', {
            'schema': 'project08-inheritance-witness-v1', 'project': '08',
            'nonce': args.nonce, 'pid': os.getpid(), 'parentPid': os.getppid(),
            'controls': controls, 'sdkOrApplicationInvoked': False})
        return 0
    require(args.phase not in ('lock','recovery-lock'), 'Original lock opportunities consumed; no new generation')
    require(not args.close_package_retry or args.phase == 'package-retry' and not args.inside,
            'Fixed data-only retry close mode')
    if rid == 'win-x64':
        require(args.phase in ('probe','package-retry','consumer'), 'No Windows core/restore/test replay for packaging-only repair')
    if args.inside:
        require(len(args.nonce) == 32 and evidence.is_dir(), 'Internal binding')
        return inside(args, profile, admission, dotnet, rid)
    require(current_head() == args.commit, 'Allocated checkout HEAD differs from candidate')
    if os.name == 'nt' and args.phase == 'lock':
        require(not (fixed_state(profile, rid) / profile['recoveryLock']['originalFailure']['relativeTerminal']).exists(),
                'Original Windows lock opportunity exhausted; only admitted recovery-lock is available')
    if args.close_package_retry:
        require(evidence == (fixed_state(profile, 'win-x64')/'package-retry').resolve() and evidence.is_dir(),
                'Fixed existing retry evidence for data-only close')
    else:
        require(not evidence.exists(), 'Fresh evidence only')
        evidence.mkdir(parents=True)
    nonce = secrets.token_hex(16)
    if os.name != 'nt':
        bus = subprocess.run(['systemctl', '--user', 'is-system-running'], capture_output=True,
                             text=True, timeout=15, check=False, env=linux_environment())
        require(bus.returncode == 0 and bus.stdout.strip() == 'running', 'User manager unready; HOLD before lease')
    lease = Path(native(profile['canonicalLeaseWindows']))
    holder = {'projectId': '08', 'randomToken': nonce, 'ownerOS': platform.system(),
              'ownerPID': os.getpid(), 'ownerProcessStartIdentity': own_start_identity(),
              'phase': args.phase, 'startedAtUtc': time.time(), 'receiptDirectory': str(evidence)}
    protocol = lease.parent / 'LEASE-PROTOCOL.json'
    require(digest(protocol) == profile['canonicalProtocolSha256'], 'Canonical protocol identity')
    with lease.open('x', encoding='utf-8') as stream:
        json.dump(holder, stream)
    terminal = True  # No owned process has been created yet.
    phase_started = time.monotonic()
    budget_path = fixed_state(profile, rid) / 'native-budget.json'
    budget, recovery, package_retry, code = None, None, None, 125
    native_started = False
    try:
        if args.close_package_retry:
            return close_package_retry(profile, admission, args)
        if args.phase == 'recovery-lock':
            recovery = reserve_recovery(profile, admission, args, holder, origin)
            require(time.monotonic() < origin + 90 - 12, 'Recovery setup exhausted whole window')
        elif args.phase not in ('probe', 'lock'):
            require(budget_path.exists() or not (rid == 'win-x64' and
                    (fixed_state(profile, rid) / profile['recoveryLock']['markerName']).exists()),
                    'Used recovery missing budget; manager reconciliation required')
            budget = read(budget_path) if budget_path.exists() else empty_budget(profile, rid, args.commit)
            validate_budget(budget, profile, rid)
            budget = bind_package_successor(profile, admission, budget, args, rid)
            if rid == 'linux-x64': require_windows_consumer_before_linux(profile, admission, args)
            if args.phase == 'package-retry':
                package_retry = reserve_package_retry(profile, admission, args, holder, origin, budget)
                require(time.monotonic() < origin+210-12, 'Retry setup exhausted whole210')
            else:
                require(not any(item['phase'] == args.phase for item in budget['attempts']),
                        'Phase already attempted; no budget reset')
                require(budget['elapsedSeconds'] + profile['phases'][args.phase] + 9 <= 900,
                        'Native cumulative budget exhausted')
                if rid == 'win-x64': qualified_retry_producer(profile, admission, args)
                budget['attempts'].append({'phase': args.phase, 'state': 'STARTED', 'evidence': str(evidence)})
                replace_owned_json(budget_path, budget, nonce)
                native_started = True
        command = [sys.executable, str(Path(__file__).resolve()), '--phase', args.phase,
                   '--commit', args.commit, '--evidence', str(evidence), '--inside', '--nonce', nonce]
        timed = package_retry or recovery
        deadline = timed['marker']['deadlineMonotonic'] if timed else None
        ceiling = max(0, deadline - time.monotonic() - 6) if timed else profile['phases'][args.phase] + 6
        terminal = False
        if os.name == 'nt':
            code, terminal = windows_start(command, ROOT, nonce, ceiling, evidence, deadline)
        else:
            unit = 'project08-' + nonce
            invocation = ['systemd-run', '--user', '--quiet', '--wait', '--pipe', '--unit=' + unit,
                          '--working-directory=' + str(ROOT), '--property=Type=exec',
                          '--property=MemoryMax=2147483648', '--property=MemorySwapMax=0',
                          '--property=TasksMax=256', '--property=CPUQuota=200%',
                          '--property=RuntimeMaxSec=' + str(ceiling), '--property=TimeoutStopSec=3',
                          '--property=KillMode=control-group',
                          '--setenv=XDG_RUNTIME_DIR=/run/user/1000',
                          '--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus', *command]
            proc = subprocess.run(invocation, cwd=ROOT, env=linux_environment(), timeout=ceiling + 8, check=False)
            code = proc.returncode
            member = read(evidence / 'kernel-membership.json')
            group = Path(member['group'])
            terminal = not group.exists() or 'populated 0' in (group / 'cgroup.events').read_text()
        write(evidence / 'launcher-terminal.json', {'project': '08', 'nonce': nonce,
              'phase': args.phase, 'exitCode': code, 'terminal': terminal})
        require(terminal, 'Owned tree terminal state not proved; retain lease')
    finally:
        if native_started:
            budget['elapsedSeconds'] += time.monotonic() - phase_started
            budget['attempts'][-1]['state'] = 'TERMINAL' if terminal else 'INCOMPLETE'
            replace_owned_json(budget_path, budget, nonce)
        if terminal:
            current = read(lease)
            require(current['randomToken'] == nonce and current['ownerPID'] == os.getpid() and
                    current['ownerProcessStartIdentity'] == holder['ownerProcessStartIdentity'], 'Lease identity changed')
            lease.unlink()
        if package_retry is not None:
            if not finish_package_retry(package_retry, profile, admission, args, terminal, code): code = 125
        if recovery is not None:
            if not finish_recovery(recovery, args, terminal, code, phase_started - origin):
                code = 125
    return code

if __name__ == '__main__':
    raise SystemExit(main())
