"""Project08 fixed hosted containment primitives, copied unchanged from signedbb406.
No local admission/paths/ledger and no SDK bootstrap logic. Actual hosted proof is mandatory.
"""
import ctypes,json,os,subprocess,time
from pathlib import Path

def require(value, why):
    if not value:
        raise RuntimeError(why)

def write(path, value):
    payload = (json.dumps(value, indent=2) + '\n').encode()
    require(len(payload) <= 65536, 'Receipt size')
    with Path(path).open('xb') as stream:
        stream.write(payload)

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
