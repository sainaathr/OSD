"""
Diagnosis Page — Evidence-Led Technical Findings
Deep heuristic and threshold evaluation of compute, memory, disk, and process behavior.
Presents diagnoses with clear distinction between detection, evidence, causes, and next steps.
"""
import json
import os
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style, panel_alt_style, severity_badge_style
from app.ui.components import PageHeader, EmptyStateWidget
from app.utils.formatting import (
    format_bytes, format_speed, format_timestamp, severity_color,
    health_score_color, health_score_label
)
from app.monitoring.system_monitor import SystemMonitor
from app.analysis.engine import AnalysisEngine, Diagnosis, Severity
from app.recommendations.engine import RecommendationEngine
from app.database.db_manager import DatabaseManager
from app.workers.monitor_worker import DiagnosisWorker


class DiagnosisFindingCard(QFrame):
    """
    Evidence-led technical diagnosis finding card.
    Clearly distinguishes detection, evidence, probable cause, confidence, and remediation.
    """

    def __init__(self, diag: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet(card_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 1. Header: Severity + Title + Confidence
        header = QHBoxLayout()
        header.setSpacing(10)

        sev = diag.get('severity', 'Information')
        sev_label = QLabel(sev.upper())
        sev_label.setStyleSheet(severity_badge_style(sev))
        header.addWidget(sev_label)

        title = QLabel(diag.get('title', 'Unknown Diagnostic Finding'))
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title, 1)

        conf = diag.get('confidence', '')
        if conf:
            conf_label = QLabel(f"CONFIDENCE: {conf.upper()}")
            conf_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 600; "
                f"font-family: 'Consolas', monospace;"
            )
            header.addWidget(conf_label)

        layout.addLayout(header)

        # 2. Structured Technical Blocks Inset Box
        content_box = QFrame()
        content_box.setStyleSheet(panel_alt_style())
        cbl = QVBoxLayout(content_box)
        cbl.setContentsMargins(14, 12, 14, 12)
        cbl.setSpacing(8)

        # A. Observed Evidence
        evidence = diag.get('evidence', '')
        if evidence:
            ev_row = QVBoxLayout()
            ev_row.setSpacing(2)
            ev_title = QLabel("OBSERVED EVIDENCE")
            ev_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; font-family: 'Consolas', monospace;")
            ev_row.addWidget(ev_title)

            ev_lbl = QLabel(evidence)
            ev_lbl.setWordWrap(True)
            ev_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-family: 'Consolas', monospace;")
            ev_row.addWidget(ev_lbl)
            cbl.addLayout(ev_row)

        # B. Probable Causes
        cause = diag.get('probable_cause', '')
        if cause:
            cause_row = QVBoxLayout()
            cause_row.setSpacing(2)
            cause_title = QLabel("PROBABLE CAUSES")
            cause_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; font-family: 'Consolas', monospace;")
            cause_row.addWidget(cause_title)

            cause_lbl = QLabel(cause)
            cause_lbl.setWordWrap(True)
            cause_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 12px;")
            cause_row.addWidget(cause_lbl)
            cbl.addLayout(cause_row)

        # C. Recommended Next Steps
        rec = diag.get('recommendation', '')
        if rec:
            rec_row = QVBoxLayout()
            rec_row.setSpacing(2)
            rec_title = QLabel("RECOMMENDED ACTION")
            rec_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; font-family: 'Consolas', monospace;")
            rec_row.addWidget(rec_title)

            rec_lbl = QLabel(rec)
            rec_lbl.setWordWrap(True)
            rec_lbl.setStyleSheet(f"color: {COLORS['accent_lime']}; font-size: 12px; font-weight: 500;")
            rec_row.addWidget(rec_lbl)
            cbl.addLayout(rec_row)

        # D. Technical Context / Explanation
        expl = diag.get('explanation', '')
        if expl:
            expl_lbl = QLabel(expl)
            expl_lbl.setWordWrap(True)
            expl_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            cbl.addWidget(expl_lbl)

        layout.addWidget(content_box)


class DiagnosisPage(QWidget):
    """Deep system diagnosis page with manual and live heuristic audits."""

    def __init__(self, monitor: SystemMonitor, analysis: AnalysisEngine,
                 recommender: RecommendationEngine, db: DatabaseManager,
                 parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.analysis = analysis
        self.recommender = recommender
        self.db = db
        self._last_report = None
        self._diagnosis_worker = None
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

        eyebrow = QLabel("ANALYSIS & AUDITING")
        eyebrow.setStyleSheet(
            f"color: {COLORS['accent_teal']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; font-family: 'Consolas', monospace;"
        )
        title_box.addWidget(eyebrow)

        title = QLabel("System Diagnosis")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        self.status_label = QLabel("Click 'Diagnose My PC' to initiate a multi-subsystem heuristic evaluation.")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(self.status_label)

        header_row.addLayout(title_box, 1)

        # Action Buttons
        self.save_btn = QPushButton("Export Technical Report")
        self.save_btn.setFixedHeight(38)
        self.save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; color: {COLORS['text_primary']}; }}"
        )
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_report)
        self.save_btn.setEnabled(False)
        header_row.addWidget(self.save_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.diagnose_btn = QPushButton("⌕  Diagnose My PC")
        self.diagnose_btn.setFixedHeight(38)
        self.diagnose_btn.setMinimumWidth(160)
        self.diagnose_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_lime']}; color: {COLORS['text_inverse']}; "
            f"border: 1px solid {COLORS['accent_lime']}; border-radius: 6px; "
            f"font-size: 12px; font-weight: 700; padding: 8px 18px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_lime_dim']}; }}"
        )
        self.diagnose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.diagnose_btn.clicked.connect(self.run_full_diagnosis)
        header_row.addWidget(self.diagnose_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.layout_main.addLayout(header_row)

        # Results Container (Full Audit findings)
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(10)
        self.layout_main.addLayout(self.results_layout)

        # Live Stream Separator
        stream_sep = QFrame()
        stream_sep.setStyleSheet(panel_alt_style())
        ssl = QHBoxLayout(stream_sep)
        ssl.setContentsMargins(12, 8, 12, 8)
        live_title = QLabel("LIVE DIAGNOSTIC ANOMALIES & TELEMETRY STREAM")
        live_title.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        ssl.addWidget(live_title)
        ssl.addStretch()
        self.live_count_lbl = QLabel("MONITORING ACTIVE")
        self.live_count_lbl.setStyleSheet(f"color: {COLORS['accent_teal']}; font-size: 10px; font-family: 'Consolas', monospace;")
        ssl.addWidget(self.live_count_lbl)
        self.layout_main.addWidget(stream_sep)

        # Live Results Container
        self.live_results_layout = QVBoxLayout()
        self.live_results_layout.setSpacing(8)
        self.layout_main.addLayout(self.live_results_layout)

        # Initial placeholder
        self.empty_live = EmptyStateWidget(
            "No Anomalies Detected in Live Stream",
            "Hardware thresholds and process growth curves are currently within safe operating tolerances."
        )
        self.live_results_layout.addWidget(self.empty_live)

        self.layout_main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def stop(self):
        """Stop background diagnosis worker safely."""
        if self._diagnosis_worker and self._diagnosis_worker.isRunning():
            self._diagnosis_worker.stop()
            self._diagnosis_worker.wait(2000)
            if self._diagnosis_worker.isRunning():
                self._diagnosis_worker.terminate()
                self._diagnosis_worker.wait(500)

    def run_full_diagnosis(self):
        """Run a complete system diagnosis via worker thread."""
        if self._diagnosis_worker and self._diagnosis_worker.isRunning():
            return

        self.diagnose_btn.setEnabled(False)
        self.diagnose_btn.setText("Auditing System...")
        self.status_label.setText("Collecting deep snapshot and running heuristic rules...")

        # Clear previous audit results
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._diagnosis_worker = DiagnosisWorker(
            self.monitor, self.analysis, self.recommender, self.db
        )
        self._diagnosis_worker.progress_update.connect(self._on_progress)
        self._diagnosis_worker.diagnosis_complete.connect(self._on_complete)
        self._diagnosis_worker.error_occurred.connect(self._on_error)
        self._diagnosis_worker.start()

    def _on_progress(self, message: str):
        self.status_label.setText(message)

    def _on_complete(self, report: dict):
        self._last_report = report
        self.diagnose_btn.setEnabled(True)
        self.diagnose_btn.setText("⌕  Diagnose My PC")
        self.save_btn.setEnabled(True)

        hs = report.get('health_score', {})
        score = hs.get('total_score', 0)
        color = health_score_color(score)
        label_text = health_score_label(score)

        # Score Summary Frame
        score_frame = QFrame()
        score_frame.setStyleSheet(card_style())
        sl = QHBoxLayout(score_frame)
        sl.setContentsMargins(18, 14, 18, 14)
        sl.setSpacing(16)

        num_lbl = QLabel(f"{score:.0f}")
        num_lbl.setFont(QFont("Consolas", 28, QFont.Weight.Bold))
        num_lbl.setStyleSheet(f"color: {color};")
        sl.addWidget(num_lbl)

        score_details = QVBoxLayout()
        score_details.setSpacing(2)
        score_title = QLabel(f"HEALTH SCORE INDEX: {label_text.upper()}")
        score_title.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace;")
        score_details.addWidget(score_title)

        snap = report.get('snapshot', {})
        info = QLabel(
            f"CPU: {snap.get('cpu_percent', 0):.1f}%  •  "
            f"RAM: {snap.get('memory_percent', 0):.1f}%  •  "
            f"Disk: {snap.get('disk_percent', 0):.1f}%  •  "
            f"Active Tasks: {snap.get('process_count', 0)}"
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: 'Consolas', monospace;")
        score_details.addWidget(info)
        sl.addLayout(score_details, 1)

        self.results_layout.addWidget(score_frame)

        # Finding Cards
        diagnoses = report.get('diagnoses', [])
        self.status_label.setText(
            f"Audit finished at {time.strftime('%H:%M:%S')}. Found {len(diagnoses)} finding(s)."
        )

        for diag in diagnoses:
            card = DiagnosisFindingCard(diag)
            self.results_layout.addWidget(card)

    def _on_error(self, error_msg: str):
        self.diagnose_btn.setEnabled(True)
        self.diagnose_btn.setText("⌕  Diagnose My PC")
        self.status_label.setText(f"Audit encountered an error: {error_msg}")

    def update_live_diagnoses(self, diagnoses: list):
        """Update live diagnosis section."""
        while self.live_results_layout.count():
            item = self.live_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        non_healthy = [d for d in diagnoses if d.severity != Severity.HEALTHY]

        if not non_healthy:
            ok = EmptyStateWidget(
                "No Anomalies Detected in Live Stream",
                "Telemetry stream indicates all system resources are balanced."
            )
            self.live_results_layout.addWidget(ok)
            self.live_count_lbl.setText("STREAM NOMINAL")
            return

        self.live_count_lbl.setText(f"{len(non_healthy)} ANOMALIES")

        for diag in non_healthy[:5]:
            diag_dict = {
                'severity': diag.severity,
                'title': diag.title,
                'evidence': diag.evidence,
                'probable_cause': diag.probable_cause,
                'recommendation': diag.recommendation,
                'explanation': diag.explanation,
                'confidence': diag.confidence
            }
            card = DiagnosisFindingCard(diag_dict)
            self.live_results_layout.addWidget(card)

    def _save_report(self):
        """Save report to a file."""
        if not self._last_report:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Diagnostic Audit Report",
            f"OSD_Report_{time.strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        if not filename:
            return

        try:
            with open(filename, 'w') as f:
                if filename.endswith('.json'):
                    json.dump(self._last_report, f, indent=2)
                else:
                    f.write("=== OSD Diagnostic Audit Report ===\n")
                    f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    hs = self._last_report.get('health_score', {})
                    f.write(f"Health Score: {hs.get('total_score', 0):.0f}/100\n\n")
                    for d in self._last_report.get('diagnoses', []):
                        f.write(f"[{d.get('severity')}] {d.get('title')}\n")
                        f.write(f"  Evidence: {d.get('evidence')}\n")
                        f.write(f"  Cause:    {d.get('probable_cause')}\n")
                        f.write(f"  Next:     {d.get('recommendation')}\n\n")

            QMessageBox.information(self, "Report Saved", f"Report saved successfully to:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Error Saving Report", str(e))
