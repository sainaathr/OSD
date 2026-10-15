"""
Predictive Performance Engine — Time-series analysis, slope estimation,
and resource pressure projections based on real rolling metric samples.
"""
import time
import math
from dataclasses import dataclass, field
from typing import Optional
from app.monitoring.system_monitor import SystemSnapshot, ProcessInfo


@dataclass
class PredictiveAlert:
    metric: str                     # "Memory", "CPU", "Swap", "Disk Storage"
    severity: str                   # "Warning", "Critical", "Information"
    headline: str
    current_value: float
    current_rate_per_min: float
    projected_minutes: Optional[float]
    confidence: str                 # "Low", "Medium", "High"
    evidence: str
    assumptions: str
    limitations: str
    prevention_action: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'metric': self.metric,
            'severity': self.severity,
            'headline': self.headline,
            'current_value': round(self.current_value, 1),
            'current_rate_per_min': round(self.current_rate_per_min, 2),
            'projected_minutes': round(self.projected_minutes, 1) if self.projected_minutes is not None else None,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'assumptions': self.assumptions,
            'limitations': self.limitations,
            'prevention_action': self.prevention_action,
            'timestamp': self.timestamp,
        }


def calculate_linear_slope_and_r2(x: list[float], y: list[float]) -> tuple[float, float]:
    """Calculate slope (dy/dx) and Pearson correlation coefficient R²."""
    n = len(x)
    if n < 2:
        return 0.0, 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denom_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denom_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    if denom_x == 0:
        return 0.0, 0.0

    slope = numerator / denom_x

    if denom_x * denom_y <= 0:
        r2 = 0.0
    else:
        r = numerator / math.sqrt(denom_x * denom_y)
        r2 = r ** 2

    return slope, r2


class PredictiveEngine:
    """Time-series resource forecasting and early pressure detection."""

    def __init__(self, max_history: int = 30):
        self.max_history = max_history
        self._history: list[SystemSnapshot] = []

    def add_snapshot(self, snapshot: SystemSnapshot):
        self._history.append(snapshot)
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def clear(self):
        self._history.clear()

    def get_sample_count(self) -> int:
        return len(self._history)

    def analyze_predictions(self, current_snapshot: SystemSnapshot,
                            processes: Optional[list[ProcessInfo]] = None) -> list[PredictiveAlert]:
        """Examine rolling trend slopes and generate predictive early warnings."""
        alerts: list[PredictiveAlert] = []

        # We require at least 4 rolling samples to make a meaningful statistical projection
        if len(self._history) < 4:
            return alerts

        timestamps = [s.timestamp - self._history[0].timestamp for s in self._history]
        
        # 1. Physical RAM Trend Analysis
        mem_pcts = [s.memory.percent for s in self._history]
        mem_slope_sec, mem_r2 = calculate_linear_slope_and_r2(timestamps, mem_pcts)
        mem_slope_min = mem_slope_sec * 60.0  # % per minute

        avail_mb = current_snapshot.memory.available / (1024 * 1024)
        total_mb = current_snapshot.memory.total / (1024 * 1024)

        if mem_slope_min > 0.4 and mem_r2 >= 0.50 and current_snapshot.memory.percent > 65.0:
            growth_mb_per_min = (mem_slope_min / 100.0) * total_mb
            projected_min = (avail_mb / growth_mb_per_min) if growth_mb_per_min > 0 else None

            confidence = "High" if (mem_r2 > 0.80 and len(self._history) >= 8) else ("Medium" if mem_r2 > 0.60 else "Low")
            
            top_growing_proc = ""
            if processes:
                heavy = sorted(processes, key=lambda p: p.memory_mb, reverse=True)[:3]
                top_growing_proc = f" Top active consumer: {heavy[0].name} ({heavy[0].memory_mb:.0f} MB)."

            alerts.append(PredictiveAlert(
                metric="Memory",
                severity="Critical" if (projected_min and projected_min < 15.0) else "Warning",
                headline="Impending Physical Memory Saturation" if (projected_min and projected_min < 30.0) else "Steady Upward RAM Growth Detected",
                current_value=current_snapshot.memory.percent,
                current_rate_per_min=growth_mb_per_min,
                projected_minutes=projected_min,
                confidence=confidence,
                evidence=f"RAM has grown at +{growth_mb_per_min:.0f} MB/min (+{mem_slope_min:.1f}%/min) over the last {len(self._history)} samples (R²={mem_r2:.2f}). Available RAM: {avail_mb/1024:.1f} GB.{top_growing_proc}",
                assumptions="Assumes current workload intensity and memory allocation rates continue without process exits.",
                limitations="Windows working set trimming, memory compression, and page file paging will automatically intervene as RAM tightens.",
                prevention_action="Close inactive memory-intensive applications now to avoid swapping and sluggish response."
            ))

        # 2. Swap / Page File Accumulation Trend
        swap_pcts = [s.memory.swap_percent for s in self._history]
        swap_slope_sec, swap_r2 = calculate_linear_slope_and_r2(timestamps, swap_pcts)
        swap_slope_min = swap_slope_sec * 60.0

        if swap_slope_min > 0.5 and swap_r2 >= 0.55 and current_snapshot.memory.swap_percent > 35.0:
            confidence = "High" if swap_r2 > 0.80 else "Medium"
            alerts.append(PredictiveAlert(
                metric="Swap",
                severity="Warning",
                headline="Accelerating Virtual Memory (Page File) Dependence",
                current_value=current_snapshot.memory.swap_percent,
                current_rate_per_min=swap_slope_min,
                projected_minutes=None,
                confidence=confidence,
                evidence=f"Page file usage is climbing at +{swap_slope_min:.1f}%/min (current: {current_snapshot.memory.swap_percent:.1f}% used).",
                assumptions="Linear growth indicates physical RAM capacity has been exceeded for active tasks.",
                limitations="System responsiveness will degrade as disk-based paging increases.",
                prevention_action="Relieve physical RAM pressure immediately to reduce disk paging latency."
            ))

        # 3. CPU Sustained Saturation
        cpu_pcts = [s.cpu.overall_percent for s in self._history]
        avg_cpu = sum(cpu_pcts) / len(cpu_pcts)
        if avg_cpu > 78.0 and all(c > 65.0 for c in cpu_pcts[-4:]):
            alerts.append(PredictiveAlert(
                metric="CPU",
                severity="Warning" if avg_cpu < 90.0 else "Critical",
                headline="Persistent Compute Saturation Emerging",
                current_value=current_snapshot.cpu.overall_percent,
                current_rate_per_min=0.0,
                projected_minutes=None,
                confidence="High",
                evidence=f"CPU has remained pegged at an average of {avg_cpu:.1f}% across all recent {len(self._history)} samples.",
                assumptions="Workload appears compute-bound (compilation, rendering, or runaway loop).",
                limitations="Short burst workloads (e.g. batch compilation) will naturally subside upon completion.",
                prevention_action="Inspect the top CPU-consuming thread or lower process priority to restore UI responsiveness."
            ))

        return alerts
