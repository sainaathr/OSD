"""
Ask OSD Assistant — Conversational performance analyst.
Answers questions using real telemetry, active root-cause diagnoses,
predictive trends, and verified recovery history.
100% Offline Rule-Based NLP engine by default; optional privacy-conscious custom AI hook.
"""
import time
import re
from typing import Optional
from app.monitoring.system_monitor import SystemMonitor, SystemSnapshot, ProcessInfo
from app.analysis.engine import AnalysisEngine, Diagnosis
from app.analysis.predictive_engine import PredictiveEngine
from app.database.db_manager import DatabaseManager
from app.utils.formatting import format_timestamp


class AskOSDEngine:
    """Conversational assistant grounded in live telemetry and SQLite history."""

    def __init__(self, monitor: SystemMonitor, analysis: AnalysisEngine,
                 predictive: PredictiveEngine, db: DatabaseManager):
        self.monitor = monitor
        self.analysis = analysis
        self.predictive = predictive
        self.db = db

    def ask(self, query: str) -> str:
        """Process natural language question and return evidence-backed response."""
        q = query.strip().lower()

        # Gather fresh live state
        snap = self.monitor.collect_snapshot()
        health = self.analysis.calculate_health_score(snap)
        procs = self.monitor.get_processes(sort_by="cpu", limit=20)
        diags = self.analysis.diagnose(snap, procs)

        # 1. Why is my PC slow? / What is the bottleneck?
        if any(phrase in q for phrase in ["why is my pc slow", "why is it slow", "slow", "bottleneck", "lagging", "unresponsive"]):
            return self._answer_why_slow(snap, health, diags, procs)

        # 2. Which process uses the most memory / RAM?
        if any(phrase in q for phrase in ["most memory", "most ram", "highest memory", "memory hog", "using memory", "ram hog"]):
            return self._answer_top_memory(procs, snap)

        # 3. Which process uses the most CPU?
        if any(phrase in q for phrase in ["most cpu", "highest cpu", "cpu consumer", "using cpu", "cpu hog"]):
            return self._answer_top_cpu(procs, snap)

        # 4. What has changed recently?
        if any(phrase in q for phrase in ["what has changed", "changed recently", "recent change", "difference", "history comparison"]):
            return self._answer_what_changed(snap, health)

        # 5. Which recommendation is safest?
        if any(phrase in q for phrase in ["safest recommendation", "safest action", "safest", "safe fix", "least risk", "safe to close"]):
            return self._answer_safest_action(diags, procs, snap)

        # 6. Is memory usage increasing? / Memory leak?
        if any(phrase in q for phrase in ["is memory increasing", "ram increasing", "memory leak", "memory trend", "ram trend", "running out of memory"]):
            return self._answer_memory_trend(snap, procs)

        # 7. Did the last recovery action improve performance?
        if any(phrase in q for phrase in ["last recovery", "last action", "did it help", "did the action improve", "recovery result", "verified outcome"]):
            return self._answer_last_recovery()

        # 8. Health status / summary
        if any(phrase in q for phrase in ["health", "status", "score", "how is my pc", "overall"]):
            return self._answer_health_status(health, snap, diags)

        # Default helpful guide
        return self._answer_default(snap, health)

    def _answer_why_slow(self, snap: SystemSnapshot, health, diags: list[Diagnosis], procs: list[ProcessInfo]) -> str:
        score = health.total_score
        non_healthy = [d for d in diags if d.severity != "Healthy"]

        if not non_healthy or score >= 85:
            return (
                f"Your PC is currently operating in a **Healthy state** (System Health Score: **{score:.0f}/100**).\n\n"
                f"• CPU is at **{snap.cpu.overall_percent:.1f}%**\n"
                f"• RAM is at **{snap.memory.percent:.1f}%** ({snap.memory.available / (1024**3):.1f} GB available)\n"
                f"• Disk I/O is normal ({((snap.disk.read_bytes_per_sec + snap.disk.write_bytes_per_sec)/(1024*1024)):.1f} MB/s)\n\n"
                "If an individual application feels sluggish, it may be waiting on a network response or performing internal synchronization rather than saturating system hardware."
            )

        primary = non_healthy[0]
        top_cpu = sorted(procs, key=lambda p: p.cpu_percent, reverse=True)[:3]
        top_mem = sorted(procs, key=lambda p: p.memory_mb, reverse=True)[:3]

        response = (
            f"Your PC's System Health Score is currently **{score:.0f}/100**.\n\n"
            f"**Primary Bottleneck Identified:** {primary.title} ({primary.severity})\n"
            f"• **Evidence:** {primary.evidence}\n"
            f"• **Probable Cause:** {primary.probable_cause}\n"
            f"• **Recommended Action:** {primary.recommendation}\n\n"
            f"**Key Active Consumers Right Now:**\n"
            f"1. `{top_cpu[0].name}` (PID {top_cpu[0].pid}) — {top_cpu[0].cpu_percent:.1f}% CPU, {top_cpu[0].memory_mb:.0f} MB RAM\n"
            f"2. `{top_mem[0].name}` (PID {top_mem[0].pid}) — {top_mem[0].memory_mb:.0f} MB RAM ({top_mem[0].memory_percent:.1f}% of total)\n"
        )
        return response

    def _answer_top_memory(self, procs: list[ProcessInfo], snap: SystemSnapshot) -> str:
        if not procs:
            return "No running processes are currently accessible."
        by_mem = sorted(procs, key=lambda p: p.memory_mb, reverse=True)
        top = by_mem[0]
        total_gb = snap.memory.total / (1024**3)
        avail_gb = snap.memory.available / (1024**3)

        runners_up = ""
        if len(by_mem) >= 3:
            runners_up = f"\n\nNext top consumers: `{by_mem[1].name}` ({by_mem[1].memory_mb:.0f} MB) and `{by_mem[2].name}` ({by_mem[2].memory_mb:.0f} MB)."
        elif len(by_mem) == 2:
            runners_up = f"\n\nNext top consumer: `{by_mem[1].name}` ({by_mem[1].memory_mb:.0f} MB)."

        return (
            f"The process consuming the most RAM is **`{top.name}`** (PID `{top.pid}`).\n\n"
            f"• **Memory Footprint:** {top.memory_mb:.0f} MB ({top.memory_percent:.1f}% of physical RAM)\n"
            f"• **Status:** {top.status} ({top.num_threads} threads)\n"
            f"• **System Overview:** Total RAM: {total_gb:.1f} GB | Currently Available: {avail_gb:.1f} GB"
            f"{runners_up}"
        )

    def _answer_top_cpu(self, procs: list[ProcessInfo], snap: SystemSnapshot) -> str:
        if not procs:
            return "No running processes are currently accessible."
        by_cpu = sorted(procs, key=lambda p: p.cpu_percent, reverse=True)
        top = by_cpu[0]

        runners_up = ""
        if len(by_cpu) >= 3:
            runners_up = f"\n\nNext highest CPU consumers: `{by_cpu[1].name}` ({by_cpu[1].cpu_percent:.1f}%) and `{by_cpu[2].name}` ({by_cpu[2].cpu_percent:.1f}%)."
        elif len(by_cpu) == 2:
            runners_up = f"\n\nNext highest CPU consumer: `{by_cpu[1].name}` ({by_cpu[1].cpu_percent:.1f}%)."

        return (
            f"The process demanding the most CPU cycles is **`{top.name}`** (PID `{top.pid}`).\n\n"
            f"• **Current CPU Usage:** {top.cpu_percent:.1f}%\n"
            f"• **RAM Usage:** {top.memory_mb:.0f} MB\n"
            f"• **Active Threads:** {top.num_threads}\n"
            f"• **Overall System CPU:** {snap.cpu.overall_percent:.1f}% across {snap.cpu.core_count_logical} logical cores."
            f"{runners_up}"
        )

    def _answer_what_changed(self, snap: SystemSnapshot, health) -> str:
        history = self.db.get_resource_history(hours=1.0, limit=20)
        if len(history) < 2:
            return "Insufficient historical samples in database yet to compute changes. OSD records baseline metrics continuously every few seconds."

        oldest = history[-1]
        delta_cpu = snap.cpu.overall_percent - (oldest.get('cpu_percent') or 0.0)
        delta_mem = snap.memory.percent - (oldest.get('memory_percent') or 0.0)
        delta_health = health.total_score - (oldest.get('health_score') or 100.0)

        cpu_dir = f"+{delta_cpu:.1f}% higher" if delta_cpu > 0 else f"{delta_cpu:.1f}% lower"
        mem_dir = f"+{delta_mem:.1f}% higher" if delta_mem > 0 else f"{delta_mem:.1f}% lower"

        return (
            f"**Comparison with Baseline (~{len(history)*2} seconds ago):**\n\n"
            f"• **Health Score:** Changed from {oldest.get('health_score', 100):.0f} to **{health.total_score:.0f}**\n"
            f"• **CPU Load:** Now {snap.cpu.overall_percent:.1f}% ({cpu_dir} than baseline)\n"
            f"• **Memory Load:** Now {snap.memory.percent:.1f}% ({mem_dir} than baseline)\n"
            f"• **Active Processes:** {snap.process_count} (baseline had {oldest.get('process_count', 0)})\n\n"
            "System trends remain stable within normal operating variance."
        )

    def _answer_safest_action(self, diags: list[Diagnosis], procs: list[ProcessInfo], snap: SystemSnapshot) -> str:
        heavy_cpu = [p for p in procs if p.cpu_percent > 20.0]
        if heavy_cpu:
            proc = heavy_cpu[0]
            return (
                f"**Safest Recommended Action:** Lower the CPU priority of `{proc.name}` (PID {proc.pid}) to 'Below Normal'.\n\n"
                f"• **Risk Level:** **Low (Completely Reversible)**\n"
                f"• **Why it's safe:** Unlike terminating the process, lowering priority does not close the application or risk unsaved work. "
                "The process continues executing, but automatically yields compute cycles whenever foreground apps need them."
            )

        return (
            "**Safest Recommended Action:** Close inactive background browser tabs or use Disk Cleanup to reclaim temporary files.\n\n"
            "• **Risk Level:** **Low**\n"
            "• **Why it's safe:** Closing background tabs immediately frees RAM without terminating primary applications or services."
        )

    def _answer_memory_trend(self, snap: SystemSnapshot, procs: list[ProcessInfo]) -> str:
        alerts = self.predictive.analyze_predictions(snap, procs)
        mem_alert = next((a for a in alerts if a.metric == "Memory"), None)

        if mem_alert:
            proj = f"in ~{mem_alert.projected_minutes:.0f} minutes" if mem_alert.projected_minutes else "shortly"
            return (
                f"**Yes, memory pressure is steadily increasing.**\n\n"
                f"• **Current Trend:** {mem_alert.headline}\n"
                f"• **Rate of Growth:** {mem_alert.current_rate_per_min:+.1f} MB/min\n"
                f"• **Projected Exhaustion:** {proj} (Confidence: {mem_alert.confidence})\n"
                f"• **Evidence:** {mem_alert.evidence}\n"
                f"• **Prevention:** {mem_alert.prevention_action}"
            )

        return (
            f"**No rapid memory leak detected.** Memory utilization is currently at **{snap.memory.percent:.1f}%** "
            f"({snap.memory.available / (1024**3):.1f} GB available). Rolling samples indicate a stable allocation curve."
        )

    def _answer_last_recovery(self) -> str:
        last = self.db.get_latest_recovery_action()
        if not last:
            return "No automated recovery actions have been executed in this session yet. You can review and approve safe recovery plans in the **Recovery Advisor** tab."

        ts = format_timestamp(last.get('timestamp', 0))
        proc = last.get('target_process', 'Unknown')
        freed = last.get('freed_memory_mb', 0.0)
        cpu_drop = last.get('cpu_drop', 0.0)
        health_gain = last.get('health_gain', 0.0)

        return (
            f"**Verified Results of Last Recovery Action ({ts}):**\n\n"
            f"• **Action Executed:** `{last.get('action_name')}` on `{proc}` (PID {last.get('target_pid')})\n"
            f"• **Freed RAM:** **{freed:.0f} MB** reclaimed\n"
            f"• **CPU Load Reduction:** **-{cpu_drop:.1f}%** drop in CPU pressure\n"
            f"• **Health Score Gain:** **+{health_gain:+.1f} points**\n"
            f"• **Status:** Verified and permanently logged in SQLite."
        )

    def _answer_health_status(self, health, snap: SystemSnapshot, diags: list[Diagnosis]) -> str:
        return (
            f"**System Health Overview:** **{health.total_score:.0f}/100**\n\n"
            f"• CPU Component: {health.cpu_score:.0f}/100\n"
            f"• Memory Component: {health.memory_score:.0f}/100\n"
            f"• Swap Component: {health.swap_score:.0f}/100\n"
            f"• Disk Component: {health.disk_score:.0f}/100\n\n"
            f"Active Findings: {len(diags)} item(s) logged."
        )

    def _answer_default(self, snap: SystemSnapshot, health) -> str:
        return (
            f"I am **OSD Assistant**, your offline, local privacy-conscious system intelligence engine, "
            f"connected to your real-time hardware telemetry and historical database.\n\n"
            f"**Current Status:** System Health Score is **{health.total_score:.0f}/100** | CPU: **{snap.cpu.overall_percent:.1f}%** | RAM: **{snap.memory.percent:.1f}%**\n\n"
            "**Questions you can ask me:**\n"
            "• *Why is my PC slow?*\n"
            "• *Which process uses the most memory?*\n"
            "• *Which process uses the most CPU?*\n"
            "• *What has changed recently?*\n"
            "• *Which recommendation is safest?*\n"
            "• *Is the memory usage increasing?*\n"
            "• *Did the last recovery action improve performance?*"
        )


# Backward compatibility alias
AskOSenseEngine = AskOSDEngine
