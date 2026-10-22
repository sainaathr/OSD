"""
Recommendation Engine for OSD.
Converts diagnostic findings into actionable recommendations with clear risk levels.
"""
from dataclasses import dataclass
from typing import Optional, Any
from osd_core.models.diagnostics import Diagnosis, Severity
from osd_core.models.metrics import SystemSnapshot, ProcessInfo


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
    
    def to_dict(self) -> dict[str, Any]:
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
            elif "Disk Space" in diag.title or "Low Disk" in diag.title:
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
            heavy = [p for p in processes if p.memory_percent > 10 or p.memory_mb > 500]
            for proc in heavy[:3]:
                recs.append(Recommendation(
                    problem=f"{proc.name} is using {proc.memory_mb:.0f} MB RAM",
                    evidence=f"Process '{proc.name}' (PID {proc.pid}) holds {proc.memory_percent:.1f}% of memory.",
                    action=f"Save work in {proc.name} and restart the application if it has been running for a long time.",
                    benefit=f"May reclaim up to {proc.memory_mb:.0f} MB of RAM if the application has accumulated memory.",
                    risk_level="Medium",
                    action_type="close_app",
                    target_process=proc.name,
                    target_pid=proc.pid,
                ))
        
        recs.append(Recommendation(
            problem="High memory pressure",
            evidence=diag.evidence,
            action="Close unused background applications and browser windows.",
            benefit="Reclaims physical RAM and reduces dependence on slower virtual memory.",
            risk_level="Low",
            action_type="info",
        ))
        return recs
    
    def _swap_recommendations(self, diag: Diagnosis, snap: SystemSnapshot,
                              processes: Optional[list[ProcessInfo]]) -> list[Recommendation]:
        return [
            Recommendation(
                problem="High virtual memory (page file) usage",
                evidence=diag.evidence,
                action="Close memory-heavy applications to bring active workload within physical RAM limits.",
                benefit="Reduces disk paging activity, which significantly improves system responsiveness.",
                risk_level="Low",
                action_type="info",
            ),
            Recommendation(
                problem="Frequent virtual memory pressure",
                evidence=diag.evidence,
                action="If this occurs regularly during normal tasks, consider upgrading physical RAM.",
                benefit="Prevents the system from needing to page memory to disk.",
                risk_level="Low",
                action_type="info",
            ),
        ]
    
    def _disk_space_recommendations(self, diag: Diagnosis, snap: SystemSnapshot) -> list[Recommendation]:
        return [
            Recommendation(
                problem=diag.title,
                evidence=diag.evidence,
                action="Run standard system disk cleanup utility or remove unused temporary files.",
                benefit="Frees up disk space to prevent system instability.",
                risk_level="Low",
                action_type="cleanup",
            ),
            Recommendation(
                problem=diag.title,
                evidence=diag.evidence,
                action="Review Downloads, Videos, and large applications that can be archived or uninstalled.",
                benefit="Reclaims permanent storage headroom.",
                risk_level="Low",
                action_type="inspect",
            ),
        ]
    
    def _disk_io_recommendations(self, diag: Diagnosis, snap: SystemSnapshot) -> list[Recommendation]:
        return [
            Recommendation(
                problem="Heavy disk activity detected",
                evidence=diag.evidence,
                action="Allow active file operations, scans, or updates to complete before launching heavy apps.",
                benefit="Reduces disk queue length and improves foreground task responsiveness.",
                risk_level="Low",
                action_type="info",
            ),
        ]
