# -*- coding: utf-8 -*-
"""
Модуль холста для работы с изображениями (вкладка 2).
Загружает изображения и распознает контуры.
"""

import cv2
import numpy as np
from typing import List
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QImage
from PyQt5.QtCore import Qt
from .models import Point


class ImageCanvas(QWidget):
    """
    Виджет-холст для второй вкладки.
    Загружает изображения и автоматически распознает контуры.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(200, 150)

        self.contours: List[List[Point]] = []
        self.original_contours: List[List[Point]] = []
        self.original_image = None
        self.display_pixmap = None
        self.image_path = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def to_canvas_coords(self, point):
        """Преобразует координаты робота в координаты холста."""
        return point.to_canvas_coords(self.width(), self.height())

    def load_image(self, image_path):
        """Загружает изображение из файла."""
        try:
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                return False

            self.image_path = image_path

            rgb_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.display_pixmap = QPixmap.fromImage(qt_image)

            self.contours.clear()
            self.original_contours.clear()
            self.update()
            return True

        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return False

    def detect_contours(self):
        """Распознает контуры на загруженном изображении."""
        if self.original_image is None:
            return False

        try:
            img_height, img_width = self.original_image.shape[:2]

            scale_x = 460 / img_width
            scale_y = 340 / img_height
            self.scale = min(scale_x, scale_y)

            self.offset_x = (480 - img_width * self.scale) / 2 - 240
            self.offset_y = (360 - img_height * self.scale) / 2 - 180

            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            img = cv2.bitwise_not(gray)
            _, threshold = cv2.threshold(img, 110, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            self.contours.clear()
            self.original_contours.clear()

            for cnt in contours:
                if len(cnt) < 3:
                    continue

                epsilon = 0.001 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)

                contour_points = []
                n = approx.ravel()

                for i in range(0, len(n), 2):
                    if i + 1 < len(n):
                        x = n[i]
                        y = n[i + 1]

                        robot_x = x * self.scale + self.offset_x
                        robot_y = -(y * self.scale + self.offset_y)

                        robot_x = max(-240, min(240, robot_x))
                        robot_y = max(-180, min(180, robot_y))

                        contour_points.append(Point(robot_x, robot_y))

                if len(contour_points) > 2:
                    contour_points.append(contour_points[0])
                    self.contours.append(contour_points)
                    self.original_contours.append(contour_points[:])

            self.update()
            return True

        except Exception as e:
            print(f"Ошибка распознавания контуров: {e}")
            return False

    def simplify_contours(self, epsilon_factor):
        """Упрощает контуры с помощью алгоритма Ramer-Douglas-Peucker."""
        if not self.original_contours:
            return False, 0, 0

        if epsilon_factor == 0:
            self.contours = [contour[:] for contour in self.original_contours]
            self.update()
            original_points = sum(len(contour) for contour in self.original_contours)
            return True, original_points, original_points

        original_points = sum(len(contour) for contour in self.original_contours)
        simplified_contours = []

        for contour in self.original_contours:
            if len(contour) < 3:
                simplified_contours.append(contour[:])
                continue

            points_array = np.array([[[p.x, p.y]] for p in contour], dtype=np.float32)

            peri = cv2.arcLength(points_array, True)
            epsilon = epsilon_factor * peri
            approx = cv2.approxPolyDP(points_array, epsilon, True)

            simplified = [Point(float(p[0][0]), float(p[0][1])) for p in approx]
            simplified_contours.append(simplified)

        self.contours = simplified_contours
        self.update()

        simplified_points = sum(len(contour) for contour in self.contours)
        return True, original_points, simplified_points

    def clear(self):
        """Полностью очищает холст изображения."""
        self.contours.clear()
        self.original_contours.clear()
        self.original_image = None
        self.display_pixmap = None
        self.image_path = None
        self.update()

    def draw_grid(self, painter):
        """Рисует координатную сетку и загруженное изображение."""
        w = self.width()
        h = self.height()
        center_x = w / 2
        center_y = h / 2
        scale = min(w / 480, h / 360)

        left = int(center_x - 240 * scale)
        right = int(center_x + 240 * scale)
        top = int(center_y - 180 * scale)
        bottom = int(center_y + 180 * scale)

        painter.fillRect(self.rect(), Qt.white)

        if self.display_pixmap:
            scaled_pixmap = self.display_pixmap.scaled(
                int(480 * scale), int(360 * scale),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            painter.drawPixmap(
                int(center_x - scaled_pixmap.width() / 2),
                int(center_y - scaled_pixmap.height() / 2),
                scaled_pixmap
            )

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
        """Главный метод отрисовки ImageCanvas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.draw_grid(painter)

        colors = [Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.cyan, Qt.yellow]

        for idx, contour in enumerate(self.contours):
            color = colors[idx % len(colors)]

            if len(contour) > 1:
                pen = QPen(color, 2)
                painter.setPen(pen)
                for i in range(len(contour) - 1):
                    p1 = self.to_canvas_coords(contour[i])
                    p2 = self.to_canvas_coords(contour[i + 1])
                    painter.drawLine(p1, p2)

            for point in contour:
                canvas_point = self.to_canvas_coords(point)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawEllipse(canvas_point, 3, 3)

        painter.setPen(QPen(Qt.darkGray))
        painter.drawText(10, 10, f"Контуров: {len(self.contours)}")
