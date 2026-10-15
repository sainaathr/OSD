"""
Unit tests for RecommendationEngine.
"""
import pytest
from app.monitoring.system_monitor import ProcessInfo
from app.analysis.engine import Diagnosis, Severity
from app.recommendations.engine import RecommendationEngine, Recommendation
from tests.test_analysis_engine import create_mock_snapshot


class TestRecommendationEngine:
    """Test recommendation generation rules and safety constraints."""

    def test_healthy_diagnosis_produces_no_recommendations(self):
        engine = RecommendationEngine()
        snap = create_mock_snapshot()
        diag = Diagnosis(
            title="System Healthy",
            severity=Severity.HEALTHY,
            evidence="All metrics normal",
        )
        recs = engine.generate([diag], snap)
        assert len(recs) == 0

    def test_cpu_recommendation_with_processes(self):
        engine = RecommendationEngine()
        snap = create_mock_snapshot(cpu_percent=88.0)
        diag = Diagnosis(
            title="High CPU Utilization",
            severity=Severity.WARNING,
            evidence="CPU at 88%",
        )
        procs = [
            ProcessInfo(pid=1001, name="heavy_render.exe", cpu_percent=65.0, memory_mb=500.0),
            ProcessInfo(pid=1002, name="background_task.exe", cpu_percent=15.0, memory_mb=200.0),
        ]
        recs = engine.generate([diag], snap, procs)
        assert len(recs) >= 2
        # Verify targeted action
        close_recs = [r for r in recs if r.action_type == "close_app"]
        assert len(close_recs) >= 1
        assert close_recs[0].target_pid == 1001
        assert close_recs[0].target_process == "heavy_render.exe"
        assert close_recs[0].risk_level == "Medium"

    def test_memory_recommendation_with_processes(self):
        engine = RecommendationEngine()
        snap = create_mock_snapshot(mem_percent=90.0, mem_avail_gb=1.0)
        diag = Diagnosis(
            title="High Memory Utilization",
            severity=Severity.CRITICAL,
            evidence="Memory at 90%",
        )
        procs = [
            ProcessInfo(pid=2001, name="memory_hog.exe", cpu_percent=2.0, memory_mb=2500.0),
        ]
        recs = engine.generate([diag], snap, procs)
        assert any(r.target_process == "memory_hog.exe" for r in recs)
        assert any(r.risk_level == "Low" and r.action_type == "info" for r in recs)

    def test_disk_space_recommendations(self):
        engine = RecommendationEngine()
        snap = create_mock_snapshot(disk_percent=94.0, disk_free_gb=10.0)
        diag = Diagnosis(
            title="Low Disk Space on C:\\",
            severity=Severity.CRITICAL,
            evidence="Drive C: is 94% full.",
        )
        recs = engine.generate([diag], snap)
        assert len(recs) >= 1
        assert any("Disk Cleanup" in r.action or "Storage Sense" in r.action for r in recs)
        # Ensure no destructive commands
        assert all(r.risk_level in ("Low", "Medium") for r in recs)

    def test_recommendation_deduplication(self):
        engine = RecommendationEngine()
        snap = create_mock_snapshot(cpu_percent=85.0)
        diag1 = Diagnosis(title="High CPU Utilization", severity=Severity.WARNING)
        diag2 = Diagnosis(title="High CPU Utilization", severity=Severity.WARNING)
        recs = engine.generate([diag1, diag2], snap)
        # Verify no duplicate problem-action pairs
        pairs = [(r.problem, r.action) for r in recs]
        assert len(pairs) == len(set(pairs))
