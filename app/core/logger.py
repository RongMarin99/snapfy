"""
Snapfy Logger Module
"""

import os
import sys
import logging
from datetime import datetime
from PySide6.QtCore import QObject, Signal

class QtLogHandler(logging.Handler, QObject):
    log_signal = Signal(str, str, str)  # (level, timestamp, message)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        self.log_signal.emit(record.levelname, timestamp, msg)

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

        # File Handler
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f"{today_str}.log")

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

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

    def network(self, msg: str):
        self.logger.info(f"[NETWORK] {msg}")

    def scraper(self, msg: str):
        self.logger.info(f"[SCRAPER] {msg}")

logger = AppLogger()
