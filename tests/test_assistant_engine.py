"""
Tests for OSense 2.0 Ask OSense Assistant NLP Engine.
Validates offline rule-based natural language responses grounded in live telemetry,
active diagnoses, predictive analysis, and verified recovery history.
"""
import pytest
import time
from unittest.mock import MagicMock
from app.assistant.chat_engine import AskOSenseEngine
from app.monitoring.system_monitor import SystemMonitor, ProcessInfo, SystemSnapshot, CpuMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics
from app.analysis.engine import AnalysisEngine, Diagnosis, HealthScoreBreakdown
from app.analysis.predictive_engine import PredictiveEngine, PredictiveAlert
from app.database.db_manager import DatabaseManager


@pytest.fixture
def mock_deps(tmp_path):
    db = DatabaseManager(str(tmp_path / "chat_test.db"))
    monitor = MagicMock(spec=SystemMonitor)
    analysis = MagicMock(spec=AnalysisEngine)
    predictive = MagicMock(spec=PredictiveEngine)

    # Setup standard snapshot
    total_bytes = 16 * 1024 * 1024 * 1024
    snap = SystemSnapshot(
        timestamp=time.time(),
        cpu=CpuMetrics(overall_percent=45.0, per_core_percent=[45.0], core_count_logical=4, core_count_physical=2, frequency_current=2400.0),
        memory=MemoryMetrics(total=total_bytes, available=4 * 1024 * 1024 * 1024,
                             used=12 * 1024 * 1024 * 1024, percent=75.0, swap_total=4 * 1024 * 1024 * 1024,
                             swap_used=0, swap_free=4 * 1024 * 1024 * 1024, swap_percent=0.0),
        disk=DiskMetrics(total=500 * 1024 * 1024 * 1024, used=200 * 1024 * 1024 * 1024,
                         free=300 * 1024 * 1024 * 1024, percent=40.0, read_bytes_per_sec=0.0,
                         write_bytes_per_sec=0.0),
        network=NetworkMetrics(upload_speed=0.0, download_speed=0.0),
        process_count=120
    )
    monitor.collect_snapshot.return_value = snap

    procs = [
        ProcessInfo(pid=1001, name="chrome.exe",
                    cpu_percent=12.0, memory_percent=25.0, memory_mb=4000.0,
                    num_threads=15, create_time=time.time() - 3600, username="User"),
        ProcessInfo(pid=1002, name="blender.exe",
                    cpu_percent=60.0, memory_percent=15.0, memory_mb=2400.0,
                    num_threads=24, create_time=time.time() - 1200, username="User")
    ]
    monitor.get_processes.return_value = procs

    health = HealthScoreBreakdown(total_score=82.0, cpu_score=90.0, memory_score=85.0,
                                 swap_score=100.0, disk_score=100.0)
    analysis.calculate_health_score.return_value = health
    analysis.diagnose.return_value = []
    predictive.analyze_predictions.return_value = []

    engine = AskOSenseEngine(monitor, analysis, predictive, db)
    return engine, db


class TestAskOSenseEngine:

    def test_question_why_is_pc_slow(self, mock_deps):
        engine, _ = mock_deps
        ans = engine.ask("Why is my PC slow?")
        assert "System Health Score" in ans
        assert "82/100" in ans or "Health" in ans

    def test_question_top_memory(self, mock_deps):
        engine, _ = mock_deps
        ans = engine.ask("Which process uses the most memory?")
        assert "chrome.exe" in ans
        assert "4000 MB" in ans

    def test_question_top_cpu(self, mock_deps):
        engine, _ = mock_deps
        ans = engine.ask("Which process uses the most CPU?")
        assert "blender.exe" in ans or "chrome.exe" in ans

    def test_question_memory_increasing(self, mock_deps):
        engine, _ = mock_deps
        ans = engine.ask("Is memory usage increasing?")
        assert "RAM" in ans or "Memory" in ans

    def test_question_safest_recommendation(self, mock_deps):
        engine, _ = mock_deps
        ans = engine.ask("Which recommendation is safest?")
        assert "Safe" in ans or "disruption" in ans

    def test_question_recovery_action_outcome(self, mock_deps):
        engine, db = mock_deps
        # Insert a simulated recovery action
        db.save_recovery_action(
            action_name="trim_working_set",
            target_process="chrome.exe",
            target_pid=1001,
            freed_memory_mb=450.0,
            cpu_drop=5.0,
            before_health=70.0,
            after_health=85.0,
            verified=True,
            details="Freed 450 MB working set"
        )
        ans = engine.ask("Did the last recovery action improve performance?")
        assert "trim_working_set" in ans
        assert "chrome.exe" in ans
        assert "450" in ans

    def test_unknown_fallback_privacy(self, mock_deps):
        engine, _ = mock_deps
        ans = engine.ask("Can you bake a cake?")
        assert "OSense Assistant" in ans
        assert "offline" in ans.lower() or "local" in ans.lower()
