"""
Snapfy Cookie Importer Dialog
"""

import json
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFileDialog, QMessageBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
from app.core.settings import settings_manager
from app.core.browser import browser_manager

class CookieDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Snapfy - Add / Import Account Session Cookies")
        self.setFixedSize(580, 440)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #CBD5E1;
            }
            QTextEdit {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px;
                color: #F8FAFC;
                font-family: monospace;
            }
            QTextEdit:focus {
                border: 1px solid #0EA5E9;
            }
            QPushButton {
                background-color: #0EA5E9;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0284C7;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title_lbl = QLabel("🍪 Add / Import Session Cookies")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        sub_lbl = QLabel("Import cookies from browser extensions (EditThisCookie, Get cookies.txt) or paste HTTP Cookie headers.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")

        layout.addWidget(title_lbl)
        layout.addWidget(sub_lbl)

        # Tabs for Paste vs File Import
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 6px;
                background-color: #0F172A;
            }
            QTabBar::tab {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #0EA5E9;
                color: white;
                font-weight: bold;
            }
        """)

        # Tab 1: Paste Text
        paste_tab = QWidget()
        paste_layout = QVBoxLayout(paste_tab)
        paste_layout.addWidget(QLabel("Paste Cookie Header String or JSON array:"))
        
        self.cookie_text_edit = QTextEdit()
        self.cookie_text_edit.setPlaceholderText("Paste cookies here (e.g. session_id=abc123xyz; visitor_token=... OR [{'name': '...', 'value': '...'}])")
        self.cookie_text_edit.setPlainText(settings_manager.get("cookie_string", ""))
        paste_layout.addWidget(self.cookie_text_edit)
        
        tabs.addTab(paste_tab, "📋 Paste Cookies")

        # Tab 2: File Import
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        file_layout.addWidget(QLabel("Select a .json or .txt cookie file exported from your browser:"))
        
        file_btn_box = QHBoxLayout()
        self.file_path_lbl = QLabel("No file selected")
        self.file_path_lbl.setStyleSheet("color: #F59E0B; font-style: italic;")
        
        browse_file_btn = QPushButton("📁 Select Cookie File...")
        browse_file_btn.setStyleSheet("background-color: #8B5CF6;")
        browse_file_btn.clicked.connect(self.browse_cookie_file)

        file_btn_box.addWidget(browse_file_btn)
        file_btn_box.addWidget(self.file_path_lbl, stretch=1)

        file_layout.addLayout(file_btn_box)
        file_layout.addStretch()

        tabs.addTab(file_tab, "📂 Import File")

        layout.addWidget(tabs)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.save_btn = QPushButton("Save & Apply Cookies")
        self.save_btn.setStyleSheet("background-color: #10B981; font-size: 13px;")
        self.save_btn.clicked.connect(self.save_cookies)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #475569;")
        self.cancel_btn.clicked.connect(self.reject)

        btn_box.addWidget(self.cancel_btn)
        btn_box.addWidget(self.save_btn)

        layout.addLayout(btn_box)

    def browse_cookie_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Browser Cookie File", "", "Cookie Files (*.json *.txt);;All Files (*)"
        )
        if file_path:
            self.file_path_lbl.setText(os.path.basename(file_path))
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.cookie_text_edit.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to read file: {e}")

    def save_cookies(self):
        raw_text = self.cookie_text_edit.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "Empty", "Please paste or import cookie content.")
            return

        # Save to settings
        settings_manager.set("cookie_string", raw_text)

        # Update Playwright storage state format
        try:
            success = browser_manager.import_cookies(raw_text)
            if success:
                QMessageBox.information(self, "Success", "Cookies imported & saved successfully! Session active.")
            else:
                QMessageBox.information(self, "Saved", "Cookie string saved to settings.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not process cookies: {e}")
