"""
Recovery Page — Autonomous Recovery Advisor & Verification
Safe, transparent recovery workflow:
Detect -> Investigate -> Recommend -> Obtain Consent -> Execute -> Verify.
Displays issue, recommended fix, expected benefit, disruption, confirmation, and before-and-after results.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style, panel_alt_style
from app.ui.components import PageHeader, ConfirmationModal, EmptyStateWidget
from app.recommendations.recovery_advisor import RecoveryAdvisor, RecoveryPlan, RecoveryVerification


class RecoveryPlanCard(QFrame):
    """
    Evidence-led recovery plan card.
    Clearly displays issue, fix, benefit, disruption risk, and before-after verification.
    """

    action_executed = Signal(object)  # RecoveryVerification

    def __init__(self, plan: RecoveryPlan, advisor: RecoveryAdvisor, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.advisor = advisor

        # Restrained border indicator based on risk
        risk = plan.risk_level.lower()
        if 'high' in risk or 'crit' in risk:
            border_color = COLORS['red']
        elif 'med' in risk:
            border_color = COLORS['amber']
        else:
            border_color = COLORS['accent_teal']

        self.setStyleSheet(card_style(f"border-left: 3px solid {border_color};"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header: Title + Risk Pill
        header = QHBoxLayout()
        header.setSpacing(10)

        title_lbl = QLabel(plan.issue_title)
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title_lbl, 1)

        risk_lbl = QLabel(f"RISK: {plan.risk_level.upper()}")
        risk_lbl.setStyleSheet(
            f"color: {border_color}; background-color: {border_color}18; "
            f"border: 1px solid {border_color}40; border-radius: 4px; padding: 2px 7px; "
            f"font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;"
        )
        header.addWidget(risk_lbl)
        layout.addLayout(header)

        # Inset Technical Details Box
        details_box = QFrame()
        details_box.setStyleSheet(panel_alt_style())
        dbl = QVBoxLayout(details_box)
        dbl.setContentsMargins(14, 12, 14, 12)
        dbl.setSpacing(8)

        # Target & Proposed Fix
        fix_row = QHBoxLayout()
        target_lbl = QLabel(f"TARGET: <b>{plan.target_process}</b> (PID {plan.target_pid})")
        target_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-family: 'Consolas', monospace;")
        fix_row.addWidget(target_lbl)
        fix_row.addStretch()
        dbl.addLayout(fix_row)

        fix_lbl = QLabel(f"<b>Proposed Fix:</b> {plan.proposed_fix}")
        fix_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 12px;")
        dbl.addWidget(fix_lbl)

        # Benefit
        ben_lbl = QLabel(f"<b>Expected Benefit:</b> {plan.expected_benefit}")
        ben_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 12px;")
        dbl.addWidget(ben_lbl)

        # Disruption Assessment
        disr_text = getattr(plan, 'disruption_desc', None) or (
            "Low disruption. Background cache buffers trimmed; application process remains alive."
            if plan.risk_level == "Low" else
            "Moderate disruption. Application will be terminated; unsaved buffers will close."
        )
        disr_lbl = QLabel(f"<b>Potential Disruption:</b> {disr_text}")
        disr_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        dbl.addWidget(disr_lbl)

        # Evidence
        if plan.evidence:
            ev_lbl = QLabel(f"<b>Observed Telemetry:</b> {plan.evidence}")
            ev_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
            dbl.addWidget(ev_lbl)

        layout.addWidget(details_box)

        # Action Button Row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        exec_btn = QPushButton("Authorize & Verify Action")
        exec_btn.setFixedHeight(34)
        is_dest = plan.risk_level.lower() in ['high', 'critical']
        if is_dest:
            exec_btn.setStyleSheet(
                f"QPushButton {{ background-color: #2E1517; color: {COLORS['red']}; "
                f"border: 1px solid {COLORS['red']}; border-radius: 6px; font-weight: 700; font-size: 11px; padding: 6px 16px; }}"
                f"QPushButton:hover {{ background-color: #3D1C1E; }}"
            )
        else:
            exec_btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
                f"border: 1px solid {COLORS['accent_lime']}; border-radius: 6px; font-weight: 700; font-size: 11px; padding: 6px 16px; }}"
                f"QPushButton:hover {{ background-color: {COLORS['accent_lime_dim']}; }}"
            )
        exec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exec_btn.clicked.connect(self._on_execute)
        btn_row.addWidget(exec_btn)
        layout.addLayout(btn_row)

    def _on_execute(self):
        plan = self.plan
        modal = ConfirmationModal(
            self,
            title="Authorize Recovery Remediation",
            action_name=f"Execute: {plan.proposed_fix}",
            target_desc=f"{plan.target_process} (PID {plan.target_pid})",
            impact_desc=f"Expected Benefit: {plan.expected_benefit}. Baseline will be sampled before action, and outcome verified post-execution.",
            is_destructive=(plan.risk_level.lower() in ['high', 'critical'])
        )

        if modal.exec() == ConfirmationModal.DialogCode.Accepted:
            # Execute and verify before/after
            verification = self.advisor.execute_and_verify(plan)
            if verification.success:
                QMessageBox.information(
                    self, "Remediation Verified",
                    f"Action Succeeded and Verified:\n\n{verification.message}\n\n"
                    f"Pre-action baseline captured and post-action outcome audited."
                )
            else:
                QMessageBox.warning(
                    self, "Remediation Aborted",
                    f"Action did not achieve expected threshold:\n\n{verification.message}"
                )
            self.action_executed.emit(verification)


class RecoveryPage(QWidget):
    """Refined Recovery Advisor view with audited outcome verification."""

    recovery_performed = Signal()

    def __init__(self, advisor: RecoveryAdvisor, parent=None):
        super().__init__(parent)
        self.advisor = advisor
        self._current_plans = []
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

        # Header
        header = PageHeader(
            eyebrow="AUTONOMOUS ADVISOR",
            title="Safe System Recovery",
            description="Six-step verification protocol: Detect → Investigate → Recommend → Consent → Execute → Verify. Every action is audited with baseline before-and-after measurements."
        )
        self.layout_main.addWidget(header)

        # Protocol Explanation Banner
        banner = QFrame()
        banner.setStyleSheet(panel_alt_style())
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(14, 10, 14, 10)
        bl.setSpacing(12)

        prot_lbl = QLabel(
            "<b>VERIFICATION GUARANTEE:</b> OSense never executes destructive tasks in the background without explicit user authorization. Every executed fix records pre/post delta metrics to SQLite."
        )
        prot_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        bl.addWidget(prot_lbl)
        self.layout_main.addWidget(banner)

        # Active Plans Header Strip
        plans_strip = QHBoxLayout()
        ps_title = QLabel("ACTIVE RECOVERY PROPOSALS")
        ps_title.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        plans_strip.addWidget(ps_title)
        plans_strip.addStretch()

        self.plans_count_lbl = QLabel("0 PENDING")
        self.plans_count_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-family: 'Consolas', monospace;")
        plans_strip.addWidget(self.plans_count_lbl)
        self.layout_main.addLayout(plans_strip)

        # Plans Container
        self.plans_layout = QVBoxLayout()
        self.plans_layout.setSpacing(10)
        self.layout_main.addLayout(self.plans_layout)

        # Initial Empty State
        self.empty_widget = EmptyStateWidget(
            "All Systems Operating Under Nominal Thresholds",
            "No automated interventions are recommended at this time. Telemetry shows stable memory retention and low thread contention."
        )
        self.plans_layout.addWidget(self.empty_widget)

        self.layout_main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def update_plans(self, plans: list[RecoveryPlan]):
        """Update live recovery proposals."""
        self._current_plans = plans
        while self.plans_layout.count():
            item = self.plans_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not plans:
            self.plans_count_lbl.setText("0 PENDING")
            self.plans_count_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-family: 'Consolas', monospace;")
            empty = EmptyStateWidget(
                "All Systems Operating Under Nominal Thresholds",
                "No automated interventions are recommended at this time. Telemetry shows stable memory retention and low thread contention."
            )
            self.plans_layout.addWidget(empty)
            return

        self.plans_count_lbl.setText(f"{len(plans)} PROPOSALS")
        self.plans_count_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-weight: 700; font-family: 'Consolas', monospace;")

        for plan in plans:
            card = RecoveryPlanCard(plan, self.advisor)
            card.action_executed.connect(self._on_action_executed)
            self.plans_layout.addWidget(card)

    def _on_action_executed(self, verification):
        self.recovery_performed.emit()
