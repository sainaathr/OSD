"""
Unit tests for OSD Platform Adapters (Windows, Linux, macOS, Fallback).
Verifies OS-specific abstraction, permission error handling, priority mapping,
and graceful degradation for unsupported features.
"""
from unittest.mock import patch, MagicMock
import pytest

from osd_core.platform_support.factory import get_platform_adapter, FallbackAdapter
from osd_core.platform_support.windows import WindowsAdapter
from osd_core.platform_support.linux import LinuxAdapter
from osd_core.platform_support.macos import MacOSAdapter
from osd_core.platform_support.base import PlatformAdapter


def test_factory_returns_platform_adapter():
    """Verify get_platform_adapter returns a valid PlatformAdapter subclass."""
    adapter = get_platform_adapter()
    assert isinstance(adapter, PlatformAdapter)
    assert adapter.get_os_family() in ("windows", "linux", "darwin", "unknown")


def test_windows_adapter_capabilities():
    """Verify Windows adapter capabilities and process protection."""
    adapter = WindowsAdapter()
    assert adapter.get_os_family() == "windows"
    assert adapter.can_trim_working_set() is True
    
    protected = adapter.get_protected_processes()
    assert "system" in protected
    assert "explorer.exe" in protected
    assert "csrss.exe" in protected
    assert adapter.is_protected_process("explorer.exe") is True
    assert adapter.is_protected_process("explorer") is True
    
    caps = adapter.check_runtime_capabilities()
    assert caps.get("os_family") == "windows"
    assert caps.get("can_trim_working_set") is True
    assert "normal" in caps.get("supported_priorities")


def test_windows_adapter_priority_mapping():
    """Test priority mapping on Windows."""
    adapter = WindowsAdapter()
    with patch("psutil.Process") as mock_proc_cls:
        mock_proc = MagicMock()
        mock_proc_cls.return_value = mock_proc
        
        # Valid priorities
        success, _ = adapter.adjust_process_priority(1234, "idle")
        assert success is True
        success, _ = adapter.adjust_process_priority(1234, "normal")
        assert success is True
        success, _ = adapter.adjust_process_priority(1234, "high")
        assert success is True
        
        # Invalid priority returns False
        success, err = adapter.adjust_process_priority(1234, "nonexistent")
        assert success is False


def test_windows_adapter_error_handling():
    """Test handling of invalid PID or permission error."""
    adapter = WindowsAdapter()
    
    # Negative PID or nonexistent PID should return False gracefully
    success, _ = adapter.trim_working_set(-999)
    assert success is False
    success, _ = adapter.adjust_process_priority(-999, "normal")
    assert success is False


def test_linux_adapter_capabilities():
    """Verify Linux adapter capabilities and POSIX nice mapping."""
    adapter = LinuxAdapter()
    assert adapter.get_os_family() == "linux"
    assert adapter.can_trim_working_set() is False
    
    protected = adapter.get_protected_processes()
    assert "systemd" in protected
    assert "init" in protected
    assert "kthreadd" in protected
    assert adapter.is_protected_process("systemd") is True
    
    # Working set trim is not natively supported without cgroups v2
    success, msg = adapter.trim_working_set(1234)
    assert success is False
    assert "not supported" in msg.lower()
    
    caps = adapter.check_runtime_capabilities()
    assert caps.get("can_trim_working_set") is False


def test_linux_adapter_priority_nice():
    """Verify POSIX nice mapping for Linux."""
    adapter = LinuxAdapter()
    with patch("psutil.Process") as mock_proc_cls:
        mock_proc = MagicMock()
        mock_proc_cls.return_value = mock_proc
        
        success, _ = adapter.adjust_process_priority(5678, "idle")
        assert success is True
        mock_proc.nice.assert_called_with(19)
        
        success, _ = adapter.adjust_process_priority(5678, "normal")
        assert success is True
        mock_proc.nice.assert_called_with(0)


def test_macos_adapter_capabilities():
    """Verify macOS adapter capabilities and launchd protection."""
    adapter = MacOSAdapter()
    assert adapter.get_os_family() == "darwin"
    assert adapter.can_trim_working_set() is False
    
    protected = adapter.get_protected_processes()
    assert "launchd" in protected
    assert "kernel_task" in protected
    assert "windowserver" in protected
    assert adapter.is_protected_process("launchd") is True
    
    # Working set trim returns False gracefully
    success, msg = adapter.trim_working_set(1000)
    assert success is False


def test_fallback_adapter():
    """Verify fallback adapter behavior when running on unknown OS."""
    adapter = FallbackAdapter()
    assert adapter.get_os_family() == "unknown"
    assert adapter.can_trim_working_set() is False
    success, _ = adapter.trim_working_set(1)
    assert success is False
    success, _ = adapter.adjust_process_priority(1, "normal")
    assert success is False
    assert len(adapter.get_protected_processes()) > 0
