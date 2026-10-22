"""
Cross-Platform System Telemetry Collector.
Collects real-time hardware metrics and process accounting using psutil and PlatformAdapter.
Decoupled from UI rendering, thread-safe, and resilient against permission and runtime errors.
"""
import time
import platform
import psutil
from typing import Optional, Any
from osd_core.models.metrics import (
    CpuMetrics,
    MemoryMetrics,
    DiskMetrics,
    NetworkMetrics,
    BatteryMetrics,
    ProcessInfo,
    SystemSnapshot,
)
from osd_core.platform_support.base import PlatformAdapter
from osd_core.platform_support.factory import get_platform_adapter


class SystemCollector:
    """Collects real-time system metrics using psutil and PlatformAdapter."""

    def __init__(self, platform_adapter: Optional[PlatformAdapter] = None):
        self.adapter: PlatformAdapter = platform_adapter or get_platform_adapter()
        self._prev_net_io: Optional[psutil._common.snetio] = None
        self._prev_disk_io: Optional[dict[str, int]] = None
        self._prev_time: float = 0.0
        self._proc_cache: dict[int, psutil.Process] = {}
        self._last_cpu_percent: float = 0.0
        self._last_percore_percent: list[float] = []

        # Thread-independent CPU tracking using cpu_times()
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

        try:
            self._prev_net_io = psutil.net_io_counters()
        except Exception:
            self._prev_net_io = None

        try:
            dio = psutil.disk_io_counters()
            if dio:
                self._prev_disk_io = {'read_bytes': dio.read_bytes, 'write_bytes': dio.write_bytes}
        except Exception:
            self._prev_disk_io = None

        self._prev_time = time.time()

    def collect_snapshot(self) -> SystemSnapshot:
        """Collect a complete cross-platform system telemetry snapshot."""
        now = time.time()
        dt = now - self._prev_time if self._prev_time > 0 else 1.0
        if dt <= 0:
            dt = 1.0

        errors: list[str] = []

        # CPU
        cpu = self._collect_cpu()
        if cpu.error:
            errors.append(f"CPU: {cpu.error}")

        # Memory
        memory = self._collect_memory()
        if memory.error:
            errors.append(f"Memory: {memory.error}")

        # Disk
        disk = self._collect_disk(dt)
        if disk.error:
            errors.append(f"Disk: {disk.error}")

        # Network
        network = self._collect_network(dt)
        if network.error:
            errors.append(f"Network: {network.error}")

        # Battery
        battery = self._collect_battery()
        if battery.error:
            errors.append(f"Battery: {battery.error}")

        # Uptime & processes
        try:
            uptime = now - psutil.boot_time()
        except Exception as e:
            uptime = 0.0
            errors.append(f"Uptime: {str(e)}")

        try:
            proc_count = len(psutil.pids())
        except Exception as e:
            proc_count = 0
            errors.append(f"ProcessCount: {str(e)}")

        snapshot = SystemSnapshot(
            timestamp=now,
            cpu=cpu,
            memory=memory,
            disk=disk,
            network=network,
            battery=battery,
            uptime_seconds=uptime,
            process_count=proc_count,
            platform_info=self.adapter.get_platform_info(),
            os_version=self.adapter.get_os_version(),
            os_family=self.adapter.get_os_family(),
            collection_errors=errors,
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

            # Fallback to psutil standard call if delta was zero
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
            metrics.available = True
        except Exception as e:
            metrics.available = False
            metrics.error = str(e)
        return metrics

    def _collect_memory(self) -> MemoryMetrics:
        metrics = MemoryMetrics()
        try:
            vm = psutil.virtual_memory()
            metrics.total = vm.total
            metrics.used = vm.used
            metrics.available = vm.available
            metrics.percent = vm.percent
            metrics.is_available = True
        except Exception as e:
            metrics.is_available = False
            metrics.error = str(e)

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
        except Exception as e:
            metrics.error = str(e)

        try:
            dio = psutil.disk_io_counters()
            if dio:
                metrics.read_bytes = dio.read_bytes
                metrics.write_bytes = dio.write_bytes
                if self._prev_disk_io and dt > 0:
                    metrics.read_bytes_per_sec = max(0.0, (dio.read_bytes - self._prev_disk_io['read_bytes']) / dt)
                    metrics.write_bytes_per_sec = max(0.0, (dio.write_bytes - self._prev_disk_io['write_bytes']) / dt)
                self._prev_disk_io = {'read_bytes': dio.read_bytes, 'write_bytes': dio.write_bytes}
                metrics.io_available = True
            else:
                metrics.io_available = False
        except Exception:
            metrics.io_available = False

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
                    metrics.upload_speed = max(0.0, (net.bytes_sent - self._prev_net_io.bytes_sent) / dt)
                    metrics.download_speed = max(0.0, (net.bytes_recv - self._prev_net_io.bytes_recv) / dt)
                self._prev_net_io = net
                metrics.is_available = True
        except Exception as e:
            metrics.is_available = False
            metrics.error = str(e)
        return metrics

    def _collect_battery(self) -> BatteryMetrics:
        metrics = BatteryMetrics()
        try:
            battery = psutil.sensors_battery()
            if battery:
                metrics.available = True
                metrics.percent = battery.percent
                metrics.plugged = battery.power_plugged
                if battery.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
                    metrics.secs_left = battery.secsleft
            else:
                metrics.available = False
        except Exception as e:
            metrics.available = False
            metrics.error = str(e)
        return metrics

    def get_processes(self, sort_by: str = "cpu", limit: int = 100) -> list[ProcessInfo]:
        """Get running processes sorted by resource usage."""
        num_cores = psutil.cpu_count(logical=True) or 1
        processes: list[ProcessInfo] = []
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
            processes.sort(key=lambda p: (0.0 if p.pid == 0 or 'idle' in p.name.lower() else p.cpu_percent), reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda p: p.memory_percent, reverse=True)
        elif sort_by == "name":
            processes.sort(key=lambda p: p.name.lower())
        elif sort_by == "pid":
            processes.sort(key=lambda p: p.pid)

        return processes[:limit] if limit > 0 else processes

    def get_process_groups(self, limit: int = 20) -> list[dict[str, Any]]:
        """Group processes by application name (e.g., all Chrome/Edge tabs combined)."""
        procs = self.get_processes(limit=0)
        groups: dict[str, dict[str, Any]] = {}
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
                    'main_pid': p.pid,
                }
            groups[g]['total_cpu'] += p.cpu_percent
            groups[g]['total_memory_mb'] += p.memory_mb
            groups[g]['instance_count'] += 1
            groups[g]['pids'].append(p.pid)

        sorted_groups = sorted(groups.values(), key=lambda x: (x['total_cpu'], x['total_memory_mb']), reverse=True)
        return sorted_groups[:limit]

    def terminate_process(self, pid: int, process_name: str) -> tuple[bool, str]:
        """Terminate a process after cross-platform protected whitelist and identity revalidation."""
        if self.adapter.is_protected_process(process_name):
            return False, f"Cannot terminate protected system process: {process_name}"

        try:
            proc = psutil.Process(pid)
            current_name = proc.name()
            # Normalize for comparison
            if self.adapter.normalize_process_name(current_name) != self.adapter.normalize_process_name(process_name):
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
        """Adjust process priority using the active platform adapter."""
        return self.adapter.adjust_process_priority(pid, priority_name)

    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        """Request working set trim using the active platform adapter."""
        return self.adapter.trim_working_set(pid)
