"""
Snapfy Downloader Pro - Main Window (PySide6 Desktop GUI)
"""

import os
import asyncio
import psutil
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QHeaderView, QFileDialog, QSpinBox, QCheckBox, QComboBox, QSplitter,
    QProgressBar, QMessageBox, QFrame, QMenu
)
from PySide6.QtCore import Qt, QTimer, Slot, QThread, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices

from app.core.settings import settings_manager
from app.core.queue import queue_manager
from app.core.logger import logger
from app.core.browser import browser_manager
from app.ui.widgets import CustomProgressBarDelegate, MetricCard
from app.ui.settings_page import SettingsDialog
from app.ui.cookie_dialog import CookieDialog
from app.ui.episode_select_dialog import EpisodeSelectDialog
from app.workers.scrape_worker import ScrapeWorker
from app.workers.download_worker import DownloadWorker
from app.utils.file import export_to_csv, export_to_json, export_to_txt

class InteractiveBrowserWorker(QThread):
    finished_signal = Signal()

    def __init__(self, target_url: str):
        super().__init__()
        self.target_url = target_url

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(browser_manager.open_interactive_browser(self.target_url))
        except Exception as e:
            logger.error(f"Interactive browser worker error: {e}")
        finally:
            loop.close()
            self.finished_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SnapKee Downloader & Media V1.3.32 (Licensed) - Snapfy Pro")
        self.resize(1340, 820)
        self.setMinimumSize(1100, 700)

        self.scrape_worker = None
        self.download_worker = None
        self.browser_workers = []  # Keep references to avoid QThread destruction crash
        self.timer_seconds = 0

        self.setup_stylesheet()
        self.init_ui()
        self.connect_signals()

        # Timer for runtime counter & CPU monitor
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_system_metrics)
        self.monitor_timer.start(1000)

        # Load existing database items into table
        self.load_initial_queue()

    def setup_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0B1120;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame {
                border: none;
            }
            QLabel {
                color: #E2E8F0;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0EA5E9;
            }
            QPushButton {
                background-color: #0EA5E9;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0284C7;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748B;
            }
            QTableWidget {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                gridline-color: #1E293B;
                color: #E2E8F0;
                border-radius: 6px;
                selection-background-color: #1E3A8A;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: bold;
                border: 1px solid #0F172A;
                padding: 6px;
            }
            QListWidget {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                color: #E2E8F0;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #1E293B;
            }
            QListWidget::item:selected {
                background-color: #0284C7;
                color: white;
            }
            QComboBox, QSpinBox {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                color: #F8FAFC;
            }
            QCheckBox {
                color: #CBD5E1;
            }
            QMessageBox {
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QMessageBox QLabel {
                color: #F8FAFC;
                font-size: 13px;
                font-weight: 500;
            }
            QMessageBox QPushButton {
                background-color: #0EA5E9;
                color: white;
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: bold;
                min-width: 60px;
            }
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
            }
            QMenu::item:selected {
                background-color: #0284C7;
            }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ----------------------------------------------------
        # TOP HEADER & METRIC BAR
        # ----------------------------------------------------
        top_bar = QHBoxLayout()
        
        # Logo & App Title
        logo_lbl = QLabel("⚡ SNAPFY")
        logo_lbl.setStyleSheet("font-size: 18px; font-weight: 900; color: #38BDF8; letter-spacing: 1px;")
        sub_logo = QLabel("SCRAPER-DOWNLOADER-PRO")
        sub_logo.setStyleSheet("font-size: 9px; color: #94A3B8; font-weight: bold;")
        
        logo_box = QVBoxLayout()
        logo_box.setSpacing(0)
        logo_box.addWidget(logo_lbl)
        logo_box.addWidget(sub_logo)
        top_bar.addLayout(logo_box)
        top_bar.addSpacing(20)

        # Timer & Bandwidth cards
        self.timer_card = MetricCard("UPTIME", "00:00:00", "⏱️")
        self.bandwidth_card = MetricCard("BANDWIDTH", "0.0 Mbps", "🚀")
        top_bar.addWidget(self.timer_card)
        top_bar.addWidget(self.bandwidth_card)
        top_bar.addStretch()

        # Action / License buttons
        self.add_cookie_btn = QPushButton("🍪 Add Cookie")
        self.add_cookie_btn.setStyleSheet("background-color: #10B981; color: white;")
        self.add_cookie_btn.setToolTip("Import or paste account session cookies (.json or header string).")
        self.add_cookie_btn.clicked.connect(self.open_cookie_dialog)

        self.login_browser_btn = QPushButton("🔑 Login / Open Session")
        self.login_browser_btn.setStyleSheet("background-color: #8B5CF6; color: white;")
        self.login_browser_btn.setToolTip("Opens a visible browser to log into NetShort/Dailymotion/DramaBox and save cookies permanently.")
        self.login_browser_btn.clicked.connect(self.open_interactive_login)

        self.clear_session_btn = QPushButton("🧹 Clear Session")
        self.clear_session_btn.setStyleSheet("background-color: #475569; color: white;")
        self.clear_session_btn.setToolTip("Resets browser cookies and session storage.")
        self.clear_session_btn.clicked.connect(self.clear_session)

        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setStyleSheet("background-color: #334155; color: white;")
        self.settings_btn.clicked.connect(self.open_settings)

        license_badge = QLabel("✔ LICENSE ACTIVATED\nv1.3.32 Pro")
        license_badge.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")

        top_bar.addWidget(self.add_cookie_btn)
        top_bar.addWidget(self.login_browser_btn)
        top_bar.addWidget(self.clear_session_btn)
        top_bar.addWidget(self.settings_btn)
        top_bar.addWidget(license_badge)

        main_layout.addLayout(top_bar)

        # ----------------------------------------------------
        # URL SCRAPE CONTROL BAR
        # ----------------------------------------------------
        scrape_bar = QHBoxLayout()

        # Supported platform pills
        pills_lbl = QLabel("Supported: NetShort | DramaBox | Dailymotion | ReelShort | GoodShort | TikTok | MP4 | HLS")
        pills_lbl.setStyleSheet("background-color: #1E293B; color: #38BDF8; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;")
        scrape_bar.addWidget(pills_lbl)

        # URL Input Field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here (e.g. NetShort, Dailymotion https://dai.ly/xafttpi, DramaBox, or direct .m3u8/.mp4)...")
        scrape_bar.addWidget(self.url_input, stretch=1)

        # Action Buttons
        self.scrape_btn = QPushButton("🔍 Scrape Now")
        self.scrape_btn.setStyleSheet("background-color: #0EA5E9;")
        self.scrape_btn.clicked.connect(self.on_scrape_clicked)

        self.add_queue_btn = QPushButton("➕ Add to Queue")
        self.add_queue_btn.setStyleSheet("background-color: #6366F1;")
        self.add_queue_btn.clicked.connect(self.on_add_to_queue_clicked)

        scrape_bar.addWidget(self.scrape_btn)
        scrape_bar.addWidget(self.add_queue_btn)

        main_layout.addLayout(scrape_bar)

        # ----------------------------------------------------
        # SPLITTER: LEFT QUEUE + CENTER TABLE
        # ----------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel - URL Queue
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #0F172A; border-radius: 8px; border: 1px solid #1E293B;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        left_header = QHBoxLayout()
        left_title = QLabel("Queue Downloading")
        left_title.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 13px;")
        left_header.addWidget(left_title)
        left_header.addStretch()

        self.queue_list_widget = QListWidget()
        left_layout.addLayout(left_header)
        left_layout.addWidget(self.queue_list_widget)

        splitter.addWidget(left_panel)

        # Center Panel - Activities Table
        center_panel = QFrame()
        center_panel.setStyleSheet("background-color: #0F172A; border-radius: 8px; border: 1px solid #1E293B;")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(8, 8, 8, 8)

        table_header = QHBoxLayout()
        table_title = QLabel("Activities Tables")
        table_title.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 13px;")

        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.setStyleSheet("background-color: #EF4444; padding: 4px 10px; font-size: 11px;")
        self.clear_all_btn.clicked.connect(self.on_clear_all_clicked)

        self.export_btn = QPushButton("📥 Export")
        self.export_btn.setStyleSheet("background-color: #10B981; padding: 4px 10px; font-size: 11px;")
        self.export_btn.clicked.connect(self.on_export_clicked)

        table_header.addWidget(table_title)
        table_header.addStretch()
        table_header.addWidget(self.export_btn)
        table_header.addWidget(self.clear_all_btn)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(10)
        self.table_widget.setHorizontalHeaderLabels([
            "#", "Title", "URL", "Platform", "Type", "Size (MB)", "Speed", "ETA", "Progress", "Status"
        ])
        self.table_widget.setItemDelegateForColumn(8, CustomProgressBarDelegate(self.table_widget))
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table_widget.doubleClicked.connect(lambda index: self.open_selected_file_folder(index.row()))

        center_layout.addLayout(table_header)
        center_layout.addWidget(self.table_widget)

        splitter.addWidget(center_panel)
        splitter.setSizes([300, 900])

        main_layout.addWidget(splitter, stretch=1)

        # ----------------------------------------------------
        # BOTTOM CONTROL & SYSTEM BAR
        # ----------------------------------------------------
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #0F172A; border-radius: 8px; border: 1px solid #1E293B;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(12, 10, 12, 10)

        # Left Column - Workspace Directory Config
        ws_box = QVBoxLayout()
        ws_title = QLabel("Workspace Setting | Files Directory ℹ️")
        ws_title.setStyleSheet("font-weight: bold; color: #38BDF8;")
        
        self.dir_display = QLineEdit(os.path.normpath(settings_manager.get("download_dir")))
        self.dir_display.setReadOnly(True)
        
        ws_btn_box = QHBoxLayout()
        browse_ws_btn = QPushButton("📁 Browse")
        browse_ws_btn.setStyleSheet("background-color: #F59E0B; color: #000; font-weight: bold;")
        browse_ws_btn.clicked.connect(self.browse_workspace_directory)

        open_folder_btn = QPushButton("📂 Open Download Folder")
        open_folder_btn.setStyleSheet("background-color: #10B981; color: #FFF; font-weight: bold;")
        open_folder_btn.clicked.connect(self.open_download_folder)

        ws_btn_box.addWidget(browse_ws_btn)
        ws_btn_box.addWidget(open_folder_btn)

        ws_box.addWidget(ws_title)
        ws_box.addWidget(self.dir_display)
        ws_box.addLayout(ws_btn_box)

        bottom_layout.addLayout(ws_box, stretch=1)

        # Middle Column - Downloading & System Options
        sys_box = QVBoxLayout()
        sys_title = QLabel("General Downloading & System Setting ℹ️")
        sys_title.setStyleSheet("font-weight: bold; color: #38BDF8;")

        sys_controls = QHBoxLayout()
        
        threads_lbl = QLabel("Threads:")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(settings_manager.get("max_threads", 4))
        self.threads_spin.valueChanged.connect(lambda val: settings_manager.set("max_threads", val))

        self.gpu_check = QCheckBox("Enable GPU Acceleration")
        self.gpu_check.setChecked(settings_manager.get("gpu_acceleration", True))
        self.gpu_check.stateChanged.connect(lambda st: settings_manager.set("gpu_acceleration", bool(st)))

        self.auto_shutdown_check = QCheckBox("Shutdown PC after finished")
        self.auto_shutdown_check.stateChanged.connect(lambda st: settings_manager.set("auto_shutdown", bool(st)))

        sys_controls.addWidget(threads_lbl)
        sys_controls.addWidget(self.threads_spin)
        sys_controls.addWidget(self.gpu_check)
        sys_controls.addWidget(self.auto_shutdown_check)

        self.system_info_lbl = QLabel("CPU: --% | GPU: Auto | Cores: " + str(psutil.cpu_count()))
        self.system_info_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")

        sys_box.addWidget(sys_title)
        sys_box.addLayout(sys_controls)
        sys_box.addWidget(self.system_info_lbl)

        bottom_layout.addLayout(sys_box, stretch=2)

        # Right Column - Big Action Buttons
        btn_action_box = QVBoxLayout()
        
        self.download_now_btn = QPushButton("🚀 Download Now")
        self.download_now_btn.setStyleSheet("background-color: #10B981; font-size: 15px; padding: 12px 24px;")
        self.download_now_btn.clicked.connect(self.on_download_now_clicked)

        self.cancel_download_btn = QPushButton("✖ Cancel / Pause")
        self.cancel_download_btn.setStyleSheet("background-color: #EF4444; font-size: 12px;")
        self.cancel_download_btn.clicked.connect(self.on_cancel_clicked)

        btn_action_box.addWidget(self.download_now_btn)
        btn_action_box.addWidget(self.cancel_download_btn)

        bottom_layout.addLayout(btn_action_box)

        main_layout.addWidget(bottom_frame)

        # Status Footer Bar
        self.status_bar_lbl = QLabel("Status: Ready")
        self.status_bar_lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(self.status_bar_lbl)

    def connect_signals(self):
        queue_manager.item_added.connect(self.add_table_row)
        queue_manager.item_updated.connect(self.update_table_row)

    def update_system_metrics(self):
        self.timer_seconds += 1
        h = self.timer_seconds // 3600
        m = (self.timer_seconds % 3600) // 60
        s = self.timer_seconds % 60
        self.timer_card.set_value(f"{h:02d}:{m:02d}:{s:02d}")

        # Update CPU Usage
        cpu_usage = psutil.cpu_percent()
        self.system_info_lbl.setText(f"CPU: {cpu_usage:.1f}% | Cores: {psutil.cpu_count()} | Threads: {settings_manager.get('max_threads')}")

    def load_initial_queue(self):
        items = queue_manager.get_all_items()
        self.table_widget.setRowCount(0)
        self.queue_list_widget.clear()

        for item in items:
            self.add_table_row(item)

    @Slot(dict)
    def add_table_row(self, item: dict):
        row = self.table_widget.rowCount()
        self.table_widget.insertRow(row)

        self.table_widget.setItem(row, 0, QTableWidgetItem(str(item.get("id", ""))))
        self.table_widget.setItem(row, 1, QTableWidgetItem(item.get("title", "")))
        self.table_widget.setItem(row, 2, QTableWidgetItem(item.get("url", "")))
        self.table_widget.setItem(row, 3, QTableWidgetItem(item.get("platform", "Generic")))
        self.table_widget.setItem(row, 4, QTableWidgetItem("video"))
        
        file_size = item.get("file_size", 0.0)
        self.table_widget.setItem(row, 5, QTableWidgetItem(f"{file_size:.1f}" if file_size else "-"))
        self.table_widget.setItem(row, 6, QTableWidgetItem(item.get("speed", "0 KB/s")))
        self.table_widget.setItem(row, 7, QTableWidgetItem(item.get("eta", "--:--")))
        
        # Progress Item
        prog_item = QTableWidgetItem()
        prog_item.setData(Qt.DisplayRole, item.get("progress", 0.0))
        self.table_widget.setItem(row, 8, prog_item)

        # Status Item
        self.table_widget.setItem(row, 9, QTableWidgetItem(item.get("status", "Waiting")))

        # Add to left queue list widget
        self.queue_list_widget.addItem(f"[{item.get('platform')}] {item.get('title')}")

    @Slot(dict)
    def update_table_row(self, item: dict):
        video_id = item.get("id")
        for row in range(self.table_widget.rowCount()):
            row_id = self.table_widget.item(row, 0).text()
            if row_id == str(video_id):
                self.table_widget.setItem(row, 6, QTableWidgetItem(item.get("speed", "0 KB/s")))
                self.table_widget.setItem(row, 7, QTableWidgetItem(item.get("eta", "--:--")))
                
                prog_item = QTableWidgetItem()
                prog_item.setData(Qt.DisplayRole, item.get("progress", 0.0))
                self.table_widget.setItem(row, 8, prog_item)

                self.table_widget.setItem(row, 9, QTableWidgetItem(item.get("status", "Waiting")))

                if item.get("file_size"):
                    self.table_widget.setItem(row, 5, QTableWidgetItem(f"{item['file_size']:.1f}"))
                break

    def on_scrape_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please paste a video or series URL first.")
            return

        self.status_bar_lbl.setText(f"Status: Scraping URL {url}...")
        self.scrape_btn.setEnabled(False)

        self.scrape_worker = ScrapeWorker(url)
        self.scrape_worker.scrape_finished.connect(self.on_scrape_finished)
        self.scrape_worker.scrape_failed.connect(self.on_scrape_failed)
        self.scrape_worker.start()

    def on_scrape_finished(self, result: dict):
        self.scrape_btn.setEnabled(True)
        episodes = result.get("episodes", [])
        if not episodes:
            QMessageBox.warning(self, "Scrape Result", "No episodes found for this URL.")
            self.status_bar_lbl.setText("Status: Scraping finished (0 items found)")
            return

        series_title = result.get("title", "Series")
        dlg = EpisodeSelectDialog(series_title, episodes, self)
        if dlg.exec() != EpisodeSelectDialog.Accepted or not dlg.selected_episodes:
            self.status_bar_lbl.setText("Status: Scrape finished, no episodes added.")
            return

        selected = dlg.selected_episodes
        queue_manager.add_videos_batch(selected)
        self.status_bar_lbl.setText(f"Status: Added {len(selected)} of {len(episodes)} episode(s) to queue.")
        QMessageBox.information(self, "Scrape Success", f"Added {len(selected)} of {len(episodes)} episode(s) to queue!")

    def on_scrape_failed(self, error_msg: str):
        self.scrape_btn.setEnabled(True)
        self.status_bar_lbl.setText(f"Status: Scraping failed - {error_msg}")
        QMessageBox.critical(self, "Scrape Error", f"Failed to scrape URL:\n{error_msg}")

    def on_add_to_queue_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL.")
            return

        item_data = {
            "title": f"Queued Video - {url.split('/')[-1]}",
            "url": url,
            "platform": "Generic",
            "status": "Waiting"
        }
        queue_manager.add_video(item_data)
        self.url_input.clear()

    def on_download_now_clicked(self):
        waiting_items = queue_manager.get_waiting_items()
        if not waiting_items:
            QMessageBox.information(self, "Queue Empty", "No waiting items to download.")
            return

        self.status_bar_lbl.setText(f"Status: Downloading {len(waiting_items)} item(s)...")
        self.download_now_btn.setEnabled(False)

        self.download_worker = DownloadWorker(waiting_items)
        self.download_worker.item_finished.connect(self.on_download_item_finished)
        self.download_worker.all_finished.connect(self.on_download_all_finished)
        self.download_worker.start()

    def on_download_item_finished(self, video_id: int, is_success: bool):
        logger.info(f"UI notification: item {video_id} finished (success={is_success})")

    def on_download_all_finished(self):
        self.download_now_btn.setEnabled(True)
        self.status_bar_lbl.setText("Status: All downloads completed.")
        
        # Check auto shutdown
        if settings_manager.get("auto_shutdown", False):
            logger.info("Auto-shutdown PC option is enabled.")

    def on_cancel_clicked(self):
        if self.download_worker:
            self.download_worker.stop()
            self.status_bar_lbl.setText("Status: Download cancelled by user.")
            self.download_now_btn.setEnabled(True)

    def on_clear_all_clicked(self):
        reply = QMessageBox.question(self, "Clear Queue", "Are you sure you want to clear all items from queue?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            queue_manager.clear_queue()
            self.table_widget.setRowCount(0)
            self.queue_list_widget.clear()

    def on_export_clicked(self):
        items = queue_manager.get_all_items()
        if not items:
            QMessageBox.warning(self, "Export", "Queue is empty.")
            return

        filepath, selected_filter = QFileDialog.getSaveFileName(
            self, "Export History / Queue", "", "CSV Files (*.csv);;JSON Files (*.json);;TXT Files (*.txt)"
        )
        if filepath:
            if filepath.endswith(".csv"):
                export_to_csv(filepath, items)
            elif filepath.endswith(".json"):
                export_to_json(filepath, items)
            else:
                export_to_txt(filepath, items)
            QMessageBox.information(self, "Export", f"Successfully exported to:\n{filepath}")

    def browse_workspace_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Download Workspace Directory")
        if dir_path:
            norm = os.path.normpath(dir_path)
            settings_manager.set("download_dir", norm)
            self.dir_display.setText(norm)

    def open_download_folder(self):
        folder_path = os.path.normpath(settings_manager.get("download_dir"))
        os.makedirs(folder_path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def show_table_context_menu(self, pos):
        item = self.table_widget.itemAt(pos)
        if not item:
            return
        row = item.row()
        menu = QMenu(self)
        open_folder_act = QAction("📂 Open File Location", self)
        open_folder_act.triggered.connect(lambda: self.open_selected_file_folder(row))
        menu.addAction(open_folder_act)
        menu.exec_(self.table_widget.mapToGlobal(pos))

    def open_selected_file_folder(self, row: int = -1):
        if row < 0:
            row = self.table_widget.currentRow()

        file_path = None
        if row >= 0:
            id_item = self.table_widget.item(row, 0)
            video_id = int(id_item.text()) if id_item and id_item.text().isdigit() else None
            if video_id is not None:
                for it in queue_manager.get_all_items():
                    if it.get("id") == video_id:
                        file_path = it.get("file_path")
                        break

        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))
        else:
            self.open_download_folder()

    def open_cookie_dialog(self):
        dlg = CookieDialog(self)
        dlg.exec()

    def open_interactive_login(self):
        url = self.url_input.text().strip() or "https://netshort.com"
        worker = InteractiveBrowserWorker(url)
        self.browser_workers.append(worker)
        worker.finished_signal.connect(lambda: self.browser_workers.remove(worker) if worker in self.browser_workers else None)
        worker.start()

    def clear_session(self):
        browser_manager.clear_session_storage()
        settings_manager.set("cookie_string", "")
        QMessageBox.information(self, "Session Reset", "Browser session cookies and storage reset successfully.")

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
