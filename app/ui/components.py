"""
OSD Reusable UI Components
Art-directed Swiss / Linear desktop widgets for data density, precision, and calm usability.
"""
from collections import deque
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QSizePolicy, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QFont, QPainter, QPen, QColor, QBrush, QLinearGradient, QPolygonF

from app.ui.styles import COLORS, card_style, panel_alt_style, severity_badge_style


class PageHeader(QWidget):
    """Refined editorial page header with eyebrow, headline, and contextual action."""

    def __init__(self, eyebrow: str, title: str, description: str = "",
                 action_btn: QPushButton = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        if eyebrow:
            eb_label = QLabel(eyebrow.upper())
            eb_label.setStyleSheet(
                f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
                f"letter-spacing: 1.5px; font-family: 'Consolas', 'Segoe UI Mono', monospace;"
            )
            text_layout.addWidget(eb_label)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        text_layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        if action_btn:
            layout.addWidget(action_btn, 0, Qt.AlignmentFlag.AlignVCenter)


class MetricCard(QFrame):
    """
    High-precision technical metric card.
    Displays large monospace value, micro-label, sub-telemetry, and optional fill bar.
    """

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(card_style())
        self.setMinimumHeight(115)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Micro Header
        header = QHBoxLayout()
        header.setSpacing(6)
        
        display_title = f"{icon}  {title.upper()}" if icon else title.upper()
        self.title_label = QLabel(display_title)
        self.title_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', 'Segoe UI Mono', monospace;"
        )
        header.addWidget(self.title_label)
        header.addStretch()

        self.tag_label = QLabel("")
        self.tag_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; "
            f"font-family: 'Consolas', monospace;"
        )
        header.addWidget(self.tag_label)
        layout.addLayout(header)

        # Large Reading
        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(self.value_label)

        # Sub-telemetry
        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; "
            f"font-family: 'Segoe UI', sans-serif;"
        )
        self.sub_label.setWordWrap(True)
        layout.addWidget(self.sub_label)

        # Technical Thin Meter Bar
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            f"QProgressBar {{ background-color: {COLORS['bg_panel_alt']}; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background-color: {COLORS['accent_lime']}; border-radius: 2px; }}"
        )
        self.progress.hide()
        layout.addWidget(self.progress)

    def set_value(self, value: str, sub: str = "", percent: float = -1,
                  color: str = "", tag: str = ""):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-family: 'Consolas', monospace;")
        else:
            self.value_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-family: 'Consolas', monospace;")

        if sub:
            self.sub_label.setText(sub)
        if tag:
            self.tag_label.setText(tag)

        if percent >= 0:
            self.progress.show()
            self.progress.setValue(int(min(100, max(0, percent))))
            # Subtle color gradation
            if percent >= 90:
                chunk_color = COLORS['red']
            elif percent >= 75:
                chunk_color = COLORS['amber']
            else:
                chunk_color = COLORS['accent_lime']
            self.progress.setStyleSheet(
                f"QProgressBar {{ background-color: {COLORS['bg_panel_alt']}; border-radius: 2px; }}"
                f"QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 2px; }}"
            )


class MiniSparkline(QWidget):
    """
    Ultra-lightweight vector dual-line sparkline for CPU & RAM trends.
    Uses pure QPainter for native 60fps rendering without external library overhead.
    """

    def __init__(self, max_samples: int = 50, parent=None):
        super().__init__(parent)
        self.max_samples = max_samples
        self.cpu_history = deque([0.0] * max_samples, maxlen=max_samples)
        self.ram_history = deque([0.0] * max_samples, maxlen=max_samples)
        self.setFixedHeight(50)
        self.setMinimumWidth(180)

    def add_sample(self, cpu: float, ram: float):
        self.cpu_history.append(max(0.0, min(100.0, float(cpu))))
        self.ram_history.append(max(0.0, min(100.0, float(ram))))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        pad_top = 4.0
        pad_bottom = 4.0
        eff_h = h - pad_top - pad_bottom

        # Subtle background grid lines
        painter.setPen(QPen(QColor(COLORS['border_subtle']), 1, Qt.PenStyle.DashLine))
        y_mid = pad_top + eff_h * 0.5
        painter.drawLine(0, int(y_mid), int(w), int(y_mid))

        n = len(self.cpu_history)
        if n < 2:
            return

        dx = w / (n - 1)

        # 1. Draw RAM trend (Muted Teal line)
        ram_points = []
        for i, val in enumerate(self.ram_history):
            x = i * dx
            y = pad_top + (1.0 - (val / 100.0)) * eff_h
            ram_points.append(QPointF(x, y))

        ram_pen = QPen(QColor(COLORS['accent_teal']), 1.5)
        painter.setPen(ram_pen)
        for i in range(len(ram_points) - 1):
            painter.drawLine(ram_points[i], ram_points[i + 1])

        # 2. Draw CPU trend (Acid Lime line + subtle gradient area)
        cpu_points = []
        for i, val in enumerate(self.cpu_history):
            x = i * dx
            y = pad_top + (1.0 - (val / 100.0)) * eff_h
            cpu_points.append(QPointF(x, y))

        # Area fill under CPU
        poly = QPolygonF()
        poly.append(QPointF(0, h))
        for pt in cpu_points:
            poly.append(pt)
        poly.append(QPointF(w, h))

        fill_color = QColor(232, 255, 101, 20)  # Acid lime translucent
        painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(poly)

        # CPU Line
        cpu_pen = QPen(QColor(COLORS['accent_lime']), 1.5)
        painter.setPen(cpu_pen)
        for i in range(len(cpu_points) - 1):
            painter.drawLine(cpu_points[i], cpu_points[i + 1])


class StatusPill(QFrame):
    """Understated technical status pill indicator."""

    def __init__(self, text: str = "NOMINAL", state: str = "healthy", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(6)

        self.dot = QLabel("●")
        self.text_lbl = QLabel(text.upper())
        self.text_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))

        layout.addWidget(self.dot)
        layout.addWidget(self.text_lbl)
        self.set_state(text, state)

    def set_state(self, text: str, state: str):
        self.text_lbl.setText(text.upper())
        st = state.lower()
        if 'crit' in st or 'error' in st:
            color = COLORS['red']
            bg = COLORS['red_subtle']
        elif 'warn' in st:
            color = COLORS['amber']
            bg = COLORS['amber_subtle']
        else:
            color = COLORS['accent_teal']
            bg = COLORS['accent_teal_subtle']

        self.setStyleSheet(
            f"background-color: {bg}; border: 1px solid {color}40; "
            f"border-radius: 12px;"
        )
        self.dot.setStyleSheet(f"color: {color}; font-size: 9px;")
        self.text_lbl.setStyleSheet(f"color: {color};")


class SegmentedTab(QFrame):
    """Linear-style segmented tab switcher."""

    tab_changed = Signal(int)

    def __init__(self, tabs: list[str], current_index: int = 0, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {COLORS['bg_panel_alt']}; "
            f"border: 1px solid {COLORS['border_subtle']}; "
            f"border-radius: 6px;"
        )
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.layout.setSpacing(2)

        self.buttons: list[QPushButton] = []
        self._current_index = current_index

        for idx, tab_name in enumerate(tabs):
            btn = QPushButton(tab_name)
            btn.setCheckable(False)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda ch, i=idx: self._on_click(i))
            self.buttons.append(btn)
            self.layout.addWidget(btn)

        self._refresh_styles()

    def _on_click(self, index: int):
        if index != self._current_index:
            self._current_index = index
            self._refresh_styles()
            self.tab_changed.emit(index)

    def set_index(self, index: int):
        self._current_index = index
        self._refresh_styles()

    def _refresh_styles(self):
        for i, btn in enumerate(self.buttons):
            if i == self._current_index:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {COLORS['bg_card']}; "
                    f"color: {COLORS['accent_lime']}; border: 1px solid {COLORS['border']}; "
                    f"border-radius: 4px; font-weight: 700; font-size: 10px; padding: 3px 10px; "
                    f"font-family: 'Consolas', monospace; letter-spacing: 0.5px; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; "
                    f"color: {COLORS['text_secondary']}; border: none; "
                    f"border-radius: 4px; font-weight: 600; font-size: 10px; padding: 3px 10px; "
                    f"font-family: 'Consolas', monospace; letter-spacing: 0.5px; }}"
                    f"QPushButton:hover {{ color: {COLORS['text_primary']}; background-color: {COLORS['bg_card_hover']}; }}"
                )


class EmptyStateWidget(QFrame):
    """Calm, functional empty state placeholder."""

    def __init__(self, title: str, description: str, icon_str: str = "✓", parent=None):
        super().__init__(parent)
        self.setStyleSheet(card_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon_str)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 24px;")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)


class ConfirmationModal(QDialog):
    """Refined developer-grade confirmation dialog for destructive or disruptive operations."""

    def __init__(self, parent, title: str, action_name: str, target_desc: str,
                 impact_desc: str, is_destructive: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(460)
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Eyebrow / Warning
        eyebrow = QLabel("CONFIRMATION REQUIRED")
        eyebrow.setStyleSheet(
            f"color: {COLORS['amber'] if not is_destructive else COLORS['red']}; "
            f"font-size: 10px; font-weight: 700; letter-spacing: 1px; "
            f"font-family: 'Consolas', monospace;"
        )
        layout.addWidget(eyebrow)

        action_title = QLabel(action_name)
        action_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        action_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(action_title)

        # Details box
        box = QFrame()
        box.setStyleSheet(panel_alt_style())
        bl = QVBoxLayout(box)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(6)

        t_lbl = QLabel(f"<b>Target:</b> {target_desc}")
        t_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
        bl.addWidget(t_lbl)

        imp_lbl = QLabel(f"<b>Potential Impact:</b> {impact_desc}")
        imp_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        imp_lbl.setWordWrap(True)
        bl.addWidget(imp_lbl)

        layout.addWidget(box)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        confirm_btn = QPushButton("Authorize Action")
        confirm_btn.setFixedHeight(34)
        confirm_btn.setMinimumWidth(130)
        if is_destructive:
            confirm_btn.setProperty("danger", "true")
            confirm_btn.setStyleSheet(
                f"background-color: #2E1517; color: {COLORS['red']}; "
                f"border: 1px solid {COLORS['red']}; font-weight: bold; border-radius: 6px;"
            )
        else:
            confirm_btn.setProperty("primary", "true")
            confirm_btn.setStyleSheet(
                f"background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
                f"border: 1px solid {COLORS['accent_lime']}; font-weight: bold; border-radius: 6px;"
            )
        confirm_btn.clicked.connect(self.accept)
        btn_box.addWidget(confirm_btn)

        layout.addLayout(btn_box)
