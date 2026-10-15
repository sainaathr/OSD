"""
What-If Simulator Page — Sandboxed resource impact estimation.
Lets users explore hypothetical scenarios (e.g. closing memory hogs)
with real-time before/after estimations without touching live processes.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style
from app.analysis.simulator import WhatIfSimulator, SimulationResult
from app.monitoring.system_monitor import SystemMonitor, ProcessInfo, SystemSnapshot
from app.analysis.engine import AnalysisEngine


class SimulatorPage(QWidget):
    """Interactive sandboxed resource simulator."""

    def __init__(self, simulator: WhatIfSimulator, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.simulator = simulator
        self.monitor = monitor
        self._current_processes: list[ProcessInfo] = []
        self._current_snapshot: SystemSnapshot = None
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self.layout_main = QVBoxLayout(content)
        self.layout_main.setContentsMargins(24, 20, 24, 20)
        self.layout_main.setSpacing(16)

        # Header
        title_box = QVBoxLayout()
        title = QLabel("🧪 What-If Resource Simulator")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel(
            "Hypothetically simulate the resource relief of terminating background applications. "
            "Explore potential RAM, CPU, and Health Score gains safely in a sandbox."
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)
        self.layout_main.addLayout(title_box)

        # Disclaimer Banner
        disclaimer = QFrame()
        disclaimer.setStyleSheet(
            f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['accent_cyan']}; "
            f"border-radius: 8px; padding: 10px 14px;"
        )
        dl = QHBoxLayout(disclaimer)
        dl.setContentsMargins(0, 0, 0, 0)
        d_lbl = QLabel("🛡️ <b>SANDBOX MODE:</b> No running processes or system settings will be altered during simulation.")
        d_lbl.setStyleSheet(f"color: {COLORS['accent_cyan']}; font-size: 12px;")
        dl.addWidget(d_lbl)
        self.layout_main.addWidget(disclaimer)

        # Simulation Comparison Results Cards
        res_grid = QGridLayout()
        res_grid.setSpacing(12)

        self.cpu_sim_card = self._create_metric_card("CPU Load", "Current: --", "Simulated: --")
        self.ram_sim_card = self._create_metric_card("RAM Usage", "Current: --", "Simulated: --")
        self.freed_card = self._create_metric_card("Projected RAM Reclaim", "-- MB", "Select processes below")
        self.health_sim_card = self._create_metric_card("Health Score Gain", "-- pts", "Original: --")

        res_grid.addWidget(self.cpu_sim_card[0], 0, 0)
        res_grid.addWidget(self.ram_sim_card[0], 0, 1)
        res_grid.addWidget(self.freed_card[0], 1, 0)
        res_grid.addWidget(self.health_sim_card[0], 1, 1)
        self.layout_main.addLayout(res_grid)

        # Process Selection Section
        proc_box = QGroupBox("Select Processes to Simulate Closing")
        pl = QVBoxLayout(proc_box)
        pl.setContentsMargins(12, 16, 12, 12)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(5)
        self.proc_table.setHorizontalHeaderLabels(["Simulate", "PID", "Process Name", "CPU %", "RAM (MB)"])
        self.proc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.setShowGrid(False)
        self.proc_table.setMinimumHeight(260)
        pl.addWidget(self.proc_table)

        self.layout_main.addWidget(proc_box)

        # Assumptions & Limitations Box
        self.assumptions_label = QLabel(
            "Assumptions: Linear extrapolation based on current process RSS and CPU usage. "
            "Does not account for OS memory compression or processes restarting automatically."
        )
        self.assumptions_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic;")
        self.assumptions_label.setWordWrap(True)
        self.layout_main.addWidget(self.assumptions_label)

        self.layout_main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _create_metric_card(self, title: str, main_val: str, sub_val: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setStyleSheet(card_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: bold;")
        layout.addWidget(t_lbl)

        m_lbl = QLabel(main_val)
        m_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        m_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(m_lbl)

        s_lbl = QLabel(sub_val)
        s_lbl.setStyleSheet(f"color: {COLORS['accent_cyan']}; font-size: 11px;")
        layout.addWidget(s_lbl)

        return card, m_lbl, s_lbl

    def update_processes(self, snapshot: SystemSnapshot, processes: list[ProcessInfo]):
        """Refresh candidate process list while preserving selections."""
        self._current_snapshot = snapshot
        self._current_processes = processes

        # Remember currently checked PIDs
        checked_pids = set()
        for r in range(self.proc_table.rowCount()):
            chk = self.proc_table.cellWidget(r, 0)
            if chk and chk.isChecked():
                pid_item = self.proc_table.item(r, 1)
                if pid_item:
                    try: checked_pids.add(int(pid_item.text()))
                    except ValueError: pass

        self.proc_table.setRowCount(len(processes[:50]))
        for r, p in enumerate(processes[:50]):
            chk = QCheckBox()
            if p.pid in checked_pids:
                chk.setChecked(True)
            chk.stateChanged.connect(self._recalculate_simulation)
            self.proc_table.setCellWidget(r, 0, chk)

            self.proc_table.setItem(r, 1, QTableWidgetItem(str(p.pid)))
            self.proc_table.setItem(r, 2, QTableWidgetItem(p.name))
            self.proc_table.setItem(r, 3, QTableWidgetItem(f"{p.cpu_percent:.1f}%"))
            self.proc_table.setItem(r, 4, QTableWidgetItem(f"{p.memory_mb:.0f} MB"))

        self._recalculate_simulation()

    def _recalculate_simulation(self):
        """Run the sandbox simulation based on checked processes."""
        if not self._current_snapshot:
            return

        selected: list[ProcessInfo] = []
        for r in range(self.proc_table.rowCount()):
            chk = self.proc_table.cellWidget(r, 0)
            if chk and chk.isChecked():
                pid_item = self.proc_table.item(r, 1)
                if pid_item:
                    pid = int(pid_item.text())
                    match = next((p for p in self._current_processes if p.pid == pid), None)
                    if match:
                        selected.append(match)

        result: SimulationResult = self.simulator.simulate_closing_processes(self._current_snapshot, selected)

        # Update cards
        self.cpu_sim_card[1].setText(f"{result.simulated_cpu:.1f}%")
        self.cpu_sim_card[2].setText(f"Original: {result.original_cpu:.1f}% (-{result.cpu_reduction:.1f}%)")

        self.ram_sim_card[1].setText(f"{result.simulated_mem_percent:.1f}%")
        self.ram_sim_card[2].setText(f"Original: {result.original_mem_percent:.1f}% (-{result.mem_percent_reduction:.1f}%)")

        self.freed_card[1].setText(f"+{result.freed_memory_mb:.0f} MB")
        self.freed_card[2].setText(f"{len(selected)} application(s) selected")

        self.health_sim_card[1].setText(f"{result.simulated_health_score:.0f}/100")
        self.health_sim_card[2].setText(f"Gain: +{result.health_score_gain:+.1f} pts (Swap relief: {result.swap_relief_level})")
