# 檔名: color_palette_panel.py
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QButtonGroup
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor

class ColorPalettePanel(QWidget):
    """一個彈出式面板，用於顯示完整的顏色選擇。"""
    color_selected = pyqtSignal(QColor)
    custom_color_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(62, 74, 89, 220);
                border: 1px solid #5A6B7C;
                border-radius: 5px;
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        self.color_button_group = QButtonGroup(self)
        self.color_button_group.setExclusive(False) # Allow multiple buttons to be checked if needed, though we handle it manually

        palette_colors = [
            "#000000", "#FFFFFF", "#FF0000", "#0000FF",
            "#008000", "#FFFF00", "#00FF00", "#FF00FF"
        ]
        
        positions = [(i, j) for i in range(2) for j in range(4)]
        for position, color_hex in zip(positions, palette_colors):
            color = QColor(color_hex)
            button = self._create_color_button(color)
            button.clicked.connect(lambda _, c=color: self._on_color_click(c))
            layout.addWidget(button, *position)

        # Custom color button
        custom_button = QPushButton("...")
        custom_button.setFixedSize(28, 28)
        custom_button.setStyleSheet("""
            QPushButton { background-color: #7E8A97; color: white; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #98A3AF; }
        """)
        custom_button.setToolTip("選擇自訂顏色")
        custom_button.clicked.connect(self._on_custom_color_click)
        layout.addWidget(custom_button, 2, 0, 1, 4, Qt.AlignCenter) # Span across the bottom

    def _create_color_button(self, color: QColor) -> QPushButton:
        button = QPushButton()
        button.setFixedSize(28, 28)
        button.setStyleSheet(f"""
            QPushButton {{ background-color: {color.name()}; border: 2px solid transparent; border-radius: 4px; }}
            QPushButton:hover {{ border-color: #98A3AF; }}
            QPushButton:pressed {{ border-color: #87CEFA; }}
        """)
        return button

    def _on_color_click(self, color: QColor):
        self.color_selected.emit(color)
        self.hide()

    def _on_custom_color_click(self):
        self.custom_color_requested.emit()
        self.hide()

