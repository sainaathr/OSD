"""
Data models for recovery plans and verification audit outcomes.
"""
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RecoveryPlan:
    plan_id: str
    issue_title: str
    action_type: str        # "terminate", "lower_priority", "trim_memory", "inspect_cleanup"
    target_process: str
    target_pid: int
    proposed_fix: str
    expected_benefit: str
    risk_level: str         # "Low", "Medium", "High"
    evidence: str
    probable_cause: str
    baseline_cpu: float = 0.0
    baseline_mem_mb: float = 0.0
    baseline_health: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecoveryVerification:
    success: bool
    message: str
    before_cpu: float
    after_cpu: float
    before_mem_mb: float
    after_mem_mb: float
    before_health: float
    after_health: float
    freed_memory_mb: float
    cpu_drop: float
    health_gain: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
