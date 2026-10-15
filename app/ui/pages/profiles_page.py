"""
Workload Profiles Page — Select and customize monitoring sensitivity profiles:
Study, Coding, Gaming, Battery Saver, and Custom.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style
from app.profiles.profile_manager import ProfileManager, WorkloadProfile


class ProfileCard(QFrame):
    """Card widget for a single workload profile."""

    activated = Signal(str)

    def __init__(self, profile: WorkloadProfile, is_active: bool, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.is_active = is_active

        border = f"border: 2px solid {COLORS['accent_cyan']};" if is_active else f"border: 1px solid {COLORS['border']};"
        self.setStyleSheet(f"background-color: {COLORS['bg_card']}; {border} border-radius: 12px; padding: 18px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title_lbl = QLabel(f"{profile.icon}  {profile.display_title}")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title_lbl, 1)

        if is_active:
            active_badge = QLabel("ACTIVE")
            active_badge.setStyleSheet(
                f"background-color: {COLORS['green']}25; color: {COLORS['green']}; "
                f"border: 1px solid {COLORS['green']}60; border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 10px;"
            )
            header.addWidget(active_badge)
        layout.addLayout(header)

        # Description
        desc_lbl = QLabel(profile.description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        # Thresholds summary
        thresh_lbl = QLabel(
            f"• Thresholds: CPU Warn {profile.cpu_warning:.0f}%, RAM Warn {profile.memory_warning:.0f}%\n"
            f"• Monitoring Cadence: {profile.refresh_interval_sec}s interval"
        )
        thresh_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(thresh_lbl)

        # Action Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn = QPushButton("Active" if is_active else "Switch to Profile")
        btn.setEnabled(not is_active)
        btn.setFixedHeight(32)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_violet'] if not is_active else COLORS['bg_input']}; "
            f"color: white; border-radius: 6px; padding: 4px 16px; font-weight: bold; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_violet_dim']}; }}"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor if not is_active else Qt.CursorShape.ArrowCursor)
        btn.clicked.connect(lambda: self.activated.emit(profile.name))
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)


class ProfilesPage(QWidget):
    """Workload Profiles management page."""

    profile_changed = Signal(str)

    def __init__(self, manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.manager = manager
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
        title = QLabel("🎯 Workload Profiles")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel(
            "Customize OSense's alert sensitivities, cadence, and recommendation focus "
            "depending on your current task. Choose a profile below."
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)
        self.layout_main.addLayout(title_box)

        # Grid of profile cards
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        self.layout_main.addLayout(self.grid)

        self.layout_main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh_profiles()

    def refresh_profiles(self):
        """Render all profile cards with current active selection."""
        # Clear existing
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active_name = self.manager.get_active_profile_name()
        profiles = list(self.manager.profiles.values())

        for idx, prof in enumerate(profiles):
            is_active = (prof.name == active_name)
            card = ProfileCard(prof, is_active)
            card.activated.connect(self._on_profile_activated)
            row = idx // 2
            col = idx % 2
            self.grid.addWidget(card, row, col)

    def _on_profile_activated(self, name: str):
        if self.manager.set_active_profile(name):
            prof = self.manager.get_active_profile()
            QMessageBox.information(
                self, "Profile Activated",
                f"Switched active profile to: <b>{prof.display_title}</b>.<br><br>"
                f"Diagnostic thresholds, alert sensitivities, and monitoring cadence updated."
            )
            self.refresh_profiles()
            self.profile_changed.emit(name)
