"""
Windows platform adapter.
Implements Windows PSAPI working set trimming, priority classes,
and Windows protected process whitelist.
"""
import os
import psutil
from osd_core.platform_support.base import PlatformAdapter


class WindowsAdapter(PlatformAdapter):
    """Windows-specific platform adapter."""

    _PROTECTED_PROCESSES = {
        'system', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
        'lsass.exe', 'svchost.exe', 'winlogon.exe', 'dwm.exe', 'explorer.exe',
        'registry', 'system idle process', 'secure system', 'ntoskrnl.exe',
        'windowsdefender', 'msmpeng.exe', 'nissrv.exe', 'securityhealthservice.exe',
        'fontdrvhost.exe', 'sihost.exe', 'ctfmon.exe',
    }

    def get_os_family(self) -> str:
        return "windows"

    def get_protected_processes(self) -> set[str]:
        return set(self._PROTECTED_PROCESSES)

    def normalize_process_name(self, name: str) -> str:
        clean = name.strip()
        # Keep .exe or lowercase for matching
        return clean.lower()

    def can_trim_working_set(self) -> bool:
        return True

    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        """Request Windows kernel to flush unreferenced pages via EmptyWorkingSet."""
        try:
            import ctypes
            import ctypes.wintypes
            
            if not hasattr(ctypes, 'windll'):
                return False, "Windows PSAPI is not available on this environment."

            proc = psutil.Process(pid)
            proc_name = proc.name()
            # PROCESS_SET_QUOTA (0x0100) | PROCESS_QUERY_INFORMATION (0x0400) = 0x0500
            # Or standard PROCESS_ALL_ACCESS = 0x1F0FFF
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
            if not handle:
                # Try fallback access rights
                handle = ctypes.windll.kernel32.OpenProcess(0x0500, False, pid)

            if handle:
                try:
                    result = ctypes.windll.psapi.EmptyWorkingSet(handle)
                    if result:
                        return True, f"Successfully requested working set trim for {proc_name} (PID {pid})."
                    return False, f"EmptyWorkingSet request was rejected by OS kernel for PID {pid}."
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)

            return False, f"Access denied opening process PID {pid} for working set trim."
        except psutil.NoSuchProcess:
            return False, f"Process PID {pid} is no longer running."
        except psutil.AccessDenied:
            return False, f"Access denied when attempting to trim working set for PID {pid}."
        except Exception as e:
            return False, f"Working set trim failed: {str(e)}"

    def supported_priority_levels(self) -> list[str]:
        return ['idle', 'below_normal', 'normal', 'above_normal', 'high']

    def adjust_process_priority(self, pid: int, priority_name: str) -> tuple[bool, str]:
        """Set process priority using Windows priority classes."""
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            if self.is_protected_process(proc_name):
                return False, f"Cannot alter priority of critical system process: {proc_name}"

            priority_map = {
                'idle': getattr(psutil, 'IDLE_PRIORITY_CLASS', 64),
                'below_normal': getattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS', 16384),
                'normal': getattr(psutil, 'NORMAL_PRIORITY_CLASS', 32),
                'above_normal': getattr(psutil, 'ABOVE_NORMAL_PRIORITY_CLASS', 32768),
                'high': getattr(psutil, 'HIGH_PRIORITY_CLASS', 128),
            }
            target = priority_map.get(priority_name.lower())
            if target is None:
                return False, f"Unsupported Windows priority level '{priority_name}'. Valid: {list(priority_map.keys())}"

            proc.nice(target)
            return True, f"Adjusted priority of {proc_name} (PID {pid}) to {priority_name}."
        except psutil.AccessDenied:
            return False, f"Access denied altering priority for PID {pid}. Elevated privileges may be required."
        except psutil.NoSuchProcess:
            return False, f"Process PID {pid} not found."
        except Exception as e:
            return False, f"Error adjusting priority: {str(e)}"

    def get_default_data_dir(self) -> str:
        """Return %LOCALAPPDATA%\\OSD or fallback."""
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            path = os.path.join(local_app_data, 'OSD')
        else:
            path = os.path.join(os.path.expanduser('~'), '.osd')
        os.makedirs(path, exist_ok=True)
        return path
