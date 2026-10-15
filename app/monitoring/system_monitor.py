"""
System Monitor — Collects real-time system metrics using psutil.
"""
import time
import platform
from dataclasses import dataclass, field
from typing import Optional
import psutil


@dataclass
class CpuMetrics:
    overall_percent: float = 0.0
    per_core_percent: list[float] = field(default_factory=list)
    core_count_logical: int = 0
    core_count_physical: int = 0
    frequency_current: float = 0.0  # MHz
    frequency_max: float = 0.0


@dataclass
class MemoryMetrics:
    total: int = 0
    used: int = 0
    available: int = 0
    percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_free: int = 0
    swap_percent: float = 0.0


@dataclass
class DiskMetrics:
    total: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0.0
    read_bytes: int = 0
    write_bytes: int = 0
    read_bytes_per_sec: float = 0.0
    write_bytes_per_sec: float = 0.0
    partitions: list[dict] = field(default_factory=list)


@dataclass
class NetworkMetrics:
    bytes_sent: int = 0
    bytes_recv: int = 0
    upload_speed: float = 0.0  # bytes/sec
    download_speed: float = 0.0  # bytes/sec
    packets_sent: int = 0
    packets_recv: int = 0


@dataclass
class BatteryMetrics:
    available: bool = False
    percent: float = 0.0
    plugged: bool = False
    secs_left: Optional[int] = None


@dataclass
class ProcessInfo:
    pid: int = 0
    name: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = ""
    create_time: float = 0.0
    username: str = ""
    num_threads: int = 0
    ppid: int = 0
    group_name: str = ""


@dataclass
class SystemSnapshot:
    timestamp: float = 0.0
    cpu: CpuMetrics = field(default_factory=CpuMetrics)
    memory: MemoryMetrics = field(default_factory=MemoryMetrics)
    disk: DiskMetrics = field(default_factory=DiskMetrics)
    network: NetworkMetrics = field(default_factory=NetworkMetrics)
    battery: BatteryMetrics = field(default_factory=BatteryMetrics)
    uptime_seconds: float = 0.0
    process_count: int = 0
    platform_info: str = ""
    os_version: str = ""


class SystemMonitor:
    """Collects real-time system metrics using psutil."""
    
    def __init__(self):
        self._prev_net_io: Optional[psutil._common.snetio] = None
        self._prev_disk_io: Optional[dict] = None
        self._prev_time: float = 0.0
        self._proc_cache: dict[int, psutil.Process] = {}
        self._last_cpu_percent: float = 0.0
        self._last_percore_percent: list[float] = []

        # Initialize thread-independent CPU tracking using cpu_times()
        try:
            self._prev_cpu_times = psutil.cpu_times()
            self._prev_percpu_times = psutil.cpu_times(percpu=True)
            time.sleep(0.05)
            now_t = psutil.cpu_times()
            deltas = [getattr(now_t, f) - getattr(self._prev_cpu_times, f) for f in now_t._fields]
            tot = sum(deltas)
            if tot > 0:
                idle = getattr(now_t, 'idle', 0.0) - getattr(self._prev_cpu_times, 'idle', 0.0)
                self._last_cpu_percent = round(max(0.0, min(100.0, ((tot - idle) / tot) * 100.0)), 1)
            self._prev_cpu_times = now_t
        except Exception:
            self._prev_cpu_times = None
            self._prev_percpu_times = []

        # Prime psutil fallback
        try:
            psutil.cpu_percent(interval=None)
            psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            pass

        self._prev_net_io = psutil.net_io_counters()
        try:
            dio = psutil.disk_io_counters()
            if dio:
                self._prev_disk_io = {'read_bytes': dio.read_bytes, 'write_bytes': dio.write_bytes}
        except Exception:
            self._prev_disk_io = None
        self._prev_time = time.time()
    
    def collect_snapshot(self) -> SystemSnapshot:
        """Collect a complete system snapshot."""
        now = time.time()
        dt = now - self._prev_time if self._prev_time > 0 else 1.0
        if dt <= 0:
            dt = 1.0
        
        snapshot = SystemSnapshot(
            timestamp=now,
            cpu=self._collect_cpu(),
            memory=self._collect_memory(),
            disk=self._collect_disk(dt),
            network=self._collect_network(dt),
            battery=self._collect_battery(),
            uptime_seconds=now - psutil.boot_time(),
            process_count=len(psutil.pids()),
            platform_info=platform.platform(),
            os_version=platform.version(),
        )
        
        self._prev_time = now
        return snapshot
    
    def _collect_cpu(self) -> CpuMetrics:
        metrics = CpuMetrics()
        try:
            # 1. Thread-independent overall CPU calculation
            now_times = psutil.cpu_times()
            if self._prev_cpu_times:
                deltas = [getattr(now_times, f) - getattr(self._prev_cpu_times, f) for f in now_times._fields]
                total = sum(deltas)
                if total > 0:
                    idle = getattr(now_times, 'idle', 0.0) - getattr(self._prev_cpu_times, 'idle', 0.0)
                    busy = max(0.0, total - idle)
                    pct = round(max(0.0, min(100.0, (busy / total) * 100.0)), 1)
                    self._last_cpu_percent = pct
                    self._prev_cpu_times = now_times
            else:
                self._prev_cpu_times = now_times

            # 2. Thread-independent per-core CPU calculation
            now_percpu = psutil.cpu_times(percpu=True)
            if self._prev_percpu_times and len(self._prev_percpu_times) == len(now_percpu):
                percore = []
                for prev_c, now_c in zip(self._prev_percpu_times, now_percpu):
                    c_deltas = [getattr(now_c, f) - getattr(prev_c, f) for f in now_c._fields]
                    c_tot = sum(c_deltas)
                    if c_tot > 0:
                        c_idle = getattr(now_c, 'idle', 0.0) - getattr(prev_c, 'idle', 0.0)
                        c_busy = max(0.0, c_tot - c_idle)
                        percore.append(round(max(0.0, min(100.0, (c_busy / c_tot) * 100.0)), 1))
                    else:
                        percore.append(0.0)
                if percore:
                    self._last_percore_percent = percore
                    self._prev_percpu_times = now_percpu
            else:
                self._prev_percpu_times = now_percpu

            # 3. Fallback to psutil standard call if for any reason delta was 0
            if self._last_cpu_percent == 0.0:
                p_pct = psutil.cpu_percent(interval=None)
                if p_pct > 0.0:
                    self._last_cpu_percent = p_pct

            num_logical = psutil.cpu_count(logical=True) or 1
            metrics.overall_percent = self._last_cpu_percent
            metrics.per_core_percent = self._last_percore_percent or [metrics.overall_percent] * num_logical
            metrics.core_count_logical = num_logical
            metrics.core_count_physical = psutil.cpu_count(logical=False) or 0
            freq = psutil.cpu_freq()
            if freq:
                metrics.frequency_current = freq.current
                metrics.frequency_max = freq.max
        except Exception:
            pass
        return metrics
    
    def _collect_memory(self) -> MemoryMetrics:
        metrics = MemoryMetrics()
        try:
            vm = psutil.virtual_memory()
            metrics.total = vm.total
            metrics.used = vm.used
            metrics.available = vm.available
            metrics.percent = vm.percent
        except Exception:
            pass
        try:
            swap = psutil.swap_memory()
            metrics.swap_total = swap.total
            metrics.swap_used = swap.used
            metrics.swap_free = swap.free
            metrics.swap_percent = swap.percent
        except Exception:
            pass
        return metrics
    
    def _collect_disk(self, dt: float) -> DiskMetrics:
        metrics = DiskMetrics()
        try:
            partitions = psutil.disk_partitions(all=False)
            total = used = free = 0
            parts_info = []
            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    total += usage.total
                    used += usage.used
                    free += usage.free
                    parts_info.append({
                        'device': p.device,
                        'mountpoint': p.mountpoint,
                        'fstype': p.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent,
                    })
                except (PermissionError, OSError):
                    pass
            metrics.total = total
            metrics.used = used
            metrics.free = free
            metrics.percent = (used / total * 100) if total > 0 else 0.0
            metrics.partitions = parts_info
        except Exception:
            pass
        
        try:
            dio = psutil.disk_io_counters()
            if dio:
                metrics.read_bytes = dio.read_bytes
                metrics.write_bytes = dio.write_bytes
                if self._prev_disk_io and dt > 0:
                    metrics.read_bytes_per_sec = max(0, (dio.read_bytes - self._prev_disk_io['read_bytes']) / dt)
                    metrics.write_bytes_per_sec = max(0, (dio.write_bytes - self._prev_disk_io['write_bytes']) / dt)
                self._prev_disk_io = {'read_bytes': dio.read_bytes, 'write_bytes': dio.write_bytes}
        except Exception:
            pass
        
        return metrics
    
    def _collect_network(self, dt: float) -> NetworkMetrics:
        metrics = NetworkMetrics()
        try:
            net = psutil.net_io_counters()
            if net:
                metrics.bytes_sent = net.bytes_sent
                metrics.bytes_recv = net.bytes_recv
                metrics.packets_sent = net.packets_sent
                metrics.packets_recv = net.packets_recv
                if self._prev_net_io and dt > 0:
                    metrics.upload_speed = max(0, (net.bytes_sent - self._prev_net_io.bytes_sent) / dt)
                    metrics.download_speed = max(0, (net.bytes_recv - self._prev_net_io.bytes_recv) / dt)
                self._prev_net_io = net
        except Exception:
            pass
        return metrics
    
    def _collect_battery(self) -> BatteryMetrics:
        metrics = BatteryMetrics()
        try:
            battery = psutil.sensors_battery()
            if battery:
                metrics.available = True
                metrics.percent = battery.percent
                metrics.plugged = battery.power_plugged
                if battery.secsleft != psutil.POWER_TIME_UNLIMITED and battery.secsleft != psutil.POWER_TIME_UNKNOWN:
                    metrics.secs_left = battery.secsleft
        except Exception:
            metrics.available = False
        return metrics
    
    def get_processes(self, sort_by: str = "cpu", limit: int = 100) -> list[ProcessInfo]:
        """Get a list of running processes sorted by resource usage."""
        num_cores = psutil.cpu_count(logical=True) or 1
        processes = []
        current_pids = set()

        for proc in psutil.process_iter(['pid', 'name', 'memory_percent',
                                          'memory_info', 'status', 'create_time',
                                          'username', 'num_threads', 'ppid']):
            try:
                info = proc.info
                pid = info.get('pid', 0)
                current_pids.add(pid)

                cached_proc = self._proc_cache.get(pid)
                if cached_proc is None:
                    cached_proc = proc
                    self._proc_cache[pid] = proc
                    try:
                        cached_proc.cpu_percent(interval=None)
                    except Exception:
                        pass
                    raw_cpu = 0.0
                else:
                    try:
                        raw_cpu = cached_proc.cpu_percent(interval=None)
                    except Exception:
                        raw_cpu = 0.0

                # Normalize per-process CPU to total system percentage (0-100%)
                norm_cpu = round(raw_cpu / num_cores, 1)

                name = info.get('name', 'Unknown') or 'Unknown'
                group = name.lower()
                if group.endswith('.exe'):
                    group = group[:-4]
                pinfo = ProcessInfo(
                    pid=pid,
                    name=name,
                    cpu_percent=norm_cpu,
                    memory_percent=info.get('memory_percent', 0.0) or 0.0,
                    memory_mb=(info.get('memory_info').rss / (1024 * 1024)) if info.get('memory_info') else 0.0,
                    status=info.get('status', 'unknown'),
                    create_time=info.get('create_time', 0.0) or 0.0,
                    username=info.get('username', '') or '',
                    num_threads=info.get('num_threads', 0) or 0,
                    ppid=info.get('ppid', 0) or 0,
                    group_name=group,
                )
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Evict terminated PIDs from cache
        dead_pids = set(self._proc_cache.keys()) - current_pids
        for dead_pid in dead_pids:
            self._proc_cache.pop(dead_pid, None)

        if sort_by == "cpu":
            # Put idle thread (pid 0 or name "system idle process") at bottom of active CPU list
            processes.sort(key=lambda p: (0.0 if p.pid == 0 or 'idle' in p.name.lower() else p.cpu_percent), reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda p: p.memory_percent, reverse=True)
        elif sort_by == "name":
            processes.sort(key=lambda p: p.name.lower())
        elif sort_by == "pid":
            processes.sort(key=lambda p: p.pid)
        
        return processes[:limit] if limit > 0 else processes

    def get_process_groups(self, limit: int = 20) -> list[dict]:
        """Group processes by application name (e.g., all Chrome/Edge tabs combined)."""
        procs = self.get_processes(limit=0)
        groups = {}
        for p in procs:
            g = p.group_name
            if g not in groups:
                groups[g] = {
                    'group_name': g,
                    'display_name': p.name,
                    'total_cpu': 0.0,
                    'total_memory_mb': 0.0,
                    'instance_count': 0,
                    'pids': [],
                    'main_pid': p.pid
                }
            groups[g]['total_cpu'] += p.cpu_percent
            groups[g]['total_memory_mb'] += p.memory_mb
            groups[g]['instance_count'] += 1
            groups[g]['pids'].append(p.pid)

        sorted_groups = sorted(groups.values(), key=lambda x: (x['total_cpu'], x['total_memory_mb']), reverse=True)
        return sorted_groups[:limit]

    def terminate_process(self, pid: int, process_name: str) -> tuple[bool, str]:
        """Terminate a process after revalidating identity. Returns (success, message)."""
        # System-critical process protection
        protected = {
            'system', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
            'lsass.exe', 'svchost.exe', 'winlogon.exe', 'dwm.exe', 'explorer.exe',
            'registry', 'system idle process', 'secure system', 'ntoskrnl.exe',
            'windowsdefender', 'msmpeng.exe', 'nissrv.exe', 'securityhealthservice.exe',
        }
        
        if process_name.lower() in protected:
            return False, f"Cannot terminate protected system process: {process_name}"
        
        try:
            proc = psutil.Process(pid)
            # Revalidate PID matches expected process
            current_name = proc.name()
            if current_name.lower() != process_name.lower():
                return False, (f"PID {pid} now belongs to '{current_name}', "
                             f"not '{process_name}'. Aborting for safety.")
            
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                return True, f"Termination signal sent to {process_name} (PID {pid}). Process may take time to close."
            return True, f"Successfully terminated {process_name} (PID {pid})."
        except psutil.NoSuchProcess:
            return False, f"Process {process_name} (PID {pid}) no longer exists."
        except psutil.AccessDenied:
            return False, f"Access denied when trying to terminate {process_name} (PID {pid}). Elevated privileges may be required."
        except Exception as e:
            return False, f"Error terminating {process_name} (PID {pid}): {str(e)}"

    def adjust_process_priority(self, pid: int, priority_name: str) -> tuple[bool, str]:
        """Adjust process priority safely (e.g., 'below_normal', 'normal', 'idle')."""
        protected = {
            'system', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
            'lsass.exe', 'svchost.exe', 'winlogon.exe', 'dwm.exe', 'explorer.exe',
        }
        try:
            proc = psutil.Process(pid)
            if proc.name().lower() in protected:
                return False, f"Cannot alter priority of critical system process: {proc.name()}"

            priority_map = {
                'idle': getattr(psutil, 'IDLE_PRIORITY_CLASS', 64),
                'below_normal': getattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS', 16384),
                'normal': getattr(psutil, 'NORMAL_PRIORITY_CLASS', 32),
                'above_normal': getattr(psutil, 'ABOVE_NORMAL_PRIORITY_CLASS', 32768),
            }
            target = priority_map.get(priority_name.lower())
            if target is None:
                return False, f"Unsupported priority level: {priority_name}"

            proc.nice(target)
            return True, f"Adjusted priority of {proc.name()} (PID {pid}) to {priority_name}."
        except psutil.AccessDenied:
            return False, f"Access denied altering priority for PID {pid}."
        except psutil.NoSuchProcess:
            return False, f"Process PID {pid} not found."
        except Exception as e:
            return False, f"Error adjusting priority: {str(e)}"

    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        """Request the OS to trim empty pages from process working set."""
        try:
            import ctypes
            import ctypes.wintypes
            proc = psutil.Process(pid)
            process_handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
            if process_handle:
                result = ctypes.windll.psapi.EmptyWorkingSet(process_handle)
                ctypes.windll.kernel32.CloseHandle(process_handle)
                if result:
                    return True, f"Successfully requested working set trim for {proc.name()} (PID {pid})."
            return False, f"Working set trim was not accepted by OS for PID {pid}."
        except Exception as e:
            return False, f"Working set trim unsupported or denied: {str(e)}"
