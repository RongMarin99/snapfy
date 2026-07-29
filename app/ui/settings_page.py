"""
Snapfy Settings Dialog & View with Cookie Session Support
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QCheckBox, QFileDialog, QGroupBox,
    QFormLayout, QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt
from app.core.settings import settings_manager
from app.core.ffmpeg import ffmpeg_manager
from app.core.browser import browser_manager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Snapfy Downloader - Global Settings & Session Cookies")
        self.setFixedSize(620, 650)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: bold;
                color: #38BDF8;
            }
            QLabel {
                color: #CBD5E1;
            }
            QLineEdit, QSpinBox, QTextEdit {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 10px;
                color: #F8FAFC;
            }
            QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {
                border: 1px solid #0EA5E9;
            }
            QPushButton {
                background-color: #0284C7;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QCheckBox {
                color: #F8FAFC;
                spacing: 6px;
            }
        """)

        self.init_ui()
        self.load_values()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. Download Directory Group
        dl_group = QGroupBox("Storage & Downloading")
        dl_form = QFormLayout(dl_group)

        self.dir_input = QLineEdit()
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_folder)

        dir_box = QHBoxLayout()
        dir_box.addWidget(self.dir_input)
        dir_box.addWidget(self.browse_btn)
        dl_form.addRow("Download Directory:", dir_box)

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        dl_form.addRow("Concurrent Threads:", self.threads_spin)

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(1, 10)
        dl_form.addRow("Max Retries:", self.retries_spin)

        main_layout.addWidget(dl_group)

        # 2. Session Cookies & Account Credentials
        cookie_group = QGroupBox("🔑 Account Session & Cookie Authentication")
        cookie_layout = QVBoxLayout(cookie_group)

        cookie_info = QLabel("Paste your NetShort / Platform 'Cookie' header string below to unlock VIP episodes:")
        cookie_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        cookie_layout.addWidget(cookie_info)

        self.cookie_text = QTextEdit()
        self.cookie_text.setPlaceholderText("e.g. session_id=abc123xyz; visitor_token=...; auth_key=...")
        self.cookie_text.setMaximumHeight(80)
        cookie_layout.addWidget(self.cookie_text)

        main_layout.addWidget(cookie_group)

        # 2b. NetShort API Key
        api_group = QGroupBox("🔗 NetShort API Key (api.anichin.bio)")
        api_form = QFormLayout(api_group)

        self.netshort_api_key_input = QLineEdit()
        self.netshort_api_key_input.setPlaceholderText("e.g. TRIAL-ANICHIN-2026")
        api_form.addRow("API Key:", self.netshort_api_key_input)

        main_layout.addWidget(api_group)

        # 3. Browser & Automation Settings
        browser_group = QGroupBox("Chromium Automation & Network")
        b_form = QFormLayout(browser_group)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://user:pass@host:port")
        b_form.addRow("HTTP/HTTPS Proxy:", self.proxy_input)

        self.headless_check = QCheckBox("Run Browser in Headless Mode (Background)")
        b_form.addRow("", self.headless_check)

        self.gpu_check = QCheckBox("Enable Hardware / GPU Acceleration")
        b_form.addRow("", self.gpu_check)

        self.ssl_verify_check = QCheckBox("Disable SSL Certificate Verification (insecure - only if antivirus/proxy blocks downloads)")
        b_form.addRow("", self.ssl_verify_check)

        main_layout.addWidget(browser_group)

        # 4. FFmpeg Configuration
        ff_group = QGroupBox("FFmpeg Converter")
        ff_form = QFormLayout(ff_group)

        self.ffmpeg_input = QLineEdit()
        self.ffmpeg_browse = QPushButton("Locate...")
        self.ffmpeg_browse.clicked.connect(self.browse_ffmpeg)
        ff_box = QHBoxLayout()
        ff_box.addWidget(self.ffmpeg_input)
        ff_box.addWidget(self.ffmpeg_browse)
        ff_form.addRow("FFmpeg Binary Path:", ff_box)

        self.status_ffmpeg_lbl = QLabel()
        ff_form.addRow("Status:", self.status_ffmpeg_lbl)

        main_layout.addWidget(ff_group)

        # Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("background-color: #10B981;")
        self.save_btn.clicked.connect(self.save_values)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #475569;")
        self.cancel_btn.clicked.connect(self.reject)

        btn_box.addWidget(self.cancel_btn)
        btn_box.addWidget(self.save_btn)

        main_layout.addLayout(btn_box)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.dir_input.text())
        if folder:
            self.dir_input.setText(folder)

    def browse_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select FFmpeg Binary", "", "Executable (*.exe);;All Files (*)")
        if file_path:
            self.ffmpeg_input.setText(file_path)

    def load_values(self):
        self.dir_input.setText(settings_manager.get("download_dir", ""))
        self.threads_spin.setValue(settings_manager.get("max_threads", 4))
        self.retries_spin.setValue(settings_manager.get("max_retries", 3))
        self.cookie_text.setPlainText(settings_manager.get("cookie_string", ""))
        self.netshort_api_key_input.setText(settings_manager.get("netshort_api_key", "TRIAL-ANICHIN-2026"))
        self.proxy_input.setText(settings_manager.get("proxy", ""))
        self.headless_check.setChecked(settings_manager.get("browser_headless", True))
        self.gpu_check.setChecked(settings_manager.get("gpu_acceleration", True))
        self.ssl_verify_check.setChecked(not settings_manager.get("ssl_verify", True))
        self.ffmpeg_input.setText(settings_manager.get("ffmpeg_path", "ffmpeg"))

        if ffmpeg_manager.is_available():
            self.status_ffmpeg_lbl.setText("✅ Installed & Ready")
            self.status_ffmpeg_lbl.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.status_ffmpeg_lbl.setText("⚠️ Not found (Binary concatenation mode will be used)")
            self.status_ffmpeg_lbl.setStyleSheet("color: #F59E0B;")

    def save_values(self):
        settings_manager.set("download_dir", self.dir_input.text().strip())
        settings_manager.set("max_threads", self.threads_spin.value())
        settings_manager.set("max_retries", self.retries_spin.value())
        settings_manager.set("cookie_string", self.cookie_text.toPlainText().strip())
        settings_manager.set("netshort_api_key", self.netshort_api_key_input.text().strip() or "TRIAL-ANICHIN-2026")
        settings_manager.set("proxy", self.proxy_input.text().strip())
        settings_manager.set("browser_headless", self.headless_check.isChecked())
        settings_manager.set("gpu_acceleration", self.gpu_check.isChecked())
        settings_manager.set("ssl_verify", not self.ssl_verify_check.isChecked())
        settings_manager.set("ffmpeg_path", self.ffmpeg_input.text().strip())

        QMessageBox.information(self, "Settings Saved", "Global settings and session cookies updated successfully.")
        self.accept()
