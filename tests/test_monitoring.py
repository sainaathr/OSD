"""
Unit tests for SystemMonitor and process protection safety.
"""
import pytest
from app.monitoring.system_monitor import SystemMonitor, SystemSnapshot


class TestSystemMonitor:
    """Test metrics collection and process safety."""

    def test_collect_snapshot(self):
        monitor = SystemMonitor()
        snapshot = monitor.collect_snapshot()

        assert isinstance(snapshot, SystemSnapshot)
        assert snapshot.timestamp > 0
        assert 0.0 <= snapshot.cpu.overall_percent <= 100.0
        assert snapshot.cpu.core_count_logical > 0
        assert snapshot.memory.total > 0
        assert 0.0 <= snapshot.memory.percent <= 100.0
        assert snapshot.disk.total > 0
        assert 0.0 <= snapshot.disk.percent <= 100.0
        assert snapshot.uptime_seconds > 0
        assert snapshot.process_count > 0

    def test_get_processes(self):
        monitor = SystemMonitor()
        processes = monitor.get_processes(sort_by="cpu", limit=20)

        assert isinstance(processes, list)
        assert len(processes) > 0
        for p in processes:
            assert p.pid >= 0
            assert isinstance(p.name, str)
            assert p.cpu_percent >= 0.0
            assert p.memory_percent >= 0.0
            assert p.memory_mb >= 0.0

    def test_protected_process_termination_prevention(self):
        monitor = SystemMonitor()

        # Test protected Windows processes cannot be terminated
        protected_names = [
            "system", "smss.exe", "csrss.exe", "services.exe",
            "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe"
        ]
        for name in protected_names:
            success, message = monitor.terminate_process(pid=4, process_name=name)
            assert success is False
            assert "Cannot terminate protected system process" in message

    def test_pid_reuse_protection(self):
        monitor = SystemMonitor()
        # Find a process that actually exists
        procs = monitor.get_processes(limit=10)
        assert len(procs) > 0
        real_proc = procs[0]

        # Attempt to terminate under a different name
        fake_name = "totally_different_process_name_xyz123.exe"
        success, message = monitor.terminate_process(pid=real_proc.pid, process_name=fake_name)
        assert success is False
        assert "belongs to" in message or "Cannot terminate" in message

    def test_nonexistent_pid_termination(self):
        monitor = SystemMonitor()
        # PID 99999999 almost certainly does not exist
        success, message = monitor.terminate_process(pid=99999999, process_name="nonexistent.exe")
        assert success is False
        assert "no longer exists" in message or "Error terminating" in message
