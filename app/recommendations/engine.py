"""
Recommendation Engine — Converts diagnoses into actionable recommendations.
"""
from dataclasses import dataclass, field
from typing import Optional
from app.analysis.engine import Diagnosis, Severity
from app.monitoring.system_monitor import SystemSnapshot, ProcessInfo


@dataclass
class Recommendation:
    problem: str = ""
    evidence: str = ""
    action: str = ""
    benefit: str = ""
    risk_level: str = "Low"  # Low, Medium, High
    action_type: str = "inspect"  # inspect, close_app, cleanup, info
    target_process: Optional[str] = None
    target_pid: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'problem': self.problem,
            'evidence': self.evidence,
            'action': self.action,
            'benefit': self.benefit,
            'risk_level': self.risk_level,
            'action_type': self.action_type,
            'target_process': self.target_process,
            'target_pid': self.target_pid,
        }


class RecommendationEngine:
    """Generates safe, practical recommendations from diagnoses."""
    
    def generate(self, diagnoses: list[Diagnosis],
                 snapshot: SystemSnapshot,
                 processes: Optional[list[ProcessInfo]] = None) -> list[Recommendation]:
        """Generate recommendations based on diagnoses and current state."""
        recommendations = []
        
        for diag in diagnoses:
            if diag.severity == Severity.HEALTHY:
                continue
            
            if "CPU" in diag.title:
                recommendations.extend(self._cpu_recommendations(diag, snapshot, processes))
            elif "Memory" in diag.title and "Page" not in diag.title:
                recommendations.extend(self._memory_recommendations(diag, snapshot, processes))
            elif "Page File" in diag.title or "Swap" in diag.title:
                recommendations.extend(self._swap_recommendations(diag, snapshot, processes))
            elif "Disk Space" in diag.title:
                recommendations.extend(self._disk_space_recommendations(diag, snapshot))
            elif "Disk Activity" in diag.title:
                recommendations.extend(self._disk_io_recommendations(diag, snapshot))
        
        # Deduplicate
        seen = set()
        unique = []
        for r in recommendations:
            key = (r.problem, r.action)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        return unique
    
    def _cpu_recommendations(self, diag: Diagnosis, snap: SystemSnapshot,
                             processes: Optional[list[ProcessInfo]]) -> list[Recommendation]:
        recs = []
        
        if processes:
            heavy = [p for p in processes if p.cpu_percent > 25]
            for proc in heavy[:3]:
                recs.append(Recommendation(
                    problem=f"{proc.name} is consuming {proc.cpu_percent:.1f}% CPU",
                    evidence=f"Process '{proc.name}' (PID {proc.pid}) is using significant CPU resources.",
                    action=f"Review if {proc.name} needs to continue running. If not needed, consider closing it.",
                    benefit="May reduce CPU load and improve system responsiveness.",
                    risk_level="Medium",
                    action_type="close_app",
                    target_process=proc.name,
                    target_pid=proc.pid,
                ))
        
        recs.append(Recommendation(
            problem="High CPU utilization detected",
            evidence=diag.evidence,
            action="Close unnecessary applications and browser tabs to free CPU resources.",
            benefit="Reduces CPU contention and may improve responsiveness.",
            risk_level="Low",
            action_type="info",
        ))
        
        return recs
    
    def _memory_recommendations(self, diag: Diagnosis, snap: SystemSnapshot,
                                processes: Optional[list[ProcessInfo]]) -> list[Recommendation]:
        recs = []
        
        if processes:
            heavy = sorted(processes, key=lambda p: p.memory_mb, reverse=True)
            heavy = [p for p in heavy[:5] if p.memory_mb > 200]
            for proc in heavy[:3]:
                recs.append(Recommendation(
                    problem=f"{proc.name} is using {proc.memory_mb:.0f} MB of memory",
                    evidence=f"Process '{proc.name}' (PID {proc.pid}) occupies significant RAM.",
                    action=f"If not actively needed, closing {proc.name} would free approximately {proc.memory_mb:.0f} MB.",
                    benefit=f"Could free up to {proc.memory_mb:.0f} MB of RAM.",
                    risk_level="Medium",
                    action_type="close_app",
                    target_process=proc.name,
                    target_pid=proc.pid,
                ))
        
        avail_gb = snap.memory.available / (1024**3)
        recs.append(Recommendation(
            problem="System memory is running low",
            evidence=f"Only {avail_gb:.1f} GB of RAM is available ({snap.memory.percent:.0f}% used).",
            action="Close unused applications, browser tabs, and background programs to free memory.",
            benefit="Improves system responsiveness and reduces page file reliance.",
            risk_level="Low",
            action_type="info",
        ))
        
        return recs
    
    def _swap_recommendations(self, diag: Diagnosis, snap: SystemSnapshot,
                              processes: Optional[list[ProcessInfo]]) -> list[Recommendation]:
        recs = []
        
        recs.append(Recommendation(
            problem="System relying heavily on page file",
            evidence=diag.evidence,
            action="Free up RAM by closing unused applications. If this happens frequently, consider adding more physical memory.",
            benefit="Reduces slow disk-based virtual memory access, improving performance.",
            risk_level="Low",
            action_type="info",
        ))
        
        if processes:
            heavy = sorted(processes, key=lambda p: p.memory_mb, reverse=True)[:3]
            for proc in heavy:
                if proc.memory_mb > 500:
                    recs.append(Recommendation(
                        problem=f"{proc.name} may be contributing to memory pressure",
                        evidence=f"Using {proc.memory_mb:.0f} MB while page file is heavily utilized.",
                        action=f"Review if {proc.name} needs to be running or can reduce its memory footprint.",
                        benefit="May reduce page file dependency.",
                        risk_level="Medium",
                        action_type="inspect",
                        target_process=proc.name,
                        target_pid=proc.pid,
                    ))
        
        return recs
    
    def _disk_space_recommendations(self, diag: Diagnosis, snap: SystemSnapshot) -> list[Recommendation]:
        recs = []
        
        recs.append(Recommendation(
            problem="Disk space is running low",
            evidence=diag.evidence,
            action=("Use Windows Disk Cleanup or Storage Sense to remove temporary files. "
                   "Review Downloads folder and Recycle Bin for files you no longer need."),
            benefit="Frees disk space and may improve system stability.",
            risk_level="Low",
            action_type="info",
        ))
        
        recs.append(Recommendation(
            problem="Potential large file accumulation",
            evidence=diag.evidence,
            action="Check for large files in Downloads, Videos, and Temp folders. Review installed applications for any no longer needed.",
            benefit="Can recover significant disk space without affecting system stability.",
            risk_level="Low",
            action_type="inspect",
        ))
        
        return recs
    
    def _disk_io_recommendations(self, diag: Diagnosis, snap: SystemSnapshot) -> list[Recommendation]:
        recs = []
        
        recs.append(Recommendation(
            problem="Heavy disk I/O detected",
            evidence=diag.evidence,
            action=("Check for background processes performing file operations (updates, antivirus scans, backups). "
                   "Consider deferring large transfers if the system feels slow."),
            benefit="Reducing concurrent disk operations may improve responsiveness.",
            risk_level="Low",
            action_type="info",
        ))
        
        return recs
