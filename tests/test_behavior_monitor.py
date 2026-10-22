"""
Tests for OSD Process Behavior Monitor.
Validates behavior anomaly alerts: CPU surges, monotonic memory growth,
thread explosion, and non-invasive telemetry analysis.
"""
import pytest
import time
from app.monitoring.behavior_monitor import ProcessBehaviorMonitor, BehaviorAlert
from app.monitoring.system_monitor import ProcessInfo


def make_proc(pid=1234, name="worker.exe", cpu=5.0, mem_mb=100.0, threads=4):
    return ProcessInfo(
        pid=pid, name=name, status="running",
        cpu_percent=cpu, memory_percent=2.0, memory_mb=mem_mb,
        num_threads=threads, create_time=time.time() - 500, username="User"
    )


class TestProcessBehaviorMonitor:

    def test_cpu_surge_detection(self):
        monitor = ProcessBehaviorMonitor()
        
        # Sample 1: Low CPU
        p1 = make_proc(cpu=5.0)
        alerts1 = monitor.analyze_processes([p1])
        assert len(alerts1) == 0

        # Sample 2: Sudden surge to 80% (delta = +75% > 45%)
        p2 = make_proc(cpu=80.0)
        alerts2 = monitor.analyze_processes([p2])
        surge_alerts = [a for a in alerts2 if a.alert_type == "CPU Surge"]
        assert len(surge_alerts) == 1
        assert surge_alerts[0].pid == 1234
        assert "surge" in surge_alerts[0].description.lower()
        assert surge_alerts[0].severity in ["Warning", "Critical"]

    def test_thread_explosion_detection(self):
        monitor = ProcessBehaviorMonitor()

        # Feed 3 baseline samples with 5 threads
        for _ in range(3):
            monitor.analyze_processes([make_proc(threads=5)])

        # Sample 4: 70 threads (delta = +65 threads >= 40)
        alerts = monitor.analyze_processes([make_proc(threads=70)])
        thread_alerts = [a for a in alerts if a.alert_type == "Thread Expansion"]
        assert len(thread_alerts) == 1
        assert thread_alerts[0].pid == 1234
        assert "thread" in thread_alerts[0].description.lower()

    def test_monotonic_memory_growth_detection(self):
        monitor = ProcessBehaviorMonitor()

        # 4 consecutive samples with memory increasing by 50MB each sample
        alerts = []
        for i in range(4):
            p = make_proc(mem_mb=100.0 + (i * 50.0))
            alerts = monitor.analyze_processes([p])

        leak_alerts = [a for a in alerts if a.alert_type == "Memory Leak Pattern"]
        assert len(leak_alerts) == 1
        assert leak_alerts[0].pid == 1234
        assert "steady" in leak_alerts[0].description.lower() or "ram" in leak_alerts[0].description.lower()
