"""
Snapfy Downloader Pro - Main Application Launcher
"""

import sys
import os

# Add root project folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.database.models import init_db
from app.ui.main_window import MainWindow
from app.core.logger import logger

def main():
    logger.info("Initializing Snapfy Downloader Pro...")

    # Initialize SQLite Database
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Snapfy Downloader Pro")
    app.setStyle("Fusion")

    main_window = MainWindow()
    main_window.show()

    logger.info("Snapfy Downloader Pro UI launched successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
