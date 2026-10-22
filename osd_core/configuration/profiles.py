"""
Workload profiles configuration for OSD.
Tuning sensitivity, polling cadence, and thresholds for tasks:
Study, Coding, Gaming, Battery Saver, Custom.
"""
from dataclasses import dataclass
from typing import Optional, Any


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

    def to_dict(self) -> dict[str, Any]:
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
        description="User-configured thresholds and monitoring interval.",
        cpu_warning=80.0,
        cpu_critical=90.0,
        memory_warning=80.0,
        memory_critical=90.0,
        swap_warning=50.0,
        refresh_interval_sec=2.0,
    ),
}
