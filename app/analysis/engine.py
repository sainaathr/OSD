"""
Root-Cause Analysis Engine — Analyzes system metrics to identify performance issues.
"""
import time
from dataclasses import dataclass, field
from typing import Optional
from app.monitoring.system_monitor import SystemSnapshot, ProcessInfo


# Severity Levels
class Severity:
    HEALTHY = "Healthy"
    INFO = "Information"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class Diagnosis:
    title: str = ""
    severity: str = Severity.HEALTHY
    evidence: str = ""
    probable_cause: str = ""
    confidence: str = "Low"  # Low, Medium, High
    recommendation: str = ""
    explanation: str = ""
    evidence_strength: float = 0.5  # 0.0 to 1.0 ranking score
    category: str = "General"        # CPU, Memory, Swap, Disk, Multi-Bottleneck

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'severity': self.severity,
            'evidence': self.evidence,
            'probable_cause': self.probable_cause,
            'confidence': self.confidence,
            'recommendation': self.recommendation,
            'explanation': self.explanation,
            'evidence_strength': round(self.evidence_strength, 2),
            'category': self.category,
        }


@dataclass
class HealthScoreBreakdown:
    total_score: float = 100.0
    cpu_score: float = 100.0
    memory_score: float = 100.0
    swap_score: float = 100.0
    disk_score: float = 100.0
    factors: list[str] = field(default_factory=list)
    
    # Weights
    CPU_WEIGHT: float = 0.30
    MEMORY_WEIGHT: float = 0.30
    SWAP_WEIGHT: float = 0.15
    DISK_WEIGHT: float = 0.25

    def to_dict(self) -> dict:
        return {
            'total_score': round(self.total_score, 1),
            'cpu_score': round(self.cpu_score, 1),
            'memory_score': round(self.memory_score, 1),
            'swap_score': round(self.swap_score, 1),
            'disk_score': round(self.disk_score, 1),
            'factors': self.factors,
        }


class Thresholds:
    """Configurable thresholds for analysis."""
    def __init__(self):
        self.cpu_warning = 75.0
        self.cpu_critical = 90.0
        self.memory_warning = 80.0
        self.memory_critical = 92.0
        self.swap_warning = 50.0
        self.swap_critical = 80.0
        self.disk_warning = 85.0
        self.disk_critical = 95.0
        self.disk_io_high = 50 * 1024 * 1024  # 50 MB/s
        self.sustained_samples = 3  # number of samples to confirm sustained issue


class AnalysisEngine:
    """Rule-based root-cause analysis engine."""
    
    def __init__(self, thresholds: Optional[Thresholds] = None):
        self.thresholds = thresholds or Thresholds()
        self._history: list[SystemSnapshot] = []
        self._max_history = 60  # keep last 60 samples
    
    def add_snapshot(self, snapshot: SystemSnapshot):
        """Add a snapshot to the rolling history."""
        self._history.append(snapshot)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_recent_snapshots(self, count: int = 5) -> list[SystemSnapshot]:
        return self._history[-count:] if self._history else []
    
    def calculate_health_score(self, snapshot: SystemSnapshot) -> HealthScoreBreakdown:
        """Calculate a transparent health score from 0-100."""
        breakdown = HealthScoreBreakdown()
        
        # CPU Score (100 = idle, 0 = fully saturated)
        cpu = snapshot.cpu.overall_percent
        if cpu < 50:
            breakdown.cpu_score = 100.0
        elif cpu < self.thresholds.cpu_warning:
            breakdown.cpu_score = 100.0 - ((cpu - 50) / (self.thresholds.cpu_warning - 50)) * 30
        elif cpu < self.thresholds.cpu_critical:
            breakdown.cpu_score = 70.0 - ((cpu - self.thresholds.cpu_warning) / (self.thresholds.cpu_critical - self.thresholds.cpu_warning)) * 40
        else:
            breakdown.cpu_score = max(0, 30.0 - ((cpu - self.thresholds.cpu_critical) / (100 - self.thresholds.cpu_critical)) * 30)
        
        # Check sustained CPU pressure
        recent = self.get_recent_snapshots(self.thresholds.sustained_samples)
        if len(recent) >= self.thresholds.sustained_samples:
            avg_cpu = sum(s.cpu.overall_percent for s in recent) / len(recent)
            if avg_cpu > self.thresholds.cpu_critical:
                breakdown.cpu_score = max(0, breakdown.cpu_score - 15)
                breakdown.factors.append(f"Sustained high CPU usage ({avg_cpu:.0f}% average)")
            elif avg_cpu > self.thresholds.cpu_warning:
                breakdown.factors.append(f"Elevated CPU usage ({avg_cpu:.0f}% average)")
        
        if cpu > self.thresholds.cpu_warning:
            breakdown.factors.append(f"CPU at {cpu:.0f}%")
        
        # Memory Score
        mem = snapshot.memory.percent
        if mem < 60:
            breakdown.memory_score = 100.0
        elif mem < self.thresholds.memory_warning:
            breakdown.memory_score = 100.0 - ((mem - 60) / (self.thresholds.memory_warning - 60)) * 25
        elif mem < self.thresholds.memory_critical:
            breakdown.memory_score = 75.0 - ((mem - self.thresholds.memory_warning) / (self.thresholds.memory_critical - self.thresholds.memory_warning)) * 45
        else:
            breakdown.memory_score = max(0, 30.0 - ((mem - self.thresholds.memory_critical) / (100 - self.thresholds.memory_critical)) * 30)
        
        if mem > self.thresholds.memory_warning:
            breakdown.factors.append(f"Memory at {mem:.0f}%")
        
        # Swap Score
        swap = snapshot.memory.swap_percent
        if swap < 20:
            breakdown.swap_score = 100.0
        elif swap < self.thresholds.swap_warning:
            breakdown.swap_score = 100.0 - ((swap - 20) / (self.thresholds.swap_warning - 20)) * 30
        elif swap < self.thresholds.swap_critical:
            breakdown.swap_score = 70.0 - ((swap - self.thresholds.swap_warning) / (self.thresholds.swap_critical - self.thresholds.swap_warning)) * 40
        else:
            breakdown.swap_score = max(0, 30.0 - ((swap - self.thresholds.swap_critical) / (100 - self.thresholds.swap_critical)) * 30)
        
        if swap > self.thresholds.swap_warning:
            breakdown.factors.append(f"Page file usage at {swap:.0f}%")
        
        # Disk Score (based on capacity)
        disk = snapshot.disk.percent
        if disk < 70:
            breakdown.disk_score = 100.0
        elif disk < self.thresholds.disk_warning:
            breakdown.disk_score = 100.0 - ((disk - 70) / (self.thresholds.disk_warning - 70)) * 25
        elif disk < self.thresholds.disk_critical:
            breakdown.disk_score = 75.0 - ((disk - self.thresholds.disk_warning) / (self.thresholds.disk_critical - self.thresholds.disk_warning)) * 45
        else:
            breakdown.disk_score = max(0, 30.0 - ((disk - self.thresholds.disk_critical) / (100 - self.thresholds.disk_critical)) * 30)
        
        if disk > self.thresholds.disk_warning:
            breakdown.factors.append(f"Disk space at {disk:.0f}%")
        
        if not breakdown.factors:
            breakdown.factors.append("All systems operating normally")
        
        # Weighted total
        breakdown.total_score = (
            breakdown.cpu_score * breakdown.CPU_WEIGHT +
            breakdown.memory_score * breakdown.MEMORY_WEIGHT +
            breakdown.swap_score * breakdown.SWAP_WEIGHT +
            breakdown.disk_score * breakdown.DISK_WEIGHT
        )
        breakdown.total_score = max(0, min(100, breakdown.total_score))
        
        return breakdown
    
    def diagnose(self, snapshot: SystemSnapshot,
                 processes: Optional[list[ProcessInfo]] = None) -> list[Diagnosis]:
        """Run all diagnostic rules and return findings ranked by evidence strength."""
        diagnoses = []
        recent = self.get_recent_snapshots(self.thresholds.sustained_samples)
        
        # --- Multi-Resource Bottleneck Correlation ---
        diagnoses.extend(self._analyze_multi_bottlenecks(snapshot, recent, processes))
        # --- CPU Analysis ---
        diagnoses.extend(self._analyze_cpu(snapshot, recent, processes))
        # --- Memory Analysis ---
        diagnoses.extend(self._analyze_memory(snapshot, recent, processes))
        # --- Swap Analysis ---
        diagnoses.extend(self._analyze_swap(snapshot, recent))
        # --- Disk Analysis ---
        diagnoses.extend(self._analyze_disk(snapshot))
        # --- Disk I/O Analysis ---
        diagnoses.extend(self._analyze_disk_io(snapshot, recent))
        
        if not diagnoses:
            diagnoses.append(Diagnosis(
                title="System Healthy",
                severity=Severity.HEALTHY,
                evidence=f"CPU: {snapshot.cpu.overall_percent:.0f}%, "
                         f"Memory: {snapshot.memory.percent:.0f}%, "
                         f"Disk: {snapshot.disk.percent:.0f}%",
                probable_cause="No significant resource pressure detected.",
                confidence="High",
                recommendation="No action needed. System is operating within normal parameters.",
                explanation="All monitored resources are within acceptable thresholds.",
                evidence_strength=0.95,
                category="General"
            ))
        
        # Sort by severity priority first, then descending evidence strength
        severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2, Severity.HEALTHY: 3}
        diagnoses.sort(key=lambda d: (severity_order.get(d.severity, 4), -d.evidence_strength))
        
        return diagnoses

    def _analyze_multi_bottlenecks(self, snap: SystemSnapshot, recent: list[SystemSnapshot],
                                   processes: Optional[list[ProcessInfo]]) -> list[Diagnosis]:
        results = []
        cpu = snap.cpu.overall_percent
        mem = snap.memory.percent
        swap = snap.memory.swap_percent
        disk_io_mb = (snap.disk.read_bytes_per_sec + snap.disk.write_bytes_per_sec) / (1024 * 1024)
        
        # 1. Virtual Memory Thrashing (High RAM + High Swap)
        if mem > 82.0 and swap > 45.0:
            results.append(Diagnosis(
                title="Virtual Memory Thrashing",
                severity=Severity.CRITICAL,
                evidence=f"Physical RAM is {mem:.1f}% occupied while Page File utilization has reached {swap:.1f}%.",
                probable_cause="The working set of active processes exceeds physical RAM capacity. The kernel is constantly swapping memory pages to/from disk.",
                confidence="High",
                recommendation="Close heavy memory consumers immediately. Prolonged thrashing severely degrades UI and disk responsiveness.",
                explanation="Memory thrashing occurs when the system spends more time paging memory between disk and RAM than executing code.",
                evidence_strength=0.98,
                category="Multi-Bottleneck"
            ))

        # 2. Compute + Disk I/O Saturation (Compilation, export, or intensive batch processing)
        if cpu > 70.0 and disk_io_mb > 35.0:
            results.append(Diagnosis(
                title="Concurrent Compute & Disk I/O Saturation",
                severity=Severity.WARNING if cpu < 90.0 else Severity.CRITICAL,
                evidence=f"CPU is at {cpu:.1f}% with simultaneous high disk throughput ({disk_io_mb:.1f} MB/s).",
                probable_cause="A heavy workload is simultaneously demanding compute cycles and disk bandwidth (e.g. software build, database indexing, or media rendering).",
                confidence="High",
                recommendation="Allow ongoing batch processing to finish, or defer concurrent disk scans if interactive responsiveness is impaired.",
                explanation="Concurrent saturation of both processor and storage bus leaves little headroom for foreground interactive tasks.",
                evidence_strength=0.92,
                category="Multi-Bottleneck"
            ))
            
        return results
    
    def _analyze_cpu(self, snap: SystemSnapshot, recent: list[SystemSnapshot],
                     processes: Optional[list[ProcessInfo]]) -> list[Diagnosis]:
        results = []
        cpu = snap.cpu.overall_percent
        
        if cpu < self.thresholds.cpu_warning:
            return results
        
        # Check if sustained
        sustained = False
        if len(recent) >= self.thresholds.sustained_samples:
            avg = sum(s.cpu.overall_percent for s in recent) / len(recent)
            sustained = avg > self.thresholds.cpu_warning
        
        severity = Severity.CRITICAL if cpu >= self.thresholds.cpu_critical else Severity.WARNING
        confidence = "High" if sustained else "Medium"
        
        evidence = f"CPU utilization is at {cpu:.1f}%."
        if sustained:
            evidence += f" Average over last {len(recent)} samples: {avg:.1f}%."
        
        top_procs = ""
        if processes:
            top_cpu = sorted(processes, key=lambda p: p.cpu_percent, reverse=True)[:5]
            top_procs = ", ".join(f"{p.name} ({p.cpu_percent:.1f}%)" for p in top_cpu if p.cpu_percent > 1)
            if top_procs:
                evidence += f" Top consumers: {top_procs}."
        
        probable_cause = "One or more processes are consuming significant CPU resources."
        if sustained:
            probable_cause = "Sustained high CPU utilization suggests a compute-intensive workload or a runaway process."
        
        recommendation = "Review the top CPU-consuming processes. "
        if processes:
            heavy = [p for p in processes if p.cpu_percent > 30]
            if heavy:
                recommendation += f"Consider whether {heavy[0].name} needs to be running at this intensity."
        recommendation += " Close unnecessary applications if performance is degraded."
        
        results.append(Diagnosis(
            title="High CPU Utilization" if not sustained else "Sustained High CPU Utilization",
            severity=severity,
            evidence=evidence,
            probable_cause=probable_cause,
            confidence=confidence,
            recommendation=recommendation,
            explanation="High CPU usage means the processor is heavily loaded. "
                       "This can cause application slowdowns and system unresponsiveness. "
                       "Identifying the responsible processes helps determine if the load is expected.",
        ))
        return results
    
    def _analyze_memory(self, snap: SystemSnapshot, recent: list[SystemSnapshot],
                        processes: Optional[list[ProcessInfo]]) -> list[Diagnosis]:
        results = []
        mem = snap.memory.percent
        avail_gb = snap.memory.available / (1024**3)
        
        if mem < self.thresholds.memory_warning:
            return results
        
        sustained = False
        if len(recent) >= self.thresholds.sustained_samples:
            avg = sum(s.memory.percent for s in recent) / len(recent)
            sustained = avg > self.thresholds.memory_warning
        
        severity = Severity.CRITICAL if mem >= self.thresholds.memory_critical else Severity.WARNING
        confidence = "High" if sustained else "Medium"
        
        evidence = f"Memory utilization at {mem:.1f}%. Available: {avail_gb:.2f} GB."
        
        if processes:
            top_mem = sorted(processes, key=lambda p: p.memory_percent, reverse=True)[:5]
            top_str = ", ".join(f"{p.name} ({p.memory_mb:.0f} MB)" for p in top_mem if p.memory_mb > 50)
            if top_str:
                evidence += f" Top consumers: {top_str}."
        
        probable_cause = "Applications are consuming a large portion of available memory."
        if snap.memory.swap_percent > self.thresholds.swap_warning:
            probable_cause += " The system is also using significant page file space, which indicates memory pressure."
        
        recommendation = ("Close unused applications to free memory. "
                         "Check if any single application is using an unexpectedly large amount of memory.")
        
        results.append(Diagnosis(
            title="High Memory Utilization",
            severity=severity,
            evidence=evidence,
            probable_cause=probable_cause,
            confidence=confidence,
            recommendation=recommendation,
            explanation=("When memory usage is high and available memory is low, the system relies on "
                        "the page file (disk-based virtual memory), which is much slower than RAM. "
                        "This can cause noticeable performance degradation."),
        ))
        return results
    
    def _analyze_swap(self, snap: SystemSnapshot, recent: list[SystemSnapshot]) -> list[Diagnosis]:
        results = []
        swap = snap.memory.swap_percent
        
        if swap < self.thresholds.swap_warning or snap.memory.swap_total == 0:
            return results
        
        severity = Severity.CRITICAL if swap >= self.thresholds.swap_critical else Severity.WARNING
        swap_used_gb = snap.memory.swap_used / (1024**3)
        swap_total_gb = snap.memory.swap_total / (1024**3)
        
        results.append(Diagnosis(
            title="High Page File Usage",
            severity=severity,
            evidence=f"Page file usage at {swap:.1f}% ({swap_used_gb:.1f} / {swap_total_gb:.1f} GB).",
            probable_cause="The system has exceeded physical memory capacity and is relying heavily on disk-based virtual memory.",
            confidence="High",
            recommendation=("Close memory-intensive applications. Consider adding more physical RAM "
                          "if this occurs frequently. Review applications for memory leaks."),
            explanation=("Page file (swap) usage indicates the system doesn't have enough physical RAM "
                        "for the current workload. Data is moved to disk-based virtual memory, which is significantly slower."),
        ))
        return results
    
    def _analyze_disk(self, snap: SystemSnapshot) -> list[Diagnosis]:
        results = []
        
        for partition in snap.disk.partitions:
            pct = partition.get('percent', 0)
            if pct < self.thresholds.disk_warning:
                continue
            
            severity = Severity.CRITICAL if pct >= self.thresholds.disk_critical else Severity.WARNING
            free_gb = partition.get('free', 0) / (1024**3)
            
            results.append(Diagnosis(
                title=f"Low Disk Space on {partition.get('mountpoint', 'Unknown')}",
                severity=severity,
                evidence=f"Drive {partition.get('mountpoint', '?')} is {pct:.1f}% full. "
                        f"Only {free_gb:.1f} GB free.",
                probable_cause="The drive is running out of available storage space.",
                confidence="High",
                recommendation=(f"Free up space on {partition.get('mountpoint', 'the drive')}. "
                              "Review large files, temporary files, and unused applications. "
                              "Use Disk Cleanup or Storage Sense to reclaim space."),
                explanation=("Low disk space can cause system instability, prevent updates, "
                            "and degrade performance if the drive is used for virtual memory."),
            ))
        return results
    
    def _analyze_disk_io(self, snap: SystemSnapshot, recent: list[SystemSnapshot]) -> list[Diagnosis]:
        results = []
        total_io = snap.disk.read_bytes_per_sec + snap.disk.write_bytes_per_sec
        
        if total_io < self.thresholds.disk_io_high:
            return results
        
        sustained = False
        if len(recent) >= self.thresholds.sustained_samples:
            avg_io = sum(
                s.disk.read_bytes_per_sec + s.disk.write_bytes_per_sec
                for s in recent
            ) / len(recent)
            sustained = avg_io > self.thresholds.disk_io_high
        
        io_mb = total_io / (1024 * 1024)
        confidence = "High" if sustained else "Medium"
        
        results.append(Diagnosis(
            title="High Disk Activity",
            severity=Severity.WARNING,
            evidence=f"Disk I/O throughput is {io_mb:.1f} MB/s "
                    f"(Read: {snap.disk.read_bytes_per_sec/(1024*1024):.1f} MB/s, "
                    f"Write: {snap.disk.write_bytes_per_sec/(1024*1024):.1f} MB/s).",
            probable_cause=("Heavy disk activity may be caused by file transfers, system updates, "
                          "antivirus scanning, or applications performing intensive I/O."),
            confidence=confidence,
            recommendation=("If the system feels slow, check which processes are performing heavy disk I/O. "
                          "Consider deferring large file operations or scans."),
            explanation=("High disk activity can cause the system to feel sluggish, especially on HDDs. "
                        "This is distinct from low disk space — even drives with plenty of free space "
                        "can become a bottleneck under heavy I/O load."),
        ))
        return results
    
    def run_full_diagnosis(self, snapshot: SystemSnapshot,
                           processes: Optional[list[ProcessInfo]] = None) -> dict:
        """Run a complete diagnosis including health score. Returns a full report."""
        self.add_snapshot(snapshot)
        health = self.calculate_health_score(snapshot)
        diagnoses = self.diagnose(snapshot, processes)
        
        # Sort by severity
        severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, 
                         Severity.INFO: 2, Severity.HEALTHY: 3}
        diagnoses.sort(key=lambda d: severity_order.get(d.severity, 4))
        
        return {
            'timestamp': snapshot.timestamp,
            'health_score': health.to_dict(),
            'diagnoses': [d.to_dict() for d in diagnoses],
            'snapshot_summary': {
                'cpu_percent': snapshot.cpu.overall_percent,
                'memory_percent': snapshot.memory.percent,
                'swap_percent': snapshot.memory.swap_percent,
                'disk_percent': snapshot.disk.percent,
                'process_count': snapshot.process_count,
                'uptime_hours': snapshot.uptime_seconds / 3600,
            },
        }
