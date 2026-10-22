"""
Typed data models for hardware and operating system metrics.
Provides serialization, error reporting, and availability status.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
import time


@dataclass
class CpuMetrics:
    overall_percent: float = 0.0
    per_core_percent: list[float] = field(default_factory=list)
    core_count_logical: int = 0
    core_count_physical: int = 0
    frequency_current: float = 0.0  # MHz
    frequency_max: float = 0.0
    available: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryMetrics:
    total: int = 0
    used: int = 0
    available: int = 0
    percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_free: int = 0
    swap_percent: float = 0.0
    is_available: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiskMetrics:
    total: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0.0
    read_bytes: int = 0
    write_bytes: int = 0
    read_bytes_per_sec: float = 0.0
    write_bytes_per_sec: float = 0.0
    partitions: list[dict] = field(default_factory=list)
    io_available: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkMetrics:
    bytes_sent: int = 0
    bytes_recv: int = 0
    upload_speed: float = 0.0  # bytes/sec
    download_speed: float = 0.0  # bytes/sec
    packets_sent: int = 0
    packets_recv: int = 0
    is_available: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatteryMetrics:
    available: bool = False
    percent: float = 0.0
    plugged: bool = False
    secs_left: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessInfo:
    pid: int = 0
    name: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = ""
    create_time: float = 0.0
    username: str = ""
    num_threads: int = 0
    ppid: int = 0
    group_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SystemSnapshot:
    timestamp: float = 0.0
    cpu: CpuMetrics = field(default_factory=CpuMetrics)
    memory: MemoryMetrics = field(default_factory=MemoryMetrics)
    disk: DiskMetrics = field(default_factory=DiskMetrics)
    network: NetworkMetrics = field(default_factory=NetworkMetrics)
    battery: BatteryMetrics = field(default_factory=BatteryMetrics)
    uptime_seconds: float = 0.0
    process_count: int = 0
    platform_info: str = ""
    os_version: str = ""
    os_family: str = "unknown"
    collection_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
