"""
Unit tests for osd_core models and collectors:
- Metric data models (CpuMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics, SystemSnapshot)
- Diagnostic models and Severity levels
- Unavailable metrics representation (None vs fabricated numbers)
- System collector execution
"""
import time
import pytest

from osd_core.models.metrics import (
    CpuMetrics,
    MemoryMetrics,
    DiskMetrics,
    NetworkMetrics,
    BatteryMetrics,
    ProcessInfo,
    SystemSnapshot,
)
from osd_core.models.diagnostics import Diagnosis, Severity, HealthScoreBreakdown
from osd_core.models.recovery import RecoveryPlan, RecoveryVerification
from osd_core.collectors.system_collector import SystemCollector


def test_cpu_metrics_dataclass():
    """Verify CpuMetrics handles supported and optional fields."""
    cpu = CpuMetrics(
        overall_percent=45.2,
        core_count_logical=16,
        core_count_physical=8,
        frequency_current=3200.0,
        per_core_percent=[40.0, 50.0]
    )
    assert cpu.overall_percent == 45.2
    assert cpu.core_count_physical == 8
    assert cpu.core_count_logical == 16


def test_unsupported_metrics_represented_as_none():
    """Verify that unsupported hardware metrics remain None rather than fabricated."""
    battery = BatteryMetrics(
        available=False,
        percent=0.0,
        plugged=False,
        secs_left=None,
        error="No battery installed on desktop system"
    )
    assert battery.available is False
    assert battery.secs_left is None
    assert battery.error is not None

    cpu = CpuMetrics(
        overall_percent=12.0,
        core_count_logical=4,
        core_count_physical=4,
        available=True,
        error=None
    )
    assert cpu.error is None


def test_system_snapshot_instantiation():
    """Verify SystemSnapshot aggregates models cleanly."""
    snapshot = SystemSnapshot(
        timestamp=time.time(),
        cpu=CpuMetrics(overall_percent=10.0, core_count_logical=4, core_count_physical=4),
        memory=MemoryMetrics(total=1000, used=500, available=500, percent=50.0),
        disk=DiskMetrics(total=10000, used=4000, free=6000, percent=40.0),
        network=NetworkMetrics(bytes_sent=100, bytes_recv=200, upload_speed=0, download_speed=0),
        uptime_seconds=3600.0,
        process_count=120,
        platform_info="MockOS 1.0",
        os_family="windows"
    )
    assert snapshot.cpu.overall_percent == 10.0
    assert snapshot.memory.percent == 50.0
    assert snapshot.process_count == 120
    assert snapshot.os_family == "windows"


def test_diagnosis_severity_levels():
    """Verify Severity enum and Diagnosis structure."""
    diag = Diagnosis(
        title="High CPU Usage",
        severity=Severity.CRITICAL,
        evidence="CPU utilization exceeded 95%",
        probable_cause="Runaway task",
        confidence="High",
        recommendation="Inspect runaway tasks",
        explanation="System is under severe compute stress",
        category="CPU"
    )
    assert diag.severity == Severity.CRITICAL
    assert diag.title == "High CPU Usage"
    assert diag.category == "CPU"
    d_dict = diag.to_dict()
    assert d_dict['severity'] == "Critical"


def test_system_collector_collects_real_snapshot():
    """Verify SystemCollector returns valid real-machine snapshot."""
    collector = SystemCollector()
    snapshot = collector.collect_snapshot()

    assert snapshot.timestamp > 0
    assert 0.0 <= snapshot.cpu.overall_percent <= 100.0
    assert snapshot.cpu.core_count_logical >= 1
    assert snapshot.memory.total > 0
    assert snapshot.memory.used > 0
    assert 0.0 <= snapshot.memory.percent <= 100.0
    assert snapshot.disk.total > 0

    # Also test process list
    procs = collector.get_processes(limit=5)
    assert isinstance(procs, list)
    assert len(procs) <= 5
    if procs:
        assert procs[0].pid >= 0
