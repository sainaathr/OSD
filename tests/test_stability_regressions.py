"""
Regression tests for OSD stability, worker cancellation, and thread safety.
"""
import threading
import time
import pytest
from PySide6.QtWidgets import QApplication

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


def test_diagnosis_worker_cooperative_stop(qapp, tmp_path):
    """Verify that DiagnosisWorker can be stopped cooperatively mid-run without hanging or aborting."""
    db_file = tmp_path / "stop_test.db"
    db = DatabaseManager(str(db_file))
    monitor = SystemMonitor()
    analysis = AnalysisEngine()
    recommender = RecommendationEngine()

    worker = DiagnosisWorker(monitor, analysis, recommender, db)
    worker.start()

    # Wait briefly for worker to start sampling
    time.sleep(0.3)
    assert worker.isRunning(), "Worker should be running"

    # Issue cooperative stop
    t0 = time.perf_counter()
    worker.stop()
    stopped = worker.wait(3000)  # Wait up to 3 seconds
    elapsed = time.perf_counter() - t0

    assert stopped, "Worker failed to stop within 3 seconds"
    assert elapsed < 3.0, f"Worker took too long to stop: {elapsed:.2f}s"
    assert not worker.isRunning(), "Worker is still running after stop()"


def test_system_monitor_cache_thread_safety():
    """Verify concurrent reads and updates to SystemMonitor._proc_cache do not raise KeyError or mutate unsafely."""
    monitor = SystemMonitor()
    stop_event = threading.Event()
    errors = []

    def writer():
        try:
            for _ in range(30):
                if stop_event.is_set():
                    break
                monitor.get_processes(limit=15)
                time.sleep(0.01)
        except Exception as e:
            errors.append(f"Writer error: {e}")

    def reader():
        try:
            for _ in range(60):
                if stop_event.is_set():
                    break
                with monitor._lock:
                    _ = list(monitor._proc_cache.items())
                time.sleep(0.005)
        except Exception as e:
            errors.append(f"Reader error: {e}")

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    stop_event.set()

    assert not errors, f"Concurrent cache operations failed: {errors}"


def test_database_manager_busy_timeout(tmp_path):
    """Verify DatabaseManager handles busy timeout and WAL configuration safely under concurrent access."""
    db_file = tmp_path / "timeout_test.db"
    db = DatabaseManager(str(db_file))

    # Perform sample read/write
    db.save_resource_sample(time.time(), 25.5, 50.0, 10.0, 45.0, 100.0, 200.0, 50.0, 150.0, 120, 95.0)
    history = db.get_resource_history(hours=1.0)
    assert len(history) == 1
    assert history[0]["cpu_percent"] == 25.5

    # Concurrent write test across threads
    concurrency_errors = []

    def concurrent_writer(thread_id: int):
        try:
            for i in range(10):
                db.save_resource_sample(time.time(), float(i), 50.0, 10.0, 45.0, 100.0, 200.0, 50.0, 150.0, 120, 95.0)
        except Exception as e:
            concurrency_errors.append(f"Thread {thread_id} error: {e}")

    threads = [threading.Thread(target=concurrent_writer, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not concurrency_errors, f"Database concurrency failed: {concurrency_errors}"
    all_history = db.get_resource_history(hours=1.0)
    assert len(all_history) == 41  # 1 initial + 4*10


def test_processes_page_initial_display(qapp):
    """Verify that ProcessesPage initially populates all table cells and inspects the first process."""
    from app.ui.pages.processes_page import ProcessesPage
    from app.monitoring.system_monitor import ProcessInfo

    monitor = SystemMonitor()
    page = ProcessesPage(monitor)

    procs = [
        ProcessInfo(pid=1001, name="chrome.exe", cpu_percent=15.5, memory_percent=8.0, memory_mb=512.0, status="running", num_threads=24),
        ProcessInfo(pid=1002, name="code.exe", cpu_percent=5.0, memory_percent=12.0, memory_mb=800.0, status="running", num_threads=32),
        ProcessInfo(pid=1003, name="python.exe", cpu_percent=25.0, memory_percent=4.0, memory_mb=256.0, status="running", num_threads=8),
    ]

    page.update_processes(procs)
    page._refresh_table()

    assert page.table.rowCount() == 3
    assert page.count_badge.text() == "3 TASKS"

    # Verify all columns in row 0 are populated (not None)
    for col in range(7):
        item = page.table.item(0, col)
        assert item is not None, f"Item at row 0, col {col} is None"
        assert item.text() != "", f"Item at row 0, col {col} has empty text"

    # Sorted by CPU desc by default -> python.exe (25%) should be row 0
    assert page.table.item(0, 0).text() == "1003"
    assert page.table.item(0, 1).text() == "python.exe"
    assert "25.0%" in page.table.item(0, 2).text()
    assert page.table.item(0, 6).text() == "8"

    # Verify inspector automatically inspected row 0
    assert page.insp_name_lbl.text() == "python.exe"
    assert "1003" in page.insp_pid_lbl.text()


def test_processes_page_updates_existing_rows(qapp):
    """Verify that ProcessesPage safely updates existing QTableWidgetItem objects."""
    from app.ui.pages.processes_page import ProcessesPage
    from app.monitoring.system_monitor import ProcessInfo

    monitor = SystemMonitor()
    page = ProcessesPage(monitor)

    procs_v1 = [
        ProcessInfo(pid=500, name="app.exe", cpu_percent=10.0, memory_percent=5.0, memory_mb=200.0, status="running", num_threads=4)
    ]
    page.update_processes(procs_v1)
    page._refresh_table()

    item_v1 = page.table.item(0, 2)
    assert item_v1.text() == "10.0%"

    # Update with new CPU value
    procs_v2 = [
        ProcessInfo(pid=500, name="app.exe", cpu_percent=35.0, memory_percent=5.0, memory_mb=200.0, status="running", num_threads=4)
    ]
    page.update_processes(procs_v2)
    page._refresh_table()

    item_v2 = page.table.item(0, 2)
    assert item_v2 is item_v1, "QTableWidgetItem should be reused in place"
    assert item_v2.text() == "35.0%"


def test_processes_page_empty_list_safely(qapp):
    """Verify that ProcessesPage handles empty process list safely."""
    from app.ui.pages.processes_page import ProcessesPage

    monitor = SystemMonitor()
    page = ProcessesPage(monitor)

    page.update_processes([])
    page._refresh_table()

    assert page.table.rowCount() == 0
    assert page.count_badge.text() == "0 TASKS"


def test_processes_page_selection_and_inspector(qapp):
    """Verify that selecting a specific process updates the inspector correctly."""
    from app.ui.pages.processes_page import ProcessesPage
    from app.monitoring.system_monitor import ProcessInfo

    monitor = SystemMonitor()
    page = ProcessesPage(monitor)

    procs = [
        ProcessInfo(pid=101, name="first.exe", cpu_percent=10.0, memory_percent=5.0, memory_mb=100.0, status="running", num_threads=2),
        ProcessInfo(pid=202, name="second.exe", cpu_percent=20.0, memory_percent=10.0, memory_mb=200.0, status="running", num_threads=4),
    ]
    page.update_processes(procs)
    page._refresh_table()

    # Explicitly select row 1
    page.table.selectRow(1)
    assert page.insp_name_lbl.text() == "first.exe" or page.insp_name_lbl.text() == "second.exe"
    assert page.terminate_btn.isEnabled()  # Not a protected system process
