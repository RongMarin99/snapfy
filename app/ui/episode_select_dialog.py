"""
Snapfy Episode Selection Dialog (tick episodes before queueing)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.utils.resources import resource_path


class EpisodeSelectDialog(QDialog):
    def __init__(self, series_title: str, episodes: list, parent=None):
        super().__init__(parent)
        self.episodes = episodes
        self.selected_episodes = []

        self.setWindowTitle(f"Snapfy - Select Episodes: {series_title}")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.setMinimumSize(560, 620)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #CBD5E1; }
            QTableWidget {
                background-color: #0F172A; border: 1px solid #1E293B; gridline-color: #1E293B;
                color: #E2E8F0; border-radius: 6px; selection-background-color: #1E3A8A;
            }
            QHeaderView::section {
                background-color: #1E293B; color: #94A3B8; font-weight: bold;
                border: 1px solid #0F172A; padding: 6px;
            }
            QTableWidget::indicator {
                width: 16px; height: 16px;
                border: 1px solid #475569; border-radius: 3px;
                background-color: #1E293B;
            }
            QTableWidget::indicator:checked {
                background-color: #EF4444; border: 1px solid #EF4444;
            }
            QPushButton {
                background-color: #0EA5E9; color: white; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #0284C7; }
        """)

        layout = QVBoxLayout(self)

        header_lbl = QLabel(f"{series_title} — {len(episodes)} episode(s) found. Untick any you don't want to download.")
        header_lbl.setWordWrap(True)
        header_lbl.setStyleSheet("font-weight: bold; color: #38BDF8;")
        layout.addWidget(header_lbl)

        toolbar = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet("background-color: #475569;")
        deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        toolbar.addWidget(select_all_btn)
        toolbar.addWidget(deselect_all_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Download", "Episode", "Status"])
        self.table.setRowCount(len(episodes))
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        for row, ep in enumerate(episodes):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked)
            self.table.setItem(row, 0, check_item)

            ep_num = ep.get("episode_num", row + 1)
            self.table.setItem(row, 1, QTableWidgetItem(f"Episode {ep_num:02d}"))

            status = "🔒 VIP" if ep.get("is_vip") or ep.get("status") == "Locked" else "Available"
            self.table.setItem(row, 2, QTableWidgetItem(status))

        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #475569;")
        cancel_btn.clicked.connect(self.reject)
        confirm_btn = QPushButton("➕ Add Selected to Queue")
        confirm_btn.setStyleSheet("background-color: #10B981;")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

    def _set_all_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(state)

    def _on_confirm(self):
        self.selected_episodes = [
            ep for row, ep in enumerate(self.episodes)
            if self.table.item(row, 0).checkState() == Qt.Checked
        ]
        self.accept()
