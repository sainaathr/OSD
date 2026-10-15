"""
Recommendations Page — Displays actionable recommendations from the analysis engine.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style
from app.monitoring.system_monitor import SystemMonitor
from app.recommendations.engine import Recommendation


class RecommendationCard(QFrame):
    """Card for a single recommendation."""
    
    def __init__(self, rec: Recommendation, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.monitor = monitor
        
        risk_colors = {
            'Low': COLORS['green'],
            'Medium': COLORS['amber'],
            'High': COLORS['red'],
        }
        border_color = risk_colors.get(rec.risk_level, COLORS['border'])
        self.setStyleSheet(card_style(f"border-left: 4px solid {border_color};"))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        problem_label = QLabel(f"⚠️ {rec.problem}")
        problem_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        problem_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        problem_label.setWordWrap(True)
        header.addWidget(problem_label, 1)
        
        risk_label = QLabel(f"Risk: {rec.risk_level}")
        risk_label.setStyleSheet(
            f"color: {border_color}; background-color: {border_color}15; "
            f"border: 1px solid {border_color}40; border-radius: 4px; "
            f"padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(risk_label)
        layout.addLayout(header)
        
        # Evidence
        if rec.evidence:
            ev = QLabel(f"📊 {rec.evidence}")
            ev.setWordWrap(True)
            ev.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            layout.addWidget(ev)
        
        # Action
        if rec.action:
            act = QLabel(f"💡 Action: {rec.action}")
            act.setWordWrap(True)
            act.setStyleSheet(f"color: {COLORS['accent_cyan']}; font-size: 12px;")
            layout.addWidget(act)
        
        # Benefit
        if rec.benefit:
            ben = QLabel(f"✅ Benefit: {rec.benefit}")
            ben.setWordWrap(True)
            ben.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px;")
            layout.addWidget(ben)
        
        # Action button
        if rec.action_type == "close_app" and rec.target_pid and rec.target_process:
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            end_btn = QPushButton(f"End {rec.target_process}")
            end_btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['red']}; color: white; "
                f"border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 11px; }}"
                f"QPushButton:hover {{ background-color: {COLORS['red_dim']}; }}"
            )
            end_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            end_btn.clicked.connect(lambda: self._terminate_process())
            btn_layout.addWidget(end_btn)
            layout.addLayout(btn_layout)
    
    def _terminate_process(self):
        rec = self.rec
        reply = QMessageBox.question(
            self, "Confirm Process Termination",
            f"Are you sure you want to terminate {rec.target_process} (PID {rec.target_pid})?\n\n"
            f"This may cause unsaved work to be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.monitor.terminate_process(rec.target_pid, rec.target_process)
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.warning(self, "Failed", msg)


class RecommendationsPage(QWidget):
    """Page displaying current recommendations."""
    
    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self._setup_ui()
    
    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(12)
        
        # Header
        title = QLabel("💡 Smart Recommendations")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.main_layout.addWidget(title)
        
        desc = QLabel("Evidence-based suggestions to improve system performance. "
                      "Each recommendation is backed by observed metrics.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        desc.setWordWrap(True)
        self.main_layout.addWidget(desc)
        
        self.recs_layout = QVBoxLayout()
        self.recs_layout.setSpacing(10)
        self.main_layout.addLayout(self.recs_layout)
        
        # Default state
        self.empty_label = QLabel("✅ No recommendations — system is operating well.")
        self.empty_label.setStyleSheet(f"color: {COLORS['green']}; font-size: 14px; padding: 20px 0;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recs_layout.addWidget(self.empty_label)
        
        self.main_layout.addStretch()
        
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
    
    def update_recommendations(self, recommendations: list[Recommendation]):
        """Update displayed recommendations."""
        # Clear
        while self.recs_layout.count():
            item = self.recs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not recommendations:
            label = QLabel("✅ No recommendations — system is operating well.")
            label.setStyleSheet(f"color: {COLORS['green']}; font-size: 14px; padding: 20px 0;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.recs_layout.addWidget(label)
            return
        
        count_label = QLabel(f"📋 {len(recommendations)} recommendation(s) based on current system state")
        count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        self.recs_layout.addWidget(count_label)
        
        for rec in recommendations:
            card = RecommendationCard(rec, self.monitor)
            self.recs_layout.addWidget(card)
