"""
Performance Page — High-Precision Telemetry Charts
Art-directed real-time technical visualization with fine gridlines, restrained typography,
and authentic collected system metrics.
"""
from collections import deque
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('QtAgg')

from app.ui.styles import COLORS, card_style, panel_alt_style
from app.ui.components import PageHeader, SegmentedTab
from app.monitoring.system_monitor import SystemSnapshot


class LiveTechnicalChart(QFrame):
    """
    High-precision technical chart widget with fine gridlines and live telemetry telemetry header.
    """

    def __init__(self, title: str, unit: str = "%", line_color: str = '#E8FF65',
                 y_max: float = 100.0, max_points: int = 60, parent=None):
        super().__init__(parent)
        self.setStyleSheet(card_style())
        self.setMinimumHeight(230)

        self.title = title
        self.unit = unit
        self._max_points = max_points
        self._data = deque([0.0] * max_points, maxlen=max_points)
        self._y_max = y_max
        self._line_color = line_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Header Row: Title on Left, Realtime Technical Readout on Right
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        title_box.addWidget(self.title_label)
        header.addLayout(title_box)

        header.addStretch()

        # Telemetry metrics readout (Now / Avg / Peak)
        self.telemetry_readout = QLabel(f"NOW: 0.0{unit}  •  AVG: 0.0{unit}  •  PEAK: 0.0{unit}")
        self.telemetry_readout.setStyleSheet(
            f"color: {line_color}; font-size: 11px; font-weight: 700; "
            f"font-family: 'Consolas', monospace;"
        )
        header.addWidget(self.telemetry_readout)

        layout.addLayout(header)

        # Matplotlib Canvas
        self.fig = Figure(figsize=(5, 1.9), dpi=100)
        self.fig.patch.set_facecolor(COLORS['bg_card'])
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background: transparent; border: none;")

        self.ax = self.fig.add_subplot(111)
        self._setup_axes()

        layout.addWidget(self.canvas)

    def _setup_axes(self):
        ax = self.ax
        ax.set_facecolor(COLORS['bg_card'])
        ax.set_xlim(0, self._max_points - 1)
        ax.set_ylim(0, self._y_max)

        # Tick styling
        ax.tick_params(colors=COLORS['text_muted'], labelsize=7.5, pad=2)
        for label in ax.get_yticklabels():
            label.set_fontname('Consolas')

        # Borders / Spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(COLORS['border_subtle'])
        ax.spines['left'].set_color(COLORS['border_subtle'])
        ax.set_xticklabels([])

        # Fine technical gridlines
        ax.grid(True, linestyle='-', linewidth=0.6, alpha=0.35, color=COLORS['border'])
        self.fig.tight_layout(pad=0.4)

    def set_max_points(self, points: int):
        self._max_points = points
        old_data = list(self._data)
        self._data = deque(old_data, maxlen=points)
        while len(self._data) < points:
            self._data.appendleft(0.0)
        self.ax.set_xlim(0, self._max_points - 1)

    def add_value(self, value: float, display_override: str = ""):
        self._data.append(value)

        self.ax.clear()
        self._setup_axes()

        data_list = list(self._data)
        x = list(range(len(data_list)))

        # Clean fill under curve
        self.ax.fill_between(x, data_list, alpha=0.08, color=self._line_color)
        # Main crisp line
        self.ax.plot(x, data_list, color=self._line_color, linewidth=1.4, antialiased=True)

        self.canvas.draw_idle()

        # Update telemetry summary
        valid_pts = [v for v in data_list if v >= 0]
        if valid_pts:
            curr_val = valid_pts[-1]
            avg_val = sum(valid_pts) / len(valid_pts)
            peak_val = max(valid_pts)

            if display_override:
                self.telemetry_readout.setText(display_override)
            else:
                self.telemetry_readout.setText(
                    f"NOW: {curr_val:.1f}{self.unit}   "
                    f"AVG: {avg_val:.1f}{self.unit}   "
                    f"PEAK: {peak_val:.1f}{self.unit}"
                )


class PerformancePage(QWidget):
    """Performance telemetry page with live high-precision charts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header Row with Time-Range Switcher
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        eyebrow = QLabel("TELEMETRY STREAMS")
        eyebrow.setStyleSheet(
            f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; font-family: 'Consolas', monospace;"
        )
        title_box.addWidget(eyebrow)

        title = QLabel("Performance Metrics")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel("Real-time time-series telemetry sampled at active engine cadence. Authentically collected from OS subsystems.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)

        header_row.addLayout(title_box, 1)

        # Time-Range Switcher
        self.time_range_tabs = SegmentedTab(["60 SECONDS", "5 MINUTES", "15 MINUTES"], current_index=0)
        self.time_range_tabs.tab_changed.connect(self._on_time_range_changed)
        header_row.addWidget(self.time_range_tabs, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(header_row)

        # Charts Grid
        grid = QGridLayout()
        grid.setSpacing(14)

        # 1. CPU Utilization (Acid Lime)
        self.cpu_chart = LiveTechnicalChart(
            "CPU Utilization", unit="%", line_color=COLORS['accent_lime'], y_max=100.0, max_points=30
        )
        grid.addWidget(self.cpu_chart, 0, 0)

        # 2. Memory Utilization (Muted Teal)
        self.ram_chart = LiveTechnicalChart(
            "Physical Memory Load", unit="%", line_color=COLORS['accent_teal'], y_max=100.0, max_points=30
        )
        grid.addWidget(self.ram_chart, 0, 1)

        # 3. Disk I/O Throughput (Warm Off-white)
        self.disk_chart = LiveTechnicalChart(
            "Storage Volume I/O Rate", unit=" MB/s", line_color=COLORS['text_primary'], y_max=100.0, max_points=30
        )
        grid.addWidget(self.disk_chart, 1, 0)

        # 4. Network Throughput (Muted Teal / Soft Cyan)
        self.net_chart = LiveTechnicalChart(
            "Aggregated Network Bandwidth", unit=" KB/s", line_color='#A3E635', y_max=3000.0, max_points=30
        )
        grid.addWidget(self.net_chart, 1, 1)

        layout.addLayout(grid)
        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_time_range_changed(self, index: int):
        points_map = {0: 30, 1: 150, 2: 450}
        pts = points_map.get(index, 30)
        self.cpu_chart.set_max_points(pts)
        self.ram_chart.set_max_points(pts)
        self.disk_chart.set_max_points(pts)
        self.net_chart.set_max_points(pts)

    def update_snapshot(self, snap: SystemSnapshot):
        """Update live charts with newly collected metrics."""
        self.cpu_chart.add_value(snap.cpu.overall_percent)
        self.ram_chart.add_value(snap.memory.percent)

        disk_io_mb = (snap.disk.read_bytes_per_sec + snap.disk.write_bytes_per_sec) / (1024 * 1024)
        if disk_io_mb > self.disk_chart._y_max:
            self.disk_chart._y_max = max(100.0, disk_io_mb * 1.3)
        self.disk_chart.add_value(disk_io_mb)

        net_kb = (snap.network.upload_speed + snap.network.download_speed) / 1024
        if net_kb > self.net_chart._y_max:
            self.net_chart._y_max = max(1000.0, net_kb * 1.3)
        self.net_chart.add_value(net_kb)
