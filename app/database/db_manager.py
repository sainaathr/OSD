"""
Database Manager — SQLite storage for history, diagnoses, recommendations, and settings.
"""
import sqlite3
import json
import time
import os
from typing import Optional, Any
from contextlib import contextmanager


class DatabaseManager:
    """Manages SQLite database for OSense."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = os.path.join(os.path.expanduser("~"), ".osense")
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, "osense.db")
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables."""
        try:
            with self._get_conn() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS resource_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        cpu_percent REAL,
                        memory_percent REAL,
                        swap_percent REAL,
                        disk_percent REAL,
                        disk_read_speed REAL,
                        disk_write_speed REAL,
                        net_upload_speed REAL,
                        net_download_speed REAL,
                        process_count INTEGER,
                        health_score REAL
                    );
                    
                    CREATE TABLE IF NOT EXISTS diagnoses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        title TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        evidence TEXT,
                        probable_cause TEXT,
                        confidence TEXT,
                        recommendation TEXT,
                        explanation TEXT,
                        report_json TEXT
                    );
                    
                    CREATE TABLE IF NOT EXISTS recommendations_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        problem TEXT NOT NULL,
                        evidence TEXT,
                        action TEXT,
                        benefit TEXT,
                        risk_level TEXT,
                        acted_on INTEGER DEFAULT 0
                    );
                    
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    
                    CREATE TABLE IF NOT EXISTS recovery_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        action_name TEXT NOT NULL,
                        target_process TEXT,
                        target_pid INTEGER,
                        risk_level TEXT,
                        before_cpu REAL,
                        before_memory_mb REAL,
                        before_health REAL,
                        after_cpu REAL,
                        after_memory_mb REAL,
                        after_health REAL,
                        freed_memory_mb REAL,
                        cpu_drop REAL,
                        health_gain REAL,
                        verified INTEGER DEFAULT 0,
                        notes TEXT
                    );
                    
                    CREATE TABLE IF NOT EXISTS behavior_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        alert_type TEXT NOT NULL,
                        process_name TEXT,
                        pid INTEGER,
                        severity TEXT NOT NULL,
                        description TEXT,
                        details TEXT
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_resource_history_ts ON resource_history(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_diagnoses_ts ON diagnoses(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_recovery_actions_ts ON recovery_actions(timestamp);
                """)
        except Exception as e:
            print(f"[OSense DB] Warning: Could not initialize database: {e}")
    
    # --- Resource History ---
    def save_resource_sample(self, timestamp: float, cpu: float, memory: float,
                             swap: float, disk: float, disk_read: float, disk_write: float,
                             net_up: float, net_down: float, proc_count: int,
                             health_score: float):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO resource_history 
                    (timestamp, cpu_percent, memory_percent, swap_percent, disk_percent,
                     disk_read_speed, disk_write_speed, net_upload_speed, net_download_speed,
                     process_count, health_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, cpu, memory, swap, disk, disk_read, disk_write,
                      net_up, net_down, proc_count, health_score))
        except Exception as e:
            print(f"[OSense DB] Warning: Could not save resource sample: {e}")
    
    def get_resource_history(self, hours: float = 1.0, limit: int = 500) -> list[dict]:
        try:
            with self._get_conn() as conn:
                cutoff = time.time() - (hours * 3600)
                rows = conn.execute("""
                    SELECT * FROM resource_history 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (cutoff, limit)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []
    
    # --- Diagnoses ---
    def save_diagnosis(self, timestamp: float, title: str, severity: str,
                       evidence: str, probable_cause: str, confidence: str,
                       recommendation: str, explanation: str, report_json: str = ""):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO diagnoses 
                    (timestamp, title, severity, evidence, probable_cause, 
                     confidence, recommendation, explanation, report_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, title, severity, evidence, probable_cause,
                      confidence, recommendation, explanation, report_json))
        except Exception as e:
            print(f"[OSense DB] Warning: Could not save diagnosis: {e}")
    
    def get_diagnoses(self, limit: int = 50) -> list[dict]:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM diagnoses ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []
    
    # --- Settings ---
    def get_setting(self, key: str, default: str = "") -> str:
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = ?", (key,)
                ).fetchone()
                return row['value'] if row else default
        except Exception:
            return default
    
    def set_setting(self, key: str, value: str):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
                """, (key, value))
        except Exception as e:
            print(f"[OSense DB] Warning: Could not save setting: {e}")
    
    def get_all_settings(self) -> dict[str, str]:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT key, value FROM settings").fetchall()
                return {r['key']: r['value'] for r in rows}
        except Exception:
            return {}
    
    # --- Recovery Actions ---
    def save_recovery_action(self, action_name: str = "", target_process: str = "",
                             target_pid: int = 0, risk_level: str = "Low", before_cpu: float = 0.0,
                             before_memory_mb: float = 0.0, before_health: float = 100.0,
                             after_cpu: float = 0.0, after_memory_mb: float = 0.0,
                             after_health: float = 0.0, freed_memory_mb: float = 0.0,
                             cpu_drop: float = 0.0, health_gain: float = 0.0,
                             verified: int = 1, notes: str = "", timestamp: Optional[float] = None,
                             details: str = "") -> int:
        try:
            ts = timestamp if timestamp is not None else time.time()
            final_notes = notes or details
            with self._get_conn() as conn:
                cur = conn.execute("""
                    INSERT INTO recovery_actions
                    (timestamp, action_name, target_process, target_pid, risk_level,
                     before_cpu, before_memory_mb, before_health, after_cpu, after_memory_mb,
                     after_health, freed_memory_mb, cpu_drop, health_gain, verified, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ts, action_name, target_process, target_pid, risk_level,
                      before_cpu, before_memory_mb, before_health, after_cpu, after_memory_mb,
                      after_health, freed_memory_mb, cpu_drop, health_gain, int(verified), final_notes))
                return cur.lastrowid
        except Exception as e:
            print(f"[OSense DB] Warning: Could not save recovery action: {e}")
            return -1

    def get_recovery_actions(self, limit: int = 50) -> list[dict]:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM recovery_actions ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_latest_recovery_action(self) -> Optional[dict]:
        try:
            with self._get_conn() as conn:
                row = conn.execute("""
                    SELECT * FROM recovery_actions ORDER BY timestamp DESC LIMIT 1
                """).fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    # --- Behavior Alerts ---
    def save_behavior_alert(self, pid: int = 0, process_name: str = "", alert_type: str = "",
                            severity: str = "Warning", description: str = "", details: str = "",
                            timestamp: Optional[float] = None):
        try:
            ts = timestamp if timestamp is not None else time.time()
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO behavior_alerts
                    (timestamp, alert_type, process_name, pid, severity, description, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ts, alert_type, process_name, pid, severity, description, details))
        except Exception as e:
            print(f"[OSense DB] Warning: Could not save behavior alert: {e}")

    def get_behavior_alerts(self, limit: int = 50) -> list[dict]:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM behavior_alerts ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    # --- Session & Timeline Analytics ---
    def get_session_stats(self, hours: float = 1.0) -> dict:
        """Calculate aggregate session metrics for comparison."""
        try:
            cutoff = time.time() - (hours * 3600)
            with self._get_conn() as conn:
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as count,
                        AVG(cpu_percent) as avg_cpu,
                        MAX(cpu_percent) as max_cpu,
                        AVG(memory_percent) as avg_mem,
                        MAX(memory_percent) as max_mem,
                        AVG(health_score) as avg_health,
                        MIN(health_score) as min_health
                    FROM resource_history
                    WHERE timestamp >= ?
                """, (cutoff,)).fetchone()
                
                recs_count = conn.execute("""
                    SELECT COUNT(*) as c FROM recovery_actions WHERE timestamp >= ?
                """, (cutoff,)).fetchone()

                count_val = row['count'] if row else 0
                return {
                    'count': count_val,
                    'total_samples': count_val,
                    'avg_cpu': round(row['avg_cpu'] or 0.0, 1),
                    'max_cpu': round(row['max_cpu'] or 0.0, 1),
                    'avg_mem': round(row['avg_mem'] or 0.0, 1),
                    'max_mem': round(row['max_mem'] or 0.0, 1),
                    'avg_health': round(row['avg_health'] or 100.0, 1),
                    'min_health': round(row['min_health'] or 100.0, 1),
                    'recovery_actions_count': recs_count['c'] if recs_count else 0,
                }
        except Exception:
            return {'count': 0, 'avg_cpu': 0, 'max_cpu': 0, 'avg_mem': 0, 'max_mem': 0, 'avg_health': 100, 'min_health': 100, 'recovery_actions_count': 0}

    # --- Maintenance ---
    def cleanup_old_data(self, retention_hours: float = 168.0):
        """Remove data older than retention period (default 7 days)."""
        try:
            cutoff = time.time() - (retention_hours * 3600)
            with self._get_conn() as conn:
                conn.execute("DELETE FROM resource_history WHERE timestamp < ?", (cutoff,))
                conn.execute("DELETE FROM diagnoses WHERE timestamp < ?", (cutoff,))
                conn.execute("DELETE FROM recommendations_log WHERE timestamp < ?", (cutoff,))
                conn.execute("DELETE FROM recovery_actions WHERE timestamp < ?", (cutoff,))
                conn.execute("DELETE FROM behavior_alerts WHERE timestamp < ?", (cutoff,))
        except Exception as e:
            print(f"[OSense DB] Warning: Cleanup failed: {e}")
    
    def clear_all_history(self):
        """Clear all historical data."""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM resource_history")
                conn.execute("DELETE FROM diagnoses")
                conn.execute("DELETE FROM recommendations_log")
                conn.execute("DELETE FROM recovery_actions")
                conn.execute("DELETE FROM behavior_alerts")
        except Exception as e:
            print(f"[OSense DB] Warning: Could not clear history: {e}")
    
    def get_history_stats(self) -> dict:
        """Get statistics about stored data."""
        try:
            with self._get_conn() as conn:
                rh = conn.execute("SELECT COUNT(*) as c FROM resource_history").fetchone()
                dg = conn.execute("SELECT COUNT(*) as c FROM diagnoses").fetchone()
                ra = conn.execute("SELECT COUNT(*) as c FROM recovery_actions").fetchone()
                return {
                    'resource_samples': rh['c'] if rh else 0,
                    'diagnoses': dg['c'] if dg else 0,
                    'recovery_actions': ra['c'] if ra else 0,
                    'db_path': self.db_path,
                    'db_size_mb': round(os.path.getsize(self.db_path) / (1024*1024), 2) if os.path.exists(self.db_path) else 0,
                }
        except Exception:
            return {'resource_samples': 0, 'diagnoses': 0, 'recovery_actions': 0, 'db_path': self.db_path, 'db_size_mb': 0}
