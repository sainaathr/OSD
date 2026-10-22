"""
Script to capture screenshots of all redesigned OSD views with live data.
"""
import sys
import os
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.styles import get_global_stylesheet
from app.ui.main_window import MainWindow

app = QApplication(sys.argv)
app.setStyleSheet(get_global_stylesheet())

window = MainWindow()
window.resize(1340, 860)
window.show()

os.makedirs('app_previews', exist_ok=True)

def step_capture():
    # Wait for monitoring worker to pump a couple of snapshots
    print("Waiting 2.5s for live telemetry...")
    time.sleep(2.5)
    app.processEvents()

    # 1. Overview
    window._navigate("Overview")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/01_overview.png')
    print("Captured: 01_overview.png")

    # 2. Processes
    window._navigate("Processes")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    # Select first row in table to display inspector
    if window.processes_page.table.rowCount() > 0:
        window.processes_page.table.selectRow(0)
    app.processEvents()
    window.grab().save('app_previews/02_processes.png')
    print("Captured: 02_processes.png")

    # 3. Performance
    window._navigate("Performance")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/03_performance.png')
    print("Captured: 03_performance.png")

    # 4. Diagnosis
    window._navigate("Diagnosis")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/04_diagnosis.png')
    print("Captured: 04_diagnosis.png")

    # 5. Intelligence - Copilot
    window._navigate("Intelligence")
    window.intelligence_page._on_subtab_changed(0)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/05_intelligence_copilot.png')
    print("Captured: 05_intelligence_copilot.png")

    # 6. Intelligence - Predictive Forecasts
    window.intelligence_page.nav_tabs.set_index(1)
    window.intelligence_page._on_subtab_changed(1)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/06_intelligence_predictive.png')
    print("Captured: 06_intelligence_predictive.png")

    # 7. Intelligence - What-If Simulator
    window.intelligence_page.nav_tabs.set_index(2)
    window.intelligence_page._on_subtab_changed(2)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/07_intelligence_simulator.png')
    print("Captured: 07_intelligence_simulator.png")

    # 8. Intelligence - Workload Profiles
    window.intelligence_page.nav_tabs.set_index(3)
    window.intelligence_page._on_subtab_changed(3)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/08_intelligence_profiles.png')
    print("Captured: 08_intelligence_profiles.png")

    # 9. Recovery
    window._navigate("Recovery")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/09_recovery.png')
    print("Captured: 09_recovery.png")

    # 10. History
    window._navigate("History")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/10_history.png')
    print("Captured: 10_history.png")

    # 11. Settings
    window._navigate("Settings")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    window.grab().save('app_previews/11_settings.png')
    print("Captured: 11_settings.png")

    print("All captures completed successfully!")
    window.close()
    app.quit()

QTimer.singleShot(500, step_capture)
sys.exit(app.exec())
