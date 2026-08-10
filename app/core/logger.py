"""
Snapfy Logger Module
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject

class QtLogHandler(logging.Handler, QObject):
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        self.format(record)

class AppLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        self.logger = logging.getLogger("Snapfy")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File Handler - must be a writable, user-owned dir. A frozen exe installed
        # under Program Files runs with cwd there too, which non-admin users can't
        # write to; os.getcwd()/logs would throw PermissionError before the GUI
        # even starts (silent crash, no window, no console to show the error).
        logs_dir = Path.home() / ".snapfy" / "logs"
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            today_str = datetime.now().strftime("%Y-%m-%d")
            log_file = logs_dir / f"{today_str}.log"

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except OSError:
            # Never let logging setup itself crash the app - console handler still works.
            pass

        # Qt Signal Handler
        self.qt_handler = QtLogHandler()
        self.qt_handler.setFormatter(formatter)
        self.logger.addHandler(self.qt_handler)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def scraper(self, msg: str):
        self.logger.info(f"[SCRAPER] {msg}")

logger = AppLogger()
