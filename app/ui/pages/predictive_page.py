"""
Predictive Alerts Page — Displays time-series trend projections,
growth rates, and early warnings before thresholds are breached.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style, severity_badge_style
from app.analysis.predictive_engine import PredictiveAlert


class PredictiveAlertCard(QFrame):
    """Card widget for a single predictive alert."""

    def __init__(self, alert: PredictiveAlert, parent=None):
        super().__init__(parent)
        sev_color = COLORS['red'] if alert.severity == "Critical" else COLORS['amber']
        self.setStyleSheet(card_style(f"border-left: 4px solid {sev_color};"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        metric_badge = QLabel(alert.metric.upper())
        metric_badge.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['accent_cyan']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(metric_badge)

        headline = QLabel(alert.headline)
        headline.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        headline.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(headline, 1)

        conf_label = QLabel(f"Confidence: {alert.confidence}")
        conf_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        header.addWidget(conf_label)
        layout.addLayout(header)

        # Projections & Rates
        stats_row = QHBoxLayout()
        if alert.projected_minutes is not None:
            time_lbl = QLabel(f"⏱️ Estimated Pressure Window: ~{alert.projected_minutes:.0f} minutes")
            time_lbl.setStyleSheet(f"color: {sev_color}; font-weight: bold; font-size: 12px;")
            stats_row.addWidget(time_lbl)
        
        rate_lbl = QLabel(f"📈 Rate of Change: {alert.current_rate_per_min:+.1f} MB/min")
        rate_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        stats_row.addWidget(rate_lbl)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Evidence
        ev_lbl = QLabel(f"📊 Evidence: {alert.evidence}")
        ev_lbl.setWordWrap(True)
        ev_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(ev_lbl)

        # Prevention
        prev_lbl = QLabel(f"💡 Recommended Prevention: {alert.prevention_action}")
        prev_lbl.setWordWrap(True)
        prev_lbl.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px; font-weight: 500;")
        layout.addWidget(prev_lbl)

        # Assumptions & Limitations
        meta_row = QVBoxLayout()
        meta_row.setSpacing(2)
        ass_lbl = QLabel(f"Assumptions: {alert.assumptions}")
        ass_lbl.setWordWrap(True)
        ass_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-style: italic;")
        meta_row.addWidget(ass_lbl)

        lim_lbl = QLabel(f"Limitations: {alert.limitations}")
        lim_lbl.setWordWrap(True)
        lim_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-style: italic;")
        meta_row.addWidget(lim_lbl)
        layout.addLayout(meta_row)


class PredictivePage(QWidget):
    """Page displaying predictive analytics and early warning alerts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._alerts: list[PredictiveAlert] = []
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
        title = QLabel("🔮 Predictive Performance Engine")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel(
            "Analyzes rolling time-series trend slopes across CPU, RAM, swap, and disk activity. "
            "Detects steadily climbing resource consumption and projects potential saturation windows early."
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        desc.setWordWrap(True)
        title_box.addWidget(desc)
        self.layout_main.addLayout(title_box)

        # Alerts Container
        self.alerts_layout = QVBoxLayout()
        self.alerts_layout.setSpacing(12)
        self.layout_main.addLayout(self.alerts_layout)

        # Default Empty State
        self.empty_card = QFrame()
        self.empty_card.setStyleSheet(card_style())
        ec_layout = QVBoxLayout(self.empty_card)
        ec_layout.setContentsMargins(20, 30, 20, 30)

        empty_icon = QLabel("✅")
        empty_icon.setFont(QFont("Segoe UI", 32))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ec_layout.addWidget(empty_icon)

        empty_lbl = QLabel("No Impending Resource Saturation Detected")
        empty_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        empty_lbl.setStyleSheet(f"color: {COLORS['green']};")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ec_layout.addWidget(empty_lbl)

        empty_sub = QLabel(
            "All resource slopes are stable or fluctuating within normal tolerances. "
            "OSense requires at least 4 rolling samples to build regression confidence intervals."
        )
        empty_sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_sub.setWordWrap(True)
        ec_layout.addWidget(empty_sub)

        self.alerts_layout.addWidget(self.empty_card)
        self.layout_main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def update_predictions(self, alerts: list[PredictiveAlert]):
        """Update the list of predictive warnings."""
        self._alerts = alerts

        # Clear existing
        while self.alerts_layout.count():
            item = self.alerts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not alerts:
            self.alerts_layout.addWidget(self.empty_card)
            return

        for a in alerts:
            card = PredictiveAlertCard(a)
            self.alerts_layout.addWidget(card)
