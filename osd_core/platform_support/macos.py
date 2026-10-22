"""
macOS (Darwin) platform adapter.
Implements Darwin nice adjustments, macOS protected process whitelist,
and standard Application Support directory resolution.
"""
import os
import psutil
from osd_core.platform_support.base import PlatformAdapter


class MacOSAdapter(PlatformAdapter):
    """macOS-specific platform adapter."""

    _PROTECTED_PROCESSES = {
        'launchd', 'kernel_task', 'kextd', 'windowserver', 'dock', 'finder',
        'loginwindow', 'coreaudiod', 'opendirectoryd', 'syslogd', 'securityd',
        'diskarbitrationd', 'cfprefsd', 'distnoted', 'tccd',
    }

    def get_os_family(self) -> str:
        return "darwin"

    def get_protected_processes(self) -> set[str]:
        return set(self._PROTECTED_PROCESSES)

    def normalize_process_name(self, name: str) -> str:
        return name.strip().lower()

    def can_trim_working_set(self) -> bool:
        return False

    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        return False, "Working set memory page trimming is a Windows PSAPI feature and is not supported on macOS."

    def supported_priority_levels(self) -> list[str]:
        return ['idle', 'below_normal', 'normal', 'above_normal']

    def adjust_process_priority(self, pid: int, priority_name: str) -> tuple[bool, str]:
        """Adjust process priority using Darwin nice values (-20 to 20)."""
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            if self.is_protected_process(proc_name):
                return False, f"Cannot alter priority of critical macOS system process: {proc_name}"

            nice_map = {
                'idle': 20,
                'below_normal': 10,
                'normal': 0,
                'above_normal': -5,
            }
            target_nice = nice_map.get(priority_name.lower())
            if target_nice is None:
                return False, f"Unsupported macOS priority level '{priority_name}'. Valid: {list(nice_map.keys())}"

            proc.nice(target_nice)
            return True, f"Adjusted nice level of {proc_name} (PID {pid}) to {target_nice} ({priority_name})."
        except psutil.AccessDenied:
            return False, f"Access denied altering priority for PID {pid}. Note that raising priority requires root privileges."
        except psutil.NoSuchProcess:
            return False, f"Process PID {pid} not found."
        except Exception as e:
            return False, f"Error adjusting priority: {str(e)}"

    def get_default_data_dir(self) -> str:
        """Return ~/Library/Application Support/OSD."""
        base = os.path.expanduser('~/Library/Application Support')
        path = os.path.join(base, 'OSD')
        os.makedirs(path, exist_ok=True)
        return path
