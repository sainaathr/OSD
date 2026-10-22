"""
History Page — System Time Machine & Historical Telemetry Archive
Reconstruct system history across sessions, compare before/after recovery outcomes,
browse historical anomalies, and export telemetry datasets.
"""
import time
import os
import csv
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QGridLayout, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.ui.styles import COLORS, card_style, panel_alt_style, severity_badge_style
from app.ui.components import PageHeader, SegmentedTab, EmptyStateWidget
from app.utils.formatting import format_timestamp, format_speed, format_bytes
from app.database.db_manager import DatabaseManager


class HistoryPage(QWidget):
    """Refined System History & Time Machine Page."""

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
        self.layout_main.setContentsMargins(28, 24, 28, 24)
        self.layout_main.setSpacing(14)

        # Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        eyebrow = QLabel("TELEMETRY ARCHIVE")
        eyebrow.setStyleSheet(
            f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; font-family: 'Consolas', monospace;"
        )
        title_box.addWidget(eyebrow)

        title = QLabel("System History & Audit")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel("Reconstruct system history across operating sessions. Review verified recovery actions and export telemetry.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)

        header_row.addLayout(title_box, 1)

        # Time range combo
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"])
        self.range_combo.setFixedHeight(34)
        self.range_combo.currentIndexChanged.connect(self._on_range_changed)
        header_row.addWidget(self.range_combo)

        # Export CSV Button
        export_btn = QPushButton("Export CSV")
        export_btn.setFixedHeight(34)
        export_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; color: {COLORS['accent_lime']}; }}"
        )
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export_csv)
        header_row.addWidget(export_btn)

        # Refresh Button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; }}"
        )
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)

        self.layout_main.addLayout(header_row)

        # Session Analytics Strip (6 stats)
        session_card = QFrame()
        session_card.setStyleSheet(card_style())
        sc_layout = QGridLayout(session_card)
        sc_layout.setContentsMargins(18, 14, 18, 14)
        sc_layout.setSpacing(14)

        sc_title = QLabel("SESSION SUMMARY ANALYTICS")
        sc_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        sc_layout.addWidget(sc_title, 0, 0, 1, 3)

        self.avg_cpu_lbl = QLabel("Avg CPU: --")
        self.peak_cpu_lbl = QLabel("Peak CPU: --")
        self.avg_mem_lbl = QLabel("Avg RAM: --")
        self.peak_mem_lbl = QLabel("Peak RAM: --")
        self.avg_health_lbl = QLabel("Avg Health: --")
        self.actions_count_lbl = QLabel("Verified Actions: --")

        for lbl in [self.avg_cpu_lbl, self.peak_cpu_lbl, self.avg_mem_lbl, self.peak_mem_lbl, self.avg_health_lbl, self.actions_count_lbl]:
            lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 600; font-family: 'Consolas', monospace;")

        sc_layout.addWidget(self.avg_cpu_lbl, 1, 0)
        sc_layout.addWidget(self.peak_cpu_lbl, 1, 1)
        sc_layout.addWidget(self.actions_count_lbl, 1, 2)
        sc_layout.addWidget(self.avg_mem_lbl, 2, 0)
        sc_layout.addWidget(self.peak_mem_lbl, 2, 1)
        sc_layout.addWidget(self.avg_health_lbl, 2, 2)

        self.layout_main.addWidget(session_card)

        # Tabs for Tracks
        self.tabs = QTabWidget()

        # Track 1: Verified Action Outcomes
        track_actions = QWidget()
        ta_layout = QVBoxLayout(track_actions)
        ta_layout.setContentsMargins(8, 12, 8, 8)
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(8)
        self.actions_table.setHorizontalHeaderLabels([
            "TIMESTAMP", "ACTION", "TARGET", "FREED RAM", "CPU DROP", "HEALTH PRE", "HEALTH POST", "STATUS"
        ])
        self.actions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.actions_table.verticalHeader().setVisible(False)
        self.actions_table.setShowGrid(False)
        ta_layout.addWidget(self.actions_table)
        self.tabs.addTab(track_actions, "Verified Actions Audit")

        # Track 2: Resource Samples
        track_res = QWidget()
        tr_layout = QVBoxLayout(track_res)
        tr_layout.setContentsMargins(8, 12, 8, 8)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(7)
        self.res_table.setHorizontalHeaderLabels([
            "TIMESTAMP", "HEALTH", "CPU %", "RAM %", "SWAP %", "DISK I/O", "TASKS"
        ])
        self.res_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setShowGrid(False)
        tr_layout.addWidget(self.res_table)
        self.tabs.addTab(track_res, "Resource Metric Timeline")

        # Track 3: Diagnostic Findings & Alerts Archive
        track_diag = QWidget()
        td_layout = QVBoxLayout(track_diag)
        td_layout.setContentsMargins(8, 12, 8, 8)
        self.diag_table = QTableWidget()
        self.diag_table.setColumnCount(5)
        self.diag_table.setHorizontalHeaderLabels([
            "TIMESTAMP", "CATEGORY", "BOTTLENECK / ALERT", "SEVERITY", "SCORE"
        ])
        self.diag_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.diag_table.verticalHeader().setVisible(False)
        self.diag_table.setShowGrid(False)
        td_layout.addWidget(self.diag_table)
        self.tabs.addTab(track_diag, "Diagnoses & Alerts Archive")

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
        """Reload historical telemetry metrics and tables."""
        stats = self.db.get_session_stats(hours=self._current_hours)
        self.avg_cpu_lbl.setText(f"Avg CPU:     {stats.get('avg_cpu', 0):.1f}%")
        self.peak_cpu_lbl.setText(f"Peak CPU:    {stats.get('max_cpu', 0):.1f}%")
        self.avg_mem_lbl.setText(f"Avg RAM:     {stats.get('avg_mem', 0):.1f}%")
        self.peak_mem_lbl.setText(f"Peak RAM:    {stats.get('max_mem', 0):.1f}%")
        self.avg_health_lbl.setText(f"Avg Health:  {stats.get('avg_health', 100):.0f}/100")
        self.actions_count_lbl.setText(f"Verified Actions: {stats.get('recovery_actions_count', 0)}")

        self._last_refresh_time = time.time()

        # 1. Populate Actions Table
        actions = self.db.get_recovery_actions(limit=50)
        self.actions_table.setUpdatesEnabled(False)
        self.actions_table.blockSignals(True)
        try:
            self.actions_table.setRowCount(len(actions))
            for row, a in enumerate(actions):
                t_item = QTableWidgetItem(format_timestamp(a.get('timestamp', 0)))
                t_item.setFont(QFont("Consolas", 10))
                self.actions_table.setItem(row, 0, t_item)

                self.actions_table.setItem(row, 1, QTableWidgetItem(a.get('action_name', '')))
                self.actions_table.setItem(row, 2, QTableWidgetItem(f"{a.get('target_process')} (PID {a.get('target_pid')})"))

                freed_item = QTableWidgetItem(f"{a.get('freed_ram_mb', 0):.1f} MB")
                freed_item.setFont(QFont("Consolas", 10))
                freed_item.setForeground(QColor(COLORS['accent_lime']))
                self.actions_table.setItem(row, 3, freed_item)

                cpu_item = QTableWidgetItem(f"{a.get('cpu_drop_percent', 0):.1f}%")
                cpu_item.setFont(QFont("Consolas", 10))
                self.actions_table.setItem(row, 4, cpu_item)

                hb_item = QTableWidgetItem(f"{a.get('health_before', 0):.0f}")
                hb_item.setFont(QFont("Consolas", 10))
                self.actions_table.setItem(row, 5, hb_item)

                ha_item = QTableWidgetItem(f"{a.get('health_after', 0):.0f}")
                ha_item.setFont(QFont("Consolas", 10))
                self.actions_table.setItem(row, 6, ha_item)

                st_item = QTableWidgetItem(a.get('verification_status', 'Verified'))
                st_item.setFont(QFont("Consolas", 10))
                st_item.setForeground(QColor(COLORS['accent_teal']))
                self.actions_table.setItem(row, 7, st_item)
        finally:
            self.actions_table.blockSignals(False)
            self.actions_table.setUpdatesEnabled(True)

        # 2. Populate Resource Samples Table
        samples = self.db.get_resource_history(hours=self._current_hours, limit=100)
        self.res_table.setUpdatesEnabled(False)
        self.res_table.blockSignals(True)
        try:
            self.res_table.setRowCount(len(samples))
            for row, s in enumerate(samples):
                t_item = QTableWidgetItem(format_timestamp(s.get('timestamp', 0)))
                t_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 0, t_item)

                h_item = QTableWidgetItem(f"{s.get('health_score', 0):.0f}")
                h_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 1, h_item)

                c_item = QTableWidgetItem(f"{s.get('cpu_percent', 0):.1f}%")
                c_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 2, c_item)

                m_item = QTableWidgetItem(f"{s.get('memory_percent', 0):.1f}%")
                m_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 3, m_item)

                sw_item = QTableWidgetItem(f"{s.get('swap_percent', 0):.1f}%")
                sw_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 4, sw_item)

                dio = s.get('disk_read_speed', 0) + s.get('disk_write_speed', 0)
                d_item = QTableWidgetItem(format_speed(dio))
                d_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 5, d_item)

                p_item = QTableWidgetItem(str(s.get('process_count', 0)))
                p_item.setFont(QFont("Consolas", 10))
                self.res_table.setItem(row, 6, p_item)
        finally:
            self.res_table.blockSignals(False)
            self.res_table.setUpdatesEnabled(True)

        # 3. Populate Diagnoses & Alerts Table
        diags = self.db.get_diagnoses(limit=50)
        behavior_alerts = self.db.get_behavior_alerts(limit=50)

        all_events = []
        for d in diags:
            all_events.append({
                'timestamp': d.get('timestamp', 0),
                'category': 'Diagnosis Heuristic',
                'title': d.get('title', ''),
                'severity': d.get('severity', 'Information'),
                'score': f"{d.get('health_score', 0):.0f}"
            })
        for b in behavior_alerts:
            all_events.append({
                'timestamp': b.get('timestamp', 0),
                'category': f"Behavior: {b.get('alert_type', '')}",
                'title': f"{b.get('process_name')} (PID {b.get('pid')}): {b.get('description', '')}",
                'severity': b.get('severity', 'Warning'),
                'score': '--'
            })

        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        self.diag_table.setUpdatesEnabled(False)
        self.diag_table.blockSignals(True)
        try:
            self.diag_table.setRowCount(len(all_events))
            for row, ev in enumerate(all_events):
                t_item = QTableWidgetItem(format_timestamp(ev['timestamp']))
                t_item.setFont(QFont("Consolas", 10))
                self.diag_table.setItem(row, 0, t_item)

                self.diag_table.setItem(row, 1, QTableWidgetItem(ev['category']))
                self.diag_table.setItem(row, 2, QTableWidgetItem(ev['title']))

                sev_item = QTableWidgetItem(ev['severity'].upper())
                sev_item.setFont(QFont("Consolas", 10))
                if 'crit' in ev['severity'].lower():
                    sev_item.setForeground(QColor(COLORS['red']))
                elif 'warn' in ev['severity'].lower():
                    sev_item.setForeground(QColor(COLORS['amber']))
                else:
                    sev_item.setForeground(QColor(COLORS['accent_teal']))
                self.diag_table.setItem(row, 3, sev_item)

                sc_item = QTableWidgetItem(ev['score'])
                sc_item.setFont(QFont("Consolas", 10))
                self.diag_table.setItem(row, 4, sc_item)
        finally:
            self.diag_table.blockSignals(False)
            self.diag_table.setUpdatesEnabled(True)

    def _export_csv(self):
        """Export snapshot samples to CSV."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Telemetry Dataset to CSV",
            f"OSD_Telemetry_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        if not filename:
            return

        try:
            samples = self.db.get_resource_history(hours=168.0, limit=5000)
            if not samples:
                QMessageBox.information(self, "No Data", "No snapshot records available to export.")
                return

            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(samples[0].keys()))
                writer.writeheader()
                writer.writerows(samples)

            QMessageBox.information(self, "Export Complete", f"Successfully exported {len(samples)} records to:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", str(e))
