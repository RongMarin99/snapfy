"""
Snapfy Custom UI Widgets & Styled Components
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QStyledItemDelegate
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QBrush

class StatusBadge(QLabel):
    def __init__(self, text="Waiting", status_type="waiting"):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.set_status(status_type)

    def set_status(self, status_type: str, text: str = None):
        if text:
            self.setText(text)
        
        status_map = {
            "waiting": ("#3B82F6", "#1E3A8A"),      # Blue
            "scraping": ("#8B5CF6", "#4C1D95"),     # Purple
            "downloading": ("#059669", "#064E3B"),  # Green
            "finished": ("#10B981", "#064E3B"),     # Emerald
            "failed": ("#EF4444", "#7F1D1D"),       # Red
            "paused": ("#F59E0B", "#78350F")        # Amber
        }

        fg, bg = status_map.get(status_type.lower(), ("#6B7280", "#1F2937"))
        self.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                background-color: {bg};
                border: 1px solid {fg};
                border-radius: 10px;
                padding: 2px 10px;
                font-weight: bold;
            }}
        """)

class CustomProgressBarDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        if index.column() == 8:  # Progress Column
            val = index.model().data(index, Qt.DisplayRole)
            try:
                progress = float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                progress = 0.0

            painter.save()
            rect = option.rect.adjusted(4, 4, -4, -4)

            # Draw background
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#1E293B"))
            painter.drawRoundedRect(rect, 4, 4)

            # Draw progress bar fill
            if progress > 0:
                fill_width = int(rect.width() * (progress / 100.0))
                fill_rect = rect.adjusted(0, 0, -(rect.width() - fill_width), 0)
                
                # Gradient fill
                if progress >= 100:
                    painter.setBrush(QColor("#10B981"))
                else:
                    painter.setBrush(QColor("#0284C7"))
                
                painter.drawRoundedRect(fill_rect, 4, 4)

            # Draw text percentage
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, f"{progress:.1f}%")

            painter.restore()
        else:
            super().paint(painter, option, index)

class MetricCard(QFrame):
    def __init__(self, title: str, value: str, icon_symbol: str = "⚡"):
        super().__init__()
        self.setObjectName("MetricCard")
        self.setStyleSheet("""
            QFrame#MetricCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        self.icon_lbl = QLabel(icon_symbol)
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        
        v_box = QVBoxLayout()
        v_box.setSpacing(0)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #94A3B8; font-size: 10px; text-transform: uppercase;")
        
        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: bold;")
        
        v_box.addWidget(self.title_lbl)
        v_box.addWidget(self.val_lbl)
        
        layout.addWidget(self.icon_lbl)
        layout.addLayout(v_box)

    def set_value(self, val: str):
        self.val_lbl.setText(val)
