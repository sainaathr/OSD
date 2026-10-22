"""
Process Behavior Collector.
Observes process execution patterns across rolling samples to detect anomalies:
CPU surges, monotonic memory growth, and thread explosions.
"""
import time
from collections import defaultdict
from typing import Optional
from osd_core.models.metrics import ProcessInfo
from osd_core.models.diagnostics import BehaviorAlert


class BehaviorCollector:
    """Monitors running processes over rolling samples for behavioral anomalies."""

    def __init__(self, history_len: int = 8):
        self.history_len = history_len
        # Maps pid -> list of (timestamp, cpu, memory_mb, threads)
        self._proc_history: dict[int, list[tuple[float, float, float, int]]] = defaultdict(list)
        self._proc_names: dict[int, str] = {}
        self._last_cleanup = time.time()

    def analyze_processes(self, processes: list[ProcessInfo]) -> list[BehaviorAlert]:
        """Analyze current processes against rolling history to find behavioral anomalies."""
        now = time.time()
        alerts: list[BehaviorAlert] = []
        active_pids = set()

        for p in processes:
            active_pids.add(p.pid)
            self._proc_names[p.pid] = p.name
            hist = self._proc_history[p.pid]
            hist.append((now, p.cpu_percent, p.memory_mb, p.num_threads))
            if len(hist) > self.history_len:
                hist.pop(0)

            # Analyze if we have at least 2 historical observations
            if len(hist) >= 2:
                # 1. Check for rapid CPU jump
                prev_cpu = hist[-2][1]
                cpu_jump = p.cpu_percent - prev_cpu
                if cpu_jump >= 45.0 and p.cpu_percent > 50.0:
                    alerts.append(BehaviorAlert(
                        alert_type="CPU Surge",
                        process_name=p.name,
                        pid=p.pid,
                        severity="Warning",
                        description=f"{p.name} exhibited a sudden CPU surge (+{cpu_jump:.1f}% jump).",
                        evidence=f"CPU jumped from {prev_cpu:.1f}% to {p.cpu_percent:.1f}% in a single monitoring interval.",
                    ))

            if len(hist) >= 4:
                # 2. Check for monotonic memory climb (potential memory leak)
                memories = [h[2] for h in hist[-4:]]
                is_monotonic_increase = all(memories[i] < memories[i+1] for i in range(len(memories)-1))
                net_growth = memories[-1] - memories[0]
                if is_monotonic_increase and net_growth >= 25.0:
                    alerts.append(BehaviorAlert(
                        alert_type="Memory Leak Pattern",
                        process_name=p.name,
                        pid=p.pid,
                        severity="Warning" if net_growth < 100.0 else "Critical",
                        description=f"{p.name} has grown steadily across consecutive samples without reclaiming RAM.",
                        evidence=f"RAM consumption increased monotonically from {memories[0]:.0f} MB to {memories[-1]:.0f} MB (+{net_growth:.1f} MB over last {len(memories)} samples).",
                    ))

                # 3. Check for thread expansion
                threads = [h[3] for h in hist[-4:]]
                thread_jump = threads[-1] - threads[0]
                if thread_jump >= 40:
                    alerts.append(BehaviorAlert(
                        alert_type="Thread Expansion",
                        process_name=p.name,
                        pid=p.pid,
                        severity="Information",
                        description=f"{p.name} rapidly spawned {thread_jump} new threads.",
                        evidence=f"Thread count expanded from {threads[0]} to {threads[-1]} threads.",
                    ))

        # Evict terminated processes every 30 seconds
        if now - self._last_cleanup > 30.0:
            self._last_cleanup = now
            stale = set(self._proc_history.keys()) - active_pids
            for pid in stale:
                self._proc_history.pop(pid, None)
                self._proc_names.pop(pid, None)

        return alerts
