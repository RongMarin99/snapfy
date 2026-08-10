"""
Snapfy New Version Available Dialog - downloads and silently installs the
update in place (Inno Setup /VERYSILENT), then restarts the app.
"""

import subprocess
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QProgressBar, QApplication, QMessageBox
)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QIcon

from app.core.settings import settings_manager
from app.core.updater import UpdateInfo
from app.core.logger import logger
from app.workers.update_worker import UpdateDownloadWorker
from app.utils.resources import resource_path

# Inno Setup silent-install switches: no UI, auto-close/relaunch the running
# app (CloseApplications/RestartApplications are enabled in installer.iss).
SILENT_INSTALL_ARGS = [
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
    "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS",
]


class UpdateDialog(QDialog):
    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.download_worker = None

        self.setWindowTitle("Snapfy - Update Available")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.setFixedSize(480, 440)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #CBD5E1; }
            QTextEdit {
                background-color: #1E293B; border: 1px solid #475569; border-radius: 6px;
                padding: 8px; color: #F8FAFC;
            }
            QPushButton {
                background-color: #0EA5E9; color: white; border-radius: 6px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0284C7; }
            QPushButton:disabled { background-color: #334155; color: #64748B; }
            QProgressBar {
                background-color: #1E293B; border: 1px solid #334155; border-radius: 6px;
                text-align: center; color: #F8FAFC;
            }
            QProgressBar::chunk { background-color: #10B981; border-radius: 6px; }
        """)

        layout = QVBoxLayout(self)

        title_lbl = QLabel(f"🚀 New Version Available: v{info.latest_version}")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(title_lbl)

        current_lbl = QLabel(f"You're running v{info.current_version}")
        current_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(current_lbl)

        layout.addWidget(QLabel("What's new:"))
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(info.release_notes or "(No release notes provided.)")
        layout.addWidget(notes, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()

        self.skip_btn = QPushButton("Skip This Version")
        self.skip_btn.setStyleSheet("background-color: #475569;")
        self.skip_btn.clicked.connect(self._on_skip)

        self.later_btn = QPushButton("Remind Me Later")
        self.later_btn.setStyleSheet("background-color: #64748B;")
        self.later_btn.clicked.connect(self.reject)

        self.update_btn = QPushButton("⬇ Update Now" if info.is_installer else "🌐 Open Release Page")
        self.update_btn.setStyleSheet("background-color: #10B981;")
        self.update_btn.clicked.connect(self._on_update_clicked)

        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.later_btn)
        btn_row.addWidget(self.update_btn)
        layout.addLayout(btn_row)

    def _on_update_clicked(self):
        if not self.info.is_installer:
            # No installer asset attached to the release - fall back to manual download.
            QDesktopServices.openUrl(QUrl(self.info.release_url))
            self.accept()
            return

        self.skip_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setText("Downloading update...")

        self.download_worker = UpdateDownloadWorker(self.info)
        self.download_worker.progress_updated.connect(self._on_download_progress)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.download_failed.connect(self._on_download_failed)
        self.download_worker.start()

    def _on_download_progress(self, percent: float):
        self.progress_bar.setValue(int(percent))

    def _on_download_finished(self, installer_path: str):
        self.status_lbl.setText("Installing update...")
        try:
            subprocess.Popen([installer_path, *SILENT_INSTALL_ARGS], close_fds=True)
        except Exception as e:
            logger.error(f"Failed to launch installer: {e}")
            QMessageBox.critical(self, "Update Failed", f"Could not launch the installer:\n{e}")
            self._reset_buttons()
            return

        # Installer's Restart Manager will close & relaunch us; quit now so
        # it can overwrite our own running exe without a file lock conflict.
        self.accept()
        QApplication.instance().quit()

    def _on_download_failed(self, error_msg: str):
        QMessageBox.critical(
            self, "Download Failed",
            f"Could not download the update:\n{error_msg}\n\nYou can download it manually instead."
        )
        self._reset_buttons()

    def _reset_buttons(self):
        self.skip_btn.setEnabled(True)
        self.later_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_lbl.setText("")

    def _on_skip(self):
        settings_manager.set("skipped_update_version", self.info.latest_version)
        self.reject()
