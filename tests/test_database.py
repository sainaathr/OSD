"""
Unit tests for DatabaseManager.
"""
import os
import time
import pytest
from app.database.db_manager import DatabaseManager


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing an isolated SQLite database."""
    db_file = tmp_path / "test_osd.db"
    return DatabaseManager(str(db_file))


class TestDatabaseManager:
    """Test SQLite persistence, retrieval, settings, and retention."""

    def test_db_initialization(self, temp_db):
        assert os.path.exists(temp_db.db_path)
        stats = temp_db.get_history_stats()
        assert stats['resource_samples'] == 0
        assert stats['diagnoses'] == 0

    def test_save_and_get_resource_sample(self, temp_db):
        now = time.time()
        temp_db.save_resource_sample(
            timestamp=now,
            cpu=45.5,
            memory=60.2,
            swap=12.0,
            disk=70.0,
            disk_read=1024000.0,
            disk_write=2048000.0,
            net_up=50000.0,
            net_down=150000.0,
            proc_count=180,
            health_score=85.0
        )
        history = temp_db.get_resource_history(hours=1.0)
        assert len(history) == 1
        record = history[0]
        assert record['cpu_percent'] == pytest.approx(45.5, rel=1e-2)
        assert record['memory_percent'] == pytest.approx(60.2, rel=1e-2)
        assert record['health_score'] == pytest.approx(85.0, rel=1e-2)
        assert record['process_count'] == 180

    def test_save_and_get_diagnosis(self, temp_db):
        now = time.time()
        temp_db.save_diagnosis(
            timestamp=now,
            title="High CPU Utilization",
            severity="Warning",
            evidence="CPU reached 85%",
            probable_cause="Heavy task",
            confidence="High",
            recommendation="Inspect processes",
            explanation="CPU load is high",
            report_json='{"test": true}'
        )
        diags = temp_db.get_diagnoses(limit=10)
        assert len(diags) == 1
        d = diags[0]
        assert d['title'] == "High CPU Utilization"
        assert d['severity'] == "Warning"
        assert d['confidence'] == "High"

    def test_settings_storage(self, temp_db):
        # Default value when key does not exist
        val = temp_db.get_setting("custom_key", "default_val")
        assert val == "default_val"

        # Set and get
        temp_db.set_setting("refresh_interval", "1.5")
        assert temp_db.get_setting("refresh_interval") == "1.5"

        # Update existing
        temp_db.set_setting("refresh_interval", "3.0")
        assert temp_db.get_setting("refresh_interval") == "3.0"

        all_settings = temp_db.get_all_settings()
        assert all_settings.get("refresh_interval") == "3.0"

    def test_clear_all_history(self, temp_db):
        temp_db.save_resource_sample(
            timestamp=time.time(), cpu=50, memory=50, swap=0, disk=50,
            disk_read=0, disk_write=0, net_up=0, net_down=0, proc_count=100, health_score=90
        )
        temp_db.save_diagnosis(
            timestamp=time.time(), title="Test", severity="Info",
            evidence="", probable_cause="", confidence="", recommendation="", explanation=""
        )
        assert temp_db.get_history_stats()['resource_samples'] == 1
        assert temp_db.get_history_stats()['diagnoses'] == 1

        temp_db.clear_all_history()
        assert temp_db.get_history_stats()['resource_samples'] == 0
        assert temp_db.get_history_stats()['diagnoses'] == 0

    def test_cleanup_retention(self, temp_db):
        old_time = time.time() - (200 * 3600)  # 200 hours ago
        recent_time = time.time() - (10 * 3600)  # 10 hours ago

        temp_db.save_resource_sample(
            timestamp=old_time, cpu=10, memory=20, swap=0, disk=30,
            disk_read=0, disk_write=0, net_up=0, net_down=0, proc_count=50, health_score=95
        )
        temp_db.save_resource_sample(
            timestamp=recent_time, cpu=15, memory=25, swap=0, disk=35,
            disk_read=0, disk_write=0, net_up=0, net_down=0, proc_count=55, health_score=92
        )

        assert temp_db.get_history_stats()['resource_samples'] == 2

        # Cleanup data older than 24 hours
        temp_db.cleanup_old_data(retention_hours=24.0)
        assert temp_db.get_history_stats()['resource_samples'] == 1

    def test_recovery_actions_persistence(self, temp_db):
        temp_db.save_recovery_action(
            action_name="trim_working_set",
            target_process="firefox.exe",
            target_pid=3000,
            freed_memory_mb=120.0,
            cpu_drop=2.5,
            before_health=75.0,
            after_health=85.0,
            verified=True,
            details="Reduced working set"
        )
        actions = temp_db.get_recovery_actions(limit=10)
        assert len(actions) == 1
        assert actions[0]["target_process"] == "firefox.exe"
        assert actions[0]["freed_memory_mb"] == 120.0
        assert actions[0]["verified"] == 1

        latest = temp_db.get_latest_recovery_action()
        assert latest is not None
        assert latest["target_pid"] == 3000

    def test_behavior_alerts_persistence(self, temp_db):
        temp_db.save_behavior_alert(
            pid=4000,
            process_name="rogue.exe",
            alert_type="CPU Surge",
            description="CPU surged from 5% to 85%",
            severity="Critical"
        )
        alerts = temp_db.get_behavior_alerts(limit=5)
        assert len(alerts) == 1
        assert alerts[0]["process_name"] == "rogue.exe"
        assert alerts[0]["severity"] == "Critical"

    def test_session_stats_calculation(self, temp_db):
        temp_db.save_resource_sample(
            timestamp=time.time(), cpu=40.0, memory=60.0, swap=10.0, disk=50.0,
            disk_read=1000, disk_write=2000, net_up=500, net_down=1500, proc_count=100, health_score=80.0
        )
        temp_db.save_resource_sample(
            timestamp=time.time(), cpu=60.0, memory=80.0, swap=20.0, disk=50.0,
            disk_read=3000, disk_write=4000, net_up=1500, net_down=2500, proc_count=110, health_score=90.0
        )
        stats = temp_db.get_session_stats(hours=1.0)
        assert stats["avg_cpu"] == 50.0
        assert stats["max_cpu"] == 60.0
        assert stats["avg_mem"] == 70.0
        assert stats["max_mem"] == 80.0
        assert stats["avg_health"] == 85.0
        assert stats["total_samples"] == 2
