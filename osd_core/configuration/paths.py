"""
Cross-platform path resolution for application configuration, database, and cache.
Complies with Windows LocalAppData, Linux XDG Base Directory, and macOS Application Support.
Includes backward compatibility migration from ~/.osense/osense.db.
"""
import os
import shutil
from typing import Optional
from osd_core.platform_support.factory import get_platform_adapter


def get_app_dir() -> str:
    """Return platform-standard application data directory."""
    return get_platform_adapter().get_default_data_dir()


# Alias for compatibility
get_app_data_dir = get_app_dir


def get_db_path(custom_path: Optional[str] = None) -> str:
    """
    Return path to the SQLite database.
    If custom_path is provided, use that.
    Otherwise, check for existing legacy ~/.osense/osense.db, or use standard osd.db.
    """
    if custom_path:
        return custom_path

    # Check for legacy database path first for backward compatibility
    legacy_dir = os.path.join(os.path.expanduser('~'), '.osense')
    legacy_db = os.path.join(legacy_dir, 'osense.db')

    standard_dir = get_app_dir()
    standard_db = os.path.join(standard_dir, 'osd.db')

    # If standard db already exists, use it
    if os.path.exists(standard_db):
        return standard_db

    # If legacy db exists and standard doesn't, migrate it cleanly
    if os.path.exists(legacy_db):
        try:
            os.makedirs(standard_dir, exist_ok=True)
            shutil.copy2(legacy_db, standard_db)
            return standard_db
        except Exception:
            # If copy fails, continue using legacy db seamlessly
            return legacy_db

    return standard_db


def get_agent_token_path() -> str:
    """Return path to local agent security token file."""
    return os.path.join(get_app_dir(), 'agent_token.json')


def get_logs_dir() -> str:
    """Return path to application logs directory."""
    logs_dir = os.path.join(get_app_dir(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir
