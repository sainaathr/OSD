"""
What-If Simulator — Sandboxed resource impact estimation.
Calculates hypothetical changes in CPU, RAM, and Health Score
if selected applications are closed, without altering any live processes.
"""
from dataclasses import dataclass, field
from app.monitoring.system_monitor import SystemSnapshot, ProcessInfo
from app.analysis.engine import AnalysisEngine, HealthScoreBreakdown


@dataclass
class SimulationResult:
    selected_pids: list[int]
    selected_names: list[str]
    original_cpu: float
    simulated_cpu: float
    cpu_reduction: float
    original_mem_percent: float
    simulated_mem_percent: float
    mem_percent_reduction: float
    freed_memory_mb: float
    original_health_score: float
    simulated_health_score: float
    health_score_gain: float
    swap_relief_level: str          # "High", "Medium", "Low", "None"
    assumptions: str = (
        "Assumes selected processes terminate cleanly without transferring "
        "workload to child threads or persistent background helper services."
    )
    disclaimer: str = (
        "SIMULATION MODE: No running processes were modified, suspended, or terminated. "
        "All calculations are sandbox estimates based on live telemetry."
    )

    def to_dict(self) -> dict:
        return {
            'selected_pids': self.selected_pids,
            'selected_names': self.selected_names,
            'original_cpu': round(self.original_cpu, 1),
            'simulated_cpu': round(self.simulated_cpu, 1),
            'cpu_reduction': round(self.cpu_reduction, 1),
            'original_mem_percent': round(self.original_mem_percent, 1),
            'simulated_mem_percent': round(self.simulated_mem_percent, 1),
            'mem_percent_reduction': round(self.mem_percent_reduction, 1),
            'freed_memory_mb': round(self.freed_memory_mb, 1),
            'original_health_score': round(self.original_health_score, 1),
            'simulated_health_score': round(self.simulated_health_score, 1),
            'health_score_gain': round(self.health_score_gain, 1),
            'swap_relief_level': self.swap_relief_level,
            'assumptions': self.assumptions,
            'disclaimer': self.disclaimer,
        }


class WhatIfSimulator:
    """Computes sandboxed resource relief for hypothetical system changes."""

    def __init__(self, analysis_engine: AnalysisEngine):
        self.analysis = analysis_engine

    def simulate_closing_processes(self, snapshot: SystemSnapshot,
                                   selected_processes: list[ProcessInfo]) -> SimulationResult:
        """Simulate the effect of terminating a set of selected processes."""
        orig_health = self.analysis.calculate_health_score(snapshot).total_score

        total_ram_mb = snapshot.memory.total / (1024 * 1024)
        total_freed_mb = sum(p.memory_mb for p in selected_processes)
        total_cpu_freed = sum(p.cpu_percent for p in selected_processes)

        if not selected_processes:
            sim_cpu = snapshot.cpu.overall_percent
            sim_mem_used_mb = snapshot.memory.used / (1024 * 1024)
            sim_mem_percent = snapshot.memory.percent
            cpu_reduction = 0.0
            mem_percent_reduction = 0.0
            sim_health = orig_health
            health_gain = 0.0
        else:
            cpu_reduction = total_cpu_freed
            sim_cpu = max(1.0, snapshot.cpu.overall_percent - total_cpu_freed)
            sim_mem_used_mb = max(100.0, (snapshot.memory.used / (1024 * 1024)) - total_freed_mb)
            sim_mem_percent = max(5.0, (sim_mem_used_mb / total_ram_mb) * 100.0) if total_ram_mb > 0 else 0.0
            mem_percent_reduction = max(0.0, snapshot.memory.percent - sim_mem_percent)

            # Construct synthetic simulated snapshot for health calculation
            from copy import deepcopy
            sim_snap = deepcopy(snapshot)
            sim_snap.cpu.overall_percent = sim_cpu
            sim_snap.memory.percent = sim_mem_percent
            sim_snap.memory.used = int(sim_mem_used_mb * (1024 * 1024))
            sim_snap.memory.available = int((total_ram_mb - sim_mem_used_mb) * (1024 * 1024))

            sim_health = self.analysis.calculate_health_score(sim_snap).total_score
            health_gain = max(0.0, sim_health - orig_health)

        # Swap relief estimation
        swap_relief = "None"
        if snapshot.memory.swap_percent > 30.0 and selected_processes:
            if sim_mem_percent < 70.0:
                swap_relief = "High"
            elif sim_mem_percent < 80.0:
                swap_relief = "Medium"
            else:
                swap_relief = "Low"

        return SimulationResult(
            selected_pids=[p.pid for p in selected_processes],
            selected_names=[p.name for p in selected_processes],
            original_cpu=snapshot.cpu.overall_percent,
            simulated_cpu=sim_cpu,
            cpu_reduction=cpu_reduction,
            original_mem_percent=snapshot.memory.percent,
            simulated_mem_percent=sim_mem_percent,
            mem_percent_reduction=mem_percent_reduction,
            freed_memory_mb=total_freed_mb,
            original_health_score=orig_health,
            simulated_health_score=sim_health,
            health_score_gain=health_gain,
            swap_relief_level=swap_relief,
        )

    def simulate_process_termination(self, snapshot: SystemSnapshot,
                                     processes: list[ProcessInfo],
                                     selected_pids: list[int]) -> SimulationResult:
        """Simulate the effect of terminating a set of processes identified by PID."""
        selected = [p for p in processes if p.pid in selected_pids]
        return self.simulate_closing_processes(snapshot, selected)

    def simulate_condition_shift(self, snapshot: SystemSnapshot,
                                 cpu_shift: float = 0.0,
                                 mem_shift: float = 0.0,
                                 disk_io_mb: float = 0.0,
                                 selected_processes: list[ProcessInfo] = None) -> tuple[SystemSnapshot, HealthScoreBreakdown]:
        """Model a synthetic system state combining base snapshot, condition adjustments, and process terminations."""
        from copy import deepcopy
        sim_snap = deepcopy(snapshot)

        total_freed_mb = sum(p.memory_mb for p in (selected_processes or []))
        total_cpu_freed = sum(p.cpu_percent for p in (selected_processes or []))

        # Apply process relief
        base_cpu = max(1.0, snapshot.cpu.overall_percent - total_cpu_freed)
        total_ram_mb = snapshot.memory.total / (1024 * 1024) if snapshot.memory.total > 0 else 16384.0
        used_ram_mb = max(100.0, (snapshot.memory.used / (1024 * 1024)) - total_freed_mb)
        base_mem_pct = max(5.0, (used_ram_mb / total_ram_mb) * 100.0)

        # Apply synthetic condition shifts
        sim_cpu = max(1.0, min(100.0, base_cpu + cpu_shift))
        sim_mem_pct = max(5.0, min(100.0, base_mem_pct + mem_shift))

        sim_snap.cpu.overall_percent = sim_cpu
        sim_snap.memory.percent = sim_mem_pct
        sim_snap.memory.used = int((sim_mem_pct / 100.0) * snapshot.memory.total)
        sim_snap.memory.available = max(0, snapshot.memory.total - sim_snap.memory.used)

        if disk_io_mb > 0:
            bytes_sec = disk_io_mb * 1024 * 1024
            sim_snap.disk.read_bytes_per_sec = bytes_sec * 0.5
            sim_snap.disk.write_bytes_per_sec = bytes_sec * 0.5

        health = self.analysis.calculate_health_score(sim_snap)
        return sim_snap, health
