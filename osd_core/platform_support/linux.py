"""
Linux platform adapter.
Implements POSIX nice adjustments, Linux protected process whitelist,
and XDG Base Directory specification compliance.
"""
import os
import psutil
from osd_core.platform_support.base import PlatformAdapter


class LinuxAdapter(PlatformAdapter):
    """Linux-specific platform adapter."""

    _PROTECTED_PROCESSES = {
        'systemd', 'init', 'kthreadd', 'ksoftirqd', 'rcu_sched', 'kworker',
        'dbus-daemon', 'systemd-journald', 'systemd-logind', 'systemd-udevd',
        'sshd', 'xorg', 'wayland', 'gnome-shell', 'plasmashell', 'pulseaudio',
        'pipewire', 'cron', 'rsyslogd', 'polkitd', 'NetworkManager',
    }

    def get_os_family(self) -> str:
        return "linux"

    def get_protected_processes(self) -> set[str]:
        return set(self._PROTECTED_PROCESSES)

    def normalize_process_name(self, name: str) -> str:
        return name.strip().lower()

    def can_trim_working_set(self) -> bool:
        # Linux virtual memory management does not expose per-process working set trimming
        return False

    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        return False, "Working set memory page trimming is not supported on Linux kernels (managed by kernel VM subsystem)."

    def supported_priority_levels(self) -> list[str]:
        return ['idle', 'below_normal', 'normal', 'above_normal']

    def adjust_process_priority(self, pid: int, priority_name: str) -> tuple[bool, str]:
        """Adjust process priority using POSIX nice values (-20 to 19)."""
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            if self.is_protected_process(proc_name):
                return False, f"Cannot alter priority of critical Linux system process: {proc_name}"

            # POSIX nice map: 19 = lowest priority (idle), 10 = below normal, 0 = default, -5 = elevated
            nice_map = {
                'idle': 19,
                'below_normal': 10,
                'normal': 0,
                'above_normal': -5,
            }
            target_nice = nice_map.get(priority_name.lower())
            if target_nice is None:
                return False, f"Unsupported Linux priority level '{priority_name}'. Valid: {list(nice_map.keys())}"

            proc.nice(target_nice)
            return True, f"Adjusted nice level of {proc_name} (PID {pid}) to {target_nice} ({priority_name})."
        except psutil.AccessDenied:
            return False, f"Access denied altering nice value for PID {pid}. Note that raising priority requires root privileges."
        except psutil.NoSuchProcess:
            return False, f"Process PID {pid} not found."
        except Exception as e:
            return False, f"Error adjusting priority: {str(e)}"

    def get_default_data_dir(self) -> str:
        """Return $XDG_DATA_HOME/osd or ~/.local/share/osd."""
        xdg_data = os.environ.get('XDG_DATA_HOME')
        if xdg_data:
            path = os.path.join(xdg_data, 'osd')
        else:
            path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'osd')
        os.makedirs(path, exist_ok=True)
        return path
