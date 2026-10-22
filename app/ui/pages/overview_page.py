"""
Overview Page — Editorial System Console with Live Telemetry
Art-directed layout combining Linear clarity, Swiss typography, and restrained technical data density.
"""
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QProgressBar, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from app.ui.styles import COLORS, card_style, panel_alt_style, severity_badge_style
from app.ui.components import MetricCard, MiniSparkline, StatusPill, EmptyStateWidget
from app.utils.formatting import (
    format_bytes, format_speed, format_uptime, health_score_color,
    health_score_label
)
from app.monitoring.system_monitor import SystemSnapshot, ProcessInfo
from app.analysis.engine import HealthScoreBreakdown, Severity
from app.database.db_manager import DatabaseManager


class OverviewPage(QWidget):
    """Refined system console overview page."""

    diagnose_requested = Signal()

    def __init__(self, monitor, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.db = db
        self._sample_count = 0
        self._last_diag_keys = None
        self._pending_top_procs = None
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(16)

        # === 1. Editorial Header Section ===
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        eyebrow = QLabel("LIVE TELEMETRY // OVERVIEW")
        eyebrow.setStyleSheet(
            f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; font-family: 'Consolas', 'Segoe UI Mono', monospace;"
        )
        title_box.addWidget(eyebrow)

        self.headline = QLabel("Your machine, under control.")
        self.headline.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.headline.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(self.headline)

        self.status_subtitle = QLabel("Initializing local monitoring engine...")
        self.status_subtitle.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; font-family: 'Segoe UI', sans-serif;"
        )
        title_box.addWidget(self.status_subtitle)

        header_row.addLayout(title_box, 1)

        # Clearly accessible diagnostic action
        self.diagnose_btn = QPushButton("⌕  Run Diagnostics")
        self.diagnose_btn.setFixedHeight(40)
        self.diagnose_btn.setMinimumWidth(160)
        self.diagnose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.diagnose_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
            f"border: 1px solid {COLORS['accent_lime']}; border-radius: 6px; "
            f"font-size: 12px; font-weight: 700; padding: 8px 18px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_lime_dim']}; border-color: {COLORS['accent_lime_dim']}; }}"
        )
        self.diagnose_btn.clicked.connect(self.diagnose_requested.emit)
        header_row.addWidget(self.diagnose_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addLayout(header_row)

        # === 2. Telemetry Hero Strip (6 distinct metric modules) ===
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        # 1. CPU
        self.cpu_card = MetricCard("CPU Utilization", "⌁")
        metrics_grid.addWidget(self.cpu_card, 0, 0)

        # 2. RAM
        self.ram_card = MetricCard("Memory Footprint", "▦")
        metrics_grid.addWidget(self.ram_card, 0, 1)

        # 3. Disk Capacity (Storage volume)
        self.disk_cap_card = MetricCard("Disk Capacity", "◔")
        metrics_grid.addWidget(self.disk_cap_card, 0, 2)

        # 4. Disk Activity (I/O rate)
        self.disk_io_card = MetricCard("Disk I/O Activity", "⇅")
        metrics_grid.addWidget(self.disk_io_card, 1, 0)

        # 5. Network Throughput
        self.net_card = MetricCard("Network Throughput", "⇋")
        metrics_grid.addWidget(self.net_card, 1, 1)

        # 6. Power / Uptime
        self.power_card = MetricCard("Power & Uptime", "⚡")
        metrics_grid.addWidget(self.power_card, 1, 2)

        self.main_layout.addLayout(metrics_grid)

        # === 3. Compact Performance Timeline Panel ===
        timeline_panel = QFrame()
        timeline_panel.setStyleSheet(card_style())
        tl_layout = QVBoxLayout(timeline_panel)
        tl_layout.setContentsMargins(16, 12, 16, 12)
        tl_layout.setSpacing(6)

        tl_header = QHBoxLayout()
        tl_title = QLabel("PERFORMANCE TIMELINE (RECENT SAMPLES)")
        tl_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        tl_header.addWidget(tl_title)
        tl_header.addStretch()

        # Legend
        cpu_leg = QLabel("― CPU Load")
        cpu_leg.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        tl_header.addWidget(cpu_leg)
        tl_header.addSpacing(10)

        ram_leg = QLabel("― Memory")
        ram_leg.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        tl_header.addWidget(ram_leg)
        tl_header.addSpacing(10)

        self.timeline_rate_lbl = QLabel("TICK: 2.0s")
        self.timeline_rate_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        tl_header.addWidget(self.timeline_rate_lbl)

        tl_layout.addLayout(tl_header)

        # Sparkline widget
        self.sparkline = MiniSparkline(max_samples=60)
        tl_layout.addWidget(self.sparkline)

        self.main_layout.addWidget(timeline_panel)

        # === 4. Lower Two-Column Section ===
        lower_row = QHBoxLayout()
        lower_row.setSpacing(14)

        # --- Left Column: Health Breakdown & Active Findings ---
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Health Breakdown Frame
        health_frame = QFrame()
        health_frame.setStyleSheet(card_style())
        hf_layout = QVBoxLayout(health_frame)
        hf_layout.setContentsMargins(18, 16, 18, 16)
        hf_layout.setSpacing(12)

        hf_header = QHBoxLayout()
        hf_title = QLabel("SYSTEM HEALTH INDEX")
        hf_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        hf_header.addWidget(hf_title)
        hf_header.addStretch()

        self.health_status_pill = QLabel("NOMINAL")
        self.health_status_pill.setStyleSheet(severity_badge_style("Healthy"))
        hf_header.addWidget(self.health_status_pill)
        hf_layout.addLayout(hf_header)

        score_row = QHBoxLayout()
        score_row.setSpacing(16)

        self.health_score_num = QLabel("--")
        self.health_score_num.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        self.health_score_num.setStyleSheet(f"color: {COLORS['accent_teal']};")
        score_row.addWidget(self.health_score_num)

        # Sub-score decomposition bars
        decomp_box = QVBoxLayout()
        decomp_box.setSpacing(4)

        self.cpu_bar_tup = self._create_mini_bar("CPU")
        self.mem_bar_tup = self._create_mini_bar("RAM")
        self.swap_bar_tup = self._create_mini_bar("SWAP")
        self.disk_bar_tup = self._create_mini_bar("DISK")

        for lbl, bar, val_lbl in [self.cpu_bar_tup, self.mem_bar_tup, self.swap_bar_tup, self.disk_bar_tup]:
            r = QHBoxLayout()
            r.setSpacing(8)
            lbl.setFixedWidth(44)
            r.addWidget(lbl)
            r.addWidget(bar, 1)
            val_lbl.setFixedWidth(30)
            r.addWidget(val_lbl)
            decomp_box.addLayout(r)

        score_row.addLayout(decomp_box, 1)
        hf_layout.addLayout(score_row)

        # Factors note
        self.factors_label = QLabel("Analyzing baseline telemetry...")
        self.factors_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.factors_label.setWordWrap(True)
        hf_layout.addWidget(self.factors_label)

        left_col.addWidget(health_frame)

        # Current Intelligence / Findings Frame
        findings_frame = QFrame()
        findings_frame.setStyleSheet(card_style())
        ff_layout = QVBoxLayout(findings_frame)
        ff_layout.setContentsMargins(18, 14, 18, 14)
        ff_layout.setSpacing(8)

        ff_header = QHBoxLayout()
        ff_title = QLabel("SYSTEM INTELLIGENCE FINDINGS")
        ff_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        ff_header.addWidget(ff_title)
        ff_header.addStretch()

        self.findings_count_badge = QLabel("0 ACTIVE")
        self.findings_count_badge.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 600; "
            f"font-family: 'Consolas', monospace;"
        )
        ff_header.addWidget(self.findings_count_badge)
        ff_layout.addLayout(ff_header)

        self.findings_container = QVBoxLayout()
        self.findings_container.setSpacing(6)
        ff_layout.addLayout(self.findings_container)

        self.empty_findings = QLabel("●  All operational signals within expected baseline variance.")
        self.empty_findings.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 11px; padding: 4px 0;")
        self.findings_container.addWidget(self.empty_findings)

        ff_layout.addStretch()
        left_col.addWidget(findings_frame)

        lower_row.addLayout(left_col, 1)

        # --- Right Column: Top Resource Consumers ---
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        procs_frame = QFrame()
        procs_frame.setStyleSheet(card_style())
        pf_layout = QVBoxLayout(procs_frame)
        pf_layout.setContentsMargins(18, 14, 18, 14)
        pf_layout.setSpacing(10)

        pf_header = QHBoxLayout()
        pf_title = QLabel("TOP PROCESSES (ACTIVE CONSUMPTION)")
        pf_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        pf_header.addWidget(pf_title)
        pf_header.addStretch()

        pf_sub = QLabel("LIVE SAMPLES")
        pf_sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        pf_header.addWidget(pf_sub)
        pf_layout.addLayout(pf_header)

        # Clean Table for Top Processes
        self.top_procs_table = QTableWidget()
        self.top_procs_table.setColumnCount(4)
        self.top_procs_table.setHorizontalHeaderLabels(["PROCESS", "PID", "CPU", "MEMORY"])
        self.top_procs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_procs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.top_procs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.top_procs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.top_procs_table.verticalHeader().setVisible(False)
        self.top_procs_table.setShowGrid(False)
        self.top_procs_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.top_procs_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.top_procs_table.setFixedHeight(210)
        pf_layout.addWidget(self.top_procs_table)

        right_col.addWidget(procs_frame)
        lower_row.addLayout(right_col, 1)

        self.main_layout.addLayout(lower_row)

        scroll.setWidget(content)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _create_mini_bar(self, name: str):
        label = QLabel(name)
        label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 600; "
            f"font-family: 'Consolas', monospace;"
        )
        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setFixedHeight(4)
        bar.setTextVisible(False)
        bar.setStyleSheet(
            f"QProgressBar {{ background-color: {COLORS['bg_panel_alt']}; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background-color: {COLORS['accent_teal']}; border-radius: 2px; }}"
        )
        val_label = QLabel("--")
        val_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; "
            f"font-family: 'Consolas', monospace;"
        )
        val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return label, bar, val_label

    def _update_mini_bar(self, bar_tuple, score: float):
        _, bar, val_label = bar_tuple
        clamped = int(max(0, min(100, score)))
        bar.setValue(clamped)
        val_label.setText(f"{clamped}")
        color = health_score_color(score)
        bar.setStyleSheet(
            f"QProgressBar {{ background-color: {COLORS['bg_panel_alt']}; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}"
        )

    def update_snapshot(self, snap: SystemSnapshot):
        """Update live telemetry metrics connected to backend data."""
        self._sample_count += 1

        # 1. CPU
        cpu_pct = snap.cpu.overall_percent
        freq_str = f"{snap.cpu.frequency_current:.0f} MHz" if snap.cpu.frequency_current > 0 else "Base clock"
        self.cpu_card.set_value(
            f"{cpu_pct:.1f}%",
            f"{snap.cpu.core_count_logical} Logical Cores  •  {freq_str}",
            percent=cpu_pct,
            tag=f"SYS {snap.cpu.core_count_physical}P/{snap.cpu.core_count_logical}L"
        )

        # 2. RAM
        ram_pct = snap.memory.percent
        used_gb = snap.memory.used / (1024**3)
        total_gb = snap.memory.total / (1024**3)
        avail_gb = snap.memory.available / (1024**3)
        self.ram_card.set_value(
            f"{ram_pct:.1f}%",
            f"{used_gb:.1f} GB used of {total_gb:.1f} GB  •  {avail_gb:.1f} GB free",
            percent=ram_pct,
            tag="PHYSICAL"
        )

        # 3. Disk Capacity (Storage volume)
        disk_pct = snap.disk.percent
        disk_used_gb = snap.disk.used / (1024**3)
        disk_total_gb = snap.disk.total / (1024**3)
        disk_free_gb = snap.disk.free / (1024**3)
        self.disk_cap_card.set_value(
            f"{disk_pct:.1f}%",
            f"{disk_free_gb:.1f} GB available  •  {disk_used_gb:.1f} / {disk_total_gb:.1f} GB",
            percent=disk_pct,
            tag="VOLUME C:"
        )

        # 4. Disk Activity (I/O Throughput)
        io_total_bytes = snap.disk.read_bytes_per_sec + snap.disk.write_bytes_per_sec
        io_total_mb = io_total_bytes / (1024 * 1024)
        read_str = format_speed(snap.disk.read_bytes_per_sec)
        write_str = format_speed(snap.disk.write_bytes_per_sec)
        self.disk_io_card.set_value(
            f"{io_total_mb:.1f} MB/s",
            f"Read: {read_str}  •  Write: {write_str}",
            percent=min(100.0, (io_total_mb / 50.0) * 100.0),
            tag="REALTIME I/O"
        )

        # 5. Network Throughput
        net_up = format_speed(snap.network.upload_speed)
        net_down = format_speed(snap.network.download_speed)
        total_net_kb = (snap.network.upload_speed + snap.network.download_speed) / 1024
        self.net_card.set_value(
            f"{total_net_kb:.1f} KB/s",
            f"↑ {net_up}   ↓ {net_down}",
            percent=min(100.0, (total_net_kb / 2000.0) * 100.0),
            tag="AGGREGATED"
        )

        # 6. Power / Uptime
        if snap.battery.available:
            p_status = "Charging (AC)" if snap.battery.plugged else "Discharging"
            p_val = f"{snap.battery.percent:.0f}%"
            p_sub = f"{p_status}  •  Uptime: {format_uptime(snap.uptime_seconds)}"
            self.power_card.set_value(p_val, p_sub, percent=snap.battery.percent, tag="BATTERY")
        else:
            self.power_card.set_value(
                "A/C Power",
                f"Desktop power delivery  •  Uptime: {format_uptime(snap.uptime_seconds)}",
                percent=-1,
                tag="A/C LINE"
            )

        # Update sparkline
        self.sparkline.add_sample(cpu_pct, ram_pct)

        # Update dynamic subtitle
        cur_time = time.strftime('%H:%M:%S')
        self.status_subtitle.setText(
            f"{snap.platform_info}  •  {snap.process_count} Active Tasks  •  "
            f"Synced: {cur_time} (Sample #{self._sample_count})"
        )

    def update_health(self, health: HealthScoreBreakdown):
        """Update system health score and sub-scores."""
        score = health.total_score
        color = health_score_color(score)
        label = health_score_label(score)

        self.health_score_num.setText(f"{score:.0f}")
        self.health_score_num.setStyleSheet(f"color: {color}; font-family: 'Consolas', monospace;")

        self.health_status_pill.setText(label.upper())
        self.health_status_pill.setStyleSheet(severity_badge_style(label))

        self._update_mini_bar(self.cpu_bar_tup, health.cpu_score)
        self._update_mini_bar(self.mem_bar_tup, health.memory_score)
        self._update_mini_bar(self.swap_bar_tup, health.swap_score)
        self._update_mini_bar(self.disk_bar_tup, health.disk_score)

        if health.factors:
            self.factors_label.setText("  •  ".join(health.factors[:3]))
        else:
            self.factors_label.setText("• All resource subsystems operating within expected parameters.")

        # Adapt headline based on system state
        if score >= 85:
            self.headline.setText("Your machine, under control.")
        elif score >= 65:
            self.headline.setText("System operational with moderate load.")
        else:
            self.headline.setText("Elevated resource contention detected.")

    def showEvent(self, event):
        super().showEvent(event)
        if self._pending_top_procs is not None:
            self.update_top_processes(self._pending_top_procs)
            self._pending_top_procs = None

    def update_top_processes(self, processes: list[ProcessInfo]):
        """Populate the top processes table."""
        if not self.isVisible():
            self._pending_top_procs = processes
            return
        self._pending_top_procs = None

        # Filter out System Idle Process (PID 0) so actual active consumers show up
        filtered = [p for p in processes if p.pid != 0 and 'idle' not in p.name.lower()][:5]
        self.top_procs_table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            # Process name
            name_item = self.top_procs_table.item(row, 0)
            if not name_item:
                name_item = QTableWidgetItem()
                name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                self.top_procs_table.setItem(row, 0, name_item)
            name_item.setText(p.name)

            # PID (monospace)
            pid_item = self.top_procs_table.item(row, 1)
            if not pid_item:
                pid_item = QTableWidgetItem()
                pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                pid_item.setFont(QFont("Consolas", 10))
                pid_item.setForeground(QColor(COLORS['text_muted']))
                self.top_procs_table.setItem(row, 1, pid_item)
            pid_item.setText(str(p.pid))

            # CPU %
            cpu_item = self.top_procs_table.item(row, 2)
            if not cpu_item:
                cpu_item = QTableWidgetItem()
                cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                cpu_item.setFont(QFont("Consolas", 10))
                self.top_procs_table.setItem(row, 2, cpu_item)
            cpu_item.setText(f"{p.cpu_percent:.1f}%")
            if p.cpu_percent >= 30:
                cpu_item.setForeground(QColor(COLORS['amber']))
            else:
                cpu_item.setForeground(QColor(COLORS['text_primary']))

            # Memory (MB)
            mem_item = self.top_procs_table.item(row, 3)
            if not mem_item:
                mem_item = QTableWidgetItem()
                mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                mem_item.setFont(QFont("Consolas", 10))
                self.top_procs_table.setItem(row, 3, mem_item)
            mem_item.setText(f"{p.memory_mb:.0f} MB")

    def update_diagnoses(self, diagnoses: list):
        """Update active findings from live diagnosis stream."""
        non_healthy = [d for d in diagnoses if d.severity != Severity.HEALTHY]
        diag_keys = [(d.severity, d.title) for d in non_healthy[:4]]
        if self._last_diag_keys == diag_keys:
            return
        self._last_diag_keys = diag_keys

        # Clear findings layout
        while self.findings_container.count():
            item = self.findings_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not non_healthy:
            ok_lbl = QLabel("●  All operational signals within expected baseline variance.")
            ok_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 11px; padding: 4px 0;")
            self.findings_container.addWidget(ok_lbl)
            self.findings_count_badge.setText("0 ACTIVE")
            self.findings_count_badge.setStyleSheet(f"color: {COLORS['text_muted']}; font-family: 'Consolas', monospace;")
            return

        self.findings_count_badge.setText(f"{len(non_healthy)} ACTIVE")
        self.findings_count_badge.setStyleSheet(f"color: {COLORS['amber']}; font-weight: bold; font-family: 'Consolas', monospace;")

        for diag in non_healthy[:4]:
            row = QFrame()
            row.setStyleSheet(
                f"background-color: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; "
                f"border-radius: 4px;"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 6, 8, 6)
            rl.setSpacing(10)

            sev_badge = QLabel(diag.severity.upper())
            sev_badge.setStyleSheet(severity_badge_style(diag.severity))
            rl.addWidget(sev_badge)

            title_lbl = QLabel(diag.title)
            title_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
            rl.addWidget(title_lbl, 1)

            self.findings_container.addWidget(row)

    def update_alert_count(self, count: int):
        pass
