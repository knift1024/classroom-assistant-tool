import sys
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit,
                             QPushButton, QColorDialog, QSlider, QHBoxLayout, QFileDialog, QComboBox, QMessageBox, QButtonGroup, QStyle, QCheckBox, QAction, QShortcut)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent, QRect, QSettings, QTimer, QSize, QByteArray
import sys
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit,
                             QPushButton, QColorDialog, QSlider, QHBoxLayout, QFileDialog, QComboBox, QMessageBox, QButtonGroup, QStyle, QCheckBox, QAction, QShortcut)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent, QRect, QSettings, QTimer, QSize, QByteArray
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QCursor, QFont, QIcon, QPainterPath, QFontMetrics, QMouseEvent, QWheelEvent, QKeySequence

from toolbar import MovableToolbar

class MovableLineEdit(QLineEdit):
    """一個可以透過滑鼠拖曳移動的 QLineEdit。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dragging = False
        self._offset = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._offset = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging:
            new_pos = self.mapToParent(event.pos() - self._offset)
            self.move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
        super().mouseReleaseEvent(event)

class ScreenDrawWindow(QWidget):
    drawing_mode_ended = pyqtSignal()
    canvas_activated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("螢幕畫記")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(Qt.StrongFocus)

        screen_rect = QApplication.desktop().screenGeometry()
        self.setGeometry(screen_rect)

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "MyClassroomTools", "ScreenDraw")

        self.image = QPixmap(screen_rect.size())
        self.image.fill(Qt.transparent)

        self.background_pixmap = None
        self.loaded_background_image = None

        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor("#FF0000")
        self.pen_opacity = 255
        self.pen_width = 5
        self.eraser_width = 20

        self.current_tool = 'freehand'
        self.start_point = None
        self.current_point = None
        self.cursor_pos = QPoint()
        self.highlighter_temp_image = None

        self.laser_trail_segments = []
        self.laser_fade_timer = QTimer(self)
        self.fade_step = 15

        # History is now initialized once, here.
        self.history_stack = [self.image.copy()]
        self.redo_stack = []
        self.history_limit = 20

        self.smoothing_enabled = True
        self.point_buffer = []

        self.text_input = None
        self.font = QFont("Arial", 36)

        self.canvas_mode = 'desktop'
        self.canvas_color = QColor("#2E4636")
        self.pattern_mode = 'none'

        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        self.toolbar = MovableToolbar(self)
        self._connect_toolbar_signals()
        self.toolbar.hide()

        self.laser_fade_timer.timeout.connect(self._fade_laser_trail)
        self._setup_shortcuts()
        self.load_settings()
        if self.canvas_mode == 'transparent':
            self.setAttribute(Qt.WA_TranslucentBackground, True)
        else:
            self.setAttribute(Qt.WA_TranslucentBackground, False)

    def _grab_desktop_and_show(self):
        """A helper function to grab the desktop screenshot after a short delay."""
        screen = QApplication.primaryScreen()
        self.background_pixmap = screen.grabWindow(0)
        self.loaded_background_image = None
        self.canvas_mode = 'desktop'

        # If the canvas was transparent, we need to make it opaque again for desktop mode.
        if self.testAttribute(Qt.WA_TranslucentBackground):
            self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        self.showFullScreen()
        self.update()

    def _connect_toolbar_signals(self):
        self.toolbar.tool_changed.connect(self.handle_tool_change)
        self.toolbar.color_changed.connect(self.handle_color_change)
        self.toolbar.width_changed.connect(self.handle_width_change)
        self.toolbar.smoothing_toggled.connect(self.toggle_smoothing)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)
        self.toolbar.clear_requested.connect(self.clear_screen)
        self.toolbar.save_requested.connect(self.handle_save_action)
        self.toolbar.exit_requested.connect(self.end_drawing_mode)
        self.toolbar.canvas_changed.connect(self.handle_canvas_change)
        self.toolbar.pattern_changed.connect(self.handle_pattern_change)
        self.toolbar.font_changed.connect(self.handle_font_change)
        self.toolbar.font_size_changed.connect(self.handle_font_size_change)
        self.toolbar.opacity_changed.connect(self.handle_opacity_change)
        self.toolbar.toolbar_activated.connect(self.canvas_activated.emit)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("1"), self).activated.connect(self.toolbar.freehand_highlighter_button.click)
        QShortcut(QKeySequence("2"), self).activated.connect(self.toolbar.line_arrow_button.click)
        QShortcut(QKeySequence("3"), self).activated.connect(self.toolbar.rect_circle_button.click)
        QShortcut(QKeySequence("4"), self).activated.connect(self.toolbar.text_button.click)
        QShortcut(QKeySequence("5"), self).activated.connect(self.toolbar.tool_button_group.button(5).click)
        QShortcut(QKeySequence("6"), self).activated.connect(self.toolbar.tool_button_group.button(6).click)
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.toolbar.undo_button.click)
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.toolbar.redo_button.click)
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self.toolbar.clear_button.click)

    def _fade_laser_trail(self):
        if not self.laser_trail_segments:
            return
        new_segments = []
        for start_p, end_p, opacity in self.laser_trail_segments:
            new_opacity = opacity - self.fade_step
            if new_opacity > 0:
                new_segments.append((start_p, end_p, new_opacity))
        self.laser_trail_segments = new_segments
        self.update()

    def handle_tool_change(self, tool_name: str):
        self.current_tool = tool_name
        if self.current_tool == 'eraser':
            self.toolbar.set_width_value(self.eraser_width)
        else:
            self.toolbar.set_width_value(self.pen_width)
        if self.current_tool == 'text':
            self.setCursor(Qt.IBeamCursor)
        elif self.current_tool == 'eraser':
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(Qt.CrossCursor)
        if self.current_tool != 'laser_pointer' and self.laser_fade_timer.isActive():
            self.laser_trail_segments.clear()
            self.laser_fade_timer.stop()
            self.update()
        elif self.current_tool == 'laser_pointer' and not self.laser_fade_timer.isActive():
            self.laser_trail_segments.clear()
            self.laser_fade_timer.start(30)

    def handle_color_change(self, color: QColor):
        if color.isValid():
            self.pen_color = color
            if self.text_input:
                self.text_input.setStyleSheet(f"color: {color.name()}; background-color: transparent; border: 1px dashed {color.name()};")

    def handle_width_change(self, width: int):
        if self.current_tool == 'eraser':
            self.eraser_width = width
        else:
            self.pen_width = width

    def handle_opacity_change(self, opacity: int):
        self.pen_opacity = opacity

    def toggle_smoothing(self, enabled: bool):
        self.smoothing_enabled = enabled

    def handle_font_change(self, font_family: str):
        self.font.setFamily(font_family)
        self._update_text_input_font()

    def handle_font_size_change(self, size: int):
        self.font.setPointSize(size)
        self._update_text_input_font()

    def _update_text_input_font(self):
        if self.text_input:
            self.text_input.setFont(self.font)
            metrics = QFontMetrics(self.font)
            text_width = metrics.horizontalAdvance(self.text_input.text()) + 20
            text_height = metrics.height() + 10
            self.text_input.setFixedSize(max(100, text_width), text_height)

    def _save_history(self):
        self.redo_stack.clear()
        if len(self.history_stack) >= self.history_limit:
            del self.history_stack[0]
        self.history_stack.append(self.image.copy())
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        self.toolbar.set_undo_enabled(len(self.history_stack) > 1)
        self.toolbar.set_redo_enabled(bool(self.redo_stack))

    def undo(self):
        if len(self.history_stack) > 1:
            self.redo_stack.append(self.history_stack.pop())
            self.image = self.history_stack[-1].copy()
            self.update()
            self._update_undo_redo_buttons()

    def redo(self):
        if self.redo_stack:
            self.history_stack.append(self.redo_stack.pop())
            self.image = self.history_stack[-1].copy()
            self.update()
            self._update_undo_redo_buttons()

    def clear_screen(self):
        self.image.fill(Qt.transparent)
        self._save_history()
        self.update()

    def handle_canvas_change(self, canvas_type: str):
        """處理畫布背景變更。"""
        previous_mode = self.canvas_mode
        is_currently_transparent = self.testAttribute(Qt.WA_TranslucentBackground)

        new_mode = self.canvas_mode
        should_revert = False

        if canvas_type == "桌面":
            new_mode = 'desktop'
            self.hide()
            QTimer.singleShot(100, self._grab_desktop_and_show)
            return
        elif canvas_type == "黑板":
            new_mode = 'blackboard'
            self.canvas_color = QColor("#2E4636")
            self.background_pixmap = None
            self.loaded_background_image = None
        elif canvas_type == "白板":
            new_mode = 'whiteboard'
            self.canvas_color = QColor(Qt.white)
            self.background_pixmap = None
            self.loaded_background_image = None
        elif canvas_type == "純色":
            color = QColorDialog.getColor(self.canvas_color, self, "選擇畫布顏色")
            if color.isValid():
                new_mode = 'solid'
                self.canvas_color = color
                self.background_pixmap = None
                self.loaded_background_image = None
            else:
                should_revert = True
        elif canvas_type == "半透明":
            new_mode = 'transparent'
            self.background_pixmap = None
            self.loaded_background_image = None
        elif canvas_type == "讀取檔案":
            file_path, _ = QFileDialog.getOpenFileName(self, "選擇背景圖片", "", "Image Files (*.png *.jpg *.bmp *.jpeg)")
            if file_path:
                self.loaded_background_image = QPixmap(file_path)
                if not self.loaded_background_image.isNull():
                    new_mode = 'file'
                    self.background_pixmap = None
                else:
                    QMessageBox.warning(self, "讀取失敗", "無法讀取有效的圖片檔案。")
                    should_revert = True
            else:
                should_revert = True

        if should_revert:
            self.toolbar.canvas_combo.blockSignals(True)
            self.toolbar.canvas_combo.setCurrentText(self.get_mode_text(previous_mode))
            self.toolbar.canvas_combo.blockSignals(False)
            return

        self.canvas_mode = new_mode
        
        is_new_mode_transparent = (self.canvas_mode == 'transparent')
        if is_currently_transparent != is_new_mode_transparent:
            self.setAttribute(Qt.WA_TranslucentBackground, is_new_mode_transparent)
            self.hide()
            self.showFullScreen()
        
        self.update()

    def get_mode_text(self, mode: str) -> str:
        return {
            'desktop': '桌面', 'blackboard': '黑板', 'whiteboard': '白板',
            'solid': '純色', 'transparent': '半透明', 'file': '讀取檔案'
        }.get(mode, '桌面')

    def handle_pattern_change(self, pattern_type: str):
        mode_map = {"無": 'none', "細方格": 'fine_grid', "粗方格": 'coarse_grid'}
        self.pattern_mode = mode_map.get(pattern_type, 'none')
        self.update()

    def handle_save_action(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("選擇儲存方式")
        msg_box.setText("您要儲存整個畫面，還是只儲存圈選的範圍？")
        save_all_button = msg_box.addButton("儲存全部", QMessageBox.ActionRole)
        save_crop_button = msg_box.addButton("儲存選取", QMessageBox.ActionRole)
        msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.exec_()
        if msg_box.clickedButton() == save_all_button:
            self.save_drawing()
        elif msg_box.clickedButton() == save_crop_button:
            self.handle_tool_change('crop')

    def save_drawing(self):
        combined_pixmap = QPixmap(self.size())
        combined_pixmap.fill(Qt.transparent)
        painter = QPainter(combined_pixmap)
        if self.canvas_mode == 'desktop' and self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode in ['blackboard', 'whiteboard', 'solid']:
            painter.fillRect(self.rect(), self.canvas_color)
        elif self.canvas_mode == 'file' and self.loaded_background_image:
            painter.drawPixmap(self.rect(), self.loaded_background_image)
        elif self.canvas_mode == 'transparent':
            pass

        self.draw_pattern(painter)
        painter.drawPixmap(self.rect(), self.image)
        painter.end()

        file_path, _ = QFileDialog.getSaveFileName(self, "儲存畫記", "", "PNG 圖片 (*.png);;JPEG 圖片 (*.jpg *.jpeg)")
        if file_path:
            if self.canvas_mode == 'transparent' and not file_path.lower().endswith('.png'):
                file_path += '.png'
            combined_pixmap.save(file_path)

    def end_drawing_mode(self):
        self.save_settings()
        self.toggle_drawing_mode(False)
        self.drawing_mode_ended.emit()

    def draw_pattern(self, painter: QPainter):
        if self.pattern_mode == 'none': return
        grid_size = 25 if self.pattern_mode == 'fine_grid' else 75
        pen = QPen(QColor(128, 128, 128, 100), 1, Qt.SolidLine)
        painter.setPen(pen)
        for x in range(0, self.width(), grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_size):
            painter.drawLine(0, y, self.width(), y)

    def save_cropped_area(self, crop_rect: QRect):
        combined_pixmap = QPixmap(self.size())
        painter = QPainter(combined_pixmap)
        if self.canvas_mode == 'desktop' and self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode in ['blackboard', 'whiteboard', 'solid']:
            painter.fillRect(self.rect(), self.canvas_color)
        elif self.canvas_mode == 'file' and self.loaded_background_image:
            painter.drawPixmap(self.rect(), self.loaded_background_image)

        self.draw_pattern(painter)
        painter.drawPixmap(self.rect(), self.image)
        painter.end()

        cropped_pixmap = combined_pixmap.copy(crop_rect)
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存選取範圍", "", "PNG 圖片 (*.png);;JPEG 圖片 (*.jpg *.jpeg)")
        if file_path:
            cropped_pixmap.save(file_path)

    def toggle_drawing_mode(self, enable: bool):
        """Toggles the drawing mode on or off."""
        if enable:
            # Refresh the background screenshot only when entering desktop mode.
            if self.canvas_mode == 'desktop':
                screen = QApplication.primaryScreen()
                self.background_pixmap = screen.grabWindow(0)
            
            # Drawings and history are now preserved across hide/show.
            self._update_undo_redo_buttons() # Ensure buttons are in correct state.
            self.toolbar.show()
            self.showFullScreen()
            self.raise_()
            self.activateWindow()
            self.setFocus()
        else:
            self.toolbar.hide()
            self.hide()

    def save_settings(self):
        self.toolbar.save_state_to_settings(self.settings)
        self.settings.setValue("pen_width", self.pen_width)
        self.settings.setValue("eraser_width", self.eraser_width)
        self.settings.setValue("canvas_mode", self.canvas_mode)
        self.settings.setValue("canvas_color", self.canvas_color)
        self.settings.setValue("pattern_mode", self.pattern_mode)
        self.settings.sync()

    def load_settings(self):
        self.pen_width = self.settings.value("pen_width", 5, type=int)
        self.eraser_width = self.settings.value("eraser_width", 20, type=int)
        self.toolbar.set_initial_state(self.settings, self.font.family(), self.font.pointSize())
        self.pen_color = self.toolbar.pen_color
        self.smoothing_enabled = self.toolbar.smooth_button.isChecked()
        self.font.setFamily(self.toolbar.font_family)
        self.font.setPointSize(self.toolbar.font_size)
        self.canvas_mode = self.settings.value("canvas_mode", "desktop", type=str)
        canvas_color = self.settings.value("canvas_color", QColor("#2E4636"))
        self.canvas_color = canvas_color if isinstance(canvas_color, QColor) else QColor("#2E4636")
        self.pattern_mode = self.settings.value("pattern_mode", "none", type=str)
        self.toolbar.canvas_combo.blockSignals(True)
        self.toolbar.canvas_combo.setCurrentText(self.get_mode_text(self.canvas_mode))
        self.toolbar.canvas_combo.blockSignals(False)
        self.toolbar.pattern_combo.blockSignals(True)
        pattern_map_rev = {'none': "無", 'fine_grid': "細方格", 'coarse_grid': "粗方格"}
        self.toolbar.pattern_combo.setCurrentText(pattern_map_rev.get(self.pattern_mode, "無"))
        self.toolbar.pattern_combo.blockSignals(False)

    def _get_current_pen_color(self) -> QColor:
        """Returns the current pen color with the correct opacity."""
        color = QColor(self.pen_color)
        color.setAlpha(self.pen_opacity)
        return color

    def draw_arrow(self, painter: QPainter, start_point: QPoint, end_point: QPoint):
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
        dx = current_point.x() - start_point.x()
        dy = current_point.y() - start_point.y()
        side = max(abs(dx), abs(dy))
        constrained_x = start_point.x() + (side if dx > 0 else -side)
        constrained_y = start_point.y() + (side if dy > 0 else -side)
        return QPoint(constrained_x, constrained_y)

    def _commit_text_input(self):
        if self.text_input and self.text_input.text():
            painter = QPainter(self.image)
            painter.setPen(self._get_current_pen_color())
            painter.setFont(self.font)
            text_rect = self.text_input.geometry()
            draw_rect = text_rect.adjusted(3, 0, -5, 0)
            painter.drawText(draw_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text_input.text())
            painter.end()
            self._save_history()
        if self.text_input:
            self.text_input.deleteLater()
            self.text_input = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        self._commit_text_input()
        self.canvas_activated.emit()
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            if self.current_tool == 'text':
                self.text_input = MovableLineEdit(self)
                self.text_input.setFont(self.font)
                self.text_input.setStyleSheet(f"color: {self.pen_color.name()}; background-color: transparent; border: 1px dashed {self.pen_color.name()};")
                self.text_input.move(event.pos())
                self.text_input.setFixedSize(100, QFontMetrics(self.font).height() + 10)
                self.text_input.show()
                self.text_input.setFocus()
                self.text_input.textChanged.connect(self._update_text_input_font)
            elif self.current_tool == 'laser_pointer':
                self.laser_trail_segments.clear()
            elif self.current_tool in ['line', 'arrow', 'rectangle', 'circle', 'crop']:
                self.start_point = event.pos()
                self.current_point = event.pos()
            elif self.current_tool == 'highlighter':
                # Draw directly on self.image for correct opacity blending
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.Antialiasing)
                highlighter_color = QColor(self.pen_color.red(), self.pen_color.green(), self.pen_color.blue(), 64)
                pen = QPen(highlighter_color, self.pen_width * 2, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawPoint(self.last_point)
                painter.end()
                width = self.pen_width * 2 + 2
                update_rect = QRect(self.last_point, self.last_point).adjusted(-width, -width, width, width)
                self.update(update_rect)
            elif self.current_tool in ['freehand', 'eraser']:
                if self.current_tool == 'freehand' and self.smoothing_enabled:
                    self.point_buffer = [event.pos()]
                else:
                    painter = QPainter(self.image)
                    painter.setRenderHint(QPainter.Antialiasing)
                    width = 0
                    if self.current_tool == 'eraser':
                        painter.setCompositionMode(QPainter.CompositionMode_Clear)
                        painter.setPen(QPen(Qt.transparent, self.eraser_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        width = self.eraser_width
                    else:
                        pen_color_with_opacity = self._get_current_pen_color()
                        painter.setPen(QPen(pen_color_with_opacity, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        width = self.pen_width
                    painter.drawPoint(self.last_point)
                    painter.end()
                    margin = width // 2 + 2
                    update_rect = QRect(self.last_point, self.last_point).adjusted(-margin, -margin, margin, margin)
                    self.update(update_rect)

    def leaveEvent(self, event: QEvent):
        self.cursor_pos = QPoint(-1, -1)
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self.cursor_pos = event.pos()
        current_pos = event.pos()
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            update_rect = QRect()
            if self.current_tool == 'laser_pointer':
                self.laser_trail_segments.append((self.last_point, current_pos, 255))
                self.last_point = current_pos
                self.update()
            elif self.current_tool in ['line', 'arrow', 'rectangle', 'crop']:
                width = self.pen_width + 2
                r1 = QRect(self.start_point, self.current_point).normalized().adjusted(-width, -width, width, width)
                if event.modifiers() & Qt.ShiftModifier and self.current_tool == 'rectangle':
                    self.current_point = self._get_constrained_point(self.start_point, current_pos)
                else:
                    self.current_point = current_pos
                r2 = QRect(self.start_point, self.current_point).normalized().adjusted(-width, -width, width, width)
                update_rect = r1.united(r2)
                self.update(update_rect)
            elif self.current_tool == 'circle':
                center_x, center_y = self.start_point.x(), self.start_point.y()
                current_x, current_y = current_pos.x(), current_pos.y()

                if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                    radius = math.hypot(current_x - center_x, current_y - center_y)
                    # Bounding box for a perfect circle centered at start_point
                    update_rect = QRect(
                        int(center_x - radius), int(center_y - radius),
                        int(2 * radius), int(2 * radius)
                    )
                else:
                    rx = abs(current_x - center_x)
                    ry = abs(current_y - center_y)
                    # Bounding box for an ellipse centered at start_point
                    update_rect = QRect(
                        int(center_x - rx), int(center_y - ry),
                        int(2 * rx), int(2 * ry)
                    )
                # Add some margin for pen width
                width = self.pen_width + 2
                update_rect = update_rect.adjusted(-width, -width, width, width)
                self.current_point = current_pos # Update current_point for paintEvent
                self.update(update_rect)
            elif self.current_tool == 'highlighter':
                # Draw directly on self.image for correct opacity blending
                width = self.pen_width * 2 + 2
                update_rect = QRect(self.last_point, current_pos).normalized().adjusted(-width, -width, width, width)
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.Antialiasing)
                highlighter_color = QColor(self.pen_color.red(), self.pen_color.green(), self.pen_color.blue(), 64)
                pen = QPen(highlighter_color, self.pen_width * 2, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawLine(self.last_point, current_pos)
                painter.end()
                self.last_point = current_pos
                self.update(update_rect)
            elif self.current_tool in ['freehand', 'eraser']:
                width = self.eraser_width if self.current_tool == 'eraser' else self.pen_width
                margin = width // 2 + 2
                painter = QPainter(self.image)
                if self.smoothing_enabled:
                    painter.setRenderHint(QPainter.Antialiasing)
                if self.current_tool == 'eraser':
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    pen = QPen(Qt.transparent, self.eraser_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                else:
                    pen_color_with_opacity = self._get_current_pen_color()
                    pen = QPen(pen_color_with_opacity, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                if self.current_tool == 'freehand' and self.smoothing_enabled:
                    self.point_buffer.append(current_pos)
                    path = QPainterPath()
                    if len(self.point_buffer) >= 3:
                        p1, p2, p3 = self.point_buffer[-3:]
                        mid1 = QPoint((p1.x() + p2.x()) // 2, (p1.y() + p2.y()) // 2)
                        mid2 = QPoint((p2.x() + p3.x()) // 2, (p2.y() + p3.y()) // 2)
                        path.moveTo(mid1)
                        path.quadTo(p2, mid2)
                        painter.drawPath(path)
                    update_rect = path.boundingRect().toRect().adjusted(-margin, -margin, margin, margin)
                else:
                    update_rect = QRect(self.last_point, current_pos).normalized().adjusted(-margin, -margin, margin, margin)
                    painter.drawLine(self.last_point, current_pos)
                painter.end()
                self.last_point = current_pos
                self.update(update_rect)
        else:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            save_needed = False
            if self.current_tool in ['line', 'arrow', 'rectangle', 'circle']:
                final_point = event.pos()
                if event.modifiers() & Qt.ShiftModifier and self.current_tool == 'rectangle':
                    final_point = self._get_constrained_point(self.start_point, final_point)
                if self.start_point and self.start_point != final_point:
                    painter = QPainter(self.image)
                    painter.setRenderHint(QPainter.Antialiasing)
                    pen_color_with_opacity = self._get_current_pen_color()
                    pen = QPen(pen_color_with_opacity, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    if self.current_tool == 'line':
                        painter.drawLine(self.start_point, final_point)
                    elif self.current_tool == 'arrow':
                        self.draw_arrow(painter, self.start_point, final_point)
                    elif self.current_tool == 'rectangle':
                        painter.drawRect(QRect(self.start_point, final_point).normalized())
                    elif self.current_tool == 'circle':
                        center_x, center_y = self.start_point.x(), self.start_point.y()
                        final_x, final_y = final_point.x(), final_point.y()

                        if event.modifiers() & Qt.ShiftModifier:
                            # Draw a perfect circle (radius is distance from center to final point)
                            radius = math.hypot(final_x - center_x, final_y - center_y)
                            painter.drawEllipse(self.start_point, radius, radius)
                        else:
                            # Draw an ellipse (rx, ry are distances from center to final point)s
                            rx = abs(final_x - center_x)
                            ry = abs(final_y - center_y)
                            painter.drawEllipse(self.start_point, rx, ry)
                    painter.end()
                    save_needed = True
                self.start_point = None
                self.current_point = None
            elif self.current_tool == 'crop':
                if self.start_point and self.current_point and self.start_point != event.pos():
                    crop_rect = QRect(self.start_point, event.pos()).normalized()
                    self.save_cropped_area(crop_rect)
                self.toolbar.set_tool_checked('freehand')
                self.start_point = None
                self.current_point = None
            elif self.current_tool in ['freehand', 'eraser']:
                if self.current_tool == 'freehand' and self.smoothing_enabled:
                    painter = QPainter(self.image)
                    if self.smoothing_enabled:
                        painter.setRenderHint(QPainter.Antialiasing)
                    pen_color_with_opacity = self._get_current_pen_color()
                    pen = QPen(pen_color_with_opacity, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    if len(self.point_buffer) == 1:
                        painter.drawPoint(self.point_buffer[0])
                    elif len(self.point_buffer) == 2:
                        painter.drawLine(self.point_buffer[0], self.point_buffer[1])
                    painter.end()
                    self.point_buffer.clear()
                save_needed = True
            elif self.current_tool == 'highlighter':
                # No need to draw highlighter_temp_image, as drawing is direct now.
                # Just save history and update.
                save_needed = True # Drawing already happened in mouseMoveEvent
                self.highlighter_temp_image = None # Clear the reference
            if save_needed:
                self._save_history()
            self.update()

    def paintEvent(self, event):
        if self.width() <= 0 or self.height() <= 0:
            return

        painter = QPainter(self)
        painter.setClipRect(event.rect()) # --- 效能優化：設定剪裁區域 ---

        # --- Brute-force clear to fight rendering ghosts ---
        # On some systems, changing transparency attributes can leave stale images.
        # We start by clearing the entire widget area to full transparency.
        # This acts as a reset before every paint.
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        # --- End of clear ---

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Now, draw the correct background based on the current mode
        if self.canvas_mode == 'desktop':
            if self.background_pixmap and not self.background_pixmap.isNull():
                painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.canvas_mode in ['blackboard', 'whiteboard', 'solid']:
            painter.fillRect(self.rect(), self.canvas_color)
        elif self.canvas_mode == 'transparent':
            # The clearing at the top makes the background transparent.
            # We need to paint a near-invisible color to capture mouse events.
            painter.fillRect(self.rect(), QColor(0, 0, 0, 5))
        elif self.canvas_mode == 'file' and self.loaded_background_image:
            painter.drawPixmap(self.rect(), self.loaded_background_image)

        self.draw_pattern(painter)
        if self.image and not self.image.isNull():
            painter.drawPixmap(self.rect(), self.image)

        

        if self.drawing and self.start_point and self.current_point:
            pen_color_with_opacity = self._get_current_pen_color()
            preview_pen = QPen(QColor(0, 120, 255), 2, Qt.DashLine) if self.current_tool == 'crop' else QPen(pen_color_with_opacity, self.pen_width, Qt.DashLine)
            painter.setPen(preview_pen)
            if self.current_tool == 'line':
                painter.drawLine(self.start_point, self.current_point)
            elif self.current_tool == 'arrow':
                self.draw_arrow(painter, self.start_point, self.current_point)
            elif self.current_tool in ['rectangle', 'crop']:
                rect = QRect(self.start_point, self.current_point).normalized()
                painter.drawRect(rect)
            elif self.current_tool == 'circle':
                center_x, center_y = self.start_point.x(), self.start_point.y()
                current_x, current_y = self.current_point.x(), self.current_point.y()

                if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                    # Draw a perfect circle (radius is distance from center to current point)
                    radius = math.hypot(current_x - center_x, current_y - center_y)
                    painter.drawEllipse(self.start_point, radius, radius)
                else:
                    # Draw an ellipse (rx, ry are distances from center to current point)
                    rx = abs(current_x - center_x)
                    ry = abs(current_y - center_y)
                    painter.drawEllipse(self.start_point, rx, ry)

        if self.laser_trail_segments:
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
                color = self.pen_color
                laser_pen = QPen(QColor(color.red(), color.green(), color.blue(), opacity), int(current_width), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(laser_pen)
                painter.drawLine(start_p, end_p)

        if self.current_tool == 'eraser' and self.rect().contains(self.cursor_pos):
            radius = self.eraser_width / 2
            painter.setPen(QPen(QColor(128, 128, 128, 200), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.cursor_pos, radius, radius)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.end_drawing_mode()

    def resizeEvent(self, event):
        new_size = self.size()
        if self.image.size() != new_size and new_size.isValid() and new_size.width() > 0 and new_size.height() > 0:
            old_image = self.image
            self.image = QPixmap(new_size)
            self.image.fill(Qt.transparent)
            painter = QPainter(self.image)
            painter.drawPixmap(QPoint(0, 0), old_image)
            painter.end()
        super().resizeEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if QApplication.keyboardModifiers() == Qt.NoModifier:
            delta = event.angleDelta().y()
            step = 1
            if self.current_tool == 'eraser':
                current_width = self.eraser_width
                new_width = min(current_width + step, 50) if delta > 0 else max(current_width - step, 1)
                if new_width != self.eraser_width:
                    self.eraser_width = new_width
                    self.toolbar.set_width_value(self.eraser_width)
            else:
                current_width = self.pen_width
                new_width = min(current_width + step, 50) if delta > 0 else max(current_width - step, 1)
                if new_width != self.pen_width:
                    self.pen_width = new_width
                    self.toolbar.set_width_value(self.pen_width)
            event.accept()
        else:
            super().wheelEvent(event)



