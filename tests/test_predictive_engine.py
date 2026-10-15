"""
Tests for OSense 2.0 Predictive Performance Engine.
Validates linear regression slopes, time-to-exhaustion projections,
process memory growth attribution, and alert confidence/limitations.
"""
import time
import pytest
from app.analysis.predictive_engine import PredictiveEngine, PredictiveAlert
from app.monitoring.system_monitor import SystemSnapshot, CpuMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics, ProcessInfo


def create_mock_snapshot(timestamp: float, cpu: float = 20.0, mem_percent: float = 50.0, swap_percent: float = 0.0,
                         available_bytes: int = 4 * 1024 * 1024 * 1024,
                         total_bytes: int = 8 * 1024 * 1024 * 1024) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=timestamp,
        cpu=CpuMetrics(overall_percent=cpu, per_core_percent=[cpu], core_count_logical=4, core_count_physical=2, frequency_current=2400.0),
        memory=MemoryMetrics(total=total_bytes, available=available_bytes, used=total_bytes - available_bytes,
                             percent=mem_percent, swap_total=4 * 1024 * 1024 * 1024,
                             swap_used=int(4 * 1024 * 1024 * 1024 * (swap_percent / 100.0)),
                             swap_free=int(4 * 1024 * 1024 * 1024 * (1.0 - swap_percent / 100.0)),
                             swap_percent=swap_percent),
        disk=DiskMetrics(total=500 * 1024 * 1024 * 1024, used=200 * 1024 * 1024 * 1024,
                         free=300 * 1024 * 1024 * 1024, percent=40.0, read_bytes_per_sec=0.0,
                         write_bytes_per_sec=0.0),
        network=NetworkMetrics(upload_speed=0.0, download_speed=0.0),
        process_count=100
    )


class TestPredictiveEngine:

    def test_insufficient_samples_suppresses_prediction(self):
        engine = PredictiveEngine()
        # Only 3 snapshots (< 4 required)
        for i in range(3):
            engine.add_snapshot(create_mock_snapshot(timestamp=1000.0 + i * 2, mem_percent=50.0 + i * 5))
        
        alerts = engine.analyze_predictions(create_mock_snapshot(1006.0), [])
        assert len(alerts) == 0, "Should suppress alerts when sample count is insufficient"

    def test_memory_exhaustion_projection(self):
        engine = PredictiveEngine()
        base_time = 1000.0
        # Steadily increasing RAM from 70% up to 88% over 10 samples (slope > 0.4%/min)
        for i in range(10):
            t = base_time + i * 2.0
            mem_pct = 70.0 + (i * 2.0)
            avail = int((1.0 - (mem_pct / 100.0)) * 8 * 1024 * 1024 * 1024)
            engine.add_snapshot(create_mock_snapshot(timestamp=t, mem_percent=mem_pct, available_bytes=avail))

        procs = [
            ProcessInfo(pid=5000, name="photoshop.exe", cpu_percent=5.0, memory_percent=30.0, memory_mb=2400.0,
                        num_threads=10, create_time=time.time(), username="User")
        ]
        last_snap = create_mock_snapshot(base_time + 18.0, mem_percent=88.0, available_bytes=int(0.12 * 8 * 1024 * 1024 * 1024))
        alerts = engine.analyze_predictions(last_snap, procs)

        ram_alerts = [a for a in alerts if a.metric in ("Memory", "RAM")]
        assert len(ram_alerts) >= 1
        alert = ram_alerts[0]
        assert alert.projected_minutes is not None
        assert alert.projected_minutes > 0
        assert alert.confidence in ["Medium", "High"]
        assert len(alert.assumptions) > 0
        assert len(alert.limitations) > 0
        assert "photoshop.exe" in alert.evidence

    def test_cpu_sustained_saturation_detection(self):
        engine = PredictiveEngine()
        base_time = 1000.0
        # Sustained high CPU across samples (avg > 78%)
        for i in range(10):
            t = base_time + i * 2.0
            cpu = 85.0 + (i % 3)
            engine.add_snapshot(create_mock_snapshot(timestamp=t, cpu=cpu))

        last_snap = create_mock_snapshot(base_time + 18.0, cpu=88.0)
        alerts = engine.analyze_predictions(last_snap, [])

        cpu_alerts = [a for a in alerts if a.metric == "CPU"]
        assert len(cpu_alerts) >= 1
        assert cpu_alerts[0].severity in ["Warning", "Critical"]
        assert "Persistent" in cpu_alerts[0].headline

    def test_swap_accumulation_projection(self):
        engine = PredictiveEngine()
        base_time = 1000.0
        # Rapidly rising swap/page file usage from 40% to 65%
        for i in range(8):
            t = base_time + i * 2.0
            swap = 40.0 + (i * 3.5)
            engine.add_snapshot(create_mock_snapshot(timestamp=t, swap_percent=swap))

        last_snap = create_mock_snapshot(base_time + 14.0, swap_percent=64.5)
        alerts = engine.analyze_predictions(last_snap, [])

        swap_alerts = [a for a in alerts if a.metric == "Swap"]
        assert len(swap_alerts) >= 1
        assert "Virtual Memory" in swap_alerts[0].headline
