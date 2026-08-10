"""
Snapfy Multi-Site Cookie Importer Dialog

Cookies are stored per-platform and merged into Playwright's shared storage_state.json,
each tagged with its own cookie domain. Playwright then automatically sends the right
cookie set for whichever site a plugin navigates to - no manual "login" step needed.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QComboBox,
    QPushButton, QFileDialog, QMessageBox, QTabWidget, QWidget, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from app.core.settings import settings_manager
from app.core.browser import browser_manager
from app.utils.resources import resource_path

# (display label, settings key, cookie domain) - None domain means "custom, ask user"
SUPPORTED_SITES = [
    ("NetShort (netshort.com)", "netshort", ".netshort.com"),
    ("Dailymotion (dailymotion.com)", "dailymotion", ".dailymotion.com"),
    ("Custom Site...", "custom", None),
]


class CookieDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Snapfy - Add / Import Account Session Cookies")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.setMinimumSize(600, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #CBD5E1;
            }
            QTextEdit, QLineEdit {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px;
                color: #F8FAFC;
                font-family: monospace;
            }
            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #0EA5E9;
            }
            QComboBox {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 10px;
                color: #F8FAFC;
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
        self._on_platform_changed()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title_lbl = QLabel("🍪 Add / Import Session Cookies")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        sub_lbl = QLabel("Pick a site, then paste its Cookie header string or JSON array. Each site keeps its own cookies - Snapfy auto-picks the right one per URL, no manual login needed.")
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")

        layout.addWidget(title_lbl)
        layout.addWidget(sub_lbl)

        # Site selector
        site_row = QHBoxLayout()
        site_row.addWidget(QLabel("Site:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems([label for label, _, _ in SUPPORTED_SITES])
        self.platform_combo.currentIndexChanged.connect(self._on_platform_changed)
        site_row.addWidget(self.platform_combo, stretch=1)
        layout.addLayout(site_row)

        self.custom_domain_input = QLineEdit()
        self.custom_domain_input.setPlaceholderText("Cookie domain, e.g. .example.com")
        layout.addWidget(self.custom_domain_input)

        self.saved_sites_lbl = QLabel()
        self.saved_sites_lbl.setStyleSheet("font-size: 11px; color: #10B981;")
        self.saved_sites_lbl.setWordWrap(True)
        layout.addWidget(self.saved_sites_lbl)

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

        layout.addWidget(tabs, stretch=1)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.save_btn = QPushButton("Save && Apply Cookies")
        self.save_btn.setStyleSheet("background-color: #10B981; font-size: 13px;")
        self.save_btn.clicked.connect(self.save_cookies)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #475569;")
        self.cancel_btn.clicked.connect(self.reject)

        btn_box.addWidget(self.cancel_btn)
        btn_box.addWidget(self.save_btn)

        layout.addLayout(btn_box)

    def _current_site(self):
        """Returns (settings_key, domain) for the selected site, or (None, None) if incomplete."""
        _, key, domain = SUPPORTED_SITES[self.platform_combo.currentIndex()]
        if key == "custom":
            custom_domain = self.custom_domain_input.text().strip()
            if not custom_domain:
                return None, None
            if not custom_domain.startswith("."):
                custom_domain = "." + custom_domain
            return custom_domain.lstrip("."), custom_domain
        return key, domain

    def _on_platform_changed(self, _index: int = 0):
        _, key, domain = SUPPORTED_SITES[self.platform_combo.currentIndex()]
        self.custom_domain_input.setVisible(key == "custom")

        saved_cookies = settings_manager.get("cookies", {})
        settings_key = key if key != "custom" else ""
        self.cookie_text_edit.setPlainText(saved_cookies.get(settings_key, ""))

        configured = [k for k, v in saved_cookies.items() if v]
        self.saved_sites_lbl.setText(
            f"✅ Cookies currently saved for: {', '.join(configured)}" if configured
            else "No site has saved cookies yet."
        )

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

        settings_key, domain = self._current_site()
        if not domain:
            QMessageBox.warning(self, "Missing Domain", "Please enter the cookie domain for this custom site.")
            return

        cookies = settings_manager.get("cookies", {})
        cookies[settings_key] = raw_text
        settings_manager.set("cookies", cookies)

        try:
            success = browser_manager.import_cookies(raw_text, domain)
            if success:
                QMessageBox.information(self, "Success", f"Cookies saved for '{settings_key}' && applied! Session active.")
            else:
                QMessageBox.information(self, "Saved", "Cookie string saved to settings.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not process cookies: {e}")
