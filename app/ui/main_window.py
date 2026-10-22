"""
Main Window — Central window with 8-module grouped navigation, stacked pages,
and integrated OSD intelligence engines.
Art-directed shell with compact sidebar, custom wordmark, and persistent status telemetry.
"""
import time
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, sidebar_button_style, card_style, severity_badge_style
from app.ui.pages.overview_page import OverviewPage
from app.ui.pages.processes_page import ProcessesPage
from app.ui.pages.performance_page import PerformancePage
from app.ui.pages.diagnosis_page import DiagnosisPage
from app.ui.pages.intelligence_page import IntelligencePage
from app.ui.pages.recovery_page import RecoveryPage
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.settings_page import SettingsPage

from app.monitoring.system_monitor import SystemMonitor
from app.monitoring.behavior_monitor import ProcessBehaviorMonitor
from app.analysis.engine import AnalysisEngine, Thresholds
from app.analysis.predictive_engine import PredictiveEngine
from app.analysis.simulator import WhatIfSimulator
from app.recommendations.engine import RecommendationEngine
from app.recommendations.recovery_advisor import RecoveryAdvisor
from app.assistant.chat_engine import AskOSDEngine, AskOSenseEngine
from app.profiles.profile_manager import ProfileManager
from app.database.db_manager import DatabaseManager
from app.workers.monitor_worker import MonitorWorker, DiagnosisWorker


class SidebarButton(QPushButton):
    """Linear-style restrained sidebar navigation item."""

    def __init__(self, text: str, icon_str: str = "", parent=None):
        display = f"  {icon_str}   {text}" if icon_str else f"  {text}"
        super().__init__(display, parent)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(sidebar_button_style(False))
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        self.setStyleSheet(sidebar_button_style(active))

    def enterEvent(self, event):
        if not self._active:
            self.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_card_hover']}; "
                f"color: {COLORS['text_primary']}; border: none; border-left: 3px solid transparent; "
                f"padding: 8px 14px; text-align: left; font-size: 13px; font-weight: 500; }}"
            )
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(sidebar_button_style(self._active))
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    """OSD application window with 8 functional modules and bottom status telemetry."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OSD — System Telemetry & Recovery")
        self.setMinimumSize(1150, 750)
        self.resize(1340, 860)

        # Initialize database and telemetry collection
        self.db = DatabaseManager()
        self.monitor = SystemMonitor()

        # Load thresholds from settings
        thresholds = Thresholds()
        try:
            t_cpu_w = self.db.get_setting('threshold_cpu_warning', '')
            t_cpu_c = self.db.get_setting('threshold_cpu_critical', '')
            t_mem_w = self.db.get_setting('threshold_memory_warning', '')
            t_mem_c = self.db.get_setting('threshold_memory_critical', '')
            if t_cpu_w: thresholds.cpu_warning = float(t_cpu_w)
            if t_cpu_c: thresholds.cpu_critical = float(t_cpu_c)
            if t_mem_w: thresholds.memory_warning = float(t_mem_w)
            if t_mem_c: thresholds.memory_critical = float(t_mem_c)
        except Exception:
            pass

        # Instantiate Intelligence & Analysis Engines
        self.analysis = AnalysisEngine(thresholds)
        self.recommender = RecommendationEngine()
        self.predictive_engine = PredictiveEngine()
        self.behavior_monitor = ProcessBehaviorMonitor()
        self.recovery_advisor = RecoveryAdvisor(self.monitor, self.analysis, self.db)
        self.chat_engine = AskOSDEngine(self.monitor, self.analysis, self.predictive_engine, self.db)
        self.simulator = WhatIfSimulator(self.analysis)
        self.profile_manager = ProfileManager(self.db)

        # Sync thresholds from active workload profile
        active_prof = self.profile_manager.get_active_profile()
        if active_prof:
            self.analysis.thresholds.cpu_warning = active_prof.cpu_warning
            self.analysis.thresholds.cpu_critical = active_prof.cpu_critical
            self.analysis.thresholds.memory_warning = active_prof.memory_warning
            self.analysis.thresholds.memory_critical = active_prof.memory_critical

        self._setup_ui()
        self._start_monitoring()
        self._start_local_companion()

    def _setup_ui(self):
        # Central widget with outer vertical layout (body + bottom status bar)
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main horizontal split: Sidebar on left, Pages on right
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # --- Refined Compact Sidebar ---
        sidebar = QFrame()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet(
            f"background-color: {COLORS['bg_sidebar']}; "
            f"border-right: 1px solid {COLORS['border_subtle']};"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 14)
        sidebar_layout.setSpacing(2)

        # Wordmark & Bespoke Icon
        wordmark_box = QVBoxLayout()
        wordmark_box.setSpacing(3)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)

        # Reticle / Waveform icon badge
        icon_badge = QLabel("⌁")
        icon_badge.setFixedSize(22, 22)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            f"background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
            f"border-radius: 4px; font-weight: 900; font-size: 13px; font-family: 'Consolas', monospace;"
        )
        logo_row.addWidget(icon_badge)

        wordmark = QLabel("OSD")
        wordmark.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        wordmark.setStyleSheet(
            f"color: {COLORS['text_primary']}; letter-spacing: 2px; font-weight: 800;"
        )
        logo_row.addWidget(wordmark)
        logo_row.addStretch()
        wordmark_box.addLayout(logo_row)

        sub_tag = QLabel("SYSTEM TELEMETRY")
        sub_tag.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 1.2px; font-family: 'Consolas', monospace; padding-left: 30px;"
        )
        wordmark_box.addWidget(sub_tag)

        sidebar_layout.addLayout(wordmark_box)
        sidebar_layout.addSpacing(12)

        # Subtle thin separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border_subtle']};")
        sidebar_layout.addWidget(sep)
        sidebar_layout.addSpacing(8)

        # Navigation label
        nav_lbl = QLabel("WORKSPACE")
        nav_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 1px; font-family: 'Consolas', monospace; padding: 4px 10px;"
        )
        sidebar_layout.addWidget(nav_lbl)

        # 8 Grouped Navigation Items (as specified in Section 4)
        nav_items = [
            ("Overview", "▥"),
            ("Processes", "▦"),
            ("Performance", "📈"),
            ("Diagnosis", "⌕"),
            ("Intelligence", "🧠"),
            ("Recovery", "🛡"),
            ("History", "⏳"),
            ("Settings", "⚙"),
        ]

        self.nav_buttons: list[SidebarButton] = []
        for text, icon in nav_items:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda checked, t=text: self._navigate(t))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Understated status indicator in sidebar
        status_box = QFrame()
        status_box.setStyleSheet(
            f"background-color: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; "
            f"border-radius: 4px; padding: 6px 8px;"
        )
        sbl = QHBoxLayout(status_box)
        sbl.setContentsMargins(4, 2, 4, 2)
        sbl.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 8px;")
        sbl.addWidget(dot)

        self.engine_state_lbl = QLabel("ENGINE ONLINE")
        self.engine_state_lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        sbl.addWidget(self.engine_state_lbl)
        sbl.addStretch()
        sidebar_layout.addWidget(status_box)

        body_layout.addWidget(sidebar)

        # --- Stacked Pages ---
        self.pages = QStackedWidget()
        self.pages.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        # 0: Overview
        self.overview_page = OverviewPage(self.monitor, self.db)
        self.overview_page.diagnose_requested.connect(self._run_diagnosis)

        # 1: Processes
        self.processes_page = ProcessesPage(self.monitor)

        # 2: Performance
        self.performance_page = PerformancePage()

        # 3: Diagnosis
        self.diagnosis_page = DiagnosisPage(self.monitor, self.analysis, self.recommender, self.db)

        # 4: Intelligence (Copilot, Predictive, Simulator, Profiles)
        self.intelligence_page = IntelligencePage(
            self.chat_engine, self.simulator, self.monitor, self.profile_manager
        )
        self.intelligence_page.profile_changed.connect(self._on_profile_changed)

        # 5: Recovery
        self.recovery_page = RecoveryPage(self.recovery_advisor)
        self.recovery_page.recovery_performed.connect(self._on_recovery_performed)

        # 6: History
        self.history_page = HistoryPage(self.db)

        # 7: Settings
        self.settings_page = SettingsPage(self.db)
        self.settings_page.settings_changed.connect(self._apply_settings)

        self.pages.addWidget(self.overview_page)       # 0
        self.pages.addWidget(self.processes_page)      # 1
        self.pages.addWidget(self.performance_page)    # 2
        self.pages.addWidget(self.diagnosis_page)      # 3
        self.pages.addWidget(self.intelligence_page)   # 4
        self.pages.addWidget(self.recovery_page)       # 5
        self.pages.addWidget(self.history_page)        # 6
        self.pages.addWidget(self.settings_page)       # 7

        body_layout.addWidget(self.pages)
        root_layout.addWidget(body_widget, 1)

        # --- Refined Bottom Status Bar (Data Freshness & Monitoring State) ---
        status_bar = QFrame()
        status_bar.setFixedHeight(28)
        status_bar.setStyleSheet(
            f"background-color: {COLORS['bg_sidebar']}; border-top: 1px solid {COLORS['border_subtle']}; "
            f"padding: 0 16px;"
        )
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(12, 0, 12, 0)
        sb_layout.setSpacing(14)

        # Left status items
        self.sb_state_lbl = QLabel("●  TELEMETRY STREAM: ACTIVE")
        self.sb_state_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        sb_layout.addWidget(self.sb_state_lbl)

        self.sb_cadence_lbl = QLabel("CADENCE: 2.0s")
        self.sb_cadence_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        sb_layout.addWidget(self.sb_cadence_lbl)

        self.sb_procs_lbl = QLabel("TASKS: --")
        self.sb_procs_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        sb_layout.addWidget(self.sb_procs_lbl)

        sb_layout.addStretch()

        # Center / Right items
        self.sb_fresh_lbl = QLabel("DATA: NOMINAL")
        self.sb_fresh_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px; font-family: 'Consolas', monospace;")
        sb_layout.addWidget(self.sb_fresh_lbl)

        self.sb_sync_lbl = QLabel("LAST SYNC: --:--:--")
        self.sb_sync_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        sb_layout.addWidget(self.sb_sync_lbl)

        self.sb_prof_lbl = QLabel("PROFILE: BALANCED")
        self.sb_prof_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        sb_layout.addWidget(self.sb_prof_lbl)

        root_layout.addWidget(status_bar)

        # Initial navigation
        initial_page = self.db.get_setting('startup_page', 'Overview')
        valid_pages = [item[0] for item in nav_items]
        self._navigate(initial_page if initial_page in valid_pages else "Overview")

    def _navigate(self, page_name: str):
        page_map = {
            "Overview": 0,
            "Processes": 1,
            "Performance": 2,
            "Diagnosis": 3,
            "Intelligence": 4,
            "Recovery": 5,
            "History": 6,
            "Settings": 7,
        }
        idx = page_map.get(page_name, 0)
        self.pages.setCurrentIndex(idx)

        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == idx)

        # Trigger page specific refresh on display
        if page_name == "History":
            if time.time() - getattr(self.history_page, "_last_refresh_time", 0) > 3.0:
                self.history_page.refresh()
        elif page_name == "Intelligence":
            self.intelligence_page.refresh_profiles()
        elif page_name == "Settings":
            self.settings_page.load_settings()

    def _start_monitoring(self):
        active_prof = self.profile_manager.get_active_profile()
        interval = active_prof.refresh_interval_sec if active_prof else float(self.db.get_setting('refresh_interval', '2.0'))
        if active_prof:
            self.sb_prof_lbl.setText(f"PROFILE: {active_prof.name.upper()}")

        self.monitor_worker = MonitorWorker(
            self.monitor, self.analysis, self.recommender, self.db,
            self.predictive_engine, self.behavior_monitor, self.recovery_advisor
        )
        self.monitor_worker.set_interval(interval)
        self.monitor_worker.snapshot_ready.connect(self._on_snapshot)
        self.monitor_worker.processes_ready.connect(self._on_processes)
        self.monitor_worker.health_ready.connect(self._on_health)
        self.monitor_worker.diagnoses_ready.connect(self._on_diagnoses)
        self.monitor_worker.recommendations_ready.connect(self._on_recommendations)
        self.monitor_worker.predictions_ready.connect(self._on_predictions)
        self.monitor_worker.behavior_alerts_ready.connect(self._on_behavior_alerts)
        self.monitor_worker.recovery_plans_ready.connect(self._on_recovery_plans)
        self.monitor_worker.error_occurred.connect(self._on_monitor_error)
        self.monitor_worker.start()

    def _on_snapshot(self, snapshot):
        self.overview_page.update_snapshot(snapshot)
        self.performance_page.update_snapshot(snapshot)
        self.intelligence_page.update_snapshot(snapshot)

        # Update bottom status bar
        cur_time = time.strftime('%H:%M:%S')
        self.sb_sync_lbl.setText(f"LAST SYNC: {cur_time}")
        self.sb_procs_lbl.setText(f"TASKS: {snapshot.process_count}")

    def _on_processes(self, processes):
        self.processes_page.update_processes(processes)
        self.overview_page.update_top_processes(processes[:5])
        self.intelligence_page.update_processes(processes)

    def _on_health(self, health):
        self.overview_page.update_health(health)
        if health.total_score >= 80:
            self.sb_fresh_lbl.setText("DATA: NOMINAL")
            self.sb_fresh_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 10px; font-family: 'Consolas', monospace;")
        elif health.total_score >= 60:
            self.sb_fresh_lbl.setText("DATA: ELEVATED LOAD")
            self.sb_fresh_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 10px; font-family: 'Consolas', monospace;")
        else:
            self.sb_fresh_lbl.setText("DATA: PRESSURE DETECTED")
            self.sb_fresh_lbl.setStyleSheet(f"color: {COLORS['amber']}; font-size: 10px; font-family: 'Consolas', monospace;")

    def _on_diagnoses(self, diagnoses):
        self.overview_page.update_diagnoses(diagnoses)
        self.diagnosis_page.update_live_diagnoses(diagnoses)

    def _on_recommendations(self, recommendations):
        pass

    def _on_predictions(self, alerts):
        self.intelligence_page.update_alerts(alerts)

    def _on_recovery_plans(self, plans):
        self.recovery_page.update_plans(plans)
        self.overview_page.update_alert_count(len(plans))

    def _on_behavior_alerts(self, alerts):
        for a in alerts:
            try:
                self.db.save_behavior_alert(
                    pid=a.pid,
                    process_name=a.process_name,
                    alert_type=a.alert_type,
                    description=a.description,
                    severity=a.severity
                )
            except Exception:
                pass

    def _on_recovery_performed(self):
        """Called when a recovery action has completed."""
        self.history_page.refresh()

    def _on_profile_changed(self, profile_name: str):
        """Update analysis thresholds and worker interval when workload profile changes."""
        prof = self.profile_manager.get_active_profile()
        if prof:
            self.analysis.thresholds.cpu_warning = prof.cpu_warning
            self.analysis.thresholds.cpu_critical = prof.cpu_critical
            self.analysis.thresholds.memory_warning = prof.memory_warning
            self.analysis.thresholds.memory_critical = prof.memory_critical
            self.monitor_worker.set_interval(prof.refresh_interval_sec)
            self.sb_cadence_lbl.setText(f"CADENCE: {prof.refresh_interval_sec:.1f}s")
            self.sb_prof_lbl.setText(f"PROFILE: {prof.name.upper()}")

    def _on_monitor_error(self, error_msg):
        print(f"[OSD] Monitor error: {error_msg}")

    def _run_diagnosis(self):
        """Triggered by 'Diagnose My PC' button."""
        self._navigate("Diagnosis")
        self.diagnosis_page.run_full_diagnosis()

    def _apply_settings(self):
        """Called when settings are changed in SettingsPage."""
        try:
            interval = float(self.db.get_setting('refresh_interval', '2.0'))
            self.monitor_worker.set_interval(interval)
            self.sb_cadence_lbl.setText(f"CADENCE: {interval:.1f}s")

            # Update thresholds
            thresholds = self.analysis.thresholds
            t = self.db.get_setting('threshold_cpu_warning', '')
            if t: thresholds.cpu_warning = float(t)
            t = self.db.get_setting('threshold_cpu_critical', '')
            if t: thresholds.cpu_critical = float(t)
            t = self.db.get_setting('threshold_memory_warning', '')
            if t: thresholds.memory_warning = float(t)
            t = self.db.get_setting('threshold_memory_critical', '')
            if t: thresholds.memory_critical = float(t)
        except Exception as e:
            print(f"[OSD] Error applying settings: {e}")

    def _start_local_companion(self):
        """Start local companion loopback service for browser integration."""
        self.agent = None
        try:
            from osd_core.agent.server import OSDAgent
            self.agent = OSDAgent(host="127.0.0.1", port=8080)
            self.agent.start()
            print("[OSD Desktop] Embedded companion server active on http://127.0.0.1:8080")
        except OSError:
            print("[OSD Desktop] Local Companion port 8080 already bound; existing service retained.")
        except Exception as e:
            print(f"[OSD Desktop] Embedded companion server skipped: {e}")

    def closeEvent(self, event):
        """Clean and safe shutdown of all background threads and resources."""
        # 1. Stop diagnosis worker if active
        if hasattr(self, 'diagnosis_page'):
            try:
                self.diagnosis_page.stop()
            except Exception:
                pass

        # 2. Stop monitor worker gracefully, terminate if unresponsive
        if hasattr(self, 'monitor_worker') and self.monitor_worker:
            try:
                self.monitor_worker.stop()
                if not self.monitor_worker.wait(2000):
                    self.monitor_worker.terminate()
                    self.monitor_worker.wait(1000)
            except Exception:
                pass

        # 3. Stop embedded companion server if active
        if hasattr(self, 'agent') and self.agent:
            try:
                self.agent.stop()
            except Exception:
                pass

        # 4. Clean up database history
        try:
            self.db.cleanup_old_data()
        except Exception:
            pass
        event.accept()
