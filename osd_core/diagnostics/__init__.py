"""
OSD Diagnostics Core
"""
from osd_core.diagnostics.engine import (
    AnalysisEngine,
    Thresholds,
    Diagnosis,
    HealthScoreBreakdown,
    Severity,
)
from osd_core.diagnostics.predictive import (
    PredictiveEngine,
    PredictiveAlert,
    calculate_linear_slope_and_r2,
)
from osd_core.diagnostics.simulator import (
    WhatIfSimulator,
    SimulationResult,
)

__all__ = [
    "AnalysisEngine",
    "Thresholds",
    "Diagnosis",
    "HealthScoreBreakdown",
    "Severity",
    "PredictiveEngine",
    "PredictiveAlert",
    "calculate_linear_slope_and_r2",
    "WhatIfSimulator",
    "SimulationResult",
]
