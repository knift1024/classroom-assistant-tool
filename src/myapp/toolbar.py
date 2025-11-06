import sys
from PyQt5.QtWidgets import (QWidget, QPushButton, QSlider, QHBoxLayout, QComboBox, 
                             QLabel, QButtonGroup, QCheckBox, QStyle, QApplication)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent, QSize, QRect, QByteArray
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap

class MovableToolbar(QWidget):
    """一個可移動的、獨立的工具列，透過信號與主視窗通訊。"""
    # --- 定義信號 ---
    toolbar_activated = pyqtSignal()
    color_changed = pyqtSignal(QColor)
    tool_changed = pyqtSignal(str)
    sub_tool_changed = pyqtSignal(str) # 新增：用於在手繪/螢光筆之間切換
    color_requested = pyqtSignal()
    width_changed = pyqtSignal(int)
    smoothing_toggled = pyqtSignal(bool)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    save_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    canvas_changed = pyqtSignal(str)
    pattern_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.offset = QPoint()
        self.mouse_down = False
        self.is_dragging = False # 新增：用於判斷是否真的在拖曳
        self.drag_start_position = QPoint() # 新增：記錄拖曳起始點
        self.custom_color = QColor("#FFA500") # 預設自訂顏色為橘色
        self.current_tool_name = 'freehand'
        self.freehand_sub_mode = 'freehand' # 新增：獨立記錄手繪/螢光筆的狀態
        self.line_arrow_sub_mode = 'line' # 新增：獨立記錄直線/箭頭的狀態
        self.rect_circle_sub_mode = 'rectangle' # 新增：獨立記錄矩形/圓形的狀態
        self.previous_tool_name = 'freehand'

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
            MovableToolbar { background-color: rgba(62, 74, 89, 220); border-radius: 10px; }
            QLabel { background-color: transparent; color: white; font-weight: bold; }
            QPushButton { background-color: #7E8A97; color: white; border: 2px solid transparent; border-radius: 5px; padding: 4px 8px; font-weight: bold; }
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

        self._setup_ui()

        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        toolbar_font = QFont("Arial", 10)

        # --- 繪圖工具按鈕組 ---
        self.tool_button_group = QButtonGroup(self)
        self.tool_button_group.setExclusive(True)
        
        # 將手繪和螢光筆合併
        self.freehand_highlighter_button = QPushButton("手繪")
        self.freehand_highlighter_button.setFont(toolbar_font)
        self.freehand_highlighter_button.setCheckable(True)
        self.freehand_highlighter_button.setChecked(True)
        self.freehand_highlighter_button.clicked.connect(self._on_freehand_highlighter_clicked)
        self.freehand_highlighter_button.setFixedWidth(70) # 設定固定寬度以避免UI橫移
        layout.addWidget(self.freehand_highlighter_button)
        self.tool_button_group.addButton(self.freehand_highlighter_button, 1)

        # 其他工具
        # 合併直線/箭頭
        self.line_arrow_button = QPushButton("直線")
        self.line_arrow_button.setFont(toolbar_font)
        self.line_arrow_button.setCheckable(True)
        self.line_arrow_button.clicked.connect(self._on_line_arrow_clicked)
        self.line_arrow_button.setFixedWidth(60) # 設定固定寬度
        layout.addWidget(self.line_arrow_button)
        self.tool_button_group.addButton(self.line_arrow_button, 2)

        # 合併矩形/圓形
        self.rect_circle_button = QPushButton("矩形")
        self.rect_circle_button.setFont(toolbar_font)
        self.rect_circle_button.setCheckable(True)
        self.rect_circle_button.clicked.connect(self._on_rect_circle_clicked)
        self.rect_circle_button.setFixedWidth(60) # 設定固定寬度
        layout.addWidget(self.rect_circle_button)
        self.tool_button_group.addButton(self.rect_circle_button, 3)

        tools = [("雷射筆", "laser_pointer", False), ("橡皮擦", "eraser", False)]
        
        for i, (text, tool_name, is_checked) in enumerate(tools, 4): # ID 從 4 開始
            button = QPushButton(text)
            button.setFont(toolbar_font)
            button.setCheckable(True)
            layout.addWidget(button)
            self.tool_button_group.addButton(button, i)
        
        self.tool_button_group.buttonClicked[int].connect(self._on_tool_button_clicked)

        # --- 畫布與樣式 ---
        layout.addWidget(self._create_label("畫布:", toolbar_font))
        self.canvas_combo = self._create_combobox(["桌面", "黑板", "白板", "純色"], toolbar_font)
        self.canvas_combo.currentIndexChanged.connect(lambda i: self.canvas_changed.emit(self.canvas_combo.itemText(i)))
        layout.addWidget(self.canvas_combo)

        layout.addWidget(self._create_label("樣式:", toolbar_font))
        self.pattern_combo = self._create_combobox(["無", "細方格", "粗方格"], toolbar_font)
        self.pattern_combo.currentIndexChanged.connect(lambda i: self.pattern_changed.emit(self.pattern_combo.itemText(i)))
        layout.addWidget(self.pattern_combo)

        # --- 新的顏色選擇區 ---
        self.color_button_group = QButtonGroup(self)
        self.color_button_group.setExclusive(True)

        # 預設顏色
        palette_colors = [
            ("#000000", "黑色"), ("#FFFFFF", "白色"), ("#FF0000", "紅色"), ("#0000FF", "藍色"),
            ("#008000", "綠色"), ("#FFFF00", "黃色"), ("#00FF00", "螢光綠"), ("#FF00FF", "螢光紫")
        ]

        for i, (color_hex, tooltip) in enumerate(palette_colors):
            color_button = self._create_color_button(QColor(color_hex), tooltip)
            layout.addWidget(color_button)
            self.color_button_group.addButton(color_button, i)

        # 自訂顏色按鈕
        self.custom_color_button = self._create_color_button(self.custom_color, "自訂顏色")
        self.custom_color_button.setText("...")
        self.custom_color_button.setCheckable(True)
        layout.addWidget(self.custom_color_button)
        self.color_button_group.addButton(self.custom_color_button, len(palette_colors))

        self.color_button_group.buttonClicked[int].connect(self._on_color_button_clicked)

        # 預設選中紅色
        self.color_button_group.button(2).setChecked(True)

        layout.addWidget(self._create_label("粗細:", toolbar_font))
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 20)
        self.width_slider.setMinimumWidth(80)
        self.width_slider.valueChanged.connect(self.width_changed)
        layout.addWidget(self.width_slider)

        # --- 功能按鈕 ---
        self.smooth_button = self._create_functional_button("平滑化", toolbar_font, checkable=True, tooltip="啟用後，手繪筆觸會更圓滑")
        self.smooth_button.toggled.connect(self.smoothing_toggled)
        layout.addWidget(self.smooth_button)

        self.undo_button = self._create_functional_button("復原", toolbar_font)
        self.undo_button.clicked.connect(self.undo_requested)
        layout.addWidget(self.undo_button)

        self.redo_button = self._create_functional_button("重做", toolbar_font)
        self.redo_button.clicked.connect(self.redo_requested)
        layout.addWidget(self.redo_button)

        self.clear_button = self._create_functional_button("清除", toolbar_font)
        self.clear_button.clicked.connect(self.clear_requested)
        layout.addWidget(self.clear_button)

        self.save_button = self._create_functional_button("儲存", toolbar_font)
        self.save_button.clicked.connect(self.save_requested)
        layout.addWidget(self.save_button)

        self.exit_button = self._create_functional_button("退出 (Esc)", toolbar_font)
        self.exit_button.clicked.connect(self.exit_requested)
        layout.addWidget(self.exit_button)

        self.setLayout(layout)

    # --- UI Helper Methods ---
    def _create_label(self, text, font):
        label = QLabel(text)
        label.setFont(font)
        return label

    def _create_combobox(self, items, font):
        combo = QComboBox()
        combo.setFont(font)
        combo.addItems(items)
        return combo

    def _create_color_button(self, color, tooltip):
        button = QPushButton()
        button.setFixedSize(24, 24)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setStyleSheet(f"""
            QPushButton {{ background-color: {color.name()}; border: 2px solid transparent; border-radius: 4px; }}
            QPushButton:checked {{ border: 2px solid #87CEFA; }}
        """)
        return button

    def _create_functional_button(self, text, font, checkable=False, tooltip=None):
        button = QPushButton(text)
        button.setFont(font)
        if checkable:
            button.setCheckable(True)
        if tooltip:
            button.setToolTip(tooltip)
        return button

    # --- Event Handlers and Slots ---
    def _on_freehand_highlighter_clicked(self):
        # 只有當前工具是手繪或螢光筆時，才在兩者之間循環切換
        if self.current_tool_name in ['freehand', 'highlighter']:
            if self.freehand_sub_mode == 'freehand':
                self.freehand_sub_mode = 'highlighter'
                self.freehand_highlighter_button.setText("螢光筆")
            else:
                self.freehand_sub_mode = 'freehand'
                self.freehand_highlighter_button.setText("手繪")

        # 更新當前工具並發送信號
        self.current_tool_name = self.freehand_sub_mode
        self.tool_changed.emit(self.current_tool_name)

    def _on_line_arrow_clicked(self):
        if self.current_tool_name in ['line', 'arrow']:
            if self.line_arrow_sub_mode == 'line':
                self.line_arrow_sub_mode = 'arrow'
                self.line_arrow_button.setText("箭頭")
            else:
                self.line_arrow_sub_mode = 'line'
                self.line_arrow_button.setText("直線")
        
        self.current_tool_name = self.line_arrow_sub_mode
        self.tool_changed.emit(self.current_tool_name)

    def _on_rect_circle_clicked(self):
        if self.current_tool_name in ['rectangle', 'circle']:
            if self.rect_circle_sub_mode == 'rectangle':
                self.rect_circle_sub_mode = 'circle'
                self.rect_circle_button.setText("圓形")
            else:
                self.rect_circle_sub_mode = 'rectangle'
                self.rect_circle_button.setText("矩形")

        self.current_tool_name = self.rect_circle_sub_mode
        self.tool_changed.emit(self.current_tool_name)

    def _on_tool_button_clicked(self, button_id):
        # 這些按鈕有自己的專門處理函式，這裡直接返回
        if button_id in [1, 2, 3]:
            return

        tool_map = {4: 'laser_pointer', 5: 'eraser'}
        clicked_tool_name = tool_map.get(button_id)

        if not clicked_tool_name:
            return

        if clicked_tool_name == 'eraser':
            if self.current_tool_name == 'eraser':
                # Double-clicked eraser, switch back to the previous tool
                target_tool_name = self.previous_tool_name
                
                # Find the button for the previous tool and check it
                if target_tool_name in ['freehand', 'highlighter']:
                    self.tool_button_group.button(1).setChecked(True)
                elif target_tool_name in ['line', 'arrow']:
                    self.tool_button_group.button(2).setChecked(True)
                elif target_tool_name in ['rectangle', 'circle']:
                    self.tool_button_group.button(3).setChecked(True)
                else:
                    # 處理雷射筆等其他工具
                    other_tool_map = {v: k for k, v in tool_map.items()}
                    btn_id = other_tool_map.get(target_tool_name)
                    if btn_id:
                        self.tool_button_group.button(btn_id).setChecked(True)

                self.current_tool_name = target_tool_name
                self.tool_changed.emit(target_tool_name)
                return # End here
            else:
                # Switched to eraser for the first time, store the previous tool
                self.previous_tool_name = self.current_tool_name
        
        self.current_tool_name = clicked_tool_name
        self.tool_changed.emit(clicked_tool_name)

    def _on_color_button_clicked(self, button_id):
        if button_id < 8: # 預設顏色
            color_button = self.color_button_group.button(button_id)
            color = color_button.palette().button().color()
            self.color_changed.emit(color)
        else: # 自訂顏色
            self.color_requested.emit()
 
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            # 讓滑桿自己處理事件，因為它有複雜的拖曳邏輯
            if isinstance(obj, QSlider): return False
            
            # 對於所有其他元件，記錄滑鼠按下的狀態和位置
            self.mouse_down = True
            self.drag_start_position = event.globalPos() # 記錄按下時的全局位置
            self.offset = event.globalPos() - self.pos()
            self.toolbar_activated.emit() # 新增：通知父視窗工具列被點擊，以處理視窗層級問題
            # 返回 False，這樣按鈕等元件仍然可以處理點擊事件（例如顯示按下狀態）
            return False
        elif event.type() == QEvent.MouseMove:
            if self.mouse_down:
                # 檢查是否超過拖曳閾值
                if not self.is_dragging and (event.globalPos() - self.drag_start_position).manhattanLength() > QApplication.startDragDistance():
                    self.is_dragging = True

                if self.is_dragging:
                    self.move(event.globalPos() - self.offset)
                    return True # 消耗事件，防止在拖曳時觸發其他元件的 hover 效果
        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            # 無論如何，釋放滑鼠時都重設所有狀態
            self.mouse_down = False
            self.is_dragging = False
        return super().eventFilter(obj, event)

    # --- Public Methods for State Update ---
    def set_initial_state(self, settings, parent_widget):
        """根據傳入的設定物件初始化工具列狀態。"""
        custom_color = settings.value("pen_custom_color", QColor("#FFA500"))
        # 這裡的 update_custom_color 只是更新自訂顏色按鈕的背景色，
        # 並不會將其設為選中狀態。
        self.update_custom_color(custom_color, False)

        self.smooth_button.setChecked(settings.value("smoothing_enabled", True, type=bool))
        
        geometry = settings.value("toolbar_geometry", None)
        if geometry and isinstance(geometry, QRect):
            available_geometry = QApplication.desktop().availableGeometry(geometry.topLeft())
            if available_geometry.contains(geometry.topLeft()):
                self.setGeometry(geometry)
            else:
                self._move_to_default_position(parent_widget)
        else:
            self._move_to_default_position(parent_widget)

    def _move_to_default_position(self, parent_widget):
        if parent_widget:
            parent_rect = parent_widget.rect()
            self.adjustSize()
            x = parent_rect.width() - self.width() - 20
            y = parent_rect.height() - self.height() - 40
            self.move(x, y)

    def update_custom_color(self, color, emit_signal=True):
        self.custom_color = color
        self.custom_color_button.setStyleSheet(f"""
            QPushButton {{ background-color: {color.name()}; border: 2px solid transparent; border-radius: 4px; }}
            QPushButton:checked {{ border: 2px solid #87CEFA; }}
        """)
        if emit_signal:
            self.color_changed.emit(color)

    def set_undo_enabled(self, enabled):
        self.undo_button.setEnabled(enabled)

    def set_redo_enabled(self, enabled):
        self.redo_button.setEnabled(enabled)

    def set_width_value(self, value):
        """A public method to set the slider's value without emitting a signal."""
        self.width_slider.blockSignals(True)
        self.width_slider.setValue(value)
        self.width_slider.blockSignals(False)

    def set_color_checked(self, color: QColor):
        """根據傳入的顏色，設定對應的顏色按鈕為選中狀態。"""
        # 遍歷所有預設顏色按鈕
        for i in range(self.color_button_group.buttons().__len__() - 1):
            button = self.color_button_group.button(i)
            if button.palette().button().color() == color:
                button.setChecked(True)
                return # 找到匹配的，設定後直接返回

        # 如果沒有在預設顏色中找到匹配項，則表示當前使用的是自訂顏色
        # 更新自訂顏色按鈕的背景色並將其設為選中
        self.update_custom_color(color, False) # 更新顏色但暫不發送信號
        self.custom_color_button.setChecked(True)

    def set_tool_checked(self, tool_name):
        if tool_name in ['freehand', 'highlighter']:
            self.freehand_sub_mode = tool_name # 更新子模式狀態
            self.freehand_highlighter_button.setChecked(True)
            self.freehand_highlighter_button.setText("手繪" if tool_name == 'freehand' else "螢光筆")
            return

        if tool_name in ['line', 'arrow']:
            self.line_arrow_sub_mode = tool_name
            self.line_arrow_button.setChecked(True)
            self.line_arrow_button.setText("直線" if tool_name == 'line' else "箭頭")
            return

        if tool_name in ['rectangle', 'circle']:
            self.rect_circle_sub_mode = tool_name
            self.rect_circle_button.setChecked(True)
            self.rect_circle_button.setText("矩形" if tool_name == 'rectangle' else "圓形")
            return

        tool_map = {'laser_pointer': 4, 'eraser': 5}
        button_id = tool_map.get(tool_name)
        if button_id:
            button = self.tool_button_group.button(button_id)
            if button:
                button.setChecked(True)