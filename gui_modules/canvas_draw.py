# -*- coding: utf-8 -*-
"""
Модуль холста для ручного рисования (вкладка 1).
Позволяет пользователю рисовать точки и сегменты мышью.
"""

import math
from typing import List
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QPoint
from .models import Point


class DrawCanvas(QWidget):
    """
    Виджет-холст для первой вкладки.
    Позволяет вручную рисовать точки, формируя траекторию для робота.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(200, 150)

        self.mode = "draw"
        self.points: List[Point] = []
        self.segments: List[int] = []
        self.selected_point_index = -1
        self.selected_point = None

    def to_model_coords(self, pos):
        """Преобразует координаты мыши в координаты робота."""
        return Point.from_canvas_coords(pos, self.width(), self.height())

    def to_canvas_coords(self, point):
        """Преобразует координаты робота в координаты холста."""
        return point.to_canvas_coords(self.width(), self.height())

    def inside_area(self, x, y):
        """Проверяет, находятся ли координаты в рабочей области робота."""
        return abs(x) <= 240 and abs(y) <= 180

    def set_mode(self, mode):
        """Устанавливает режим работы холста ('draw' или 'edit')."""
        self.mode = mode
        if mode == "draw":
            self.selected_point_index = -1
            self.selected_point = None
        self.update()

    def new_line(self):
        """Начинает новый сегмент."""
        if self.points:
            self.segments.append(len(self.points))
        self.update()

    def delete_last_point(self):
        """Удаляет последнюю добавленную точку."""
        if self.points:
            self.points.pop()
            if len(self.points) in self.segments:
                self.segments.remove(len(self.points))
            self.update()

    def clear_all(self):
        """Полностью очищает холст."""
        self.points.clear()
        self.segments.clear()
        self.selected_point_index = -1
        self.selected_point = None
        self.update()

    def keyPressEvent(self, event):
        """Обработчик нажатий клавиш."""
        if event.key() == Qt.Key_Space:
            self.new_line()
            if hasattr(self.parent(), 'newLineButton'):
                self.parent().newLineButton.animateClick(100)
        if event.key() == Qt.Key_X:
            self.delete_last_point()
            if hasattr(self.parent(), 'deleteButton'):
                self.parent().deleteButton.animateClick(100)

    def find_closest_point(self, pos, max_dist=20):
        """Находит индекс ближайшей точки к позиции курсора."""
        closest_idx = -1
        min_dist = max_dist + 1
        for i, point in enumerate(self.points):
            canvas_point = self.to_canvas_coords(point)
            dist = math.sqrt((pos.x() - canvas_point.x())**2 + (pos.y() - canvas_point.y())**2)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        return closest_idx

    def mousePressEvent(self, event):
        """Обработчик нажатия кнопок мыши."""
        if event.button() == Qt.LeftButton:
            if self.mode == "draw":
                point = self.to_model_coords(event.pos())
                if not self.inside_area(point.x, point.y):
                    return
                self.points.append(point)
                self.update()
            elif self.mode == "edit":
                idx = self.find_closest_point(event.pos())
                if idx >= 0:
                    self.selected_point_index = idx
                    self.selected_point = self.points[idx]
                else:
                    self.selected_point_index = -1
                    self.selected_point = None
        elif event.button() == Qt.RightButton:
            idx = self.find_closest_point(event.pos())
            if idx >= 0:
                self.points.pop(idx)
                new_segments = []
                for seg_idx in self.segments:
                    if seg_idx > idx:
                        new_segments.append(seg_idx - 1)
                    elif seg_idx < idx:
                        new_segments.append(seg_idx)
                self.segments = new_segments
                self.selected_point_index = -1
                self.selected_point = None
                self.update()

    def mouseMoveEvent(self, event):
        """Обработчик перемещения мыши."""
        if self.mode == "edit" and self.selected_point_index >= 0:
            if event.buttons() & Qt.LeftButton:
                new_point = self.to_model_coords(event.pos())
                if not self.inside_area(new_point.x, new_point.y):
                    return
                self.points[self.selected_point_index] = new_point
                self.selected_point = new_point
                self.update()

    def mouseReleaseEvent(self, event):
        """Обработчик отпускания кнопки мыши."""
        if self.mode == "edit":
            if event.button() == Qt.LeftButton and self.selected_point_index >= 0:
                self.selected_point_index = -1
                self.selected_point = None

    def draw_grid(self, painter):
        """Рисует координатную сетку и границы рабочей области."""
        w = self.width()
        h = self.height()
        center_x = w / 2
        center_y = h / 2

        scale_x = w / 480
        scale_y = h / 360
        scale = min(scale_x, scale_y)

        left = int(center_x - 240 * scale)
        right = int(center_x + 240 * scale)
        top = int(center_y - 180 * scale)
        bottom = int(center_y + 180 * scale)

        painter.fillRect(self.rect(), Qt.white)

        pen = QPen(QColor(200, 200, 200), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(int(center_x), 0, int(center_x), h)
        painter.drawLine(0, int(center_y), w, int(center_y))

        pen.setColor(Qt.red)
        pen.setWidth(2)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(left, top, int(480 * scale), int(360 * scale))

        pen.setColor(Qt.black)
        pen.setWidth(1)
        painter.setPen(pen)

        for x in range(-240, 241, 60):
            canvas_x = int(center_x + x * scale)
            if left <= canvas_x <= right:
                painter.drawLine(canvas_x, int(center_y - 3), canvas_x, int(center_y + 3))
                if x != 0:
                    painter.drawText(canvas_x - 10, int(center_y + 20), str(x))

        for y in range(-180, 181, 60):
            canvas_y = int(center_y - y * scale)
            if top <= canvas_y <= bottom:
                painter.drawLine(int(center_x - 3), canvas_y, int(center_x + 3), canvas_y)
                if y != 0:
                    painter.drawText(int(center_x + 10), canvas_y + 5, str(y))

        painter.drawText(int(center_x + 5), int(center_y - 5), "(0,0)")

    def paintEvent(self, event):
        """Главный метод отрисовки холста."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.draw_grid(painter)

        if self.points:
            segment_indices = sorted(self.segments)
            pen = QPen(Qt.black, 2)
            painter.setPen(pen)

            start_idx = 0
            for seg_idx in segment_indices:
                for i in range(start_idx, seg_idx - 1):
                    if i + 1 < len(self.points):
                        p1 = self.to_canvas_coords(self.points[i])
                        p2 = self.to_canvas_coords(self.points[i + 1])
                        painter.drawLine(p1, p2)
                start_idx = seg_idx

            for i in range(start_idx, len(self.points) - 1):
                p1 = self.to_canvas_coords(self.points[i])
                p2 = self.to_canvas_coords(self.points[i + 1])
                painter.drawLine(p1, p2)

            for i, point in enumerate(self.points):
                canvas_point = self.to_canvas_coords(point)
                is_segment_start = i in self.segments

                if i == self.selected_point_index:
                    painter.setBrush(QBrush(Qt.red))
                    painter.setPen(QPen(Qt.black, 2))
                    painter.drawEllipse(canvas_point, 8, 8)
                else:
                    if is_segment_start:
                        painter.setBrush(QBrush(Qt.green))
                    else:
                        painter.setBrush(QBrush(Qt.blue))
                    painter.setPen(QPen(Qt.black, 1))
                    painter.drawEllipse(canvas_point, 5, 5)

        painter.setPen(QPen(Qt.darkGray))
        mode_text = "РИСОВАНИЕ" if self.mode == "draw" else "РЕДАКТИРОВАНИЕ"
        segments_count = len(self.segments) + 1 if self.points else 0
        painter.drawText(10, 10, f"Режим: {mode_text} | Точки: {len(self.points)} | Сегменты: {segments_count}")
