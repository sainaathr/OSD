"""
Workload Profiles — Customizes monitoring sensitivity, alert thresholds,
polling cadence, and recommendation focus based on the active user task.
Profiles: Study, Coding, Gaming, Battery Saver, Custom.
"""
from dataclasses import dataclass
from typing import Optional
from app.analysis.engine import Thresholds, AnalysisEngine
from app.database.db_manager import DatabaseManager


@dataclass
class WorkloadProfile:
    name: str
    display_title: str
    icon: str
    description: str
    cpu_warning: float
    cpu_critical: float
    memory_warning: float
    memory_critical: float
    swap_warning: float
    refresh_interval_sec: float
    suppress_transient_cpu_alerts: bool = False
    focus_disk_network_lag: bool = False
    focus_battery_drain: bool = False

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'display_title': self.display_title,
            'icon': self.icon,
            'description': self.description,
            'cpu_warning': self.cpu_warning,
            'cpu_critical': self.cpu_critical,
            'memory_warning': self.memory_warning,
            'memory_critical': self.memory_critical,
            'swap_warning': self.swap_warning,
            'refresh_interval_sec': self.refresh_interval_sec,
            'suppress_transient_cpu_alerts': self.suppress_transient_cpu_alerts,
            'focus_disk_network_lag': self.focus_disk_network_lag,
            'focus_battery_drain': self.focus_battery_drain,
        }


DEFAULT_PROFILES: dict[str, WorkloadProfile] = {
    "study": WorkloadProfile(
        name="study",
        display_title="Study / Quiet",
        icon="📚",
        description="Prioritizes silent operation and low thermal output. Alerts early on background CPU consumers that cause fan noise.",
        cpu_warning=60.0,
        cpu_critical=80.0,
        memory_warning=75.0,
        memory_critical=90.0,
        swap_warning=40.0,
        refresh_interval_sec=2.5,
    ),
    "coding": WorkloadProfile(
        name="coding",
        display_title="Coding & Development",
        icon="💻",
        description="Tolerates high CPU bursts during compilation and package installs. Focuses alerts on runaway background memory leaks.",
        cpu_warning=85.0,
        cpu_critical=95.0,
        memory_warning=82.0,
        memory_critical=92.0,
        swap_warning=50.0,
        refresh_interval_sec=2.0,
        suppress_transient_cpu_alerts=True,
    ),
    "gaming": WorkloadProfile(
        name="gaming",
        display_title="Gaming & High Performance",
        icon="🎮",
        description="High CPU and RAM tolerance. Strictly monitors background disk I/O and network saturation that cause stutter or ping spikes.",
        cpu_warning=90.0,
        cpu_critical=98.0,
        memory_warning=88.0,
        memory_critical=95.0,
        swap_warning=60.0,
        refresh_interval_sec=2.0,
        focus_disk_network_lag=True,
    ),
    "battery": WorkloadProfile(
        name="battery",
        display_title="Battery Saver",
        icon="🔋",
        description="Extends battery life on mobile laptops by throttling polling cadence and identifying high-drain background tasks.",
        cpu_warning=65.0,
        cpu_critical=85.0,
        memory_warning=78.0,
        memory_critical=90.0,
        swap_warning=45.0,
        refresh_interval_sec=4.0,
        focus_battery_drain=True,
    ),
    "custom": WorkloadProfile(
        name="custom",
        display_title="Custom Profile",
        icon="⚙️",
        description="Fully customized threshold, cadence, and alert sensitivities defined by the user.",
        cpu_warning=75.0,
        cpu_critical=90.0,
        memory_warning=80.0,
        memory_critical=92.0,
        swap_warning=50.0,
        refresh_interval_sec=2.0,
    ),
}


class ProfileManager:
    """Manages workload profiles and applies customized thresholds to engines."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.profiles = dict(DEFAULT_PROFILES)

    def get_active_profile_name(self) -> str:
        return self.db.get_setting("active_workload_profile", "coding")

    def get_active_profile(self) -> WorkloadProfile:
        name = self.get_active_profile_name()
        return self.profiles.get(name, self.profiles["coding"])

    def set_active_profile(self, name: str) -> bool:
        if name in self.profiles:
            self.db.set_setting("active_workload_profile", name)
            return True
        return False

    def apply_to_engine(self, analysis_engine: AnalysisEngine):
        """Configure AnalysisEngine thresholds according to active profile."""
        profile = self.get_active_profile()
        thresholds = analysis_engine.thresholds
        thresholds.cpu_warning = profile.cpu_warning
        thresholds.cpu_critical = profile.cpu_critical
        thresholds.memory_warning = profile.memory_warning
        thresholds.memory_critical = profile.memory_critical
        thresholds.swap_warning = profile.swap_warning
