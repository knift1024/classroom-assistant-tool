from PyQt5.QtWidgets import (QWidget, QButtonGroup, QApplication, QColorDialog, QSizePolicy)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QRect, QEvent, QSettings
from PyQt5.QtGui import QColor, QPainter, QBrush, QIcon
from collections import deque

from text_options_panel import TextOptionsPanel
from toolbar_builder import ToolbarUIBuilder
from color_palette_panel import ColorPalettePanel

class MovableToolbar(QWidget):
    """一個可移動的、獨立的工具列，透過信號與主視窗通訊。"""
    # --- 定義信號 ---
    toolbar_activated = pyqtSignal()
    color_changed = pyqtSignal(QColor)
    width_changed = pyqtSignal(int)
    smoothing_toggled = pyqtSignal(bool)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    save_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    canvas_changed = pyqtSignal(str)
    pattern_changed = pyqtSignal(str)
    font_changed = pyqtSignal(str)
    font_size_changed = pyqtSignal(int)
    tool_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # --- 視窗拖曳相關狀態 ---
        self.offset = QPoint()
        self.mouse_down = False
        self.is_dragging = False
        self.drag_start_position = QPoint()

        # --- 工具狀態與設定 ---
        self.pen_color = QColor("#FF0000") # 預設畫筆顏色
        self.recent_colors = deque([QColor("#0000FF"), QColor("#008000")], maxlen=2) # 最近使用的顏色
        self.current_tool_name = 'freehand'
        self.previous_tool_name = 'freehand'
        self.freehand_sub_mode = 'freehand'
        self.line_arrow_sub_mode = 'line'
        self.rect_circle_sub_mode = 'rectangle'
        self.font_family = "Arial"
        self.font_size = 36

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NativeWindow, True)

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        # 設定尺寸策略，以防止工具列水平拉伸，使其寬度由內容決定
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.setStyleSheet("""
            MovableToolbar { border-radius: 10px; }
            QLabel { background-color: transparent; color: white; font-weight: bold; }
            QPushButton { background-color: #7E8A97; color: white; border: 2px solid transparent; border-radius: 5px; padding: 4px 6px; font-weight: bold; }
            QPushButton:hover:!checked { background-color: #98A3AF; }
            QPushButton:pressed, QPushButton:checked { background-color: #697582; border: 2px solid #87CEFA; }
            QSlider::groove:horizontal { border: 1px solid #5A6B7C; height: 8px; background: #5A6B7C; margin: 2px 0; border-radius: 4px; }
            QSlider::handle:horizontal { background: #98A3AF; border: 1px solid #7E8A97; width: 18px; margin: -5px 0; border-radius: 9px; }
            QSlider::sub-page:horizontal { background: #7E8A97; border: 1px solid #5A6B7C; height: 8px; border-radius: 4px; }
            QComboBox { background-color: #7E8A97; color: white; border: 1px solid #5A6B7C; border-radius: 4px; padding: 5px; font-weight: bold; }
            QComboBox:hover { border: 1px solid #98A3AF; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left-width: 1px; border-left-style: solid; border-left-color: #5A6B7C; }
            QComboBox QAbstractItemView { border: 2px solid #5A6B7C; selection-background-color: #697582; }
        """)

        builder = ToolbarUIBuilder(self)
        builder.setup_ui()
        
        self.text_options_panel = TextOptionsPanel(self)
        self.color_palette_panel = ColorPalettePanel(self)

        self._connect_signals()
        self._update_color_buttons_ui()

        # 為工具列本身及其所有子元件安裝事件過濾器
        # 這讓我們可以在不干擾正常功能（如按鈕點擊）的情況下，攔截滑鼠點擊事件
        self.installEventFilter(self)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(62, 74, 89, 220)))
        painter.drawRoundedRect(self.rect(), 10, 10)

    def _connect_signals(self):
        """將所有 UI 元件的信號連接到對應的槽函式。"""
        # 工具按鈕
        self.freehand_highlighter_button.clicked.connect(self._on_freehand_highlighter_clicked)
        self.line_arrow_button.clicked.connect(self._on_line_arrow_clicked)
        self.rect_circle_button.clicked.connect(self._on_rect_circle_clicked)
        self.tool_button_group.buttonClicked[int].connect(self._on_tool_button_clicked)

        # 畫布與樣式
        self.canvas_combo.currentIndexChanged.connect(lambda i: self.canvas_changed.emit(self.canvas_combo.itemText(i)))
        self.pattern_combo.currentIndexChanged.connect(lambda i: self.pattern_changed.emit(self.pattern_combo.itemText(i)))

        # 顏色與寬度
        self.recent_color_1.clicked.connect(lambda: self._update_color_state(self.recent_colors[0]))
        self.recent_color_2.clicked.connect(lambda: self._update_color_state(self.recent_colors[1]))
        self.main_color_button.clicked.connect(self._show_color_palette)
        self.color_palette_panel.color_selected.connect(self._update_color_state)
        self.color_palette_panel.custom_color_requested.connect(self._handle_custom_color_requested)
        self.width_slider.valueChanged.connect(self.width_changed)

        # 功能按鈕
        self.smooth_button.toggled.connect(self.smoothing_toggled)
        self.undo_button.clicked.connect(self.undo_requested)
        self.redo_button.clicked.connect(self.redo_requested)
        self.clear_button.clicked.connect(self.clear_requested)
        self.save_button.clicked.connect(self.save_requested)
        self.exit_button.clicked.connect(self.exit_requested)
        
        # 文字選項面板
        self.text_options_panel.font_changed.connect(self.font_changed)
        self.text_options_panel.font_size_changed.connect(self.font_size_changed)

    # --- Event Handlers and Slots ---
    def _on_freehand_highlighter_clicked(self):
        self.set_text_options_visibility(False)
        if self.current_tool_name in ['freehand', 'highlighter']:
            # 如果按鈕已經是活動狀態，點擊它會切換子模式
            self.freehand_sub_mode = 'highlighter' if self.freehand_sub_mode == 'freehand' else 'freehand'
            self.freehand_highlighter_button.swap_states() # 呼叫按鈕自己的方法來交換外觀
        self.current_tool_name = self.freehand_sub_mode
        self.tool_changed.emit(self.current_tool_name)

    def _on_line_arrow_clicked(self):
        self.set_text_options_visibility(False)
        if self.current_tool_name in ['line', 'arrow']:
            # 如果按鈕已經是活動狀態，點擊它會切換子模式
            self.line_arrow_sub_mode = 'arrow' if self.line_arrow_sub_mode == 'line' else 'line'
            self.line_arrow_button.swap_states() # 呼叫按鈕自己的方法來交換外觀
        self.current_tool_name = self.line_arrow_sub_mode
        self.tool_changed.emit(self.current_tool_name)

    def _on_rect_circle_clicked(self):
        self.set_text_options_visibility(False)
        if self.current_tool_name in ['rectangle', 'circle']:
            # 如果按鈕已經是活動狀態，點擊它會切換子模式
            self.rect_circle_sub_mode = 'circle' if self.rect_circle_sub_mode == 'rectangle' else 'rectangle'
            self.rect_circle_button.swap_states() # 呼叫按鈕自己的方法來交換外觀
        self.current_tool_name = self.rect_circle_sub_mode
        self.tool_changed.emit(self.current_tool_name)

    def _on_tool_button_clicked(self, button_id):
        self.set_text_options_visibility(False)
        tool_map = {
            1: self.freehand_sub_mode,
            2: self.line_arrow_sub_mode,
            3: self.rect_circle_sub_mode,
            4: 'text',
            5: 'laser_pointer',
            6: 'eraser',
        }
        new_tool = tool_map.get(button_id)
        if new_tool:
            if self.current_tool_name != 'eraser' and new_tool == 'eraser':
                self.previous_tool_name = self.current_tool_name
            
            self.current_tool_name = new_tool
            
            if new_tool == 'text':
                self.set_text_options_visibility(True)

            self.tool_changed.emit(self.current_tool_name)

    # --- Color Management ---
    def _update_color_state(self, new_color: QColor):
        if not new_color.isValid():
            return
        if self.pen_color == new_color and self.current_tool_name != 'eraser':
            return # 如果顏色相同且不是在橡皮擦模式，則不執行任何操作
        # Update recent colors if the new color is different from the current one
        if self.pen_color != new_color:
            if self.pen_color in self.recent_colors:
                self.recent_colors.remove(self.pen_color)
            self.recent_colors.appendleft(self.pen_color)

        # Set new color
        self.pen_color = new_color
        self.color_changed.emit(self.pen_color)
        self._update_color_buttons_ui()

        # If in eraser mode, switch back to previous tool
        if self.current_tool_name == 'eraser':
            self.set_tool_checked(self.previous_tool_name)

    def _show_color_palette(self):
        # 計算位置，使面板顯示在按鈕上方
        pos = self.main_color_button.mapToGlobal(QPoint(0, -self.color_palette_panel.sizeHint().height()))        
        self.color_palette_panel.move(pos)
        self.color_palette_panel.show()

    def _handle_custom_color_requested(self):
        color = QColorDialog.getColor(self.pen_color, self, "選擇自訂顏色")
        if color.isValid():
            self._update_color_state(color)

    def _update_color_buttons_ui(self):
        """Updates the UI of the three color buttons based on current state."""
        # Update main color button
        luminance = (self.pen_color.red() * 299 + self.pen_color.green() * 587 + self.pen_color.blue() * 114) / 1000
        text_color = "black" if luminance > 128 else "white"
        self.main_color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.pen_color.name()};
                color: {text_color};
                font-weight: bold;
                border: 1px solid #5A6B7C;
                border-radius: 4px;
            }}
            QPushButton:hover {{ border-color: #98A3AF; }}
            QPushButton:pressed {{ background-color: {self.pen_color.darker(120).name()}; }}
        """)

        # Update recent color buttons
        self.recent_color_1.setStyleSheet(f"QPushButton {{ background-color: {self.recent_colors[0].name()}; border: 2px solid transparent; border-radius: 4px; }} QPushButton:checked {{ border: 2px solid #87CEFA; }}")
        self.recent_color_2.setStyleSheet(f"QPushButton {{ background-color: {self.recent_colors[1].name()}; border: 2px solid transparent; border-radius: 4px; }} QPushButton:checked {{ border: 2px solid #87CEFA; }}")
        
        # Uncheck all color buttons in the group
        if self.color_button_group.checkedButton():
            self.color_button_group.setExclusive(False)
            self.color_button_group.checkedButton().setChecked(False)
            self.color_button_group.setExclusive(True)

        # Check the button corresponding to the current color
        if self.pen_color == self.recent_colors[0]:
            self.recent_color_1.setChecked(True)
        elif self.pen_color == self.recent_colors[1]:
            self.recent_color_2.setChecked(True)

    # --- Public Methods ---
    def set_tool_checked(self, tool_name: str):
        tool_map = {
            'freehand': 1, 'highlighter': 1,
            'line': 2, 'arrow': 2,
            'rectangle': 3, 'circle': 3,
            'text': 4,
            'laser_pointer': 5,
            'eraser': 6,
        }
        button_id = tool_map.get(tool_name)
        if button_id:
            button = self.tool_button_group.button(button_id)
            if button:
                button.setChecked(True)
                # Manually trigger the handler to update state
                self._on_tool_button_clicked(button_id)

    def set_width_value(self, value: int):
        self.width_slider.blockSignals(True)
        self.width_slider.setValue(value)
        self.width_slider.blockSignals(False)

    def set_undo_enabled(self, enabled: bool):
        self.undo_button.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool):
        self.redo_button.setEnabled(enabled)

    def set_text_options_visibility(self, visible: bool):
        if visible:
            # 計算位置，使面板顯示在按鈕上方
            pos = self.text_button.mapToGlobal(QPoint(0, -self.text_options_panel.sizeHint().height()))
            self.text_options_panel.move(pos)
            self.text_options_panel.show()
        else:
            self.text_options_panel.hide()

    def set_initial_state(self, settings: QSettings, parent_font_family: str, parent_font_size: int):
        """Loads settings and sets the initial state of the toolbar."""
        # Load colors
        self.pen_color = settings.value("pen_color", QColor("#FF0000"))
        recent1 = settings.value("recent_color_1", QColor("#0000FF"))
        recent2 = settings.value("recent_color_2", QColor("#008000"))
        self.recent_colors = deque([recent1, recent2], maxlen=2)
        self._update_color_buttons_ui()

        # Load font
        self.font_family = settings.value("font_family", parent_font_family)
        self.font_size = settings.value("font_size", parent_font_size, type=int)
        self.text_options_panel.font_combo.setCurrentText(self.font_family)
        self.text_options_panel.font_size_combo.setCurrentText(str(self.font_size))

        # Load smoothing
        smoothing = settings.value("smoothing_enabled", True, type=bool)
        self.smooth_button.setChecked(smoothing)

        # Load position
        geometry = settings.value("toolbar_geometry", None)
        if geometry and isinstance(geometry, QRect):
            # 只恢復位置，讓寬度由佈局和尺寸策略自動決定，而不是恢復舊的尺寸
            pos = geometry.topLeft()
            available_geometry = QApplication.desktop().availableGeometry(pos)
            if available_geometry.contains(pos):
                self.move(pos)

    def save_state_to_settings(self, settings: QSettings):
        """Saves the current state of the toolbar to the QSettings object."""
        settings.setValue("pen_color", self.pen_color)
        settings.setValue("recent_color_1", self.recent_colors[0])
        settings.setValue("recent_color_2", self.recent_colors[1])
        settings.setValue("font_family", self.text_options_panel.font_combo.currentText())
        settings.setValue("font_size", int(self.text_options_panel.font_size_combo.currentText()))
        settings.setValue("smoothing_enabled", self.smooth_button.isChecked())
        settings.setValue("toolbar_geometry", self.geometry())

    def eventFilter(self, watched, event):
        """
        事件過濾器，主要用於解決「點擊工具列按鈕時，主工具列消失」的問題。
        """
        # 當滑鼠在工具列的任何地方（包括按鈕）按下時
        if event.type() == QEvent.MouseButtonPress:
            # 發射信號，通知主應用程式將所有工具視窗提升到最上層
            self.toolbar_activated.emit()
        # 將事件傳遞給原始的處理程序，以確保按鈕點擊、滑桿拖曳等功能正常運作
        return super().eventFilter(watched, event)
    
    def mousePressEvent(self, event):
        self.toolbar_activated.emit()
        if event.button() == Qt.LeftButton:
            self.mouse_down = True
            self.is_dragging = False
            self.drag_start_position = event.pos()
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.mouse_down:
            if not self.is_dragging and (event.pos() - self.drag_start_position).manhattanLength() > QApplication.startDragDistance():
                self.is_dragging = True
            if self.is_dragging:
                self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_down = False
            self.is_dragging = False
