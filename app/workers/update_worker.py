"""
Snapfy Background Update QThread Workers (check + download)
"""

import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.updater import check_for_update, download_installer, UpdateInfo
from app.core.logger import logger


class UpdateCheckWorker(QThread):
    update_available = Signal(object)  # UpdateInfo
    no_update = Signal()
    check_failed = Signal(str)

    def run(self):
        try:
            info = check_for_update()
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            self.check_failed.emit(str(e))
            return

        if info:
            self.update_available.emit(info)
        else:
            self.no_update.emit()


class UpdateDownloadWorker(QThread):
    progress_updated = Signal(float)   # percent 0-100
    download_finished = Signal(str)    # path to downloaded installer
    download_failed = Signal(str)

    def __init__(self, info: UpdateInfo):
        super().__init__()
        self._info = info

    def run(self):
        dest_path = Path(tempfile.gettempdir()) / f"Snapfy-Setup-v{self._info.latest_version}.exe"
        try:
            download_installer(
                self._info.download_url,
                dest_path,
                progress_callback=lambda pct: self.progress_updated.emit(pct),
            )
        except Exception as e:
            logger.error(f"Installer download failed: {e}")
            self.download_failed.emit(str(e))
            return

        self.download_finished.emit(str(dest_path))
