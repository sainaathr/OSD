"""
Factory for platform adapters.
Automatically detects the host operating system and instantiates
the appropriate adapter (Windows, Linux, macOS, or Fallback).
"""
import sys
import os
import psutil
from typing import Optional
from osd_core.platform_support.base import PlatformAdapter
from osd_core.platform_support.windows import WindowsAdapter
from osd_core.platform_support.linux import LinuxAdapter
from osd_core.platform_support.macos import MacOSAdapter


class FallbackAdapter(PlatformAdapter):
    """Generic fallback platform adapter for unclassified operating systems."""

    def get_os_family(self) -> str:
        return "unknown"

    def get_protected_processes(self) -> set[str]:
        return {'system', 'init'}

    def normalize_process_name(self, name: str) -> str:
        return name.strip()

    def can_trim_working_set(self) -> bool:
        return False

    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        return False, "Working set memory page trimming is not supported on this platform."

    def supported_priority_levels(self) -> list[str]:
        return ['normal']

    def adjust_process_priority(self, pid: int, priority_name: str) -> tuple[bool, str]:
        return False, f"Priority adjustment is not supported on this platform."

    def get_default_data_dir(self) -> str:
        path = os.path.join(os.path.expanduser('~'), '.osd')
        os.makedirs(path, exist_ok=True)
        return path


_CURRENT_ADAPTER: Optional[PlatformAdapter] = None


def get_platform_adapter(force_os: Optional[str] = None) -> PlatformAdapter:
    """
    Get the platform adapter for the current or forced operating system.
    Cached singleton by default.
    """
    global _CURRENT_ADAPTER
    if force_os is not None:
        target = force_os.lower()
        if target in ('win32', 'windows'):
            return WindowsAdapter()
        elif target in ('linux', 'linux2'):
            return LinuxAdapter()
        elif target in ('darwin', 'macos', 'osx'):
            return MacOSAdapter()
        else:
            return FallbackAdapter()

    if _CURRENT_ADAPTER is None:
        plat = sys.platform.lower()
        if plat == 'win32':
            _CURRENT_ADAPTER = WindowsAdapter()
        elif plat.startswith('linux'):
            _CURRENT_ADAPTER = LinuxAdapter()
        elif plat == 'darwin':
            _CURRENT_ADAPTER = MacOSAdapter()
        else:
            _CURRENT_ADAPTER = FallbackAdapter()

    return _CURRENT_ADAPTER
