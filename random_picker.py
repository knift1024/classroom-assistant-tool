import sys
import random
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QApplication, QMessageBox, QCheckBox, QTextEdit, QTabWidget, QListWidget)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

class NamePickerTab(QWidget):
    """姓名抽籤功能分頁"""
    def __init__(self):
        super().__init__()
        self.original_names = []
        self.remaining_names = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        controls_layout = QHBoxLayout()
        results_layout = QHBoxLayout()

        # --- 名單輸入區 ---
        name_input_layout = QVBoxLayout()
        name_input_layout.addWidget(QLabel("請貼上名單 (一行一個名字):"))
        self.name_list_input = QTextEdit()
        self.name_list_input.setPlaceholderText("王小明\n陳大華\n林美麗\n...")
        self.name_list_input.textChanged.connect(self.update_and_reset_list)
        name_input_layout.addWidget(self.name_list_input)

        # --- 控制項 ---
        controls_layout.addWidget(QLabel("抽出人數:"))
        self.draw_count_spinbox = QSpinBox()
        self.draw_count_spinbox.setRange(1, 99)
        self.draw_count_spinbox.setValue(1)
        controls_layout.addWidget(self.draw_count_spinbox)

        self.no_replacement_checkbox = QCheckBox("抽出後不放回")
        self.no_replacement_checkbox.setChecked(True) # 預設勾選
        controls_layout.addWidget(self.no_replacement_checkbox)
        controls_layout.addStretch()

        self.draw_button = QPushButton("抽籤！")
        self.draw_button.clicked.connect(self.perform_draw)
        controls_layout.addWidget(self.draw_button)

        self.reset_button = QPushButton("重設名單")
        self.reset_button.clicked.connect(self.update_and_reset_list)
        controls_layout.addWidget(self.reset_button)

        # --- 結果顯示區 ---
        drawn_layout = QVBoxLayout()
        drawn_layout.addWidget(QLabel("抽中名單:"))
        self.drawn_names_display = QListWidget()
        drawn_layout.addWidget(self.drawn_names_display)

        remaining_layout = QVBoxLayout()
        remaining_layout.addWidget(QLabel("剩餘名單:"))
        self.remaining_names_display = QListWidget()
        remaining_layout.addWidget(self.remaining_names_display)

        results_layout.addLayout(drawn_layout)
        results_layout.addLayout(remaining_layout)

        # --- 組合整體版面 ---
        main_layout.addLayout(name_input_layout, stretch=2) # 讓輸入框佔比較大空間
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(results_layout, stretch=3) # 讓結果列表佔比較大空間

    def update_and_reset_list(self):
        """從輸入框讀取名單，並重設所有列表"""
        names_text = self.name_list_input.toPlainText().strip()
        self.original_names = [name.strip() for name in names_text.split('\n') if name.strip()]
        self.remaining_names = self.original_names.copy()

        self.drawn_names_display.clear()
        self.remaining_names_display.clear()
        self.remaining_names_display.addItems(self.remaining_names)

    def perform_draw(self):
        """執行姓名抽籤"""
        draw_count = self.draw_count_spinbox.value()
        if draw_count > len(self.remaining_names):
            QMessageBox.warning(self, "數量不足", "要抽出的人數比剩餘名單的人數還多！")
            return

        drawn_names = random.sample(self.remaining_names, k=draw_count)

        self.drawn_names_display.clear()
        self.drawn_names_display.addItems(drawn_names)

        if self.no_replacement_checkbox.isChecked():
            # 更新剩餘名單
            self.remaining_names = [name for name in self.remaining_names if name not in drawn_names]
            self.remaining_names_display.clear()
            self.remaining_names_display.addItems(self.remaining_names)

class NumberPickerTab(QWidget):
    """數字抽籤功能分頁"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        settings_layout = QGridLayout()

        # --- 設定區 ---
        settings_layout.addWidget(QLabel("總人數:"), 0, 0)
        self.total_people_spinbox = QSpinBox()
        self.total_people_spinbox.setRange(1, 999)
        self.total_people_spinbox.setValue(40) # 預設值
        settings_layout.addWidget(self.total_people_spinbox, 0, 1)

        settings_layout.addWidget(QLabel("組數:"), 1, 0)
        self.groups_spinbox = QSpinBox()
        self.groups_spinbox.setRange(1, 999)
        self.groups_spinbox.setValue(1)
        settings_layout.addWidget(self.groups_spinbox, 1, 1)

        settings_layout.addWidget(QLabel("每組人數:"), 2, 0)
        self.per_group_spinbox = QSpinBox()
        self.per_group_spinbox.setRange(1, 999)
        self.per_group_spinbox.setValue(1)
        settings_layout.addWidget(self.per_group_spinbox, 2, 1)

        self.allow_duplicates_checkbox = QCheckBox("可重複抽籤")
        self.allow_duplicates_checkbox.setChecked(False) # 預設不重複
        settings_layout.addWidget(self.allow_duplicates_checkbox, 3, 0, 1, 2) # 跨兩欄

        # --- 抽籤按鈕 ---
        self.draw_button = QPushButton("開始抽籤！")
        button_font = self.draw_button.font()
        button_font.setPointSize(14)
        button_font.setBold(True)
        self.draw_button.setFont(button_font)
        self.draw_button.setMinimumHeight(50)

        # --- 結果顯示區 ---
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setFont(QFont("Consolas", 14)) # 調整結果字體大小
        self.results_display.setPlaceholderText("抽籤結果將顯示於此...")

        # --- 組合版面 ---
        main_layout.addLayout(settings_layout)
        main_layout.addWidget(self.draw_button)
        main_layout.addWidget(QLabel("抽籤結果:"))
        main_layout.addWidget(self.results_display)

        # --- 連接信號 ---
        self.draw_button.clicked.connect(self.perform_draw)

    def perform_draw(self):
        """執行抽籤邏輯"""
        total_people = self.total_people_spinbox.value()
        num_groups = self.groups_spinbox.value()
        num_per_group = self.per_group_spinbox.value()
        allow_duplicates = self.allow_duplicates_checkbox.isChecked()

        num_to_draw = num_groups * num_per_group
        population = list(range(1, total_people + 1))

        # --- 輸入驗證 ---
        if not allow_duplicates and num_to_draw > total_people:
            QMessageBox.warning(self, "設定錯誤", "在不重複抽籤模式下，抽出的總人數不能超過總人數！")
            return

        # --- 抽籤核心邏輯 ---
        if allow_duplicates:
            # 可重複抽籤 (有放回抽樣)
            results = random.choices(population, k=num_to_draw)
        else:
            # 不可重複抽籤 (無放回抽樣)
            results = random.sample(population, k=num_to_draw)

        # --- 格式化並顯示結果 ---
        self.display_results(results, num_groups)

    def display_results(self, results, num_groups):
        """將結果格式化為易於閱讀的文字並顯示"""
        self.results_display.clear()
        if num_groups == 1:
            # 如果只有一組，直接顯示結果
            self.results_display.setText("抽出的號碼：\n" + ", ".join(map(str, sorted(results))))
        else:
            # 如果有多組，分組顯示
            output_text = ""
            for i in range(num_groups):
                start_index = i * len(results) // num_groups
                end_index = (i + 1) * len(results) // num_groups
                group_members = results[start_index:end_index]
                output_text += f"第 {i+1} 組: {', '.join(map(str, sorted(group_members)))}\n"
            self.results_display.setText(output_text)

class RandomPickerWidget(QWidget):
    """一個功能完整的隨機抽籤小工具。"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("抽籤工具")
        # --- 新增：讓視窗保持在最上層 ---
        # 這樣在螢幕畫記模式下，它才能顯示在畫布之上
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(400, 500)

        # 為整個小工具設定一個較大的基礎字型
        # 子元件（如標籤、輸入框）將會繼承這個字型
        base_font = self.font()
        base_font.setPointSize(12) # 調整基礎字體大小
        self.setFont(base_font)

        # 使用 QSettings 來持久化儲存設定
        # 會在使用者目錄下創建一個設定檔
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "MyClassroomTools", "RandomPicker")

        self.init_ui()
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

            QSpinBox, QTextEdit, QListWidget {
                background-color: #5A6B7C; /* Slightly lighter than main background */
                color: white;
                border: 1px solid #7E8A97;
                border-radius: 5px;
                padding: 5px; /* 調整內邊距 */
            }

            QListWidget::item:selected {
                background-color: #697582;
            }
        """)
        self.load_settings()

    def init_ui(self):
        # 使用分頁介面來組織不同類型的抽籤工具
        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        self.number_tab = NumberPickerTab()
        self.name_tab = NamePickerTab()

        tab_widget.addTab(self.number_tab, "數字抽籤")
        tab_widget.addTab(self.name_tab, "姓名抽籤")

        main_layout.addWidget(tab_widget)

    def load_settings(self):
        """從設定檔載入各分頁的設定"""
        # 從設定檔讀取 'total_people'，如果找不到，預設為 40
        total_people = self.settings.value("NumberPicker/total_people", 40, type=int)
        self.number_tab.total_people_spinbox.setValue(total_people)

        # 載入姓名列表
        name_list = self.settings.value("NamePicker/name_list", "", type=str)
        self.name_tab.name_list_input.setPlainText(name_list)

    def save_settings(self):
        """將各分頁的設定儲存到設定檔"""
        total_people = self.number_tab.total_people_spinbox.value()
        self.settings.setValue("NumberPicker/total_people", total_people)

        # 儲存姓名列表
        name_list = self.name_tab.name_list_input.toPlainText()
        self.settings.setValue("NamePicker/name_list", name_list)
        self.settings.sync()

    def closeEvent(self, event):
        """在關閉視窗時自動儲存設定"""
        self.save_settings()
        self.hide()
        event.ignore() # 忽略關閉事件，防止視窗被銷毀