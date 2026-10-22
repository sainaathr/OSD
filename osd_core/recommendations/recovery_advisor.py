"""
Cross-Platform Recovery Advisor — 6-Step Autonomous Recovery Lifecycle:
Detect -> Investigate -> Recommend -> Obtain Consent -> Execute -> Verify.
Logs before-and-after telemetry differentials to SQLite for auditability.
Platform-aware: respects OS kernel protection and feature availability.
"""
import time
import psutil
from typing import Optional, Callable, Any
from osd_core.models.metrics import SystemSnapshot, ProcessInfo
from osd_core.models.diagnostics import Diagnosis, Severity
from osd_core.models.recovery import RecoveryPlan, RecoveryVerification
from osd_core.platform_support.base import PlatformAdapter
from osd_core.platform_support.factory import get_platform_adapter


class RecoveryAdvisor:
    """Manages the 6-step recovery workflow with automated outcome verification."""

    def __init__(self, monitor: Any, analysis: Optional[Any] = None,
                 db: Optional[Any] = None, platform_adapter: Optional[PlatformAdapter] = None):
        self.monitor = monitor
        self.analysis = analysis
        self.db = db
        self.adapter = platform_adapter or (getattr(monitor, 'adapter', None) or get_platform_adapter())

    def generate_plans(self, diagnoses: list[Diagnosis], snapshot: SystemSnapshot,
                       processes: list[ProcessInfo]) -> list[RecoveryPlan]:
        """Convert detected issues into structured recovery plans respecting platform capabilities."""
        plans: list[RecoveryPlan] = []
        health_score = 100.0
        if self.analysis is not None:
            health_score = self.analysis.calculate_health_score(snapshot).total_score

        can_trim = self.adapter.can_trim_working_set()

        for diag in diagnoses:
            if diag.severity == Severity.HEALTHY:
                continue

            # Heavy CPU consumer recovery plans
            if "CPU" in diag.title:
                heavy_cpu = [p for p in processes if p.cpu_percent > 25.0]
                for p in heavy_cpu[:2]:
                    # Plan A: Lower Priority (Low Risk)
                    plans.append(RecoveryPlan(
                        plan_id=f"prio_{p.pid}_{int(time.time())}",
                        issue_title=f"CPU Contention from {p.name}",
                        action_type="lower_priority",
                        target_process=p.name,
                        target_pid=p.pid,
                        proposed_fix=f"Lower {p.name} CPU priority to 'Below Normal'.",
                        expected_benefit="Instantly yields CPU time to foreground interactive tasks without terminating the app.",
                        risk_level="Low",
                        evidence=f"Using {p.cpu_percent:.1f}% CPU under system load.",
                        probable_cause="Compute-heavy application competing for processor cycles.",
                        baseline_cpu=snapshot.cpu.overall_percent,
                        baseline_mem_mb=p.memory_mb,
                        baseline_health=health_score,
                    ))

                    # Plan B: Graceful Termination (Medium Risk) - Never for protected OS processes
                    if not self.adapter.is_protected_process(p.name):
                        plans.append(RecoveryPlan(
                            plan_id=f"term_{p.pid}_{int(time.time())}",
                            issue_title=f"High CPU Drain by {p.name}",
                            action_type="terminate",
                            target_process=p.name,
                            target_pid=p.pid,
                            proposed_fix=f"Terminate process {p.name} (PID {p.pid}).",
                            expected_benefit=f"Completely recovers ~{p.cpu_percent:.1f}% CPU load.",
                            risk_level="Medium",
                            evidence=f"Consuming {p.cpu_percent:.1f}% CPU continuously.",
                            probable_cause="Runaway task, background loop, or high-intensity worker.",
                            baseline_cpu=snapshot.cpu.overall_percent,
                            baseline_mem_mb=p.memory_mb,
                            baseline_health=health_score,
                        ))

            # Memory pressure recovery plans
            if "Memory" in diag.title or "Thrashing" in diag.title:
                heavy_mem = sorted([p for p in processes if p.memory_mb > 350.0], key=lambda x: x.memory_mb, reverse=True)
                for p in heavy_mem[:2]:
                    # Plan A: Working set trim (only on platforms that support it, e.g. Windows PSAPI)
                    if can_trim:
                        plans.append(RecoveryPlan(
                            plan_id=f"trim_{p.pid}_{int(time.time())}",
                            issue_title=f"Memory Pressure from {p.name}",
                            action_type="trim_memory",
                            target_process=p.name,
                            target_pid=p.pid,
                            proposed_fix=f"Request OS working set trim for {p.name}.",
                            expected_benefit="Flushes unreferenced memory pages from RAM back to virtual memory safely.",
                            risk_level="Low",
                            evidence=f"Occupying {p.memory_mb:.0f} MB of physical RAM.",
                            probable_cause="Accumulated working set memory pages.",
                            baseline_cpu=snapshot.cpu.overall_percent,
                            baseline_mem_mb=p.memory_mb,
                            baseline_health=health_score,
                        ))
                    else:
                        # On platforms without working set trim, offer priority reduction as low-risk alternative
                        plans.append(RecoveryPlan(
                            plan_id=f"prio_mem_{p.pid}_{int(time.time())}",
                            issue_title=f"Memory Pressure from {p.name}",
                            action_type="lower_priority",
                            target_process=p.name,
                            target_pid=p.pid,
                            proposed_fix=f"Lower scheduling priority for {p.name}.",
                            expected_benefit="Limits CPU cycles for background memory-heavy application.",
                            risk_level="Low",
                            evidence=f"Occupying {p.memory_mb:.0f} MB of physical RAM.",
                            probable_cause="Heavy background memory allocation.",
                            baseline_cpu=snapshot.cpu.overall_percent,
                            baseline_mem_mb=p.memory_mb,
                            baseline_health=health_score,
                        ))

                    # Plan B: Close application - Never for protected OS processes
                    if not self.adapter.is_protected_process(p.name):
                        plans.append(RecoveryPlan(
                            plan_id=f"close_{p.pid}_{int(time.time())}",
                            issue_title=f"Large RAM Consumption by {p.name}",
                            action_type="terminate",
                            target_process=p.name,
                            target_pid=p.pid,
                            proposed_fix=f"Close application {p.name} (PID {p.pid}).",
                            expected_benefit=f"Reclaims approximately {p.memory_mb:.0f} MB of RAM.",
                            risk_level="Medium",
                            evidence=f"Using {p.memory_mb:.0f} MB ({p.memory_percent:.1f}% of total RAM).",
                            probable_cause="Memory-intensive process or memory leak.",
                            baseline_cpu=snapshot.cpu.overall_percent,
                            baseline_mem_mb=p.memory_mb,
                            baseline_health=health_score,
                        ))

        return plans

    def execute_and_verify(self, plan: RecoveryPlan,
                           sleep_fn: Optional[Callable[[float], None]] = None) -> RecoveryVerification:
        """
        Execute an approved recovery action and verify the outcome
        by sampling differential telemetry before and after execution.
        """
        if sleep_fn is None:
            sleep_fn = time.sleep

        # Step 4: Validate process identity before taking action
        if plan.target_pid > 0 and plan.target_process:
            try:
                proc = psutil.Process(plan.target_pid)
                if self.adapter.normalize_process_name(proc.name()) != self.adapter.normalize_process_name(plan.target_process):
                    return RecoveryVerification(
                        success=False,
                        message=f"PID {plan.target_pid} identity mismatch: Expected '{plan.target_process}', found '{proc.name()}'. Action aborted for safety.",
                        before_cpu=plan.baseline_cpu, after_cpu=plan.baseline_cpu,
                        before_mem_mb=plan.baseline_mem_mb, after_mem_mb=plan.baseline_mem_mb,
                        before_health=plan.baseline_health, after_health=plan.baseline_health,
                        freed_memory_mb=0.0, cpu_drop=0.0, health_gain=0.0
                    )
            except psutil.NoSuchProcess:
                return RecoveryVerification(
                    success=False,
                    message=f"Process {plan.target_process} (PID {plan.target_pid}) is no longer active.",
                    before_cpu=plan.baseline_cpu, after_cpu=plan.baseline_cpu,
                    before_mem_mb=plan.baseline_mem_mb, after_mem_mb=plan.baseline_mem_mb,
                    before_health=plan.baseline_health, after_health=plan.baseline_health,
                    freed_memory_mb=0.0, cpu_drop=0.0, health_gain=0.0
                )

        # Baseline measurements
        before_snap = self.monitor.collect_snapshot()
        before_cpu = before_snap.cpu.overall_percent
        before_mem_mb = plan.baseline_mem_mb
        before_health = plan.baseline_health
        if self.analysis is not None:
            before_health = self.analysis.calculate_health_score(before_snap).total_score

        # Step 5: Execute Approved Action
        action_success = False
        action_msg = ""

        if plan.action_type in ("terminate", "terminate_process"):
            action_success, action_msg = self.monitor.terminate_process(plan.target_pid, plan.target_process)
        elif plan.action_type in ("lower_priority", "adjust_priority"):
            action_success, action_msg = self.monitor.adjust_process_priority(plan.target_pid, "below_normal")
        elif plan.action_type in ("trim_memory", "trim_working_set"):
            action_success, action_msg = self.monitor.trim_working_set(plan.target_pid)
        else:
            action_success = False
            action_msg = f"Unknown action type: {plan.action_type}"

        if not action_success:
            return RecoveryVerification(
                success=False, message=action_msg,
                before_cpu=before_cpu, after_cpu=before_cpu,
                before_mem_mb=before_mem_mb, after_mem_mb=before_mem_mb,
                before_health=before_health, after_health=before_health,
                freed_memory_mb=0.0, cpu_drop=0.0, health_gain=0.0
            )

        # Allow OS to flush state & settle
        sleep_fn(1.5)

        # Step 6: Verify Result (Sample After)
        after_snap = self.monitor.collect_snapshot()
        after_cpu = after_snap.cpu.overall_percent
        after_health = before_health
        if self.analysis is not None:
            after_health = self.analysis.calculate_health_score(after_snap).total_score

        after_mem_mb = 0.0
        try:
            p_after = psutil.Process(plan.target_pid)
            after_mem_mb = p_after.memory_info().rss / (1024 * 1024)
        except Exception:
            after_mem_mb = 0.0  # Process terminated or closed

        freed_mem = max(0.0, before_mem_mb - after_mem_mb)
        cpu_drop = max(0.0, before_cpu - after_cpu)
        health_gain = after_health - before_health

        # Log verified outcome to database if present
        if self.db is not None and hasattr(self.db, 'save_recovery_action'):
            try:
                self.db.save_recovery_action(
                    timestamp=time.time(),
                    action_name=plan.action_type,
                    target_process=plan.target_process,
                    target_pid=plan.target_pid,
                    risk_level=plan.risk_level,
                    before_cpu=before_cpu,
                    before_memory_mb=before_mem_mb,
                    before_health=before_health,
                    after_cpu=after_cpu,
                    after_memory_mb=after_mem_mb,
                    after_health=after_health,
                    freed_memory_mb=freed_mem,
                    cpu_drop=cpu_drop,
                    health_gain=health_gain,
                    verified=1,
                    notes=f"Verified: Freed {freed_mem:.1f} MB, CPU drop {cpu_drop:.1f}%"
                )
            except Exception:
                pass

        return RecoveryVerification(
            success=True,
            message=f"{action_msg}\nVerified Outcome: Freed {freed_mem:.0f} MB RAM, CPU dropped by {cpu_drop:.1f}%, Health score changed from {before_health:.0f} to {after_health:.0f}.",
            before_cpu=before_cpu,
            after_cpu=after_cpu,
            before_mem_mb=before_mem_mb,
            after_mem_mb=after_mem_mb,
            before_health=before_health,
            after_health=after_health,
            freed_memory_mb=freed_mem,
            cpu_drop=cpu_drop,
            health_gain=health_gain
        )

    execute_approved_action = execute_and_verify
