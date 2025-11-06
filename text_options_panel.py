from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QFontDatabase

class TextOptionsPanel(QWidget):
    """一個彈出式面板，用於顯示文字工具的選項（字體、大小）。"""
    font_changed = pyqtSignal(str)
    font_size_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Qt.Popup 旗標讓面板在失去焦點時自動隱藏
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 套用與主工具列相似的樣式
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(62, 74, 89, 220);
                border: 1px solid #5A6B7C;
                border-radius: 5px;
                color: white;
            }
            QComboBox { background-color: #7E8A97; color: white; border: 1px solid #5A6B7C; border-radius: 4px; padding: 5px; font-weight: bold; }
            QComboBox:hover { border: 1px solid #98A3AF; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left-width: 1px; border-left-style: solid; border-left-color: #5A6B7C; }
            QComboBox QAbstractItemView { border: 2px solid #5A6B7C; selection-background-color: #697582; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.font_combo = QComboBox()
        self.font_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.font_combo.setToolTip("選擇字體")
        db = QFontDatabase()
        scalable_families = sorted([family for family in db.families() if db.isScalable(family)])
        self.font_combo.addItems(scalable_families)
        self.font_combo.currentTextChanged.connect(self.font_changed.emit)
        layout.addWidget(self.font_combo)

        self.font_size_combo = QComboBox()
        self.font_size_combo.setToolTip("選擇字體大小")
        font_sizes = ['18', '24', '36', '48', '64', '72', '96']
        self.font_size_combo.addItems(font_sizes)
        self.font_size_combo.currentTextChanged.connect(self._emit_font_size)
        layout.addWidget(self.font_size_combo)

    @pyqtSlot(str)
    def _emit_font_size(self, text):
        try:
            self.font_size_changed.emit(int(text))
        except (ValueError, TypeError):
            pass # 忽略無效輸入