"""
Automated tests for DiagnosisWorker and the Diagnose My PC workflow.
"""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer
from app.monitoring.system_monitor import SystemMonitor
from app.analysis.engine import AnalysisEngine
from app.recommendations.engine import RecommendationEngine
from app.database.db_manager import DatabaseManager
from app.workers.monitor_worker import DiagnosisWorker


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_diagnosis_worker_end_to_end(qapp, tmp_path):
    """Test full multi-sample diagnosis worker execution."""
    db_file = tmp_path / "diag_test.db"
    db = DatabaseManager(str(db_file))
    monitor = SystemMonitor()
    analysis = AnalysisEngine()
    recommender = RecommendationEngine()

    worker = DiagnosisWorker(monitor, analysis, recommender, db)
    loop = QEventLoop()

    progress_messages = []
    received_report = {}
    errors = []

    def on_progress(msg):
        progress_messages.append(msg)

    def on_complete(report):
        received_report['data'] = report
        loop.quit()

    def on_error(err):
        errors.append(err)
        loop.quit()

    worker.progress_update.connect(on_progress)
    worker.diagnosis_complete.connect(on_complete)
    worker.error_occurred.connect(on_error)

    # Fallback timeout
    QTimer.singleShot(15000, loop.quit)

    worker.start()
    loop.exec()

    assert not errors, f"Diagnosis worker failed with errors: {errors}"
    assert 'data' in received_report, "Diagnosis worker did not complete in time"
    report = received_report['data']

    assert report['samples_collected'] == 3
    assert 'health_score' in report
    assert 'diagnoses' in report
    assert 'recommendations' in report
    assert 'snapshot' in report
    assert 'top_processes' in report
    assert len(progress_messages) >= 4

    # Verify that database stored the diagnosis
    stored_diags = db.get_diagnoses()
    assert len(stored_diags) >= 1
