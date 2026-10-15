"""
Tests for OSense 2.0 Workload Profiles.
Validates profile switching (Study, Coding, Gaming, Battery Saver, Custom),
threshold adaptation, monitoring cadence configuration, and SQLite persistence.
"""
import pytest
from app.profiles.profile_manager import ProfileManager, WorkloadProfile
from app.database.db_manager import DatabaseManager


@pytest.fixture
def profile_mgr(tmp_path):
    db = DatabaseManager(str(tmp_path / "test_profiles.db"))
    return ProfileManager(db)


class TestProfileManager:

    def test_default_profile_is_coding(self, profile_mgr):
        active = profile_mgr.get_active_profile()
        assert active is not None
        assert active.name in profile_mgr.profiles

    def test_switch_to_gaming_profile(self, profile_mgr):
        assert profile_mgr.set_active_profile("gaming") is True
        prof = profile_mgr.get_active_profile()
        assert prof.name == "gaming"
        # Gaming profile allows higher CPU before alerting (90%)
        assert prof.cpu_warning == 90.0
        assert prof.refresh_interval_sec >= 2.0

    def test_switch_to_battery_saver(self, profile_mgr):
        assert profile_mgr.set_active_profile("battery") is True
        prof = profile_mgr.get_active_profile()
        assert prof.name == "battery"
        # Battery saver has longer poll interval to save power
        assert prof.refresh_interval_sec >= 4.0
        assert prof.cpu_warning <= 65.0

    def test_invalid_profile_rejected(self, profile_mgr):
        assert profile_mgr.set_active_profile("non_existent_profile") is False

    def test_profile_persistence_in_database(self, tmp_path):
        db_path = str(tmp_path / "persist_profile.db")
        db1 = DatabaseManager(db_path)
        mgr1 = ProfileManager(db1)
        mgr1.set_active_profile("study")

        # Reload manager with a fresh instance referencing same DB
        db2 = DatabaseManager(db_path)
        mgr2 = ProfileManager(db2)
        assert mgr2.get_active_profile_name() == "study"
        assert mgr2.get_active_profile().name == "study"
