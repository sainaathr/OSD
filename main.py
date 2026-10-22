"""OSD — Intelligent Operating System Diagnostics & Safe Recovery Assistant"""
import sys
import os
import logging
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import threading
from osd_core.configuration.paths import get_logs_dir

log_file = os.path.join(get_logs_dir(), "app.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
)

def global_excepthook(exc_type, exc_value, exc_traceback):
    logging.critical("Uncaught top-level exception:", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_excepthook

def thread_excepthook(args):
    logging.critical("Uncaught thread exception in %s:", args.thread.name, exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

threading.excepthook = thread_excepthook

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from app.ui.main_window import MainWindow


def main():
    try:
        logging.info("Initializing QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("OSD")
        app.setOrganizationName("OSD")
        
        # Set global font
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        
        # Apply global stylesheet
        from app.ui.styles import get_global_stylesheet
        app.setStyleSheet(get_global_stylesheet())
        
        logging.info("Creating MainWindow...")
        window = MainWindow()
        logging.info("Showing MainWindow...")
        window.show()
        logging.info("Entering QApplication exec loop...")
        
        sys.exit(app.exec())
    except Exception as e:
        logging.critical("Fatal error during application execution: %s\n%s", e, traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
