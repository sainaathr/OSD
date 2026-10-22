"""
Settings Page — Application Preferences & Architecture Telemetry
Engine cadence, alert thresholds, data retention policies, and local architecture.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QGroupBox, QFrame, QScrollArea, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style, panel_alt_style
from app.ui.components import PageHeader
from app.database.db_manager import DatabaseManager


class SettingsPage(QWidget):
    """Refined Settings and Developer Preferences page."""

    settings_changed = Signal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        self.load_settings()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        eyebrow = QLabel("SYSTEM PREFERENCES")
        eyebrow.setStyleSheet(
            f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; font-family: 'Consolas', monospace;"
        )
        title_box.addWidget(eyebrow)

        title = QLabel("Settings & Architecture")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel("Configure real-time monitoring cadence, diagnostic thresholds, and retention policies.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)

        header_row.addLayout(title_box, 1)

        # Header Buttons
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.setFixedHeight(36)
        reset_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; color: {COLORS['text_primary']}; }}"
        )
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_defaults)
        header_row.addWidget(reset_btn)

        save_btn = QPushButton("Save Preferences")
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
            f"border: 1px solid {COLORS['accent_lime']}; border-radius: 6px; padding: 6px 18px; font-weight: 700; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_lime_dim']}; }}"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        header_row.addWidget(save_btn)

        main_layout.addLayout(header_row)

        # === Group 1: Monitoring Engine Preferences ===
        mon_card = QFrame()
        mon_card.setStyleSheet(card_style())
        mon_layout = QGridLayout(mon_card)
        mon_layout.setContentsMargins(18, 16, 18, 16)
        mon_layout.setSpacing(12)

        g1_title = QLabel("MONITORING ENGINE CADENCE & RETENTION")
        g1_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        mon_layout.addWidget(g1_title, 0, 0, 1, 2)

        mon_layout.addWidget(QLabel("Telemetry Refresh Interval:"), 1, 0)
        self.interval_combo = QComboBox()
        self.interval_combo.addItems([
            "1.0 second (Realtime Precision)",
            "1.5 seconds",
            "2.0 seconds (Recommended Balanced)",
            "3.0 seconds",
            "5.0 seconds (Low Power)"
        ])
        mon_layout.addWidget(self.interval_combo, 1, 1)

        mon_layout.addWidget(QLabel("Startup Dashboard Module:"), 2, 0)
        self.startup_combo = QComboBox()
        self.startup_combo.addItems(["Overview", "Processes", "Performance", "Diagnosis", "Intelligence", "Recovery", "History"])
        mon_layout.addWidget(self.startup_combo, 2, 1)

        mon_layout.addWidget(QLabel("SQLite Telemetry Retention:"), 3, 0)
        self.retention_combo = QComboBox()
        self.retention_combo.addItems(["24 Hours", "3 Days", "7 Days (Recommended)", "14 Days", "30 Days"])
        mon_layout.addWidget(self.retention_combo, 3, 1)

        main_layout.addWidget(mon_card)

        # === Group 2: Diagnostic Heuristic Thresholds ===
        thresh_card = QFrame()
        thresh_card.setStyleSheet(card_style())
        thresh_layout = QGridLayout(thresh_card)
        thresh_layout.setContentsMargins(18, 16, 18, 16)
        thresh_layout.setSpacing(12)

        g2_title = QLabel("HEURISTIC BOTTLENECK THRESHOLDS")
        g2_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        thresh_layout.addWidget(g2_title, 0, 0, 1, 4)

        # CPU
        thresh_layout.addWidget(QLabel("CPU Warning Threshold (%):"), 1, 0)
        self.cpu_warn_spin = QSpinBox()
        self.cpu_warn_spin.setRange(40, 95)
        thresh_layout.addWidget(self.cpu_warn_spin, 1, 1)

        thresh_layout.addWidget(QLabel("CPU Critical Threshold (%):"), 1, 2)
        self.cpu_crit_spin = QSpinBox()
        self.cpu_crit_spin.setRange(50, 99)
        thresh_layout.addWidget(self.cpu_crit_spin, 1, 3)

        # Memory
        thresh_layout.addWidget(QLabel("RAM Warning Threshold (%):"), 2, 0)
        self.mem_warn_spin = QSpinBox()
        self.mem_warn_spin.setRange(50, 95)
        thresh_layout.addWidget(self.mem_warn_spin, 2, 1)

        thresh_layout.addWidget(QLabel("RAM Critical Threshold (%):"), 2, 2)
        self.mem_crit_spin = QSpinBox()
        self.mem_crit_spin.setRange(60, 99)
        thresh_layout.addWidget(self.mem_crit_spin, 2, 3)

        # Swap / Pagefile
        thresh_layout.addWidget(QLabel("Pagefile/Swap Warning (%):"), 3, 0)
        self.swap_warn_spin = QSpinBox()
        self.swap_warn_spin.setRange(20, 90)
        thresh_layout.addWidget(self.swap_warn_spin, 3, 1)

        thresh_layout.addWidget(QLabel("Pagefile/Swap Critical (%):"), 3, 2)
        self.swap_crit_spin = QSpinBox()
        self.swap_crit_spin.setRange(40, 99)
        thresh_layout.addWidget(self.swap_crit_spin, 3, 3)

        # Disk
        thresh_layout.addWidget(QLabel("Storage Volume Warning (%):"), 4, 0)
        self.disk_warn_spin = QSpinBox()
        self.disk_warn_spin.setRange(50, 95)
        thresh_layout.addWidget(self.disk_warn_spin, 4, 1)

        thresh_layout.addWidget(QLabel("Storage Volume Critical (%):"), 4, 2)
        self.disk_crit_spin = QSpinBox()
        self.disk_crit_spin.setRange(60, 99)
        thresh_layout.addWidget(self.disk_crit_spin, 4, 3)

        main_layout.addWidget(thresh_card)

        # === Group 3: Privacy & Local Inference ===
        priv_card = QFrame()
        priv_card.setStyleSheet(card_style())
        pl = QVBoxLayout(priv_card)
        pl.setContentsMargins(18, 16, 18, 16)
        pl.setSpacing(10)

        g3_title = QLabel("LOCAL PRIVACY & COPILOT ENGINE")
        g3_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        pl.addWidget(g3_title)

        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("Explanation Engine Mode:"))
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems([
            "Offline Heuristic Rule Engine (Zero-Network, Local-First, Private)",
            "Custom LLM API (Requires Custom API Key)"
        ])
        self.ai_mode_combo.currentIndexChanged.connect(self._on_ai_mode_changed)
        p_row.addWidget(self.ai_mode_combo, 1)
        pl.addLayout(p_row)

        self.api_key_frame = QWidget()
        api_layout = QHBoxLayout(self.api_key_frame)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.addWidget(QLabel("Custom API Endpoint / Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("https://api.openai.com/v1 or local http://localhost:11434")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_input, 1)
        self.api_key_frame.setVisible(False)
        pl.addWidget(self.api_key_frame)

        privacy_note = QLabel(
            "🔒 <b>LOCAL-FIRST ARCHITECTURE:</b> OSD runs 100% on-device. No telemetry metrics, process names, or hardware IDs "
            "are transmitted to external servers. All historical telemetry is stored in your local SQLite database."
        )
        privacy_note.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 11px;")
        privacy_note.setWordWrap(True)
        pl.addWidget(privacy_note)

        main_layout.addWidget(priv_card)

        # === Group 4: Architecture Specifications ===
        about_card = QFrame()
        about_card.setStyleSheet(card_style())
        al = QVBoxLayout(about_card)
        al.setContentsMargins(18, 16, 18, 16)
        al.setSpacing(8)

        g4_title = QLabel("ABOUT OSD")
        g4_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        al.addWidget(g4_title)

        about_title = QLabel("OSD — Operating System Diagnostics & Safe Recovery Assistant")
        about_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        about_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        al.addWidget(about_title)

        about_desc = QLabel(
            "Architecture: Modular Python 3.12 / PySide6 / psutil / SQLite3 / Matplotlib / Linear Art Direction\n"
            "Status: Local Engine Active • Safe Recovery Verification Protocol Enabled\n"
            "Mission: Transform opaque operating system metrics into clear explanations, probable root causes, and verified recovery actions."
        )
        about_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: 'Consolas', monospace;")
        al.addWidget(about_desc)

        main_layout.addWidget(about_card)
        main_layout.addStretch()

        scroll.setWidget(content)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _on_ai_mode_changed(self, index: int):
        self.api_key_frame.setVisible(index == 1)

    def load_settings(self):
        """Load values from DatabaseManager settings table."""
        interval = self.db.get_setting('refresh_interval', '2.0')
        interval_map = {'1.0': 0, '1.5': 1, '2.0': 2, '3.0': 3, '5.0': 4}
        self.interval_combo.setCurrentIndex(interval_map.get(interval, 2))

        startup = self.db.get_setting('startup_page', 'Overview')
        page_names = ["Overview", "Processes", "Performance", "Diagnosis", "Intelligence", "Recovery", "History"]
        if startup in page_names:
            self.startup_combo.setCurrentIndex(page_names.index(startup))

        retention = self.db.get_setting('history_retention_hours', '168')
        ret_map = {'24': 0, '72': 1, '168': 2, '336': 3, '720': 4}
        self.retention_combo.setCurrentIndex(ret_map.get(retention, 2))

        self.cpu_warn_spin.setValue(int(float(self.db.get_setting('threshold_cpu_warning', '75'))))
        self.cpu_crit_spin.setValue(int(float(self.db.get_setting('threshold_cpu_critical', '90'))))
        self.mem_warn_spin.setValue(int(float(self.db.get_setting('threshold_memory_warning', '80'))))
        self.mem_crit_spin.setValue(int(float(self.db.get_setting('threshold_memory_critical', '92'))))
        self.swap_warn_spin.setValue(int(float(self.db.get_setting('threshold_swap_warning', '50'))))
        self.swap_crit_spin.setValue(int(float(self.db.get_setting('threshold_swap_critical', '80'))))
        self.disk_warn_spin.setValue(int(float(self.db.get_setting('threshold_disk_warning', '85'))))
        self.disk_crit_spin.setValue(int(float(self.db.get_setting('threshold_disk_critical', '95'))))

        ai_mode = self.db.get_setting('ai_explanation_mode', 'offline')
        self.ai_mode_combo.setCurrentIndex(1 if ai_mode == 'custom' else 0)
        self.api_key_input.setText(self.db.get_setting('ai_api_key', ''))

    def _save_settings(self):
        """Persist settings to database and emit signal."""
        intervals = ['1.0', '1.5', '2.0', '3.0', '5.0']
        chosen_interval = intervals[self.interval_combo.currentIndex()]
        self.db.set_setting('refresh_interval', chosen_interval)

        self.db.set_setting('startup_page', self.startup_combo.currentText())

        retention_hours = ['24', '72', '168', '336', '720']
        chosen_ret = retention_hours[self.retention_combo.currentIndex()]
        self.db.set_setting('history_retention_hours', chosen_ret)

        self.db.set_setting('threshold_cpu_warning', str(self.cpu_warn_spin.value()))
        self.db.set_setting('threshold_cpu_critical', str(self.cpu_crit_spin.value()))
        self.db.set_setting('threshold_memory_warning', str(self.mem_warn_spin.value()))
        self.db.set_setting('threshold_memory_critical', str(self.mem_crit_spin.value()))
        self.db.set_setting('threshold_swap_warning', str(self.swap_warn_spin.value()))
        self.db.set_setting('threshold_swap_critical', str(self.swap_crit_spin.value()))
        self.db.set_setting('threshold_disk_warning', str(self.disk_warn_spin.value()))
        self.db.set_setting('threshold_disk_critical', str(self.disk_crit_spin.value()))

        mode = 'custom' if self.ai_mode_combo.currentIndex() == 1 else 'offline'
        self.db.set_setting('ai_explanation_mode', mode)
        self.db.set_setting('ai_api_key', self.api_key_input.text().strip())

        self.settings_changed.emit()
        QMessageBox.information(self, "Preferences Saved", "Settings updated successfully!")

    def _reset_defaults(self):
        """Reset values to safe defaults."""
        self.interval_combo.setCurrentIndex(2)  # 2.0s
        self.startup_combo.setCurrentIndex(0)   # Overview
        self.retention_combo.setCurrentIndex(2) # 7 Days
        self.cpu_warn_spin.setValue(75)
        self.cpu_crit_spin.setValue(90)
        self.mem_warn_spin.setValue(80)
        self.mem_crit_spin.setValue(92)
        self.swap_warn_spin.setValue(50)
        self.swap_crit_spin.setValue(80)
        self.disk_warn_spin.setValue(85)
        self.disk_crit_spin.setValue(95)
        self.ai_mode_combo.setCurrentIndex(0)
        self.api_key_input.clear()
