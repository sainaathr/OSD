"""OSense — Intelligent Operating System Health & Resource Assistant"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OSense")
    app.setOrganizationName("OSense")
    
    # Set global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Apply global stylesheet
    from app.ui.styles import get_global_stylesheet
    app.setStyleSheet(get_global_stylesheet())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
