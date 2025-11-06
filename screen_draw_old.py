import sys
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QPushButton, QColorDialog, QSlider, QHBoxLayout, QFileDialog, QComboBox, QMessageBox, QButtonGroup, QStyle, QCheckBox)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent, QRect, QSettings, QTimer, QSize, QByteArray
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QCursor, QFont, QIcon, QPainterPath

# --- 新增：Base64 編碼的 SVG 圖示 ---
# 鎖定圖示 (白色鎖頭)
LOCK_ICON_BASE64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0xMiAxN2MxLjEgMCAyLS45IDItMnMtLjktMi0yLTItMiAuOS0yIDIgLjkgMiAyIDJ6bTYtOWgtMVY2YzAtMi43Ni0yLjI0LTUtNS01UzcgMy4yNCA3IDZ2Mkg2Yy0xLjEgMC0yIC45LTIgMnYxMGMwIDEuMS45IDIgMiAyaDEyYzEuMSAwIDItLjkgMi0yVjEwYzAtMS4xLS45LTItMi0yem0tMy0zYzAtMS42NiAxLjM0LTMgMy0zczMgMS4zNCAzIDN2Mkg5VjZ6Ii8+PC9zdmc+"
# 解鎖圖示 (白色打開的鎖頭)
UNLOCK_ICON_BASE64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0xMiAxN2MxLjEgMCAyLS45IDItMnMtLjktMi0yLTItMiAuOS0yIDIgLjkgMiAyIDJ6TTE4IDhoLTFWNmMwLTIuNzYtMi4yNC01LTUtNVM3IDMuMjQgNyA2aDJjMC0xLjY2IDEuMzQtMyAzLTNzMyAxLjM0IDMgM3YySDZjLTEuMSAwLTIgLjktMiAydjEwYzAgMS4xLjkgMiAyIDJoMTJjMS4xIDAgMi0uOSAyLTJWMTBjMC0xLjEtLjktMi0yLTJ6Ii8+PC9zdmc+"

# 新增一個可移動的工具列類別
class MovableToolbar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.offset = QPoint()
        self.mouse_down = False
        self.is_locked = False # 新增：鎖定狀態

        # 設定工具列自身的視窗旗標
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # 永遠在最上層
            Qt.FramelessWindowHint |   # 無邊框
            Qt.Tool                    # 不顯示在任務欄 (避免出現在任務欄或應用程式切換器中)
        )
        self.setFocusPolicy(Qt.NoFocus) # 防止工具列竊取主畫布視窗的焦點
        self.setAttribute(Qt.WA_TranslucentBackground) # 必須保留此屬性以使背景透明度生效

        # --- 美化: 套用莫蘭迪風格的 QSS 樣式表 ---
        self.setStyleSheet("""
            MovableToolbar { /* 使用類別名稱作為選擇器 */
                background-color: rgba(62, 74, 89, 220); /* Morandi Blue-Gray with transparency */
                border-radius: 10px;
            }
            QLabel {
                background-color: transparent;
                color: white;
                font-weight: bold;
            }
            QPushButton {
                background-color: #7E8A97;
                color: white;
                border: 2px solid transparent; /* 預留邊框空間以避免版面移動 */
                border-radius: 5px;
                padding: 4px 8px; /* 調整內邊距以適應邊框 */
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #98A3AF;
            }
            QPushButton:pressed, QPushButton:checked { /* 按下或選中時的樣式 */
                background-color: #697582;
                border: 2px solid #87CEFA; /* 高反差的亮藍色外框 */
            }
            QSlider::groove:horizontal {
                border: 1px solid #5A6B7C; height: 8px; background: #5A6B7C;
                margin: 2px 0; border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #98A3AF; border: 1px solid #7E8A97;
                width: 18px; margin: -5px 0; border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #7E8A97;
                border: 1px solid #5A6B7C;
                height: 8px;
                border-radius: 4px;
            }
            QComboBox {
                background-color: #7E8A97;
                color: white;
                border: 1px solid #5A6B7C;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QComboBox:hover {
                border: 1px solid #98A3AF;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-style: solid;
                border-left-color: #5A6B7C;
            }
            QComboBox QAbstractItemView { /* 下拉選單的項目樣式，padding 5px 保持不變 */
                border: 2px solid #5A6B7C;
                selection-background-color: #697582;
            }
        """)

    # Override eventFilter to intercept events from child widgets
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                # Sliders have their own complex dragging, let them handle it completely.
                if isinstance(obj, QSlider):
                    return False # Let slider process the event

                # For all other widgets, we record the press position and state.
                self.mouse_down = True
                self.offset = event.globalPos() - self.pos()
                # Return False so the widget (e.g., QPushButton) can still
                # process the press event (e.g., show its "pressed" state).
                return False

        elif event.type() == QEvent.MouseMove:
            # If the mouse is moving and the button is down, we drag the toolbar.
            if self.mouse_down and not self.is_locked: # 新增：如果未鎖定，才允許拖曳
                self.move(event.globalPos() - self.offset)
                # Consume the move event to prevent other widgets from reacting to it during a drag.
                return True
            
        elif event.type() == QEvent.MouseButtonRelease:
            # On release, we reset the state.
            if event.button() == Qt.LeftButton:
                self.mouse_down = False
                # We must return False so that the QPushButton can receive the release
                # event and emit the clicked() signal.
                return False

        # For any other event type, let the default handler process it.
        return super().eventFilter(obj, event) 

class ScreenDrawWindow(QWidget):
    """
    螢幕畫記視窗：一個全螢幕、透明、置頂的畫布，用於在螢幕上進行畫記。
    """
    drawing_mode_ended = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("螢幕畫記")

        # --- 視窗底層屬性設定 (核心部分) ---
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(Qt.StrongFocus)

        # --- 尺寸與畫布設定 ---
        screen_rect = QApplication.desktop().screenGeometry()
        self.setGeometry(screen_rect)

        # 使用 QSettings 來持久化儲存設定
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "MyClassroomTools", "ScreenDraw")

        # 繪圖層：一個透明的畫布，用於儲存使用者的筆跡
        self.image = QPixmap(screen_rect.size()) # 使用 screen_rect.size() 確保 QPixmap 初始化時有有效的尺寸
        self.image.fill(Qt.transparent)

        # 背景層：用於儲存桌面截圖
        self.background_pixmap = None

        # --- 狀態與繪圖工具 ---
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.red)
        self.pen_width = 5

        # 新增：繪圖模式與圖形繪製的起點和終點
        self.draw_mode = 'freehand'  # 'freehand', 'line', 'arrow', 'rectangle', 'circle', 'laser_pointer', 'eraser', 'crop'
        
        self.previous_tool_id = 1 # 新增：用於記錄切換到橡皮擦前的工具，預設為手繪

        # 新增：雷射筆殘影相關屬性
        self.laser_trail_segments = [] # 儲存 (start_point, end_point, current_opacity)
        self.laser_fade_timer = QTimer(self)
        self.fade_step = 15 # 每次更新減少的透明度
        
        # 新增：復原/重做 功能的歷史紀錄堆疊
        self.history_stack = []
        self.redo_stack = []
        self.history_limit = 20 # 限制復原步數以避免過高的記憶體使用

        # 新增：筆觸平滑化相關屬性
        self.smoothing_enabled = True # 預設啟用
        self.point_buffer = [] # 用於平滑演算法的點緩衝區

        self.start_point = None
        self.current_point = None
        
        # 新增畫布與樣式狀態
        self.canvas_mode = 'desktop'  # 'desktop', 'blackboard', 'whiteboard', 'solid'
        self.canvas_color = QColor("#2E4636")  # 預設為黑板的深綠色
        self.pattern_mode = 'none'  # 'none', 'fine_grid', 'coarse_grid'

        # 新增：建立鎖定/解鎖圖示
        self.lock_icon = QIcon()
        lock_pixmap = QPixmap()
        lock_pixmap.loadFromData(QByteArray.fromBase64(LOCK_ICON_BASE64.encode()))
        self.lock_icon.addPixmap(lock_pixmap)

        self.unlock_icon = QIcon()
        unlock_pixmap = QPixmap()
        unlock_pixmap.loadFromData(QByteArray.fromBase64(UNLOCK_ICON_BASE64.encode()))
        self.unlock_icon.addPixmap(unlock_pixmap)

        # --- 游標與滑鼠追蹤 ---
        self.setMouseTracking(True) # 視窗可見時，永遠追蹤滑鼠
        self.setCursor(Qt.CrossCursor)

        # --- 浮動工具列 ---
        self.toolbar = self.create_toolbar()
        self.toggle_toolbar_lock(False) # 初始化鎖定按鈕的狀態
        self._update_undo_redo_buttons() # 初始化按鈕狀態
        self.toolbar.hide()
        self.laser_fade_timer.timeout.connect(self._fade_laser_trail)
        self.load_settings() # 載入上次的設定

    def create_toolbar(self):
         # 實例化新的 MovableToolbar 類別
        toolbar = MovableToolbar(self) # 將 ScreenDrawWindow 設為父物件

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(15, 10, 15, 10) # 增加內邊距
        layout.setSpacing(15) # 增加元件間距

        # --- 新增：鎖定按鈕 ---
        self.lock_button = QPushButton()
        self.lock_button.setCheckable(True)
        # 為了讓它看起來像個圖示按鈕，我們設定固定大小並移除一些邊框/背景樣式
        self.lock_button.setFixedSize(32, 32)
        self.lock_button.setIconSize(QSize(20, 20))
        self.lock_button.setStyleSheet("""
            QPushButton { padding: 0; border: 2px solid transparent; background-color: transparent; }
            QPushButton:hover { background-color: #98A3AF; }
            QPushButton:pressed, QPushButton:checked { background-color: #697582; border: 2px solid #87CEFA; }
        """)
        self.lock_button.toggled.connect(self.toggle_toolbar_lock)
        layout.addWidget(self.lock_button)

        # 定義一個較大的字體用於工具列元件
        toolbar_font = QFont("Arial", 10) # 調整為標準大小的字體

        # --- 新增：繪圖工具按鈕組 ---
        self.tool_button_group = QButtonGroup(self)
        self.tool_button_group.setExclusive(True) # 確保按鈕互斥

        self.freehand_button = QPushButton("手繪")
        self.freehand_button.setFont(toolbar_font)
        self.freehand_button.setCheckable(True)
        self.freehand_button.setChecked(True) # 預設為手繪模式
        layout.addWidget(self.freehand_button)
        self.tool_button_group.addButton(self.freehand_button, 1)

        self.line_button = QPushButton("直線")
        self.line_button.setFont(toolbar_font)
        self.line_button.setCheckable(True)
        layout.addWidget(self.line_button)
        self.tool_button_group.addButton(self.line_button, 2)

        self.arrow_button = QPushButton("箭頭")
        self.arrow_button.setFont(toolbar_font)
        self.arrow_button.setCheckable(True)
        layout.addWidget(self.arrow_button)
        self.tool_button_group.addButton(self.arrow_button, 3)

        self.rect_button = QPushButton("矩形")
        self.rect_button.setFont(toolbar_font)
        self.rect_button.setCheckable(True)
        layout.addWidget(self.rect_button)
        self.tool_button_group.addButton(self.rect_button, 5)

        self.circle_button = QPushButton("圓形")
        self.circle_button.setFont(toolbar_font)
        self.circle_button.setCheckable(True)
        layout.addWidget(self.circle_button)
        self.tool_button_group.addButton(self.circle_button, 6)

        self.laser_button = QPushButton("雷射筆")
        self.laser_button.setFont(toolbar_font)
        self.laser_button.setCheckable(True)
        layout.addWidget(self.laser_button)
        self.tool_button_group.addButton(self.laser_button, 7)


        # --- 新增畫布與樣式下拉選單 ---
        canvas_label = QLabel("畫布:")
        canvas_label.setFont(toolbar_font)
        layout.addWidget(canvas_label)

        self.canvas_combo = QComboBox()
        self.canvas_combo.setFont(toolbar_font)
        self.canvas_combo.addItems(["桌面", "黑板", "白板", "純色"])
        self.canvas_combo.currentIndexChanged.connect(self.handle_canvas_change)
        layout.addWidget(self.canvas_combo)

        pattern_label = QLabel("樣式:")
        pattern_label.setFont(toolbar_font)
        layout.addWidget(pattern_label)

        self.pattern_combo = QComboBox()
        self.pattern_combo.setFont(toolbar_font)
        self.pattern_combo.addItems(["無", "細方格", "粗方格"])
        self.pattern_combo.currentIndexChanged.connect(self.handle_pattern_change)
        layout.addWidget(self.pattern_combo)

        # --- 原有按鈕 ---
        self.color_button = QPushButton("顏色")
        self.color_button.setFont(toolbar_font) # 套用字體
        self.color_button.clicked.connect(self.choose_color)
        self.update_color_button_style() # 設定初始顏色按鈕樣式
        layout.addWidget(self.color_button)

        width_label = QLabel("粗細:")
        width_label.setFont(toolbar_font) # 套用字體
        layout.addWidget(width_label)
        
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 20)
        self.width_slider.setValue(self.pen_width)
        self.width_slider.setToolTip(f"畫筆粗細: {self.pen_width}")
        self.width_slider.valueChanged.connect(self.set_pen_width)
        self.width_slider.setMinimumWidth(80) # 新增：設定最小寬度，避免在較低解析度下被過度壓縮
        layout.addWidget(self.width_slider)

        # --- 新增：平滑化選項 ---
        self.smooth_button = QPushButton("平滑化")
        self.smooth_button.setFont(toolbar_font)
        self.smooth_button.setCheckable(True) # 設定為可切換狀態的按鈕
        self.smooth_button.setChecked(self.smoothing_enabled)
        self.smooth_button.setToolTip("啟用後，手繪筆觸會更圓滑")
        self.smooth_button.toggled.connect(self.toggle_smoothing)
        layout.addWidget(self.smooth_button)

        self.eraser_button = QPushButton("橡皮擦")
        self.eraser_button.setFont(toolbar_font) # 套用字體
        self.eraser_button.setCheckable(True)
        self.tool_button_group.addButton(self.eraser_button, 4) # 將橡皮擦也加入按鈕組
        layout.addWidget(self.eraser_button)

        # --- 新增：復原與重做按鈕 ---
        self.undo_button = QPushButton("復原")
        self.undo_button.setFont(toolbar_font)
        self.undo_button.clicked.connect(self.undo)
        layout.addWidget(self.undo_button)

        self.redo_button = QPushButton("重做")
        self.redo_button.setFont(toolbar_font)
        self.redo_button.clicked.connect(self.redo)
        layout.addWidget(self.redo_button)
        self.clear_button = QPushButton("清除")
        self.clear_button.setFont(toolbar_font) # 套用字體
        self.clear_button.clicked.connect(self.clear_screen)
        layout.addWidget(self.clear_button)

        # 新增儲存按鈕
        self.save_button = QPushButton("儲存")
        self.save_button.setFont(toolbar_font)
        self.save_button.clicked.connect(self.handle_save_action)
        layout.addWidget(self.save_button) # 修正：將儲存按鈕添加到版面配置中

        self.exit_button = QPushButton("退出 (Esc)")
        self.exit_button.setFont(toolbar_font) # 套用字體
        self.exit_button.clicked.connect(self.end_drawing_mode)
        layout.addWidget(self.exit_button)

        # 連接按鈕組的點擊信號到處理函式
        self.tool_button_group.buttonClicked[int].connect(self.handle_tool_change)

        # 為工具列中的所有子元件安裝事件過濾器，以便 MovableToolbar 可以攔截它們的滑鼠事件
        for widget in toolbar.findChildren(QWidget):
            widget.installEventFilter(toolbar)

        toolbar.setLayout(layout)
        toolbar.adjustSize()
        # 工具列的初始位置將由 load_settings 處理
        return toolbar

    def _move_toolbar_to_default_position(self):
        """將工具列移動到預設的右下角位置。"""
        # 確保在呼叫此方法時工具列已經有正確的大小
        self.toolbar.adjustSize()
        x = self.width() - self.toolbar.width() - 20
        y = self.height() - self.toolbar.height() - 40
        self.toolbar.move(x, y)

    def toggle_toolbar_lock(self, checked):
        """鎖定或解鎖工具列的拖曳功能。"""
        self.toolbar.is_locked = checked
        if checked:
            self.lock_button.setIcon(self.lock_icon)
            self.lock_button.setToolTip("工具列已鎖定 (點擊解鎖)")
        else:
            self.lock_button.setIcon(self.unlock_icon)
            self.lock_button.setToolTip("工具列未鎖定 (點擊鎖定)")

    def toggle_smoothing(self, checked):
        """切換筆觸平滑化功能的開關。"""
        self.smoothing_enabled = checked

    def handle_tool_change(self, button_id):
        """根據被點擊的按鈕ID，更新目前的繪圖模式，並支援橡皮擦切換返回。"""
        # 如果點擊的是橡皮擦按鈕 (ID 4)
        if button_id == 4:
            # 如果當前已經是橡皮擦模式，則切換回之前的工具
            if self.draw_mode == 'eraser':
                button_to_check = self.tool_button_group.button(self.previous_tool_id)
                if button_to_check:
                    button_to_check.setChecked(True)
                # 關鍵修改：將 button_id 更新為上一個工具的 ID，讓後續的邏輯來處理模式切換，而不是直接返回
                button_id = self.previous_tool_id
        
        # 如果是從非橡皮擦模式切換到橡皮擦模式，儲存當前的工具ID
        if self.draw_mode != 'eraser' and button_id == 4:
            tool_map = {
                'freehand': 1, 'line': 2, 'arrow': 3,
                'rectangle': 5, 'circle': 6, 'laser_pointer': 7
            }
            self.previous_tool_id = tool_map.get(self.draw_mode, 1)

        # --- 更新繪圖模式 ---
        if button_id == 1:
            self.draw_mode = 'freehand'
        elif button_id == 2:
            self.draw_mode = 'line'
        elif button_id == 3:
            self.draw_mode = 'arrow'
        elif button_id == 4:
            self.draw_mode = 'eraser'
        elif button_id == 5:
            self.draw_mode = 'rectangle'
        elif button_id == 6:
            self.draw_mode = 'circle'
        elif button_id == 7:
            self.draw_mode = 'laser_pointer'
            self.laser_trail_segments.clear() # 切換到雷射筆時清空殘影
            self.laser_fade_timer.start(30) # 啟動雷射筆淡出計時器
        
        # 如果從雷射筆模式切換到其他模式，停止計時器
        if self.draw_mode != 'laser_pointer' and self.laser_fade_timer.isActive():
            self.laser_trail_segments.clear()
            self.laser_fade_timer.stop()
        self.update_color_button_style()

    def handle_canvas_change(self, index):
        """處理畫布下拉選單的變更。"""
        canvas_type = self.canvas_combo.itemText(index)
        previous_mode = self.canvas_mode

        if canvas_type == "桌面":
            self.canvas_mode = 'desktop'
        elif canvas_type == "黑板":
            self.canvas_mode = 'blackboard'
            self.canvas_color = QColor("#2E4636")  # 深綠色
        elif canvas_type == "白板":
            self.canvas_mode = 'whiteboard'
            self.canvas_color = QColor(Qt.white)
        elif canvas_type == "純色":
            color = QColorDialog.getColor(self.canvas_color, self, "選擇畫布顏色")
            if color.isValid():
                self.canvas_mode = 'solid'
                self.canvas_color = color
            else:
                # 如果使用者取消選色，恢復下拉選單到之前的選項
                self.canvas_combo.blockSignals(True)
                previous_index = self.canvas_combo.findText(self.get_mode_text(previous_mode))
                self.canvas_combo.setCurrentIndex(previous_index)
                self.canvas_combo.blockSignals(False)
        
        self.update()  # 觸發重繪

    def get_mode_text(self, mode):
        """根據模式名稱返回對應的下拉選單文字。"""
        if mode == 'desktop': return '桌面'
        if mode == 'blackboard': return '黑板'
        if mode == 'whiteboard': return '白板'
        if mode == 'solid': return '純色'
        return '桌面'  # 預設值

    def handle_pattern_change(self, index):
        """處理樣式下拉選單的變更。"""
        pattern_type = self.pattern_combo.itemText(index)
        if pattern_type == "無":
            self.pattern_mode = 'none'
        elif pattern_type == "細方格":
            self.pattern_mode = 'fine_grid'
        elif pattern_type == "粗方格":
            self.pattern_mode = 'coarse_grid'
        self.update()  # 觸發重繪

    def draw_pattern(self, painter):
        """根據目前的樣式模式繪製格線。"""
        if self.pattern_mode == 'none': return

        grid_size = 25 if self.pattern_mode == 'fine_grid' else 75
        pen = QPen(QColor(128, 128, 128, 100), 1, Qt.SolidLine)  # 半透明灰色
        painter.setPen(pen)
        for x in range(0, self.width(), grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_size):
            painter.drawLine(0, y, self.width(), y)

    def draw_arrow(self, painter, start_point, end_point):
        """
        繪製一個帶有箭頭的線條。
        :param painter: QPainter 物件
        :param start_point: 起始點 (QPoint)
        :param end_point: 結束點 (QPoint)
        """
        line = end_point - start_point
        if line.isNull(): return # 避免對長度為零的線進行數學運算
        angle = math.atan2(-line.y(), line.x())
        arrow_size = self.pen_width * 3 + 10 # 箭頭大小與畫筆粗細相關

        painter.drawLine(start_point, end_point)

        # 計算箭頭兩翼的座標
        arrow_p1 = end_point - QPoint(int(math.cos(angle + math.pi / 6) * arrow_size), int(-math.sin(angle + math.pi / 6) * arrow_size))
        arrow_p2 = end_point - QPoint(int(math.cos(angle - math.pi / 6) * arrow_size), int(-math.sin(angle - math.pi / 6) * arrow_size))
        painter.drawLine(end_point, arrow_p1)
        painter.drawLine(end_point, arrow_p2)

    def _get_constrained_point(self, start_point: QPoint, current_point: QPoint) -> QPoint:
        """
        根據起始點和當前點，計算一個受約束的終點，以形成正方形的邊界框。
        這用於繪製正方形和正圓。
        """
        dx = current_point.x() - start_point.x()
        dy = current_point.y() - start_point.y()

        # 決定邊長，取絕對值較大的那個差值
        side = max(abs(dx), abs(dy))

        # 根據原始方向調整終點，使其形成正方形
        constrained_x = start_point.x() + (side if dx > 0 else -side)
        constrained_y = start_point.y() + (side if dy > 0 else -side)
        return QPoint(constrained_x, constrained_y)

    def _fade_laser_trail(self):
        """
        定時器觸發，減少雷射筆殘影的透明度並移除完全透明的線段。
        """
        if not self.laser_trail_segments:
            return

        new_segments = []
        for start_p, end_p, opacity in self.laser_trail_segments:
            new_opacity = opacity - self.fade_step
            if new_opacity > 0:
                new_segments.append((start_p, end_p, new_opacity))
        self.laser_trail_segments = new_segments
        self.update() # 請求重繪
    def save_settings(self):
        """將畫筆與工具列設定儲存到設定檔。"""
        self.settings.setValue("pen_color", self.pen_color)
        self.settings.setValue("pen_width", self.pen_width)
        # 新增：儲存工具列位置與鎖定狀態
        if self.toolbar:
            # 直接儲存 QRect 物件，它包含位置和大小，更為穩健
            self.settings.setValue("toolbar_geometry", self.toolbar.geometry())
            self.settings.setValue("smoothing_enabled", self.smoothing_enabled)
            self.settings.setValue("toolbar_locked", self.toolbar.is_locked)
        self.settings.sync() # 強制寫入

    def load_settings(self):
        """從設定檔載入畫筆與工具列設定。"""
        # 載入顏色，如果找不到，預設為紅色
        color = self.settings.value("pen_color", QColor(Qt.red))
        self.pen_color = color if isinstance(color, QColor) and color.isValid() else QColor(Qt.red)

        # 載入粗細，如果找不到，預設為 5
        width = self.settings.value("pen_width", 5, type=int)
        self.pen_width = width

        # 更新 UI
        self.width_slider.setValue(self.pen_width)
        self.update_color_button_style()

        # 新增：載入工具列設定
        toolbar_geometry = self.settings.value("toolbar_geometry", None)
        if toolbar_geometry is not None and isinstance(toolbar_geometry, QRect):
            # 檢查儲存的位置是否在任何一個可用的螢幕範圍內
            available_geometry = QApplication.desktop().availableGeometry(toolbar_geometry.topLeft())
            if available_geometry.contains(toolbar_geometry.topLeft()):
                self.toolbar.setGeometry(toolbar_geometry)
            else:
                self._move_toolbar_to_default_position()
        else:
            self._move_toolbar_to_default_position()

        toolbar_locked = self.settings.value("toolbar_locked", False, type=bool)
        self.lock_button.setChecked(toolbar_locked)

        # 載入平滑化設定
        smoothing_enabled = self.settings.value("smoothing_enabled", True, type=bool)
        self.smooth_button.setChecked(smoothing_enabled)

    def _save_history(self):
        """將當前的畫布狀態儲存到歷史紀錄堆疊中。"""
        # 當有新的繪圖動作時，清空重做堆疊
        self.redo_stack.clear()
        # 限制歷史紀錄的大小
        if len(self.history_stack) >= self.history_limit:
            del self.history_stack[0]
        self.history_stack.append(self.image.copy())
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        """根據歷史紀錄堆疊的狀態，更新復原/重做按鈕的可用性。"""
        # 如果歷史紀錄超過1個（初始的空白狀態），則可以復原
        self.undo_button.setEnabled(len(self.history_stack) > 1)
        # 如果重做堆疊中有內容，則可以重做
        self.redo_button.setEnabled(bool(self.redo_stack))

    def undo(self):
        """回到上一個繪圖狀態。"""
        if len(self.history_stack) > 1:
            self.redo_stack.append(self.history_stack.pop())
            self.image = self.history_stack[-1].copy()
            self.update()
            self._update_undo_redo_buttons()

    def redo(self):
        """重新套用一個已復原的繪圖狀態。"""
        if self.redo_stack:
            self.history_stack.append(self.redo_stack.pop())
            self.image = self.history_stack[-1].copy()
            self.update()
            self._update_undo_redo_buttons()

    def toggle_drawing_mode(self, enable: bool):
        if enable:
            # 關鍵修改：在顯示畫布前，擷取當前的桌面作為背景
            screen = QApplication.primaryScreen()
            # grabWindow(0) 表示擷取整個螢幕
            self.background_pixmap = screen.grabWindow(0)

            # 初始化歷史紀錄，儲存一個空白的初始狀態
            self.image.fill(Qt.transparent)
            self.history_stack = [self.image.copy()]
            self.redo_stack = []
            self._update_undo_redo_buttons()

            self.toolbar.show()
            self.showFullScreen()
            self.raise_()
            self.activateWindow()
            self.setFocus()
        else:
            self.toolbar.hide()
            self.hide()

    def update_color_button_style(self):
        """根據當前狀態（畫筆或橡皮擦）更新顏色按鈕的樣式。"""
        # 此樣式必須包含所有屬性，因為它會覆蓋由父元件QSS提供的預設QPushButton樣式。
        base_style = """
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 12px;
            font-weight: bold;
        """
        if self.draw_mode == 'eraser':
            # 橡皮擦模式下，顏色按鈕顯示為灰色
            bg_color = "#5A6B7C"
        else:
            # 畫筆模式下，顯示當前畫筆顏色
            bg_color = self.pen_color.name()
        
        self.color_button.setStyleSheet(f"background-color: {bg_color}; {base_style}")

    def choose_color(self):
        color = QColorDialog.getColor(self.pen_color, self, "選擇畫筆顏色")
        if color.isValid():
            self.pen_color = color
            # 如果當前是橡皮擦模式，選擇顏色後自動切換回手繪模式
            if self.draw_mode == 'eraser':
                self.freehand_button.setChecked(True)
                self.handle_tool_change(self.tool_button_group.id(self.freehand_button))
            self.update_color_button_style()

    def set_pen_width(self, width):
        self.pen_width = width
        self.width_slider.setToolTip(f"畫筆粗細: {self.pen_width}")

    def clear_screen(self):
        self.image.fill(Qt.transparent)
        self._save_history() # 讓清除動作可以被復原
        self.update()

    def handle_save_action(self):
        """彈出對話框，讓使用者選擇儲存全部或儲存選取範圍。"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("選擇儲存方式")
        msg_box.setText("您要儲存整個畫面，還是只儲存圈選的範圍？")
        
        save_all_button = msg_box.addButton("儲存全部", QMessageBox.ActionRole)
        save_crop_button = msg_box.addButton("儲存選取", QMessageBox.ActionRole)
        msg_box.addButton("取消", QMessageBox.RejectRole)
        
        msg_box.exec_()
        
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == save_all_button:
            self.save_drawing()
        elif clicked_button == save_crop_button:
            self.draw_mode = 'crop'

    def save_cropped_area(self, crop_rect):
        """將指定的圈選範圍儲存為圖片檔案。"""
        # 創建一個新的 QPixmap，用於合併背景和畫記
        combined_pixmap = QPixmap(self.size())
        painter = QPainter(combined_pixmap)

        # 1. 繪製背景
        if self.canvas_mode == 'desktop' and self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode == 'blackboard':
            painter.fillRect(self.rect(), QColor("#2E4636"))
        elif self.canvas_mode == 'whiteboard':
            painter.fillRect(self.rect(), Qt.white)
        elif self.canvas_mode == 'solid':
            painter.fillRect(self.rect(), self.canvas_color)

        # 2. 繪製樣式遮罩
        self.draw_pattern(painter)

        # 3. 繪製使用者筆跡
        painter.drawPixmap(self.rect(), self.image)
        painter.end()

        # 4. 複製圈選的區域並儲存
        cropped_pixmap = combined_pixmap.copy(crop_rect)
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存圈選範圍", "", "PNG 圖片 (*.png);;JPEG 圖片 (*.jpg *.jpeg);;所有檔案 (*)")
        if file_path:
            cropped_pixmap.save(file_path)

    def save_drawing(self):
        """將當前畫布內容（包含背景截圖和畫記）儲存為圖片檔案。"""
        # 創建一個新的 QPixmap，用於合併背景和畫記
        combined_pixmap = QPixmap(self.size())
        painter = QPainter(combined_pixmap)

        # 1. 繪製背景
        if self.canvas_mode == 'desktop' and self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode == 'blackboard':
            painter.fillRect(self.rect(), QColor("#2E4636"))
        elif self.canvas_mode == 'whiteboard':
            painter.fillRect(self.rect(), Qt.white)
        elif self.canvas_mode == 'solid':
            painter.fillRect(self.rect(), self.canvas_color)

        # 2. 繪製樣式遮罩
        self.draw_pattern(painter)

        # 3. 繪製使用者筆跡
        painter.drawPixmap(self.rect(), self.image)
        painter.end()

        # 彈出檔案儲存對話框
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存畫記", "", "PNG 圖片 (*.png);;JPEG 圖片 (*.jpg *.jpeg);;所有檔案 (*)")
        if file_path:
            combined_pixmap.save(file_path)

    def end_drawing_mode(self):
        self.save_settings() # 儲存設定
        self.toggle_drawing_mode(False)
        self.drawing_mode_ended.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

            if self.draw_mode == 'laser_pointer':
                self.laser_trail_segments.clear() # 開始新的雷射筆軌跡
                # 雷射筆模式不需要 start_point/current_point，直接用 last_point
            elif self.draw_mode in ['line', 'arrow', 'rectangle', 'circle', 'crop']: # 這些模式需要 start_point 和 current_point
                # 對於矩形和圓形，如果按下 Shift 鍵，則在 mouseMoveEvent 中會進行約束
                # 但在 mousePressEvent 中，start_point 和 current_point 仍然是原始的點擊位置
                # 實際的約束會在 mouseMoveEvent 和 mouseReleaseEvent 中應用
                
                self.start_point = event.pos()
                self.current_point = event.pos()
            elif self.draw_mode == 'freehand' or self.draw_mode == 'eraser':
                if self.draw_mode == 'freehand' and self.smoothing_enabled:
                    self.point_buffer = [event.pos()]

                # 對於手繪和橡皮擦，按下時就畫一個點，以處理單擊的情況
                painter = QPainter(self.image)
                if self.draw_mode == 'eraser':
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.setPen(QPen(Qt.transparent, self.pen_width * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                else: # freehand
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPoint(self.last_point)
                painter.end()
                self.update()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            if self.draw_mode == 'laser_pointer':
                self.laser_trail_segments.append((self.last_point, event.pos(), 255)) # 255為完全不透明
                self.last_point = event.pos()
            elif self.draw_mode in ['line', 'arrow', 'rectangle', 'circle', 'crop']: # 這些模式需要即時預覽
                if event.modifiers() & Qt.ShiftModifier and self.draw_mode in ['rectangle', 'circle']:
                    # 如果按下 Shift 鍵且是矩形或圓形模式，則約束繪圖點為正方形
                    self.current_point = self._get_constrained_point(self.start_point, event.pos())
                else:
                    self.current_point = event.pos()
            elif self.draw_mode == 'freehand' or self.draw_mode == 'eraser':
                if self.draw_mode == 'freehand' and self.smoothing_enabled:
                    self.point_buffer.append(event.pos())
                    if len(self.point_buffer) >= 3:
                        # 使用二次貝茲曲線來平滑筆觸
                        p1 = self.point_buffer[-3]
                        p2 = self.point_buffer[-2]
                        p3 = self.point_buffer[-1]

                        mid1 = QPoint((p1.x() + p2.x()) // 2, (p1.y() + p2.y()) // 2)
                        mid2 = QPoint((p2.x() + p3.x()) // 2, (p2.y() + p3.y()) // 2)

                        painter = QPainter(self.image)
                        painter.setRenderHint(QPainter.Antialiasing)
                        painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        
                        path = QPainterPath()
                        path.moveTo(mid1)
                        path.quadTo(p2, mid2) # p2 是控制點
                        painter.drawPath(path)
                        painter.end()
                else: # 原始的非平滑繪圖邏輯 (也用於橡皮擦)
                    painter = QPainter(self.image)
                    if self.draw_mode == 'eraser':
                        painter.setCompositionMode(QPainter.CompositionMode_Clear)
                        painter.setPen(QPen(Qt.transparent, self.pen_width * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    else: # freehand (not smoothed)
                        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                        painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    
                    painter.drawLine(self.last_point, event.pos())
                    self.last_point = event.pos()
                    painter.end()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            save_needed = False # 標記是否需要儲存到歷史紀錄

            # 處理圖形繪製模式 (直線、箭頭、矩形、圓形)
            if self.draw_mode in ['line', 'arrow', 'rectangle', 'circle']:
                final_point = event.pos()
                if event.modifiers() & Qt.ShiftModifier and self.draw_mode in ['rectangle', 'circle']:
                    final_point = self._get_constrained_point(self.start_point, event.pos())

                # 只有在圖形有實際大小時（非單純點擊），才進行繪製和儲存
                if self.start_point != final_point:
                    painter = QPainter(self.image)
                    painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    if self.draw_mode == 'line':
                        painter.drawLine(self.start_point, final_point)
                    elif self.draw_mode == 'arrow':
                        self.draw_arrow(painter, self.start_point, final_point)
                    elif self.draw_mode == 'rectangle':
                        painter.drawRect(QRect(self.start_point, final_point))
                    elif self.draw_mode == 'circle':
                        painter.drawEllipse(QRect(self.start_point, final_point))
                    painter.end()
                    save_needed = True
                
                self.start_point = None
                self.current_point = None
            elif self.draw_mode == 'crop':
                # 只有在圈選了有效範圍時才觸發儲存
                if self.start_point and self.current_point and self.start_point != event.pos():
                    crop_rect = QRect(self.start_point, event.pos()).normalized()
                    self.save_cropped_area(crop_rect)
                
                # 動作完成後，重設回手繪模式
                self.freehand_button.setChecked(True)
                self.handle_tool_change(self.tool_button_group.id(self.freehand_button))
                
                self.start_point = None
                self.current_point = None
                save_needed = False # 圈選儲存不屬於畫布歷史
            # 處理手繪或橡皮擦模式
            elif self.draw_mode in ['freehand', 'eraser']:
                if self.draw_mode == 'freehand' and self.smoothing_enabled:
                    # 處理筆劃結束時剩餘的點 (例如非常短的筆劃)
                    if len(self.point_buffer) == 2:
                        p1 = self.point_buffer[0]
                        p2 = self.point_buffer[1]
                        painter = QPainter(self.image)
                        painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        painter.drawLine(p1, p2)
                        painter.end()
                    self.point_buffer.clear()

                # 標記需要儲存歷史紀錄
                save_needed = True

            if save_needed:
                self._save_history()

            self.update()

    def paintEvent(self, event):
        # 增加一個保護，如果視窗本身的大小無效，則不進行任何繪製操作。
        # 這可以防止在視窗狀態轉換的極端情況下，試圖在一個0x0的元件上繪圖而導致的錯誤。
        if self.width() <= 0 or self.height() <= 0:
            return

        # 關鍵修改：疊加繪製
        painter = QPainter(self)

        # 1. 繪製背景層 (畫布)
        if self.canvas_mode == 'desktop':
            # 在繪製前，進行嚴格的檢查，確保 pixmap 物件存在且有效
            if self.background_pixmap and not self.background_pixmap.isNull():
                painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode == 'blackboard':
            painter.fillRect(self.rect(), QColor("#2E4636"))
        elif self.canvas_mode == 'whiteboard':
            painter.fillRect(self.rect(), Qt.white)
        elif self.canvas_mode == 'solid':
            painter.fillRect(self.rect(), self.canvas_color)

        # 2. 繪製樣式層 (格線)
        self.draw_pattern(painter)

        # 3. 繪製筆跡層 (使用者畫的內容)，同樣進行嚴格檢查
        if self.image and not self.image.isNull():
            painter.drawPixmap(self.rect(), self.image)

        # 4. 新增：繪製即時預覽圖形
        if self.drawing and self.start_point and self.current_point:
            if self.draw_mode == 'crop':
                # 使用不同的樣式來預覽圈選範圍
                preview_pen = QPen(QColor(0, 120, 255), 2, Qt.DashLine)
                painter.setPen(preview_pen)
                painter.drawRect(QRect(self.start_point, self.current_point))
            else:
                # 使用虛線來表示預覽
                preview_pen = QPen(self.pen_color, self.pen_width, Qt.DashLine)
                painter.setPen(preview_pen)
                if self.draw_mode == 'line':
                    painter.drawLine(self.start_point, self.current_point)
                elif self.draw_mode == 'arrow':
                    # 預覽箭頭也用虛線
                    self.draw_arrow(painter, self.start_point, self.current_point)
                elif self.draw_mode == 'rectangle':
                    painter.drawRect(QRect(self.start_point, self.current_point))
                elif self.draw_mode == 'circle':
                    painter.drawEllipse(QRect(self.start_point, self.current_point))
        
        # 5. 繪製雷射筆殘影
        if self.laser_trail_segments:
            painter.setRenderHint(QPainter.Antialiasing)  # 讓線條更平滑

            num_segments = len(self.laser_trail_segments)
            max_width = self.pen_width

            # 定義在筆跡頭尾用於實現寬度變化的線段數量
            taper_length = min(15, num_segments // 2)

            for i, (start_p, end_p, opacity) in enumerate(self.laser_trail_segments):
                # --- 寬度計算，實現書寫壓感效果 ---
                if taper_length > 0:
                    if i < taper_length:
                        # 筆跡開始部分，寬度由窄變寬
                        current_width = max(1, max_width * ((i + 1) / taper_length))
                    elif i >= num_segments - taper_length:
                        # 筆跡結束部分，寬度由寬變窄
                        current_width = max(1, max_width * ((num_segments - i) / taper_length))
                    else:
                        # 筆跡中間部分，使用完整寬度
                        current_width = max_width
                else:
                    # 對於非常短的筆跡，直接使用完整寬度
                    current_width = max_width

                laser_pen = QPen(self.pen_color)
                laser_pen.setWidth(int(current_width))
                # 使用圓頭畫筆，讓線段連接處更平滑
                laser_pen.setCapStyle(Qt.RoundCap)
                laser_pen.setJoinStyle(Qt.RoundJoin)

                # 設定透明度以實現淡出效果
                current_color = laser_pen.color()
                laser_pen.setColor(QColor(current_color.red(),
                                          current_color.green(),
                                          current_color.blue(),
                                          opacity)) # 設定透明度
                painter.setPen(laser_pen)
                painter.drawLine(start_p, end_p)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.end_drawing_mode()

    def resizeEvent(self, event):
        new_size = self.size()
        # 如果畫布無效，或尺寸與視窗不符，就重新建立畫布
        if self.image.isNull() or self.image.size() != new_size:
            if not new_size.isValid() or new_size.width() <= 0 or new_size.height() <= 0:
                # 如果視窗被縮小到無效尺寸，則不執行任何操作，避免建立無效的 QPixmap
                return

            # 建立一個新的、尺寸正確的畫布
            old_image = self.image            
            new_image = QPixmap(new_size)
            new_image.fill(Qt.transparent)

            # 將舊畫布的內容繪製到新畫布上，以保留現有筆跡
            if not old_image.isNull():
                p = QPainter(new_image)
                p.drawPixmap(QPoint(0, 0), old_image)
                p.end()

            self.image = new_image