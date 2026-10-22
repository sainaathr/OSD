"""
Abstract base class for operating system platform adapters.
Provides uniform abstractions for process safety, memory trimming,
priority adjustments, and per-user filesystem directories.
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
import platform
import psutil
import os


class PlatformAdapter(ABC):
    """Abstract operating system adapter."""

    @abstractmethod
    def get_os_family(self) -> str:
        """Return canonical OS family: 'windows', 'linux', 'darwin', or 'unknown'."""
        pass

    def get_platform_info(self) -> str:
        """Return human-readable platform string."""
        return platform.platform()

    def get_os_version(self) -> str:
        """Return OS release version string."""
        return platform.version()

    @abstractmethod
    def get_protected_processes(self) -> set[str]:
        """Return set of lower-case protected process names that must never be terminated."""
        pass

    def is_protected_process(self, process_name: str) -> bool:
        """Check if process is in the protected OS whitelist."""
        clean_name = self.normalize_process_name(process_name).lower()
        protected = self.get_protected_processes()
        if clean_name in protected:
            return True
        # Check bidirectional extension matching (.exe on Windows)
        if clean_name.endswith('.exe') and clean_name[:-4] in protected:
            return True
        if not clean_name.endswith('.exe') and f"{clean_name}.exe" in protected:
            return True
        return False

    def normalize_process_name(self, name: str) -> str:
        """Normalize process name for cross-platform comparison."""
        return name.strip()

    @abstractmethod
    def can_trim_working_set(self) -> bool:
        """Return True if the OS supports working set memory trimming."""
        pass

    @abstractmethod
    def trim_working_set(self, pid: int) -> tuple[bool, str]:
        """Request OS to trim working set memory pages for the target PID."""
        pass

    @abstractmethod
    def supported_priority_levels(self) -> list[str]:
        """Return list of supported priority level names."""
        pass

    @abstractmethod
    def adjust_process_priority(self, pid: int, priority_name: str) -> tuple[bool, str]:
        """Adjust process scheduling priority."""
        pass

    @abstractmethod
    def get_default_data_dir(self) -> str:
        """Return standard per-user application data directory."""
        pass

    def check_runtime_capabilities(self) -> dict[str, Any]:
        """Return runtime diagnostic capability map for telemetry."""
        return {
            "os_family": self.get_os_family(),
            "platform_info": self.get_platform_info(),
            "os_version": self.get_os_version(),
            "can_trim_working_set": self.can_trim_working_set(),
            "supported_priorities": self.supported_priority_levels(),
            "data_dir": self.get_default_data_dir(),
        }
