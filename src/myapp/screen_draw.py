import sys
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QPushButton, QColorDialog, QSlider, QHBoxLayout, QFileDialog, QComboBox, QMessageBox, QButtonGroup, QStyle, QCheckBox, QAction)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent, QRect, QSettings, QTimer, QSize, QByteArray
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QCursor, QFont, QIcon, QPainterPath

from toolbar import MovableToolbar

class ScreenDrawWindow(QWidget):
    """
    螢幕畫記視窗：一個全螢幕、透明、置頂的畫布，用於在螢幕上進行畫記。
    """
    drawing_mode_ended = pyqtSignal()
    canvas_activated = pyqtSignal() # 新增：當畫布被點擊時發射的信號

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
        self.image = QPixmap(screen_rect.size())
        self.image.fill(Qt.transparent)

        # 背景層：用於儲存桌面截圖
        self.background_pixmap = None

        # --- 狀態與繪圖工具 ---
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.red)
        self.pen_width = 5
        self.eraser_width = 15 # 橡皮擦的獨立寬度
        self.draw_mode = 'freehand'  # 'freehand', 'highlighter', 'line', 'arrow', 'rectangle', 'circle', 'laser_pointer', 'eraser', 'crop'
        
        # 雷射筆殘影相關屬性
        self.laser_trail_segments = []
        self.laser_fade_timer = QTimer(self)
        self.fade_step = 15
        
        # 復原/重做 功能的歷史紀錄堆疊
        self.history_stack = []
        self.redo_stack = []
        self.history_limit = 20

        # 筆觸平滑化相關屬性
        self.smoothing_enabled = True
        self.point_buffer = []

        self.start_point = None
        self.current_point = None
        
        # 畫布與樣式狀態
        self.canvas_mode = 'desktop'
        self.canvas_color = QColor("#2E4636")
        self.pattern_mode = 'none'

        # 新增：用於判斷是否為首次啟動的旗標
        self._first_time_setup = True

        self.image_painter = None # 用於優化繪圖，避免在高頻事件中重複創建 QPainter

        # --- 游標與滑鼠追蹤 ---
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        # --- 浮動工具列 ---
        self.toolbar = MovableToolbar(self)
        self._connect_toolbar_signals()

        self.laser_fade_timer.timeout.connect(self._fade_laser_trail)
        self.load_settings()
        self._update_undo_redo_buttons()
        self.toolbar.hide()

    def _connect_toolbar_signals(self):
        """將工具列的信號連接到此視窗的槽。"""
        self.toolbar.color_changed.connect(self._handle_color_change)
        self.toolbar.tool_changed.connect(self._handle_tool_change)
        self.toolbar.color_requested.connect(self.choose_color)
        self.toolbar.width_changed.connect(self._handle_width_change)
        self.toolbar.smoothing_toggled.connect(self._handle_smoothing_toggle)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)
        self.toolbar.clear_requested.connect(self.clear_screen)
        self.toolbar.save_requested.connect(self.handle_save_action)
        self.toolbar.exit_requested.connect(self.end_drawing_mode)
        self.toolbar.canvas_changed.connect(self._handle_canvas_change)
        self.toolbar.pattern_changed.connect(self._handle_pattern_change)
        # 新增：當工具列本身被點擊時，也觸發 canvas_activated 信號。
        # 這可以確保主工具列在點擊畫記工具列後，能被提升到最上層，解決其消失的問題。
        self.toolbar.toolbar_activated.connect(self.canvas_activated.emit)


    def _handle_smoothing_toggle(self, checked):
        """切換筆觸平滑化功能的開關。"""
        self.smoothing_enabled = checked

    def _handle_tool_change(self, tool_name):
        """根據從工具列傳來的工具名稱，更新目前的繪圖模式。"""
        self.draw_mode = tool_name

        self._update_cursor() # 新增：根據新工具更新游標
        if self.draw_mode == 'laser_pointer':
            self.laser_trail_segments.clear()
            self.laser_fade_timer.start(30)
        elif self.laser_fade_timer.isActive():
            self.laser_trail_segments.clear()
            self.laser_fade_timer.stop()
        
        # 更新滑桿的值以匹配當前工具的寬度
        if self.draw_mode == 'eraser':
            self.toolbar.set_width_value(self.eraser_width)
        else:
            self.toolbar.set_width_value(self.pen_width)

    def _handle_color_change(self, color):
        """處理從工具列傳來的顏色變更。"""
        self.pen_color = color
        if self.draw_mode == 'eraser':
            # 當在橡皮擦模式下選擇顏色時，自動切換回之前的繪圖模式
            # 工具列(toolbar)記錄了之前的工具名稱
            previous_tool = self.toolbar.previous_tool_name
            self.draw_mode = previous_tool
            self.toolbar.set_tool_checked(previous_tool)
            self._update_cursor()
            self.toolbar.set_width_value(self.pen_width) # 切換回繪圖工具，更新滑桿為畫筆寬度
 
    def _handle_canvas_change(self, canvas_type):
        """處理畫布下拉選單的變更。"""
        previous_mode = self.canvas_mode
        if canvas_type == "桌面":
            self.canvas_mode = 'desktop'
        elif canvas_type == "黑板":
            self.canvas_mode = 'blackboard'
            self.canvas_color = QColor("#2E4636")
        elif canvas_type == "白板":
            self.canvas_mode = 'whiteboard'
            self.canvas_color = QColor(Qt.white)
        elif canvas_type == "純色":
            color = QColorDialog.getColor(self.canvas_color, self, "選擇畫布顏色")
            if color.isValid():
                self.canvas_mode = 'solid'
                self.canvas_color = color
            else:
                # 如果使用者取消，恢復下拉選單到之前的選項
                self.toolbar.canvas_combo.blockSignals(True)
                previous_index = self.toolbar.canvas_combo.findText(self.get_mode_text(previous_mode))
                self.toolbar.canvas_combo.setCurrentIndex(previous_index)
                self.toolbar.canvas_combo.blockSignals(False)
        
        self.update()

    def get_mode_text(self, mode):
        """根據模式名稱返回對應的下拉選單文字。"""
        if mode == 'desktop': return '桌面'
        if mode == 'blackboard': return '黑板'
        if mode == 'whiteboard': return '白板'
        if mode == 'solid': return '純色'
        return '桌面'  # 預設值

    def _handle_pattern_change(self, pattern_type):
        """處理樣式下拉選單的變更。"""
        if pattern_type == "無":
            self.pattern_mode = 'none'
        elif pattern_type == "細方格":
            self.pattern_mode = 'fine_grid'
        elif pattern_type == "粗方格":
            self.pattern_mode = 'coarse_grid'
        self.update()
    def draw_pattern(self, painter):
        """根據目前的樣式模式繪製格線。"""
        if self.pattern_mode == 'none': return

        grid_size = 25 if self.pattern_mode == 'fine_grid' else 75
        pen = QPen(QColor(128, 128, 128, 100), 1, Qt.SolidLine)
        painter.setPen(pen)
        for x in range(0, self.width(), grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_size):
            painter.drawLine(0, y, self.width(), y)

    def draw_arrow(self, painter, start_point, end_point):
        """繪製一個帶有箭頭的線條。"""
        line = end_point - start_point
        if line.isNull(): return
        angle = math.atan2(-line.y(), line.x())
        arrow_size = self.pen_width * 3 + 10

        painter.drawLine(start_point, end_point)

        arrow_p1 = end_point - QPoint(int(math.cos(angle + math.pi / 6) * arrow_size), int(-math.sin(angle + math.pi / 6) * arrow_size))
        arrow_p2 = end_point - QPoint(int(math.cos(angle - math.pi / 6) * arrow_size), int(-math.sin(angle - math.pi / 6) * arrow_size))
        painter.drawLine(end_point, arrow_p1)
        painter.drawLine(end_point, arrow_p2)

    def _get_constrained_point(self, start_point: QPoint, current_point: QPoint) -> QPoint:
        """根據起始點和當前點，計算一個受約束的終點，以形成正方形的邊界框。"""
        dx = current_point.x() - start_point.x()
        dy = current_point.y() - start_point.y()
        side = max(abs(dx), abs(dy))
        constrained_x = start_point.x() + (side if dx > 0 else -side)
        constrained_y = start_point.y() + (side if dy > 0 else -side)
        return QPoint(constrained_x, constrained_y)

    def _fade_laser_trail(self):
        """定時器觸發，減少雷射筆殘影的透明度並移除完全透明的線段。"""
        if not self.laser_trail_segments:
            return

        new_segments = []
        for start_p, end_p, opacity in self.laser_trail_segments:
            new_opacity = opacity - self.fade_step
            if new_opacity > 0:
                new_segments.append((start_p, end_p, new_opacity))
        self.laser_trail_segments = new_segments
        self.update()

    def _create_eraser_cursor(self):
        """建立一個代表橡皮擦範圍的自訂游標。"""
        diameter = self.eraser_width * 2
        # 建立一個足夠大的透明畫布來容納圓圈和邊框
        pixmap = QPixmap(QSize(diameter + 2, diameter + 2))
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        # 使用灰色虛線來繪製圓圈
        pen = QPen(QColor(128, 128, 128), 1, Qt.DashLine)
        painter.setPen(pen)
        # 在畫布中心繪製圓圈
        painter.drawEllipse(1, 1, diameter, diameter)
        painter.end()

        return QCursor(pixmap)

    def _update_cursor(self):
        """根據目前的繪圖模式更新滑鼠游標。"""
        self.setCursor(self._create_eraser_cursor() if self.draw_mode == 'eraser' else Qt.CrossCursor)

    def save_settings(self):
        """將畫筆與工具列設定儲存到設定檔。"""
        self.settings.setValue("pen_color", self.pen_color)
        self.settings.setValue("pen_width", self.pen_width)
        self.settings.setValue("eraser_width", self.eraser_width)
        self.settings.setValue("pen_custom_color", self.toolbar.custom_color)
        if self.toolbar:
            self.settings.setValue("toolbar_geometry", self.toolbar.geometry())
            self.settings.setValue("smoothing_enabled", self.toolbar.smooth_button.isChecked())
        self.settings.sync()

    def load_settings(self):
        """從設定檔載入畫筆設定並初始化工具列。"""
        color = self.settings.value("pen_color", QColor(Qt.red))
        self.pen_color = color if isinstance(color, QColor) and color.isValid() else QColor(Qt.red)
        self.pen_width = self.settings.value("pen_width", 5, type=int)
        self.eraser_width = self.settings.value("eraser_width", 15, type=int)
        
        if self.toolbar:
            self.toolbar.set_initial_state(self.settings, self)
            # 新增：在載入設定後，明確地告訴工具列要高亮哪個顏色按鈕
            # 根據預設工具（手繪）設定初始滑桿值
            self.toolbar.set_width_value(self.pen_width)
            self.toolbar.set_color_checked(self.pen_color)

    def _save_history(self):
        """將當前的畫布狀態儲存到歷史紀錄堆疊中。"""
        self.redo_stack.clear()
        if len(self.history_stack) >= self.history_limit:
            del self.history_stack[0]
        self.history_stack.append(self.image.copy())
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        """根據歷史紀錄堆疊的狀態，更新復原/重做按鈕的可用性。"""
        if self.toolbar:
            self.toolbar.set_undo_enabled(len(self.history_stack) > 1)
            self.toolbar.set_redo_enabled(bool(self.redo_stack))

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
            # 每次啟用時都重新擷取桌面背景，以確保背景是最新的
            screen = QApplication.primaryScreen()
            self.background_pixmap = screen.grabWindow(0)

            # 只有在第一次啟動時才執行設定
            if self._first_time_setup:
                self.image.fill(Qt.transparent)
                self.history_stack = [self.image.copy()]
                self.redo_stack = []
                self._update_undo_redo_buttons()
                self._first_time_setup = False

            self.toolbar.show()
            self.showFullScreen()
            self.raise_()
            self.activateWindow()
            self.setFocus()
        else:
            self.toolbar.hide()
            self.hide()

    def choose_color(self):
        color = QColorDialog.getColor(self.pen_color, self, "選擇畫筆顏色")
        if color.isValid():
            self.toolbar.update_custom_color(color)
            self.toolbar.custom_color_button.setChecked(True)

    def _handle_width_change(self, width):
        if self.draw_mode == 'eraser':
            self.eraser_width = width
        else:
            self.pen_width = width
        self._update_cursor()

    def clear_screen(self):
        self.image.fill(Qt.transparent)
        self._save_history()
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

    def _create_combined_pixmap(self):
        """創建一個合併了背景、樣式和筆跡的 QPixmap。"""
        combined_pixmap = QPixmap(self.size())
        painter = QPainter(combined_pixmap)

        if self.canvas_mode == 'desktop' and self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode == 'blackboard':
            painter.fillRect(self.rect(), QColor("#2E4636"))
        elif self.canvas_mode == 'whiteboard':
            painter.fillRect(self.rect(), Qt.white)
        elif self.canvas_mode == 'solid':
            painter.fillRect(self.rect(), self.canvas_color)

        self.draw_pattern(painter)
        painter.drawPixmap(self.rect(), self.image)
        painter.end()
        return combined_pixmap

    def save_cropped_area(self, crop_rect):
        """將指定的圈選範圍儲存為圖片檔案。"""
        combined_pixmap = self._create_combined_pixmap()
        cropped_pixmap = combined_pixmap.copy(crop_rect)
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存圈選範圍", "", "PNG 圖片 (*.png);;JPEG 圖片 (*.jpg *.jpeg);;所有檔案 (*)")
        if file_path:
            cropped_pixmap.save(file_path)

    def save_drawing(self):
        """將當前畫布內容儲存為圖片檔案。"""
        combined_pixmap = self._create_combined_pixmap()
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存畫記", "", "PNG 圖片 (*.png);;JPEG 圖片 (*.jpg *.jpeg);;所有檔案 (*)")
        if file_path:
            combined_pixmap.save(file_path)

    def end_drawing_mode(self):
        self.save_settings()
        self.toggle_drawing_mode(False)
        self.drawing_mode_ended.emit()

    def mousePressEvent(self, event):
        # 關鍵修改：在處理任何點擊事件之前，先發射信號
        # 通知主工具列將所有工具視窗提升到最上層
        self.canvas_activated.emit()

        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

            if self.draw_mode in ['line', 'arrow', 'rectangle', 'circle', 'crop']:
                self.start_point = event.pos()
                self.current_point = event.pos()
            elif self.draw_mode in ['freehand', 'highlighter', 'eraser']:
                if self.smoothing_enabled:
                    self.point_buffer = [event.pos()]
                
                self.image_painter = QPainter(self.image)
                if self.smoothing_enabled:
                    self.image_painter.setRenderHint(QPainter.Antialiasing)

                if self.draw_mode == 'eraser':
                    self.image_painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    self.image_painter.setPen(QPen(Qt.transparent, self.eraser_width * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                elif self.draw_mode == 'highlighter':
                    self.image_painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    color = QColor(self.pen_color)
                    color.setAlpha(100) # 設定半透明效果
                    self.image_painter.setPen(QPen(color, self.pen_width, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin)) # 平頭筆刷
                else:
                    self.image_painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    self.image_painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                self.image_painter.drawPoint(self.last_point)
                # 注意：此處不呼叫 .end()，以保留 painter 供 mouseMoveEvent 使用
                self.update()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            if self.draw_mode == 'laser_pointer':
                self.laser_trail_segments.append((self.last_point, event.pos(), 255))
                self.last_point = event.pos()
            elif self.draw_mode in ['line', 'arrow', 'rectangle', 'circle', 'crop']:
                if event.modifiers() & Qt.ShiftModifier and self.draw_mode in ['rectangle', 'circle']:
                    self.current_point = self._get_constrained_point(self.start_point, event.pos())
                else:
                    self.current_point = event.pos()
            elif self.draw_mode in ['freehand', 'highlighter', 'eraser']:
                if not self.image_painter: # 安全性檢查，如果 painter 不存在則不繪圖
                    return

                if self.smoothing_enabled:
                    self.point_buffer.append(event.pos())
                    if len(self.point_buffer) >= 3:
                        p1 = self.point_buffer[-3]
                        p2 = self.point_buffer[-2]
                        p3 = self.point_buffer[-1]
                        mid1 = QPoint((p1.x() + p2.x()) // 2, (p1.y() + p2.y()) // 2)
                        mid2 = QPoint((p2.x() + p3.x()) // 2, (p2.y() + p3.y()) // 2)

                        # 直接使用在 mousePressEvent 中創建的 painter
                        path = QPainterPath()
                        path.moveTo(mid1)
                        path.quadTo(p2, mid2)
                        self.image_painter.drawPath(path)
                else:
                    # 直接使用在 mousePressEvent 中創建的 painter
                    self.image_painter.drawLine(self.last_point, event.pos())
                    self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            save_needed = False

            # 在處理釋放事件的邏輯之前，先結束並清理手繪模式的 painter
            if self.image_painter:
                self.image_painter.end()
                self.image_painter = None

            if self.draw_mode in ['line', 'arrow', 'rectangle', 'circle']:
                final_point = event.pos()
                if event.modifiers() & Qt.ShiftModifier and self.draw_mode in ['rectangle', 'circle']:
                    final_point = self._get_constrained_point(self.start_point, event.pos())

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
                if self.start_point and self.current_point and self.start_point != event.pos():
                    crop_rect = QRect(self.start_point, event.pos()).normalized()
                    self.save_cropped_area(crop_rect)
                
                self.toolbar.set_tool_checked('freehand')
                self.start_point = None
                self.current_point = None
                save_needed = False
            elif self.draw_mode in ['freehand', 'highlighter', 'eraser']:
                if self.smoothing_enabled:
                    # 處理筆劃結束時剩餘的點 (例如非常短的筆劃，只有2個點)
                    if len(self.point_buffer) == 2:
                        # 由於 self.image_painter 已經結束，這裡需要一個臨時的 painter
                        painter = QPainter(self.image)
                        if self.draw_mode == 'eraser':
                            painter.setCompositionMode(QPainter.CompositionMode_Clear)
                            painter.setPen(QPen(Qt.transparent, self.eraser_width * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        elif self.draw_mode == 'highlighter':
                            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                            color = QColor(self.pen_color)
                            color.setAlpha(100)
                            painter.setPen(QPen(color, self.pen_width, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin))
                        else: # freehand
                            painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        painter.drawLine(self.point_buffer[0], self.point_buffer[1])
                        painter.end()
                    self.point_buffer.clear()
                save_needed = True

            if save_needed:
                self._save_history()

            self.update()

    def paintEvent(self, event):
        if self.width() <= 0 or self.height() <= 0:
            return

        painter = QPainter(self)

        # 1. 繪製背景層
        if self.canvas_mode == 'desktop':
            if self.background_pixmap and not self.background_pixmap.isNull():
                painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode == 'blackboard':
            painter.fillRect(self.rect(), QColor("#2E4636"))
        elif self.canvas_mode == 'whiteboard':
            painter.fillRect(self.rect(), Qt.white)
        elif self.canvas_mode == 'solid':
            painter.fillRect(self.rect(), self.canvas_color)

        # 2. 繪製樣式層
        self.draw_pattern(painter)

        # 3. 繪製筆跡層
        if self.image and not self.image.isNull():
            painter.drawPixmap(self.rect(), self.image)

        # 4. 繪製即時預覽圖形
        if self.drawing and self.start_point and self.current_point:
            if self.draw_mode == 'crop':
                preview_pen = QPen(QColor(0, 120, 255), 2, Qt.DashLine)
            else:
                preview_pen = QPen(self.pen_color, self.pen_width, Qt.DashLine)
            
            painter.setPen(preview_pen)
            
            if self.draw_mode == 'line':
                painter.drawLine(self.start_point, self.current_point)
            elif self.draw_mode == 'arrow':
                self.draw_arrow(painter, self.start_point, self.current_point)
            elif self.draw_mode in ['rectangle', 'crop']:
                painter.drawRect(QRect(self.start_point, self.current_point))
            elif self.draw_mode == 'circle':
                painter.drawEllipse(QRect(self.start_point, self.current_point))
        
        # 5. 繪製雷射筆殘影
        if self.laser_trail_segments:
            painter.setRenderHint(QPainter.Antialiasing)
            num_segments = len(self.laser_trail_segments)
            max_width = self.pen_width
            taper_length = min(15, num_segments // 2)

            for i, (start_p, end_p, opacity) in enumerate(self.laser_trail_segments):
                if taper_length > 0:
                    if i < taper_length:
                        current_width = max(1, max_width * ((i + 1) / taper_length))
                    elif i >= num_segments - taper_length:
                        current_width = max(1, max_width * ((num_segments - i) / taper_length))
                    else:
                        current_width = max_width
                else:
                    current_width = max_width
                
                laser_pen = QPen(self.pen_color)
                laser_pen.setWidth(int(current_width))
                laser_pen.setCapStyle(Qt.RoundCap)
                laser_pen.setJoinStyle(Qt.RoundJoin)

                current_color = laser_pen.color()
                laser_pen.setColor(QColor(current_color.red(),
                                          current_color.green(),
                                          current_color.blue(),
                                          opacity))
                painter.setPen(laser_pen)
                painter.drawLine(start_p, end_p)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.end_drawing_mode()

    def resizeEvent(self, event):
        new_size = self.size()
        if self.image.isNull() or self.image.size() != new_size:
            if not new_size.isValid() or new_size.width() <= 0 or new_size.height() <= 0:
                return

            old_image = self.image            
            new_image = QPixmap(new_size)
            new_image.fill(Qt.transparent)

            if not old_image.isNull():
                p = QPainter(new_image)
                p.drawPixmap(QPoint(0, 0), old_image)
                p.end()

            self.image = new_image

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScreenDrawWindow()
    window.toggle_drawing_mode(True)
    sys.exit(app.exec_())
