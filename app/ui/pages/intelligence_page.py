"""
Intelligence Page — Unified System Intelligence Suite
Integrates:
1. Ask OSD (Telemetry-Grounded Technical Copilot)
2. Predictive Alerts & Behavior Forensics
3. What-If Sandboxed Resource Simulator
4. Workload Sensitivity Profiles
Art-directed as an integrated technical console rather than a generic chatbot card.
"""
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QGridLayout, QMessageBox,
    QSlider, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from app.ui.styles import COLORS, card_style, panel_alt_style, severity_badge_style
from app.ui.components import PageHeader, SegmentedTab, EmptyStateWidget
from app.assistant.chat_engine import AskOSDEngine, AskOSenseEngine
from app.analysis.predictive_engine import PredictiveAlert
from app.analysis.simulator import WhatIfSimulator, SimulationResult
from app.recommendations.engine import RecommendationEngine
from app.analysis.engine import HealthScoreBreakdown
from app.profiles.profile_manager import ProfileManager, WorkloadProfile
from app.monitoring.system_monitor import SystemMonitor, ProcessInfo, SystemSnapshot


# -------------------------------------------------------------
# 1. Ask OSD Copilot Tab
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


class AskOSDTab(QWidget):
    """Technical copilot tab grounded in live telemetry."""

    def __init__(self, chat_engine: AskOSDEngine, parent=None):
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
            "OSD Copilot",
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
        self.query_input.setPlaceholderText("Ask OSD about system state, bottlenecks, or resource hogs... (Enter)")
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
        bot_item = ChatMemoItem("OSD Copilot", answer, is_user=False)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bot_item)

        # Scroll to bottom
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())


# Backward-compatible alias
AskOSenseTab = AskOSDTab


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
    """
    Sandboxed what-if load impact simulator.
    Provides interactive controls for candidate processes and simulated system conditions,
    calculating real-time before/after metrics, simulated diagnosis findings,
    recommendations, and simulated recovery actions.
    """

    def __init__(self, simulator: WhatIfSimulator, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.simulator = simulator
        self.monitor = monitor
        self.recommender = RecommendationEngine()

        self._current_processes: list[ProcessInfo] = []
        self._current_snapshot: SystemSnapshot = None
        self._selected_pids: set[int] = set()

        # Simulation state
        self._is_live_paused = False
        self._cpu_offset = 0.0
        self._ram_offset = 0.0
        self._disk_io_mb = 0.0
        self._sim_recovery_applied = []
        self._dirty = True

        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(14)

        # 1. Prominent Sandbox Isolation Banner
        banner = QFrame()
        banner.setStyleSheet(
            f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['accent_teal']}; "
            f"border-radius: 6px; padding: 10px 14px;"
        )
        bl = QVBoxLayout(banner)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)

        b_hdr = QHBoxLayout()
        tag = QLabel("🛡️  SIMULATION MODE // MATHEMATICALLY MODELED SANDBOX")
        tag.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        b_hdr.addWidget(tag)
        b_hdr.addStretch()

        self.mode_status_badge = QLabel("SANDBOX ACTIVE")
        self.mode_status_badge.setStyleSheet(
            f"color: {COLORS['accent_lime']}; background: rgba(212, 255, 0, 0.12); "
            f"padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
        )
        b_hdr.addWidget(self.mode_status_badge)
        bl.addLayout(b_hdr)

        lbl = QLabel(
            "All metrics, diagnoses, and actions are mathematically simulated in memory. "
            "Zero changes are made to actual PC processes, disks, or OS settings."
        )
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        bl.addWidget(lbl)
        layout.addWidget(banner)

        # 2. Interactive Controls & Action Toolbar
        tb_frame = QFrame()
        tb_frame.setStyleSheet(panel_alt_style())
        tbl = QHBoxLayout(tb_frame)
        tbl.setContentsMargins(10, 8, 10, 8)
        tbl.setSpacing(8)

        action_lbl = QLabel("SCENARIOS:")
        action_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        tbl.addWidget(action_lbl)

        btn_top3 = QPushButton("⚡ Select Top 3 Hogs")
        btn_top3.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 10px; font-size: 11px;")
        btn_top3.clicked.connect(self._select_top3)
        tbl.addWidget(btn_top3)

        btn_browsers = QPushButton("🌐 Select Browsers")
        btn_browsers.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 10px; font-size: 11px;")
        btn_browsers.clicked.connect(self._select_browsers)
        tbl.addWidget(btn_browsers)

        btn_clear = QPushButton("🧹 Clear All")
        btn_clear.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 10px; font-size: 11px;")
        btn_clear.clicked.connect(self._clear_selections)
        tbl.addWidget(btn_clear)

        tbl.addStretch()

        self.btn_pause = QPushButton("⏸ Pause Baseline")
        self.btn_pause.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 10px; font-size: 11px;")
        self.btn_pause.clicked.connect(self._toggle_pause_baseline)
        tbl.addWidget(self.btn_pause)

        btn_reset = QPushButton("🔄 Reset to Baseline")
        btn_reset.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 10px; font-size: 11px;")
        btn_reset.clicked.connect(self._reset_to_baseline)
        tbl.addWidget(btn_reset)

        btn_defaults = QPushButton("↺ Restore Defaults")
        btn_defaults.setStyleSheet(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 10px; font-size: 11px;")
        btn_defaults.clicked.connect(self._restore_defaults)
        tbl.addWidget(btn_defaults)

        layout.addWidget(tb_frame)

        # 3. Simulated System Condition Controls & Stress Presets
        cond_box = QGroupBox("SIMULATED LOAD CONDITIONS & BOTTLENECK STRESS PRESETS")
        cond_box.setStyleSheet(
            f"QGroupBox {{ color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"border: 1px solid {COLORS['border_subtle']}; border-radius: 6px; margin-top: 10px; padding-top: 14px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}"
        )
        cbl = QVBoxLayout(cond_box)
        cbl.setContentsMargins(12, 12, 12, 12)
        cbl.setSpacing(10)

        # Presets Row
        p_row = QHBoxLayout()
        p_row.setSpacing(8)
        p_lbl = QLabel("PRESETS:")
        p_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        p_row.addWidget(p_lbl)

        btn_p_opt = QPushButton("✨ Healthy Baseline")
        btn_p_opt.setStyleSheet(f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; padding: 3px 8px; font-size: 10px;")
        btn_p_opt.clicked.connect(lambda: self._apply_condition_preset(0, 0, 0))
        p_row.addWidget(btn_p_opt)

        btn_p_cpu = QPushButton("🔥 High CPU Surge (+40%)")
        btn_p_cpu.setStyleSheet(f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; padding: 3px 8px; font-size: 10px;")
        btn_p_cpu.clicked.connect(lambda: self._apply_condition_preset(40, 0, 0))
        p_row.addWidget(btn_p_cpu)

        btn_p_mem = QPushButton("💾 Memory Pressure (+30%)")
        btn_p_mem.setStyleSheet(f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; padding: 3px 8px; font-size: 10px;")
        btn_p_mem.clicked.connect(lambda: self._apply_condition_preset(0, 30, 0))
        p_row.addWidget(btn_p_mem)

        btn_p_disk = QPushButton("💿 Disk Contention (80 MB/s)")
        btn_p_disk.setStyleSheet(f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; padding: 3px 8px; font-size: 10px;")
        btn_p_disk.clicked.connect(lambda: self._apply_condition_preset(0, 0, 80))
        p_row.addWidget(btn_p_disk)

        p_row.addStretch()
        cbl.addLayout(p_row)

        # Condition Sliders Grid
        s_grid = QGridLayout()
        s_grid.setSpacing(10)

        # CPU slider
        s_grid.addWidget(QLabel("Simulated CPU Offset:"), 0, 0)
        self.slider_cpu = QSlider(Qt.Orientation.Horizontal)
        self.slider_cpu.setRange(-40, 60)
        self.slider_cpu.setValue(0)
        self.slider_cpu.valueChanged.connect(self._on_slider_changed)
        s_grid.addWidget(self.slider_cpu, 0, 1)
        self.lbl_cpu_slider_val = QLabel("0%")
        self.lbl_cpu_slider_val.setStyleSheet(f"color: {COLORS['accent_teal']}; font-family: 'Consolas', monospace; font-size: 11px;")
        self.lbl_cpu_slider_val.setFixedWidth(55)
        s_grid.addWidget(self.lbl_cpu_slider_val, 0, 2)

        # RAM slider
        s_grid.addWidget(QLabel("Simulated RAM Offset:"), 1, 0)
        self.slider_ram = QSlider(Qt.Orientation.Horizontal)
        self.slider_ram.setRange(-40, 50)
        self.slider_ram.setValue(0)
        self.slider_ram.valueChanged.connect(self._on_slider_changed)
        s_grid.addWidget(self.slider_ram, 1, 1)
        self.lbl_ram_slider_val = QLabel("0%")
        self.lbl_ram_slider_val.setStyleSheet(f"color: {COLORS['accent_teal']}; font-family: 'Consolas', monospace; font-size: 11px;")
        self.lbl_ram_slider_val.setFixedWidth(55)
        s_grid.addWidget(self.lbl_ram_slider_val, 1, 2)

        # Disk I/O slider
        s_grid.addWidget(QLabel("Simulated Disk I/O:"), 2, 0)
        self.slider_disk = QSlider(Qt.Orientation.Horizontal)
        self.slider_disk.setRange(0, 150)
        self.slider_disk.setValue(0)
        self.slider_disk.valueChanged.connect(self._on_slider_changed)
        s_grid.addWidget(self.slider_disk, 2, 1)
        self.lbl_disk_slider_val = QLabel("0 MB/s")
        self.lbl_disk_slider_val.setStyleSheet(f"color: {COLORS['accent_teal']}; font-family: 'Consolas', monospace; font-size: 11px;")
        self.lbl_disk_slider_val.setFixedWidth(55)
        s_grid.addWidget(self.lbl_disk_slider_val, 2, 2)

        cbl.addLayout(s_grid)
        layout.addWidget(cond_box)

        # 4. Visual Comparison Metric Cards
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self.card_cpu, self.sim_cpu_val, self.sim_cpu_sub = self._create_sim_card("SIMULATED CPU", "--%", "Current Baseline: --%")
        self.card_ram, self.sim_ram_val, self.sim_ram_sub = self._create_sim_card("SIMULATED RAM", "--%", "Current Baseline: --%")
        self.card_freed, self.sim_freed_val, self.sim_freed_sub = self._create_sim_card("RECLAIMED RAM", "0 MB", "0 processes selected", val_color=COLORS['accent_lime'])
        self.card_health, self.sim_health_val, self.sim_health_sub = self._create_sim_card("PROJECTED HEALTH", "--/100", "Baseline: --")

        cards_grid.addWidget(self.card_cpu, 0, 0)
        cards_grid.addWidget(self.card_ram, 0, 1)
        cards_grid.addWidget(self.card_freed, 1, 0)
        cards_grid.addWidget(self.card_health, 1, 1)
        layout.addLayout(cards_grid)

        # 5. Simulated Diagnoses & Recovery Remediation Row
        diag_rec_row = QHBoxLayout()
        diag_rec_row.setSpacing(12)

        # Left: Simulated Findings
        diag_card = QFrame()
        diag_card.setStyleSheet(card_style())
        dcl = QVBoxLayout(diag_card)
        dcl.setContentsMargins(14, 12, 14, 12)
        dcl.setSpacing(8)

        dc_hdr = QLabel("SIMULATED BOTTLENECK FINDINGS & RECOMMENDATIONS")
        dc_hdr.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        dcl.addWidget(dc_hdr)

        self.sim_findings_layout = QVBoxLayout()
        self.sim_findings_layout.setSpacing(6)
        self.lbl_findings_empty = QLabel("●  All simulated operational parameters within expected baseline variance.")
        self.lbl_findings_empty.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 11px;")
        self.sim_findings_layout.addWidget(self.lbl_findings_empty)
        dcl.addLayout(self.sim_findings_layout)
        dcl.addStretch()
        diag_rec_row.addWidget(diag_card, 1)

        # Right: Simulated Recovery Actions
        rec_card = QFrame()
        rec_card.setStyleSheet(card_style())
        rcl = QVBoxLayout(rec_card)
        rcl.setContentsMargins(14, 12, 14, 12)
        rcl.setSpacing(8)

        rc_hdr = QLabel("TEST SIMULATED RECOVERY ACTIONS")
        rc_hdr.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        rcl.addWidget(rc_hdr)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_trim = QPushButton("⚡ Simulate Memory Trim (-350 MB)")
        btn_trim.setStyleSheet(f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 8px; font-size: 10px;")
        btn_trim.clicked.connect(lambda: self._apply_sim_recovery("trim"))
        btn_row.addWidget(btn_trim)

        btn_throt = QPushButton("🛡️ Simulate CPU Throttle (-20%)")
        btn_throt.setStyleSheet(f"background: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; padding: 4px 8px; font-size: 10px;")
        btn_throt.clicked.connect(lambda: self._apply_sim_recovery("throttle"))
        btn_row.addWidget(btn_throt)

        rcl.addLayout(btn_row)

        self.sim_recovery_audit_lbl = QLabel("Select candidate actions to preview theoretical remediation outcome.")
        self.sim_recovery_audit_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.sim_recovery_audit_lbl.setWordWrap(True)
        rcl.addWidget(self.sim_recovery_audit_lbl)
        rcl.addStretch()
        diag_rec_row.addWidget(rec_card, 1)

        layout.addLayout(diag_rec_row)

        # 6. Candidate Processes Selection Table
        table_hdr = QHBoxLayout()
        table_lbl = QLabel("CANDIDATE APPLICATIONS TO HYPOTHETICALLY TERMINATE:")
        table_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        table_hdr.addWidget(table_lbl)
        table_hdr.addStretch()

        self.proc_count_badge = QLabel("0 CANDIDATES")
        self.proc_count_badge.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        table_hdr.addWidget(self.proc_count_badge)
        layout.addLayout(table_hdr)

        self.sim_table = QTableWidget()
        self.sim_table.setColumnCount(5)
        self.sim_table.setHorizontalHeaderLabels(["SIMULATE", "PID", "PROCESS NAME", "CPU %", "RAM (MB)"])
        self.sim_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.sim_table.verticalHeader().setVisible(False)
        self.sim_table.setShowGrid(False)
        self.sim_table.setMinimumHeight(240)
        layout.addWidget(self.sim_table)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _create_sim_card(self, title: str, main_val: str, sub_val: str, val_color: str = None):
        card = QFrame()
        card.setStyleSheet(card_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        layout.addWidget(t_lbl)

        m_lbl = QLabel(main_val)
        m_lbl.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        m_lbl.setStyleSheet(f"color: {val_color or COLORS['text_primary']};")
        layout.addWidget(m_lbl)

        s_lbl = QLabel(sub_val)
        s_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(s_lbl)

        return card, m_lbl, s_lbl

    def update_snapshot(self, snap: SystemSnapshot):
        if self._is_live_paused and self._current_snapshot is not None:
            return
        self._current_snapshot = snap
        if self.isVisible():
            self._run_simulation()

    def update_processes(self, procs: list[ProcessInfo]):
        if self._is_live_paused and self._current_processes:
            return
        # Filter idle process, sort by memory descending
        self._current_processes = [p for p in procs if p.pid != 0 and 'idle' not in p.name.lower()][:40]
        self.proc_count_badge.setText(f"{len(self._current_processes)} CANDIDATES")
        if self.isVisible():
            self._refresh_sim_table()
            self._run_simulation()
            self._dirty = False
        else:
            self._dirty = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._dirty:
            self._refresh_sim_table()
            self._run_simulation()
            self._dirty = False

    def _refresh_sim_table(self):
        self.sim_table.setUpdatesEnabled(False)
        self.sim_table.blockSignals(True)
        try:
            self.sim_table.setRowCount(len(self._current_processes))
            for row, p in enumerate(self._current_processes):
                cb = self.sim_table.cellWidget(row, 0)
                if not cb:
                    cb = QCheckBox()
                    self.sim_table.setCellWidget(row, 0, cb)
                cb.blockSignals(True)
                cb.setChecked(p.pid in self._selected_pids)
                cb.blockSignals(False)
                try:
                    cb.disconnect()
                except Exception:
                    pass
                cb.stateChanged.connect(lambda state, pid=p.pid: self._on_toggle(pid, state))

                # PID
                pid_item = self.sim_table.item(row, 1)
                if not pid_item:
                    pid_item = QTableWidgetItem()
                    pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    pid_item.setFont(QFont("Consolas", 10))
                    pid_item.setForeground(QColor(COLORS['text_muted']))
                    self.sim_table.setItem(row, 1, pid_item)
                pid_item.setText(str(p.pid))

                # Name
                name_item = self.sim_table.item(row, 2)
                if not name_item:
                    name_item = QTableWidgetItem()
                    name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                    self.sim_table.setItem(row, 2, name_item)
                name_item.setText(p.name)

                # CPU %
                cpu_item = self.sim_table.item(row, 3)
                if not cpu_item:
                    cpu_item = QTableWidgetItem()
                    cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    cpu_item.setFont(QFont("Consolas", 10))
                    self.sim_table.setItem(row, 3, cpu_item)
                cpu_item.setText(f"{p.cpu_percent:.1f}%")

                # Memory MB
                mem_item = self.sim_table.item(row, 4)
                if not mem_item:
                    mem_item = QTableWidgetItem()
                    mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    mem_item.setFont(QFont("Consolas", 10))
                    self.sim_table.setItem(row, 4, mem_item)
                mem_item.setText(f"{p.memory_mb:.0f} MB")
        finally:
            self.sim_table.blockSignals(False)
            self.sim_table.setUpdatesEnabled(True)

    def _on_toggle(self, pid: int, state: int):
        if state == 2:
            self._selected_pids.add(pid)
        else:
            self._selected_pids.discard(pid)
        self._run_simulation()

    def _select_top3(self):
        self._selected_pids.clear()
        for p in self._current_processes[:3]:
            self._selected_pids.add(p.pid)
        self._refresh_sim_table()
        self._run_simulation()

    def _select_browsers(self):
        self._selected_pids.clear()
        kw = ('chrome', 'msedge', 'edge', 'firefox', 'brave', 'opera')
        for p in self._current_processes:
            if any(k in p.name.lower() for k in kw):
                self._selected_pids.add(p.pid)
        self._refresh_sim_table()
        self._run_simulation()

    def _clear_selections(self):
        self._selected_pids.clear()
        self._refresh_sim_table()
        self._run_simulation()

    def _toggle_pause_baseline(self):
        self._is_live_paused = not self._is_live_paused
        if self._is_live_paused:
            self.btn_pause.setText("▶ Resume Live Baseline")
            self.mode_status_badge.setText("BASELINE FROZEN")
            self.mode_status_badge.setStyleSheet(
                f"color: {COLORS['amber']}; background: rgba(245, 158, 11, 0.12); "
                f"padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
            )
        else:
            self.btn_pause.setText("⏸ Pause Baseline")
            self.mode_status_badge.setText("SANDBOX ACTIVE")
            self.mode_status_badge.setStyleSheet(
                f"color: {COLORS['accent_lime']}; background: rgba(212, 255, 0, 0.12); "
                f"padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
            )

    def _reset_to_baseline(self):
        self._selected_pids.clear()
        self._cpu_offset = 0.0
        self._ram_offset = 0.0
        self._disk_io_mb = 0.0
        self._sim_recovery_applied.clear()
        self.slider_cpu.setValue(0)
        self.slider_ram.setValue(0)
        self.slider_disk.setValue(0)
        self.sim_recovery_audit_lbl.setText("Select candidate actions to preview theoretical remediation outcome.")
        self._refresh_sim_table()
        self._run_simulation()

    def _restore_defaults(self):
        self._reset_to_baseline()
        self._is_live_paused = False
        self.btn_pause.setText("⏸ Pause Baseline")
        self.mode_status_badge.setText("SANDBOX ACTIVE")
        self.mode_status_badge.setStyleSheet(
            f"color: {COLORS['accent_lime']}; background: rgba(212, 255, 0, 0.12); "
            f"padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
        )

    def _apply_condition_preset(self, cpu: float, ram: float, disk: float):
        self.slider_cpu.setValue(int(cpu))
        self.slider_ram.setValue(int(ram))
        self.slider_disk.setValue(int(disk))

    def _on_slider_changed(self):
        self._cpu_offset = float(self.slider_cpu.value())
        self._ram_offset = float(self.slider_ram.value())
        self._disk_io_mb = float(self.slider_disk.value())

        self.lbl_cpu_slider_val.setText(f"{self._cpu_offset:+.0f}%")
        self.lbl_ram_slider_val.setText(f"{self._ram_offset:+.0f}%")
        self.lbl_disk_slider_val.setText(f"{self._disk_io_mb:.0f} MB/s")

        self._run_simulation()

    def _apply_sim_recovery(self, action: str):
        if action not in self._sim_recovery_applied:
            self._sim_recovery_applied.append(action)
        if action == "trim":
            self.sim_recovery_audit_lbl.setText(
                "⚡ [SIMULATED ACTION APPLIED]: Simulated working-set memory trim (-350 MB). "
                "Projected RAM relief achieved in sandbox. (Zero changes to real processes)."
            )
        elif action == "throttle":
            self.sim_recovery_audit_lbl.setText(
                "🛡️ [SIMULATED ACTION APPLIED]: Simulated throttling background thread priority (-20% CPU). "
                "Processor contention mitigated in sandbox. (Zero changes to real processes)."
            )
        self._run_simulation()

    def _run_simulation(self):
        if not self._current_snapshot:
            return

        snap = self._current_snapshot
        selected_procs = [p for p in self._current_processes if p.pid in self._selected_pids]

        # Calculate process relief
        base_res = self.simulator.simulate_closing_processes(snap, selected_procs)

        # Apply synthetic slider offsets and simulated recovery actions
        extra_freed_ram_mb = 0.0
        extra_cpu_drop = 0.0

        if "trim" in self._sim_recovery_applied:
            extra_freed_ram_mb += 350.0
        if "throttle" in self._sim_recovery_applied:
            extra_cpu_drop += 20.0

        total_ram_mb = snap.memory.total / (1024 * 1024) if snap.memory.total > 0 else 16384.0
        recovery_ram_pct = (extra_freed_ram_mb / total_ram_mb) * 100.0 if total_ram_mb > 0 else 0.0

        sim_cpu = max(1.0, min(100.0, base_res.simulated_cpu + self._cpu_offset - extra_cpu_drop))
        sim_ram = max(5.0, min(100.0, base_res.simulated_mem_percent + self._ram_offset - recovery_ram_pct))
        total_freed_mb = base_res.freed_memory_mb + extra_freed_ram_mb

        # Update Card 1: CPU
        self.sim_cpu_val.setText(f"{sim_cpu:.1f}%")
        cpu_diff = sim_cpu - snap.cpu.overall_percent
        if cpu_diff < 0:
            self.sim_cpu_sub.setText(f"Baseline: {snap.cpu.overall_percent:.1f}% ({cpu_diff:.1f}% relief)")
        elif cpu_diff > 0:
            self.sim_cpu_sub.setText(f"Baseline: {snap.cpu.overall_percent:.1f}% (+{cpu_diff:.1f}% load)")
        else:
            self.sim_cpu_sub.setText(f"Baseline: {snap.cpu.overall_percent:.1f}% (No change)")

        # Update Card 2: RAM
        self.sim_ram_val.setText(f"{sim_ram:.1f}%")
        ram_diff = sim_ram - snap.memory.percent
        if ram_diff < 0:
            self.sim_ram_sub.setText(f"Baseline: {snap.memory.percent:.1f}% ({ram_diff:.1f}% relief)")
        elif ram_diff > 0:
            self.sim_ram_sub.setText(f"Baseline: {snap.memory.percent:.1f}% (+{ram_diff:.1f}% pressure)")
        else:
            self.sim_ram_sub.setText(f"Baseline: {snap.memory.percent:.1f}% (No change)")

        # Update Card 3: Reclaimed RAM
        self.sim_freed_val.setText(f"+{total_freed_mb:.0f} MB")
        self.sim_freed_sub.setText(f"{len(selected_procs)} processes modeled")

        # Construct synthetic snapshot for diagnosis and health calculation
        from copy import deepcopy
        sim_snap = deepcopy(snap)
        sim_snap.cpu.overall_percent = sim_cpu
        sim_snap.memory.percent = sim_ram
        sim_snap.memory.used = int((sim_ram / 100.0) * snap.memory.total)
        sim_snap.memory.available = max(0, snap.memory.total - sim_snap.memory.used)
        if self._disk_io_mb > 0:
            bytes_sec = self._disk_io_mb * 1024 * 1024
            sim_snap.disk.read_bytes_per_sec = bytes_sec * 0.5
            sim_snap.disk.write_bytes_per_sec = bytes_sec * 0.5

        # Compute simulated health
        sim_health = self.simulator.analysis.calculate_health_score(sim_snap)
        orig_health = self.simulator.analysis.calculate_health_score(snap).total_score
        h_gain = sim_health.total_score - orig_health

        # Update Card 4: Health
        self.sim_health_val.setText(f"{sim_health.total_score:.0f}/100")
        if h_gain >= 0:
            self.sim_health_sub.setText(f"Potential Gain: +{h_gain:.1f} pts (Swap: {base_res.swap_relief_level} Relief)")
        else:
            self.sim_health_sub.setText(f"Load Impact: {h_gain:.1f} pts (Elevated stress)")

        # Compute simulated diagnoses & recommendations
        remaining_procs = [p for p in self._current_processes if p.pid not in self._selected_pids]
        sim_diags = self.simulator.analysis.diagnose(sim_snap, remaining_procs)
        sim_recs = self.recommender.generate(sim_diags, sim_snap, remaining_procs)

        # Clear simulated findings layout
        while self.sim_findings_layout.count():
            item = self.sim_findings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        non_healthy = [d for d in sim_diags if getattr(d, 'severity', '').lower() != 'healthy']
        if not non_healthy:
            ok_lbl = QLabel("●  All simulated operational parameters within expected baseline variance.")
            ok_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 11px;")
            self.sim_findings_layout.addWidget(ok_lbl)
        else:
            for diag in non_healthy[:3]:
                d_row = QHBoxLayout()
                badge = QLabel(diag.severity.upper())
                badge.setStyleSheet(severity_badge_style(diag.severity))
                d_row.addWidget(badge)
                t_lbl = QLabel(diag.title)
                t_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
                d_row.addWidget(t_lbl, 1)
                self.sim_findings_layout.addLayout(d_row)

            if sim_recs:
                rec_action = getattr(sim_recs[0], 'action', getattr(sim_recs[0], 'title', 'Review suggested action'))
                rec_type = getattr(sim_recs[0], 'action_type', 'inspect')
                rec_lbl = QLabel(f"<b>Recommendation:</b> {rec_action} ({rec_type})")
                rec_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 11px; margin-top: 4px;")
                self.sim_findings_layout.addWidget(rec_lbl)


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
            "Workload profiles adapt OSD's anomaly thresholds, alerting sensitivity, and background polling cadence "
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

    def __init__(self, chat_engine: AskOSDEngine, simulator: WhatIfSimulator,
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

        self.ask_tab = AskOSDTab(chat_engine)
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
