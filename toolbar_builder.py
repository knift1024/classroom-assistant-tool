from PyQt5.QtWidgets import (QPushButton, QSlider, QHBoxLayout, QComboBox,
                             QButtonGroup, QWidget, QSizePolicy)
from PyQt5.QtCore import QByteArray, QSize, Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor

from toolbar_icons import (
    HANDWRITING_ICON_SVG, HIGHLIGHTER_ICON_SVG,
    LINE_ICON_SVG, ARROW_ICON_SVG, RECTANGLE_ICON_SVG, CIRCLE_ICON_SVG, 
    TEXT_ICON_SVG, LASER_ICON_SVG, ERASER_ICON_SVG
)
from flippable_button import FlippableButton

class ToolbarUIBuilder:
    """
    一個專門用來建立 MovableToolbar UI 元件的類別。
    這將「外觀」(UI 建立) 與「行為」(邏輯處理) 分離。
    """
    def __init__(self, toolbar: QWidget):
        self.toolbar = toolbar
        # 版面配置直接與傳入的 toolbar 元件關聯
        self.layout = QHBoxLayout(self.toolbar)
        self.layout.setContentsMargins(5, 4, 10, 4)
        self.layout.setSpacing(6)

    def setup_ui(self):
        """建立並排列工具列中的所有元件。"""
        # --- 建立圖示 ---
        self.toolbar.handwriting_icon = self._create_icon_from_svg(HANDWRITING_ICON_SVG)
        self.toolbar.highlighter_icon = self._create_icon_from_svg(HIGHLIGHTER_ICON_SVG)
        self.toolbar.line_icon = self._create_icon_from_svg(LINE_ICON_SVG)
        self.toolbar.arrow_icon = self._create_icon_from_svg(ARROW_ICON_SVG)
        self.toolbar.rect_icon = self._create_icon_from_svg(RECTANGLE_ICON_SVG)
        self.toolbar.circle_icon = self._create_icon_from_svg(CIRCLE_ICON_SVG)
        self.toolbar.text_icon = self._create_icon_from_svg(TEXT_ICON_SVG)
        self.toolbar.laser_icon = self._create_icon_from_svg(LASER_ICON_SVG)
        self.toolbar.eraser_icon = self._create_icon_from_svg(ERASER_ICON_SVG)

        # --- 工具列字體 ---
        toolbar_font = QFont("Arial", 10)

        # --- 繪圖工具按鈕 ---
        self.toolbar.tool_button_group = QButtonGroup(self.toolbar)
        self.toolbar.tool_button_group.setExclusive(True)

        # --- 使用 FlippableButton 建立雙功能按鈕 ---
        wrapper = self._create_flippable_button(
            first_state={'icon': self.toolbar.handwriting_icon, 'tooltip': "手繪模式 (1)"},
            second_state={'icon': self.toolbar.highlighter_icon, 'tooltip': "螢光筆模式 (1)"}
        )
        self.toolbar.freehand_highlighter_button = wrapper.button
        self.toolbar.freehand_highlighter_button.setChecked(True)
        self.layout.addWidget(wrapper)
        self.toolbar.tool_button_group.addButton(self.toolbar.freehand_highlighter_button, 1)

        wrapper = self._create_flippable_button(
            first_state={'icon': self.toolbar.line_icon, 'tooltip': "直線 (2)"},
            second_state={'icon': self.toolbar.arrow_icon, 'tooltip': "箭頭 (2)"}
        )
        self.toolbar.line_arrow_button = wrapper.button
        self.layout.addWidget(wrapper)
        self.toolbar.tool_button_group.addButton(self.toolbar.line_arrow_button, 2)

        wrapper = self._create_flippable_button(
            first_state={'icon': self.toolbar.rect_icon, 'tooltip': "矩形 (3)"},
            second_state={'icon': self.toolbar.circle_icon, 'tooltip': "圓形 (3)"}
        )
        self.toolbar.rect_circle_button = wrapper.button
        self.layout.addWidget(wrapper)
        self.toolbar.tool_button_group.addButton(self.toolbar.rect_circle_button, 3)

        # --- 單功能按鈕 ---
        self.toolbar.text_button = self._create_icon_button(self.toolbar.text_icon, "文字 (4)")
        self.layout.addWidget(self.toolbar.text_button)
        self.toolbar.tool_button_group.addButton(self.toolbar.text_button, 4)

        laser_button = self._create_icon_button(self.toolbar.laser_icon, "雷射筆 (5)")
        self.layout.addWidget(laser_button)
        self.toolbar.tool_button_group.addButton(laser_button, 5)

        eraser_button = self._create_icon_button(self.toolbar.eraser_icon, "橡皮擦 (6)")
        self.layout.addWidget(eraser_button)
        self.toolbar.tool_button_group.addButton(eraser_button, 6)

        # --- 畫布與樣式 ---
        self.toolbar.canvas_combo = self._create_combobox(["桌面", "黑板", "白板", "純色", "半透明", "讀取檔案"], toolbar_font)
        self.toolbar.canvas_combo.setToolTip("選擇畫布背景")
        self.layout.addWidget(self.toolbar.canvas_combo)

        self.toolbar.pattern_combo = self._create_combobox(["無", "細方格", "粗方格"], toolbar_font)
        self.toolbar.pattern_combo.setToolTip("選擇畫布格線樣式")
        self.layout.addWidget(self.toolbar.pattern_combo)

        # --- 新的顏色選擇區 (最近使用 + 主顏色) ---
        self.toolbar.color_button_group = QButtonGroup(self.toolbar)
        self.toolbar.color_button_group.setExclusive(True)

        # 建立兩個最近使用顏色按鈕 (較小)
        # 預設顏色稍後會由 toolbar 邏輯更新

        self.toolbar.recent_color_2 = self._create_color_button(QColor("#000000"), "最近使用顏色 2", size=20)
        self.layout.addWidget(self.toolbar.recent_color_2)
        self.toolbar.color_button_group.addButton(self.toolbar.recent_color_2)

        self.toolbar.recent_color_1 = self._create_color_button(QColor("#FFFFFF"), "最近使用顏色 1", size=20)
        self.layout.addWidget(self.toolbar.recent_color_1)
        self.toolbar.color_button_group.addButton(self.toolbar.recent_color_1)

        # 建立主顏色按鈕 (較大)，點擊它會彈出調色盤
        # 它的背景顏色會反映當前選擇的顏色
        self.toolbar.main_color_button = self._create_color_button(QColor("#FF0000"), "開啟調色盤", size=28, checkable=False)
        self.toolbar.main_color_button.setText("▼")
        self.layout.addWidget(self.toolbar.main_color_button)

        self.toolbar.width_slider = QSlider(Qt.Horizontal)
        self.toolbar.width_slider.setToolTip("調整畫筆或橡皮擦的粗細")
        self.toolbar.width_slider.setRange(1, 50) # 增加最大寬度
        self.toolbar.width_slider.setMinimumWidth(70) # 限制最小寬度
        self.layout.addWidget(self.toolbar.width_slider)

        # --- 功能按鈕 ---
        self.toolbar.smooth_button = self._create_functional_button("平滑化", toolbar_font, checkable=True, tooltip="啟用後，手繪筆觸會更圓滑")
        self.layout.addWidget(self.toolbar.smooth_button)

        self.toolbar.undo_button = self._create_functional_button("復原", toolbar_font, tooltip="復原 (←)")
        self.layout.addWidget(self.toolbar.undo_button)

        self.toolbar.redo_button = self._create_functional_button("重做", toolbar_font, tooltip="重做 (→)")
        self.layout.addWidget(self.toolbar.redo_button)

        self.toolbar.clear_button = self._create_functional_button("清除", toolbar_font, tooltip="清除所有畫記 (Del)")
        self.layout.addWidget(self.toolbar.clear_button)

        self.toolbar.save_button = self._create_functional_button("儲存", toolbar_font, tooltip="儲存畫記")
        self.layout.addWidget(self.toolbar.save_button)

        self.toolbar.exit_button = self._create_functional_button("退出", toolbar_font, tooltip="退出畫記模式 (Esc)")
        self.layout.addWidget(self.toolbar.exit_button)

        # 新增：在所有元件的末端加入一個彈性空間
        # 這會將所有元件推向左側，並讓工具列的寬度自動縮減到其內容所需的最小值
        self.layout.addStretch()

    # --- UI Helper Methods (moved from MovableToolbar) ---
    def _create_icon_from_svg(self, svg_data: str) -> QIcon:
        """從 SVG 字串建立一個 QIcon。"""
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg_data.encode('utf-8')))
        return QIcon(pixmap)

    def _create_icon_button(self, icon, tooltip):
        """建立一個標準的圖示工具按鈕。"""
        button = QPushButton()
        button.setIcon(icon)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setFixedSize(32, 32)
        button.setIconSize(QSize(20, 20))
        button.setStyleSheet("QPushButton { padding: 0px; }")
        return button

    def _create_flippable_button(self, first_state: dict, second_state: dict, font: QFont = None) -> QWidget:
        """
        建立一個包含可翻轉按鈕的包裝盒 (Wrapper)。
        這個包裝盒有固定的尺寸，可以防止動畫影響整體佈局。
        """
        # 1. 建立按鈕並設定其兩種狀態
        button = FlippableButton()
        button.set_first_state(**first_state)
        button.set_second_state(**second_state)

        if font:
            button.setFont(font)
        else: # 圖示按鈕
            button.setIconSize(QSize(20, 20))
            button.setStyleSheet("QPushButton { padding: 0px; }")
            # 移除 setMinimumSize，讓按鈕尺寸完全由 sizeHint 決定

        # 2. 根據按鈕類型決定包裝盒的尺寸
        if font:
            # 對於文字按鈕，根據內容計算所需的最大尺寸
            original_text = button.text()
            button.setText(first_state.get('text') or '')
            size1 = button.sizeHint()
            button.setText(second_state.get('text') or '')
            size2 = button.sizeHint()
            button.setText(original_text)
            max_width = max(size1.width(), size2.width())
            max_height = max(size1.height(), size2.height())
        else:
            # 對於圖示按鈕，使用與其他標準圖示按鈕相同的固定尺寸
            max_width = 32
            max_height = 32

        # 3. 建立固定尺寸的包裝盒，並將按鈕放入其中
        wrapper = QWidget()
        wrapper.setFixedSize(max_width, max_height)
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(button)

        # 4. 將實際的按鈕附加到包裝盒上，以便外部可以存取
        wrapper.button = button

        return wrapper

    def _create_combobox(self, items, font):
        combo = QComboBox()
        combo.setFont(font)
        combo.addItems(items)
        return combo

    def _create_color_button(self, color, tooltip, size=24, checkable=True):
        button = QPushButton()
        button.setFixedSize(size, size)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)

        # 根據背景亮度決定文字顏色，以確保可見性
        luminance = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        text_color = "black" if luminance > 128 else "white"

        if checkable:
            button.setStyleSheet(f"""
                QPushButton {{ background-color: {color.name()}; border: 2px solid transparent; border-radius: 4px; }}
                QPushButton:checked {{ border: 2px solid #87CEFA; }}
            """)
        else:
            # 非 checkable 按鈕的樣式 (例如主顏色觸發按鈕)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {text_color};
                    font-weight: bold;
                    border: 1px solid #5A6B7C;
                    border-radius: 4px;
                }}
                QPushButton:hover {{ border-color: #98A3AF; }}
                QPushButton:pressed {{ background-color: {color.darker(120).name()}; }}
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
