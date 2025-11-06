import sys
import os

# --- PyInstaller & Qt Plugin Fix ---
# This block must be at the very top of the file, before any PyQt5 imports.
# It sets up the environment for both packaged executables and source execution.
# The key is to set the QT_QPA_PLATFORM_PLUGIN_PATH environment variable
# *before* QApplication is created.

# 1. Handle DLL search path for one-file executables on Windows.
# This helps libraries like pyaudio find their dependencies.
if sys.platform == 'win32' and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    os.add_dll_directory(sys._MEIPASS)

# 2. Set the Qt plugin path. This is crucial for the app to find qwindows.dll.
if getattr(sys, 'frozen', False):
    # Packaged executable: determine base path for one-file or one-folder mode.
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    plugin_path = os.path.join(base_path, 'PyQt5', 'Qt5', 'plugins')
else:
    # Running from source. We need to find the path relative to the PyQt5 package.
    # This is the first import of a PyQt5 module, which is safe.
    from PyQt5 import QtCore
    plugin_path = os.path.join(os.path.dirname(QtCore.__file__), "Qt5", "plugins")

os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QMessageBox, QToolButton, QStyle) # 引入 QHBoxLayout, QToolButton 和 QStyle
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QPropertyAnimation, QEasingCurve, QSettings # 引入動畫相關工具和設定
from PyQt5.QtGui import QPainter, QColor, QBrush # 引入繪圖相關工具

from screen_draw import ScreenDrawWindow # 匯入實際的螢幕畫記視窗
from timer import TimerWidget
# from volume_monitor import VolumeMonitorWidget # 移除音量監測工具
from random_picker import RandomPickerWidget # 匯入實際的抽籤工具

class MainToolBar(QWidget):
    """主工具列，作為所有功能的啟動入口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("課堂輔助工具")

        # --- 美化: 視窗屬性 ---
        self.setWindowFlags(
            Qt.FramelessWindowHint |    # 無邊框
            Qt.WindowStaysOnTopHint |   # 永遠在最上層
            Qt.Tool                     # 不顯示在任務欄
        )
        self.setAttribute(Qt.WA_TranslucentBackground) # 啟用此屬性以實現真正的透明背景

        # --- 可收折功能屬性 ---
        self.is_expanded = False # 預設為收合狀態
        self.animation = QPropertyAnimation()
        self.animation.setDuration(150) # 動畫持續時間 (毫秒)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic) # 平滑的動畫曲線

        # --- 拖動視窗所需的變數 ---
        self.mouse_down = False
        self.offset = QPoint()

        # 這些變數用來持有子視窗的實例，避免被記憶體回收
        self.draw_window = None
        self.timer_widget = None
        # self.volume_monitor_widget = None # 移除音量監測工具的實例
        self.picker_widget = None
        
        # 新增：使用 QSettings 來儲存/載入視窗位置
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "MyClassroomTools", "MainToolBar")

        # --- QSS 樣式表 (只針對子元件) ---
        self.setStyleSheet("""
            QToolButton {
                color: white;
                background-color: #7E8A97; /* 莫蘭迪灰藍色 (Muted Blue-Gray) */
                border: none;
                border-radius: 8px; /* 圓角按鈕 */
                padding: 4px; /* 進一步減少內邊距 */
                font-size: 6pt; /* 進一步縮小字體 */
                font-weight: bold;
                min-width: 60px; /* 進一步縮小按鈕最小寬度 */
            }
            QToolButton:hover {
                background-color: #98A3AF; /* 滑鼠懸停時稍亮 */
            }
            QToolButton:pressed {
                background-color: #697582; /* 按下時稍暗 */
            }
        """)

        # --- 佈局結構調整 ---
        # 主佈局，垂直排列
        main_layout = QVBoxLayout(self)
        # 增加底部邊距 (從 4 增加到 16)，為浮水印提供足夠的空間
        # 讓它不會被下方的收合按鈕遮擋
        main_layout.setContentsMargins(4, 4, 4, 16)
        main_layout.setSpacing(5)

        # 1. 可收折的按鈕容器
        self.button_container = QWidget()
        container_layout = QVBoxLayout(self.button_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(5)
        
        # 將動畫目標設為按鈕容器，並預設為收合狀態
        self.animation.setTargetObject(self.button_container)
        self.animation.setPropertyName(b"maximumHeight")
        # 當動畫值改變時，呼叫自訂函式來向上調整視窗大小和位置
        self.animation.valueChanged.connect(self._handle_resize_upwards)

        # --- 美化: 使用帶有圖示的 QToolButton ---
        icon_size = QSize(24, 24) # 進一步縮小圖示尺寸

        self.draw_button = QToolButton()
        self.draw_button.setText("螢幕畫記")
        self.draw_button.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
        self.draw_button.setIconSize(icon_size)
        self.draw_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.timer_button = QToolButton()
        self.timer_button.setText("計時器")
        self.timer_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay)) # 替換為可用的標準圖示
        self.timer_button.setIconSize(icon_size)
        self.timer_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.picker_button = QToolButton()
        self.picker_button.setText("抽籤工具")
        self.picker_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        self.picker_button.setIconSize(icon_size)
        self.picker_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # # 移除音量監測按鈕
        # self.volume_monitor_button = QToolButton()
        # self.volume_monitor_button.setText("音量監測")
        # self.volume_monitor_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume)) # 使用音量圖示
        # self.volume_monitor_button.setIconSize(icon_size)
        # self.volume_monitor_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # 新增退出按鈕
        self.exit_button = QToolButton()
        self.exit_button.setText("退出")
        self.exit_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton)) # 使用關閉圖示
        self.exit_button.setIconSize(icon_size)
        self.exit_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # 將按鈕加入可收折的容器中
        container_layout.addWidget(self.draw_button)
        container_layout.addWidget(self.timer_button)
        container_layout.addWidget(self.picker_button)
        # container_layout.addWidget(self.volume_monitor_button)
        container_layout.addWidget(self.exit_button)

        # 2. 收折/展開按鈕
        self.toggle_button = QToolButton()
        self.toggle_button.setArrowType(Qt.UpArrow) # 預設顯示向上箭頭 (表示可展開)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }") # 移除邊框使其更像一個圖示

        # 將按鈕容器和收折按鈕加入主佈局
        main_layout.addWidget(self.button_container)
        main_layout.addWidget(self.toggle_button, 0, Qt.AlignCenter)

        # --- 連接信號 ---
        self.draw_button.clicked.connect(self.toggle_drawing)
        self.timer_button.clicked.connect(self.open_timer)
        self.picker_button.clicked.connect(self.open_picker)
        # self.volume_monitor_button.clicked.connect(self.open_volume_monitor) # 移除音量監測功能
        self.exit_button.clicked.connect(QApplication.quit) # 連接退出功能
        self.toggle_button.clicked.connect(self.toggle_expansion) # 連接收折/展開功能

        # --- 強制設定視窗寬度 ---
        self.setFixedWidth(80)

        # 初始設定為收合狀態，然後再計算視窗大小
        self.button_container.setMaximumHeight(0)
        self.adjustSize() # 讓佈局管理器自動計算初始的收合尺寸

        # 連接到應用程式的 aboutToQuit 信號，以執行關閉前的清理工作
        app = QApplication.instance()
        app.aboutToQuit.connect(self.on_application_quit)

        self.load_position() # 載入上次的視窗位置

    def paintEvent(self, event):
        """覆寫 paintEvent 來手動繪製背景，這樣才能接收滑鼠事件。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # 讓圓角更平滑
        painter.setPen(Qt.NoPen) # 不需要邊框
        # 設定畫刷顏色為半透明
        painter.setBrush(QBrush(QColor(62, 74, 89, 220)))
        # 繪製一個填滿整個視窗的圓角矩形
        painter.drawRoundedRect(self.rect(), 8, 8)

        # --- 新增：繪製右下角浮水印 ---
        painter.save() # 儲存當前繪圖狀態
        try:
            font = self.font()
            font.setPointSize(7) # 設定一個較小的字體
            painter.setFont(font)
            # 設定半透明的白色作為文字顏色
            painter.setPen(QColor(255, 255, 255, 120))

            text = "Build by 許俊義"
            metrics = painter.fontMetrics()
            # 計算文字位置，使其位於右下角並保留邊距
            x = self.width() - metrics.horizontalAdvance(text) - 8
            y = self.height() - metrics.descent() - 2
            painter.drawText(int(x), int(y), text)
        finally:
            painter.restore() # 恢復繪圖狀態，避免影響其他部分

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_down = True
            self.offset = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.mouse_down:
            self.move(event.globalPos() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.mouse_down = False
        event.accept()

    def on_application_quit(self):
        """
        在應用程式完全退出前，執行所有必要的清理工作。
        這包括安全地關閉背景執行緒和儲存設定。
        """
        # 1. 優先關閉任何可能阻塞的背景執行緒
        # if hasattr(self, 'volume_monitor_widget') and self.volume_monitor_widget and hasattr(self.volume_monitor_widget, 'shutdown'):
        #     self.volume_monitor_widget.shutdown()
        pass # 移除音量監測後，此處無需操作
        # 2. 執行緒關閉後，再儲存所有設定
        self.save_all_settings()

    def save_all_settings(self):
        """在應用程式關閉前，儲存所有需要持久化的設定。"""
        # 儲存主工具列自己的位置
        pos = self.pos()
        self.settings.setValue("pos_x", pos.x())
        self.settings.setValue("pos_bottom_y", pos.y() + self.height())
        self.settings.sync()

        # 遍歷所有子視窗，如果它們有 save_settings 方法，就呼叫它
        for widget in [self.draw_window, self.timer_widget, self.picker_widget]:
            if widget and hasattr(widget, 'save_settings'):
                widget.save_settings()

    def load_position(self):
        """載入上次儲存的視窗位置，若無則使用預設位置。"""
        # 讀取儲存的左下角位置
        pos_x = self.settings.value("pos_x", defaultValue=None, type=int)
        pos_bottom_y = self.settings.value("pos_bottom_y", defaultValue=None, type=int)

        if pos_x is not None and pos_bottom_y is not None:
            # 根據當前 (收合後) 的高度計算新的左上角 y 座標
            current_height = self.height()
            new_y = pos_bottom_y - current_height
            new_pos = QPoint(pos_x, new_y)

            # 檢查儲存的位置是否在任何一個可用的螢幕範圍內
            # 這可以防止在螢幕配置改變後，視窗在螢幕外開啟
            available_geometry = QApplication.desktop().availableGeometry(new_pos)
            if available_geometry.contains(new_pos):
                self.move(new_pos)
                return # 成功移動，結束函式

        # 如果沒有儲存的位置，或位置無效，則移至預設位置
        self._move_to_default_position()

    def _move_to_default_position(self):
        """將視窗移動到預設的左下角位置。"""
        screen_rect = QApplication.desktop().screenGeometry()
        x = 20 # 離左邊緣的距離
        y = screen_rect.height() - self.height() - 40 # 離下邊緣的距離 (40 考慮到 Windows 任務欄)
        self.move(x, y)

    def toggle_expansion(self):
        """處理工具列的展開與收合動畫。"""
        if self.is_expanded:
            # --- 收合 ---
            self.is_expanded = False
            # 箭頭變為向上，提示使用者可以點擊展開
            self.toggle_button.setArrowType(Qt.UpArrow)
            self.animation.setStartValue(self.button_container.sizeHint().height())
            self.animation.setEndValue(0)
        else:
            # --- 展開 ---
            self.is_expanded = True
            # 箭頭變為向下，提示使用者可以點擊收合
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.animation.setStartValue(0)
            self.animation.setEndValue(self.button_container.sizeHint().height())
        self.animation.start()

    def _handle_resize_upwards(self):
        """在動畫過程中，向上調整視窗位置和大小。"""
        old_height = self.height()
        self.adjustSize()
        new_height = self.height()
        self.move(self.x(), self.y() - (new_height - old_height))
        self.raise_() # 新增：在每次調整大小和位置後，都將視窗提升到最上層

    def raise_all_tools(self):
        """
        當畫布被點擊時，此方法會被呼叫，以確保所有工具視窗都保持在畫布之上。
        """
        self.raise_()
        if self.timer_widget and self.timer_widget.isVisible():
            self.timer_widget.raise_()
        if self.picker_widget and self.picker_widget.isVisible():
            self.picker_widget.raise_()

    def _start_drawing_after_animation(self):
        self.hide()
        # A brief delay to ensure the window is hidden before capturing the screen
        QTimer.singleShot(50, lambda: (
            self.draw_window.toggle_drawing_mode(True),
            self.show()
        ))

    def toggle_drawing(self):
        # 螢幕畫記視窗比較特殊，通常是全螢幕的
        if self.draw_window is None:
            self.draw_window = ScreenDrawWindow()
            # 連接畫記視窗的信號，以便在畫記模式從畫記視窗內部結束時更新主工具列的狀態
            self.draw_window.drawing_mode_ended.connect(self.on_drawing_mode_ended)
            # 新增：連接畫布點擊信號，以確保工具列保持在最上層
            self.draw_window.canvas_activated.connect(self.raise_all_tools)

        if not self.draw_window.isVisible():
            self.draw_button.setText("結束畫記") # 改變按鈕文字

            # 如果是展開的，就收合它，並等待動畫結束
            if self.is_expanded:
                self.toggle_expansion()
                # 動畫時長為 150ms，我們等待稍長一點的時間
                QTimer.singleShot(160, self._start_drawing_after_animation)
            else:
                # 如果本來就是收合的，直接開始畫圖程序
                self._start_drawing_after_animation()
        else:
            # 呼叫 end_drawing_mode() 而不是 toggle_drawing_mode(False)。
            # end_drawing_mode 會發射 drawing_mode_ended 信號，觸發 on_drawing_mode_ended 來重設按鈕文字。
            self.draw_window.end_drawing_mode()

    def on_drawing_mode_ended(self):
        """當畫記模式從畫記視窗內部 (例如按 Esc) 結束時被呼叫。"""
        self.draw_button.setText("螢幕畫記") # 恢復主工具列按鈕文字
        self.show() # 關鍵修改：在畫記結束後，重新顯示主工具列

    def open_timer(self):
        # 首次點擊時創建視窗，之後重複使用
        if self.timer_widget is None:
            self.timer_widget = TimerWidget()
        
        if not self.timer_widget.isVisible():
            self.timer_widget.show()
        else:
            # 如果視窗已存在，則將其帶到最上層並設為活動視窗
            self.timer_widget.raise_()
            self.timer_widget.activateWindow()

    def open_picker(self):
        # 首次點擊時創建視窗，之後重複使用
        if self.picker_widget is None:
            self.picker_widget = RandomPickerWidget()
        
        if not self.picker_widget.isVisible():
            self.picker_widget.show()
        else:
            # 如果視窗已存在，則將其帶到最上層並設為活動視窗
            self.picker_widget.raise_()
            self.picker_widget.activateWindow()

if __name__ == '__main__':
    # 啟用高 DPI 縮放，讓 Qt 自動根據系統 DPI 設定調整 UI 元素大小
    # 這應該能解決在不同解析度螢幕上 UI 元素大小不一致的問題
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps) # 確保高解析度圖示也被正確縮放
    app = QApplication(sys.argv)
    main_window = MainToolBar()
    main_window.show()
    sys.exit(app.exec_())