"""
Data models for diagnostics, health scoring, predictive alerts, and behavior anomalies.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Any


class Severity(Enum):
    HEALTHY = "Healthy"
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"

    def __str__(self):
        return self.value


@dataclass
class HealthScoreBreakdown:
    total_score: float = 100.0
    cpu_score: float = 100.0
    memory_score: float = 100.0
    swap_score: float = 100.0
    disk_score: float = 100.0
    factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'total_score': self.total_score,
            'cpu_score': self.cpu_score,
            'memory_score': self.memory_score,
            'swap_score': self.swap_score,
            'disk_score': self.disk_score,
            'factors': self.factors,
        }


@dataclass
class Diagnosis:
    title: str = ""
    severity: Severity = Severity.HEALTHY
    evidence: str = ""
    probable_cause: str = ""
    confidence: str = "High"
    recommendation: str = ""
    explanation: str = ""
    evidence_strength: float = 1.0
    category: str = "General"
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'title': self.title,
            'severity': self.severity.value if isinstance(self.severity, Severity) else str(self.severity),
            'evidence': self.evidence,
            'probable_cause': self.probable_cause,
            'confidence': self.confidence,
            'recommendation': self.recommendation,
            'explanation': self.explanation,
            'evidence_strength': self.evidence_strength,
            'category': self.category,
            'metrics': self.metrics,
        }


@dataclass
class PredictiveAlert:
    headline: str
    severity: str
    confidence: str
    evidence: str
    prevention_action: str
    projected_minutes: Optional[float] = None
    assumptions: str = ""
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BehaviorAlert:
    alert_type: str
    process_name: str
    pid: int
    severity: str
    description: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
