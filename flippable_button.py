from PyQt5.QtWidgets import QPushButton, QWidget
from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QTimer,
                          QEvent, QSize, QParallelAnimationGroup)
from PyQt5.QtGui import QIcon

class FlippableButton(QPushButton):
    """
    一個可以在滑鼠懸停時顯示翻轉動畫，以揭示第二個功能的按鈕。
    """
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setCheckable(True)

        # --- 狀態儲存 ---
        # 使用字典來儲存每個狀態的屬性 (文字、圖示、提示)
        self._prop1 = {}
        self._prop2 = {}

        self._is_flipped = False
        self._animation_running = False
        # 儲存由外部設定的原始圖示大小，以便在動畫中恢復
        self._original_icon_size = self.iconSize()

        # --- 動畫 ---
        # 建立兩個並行動畫組：一個用於縮小 (翻出去)，一個用於放大 (翻進來)
        self._anim_group_flip_out = QParallelAnimationGroup(self)
        self._anim_group_flip_in = QParallelAnimationGroup(self)

        # --- 計時器 ---
        # 用於延遲觸發懸停效果，避免滑鼠快速劃過時產生不必要的動畫
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        # 縮短延遲，讓反應更靈敏
        self._hover_timer.setInterval(100) # 100 毫秒延遲

        # --- 連接信號 ---
        self._anim_group_flip_out.finished.connect(self._on_flip_out_finished)
        self._hover_timer.timeout.connect(self._start_flip_animation)

    def _apply_properties(self, props: dict):
        """將指定的屬性字典應用到按鈕上。"""
        if props.get('icon'):
            self.setIcon(props['icon'])
        # 檢查 'text' 是否存在，因為空字串是有效值
        if props.get('text') is not None:
            self.setText(props['text'])
        if props.get('tooltip'):
            self.setToolTip(props['tooltip'])

    def set_first_state(self, tooltip: str, icon: QIcon = None, text: str = None):
        """設定按鈕的主要狀態。"""
        self._prop1 = {'icon': icon, 'text': text, 'tooltip': tooltip}
        if not self._is_flipped:
            self._apply_properties(self._prop1)

    def set_second_state(self, tooltip: str, icon: QIcon = None, text: str = None):
        """設定按鈕的次要 (翻轉後) 狀態。"""
        self._prop2 = {'icon': icon, 'text': text, 'tooltip': tooltip}
        if self._is_flipped:
            self._apply_properties(self._prop2)

    def setIconSize(self, size: QSize):
        """覆寫 setIconSize 以捕捉原始圖示大小。"""
        super().setIconSize(size)
        # 僅在動畫未執行時更新原始大小，以避免在動畫過程中 (大小為0時) 覆寫它
        if not self._animation_running:
            self._original_icon_size = size

    def sizeHint(self) -> QSize:
        """
        覆寫 sizeHint，為圖示按鈕提供一個固定的尺寸提示。
        這是解決按鈕大小不一問題的關鍵。
        """
        # 如果按鈕沒有文字 (代表它是一個圖示按鈕)，則回傳一個固定的 32x32 尺寸，以匹配其他標準按鈕。
        if not self.text():
            return QSize(32, 32)
        # 對於文字按鈕，使用預設的行為，讓其尺寸根據文字內容決定。
        return super().sizeHint()

    def swap_states(self):
        """交換主要和次要狀態，通常在按鈕被點擊後呼叫。"""
        self._prop1, self._prop2 = self._prop2, self._prop1
        # 立即應用新的主要狀態
        self._apply_properties(self._prop1)
        # 關鍵：點擊後，新的狀態就是主要狀態，所以重設翻轉旗標。
        # 這可以防止滑鼠移開時，leaveEvent 將其翻轉回去。
        self._is_flipped = False

    def enterEvent(self, event: QEvent):
        """當滑鼠進入按鈕區域時觸發。"""
        # 只有在按鈕被選中 (active) 且沒有動畫正在執行時，才啟動懸停計時器
        if self.isChecked() and not self._animation_running:
            self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """當滑鼠離開按鈕區域時觸發。"""
        self._hover_timer.stop() # 取消任何待處理的翻轉動畫
        # 如果按鈕已翻轉，則將其翻轉回來
        if self.isChecked() and self._is_flipped and not self._animation_running:
            self._start_flip_animation()
        super().leaveEvent(event)

    def _start_flip_animation(self):
        """開始執行翻轉動畫。"""
        if not self.isChecked() or self._animation_running:
            return
        self._animation_running = True

        # --- 設定 "翻出去" 動畫組 ---
        self._anim_group_flip_out.clear()

        current_width = self.width()

        # 1a. 最小寬度縮小動畫
        anim_min_width = QPropertyAnimation(self, b"minimumWidth")
        anim_min_width.setDuration(100)
        anim_min_width.setStartValue(current_width)
        anim_min_width.setEndValue(0)
        anim_min_width.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_group_flip_out.addAnimation(anim_min_width)

        # 1b. 最大寬度縮小動畫 (關鍵修正)
        anim_max_width = QPropertyAnimation(self, b"maximumWidth")
        anim_max_width.setDuration(100)
        anim_max_width.setStartValue(current_width)
        anim_max_width.setEndValue(0)
        anim_max_width.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_group_flip_out.addAnimation(anim_max_width)

        # 2. 圖示縮小動畫
        if not self.icon().isNull():
            anim_icon = QPropertyAnimation(self, b"iconSize")
            anim_icon.setDuration(100)
            anim_icon.setStartValue(self.iconSize())
            anim_icon.setEndValue(QSize(0, 0))
            anim_icon.setEasingCurve(QEasingCurve.InOutQuad)
            self._anim_group_flip_out.addAnimation(anim_icon)

        self._anim_group_flip_out.start()

    def _on_flip_out_finished(self):
        """當按鈕 '消失' (寬度為 0) 時呼叫。"""
        # 根據當前是否已翻轉，來決定要顯示哪一個狀態
        if self._is_flipped:
            self._apply_properties(self._prop1) # 翻回主要狀態
        else:
            self._apply_properties(self._prop2) # 翻到次要狀態
        
        self._is_flipped = not self._is_flipped

        # --- 設定 "翻進來" 動畫組 ---
        self._anim_group_flip_in.clear()

        new_width = self.sizeHint().width()

        # 1a. 最小寬度放大動畫
        anim_min_width = QPropertyAnimation(self, b"minimumWidth")
        anim_min_width.setDuration(100)
        anim_min_width.setStartValue(0)
        anim_min_width.setEndValue(new_width)
        anim_min_width.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_group_flip_in.addAnimation(anim_min_width)

        # 1b. 最大寬度放大動畫 (關鍵修正)
        anim_max_width = QPropertyAnimation(self, b"maximumWidth")
        anim_max_width.setDuration(100)
        anim_max_width.setStartValue(0)
        anim_max_width.setEndValue(new_width)
        anim_max_width.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_group_flip_in.addAnimation(anim_max_width)

        # 2. 圖示放大動畫
        if not self.icon().isNull():
            anim_icon = QPropertyAnimation(self, b"iconSize")
            anim_icon.setDuration(100)
            anim_icon.setStartValue(QSize(0, 0))
            anim_icon.setEndValue(self._original_icon_size)
            anim_icon.setEasingCurve(QEasingCurve.InOutQuad)
            self._anim_group_flip_in.addAnimation(anim_icon)

        self._anim_group_flip_in.start()
        # 當 '翻進來' 的動畫結束時，整個翻轉過程才算完成
        self._anim_group_flip_in.finished.connect(self._on_animation_finished)

    def _on_animation_finished(self):
        """重設動畫執行旗標。"""
        self._animation_running = False
        # 解除連接，避免重複觸發
        try:
            self._anim_group_flip_in.finished.disconnect(self._on_animation_finished)
        except TypeError:
            pass # 如果信號已解除，會引發 TypeError，直接忽略即可

    def resizeEvent(self, event):
        """在按鈕大小改變時，更新動畫的目標值。"""
        super().resizeEvent(event)
        # 動畫的起始/結束值現在是動態設定的，此處無需操作。
