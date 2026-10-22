"""
OSD Core — Operating System Diagnostics Shared Monitoring & Analysis Library.
Cross-platform telemetry collection, root-cause diagnosis, forecasting, and recovery.
"""
from osd_core.models import (
    CpuMetrics,
    MemoryMetrics,
    DiskMetrics,
    NetworkMetrics,
    BatteryMetrics,
    ProcessInfo,
    SystemSnapshot,
    Severity,
    HealthScoreBreakdown,
    Diagnosis,
    PredictiveAlert,
    BehaviorAlert,
    RecoveryPlan,
    RecoveryVerification,
)
from osd_core.platform_support import (
    PlatformAdapter,
    WindowsAdapter,
    LinuxAdapter,
    MacOSAdapter,
    FallbackAdapter,
    get_platform_adapter,
)
from osd_core.collectors import (
    SystemCollector,
    BehaviorCollector,
)
from osd_core.diagnostics import (
    AnalysisEngine,
    Thresholds,
    PredictiveEngine,
    WhatIfSimulator,
    SimulationResult,
)
from osd_core.recommendations import (
    RecommendationEngine,
    Recommendation,
    RecoveryAdvisor,
)
from osd_core.configuration import (
    get_app_dir,
    get_db_path,
    get_agent_token_path,
    get_logs_dir,
    WorkloadProfile,
    DEFAULT_PROFILES,
)

__version__ = "2.1.0"

__all__ = [
    # Models
    "CpuMetrics",
    "MemoryMetrics",
    "DiskMetrics",
    "NetworkMetrics",
    "BatteryMetrics",
    "ProcessInfo",
    "SystemSnapshot",
    "Severity",
    "HealthScoreBreakdown",
    "Diagnosis",
    "PredictiveAlert",
    "BehaviorAlert",
    "RecoveryPlan",
    "RecoveryVerification",
    # Platform Support
    "PlatformAdapter",
    "WindowsAdapter",
    "LinuxAdapter",
    "MacOSAdapter",
    "FallbackAdapter",
    "get_platform_adapter",
    # Collectors
    "SystemCollector",
    "BehaviorCollector",
    # Diagnostics
    "AnalysisEngine",
    "Thresholds",
    "PredictiveEngine",
    "WhatIfSimulator",
    "SimulationResult",
    # Recommendations
    "RecommendationEngine",
    "Recommendation",
    "RecoveryAdvisor",
    # Configuration
    "get_app_dir",
    "get_db_path",
    "get_agent_token_path",
    "get_logs_dir",
    "WorkloadProfile",
    "DEFAULT_PROFILES",
]
