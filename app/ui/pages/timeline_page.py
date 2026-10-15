"""
System Time Machine Page — Interactive historical timeline, session comparisons,
and before-and-after recovery outcomes.
"""
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style, severity_badge_style
from app.utils.formatting import format_timestamp, format_speed
from app.database.db_manager import DatabaseManager


class TimelinePage(QWidget):
    """System Time Machine view for trend history and session comparisons."""

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_hours = 1.0
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
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("⏳ System Time Machine")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel(
            "Reconstruct system history across sessions. Compare performance before and after recovery actions."
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)
        header.addLayout(title_box)
        header.addStretch()

        # Range filter
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"])
        self.range_combo.setFixedHeight(34)
        self.range_combo.currentIndexChanged.connect(self._on_range_changed)
        header.addWidget(self.range_combo)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 4px 14px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; }}"
        )
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        self.layout_main.addLayout(header)

        # Session Metrics Card
        self.session_card = QFrame()
        self.session_card.setStyleSheet(card_style())
        sc_layout = QGridLayout(self.session_card)
        sc_layout.setContentsMargins(16, 14, 16, 14)
        sc_layout.setSpacing(12)

        self.avg_cpu_lbl = QLabel("Avg CPU: --")
        self.peak_cpu_lbl = QLabel("Peak CPU: --")
        self.avg_mem_lbl = QLabel("Avg RAM: --")
        self.peak_mem_lbl = QLabel("Peak RAM: --")
        self.avg_health_lbl = QLabel("Avg Health: --")
        self.actions_count_lbl = QLabel("Verified Actions: --")

        for lbl in [self.avg_cpu_lbl, self.peak_cpu_lbl, self.avg_mem_lbl, self.peak_mem_lbl, self.avg_health_lbl, self.actions_count_lbl]:
            lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 600;")

        sc_layout.addWidget(QLabel("📊 Session Summary Analytics:"), 0, 0, 1, 3)
        sc_layout.addWidget(self.avg_cpu_lbl, 1, 0)
        sc_layout.addWidget(self.peak_cpu_lbl, 1, 1)
        sc_layout.addWidget(self.actions_count_lbl, 1, 2)
        sc_layout.addWidget(self.avg_mem_lbl, 2, 0)
        sc_layout.addWidget(self.peak_mem_lbl, 2, 1)
        sc_layout.addWidget(self.avg_health_lbl, 2, 2)

        self.layout_main.addWidget(self.session_card)

        # Tabs: Timeline Tracks
        self.tabs = QTabWidget()

        # Track 1: Before-and-After Verified Actions
        track_actions = QWidget()
        ta_layout = QVBoxLayout(track_actions)
        ta_layout.setContentsMargins(8, 12, 8, 8)
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(8)
        self.actions_table.setHorizontalHeaderLabels([
            "Time", "Action", "Target", "Freed RAM", "CPU Drop", "Health Before", "Health After", "Status"
        ])
        self.actions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.actions_table.verticalHeader().setVisible(False)
        self.actions_table.setShowGrid(False)
        ta_layout.addWidget(self.actions_table)
        self.tabs.addTab(track_actions, "🛡️ Verified Action Outcomes")

        # Track 2: Resource Samples
        track_res = QWidget()
        tr_layout = QVBoxLayout(track_res)
        tr_layout.setContentsMargins(8, 12, 8, 8)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(7)
        self.res_table.setHorizontalHeaderLabels([
            "Time", "Health", "CPU %", "RAM %", "Swap %", "Disk I/O", "Processes"
        ])
        self.res_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setShowGrid(False)
        tr_layout.addWidget(self.res_table)
        self.tabs.addTab(track_res, "📈 Resource Metric Timeline")

        # Track 3: Diagnoses & Alerts History
        track_diag = QWidget()
        td_layout = QVBoxLayout(track_diag)
        td_layout.setContentsMargins(8, 12, 8, 8)
        self.diag_table = QTableWidget()
        self.diag_table.setColumnCount(5)
        self.diag_table.setHorizontalHeaderLabels([
            "Time", "Category / Type", "Primary Bottleneck / Alert", "Strength / Severity", "Health"
        ])
        self.diag_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.diag_table.verticalHeader().setVisible(False)
        self.diag_table.setShowGrid(False)
        td_layout.addWidget(self.diag_table)
        self.tabs.addTab(track_diag, "🔍 Diagnoses & Alerts")

        self.layout_main.addWidget(self.tabs)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh()

    def _on_range_changed(self, index: int):
        hours_map = {0: 1.0, 1: 6.0, 2: 24.0, 3: 168.0}
        self._current_hours = hours_map.get(index, 1.0)
        self.refresh()

    def refresh(self):
        """Reload session comparison metrics and timeline events."""
        stats = self.db.get_session_stats(hours=self._current_hours)
        self.avg_cpu_lbl.setText(f"Avg CPU: {stats.get('avg_cpu', 0)}%")
        self.peak_cpu_lbl.setText(f"Peak CPU: {stats.get('max_cpu', 0)}%")
        self.avg_mem_lbl.setText(f"Avg RAM: {stats.get('avg_mem', 0)}%")
        self.peak_mem_lbl.setText(f"Peak RAM: {stats.get('max_mem', 0)}%")
        self.avg_health_lbl.setText(f"Avg Health: {stats.get('avg_health', 100)}/100")
        self.actions_count_lbl.setText(f"Verified Actions: {stats.get('recovery_actions_count', 0)}")

        # Populate Verified Actions Table
        actions = self.db.get_recovery_actions(limit=50)
        self.actions_table.setRowCount(len(actions))
        for row, a in enumerate(actions):
            self.actions_table.setItem(row, 0, QTableWidgetItem(format_timestamp(a.get('timestamp', 0))))
            self.actions_table.setItem(row, 1, QTableWidgetItem(a.get('action_name', '')))
            self.actions_table.setItem(row, 2, QTableWidgetItem(f"{a.get('target_process')} (PID {a.get('target_pid')})"))

            freed_item = QTableWidgetItem(f"+{a.get('freed_memory_mb', 0):.0f} MB")
            freed_item.setForeground(Qt.GlobalColor.green)
            self.actions_table.setItem(row, 3, freed_item)

            drop_item = QTableWidgetItem(f"-{a.get('cpu_drop', 0):.1f}%")
            drop_item.setForeground(Qt.GlobalColor.green)
            self.actions_table.setItem(row, 4, drop_item)

            self.actions_table.setItem(row, 5, QTableWidgetItem(f"{a.get('before_health', 0):.0f}"))
            self.actions_table.setItem(row, 6, QTableWidgetItem(f"{a.get('after_health', 0):.0f}"))
            
            ver_item = QTableWidgetItem("✅ Verified" if a.get('verified') else "Logged")
            ver_item.setForeground(Qt.GlobalColor.green)
            self.actions_table.setItem(row, 7, ver_item)

        # Populate Resource Timeline
        samples = self.db.get_resource_history(hours=self._current_hours, limit=200)
        self.res_table.setRowCount(len(samples))
        for row, s in enumerate(samples):
            self.res_table.setItem(row, 0, QTableWidgetItem(format_timestamp(s.get('timestamp', 0))))
            
            h_score = s.get('health_score', 100)
            h_item = QTableWidgetItem(f"{h_score:.0f}")
            h_item.setForeground(Qt.GlobalColor.green if h_score >= 80 else (Qt.GlobalColor.yellow if h_score >= 60 else Qt.GlobalColor.red))
            self.res_table.setItem(row, 1, h_item)

            self.res_table.setItem(row, 2, QTableWidgetItem(f"{s.get('cpu_percent', 0):.1f}%"))
            self.res_table.setItem(row, 3, QTableWidgetItem(f"{s.get('memory_percent', 0):.1f}%"))
            self.res_table.setItem(row, 4, QTableWidgetItem(f"{s.get('swap_percent', 0):.1f}%"))
            
            disk_io = (s.get('disk_read_speed', 0) + s.get('disk_write_speed', 0)) / (1024 * 1024)
            self.res_table.setItem(row, 5, QTableWidgetItem(f"{disk_io:.1f} MB/s"))
            self.res_table.setItem(row, 6, QTableWidgetItem(str(s.get('process_count', 0))))

        # Populate Diagnoses & Alerts History
        diags = self.db.get_diagnoses(limit=50)
        alerts = self.db.get_behavior_alerts(limit=50)
        combined_events = []
        for d in diags:
            combined_events.append({
                'time': d.get('timestamp', 0),
                'type': f"Diagnosis: {d.get('category', 'Bottleneck')}",
                'desc': d.get('primary_cause', ''),
                'score': f"Strength: {d.get('evidence_strength', 0.8):.2f}",
                'health': f"{d.get('overall_health', 100):.0f}"
            })
        for a in alerts:
            combined_events.append({
                'time': a.get('timestamp', 0),
                'type': f"Behavior Alert: {a.get('alert_type', '')}",
                'desc': f"{a.get('process_name', '')} (PID {a.get('pid', '')}): {a.get('description', '')}",
                'score': a.get('severity', 'Warning'),
                'health': "--"
            })
        combined_events.sort(key=lambda x: x['time'], reverse=True)

        self.diag_table.setRowCount(len(combined_events))
        for row, ev in enumerate(combined_events):
            self.diag_table.setItem(row, 0, QTableWidgetItem(format_timestamp(ev['time'])))
            self.diag_table.setItem(row, 1, QTableWidgetItem(ev['type']))
            self.diag_table.setItem(row, 2, QTableWidgetItem(ev['desc']))
            
            s_item = QTableWidgetItem(ev['score'])
            if "Critical" in ev['score']:
                s_item.setForeground(Qt.GlobalColor.red)
            elif "Warning" in ev['score'] or "Medium" in ev['score']:
                s_item.setForeground(Qt.GlobalColor.yellow)
            self.diag_table.setItem(row, 3, s_item)

            self.diag_table.setItem(row, 4, QTableWidgetItem(ev['health']))
