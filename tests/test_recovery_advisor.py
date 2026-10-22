"""
Tests for OSD Autonomous Recovery Advisor.
Validates the 6-step lifecycle: Detect -> Investigate -> Recommend -> Consent -> Execute -> Verify.
Tests safety guarantees, protected process refusal, and before/after verification auditing.
"""
import os
import pytest
import time
import psutil
from unittest.mock import MagicMock
from app.recommendations.recovery_advisor import RecoveryAdvisor, RecoveryPlan, RecoveryVerification
from app.monitoring.system_monitor import SystemMonitor, ProcessInfo, SystemSnapshot, CpuMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics
from app.analysis.engine import Diagnosis
from app.database.db_manager import DatabaseManager


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_advisor.db")
    return DatabaseManager(db_file)


@pytest.fixture
def mock_monitor():
    monitor = MagicMock(spec=SystemMonitor)
    return monitor


def create_mock_snapshot(cpu=85.0, mem=88.0):
    total_bytes = 16 * 1024 * 1024 * 1024
    used_bytes = int(total_bytes * (mem / 100.0))
    avail_bytes = total_bytes - used_bytes
    return SystemSnapshot(
        timestamp=time.time(),
        cpu=CpuMetrics(overall_percent=cpu, per_core_percent=[cpu], core_count_logical=4, core_count_physical=2, frequency_current=2400.0),
        memory=MemoryMetrics(total=total_bytes, available=avail_bytes,
                             used=used_bytes, percent=mem, swap_total=4 * 1024 * 1024 * 1024,
                             swap_used=1 * 1024 * 1024 * 1024, swap_free=3 * 1024 * 1024 * 1024, swap_percent=25.0),
        disk=DiskMetrics(total=500 * 1024 * 1024 * 1024, used=200 * 1024 * 1024 * 1024,
                         free=300 * 1024 * 1024 * 1024, percent=40.0, read_bytes_per_sec=0.0,
                         write_bytes_per_sec=0.0),
        network=NetworkMetrics(upload_speed=0.0, download_speed=0.0),
        process_count=100
    )


class TestRecoveryAdvisor:

    def test_plan_generation_for_memory_pressure(self, mock_monitor, test_db):
        advisor = RecoveryAdvisor(mock_monitor, db=test_db)
        diag = Diagnosis(
            category="Memory",
            severity="Critical",
            title="Sustained Memory Pressure",
            probable_cause="Process memory consumption",
            evidence="RAM at 88%",
            evidence_strength=0.9
        )
        snap = create_mock_snapshot(mem=88.0)
        procs = [
            ProcessInfo(pid=1234, name="heavy_app.exe",
                        cpu_percent=5.0, memory_percent=35.0, memory_mb=5600.0,
                        num_threads=10, create_time=time.time() - 500, username="User")
        ]

        plans = advisor.generate_plans([diag], snap, procs)
        assert len(plans) >= 1
        
        # Verify plans include safe working set trimming and graceful termination
        action_types = [p.action_type for p in plans]
        assert "trim_memory" in action_types
        assert "terminate" in action_types

        # Verify low disruption ranking on trim
        trim_plan = next(p for p in plans if p.action_type == "trim_memory")
        assert trim_plan.risk_level == "Low"
        assert trim_plan.target_pid == 1234

    def test_protected_process_refusal(self, mock_monitor, test_db):
        advisor = RecoveryAdvisor(mock_monitor, db=test_db)
        # Attempt to plan action against Windows critical system process
        diag = Diagnosis(
            category="CPU",
            severity="Critical",
            title="High CPU Usage",
            probable_cause="svchost.exe",
            evidence="CPU 95%",
            evidence_strength=0.9
        )
        snap = create_mock_snapshot(cpu=95.0)
        procs = [
            ProcessInfo(pid=888, name="svchost.exe",
                        cpu_percent=90.0, memory_percent=5.0, memory_mb=400.0,
                        num_threads=20, create_time=time.time() - 1000, username="SYSTEM")
        ]

        plans = advisor.generate_plans([diag], snap, procs)
        # Termination plan must NOT be generated for protected process svchost.exe
        term_plans = [p for p in plans if p.action_type == "terminate" and p.target_pid == 888]
        assert len(term_plans) == 0, "Protected processes must never receive termination plans"

    def test_execute_plan_with_verification(self, mock_monitor, test_db):
        advisor = RecoveryAdvisor(mock_monitor, db=test_db)
        curr_pid = os.getpid()
        curr_name = psutil.Process(curr_pid).name()

        plan = RecoveryPlan(
            plan_id="plan_test_01",
            issue_title="High RAM in Test App",
            evidence="RAM at 85%",
            probable_cause=f"{curr_name} memory hog",
            proposed_fix="Trim working set pages",
            expected_benefit="Free physical memory",
            risk_level="Low",
            action_type="trim_memory",
            target_pid=curr_pid,
            target_process=curr_name,
            baseline_cpu=40.0,
            baseline_mem_mb=120.0,
            baseline_health=70.0
        )

        # Mock monitor responses
        mock_monitor.trim_working_set.return_value = (True, "Reduced 50 MB")
        mock_monitor.collect_snapshot.return_value = create_mock_snapshot(cpu=20.0, mem=65.0)

        # Execute with instantaneous sleep_fn to avoid waiting
        ver = advisor.execute_approved_action(plan, sleep_fn=lambda s: None)
        assert ver.success is True
        assert ver.before_health >= 0

        # Verify DB audit log recorded the action
        logged = test_db.get_recovery_actions(limit=5)
        assert len(logged) >= 1
        assert logged[0]["action_name"] == "trim_memory"
        assert logged[0]["target_pid"] == curr_pid
