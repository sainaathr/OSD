"""
Unit tests for AnalysisEngine, HealthScore calculation, and diagnostic rules.
"""
import pytest
from app.monitoring.system_monitor import (
    SystemSnapshot, CpuMetrics, MemoryMetrics, DiskMetrics,
    NetworkMetrics, BatteryMetrics, ProcessInfo
)
from app.analysis.engine import (
    AnalysisEngine, Thresholds, Severity, Diagnosis, HealthScoreBreakdown
)


def create_mock_snapshot(
    cpu_percent: float = 15.0,
    mem_percent: float = 35.0,
    mem_avail_gb: float = 10.0,
    mem_total_gb: float = 16.0,
    swap_percent: float = 5.0,
    disk_percent: float = 40.0,
    disk_free_gb: float = 200.0,
    disk_total_gb: float = 500.0,
    disk_read_speed: float = 1024 * 1024,
    disk_write_speed: float = 1024 * 1024,
    upload_speed: float = 50 * 1024,
    download_speed: float = 100 * 1024,
    process_count: int = 150,
    timestamp: float = 1000.0
) -> SystemSnapshot:
    """Helper to generate synthetic test snapshots."""
    return SystemSnapshot(
        timestamp=timestamp,
        cpu=CpuMetrics(
            overall_percent=cpu_percent,
            per_core_percent=[cpu_percent] * 8,
            core_count_logical=8,
            core_count_physical=4,
            frequency_current=2800.0,
            frequency_max=4200.0,
        ),
        memory=MemoryMetrics(
            total=int(mem_total_gb * (1024**3)),
            used=int((mem_total_gb * (mem_percent / 100)) * (1024**3)),
            available=int(mem_avail_gb * (1024**3)),
            percent=mem_percent,
            swap_total=int(8 * (1024**3)),
            swap_used=int((8 * (swap_percent / 100)) * (1024**3)),
            swap_free=int((8 * (1 - swap_percent / 100)) * (1024**3)),
            swap_percent=swap_percent,
        ),
        disk=DiskMetrics(
            total=int(disk_total_gb * (1024**3)),
            used=int((disk_total_gb * (disk_percent / 100)) * (1024**3)),
            free=int(disk_free_gb * (1024**3)),
            percent=disk_percent,
            read_bytes_per_sec=disk_read_speed,
            write_bytes_per_sec=disk_write_speed,
            partitions=[{
                'device': 'C:\\',
                'mountpoint': 'C:\\',
                'fstype': 'NTFS',
                'total': int(disk_total_gb * (1024**3)),
                'used': int((disk_total_gb * (disk_percent / 100)) * (1024**3)),
                'free': int(disk_free_gb * (1024**3)),
                'percent': disk_percent,
            }]
        ),
        network=NetworkMetrics(
            bytes_sent=1000000,
            bytes_recv=2000000,
            upload_speed=upload_speed,
            download_speed=download_speed,
        ),
        battery=BatteryMetrics(
            available=True,
            percent=95.0,
            plugged=True,
        ),
        uptime_seconds=3600.0 * 5,
        process_count=process_count,
        platform_info="Windows 11 Test",
        os_version="10.0.22631",
    )


class TestAnalysisEngine:
    """Test suite for diagnostic rules and health scores."""

    def test_healthy_system(self):
        engine = AnalysisEngine()
        snap = create_mock_snapshot(
            cpu_percent=10.0, mem_percent=30.0, swap_percent=2.0, disk_percent=45.0
        )
        health = engine.calculate_health_score(snap)
        assert health.total_score >= 90.0
        assert health.cpu_score == 100.0
        assert health.memory_score == 100.0

        diagnoses = engine.diagnose(snap)
        assert len(diagnoses) == 1
        assert diagnoses[0].severity == Severity.HEALTHY
        assert "System Healthy" in diagnoses[0].title

    def test_high_cpu_warning_and_critical(self):
        thresholds = Thresholds()
        thresholds.cpu_warning = 75.0
        thresholds.cpu_critical = 90.0
        engine = AnalysisEngine(thresholds)

        # Warning level
        snap_warn = create_mock_snapshot(cpu_percent=80.0)
        diags_warn = engine.diagnose(snap_warn)
        assert any(d.severity == Severity.WARNING and "CPU" in d.title for d in diags_warn)

        # Critical level
        snap_crit = create_mock_snapshot(cpu_percent=95.0)
        diags_crit = engine.diagnose(snap_crit)
        assert any(d.severity == Severity.CRITICAL and "CPU" in d.title for d in diags_crit)

    def test_sustained_cpu_pressure(self):
        thresholds = Thresholds()
        thresholds.cpu_warning = 75.0
        thresholds.sustained_samples = 3
        engine = AnalysisEngine(thresholds)

        # Feed 3 samples of high CPU
        for i in range(3):
            snap = create_mock_snapshot(cpu_percent=85.0, timestamp=1000.0 + i)
            engine.add_snapshot(snap)

        diags = engine.diagnose(snap)
        cpu_diag = next(d for d in diags if "CPU" in d.title)
        assert "Sustained" in cpu_diag.title
        assert cpu_diag.confidence == "High"

    def test_memory_pressure_and_swap(self):
        engine = AnalysisEngine()
        snap = create_mock_snapshot(
            mem_percent=88.0, mem_avail_gb=1.2, swap_percent=65.0
        )
        diags = engine.diagnose(snap)

        titles = [d.title for d in diags]
        assert any("Memory" in t for t in titles)
        assert any("Page File" in t or "Swap" in t for t in titles)

        # Verify page file diagnosis details
        swap_diag = next(d for d in diags if "Page File" in d.title)
        assert swap_diag.severity in (Severity.WARNING, Severity.CRITICAL)
        assert "virtual memory" in swap_diag.explanation.lower()

    def test_disk_capacity_vs_disk_io(self):
        engine = AnalysisEngine()

        # Low disk space scenario with low I/O
        snap_space = create_mock_snapshot(
            disk_percent=92.0, disk_free_gb=15.0,
            disk_read_speed=1024, disk_write_speed=1024
        )
        diags_space = engine.diagnose(snap_space)
        assert any("Low Disk Space" in d.title for d in diags_space)
        assert not any("High Disk Activity" in d.title for d in diags_space)

        # High disk I/O scenario with plenty of free space
        snap_io = create_mock_snapshot(
            disk_percent=30.0, disk_free_gb=350.0,
            disk_read_speed=60 * 1024 * 1024, disk_write_speed=20 * 1024 * 1024
        )
        diags_io = engine.diagnose(snap_io)
        assert any("High Disk Activity" in d.title for d in diags_io)
        assert not any("Low Disk Space" in d.title for d in diags_io)

    def test_health_score_weights_and_bounds(self):
        engine = AnalysisEngine()
        # Worst case: 100% on everything
        snap_worst = create_mock_snapshot(
            cpu_percent=100.0, mem_percent=100.0, swap_percent=100.0, disk_percent=100.0
        )
        score_worst = engine.calculate_health_score(snap_worst)
        assert 0.0 <= score_worst.total_score <= 10.0
        assert len(score_worst.factors) >= 4

        # Best case: Idle
        snap_best = create_mock_snapshot(
            cpu_percent=5.0, mem_percent=20.0, swap_percent=0.0, disk_percent=25.0
        )
        score_best = engine.calculate_health_score(snap_best)
        assert score_best.total_score == 100.0

    def test_empty_and_edge_case_processes(self):
        engine = AnalysisEngine()
        snap = create_mock_snapshot(cpu_percent=88.0, mem_percent=85.0)

        # Empty process list should not raise exceptions
        diags_empty = engine.diagnose(snap, processes=[])
        assert len(diags_empty) >= 2

        # None process list should not raise exceptions
        diags_none = engine.diagnose(snap, processes=None)
        assert len(diags_none) >= 2

    def test_run_full_diagnosis_report(self):
        engine = AnalysisEngine()
        snap = create_mock_snapshot()
        report = engine.run_full_diagnosis(snap)
        assert 'health_score' in report
        assert 'diagnoses' in report
        assert 'snapshot_summary' in report
        assert isinstance(report['diagnoses'], list)
