"""
Intelligence Page — Unified System Intelligence Suite
Integrates:
1. Ask OSense (Telemetry-Grounded Technical Copilot)
2. Predictive Alerts & Behavior Forensics
3. What-If Sandboxed Resource Simulator
4. Workload Sensitivity Profiles
Art-directed as an integrated technical console rather than a generic chatbot card.
"""
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from app.ui.styles import COLORS, card_style, panel_alt_style, severity_badge_style
from app.ui.components import PageHeader, SegmentedTab, EmptyStateWidget
from app.assistant.chat_engine import AskOSenseEngine
from app.analysis.predictive_engine import PredictiveAlert
from app.analysis.simulator import WhatIfSimulator, SimulationResult
from app.profiles.profile_manager import ProfileManager, WorkloadProfile
from app.monitoring.system_monitor import SystemMonitor, ProcessInfo, SystemSnapshot


# -------------------------------------------------------------
# 1. Ask OSense Copilot Tab
# -------------------------------------------------------------
class ChatMemoItem(QFrame):
    """Clean technical transcript memo item."""

    def __init__(self, sender: str, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(panel_alt_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        sender_lbl = QLabel(sender.upper())
        sender_lbl.setStyleSheet(
            f"color: {COLORS['accent_lime'] if is_user else COLORS['accent_teal']}; "
            f"font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
        )
        hdr.addWidget(sender_lbl)
        hdr.addStretch()

        time_lbl = QLabel(time.strftime("%H:%M:%S"))
        time_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        hdr.addWidget(time_lbl)
        layout.addLayout(hdr)

        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
        msg_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; line-height: 1.45;")
        layout.addWidget(msg_lbl)


class AskOSenseTab(QWidget):
    """Technical copilot tab grounded in live telemetry."""

    def __init__(self, chat_engine: AskOSenseEngine, parent=None):
        super().__init__(parent)
        self.engine = chat_engine
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        # Telemetry grounding banner
        banner = QFrame()
        banner.setStyleSheet(panel_alt_style())
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel("●  GROUNDED IN LIVE TELEMETRY  •  LOCAL INFERENCE  •  NO EXTERNAL CLOUD TRANSMISSION")
        lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        bl.addWidget(lbl)
        layout.addWidget(banner)

        # Quick Technical Prompts Row
        prompts_box = QHBoxLayout()
        prompts_box.setSpacing(8)

        prompts = [
            "Why is my machine slow?",
            "Which process uses the most memory?",
            "What has changed recently?",
            "Are there any memory leak risks?",
            "Is the memory usage increasing?"
        ]
        for p in prompts[:4]:
            btn = QPushButton(p)
            btn.setFixedHeight(26)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_secondary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; font-size: 10px; padding: 2px 10px; font-weight: 500; }}"
                f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; color: {COLORS['accent_lime']}; }}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda ch, text=p: self._send_query(text))
            prompts_box.addWidget(btn)
        prompts_box.addStretch()
        layout.addLayout(prompts_box)

        # Transcript Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(10)

        # Welcome memo
        welcome = ChatMemoItem(
            "OSense Copilot",
            "Hello. I am grounded in your live CPU, memory, disk I/O, process states, and SQLite history. "
            "Ask a performance question or click one of the technical prompts above."
        )
        self.chat_layout.addWidget(welcome)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll, 1)

        # Query Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask OSense about system state, bottlenecks, or resource hogs... (Enter)")
        self.query_input.setFixedHeight(38)
        self.query_input.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.query_input, 1)

        send_btn = QPushButton("Submit Query")
        send_btn.setFixedHeight(38)
        send_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
            f"border: 1px solid {COLORS['accent_lime']}; border-radius: 6px; font-weight: 700; font-size: 11px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_lime_dim']}; }}"
        )
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._on_submit)
        input_row.addWidget(send_btn)

        layout.addLayout(input_row)

    def _on_submit(self):
        text = self.query_input.text().strip()
        if text:
            self.query_input.clear()
            self._send_query(text)

    def _send_query(self, query: str):
        # Insert user message
        user_item = ChatMemoItem("User", query, is_user=True)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, user_item)

        # Get response from local chat engine
        answer = self.engine.ask(query)

        # Insert assistant response
        bot_item = ChatMemoItem("OSense Copilot", answer, is_user=False)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bot_item)

        # Scroll to bottom
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())


# -------------------------------------------------------------
# 2. Predictive Alerts & Forensics Tab
# -------------------------------------------------------------
class PredictiveAlertCard(QFrame):
    """Forensic alert card with rate of change and projection window."""

    def __init__(self, alert: PredictiveAlert, parent=None):
        super().__init__(parent)
        is_crit = alert.severity.lower() in ['critical', 'high']
        border_color = COLORS['red'] if is_crit else COLORS['amber']
        self.setStyleSheet(card_style(f"border-left: 3px solid {border_color};"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        metric_badge = QLabel(alert.metric.upper())
        metric_badge.setStyleSheet(
            f"color: {COLORS['accent_teal']}; background-color: {COLORS['bg_panel_alt']}; "
            f"border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 2px 7px; "
            f"font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
        )
        hdr.addWidget(metric_badge)

        headline = QLabel(alert.headline)
        headline.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        headline.setStyleSheet(f"color: {COLORS['text_primary']};")
        hdr.addWidget(headline, 1)

        conf_lbl = QLabel(f"CONFIDENCE: {alert.confidence.upper()}")
        conf_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        hdr.addWidget(conf_lbl)
        layout.addLayout(hdr)

        # Inset Technical Forensics
        ibox = QFrame()
        ibox.setStyleSheet(panel_alt_style())
        ibl = QVBoxLayout(ibox)
        ibl.setContentsMargins(14, 10, 14, 10)
        ibl.setSpacing(6)

        stats_row = QHBoxLayout()
        if alert.projected_minutes is not None:
            w_lbl = QLabel(f"⏱️ ESTIMATED PRESSURE WINDOW: ~{alert.projected_minutes:.0f} MINUTES")
            w_lbl.setStyleSheet(f"color: {border_color}; font-weight: 700; font-size: 11px; font-family: 'Consolas', monospace;")
            stats_row.addWidget(w_lbl)

        r_lbl = QLabel(f"GROWTH RATE: {alert.current_rate_per_min:+.1f} MB/MIN")
        r_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: 'Consolas', monospace;")
        stats_row.addWidget(r_lbl)
        stats_row.addStretch()
        ibl.addLayout(stats_row)

        ev_lbl = QLabel(f"<b>Evidence:</b> {alert.evidence}")
        ev_lbl.setWordWrap(True)
        ev_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px;")
        ibl.addWidget(ev_lbl)

        prev_lbl = QLabel(f"<b>Recommended Prevention:</b> {alert.prevention_action}")
        prev_lbl.setWordWrap(True)
        prev_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 11px;")
        ibl.addWidget(prev_lbl)

        # Assumptions
        ass_lbl = QLabel(f"Assumptions: {alert.assumptions}  •  Limitations: {alert.limitations}")
        ass_lbl.setWordWrap(True)
        ass_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-style: italic;")
        ibl.addWidget(ass_lbl)

        layout.addWidget(ibox)


class PredictiveTab(QWidget):
    """Predictive trend alerts and time-series extrapolation view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        self.alerts_layout = QVBoxLayout()
        self.alerts_layout.setSpacing(10)

        self.empty_widget = EmptyStateWidget(
            "No Linear Trend Breaches Projected",
            "Continuous memory growth rate and swap usage are stable. No processes show active leakage characteristics."
        )
        self.alerts_layout.addWidget(self.empty_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        c = QWidget()
        c.setLayout(self.alerts_layout)
        scroll.setWidget(c)

        layout.addWidget(scroll)

    def update_alerts(self, alerts: list[PredictiveAlert]):
        while self.alerts_layout.count():
            item = self.alerts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not alerts:
            self.alerts_layout.addWidget(EmptyStateWidget(
                "No Linear Trend Breaches Projected",
                "Continuous memory growth rate and swap usage are stable. No processes show active leakage characteristics."
            ))
            return

        for a in alerts:
            card = PredictiveAlertCard(a)
            self.alerts_layout.addWidget(card)


# -------------------------------------------------------------
# 3. What-If Resource Simulator Tab
# -------------------------------------------------------------
class SimulatorTab(QWidget):
    """Sandboxed what-if load impact simulator."""

    def __init__(self, simulator: WhatIfSimulator, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.simulator = simulator
        self.monitor = monitor
        self._current_processes: list[ProcessInfo] = []
        self._current_snapshot: SystemSnapshot = None
        self._selected_pids = set()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        # Sandbox Guarantee Banner
        banner = QFrame()
        banner.setStyleSheet(panel_alt_style())
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel("🛡️  SANDBOX MODE: No running processes will be touched. Impact is mathematically modeled from live telemetry.")
        lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        bl.addWidget(lbl)
        layout.addWidget(banner)

        # Simulation Comparison Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self.before_card = QFrame()
        self.before_card.setStyleSheet(card_style())
        bcl = QVBoxLayout(self.before_card)
        bcl.setContentsMargins(14, 12, 14, 12)
        bcl.addWidget(QLabel("BASELINE (CURRENT)"))
        self.baseline_lbl = QLabel("CPU: --  •  RAM: --")
        self.baseline_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-family: 'Consolas', monospace;")
        bcl.addWidget(self.baseline_lbl)
        cards_row.addWidget(self.before_card)

        self.after_card = QFrame()
        self.after_card.setStyleSheet(card_style())
        acl = QVBoxLayout(self.after_card)
        acl.setContentsMargins(14, 12, 14, 12)
        acl.addWidget(QLabel("SIMULATED OUTCOME"))
        self.simulated_lbl = QLabel("Select candidate processes below...")
        self.simulated_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-family: 'Consolas', monospace;")
        acl.addWidget(self.simulated_lbl)
        cards_row.addWidget(self.after_card)

        layout.addLayout(cards_row)

        # Process Selection Table
        table_lbl = QLabel("SELECT PROCESSES TO HYPOTHETICALLY TERMINATE:")
        table_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        layout.addWidget(table_lbl)

        self.sim_table = QTableWidget()
        self.sim_table.setColumnCount(4)
        self.sim_table.setHorizontalHeaderLabels(["SIMULATE", "PID", "PROCESS NAME", "MEMORY FOOTPRINT"])
        self.sim_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.sim_table.verticalHeader().setVisible(False)
        self.sim_table.setShowGrid(False)
        layout.addWidget(self.sim_table, 1)

    def update_snapshot(self, snap: SystemSnapshot):
        self._current_snapshot = snap
        self.baseline_lbl.setText(
            f"CPU: {snap.cpu.overall_percent:.1f}%  |  "
            f"RAM: {snap.memory.percent:.1f}% ({snap.memory.used/(1024**3):.1f} GB)"
        )

    def update_processes(self, procs: list[ProcessInfo]):
        self._current_processes = sorted(procs, key=lambda p: p.memory_mb, reverse=True)[:25]
        self.sim_table.setRowCount(len(self._current_processes))

        for row, p in enumerate(self._current_processes):
            cb = QCheckBox()
            cb.setChecked(p.pid in self._selected_pids)
            cb.stateChanged.connect(lambda state, pid=p.pid: self._on_toggle(pid, state))
            self.sim_table.setCellWidget(row, 0, cb)

            pid_item = QTableWidgetItem(str(p.pid))
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pid_item.setFont(QFont("Consolas", 10))
            self.sim_table.setItem(row, 1, pid_item)

            name_item = QTableWidgetItem(p.name)
            self.sim_table.setItem(row, 2, name_item)

            mem_item = QTableWidgetItem(f"{p.memory_mb:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            mem_item.setFont(QFont("Consolas", 10))
            self.sim_table.setItem(row, 3, mem_item)

    def _on_toggle(self, pid: int, state: int):
        if state == 2:
            self._selected_pids.add(pid)
        else:
            self._selected_pids.discard(pid)
        self._run_simulation()

    def _run_simulation(self):
        if not self._current_snapshot or not self._selected_pids:
            self.simulated_lbl.setText("Select candidate processes below...")
            return

        res: SimulationResult = self.simulator.simulate_process_termination(
            self._current_snapshot, self._current_processes, list(self._selected_pids)
        )
        self.simulated_lbl.setText(
            f"Freed: {res.freed_memory_mb:.0f} MB  |  "
            f"Projected RAM: {res.projected_ram_percent:.1f}%  |  "
            f"Health Score Gain: +{res.health_score_delta:.0f} pts"
        )


# -------------------------------------------------------------
# 4. Workload Profiles Tab
# -------------------------------------------------------------
class ProfilesTab(QWidget):
    """Workload sensitivity profiles tab."""

    profile_changed = Signal(str)

    def __init__(self, manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        desc = QLabel(
            "Workload profiles adapt OSense's anomaly thresholds, alerting sensitivity, and background polling cadence "
            "to match your current task."
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(desc)

        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(12)
        layout.addLayout(self.cards_grid)
        layout.addStretch()

        self.refresh_profiles()

    def refresh_profiles(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        profiles = list(self.manager.profiles.values())
        active = self.manager.get_active_profile()

        for idx, p in enumerate(profiles):
            is_act = (active.name == p.name) if active else False
            card = QFrame()
            border = f"border: 2px solid {COLORS['accent_lime']};" if is_act else f"border: 1px solid {COLORS['border']};"
            card.setStyleSheet(
                f"QFrame {{ background-color: {COLORS['bg_card']}; {border} border-radius: 8px; }} "
                f"QLabel {{ background: transparent; }}"
            )

            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.setSpacing(6)

            hdr = QHBoxLayout()
            t_lbl = QLabel(p.display_title.upper())
            t_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            t_lbl.setStyleSheet(f"color: {COLORS['accent_lime'] if is_act else COLORS['text_primary']};")
            hdr.addWidget(t_lbl)
            hdr.addStretch()

            if is_act:
                act_badge = QLabel("ACTIVE PROFILE")
                act_badge.setStyleSheet(severity_badge_style("Healthy"))
                hdr.addWidget(act_badge)
            cl.addLayout(hdr)

            d_lbl = QLabel(p.description)
            d_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            d_lbl.setWordWrap(True)
            cl.addWidget(d_lbl)

            th_lbl = QLabel(f"• Thresholds: CPU Warn {p.cpu_warning:.0f}%, RAM Warn {p.memory_warning:.0f}% • Cadence: {p.refresh_interval_sec}s")
            th_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
            cl.addWidget(th_lbl)

            if not is_act:
                btn = QPushButton("Activate Profile")
                btn.setFixedHeight(28)
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {COLORS['bg_panel_alt']}; color: {COLORS['text_primary']}; "
                    f"border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; font-size: 11px; font-weight: 600; }}"
                    f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; color: {COLORS['accent_lime']}; }}"
                )
                btn.clicked.connect(lambda ch, name=p.name: self._activate(name))
                cl.addWidget(btn)

            row = idx // 2
            col = idx % 2
            self.cards_grid.addWidget(card, row, col)

    def _activate(self, name: str):
        self.manager.set_active_profile(name)
        self.refresh_profiles()
        self.profile_changed.emit(name)


# -------------------------------------------------------------
# Main Intelligence Page Container
# -------------------------------------------------------------
class IntelligencePage(QWidget):
    """Central unified Intelligence Suite."""

    profile_changed = Signal(str)

    def __init__(self, chat_engine: AskOSenseEngine, simulator: WhatIfSimulator,
                 monitor: SystemMonitor, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self._setup_ui(chat_engine, simulator, monitor, profile_manager)

    def _setup_ui(self, chat_engine, simulator, monitor, profile_manager):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        eyebrow = QLabel("ANALYTIC INTELLIGENCE")
        eyebrow.setStyleSheet(
            f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; font-family: 'Consolas', monospace;"
        )
        title_box.addWidget(eyebrow)

        title = QLabel("System Intelligence")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel("Integrated telemetry reasoning: Copilot assistant, predictive growth alerts, sandboxed simulator, and sensitivity profiles.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)

        header_row.addLayout(title_box, 1)

        # Linear-Style Segmented Navigation Tabs
        self.nav_tabs = SegmentedTab([
            "COPILOT",
            "PREDICTIVE",
            "SIMULATOR",
            "PROFILES"
        ], current_index=0)
        self.nav_tabs.tab_changed.connect(self._on_subtab_changed)
        header_row.addWidget(self.nav_tabs, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(header_row)

        # Stacked Sub-views
        self.sub_stack = QStackedWidget()

        self.ask_tab = AskOSenseTab(chat_engine)
        self.pred_tab = PredictiveTab()
        self.sim_tab = SimulatorTab(simulator, monitor)
        self.prof_tab = ProfilesTab(profile_manager)
        self.prof_tab.profile_changed.connect(self.profile_changed.emit)

        self.sub_stack.addWidget(self.ask_tab)
        self.sub_stack.addWidget(self.pred_tab)
        self.sub_stack.addWidget(self.sim_tab)
        self.sub_stack.addWidget(self.prof_tab)

        layout.addWidget(self.sub_stack, 1)

    def _on_subtab_changed(self, index: int):
        self.sub_stack.setCurrentIndex(index)
        if index == 3:
            self.prof_tab.refresh_profiles()

    def update_alerts(self, alerts: list[PredictiveAlert]):
        self.pred_tab.update_alerts(alerts)

    def update_snapshot(self, snap: SystemSnapshot):
        self.sim_tab.update_snapshot(snap)

    def update_processes(self, procs: list[ProcessInfo]):
        self.sim_tab.update_processes(procs)

    def refresh_profiles(self):
        self.prof_tab.refresh_profiles()
