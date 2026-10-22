"""
Platform Support Layer for OSD
"""
from osd_core.platform_support.base import PlatformAdapter
from osd_core.platform_support.windows import WindowsAdapter
from osd_core.platform_support.linux import LinuxAdapter
from osd_core.platform_support.macos import MacOSAdapter
from osd_core.platform_support.factory import get_platform_adapter, FallbackAdapter

__all__ = [
    "PlatformAdapter",
    "WindowsAdapter",
    "LinuxAdapter",
    "MacOSAdapter",
    "FallbackAdapter",
    "get_platform_adapter",
]
