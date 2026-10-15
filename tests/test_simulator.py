"""
Tests for OSense 2.0 What-If Resource Simulator.
Validates transparent calculation of hypothetical resource relief,
CPU reduction, RAM reclamation, Health Score gains, and sandbox safety.
"""
import pytest
import time
from app.analysis.simulator import WhatIfSimulator, SimulationResult
from app.analysis.engine import AnalysisEngine, Thresholds
from app.monitoring.system_monitor import SystemSnapshot, CpuMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics, ProcessInfo


@pytest.fixture
def simulator():
    engine = AnalysisEngine(Thresholds())
    return WhatIfSimulator(engine)


def create_mock_snapshot(cpu=80.0, mem=85.0):
    total_bytes = 16 * 1024 * 1024 * 1024
    used_bytes = int(total_bytes * (mem / 100.0))
    avail_bytes = total_bytes - used_bytes
    return SystemSnapshot(
        timestamp=time.time(),
        cpu=CpuMetrics(overall_percent=cpu, per_core_percent=[cpu], core_count_logical=8, core_count_physical=4, frequency_current=3200.0),
        memory=MemoryMetrics(total=total_bytes, available=avail_bytes, used=used_bytes,
                             percent=mem, swap_total=8 * 1024 * 1024 * 1024, swap_used=2 * 1024 * 1024 * 1024,
                             swap_free=6 * 1024 * 1024 * 1024, swap_percent=25.0),
        disk=DiskMetrics(total=500 * 1024 * 1024 * 1024, used=200 * 1024 * 1024 * 1024,
                         free=300 * 1024 * 1024 * 1024, percent=40.0, read_bytes_per_sec=0.0,
                         write_bytes_per_sec=0.0),
        network=NetworkMetrics(upload_speed=0.0, download_speed=0.0),
        process_count=150
    )


class TestWhatIfSimulator:

    def test_simulation_empty_selection(self, simulator):
        snap = create_mock_snapshot(cpu=60.0, mem=70.0)
        res = simulator.simulate_closing_processes(snap, [])
        assert res.cpu_reduction == 0.0
        assert res.freed_memory_mb == 0.0
        assert res.simulated_cpu == snap.cpu.overall_percent
        assert res.simulated_mem_percent == pytest.approx(snap.memory.percent, abs=0.05)
        assert res.health_score_gain == pytest.approx(0.0, abs=0.01)

    def test_simulation_multiple_processes(self, simulator):
        snap = create_mock_snapshot(cpu=85.0, mem=90.0)
        selected_procs = [
            ProcessInfo(pid=101, name="heavy_ide.exe",
                        cpu_percent=25.0, memory_percent=15.0, memory_mb=2400.0,
                        num_threads=20, create_time=time.time(), username="User"),
            ProcessInfo(pid=102, name="compiler.exe",
                        cpu_percent=35.0, memory_percent=10.0, memory_mb=1600.0,
                        num_threads=16, create_time=time.time(), username="User")
        ]

        res = simulator.simulate_closing_processes(snap, selected_procs)
        
        # Verify CPU relief (25% + 35% = 60% total)
        assert res.cpu_reduction == pytest.approx(60.0, abs=0.1)
        assert res.simulated_cpu == pytest.approx(25.0, abs=0.1)

        # Verify RAM relief (2400 + 1600 = 4000 MB)
        assert res.freed_memory_mb == pytest.approx(4000.0, abs=1.0)
        assert res.simulated_mem_percent < snap.memory.percent

        # Health score must improve
        assert res.health_score_gain > 0
        assert res.simulated_health_score > res.original_health_score

        # Check transparency metadata
        assert len(res.assumptions) > 0
        assert "SIMULATION MODE" in res.disclaimer
