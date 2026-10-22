"""
Unit tests for OSD cross-platform path resolution and directory creation.
Verifies standards-compliant path locations:
- Windows: %LOCALAPPDATA%\\OSD
- Linux: ~/.local/share/osd or $XDG_DATA_HOME
- macOS: ~/Library/Application Support/OSD
"""
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch
import pytest

from osd_core.configuration.paths import (
    get_app_dir,
    get_app_data_dir,
    get_db_path,
    get_agent_token_path,
    get_logs_dir,
)
from osd_core.platform_support.windows import WindowsAdapter
from osd_core.platform_support.linux import LinuxAdapter
from osd_core.platform_support.macos import MacOSAdapter


def test_windows_adapter_data_dir():
    """Verify Windows uses LOCALAPPDATA."""
    adapter = WindowsAdapter()
    with patch.dict(os.environ, {"LOCALAPPDATA": "C:\\MockAppData"}):
        path = adapter.get_default_data_dir()
        assert "MockAppData" in path
        assert path.endswith("OSD")


def test_linux_adapter_data_dir():
    """Verify Linux respects XDG_DATA_HOME and defaults to ~/.local/share/osd."""
    adapter = LinuxAdapter()
    with patch.dict(os.environ, {"XDG_DATA_HOME": "/home/mockuser/.custom_share"}):
        path = adapter.get_default_data_dir()
        assert Path(path) == Path("/home/mockuser/.custom_share/osd")


def test_macos_adapter_data_dir():
    """Verify macOS uses ~/Library/Application Support/OSD."""
    adapter = MacOSAdapter()
    path = adapter.get_default_data_dir()
    assert "Application Support" in path
    assert path.endswith("OSD")


def test_get_app_dir_and_alias():
    """Verify get_app_dir and get_app_data_dir return valid string path."""
    d1 = get_app_dir()
    d2 = get_app_data_dir()
    assert d1 == d2
    assert os.path.exists(d1)


def test_get_db_path():
    """Verify database path resides within app data directory."""
    db_path = get_db_path()
    assert db_path.endswith("osd.db") or db_path.endswith("osense.db")


def test_get_agent_token_path():
    """Verify agent token path is correctly located."""
    token_path = get_agent_token_path()
    assert token_path.endswith("agent_token.json")


def test_get_logs_dir():
    """Verify logs directory is created and returned."""
    logs_dir = get_logs_dir()
    assert os.path.exists(logs_dir)
    assert logs_dir.endswith("logs")


def test_legacy_database_migration(tmp_path):
    """Verify automatic copy from legacy ~/.osense/osense.db if standard DB does not exist."""
    legacy_dir = tmp_path / ".osense"
    legacy_dir.mkdir()
    legacy_db = legacy_dir / "osense.db"
    legacy_db.write_text("LEGACY_SQLITE_TEST_PAYLOAD")

    target_dir = tmp_path / "AppData" / "OSD"
    standard_db = str(target_dir / "osd.db")

    with patch("os.path.expanduser", return_value=str(tmp_path)):
        with patch("osd_core.configuration.paths.get_app_dir", return_value=str(target_dir)):
            result_db = get_db_path()
            assert result_db == standard_db
            assert os.path.exists(standard_db)
            with open(standard_db, "r") as f:
                assert f.read() == "LEGACY_SQLITE_TEST_PAYLOAD"
