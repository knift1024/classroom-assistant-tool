import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QApplication, QMessageBox, QTabWidget, QListWidget)
from PyQt5.QtCore import QTimer, Qt, QTime, QSettings
from PyQt5.QtGui import QFont

class CountdownTab(QWidget):
    """倒數計時功能分頁"""
    def __init__(self):
        super().__init__()
        self.remaining_seconds = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        button_layout = QHBoxLayout()

        self.time_label = QLabel("00:00")
        # 將字體設定移至 QSS 樣式表中，以避免被覆蓋
        self.time_label.setObjectName("CountdownTimeLabel")
        self.time_label.setAlignment(Qt.AlignCenter)

        self.min_spinbox = QSpinBox()
        self.min_spinbox.setRange(0, 99)
        self.min_spinbox.setSuffix(" 分")
        self.sec_spinbox = QSpinBox()
        self.sec_spinbox.setRange(0, 59)
        self.sec_spinbox.setValue(10)
        self.sec_spinbox.setSuffix(" 秒")

        input_layout.addWidget(QLabel("設定時間:"))
        input_layout.addStretch()
        input_layout.addWidget(self.min_spinbox)
        input_layout.addWidget(self.sec_spinbox)

        self.start_button = QPushButton("開始")
        self.pause_button = QPushButton("暫停")
        self.reset_button = QPushButton("重設")

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)

        main_layout.addWidget(self.time_label)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.start_button.clicked.connect(self.start_timer)
        self.pause_button.clicked.connect(self.pause_timer)
        self.reset_button.clicked.connect(self.reset_timer)

        self.update_ui_state(running=False)

    def start_timer(self):
        minutes = self.min_spinbox.value()
        seconds = self.sec_spinbox.value()
        self.remaining_seconds = minutes * 60 + seconds

        if self.remaining_seconds > 0:
            self.timer.start(1000)
            self.update_ui_state(running=True)
            self.update_display()

    def pause_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.pause_button.setText("繼續")
        else:
            if self.remaining_seconds > 0:
                self.timer.start(1000)
                self.pause_button.setText("暫停")

    def reset_timer(self):
        self.timer.stop()
        self.remaining_seconds = 0
        self.update_display()
        self.update_ui_state(running=False)

    def update_countdown(self):
        self.remaining_seconds -= 1
        self.update_display()
        if self.remaining_seconds <= 0:
            self.timer.stop()
            self.update_ui_state(running=False)
            QApplication.beep()
            QMessageBox.information(self, "時間到！", "倒數計時結束！")

    def update_display(self):
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

    def update_ui_state(self, running: bool):
        self.start_button.setEnabled(not running)
        self.min_spinbox.setEnabled(not running)
        self.sec_spinbox.setEnabled(not running)

        self.pause_button.setEnabled(running)
        self.reset_button.setEnabled(running)

        if not running:
            self.pause_button.setText("暫停")

class StopwatchTab(QWidget):
    """碼表功能分頁"""
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.start_time = QTime(0, 0, 0)
        self.elapsed_time = QTime(0, 0, 0)
        self.timer = QTimer(self)
        self.timer.setInterval(10) # 每10毫秒更新一次，顯示更流暢
        self.timer.timeout.connect(self.update_stopwatch)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        self.time_label = QLabel("00:00:00.000")
        # 將字體設定移至 QSS 樣式表中，以避免被覆蓋
        self.time_label.setObjectName("StopwatchTimeLabel")
        self.time_label.setAlignment(Qt.AlignCenter)

        self.lap_list = QListWidget()

        self.start_stop_button = QPushButton("開始")
        self.lap_button = QPushButton("計次")
        self.reset_button = QPushButton("重設")

        button_layout.addWidget(self.start_stop_button)
        button_layout.addWidget(self.lap_button)
        button_layout.addWidget(self.reset_button)

        main_layout.addWidget(self.time_label)
        main_layout.addWidget(self.lap_list)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.start_stop_button.clicked.connect(self.toggle_start_stop)
        self.lap_button.clicked.connect(self.record_lap)
        self.reset_button.clicked.connect(self.reset_stopwatch)

        self.update_ui_state()

    def toggle_start_stop(self):
        if self.is_running:
            # 停止
            self.is_running = False
            self.timer.stop()
            self.elapsed_time = self.elapsed_time.addMSecs(self.start_time.msecsTo(QTime.currentTime()))
            self.start_stop_button.setText("繼續")
        else:
            # 開始或繼續
            self.is_running = True
            self.start_time = QTime.currentTime()
            self.timer.start()
            self.start_stop_button.setText("暫停")
        self.update_ui_state()

    def record_lap(self):
        lap_time = self.time_label.text()
        self.lap_list.insertItem(0, f"第 {self.lap_list.count() + 1} 次: {lap_time}")

    def reset_stopwatch(self):
        self.is_running = False
        self.timer.stop()
        self.start_time = QTime(0, 0, 0)
        self.elapsed_time = QTime(0, 0, 0)
        self.lap_list.clear()
        self.time_label.setText("00:00:00.000")
        self.start_stop_button.setText("開始")
        self.update_ui_state()

    def update_stopwatch(self):
        if self.is_running:
            current_elapsed = self.start_time.msecsTo(QTime.currentTime())
            total_time = self.elapsed_time.addMSecs(current_elapsed)
            self.time_label.setText(total_time.toString("mm:ss:zzz"))

    def update_ui_state(self):
        # 只有在計時器停止且時間不為0時，重設按鈕才可用
        can_reset = not self.is_running and (self.elapsed_time.msecsTo(QTime(0,0,0)) != 0)
        self.reset_button.setEnabled(can_reset)
        # 只有在計時器運行時，計次按鈕才可用
        self.lap_button.setEnabled(self.is_running)


class TimerWidget(QWidget):
    """一個包含倒數計時和碼表功能的計時器視窗"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("計時器")
        # --- 新增：讓視窗保持在最上層 ---
        # 這樣在螢幕畫記模式下，它才能顯示在畫布之上
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(400, 450)

        # 新增：使用 QSettings 來持久化儲存設定
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "MyClassroomTools", "TimerWidget")

        # 為整個小工具設定一個較大的基礎字型
        base_font = self.font()
        base_font.setPointSize(12) # 調整基礎字體大小
        self.setFont(base_font)

        # --- 美化: QSS 樣式表 ---
        self.setStyleSheet("""
            QWidget { /* Base for the whole widget, including tabs */
                background-color: #3E4A59; /* Dark Blue-Gray */
                color: white;
                font-size: 12pt; /* 使用點(pt)作為單位，更適合字體縮放 */
            }

            QTabWidget::pane { /* The area where tabs content is displayed */
                border: 1px solid #5A6B7C; /* Slightly lighter border */
                background-color: #3E4A59;
            }

            QTabBar::tab {
                background: #5A6B7C; /* Tab background */
                color: white;
                border: 1px solid #5A6B7C;
                border-bottom-color: #3E4A59; /* Same as pane color to hide border */
                border-top-left-radius: 4px;
                border-top-right-radius: 6px; /* 圓角稍大 */
                padding: 8px 12px; /* 調整內邊距 */
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background: #3E4A59; /* Selected tab background */
                border-color: #5A6B7C;
                border-bottom-color: #3E4A59; /* Same as pane color */
            }

            QTabBar::tab:hover {
                background: #697582; /* Hover tab background */
            }

            QPushButton {
                background-color: #7E8A97; /* Muted Blue-Gray */
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px; /* 調整內邊距 */
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #98A3AF; /* Lighter Muted Blue-Gray */
            }
            
            QPushButton:pressed {
                background-color: #697582; /* Darker Muted Blue-Gray */
            }

            QSpinBox, QListWidget {
                background-color: #5A6B7C; /* Slightly lighter than main background */
                color: white;
                border: 1px solid #7E8A97;
                border-radius: 5px;
                padding: 5px; /* 調整內邊距 */
            }
            QLabel {
                color: white;
            }

            /* --- 針對時間顯示標籤的特定樣式 --- */
            QLabel#CountdownTimeLabel {
                font-family: Arial, sans-serif;
                font-size: 48pt;
                font-weight: bold;
            }
            QLabel#StopwatchTimeLabel {
                font-family: Arial, sans-serif;
                font-size: 36pt;
                font-weight: bold;
            }
        """)
        # --- 建立分頁元件 ---
        tab_widget = QTabWidget()
        self.countdown_tab = CountdownTab()
        self.stopwatch_tab = StopwatchTab()

        tab_widget.addTab(self.countdown_tab, "倒數計時")
        tab_widget.addTab(self.stopwatch_tab, "碼表")

        # --- 主版面配置 ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tab_widget)

        self.load_settings()

    def load_settings(self):
        """從設定檔載入各分頁的設定。"""
        minutes = self.settings.value("Countdown/minutes", 1, type=int)
        seconds = self.settings.value("Countdown/seconds", 0, type=int)
        self.countdown_tab.min_spinbox.setValue(minutes)
        self.countdown_tab.sec_spinbox.setValue(seconds)

    def save_settings(self):
        """將各分頁的設定儲存到設定檔。"""
        minutes = self.countdown_tab.min_spinbox.value()
        seconds = self.countdown_tab.sec_spinbox.value()
        self.settings.setValue("Countdown/minutes", minutes)
        self.settings.setValue("Countdown/seconds", seconds)
        self.settings.sync()

    def closeEvent(self, event):
        """關閉視窗時確保所有計時器都停止，並隱藏視窗而不是銷毀它。"""
        self.save_settings()
        self.countdown_tab.timer.stop()
        self.stopwatch_tab.timer.stop()
        self.hide()
        event.ignore() # 忽略關閉事件，防止視窗被銷毀