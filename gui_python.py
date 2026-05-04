# -*- coding: utf-8 -*-

# Импорт стандартных библиотек
import sys
import subprocess
import math
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List
import os

# Импорт компонентов графического интерфейса PyQt5
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QMessageBox, QFileDialog, QSizePolicy, QLabel, QPushButton
)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QImage
from PyQt5.QtCore import Qt, QPoint
# Импорт сгенерированного класса пользовательского интерфейса
from ui_main import Ui_MainWindow

# --- Глобальные константы ---
# Специальный код, добавляемый к координатам X первой точки каждого сегмента,
# чтобы робот понял, что нужно поднять перо перед перемещением в эту точку.
PEN_UP_CODE = 1000

# --- Вспомогательный класс для представления точки ---
@dataclass
class Point:
    """Класс для хранения координат точки в системе робота и преобразования их в координаты холста."""
    x: float
    y: float
    
    def to_canvas_coords(self, canvas_width: int, canvas_height: int) -> QPoint:
        """
        Преобразует координаты робота (миллиметры или условные единицы)
        в координаты виджета QPoint для отображения на холсте.
        Центр холста соответствует точке (0,0) робота.
        """
        # Вычисляем масштаб, чтобы рабочая область робота (480x360) вписалась в холст
        scale_x = canvas_width / 480
        scale_y = canvas_height / 360
        scale = min(scale_x, scale_y)  # Сохраняем пропорции
        
        # Преобразование: X робота добавляется к центру холста, Y вычитается, т.к. ось Y на холсте направлена вниз
        canvas_x = int(canvas_width / 2 + self.x * scale)
        canvas_y = int(canvas_height / 2 - self.y * scale)
        
        return QPoint(canvas_x, canvas_y)
    
    @staticmethod
    def from_canvas_coords(pos: QPoint, canvas_width: int, canvas_height: int) -> 'Point':
        """Преобразует координаты точки на холсте (QPoint) обратно в координаты робота (Point)."""
        scale_x = canvas_width / 480
        scale_y = canvas_height / 360
        scale = min(scale_x, scale_y)
        
        # Обратное преобразование
        x = (pos.x() - canvas_width / 2) / scale
        y = (canvas_height / 2 - pos.y()) / scale
        
        # Ограничение координат рабочей областью робота
        x = max(-240, min(240, x))
        y = max(-180, min(180, y))
        
        return Point(x, y)


# -----------------------------
# Класс холста для рисования точек (1 вкладка)
# -----------------------------
class DrawCanvas(QWidget):
    """
    Виджет-холст для первой вкладки, позволяющий пользователю вручную рисовать точки,
    формируя траекторию для робота-художника.
    """
    def __init__(self, parent=None):
        """Инициализация холста: настройка отслеживания мыши и начальных переменных."""
        super().__init__(parent)
        self.setMouseTracking(True)  # Отслеживаем движение мыши, даже если кнопка не нажата
        self.setFocusPolicy(Qt.StrongFocus)  # Виджет может принимать фокус для обработки клавиш
        self.setMinimumSize(200, 150)

        self.mode = "draw"  # Режим работы: "draw" (рисование) или "edit" (редактирование)
        self.points: List[Point] = []  # Список всех точек на холсте
        self.segments: List[int] = []  # Индексы точек, которые являются началом нового сегмента (линии)
        self.selected_point_index = -1  # Индекс точки, выбранной в режиме редактирования
        self.selected_point = None  # Координаты выбранной точки

    def to_model_coords(self, pos):
        """Преобразует координаты мыши (QPoint) в координаты робота (Point)."""
        return Point.from_canvas_coords(pos, self.width(), self.height())

    def to_canvas_coords(self, point):
        """Преобразует координаты робота (Point) в координаты холста (QPoint)."""
        return point.to_canvas_coords(self.width(), self.height())

    def inside_area(self, x, y):
        """Проверяет, находятся ли координаты (x, y) в допустимой рабочей области робота."""
        return abs(x) <= 240 and abs(y) <= 180

    def set_mode(self, mode):
        """Устанавливает режим работы холста ('draw' или 'edit') и сбрасывает выделение."""
        self.mode = mode
        if mode == "draw":
            self.selected_point_index = -1
            self.selected_point = None
        self.update()  # Перерисовываем холст

    def new_line(self):
        """Начинает новый сегмент. Следующая добавленная точка будет началом новой линии."""
        if self.points:
            self.segments.append(len(self.points))
        self.update()

    def delete_last_point(self):
        """Удаляет последнюю добавленную точку. Если она была началом сегмента, обновляет информацию о сегментах."""
        if self.points:
            self.points.pop()
            if len(self.points) in self.segments:
                self.segments.remove(len(self.points))
            self.update()

    def clear_all(self):
        """Полностью очищает холст, удаляя все точки и сегменты."""
        self.points.clear()
        self.segments.clear()
        self.selected_point_index = -1
        self.selected_point = None
        self.update()

    def keyPressEvent(self, event):
        """
        Обработчик нажатий клавиш:
        - Пробел (Space): начать новую линию.
        - Клавиша X: удалить последнюю точку.
        """
        if event.key() == Qt.Key_Space:
            self.new_line()
            # Визуально "нажимаем" соответствующую кнопку в интерфейсе, если она есть
            if hasattr(self.parent(), 'newLineButton'):
                self.parent().newLineButton.animateClick(100)
        if event.key() == Qt.Key_X:
            self.delete_last_point()
            if hasattr(self.parent(), 'deleteButton'):
                self.parent().deleteButton.animateClick(100)

    def find_closest_point(self, pos, max_dist=20):
        """
        Находит индекс точки, ближайшей к позиции курсора `pos`.
        Возвращает индекс точки или -1, если все точки дальше, чем `max_dist`.
        """
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
        """
        Обработчик нажатия кнопок мыши:
        - ЛКМ в режиме "draw": добавляет новую точку на холст.
        - ЛКМ в режиме "edit": выбирает ближайшую точку для редактирования.
        - ПКМ в обоих режимах: удаляет ближайшую точку и обновляет сегменты.
        """
        if event.button() == Qt.LeftButton:
            if self.mode == "draw":
                # Создаем новую точку, проверяя, что она в рабочей области
                point = self.to_model_coords(event.pos())
                if not self.inside_area(point.x, point.y):
                    return
                self.points.append(point)
                self.update()
            elif self.mode == "edit":
                # Выбираем точку для редактирования
                idx = self.find_closest_point(event.pos())
                if idx >= 0:
                    self.selected_point_index = idx
                    self.selected_point = self.points[idx]
                else:
                    self.selected_point_index = -1
                    self.selected_point = None
        elif event.button() == Qt.RightButton:
            # Удаляем ближайшую точку
            idx = self.find_closest_point(event.pos())
            if idx >= 0:
                self.points.pop(idx)
                # Корректируем индексы начала сегментов после удаления точки
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
        """
        Обработчик перемещения мыши.
        Если в режиме "edit" зажата ЛКМ, перемещает выбранную точку.
        """
        if self.mode == "edit" and self.selected_point_index >= 0:
            if event.buttons() & Qt.LeftButton:
                new_point = self.to_model_coords(event.pos())
                if not self.inside_area(new_point.x, new_point.y):
                    return
                self.points[self.selected_point_index] = new_point
                self.selected_point = new_point
                self.update()

    def mouseReleaseEvent(self, event):
        """Обработчик отпускания кнопки мыши. Снимает выделение с точки в режиме редактирования."""
        if self.mode == "edit":
            if event.button() == Qt.LeftButton and self.selected_point_index >= 0:
                self.selected_point_index = -1
                self.selected_point = None

    def draw_grid(self, painter):
        """Рисует координатную сетку, оси и границы рабочей области робота."""
        w = self.width()
        h = self.height()
        center_x = w / 2
        center_y = h / 2
        
        scale_x = w / 480
        scale_y = h / 360
        scale = min(scale_x, scale_y)
        
        # Границы рабочей области в координатах холста
        left = int(center_x - 240 * scale)
        right = int(center_x + 240 * scale)
        top = int(center_y - 180 * scale)
        bottom = int(center_y + 180 * scale)
        
        painter.fillRect(self.rect(), Qt.white)  # Белый фон
        
        # Рисуем легкие осевые линии
        pen = QPen(QColor(200, 200, 200), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(int(center_x), 0, int(center_x), h)
        painter.drawLine(0, int(center_y), w, int(center_y))
        
        # Рисуем красную рамку рабочей области робота
        pen.setColor(Qt.red)
        pen.setWidth(2)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(left, top, int(480 * scale), int(360 * scale))
        
        # Рисуем метки на осях
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
        """Главный метод отрисовки всего содержимого холста."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # Сглаживание
        self.draw_grid(painter)  # Сначала рисуем сетку
        
        if self.points:
            # Рисуем линии между точками
            segment_indices = sorted(self.segments)
            pen = QPen(Qt.black, 2)
            painter.setPen(pen)
            
            start_idx = 0
            for seg_idx in segment_indices:
                # Рисуем сегмент как набор линий между точками
                for i in range(start_idx, seg_idx - 1):
                    if i + 1 < len(self.points):
                        p1 = self.to_canvas_coords(self.points[i])
                        p2 = self.to_canvas_coords(self.points[i + 1])
                        painter.drawLine(p1, p2)
                start_idx = seg_idx  # Переходим к следующему сегменту
            
            # Рисуем последний сегмент (если он не закончился явно)
            for i in range(start_idx, len(self.points) - 1):
                p1 = self.to_canvas_coords(self.points[i])
                p2 = self.to_canvas_coords(self.points[i + 1])
                painter.drawLine(p1, p2)
            
            # Рисуем точки
            for i, point in enumerate(self.points):
                canvas_point = self.to_canvas_coords(point)
                is_segment_start = i in self.segments
                
                if i == self.selected_point_index:  # Выбранная точка (красная, большая)
                    painter.setBrush(QBrush(Qt.red))
                    painter.setPen(QPen(Qt.black, 2))
                    painter.drawEllipse(canvas_point, 8, 8)
                else:
                    # Начало сегмента - зеленая, обычные точки - синие
                    if is_segment_start:
                        painter.setBrush(QBrush(Qt.green))
                    else:
                        painter.setBrush(QBrush(Qt.blue))
                    painter.setPen(QPen(Qt.black, 1))
                    painter.drawEllipse(canvas_point, 5, 5)
        
        # Выводим служебную информацию: режим, количество точек и сегментов
        painter.setPen(QPen(Qt.darkGray))
        mode_text = "РИСОВАНИЕ" if self.mode == "draw" else "РЕДАКТИРОВАНИЕ"
        segments_count = len(self.segments) + 1 if self.points else 0
        painter.drawText(10, 10, f"Режим: {mode_text} | Точки: {len(self.points)} | Сегменты: {segments_count}")


# -----------------------------
# Класс холста для отображения изображения (2 вкладка)
# -----------------------------
class ImageCanvas(QWidget):
    """
    Виджет-холст для второй вкладки, предназначенный для загрузки изображения
    и автоматического распознавания на нем контуров.
    """
    def __init__(self, parent=None):
        """Инициализация холста изображения."""
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(200, 150)

        self.contours: List[List[Point]] = []  # Набор распознанных контуров (после возможного упрощения)
        self.original_contours: List[List[Point]] = []  # Исходные, неупрощенные контуры
        self.original_image = None  # Исходное изображение OpenCV
        self.display_pixmap = None  # QPixmap для отображения загруженного изображения на холсте
        self.image_path = None  # Путь к загруженному файлу изображения
        self.scale = 1.0  # Масштаб для преобразования координат изображения в координаты робота
        self.offset_x = 0  # Смещение по X для центрирования изображения
        self.offset_y = 0  # Смещение по Y для центрирования изображения

    def to_canvas_coords(self, point):
        """Преобразует координаты робота (Point) в координаты холста (QPoint)."""
        return point.to_canvas_coords(self.width(), self.height())

    def load_image(self, image_path):
        """
        Загружает изображение из файла, преобразует его в QPixmap для отображения
        и очищает предыдущие контуры. Возвращает True в случае успеха.
        """
        try:
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                return False
            
            self.image_path = image_path
            
            # Конвертируем OpenCV BGR в RGB QImage
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
        """
        Запускает процесс распознавания контуров на загруженном изображении OpenCV.
        Преобразует найденные контуры в координаты робота.
        Возвращает True в случае успеха.
        """
        if self.original_image is None:
            return False
        
        try:
            img_height, img_width = self.original_image.shape[:2]
            
            # Вычисляем масштаб и смещение, чтобы изображение вписалось в рабочую зону робота (480x360) с небольшим отступом
            scale_x = 460 / img_width
            scale_y = 340 / img_height
            self.scale = min(scale_x, scale_y)
            
            self.offset_x = (480 - img_width * self.scale) / 2 - 240
            self.offset_y = (360 - img_height * self.scale) / 2 - 180
            
            # Подготовка изображения: инверсия, применение порога для бинаризации
            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            img = cv2.bitwise_not(gray)
            _, threshold = cv2.threshold(img, 110, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            self.contours.clear()
            self.original_contours.clear()
            
            for cnt in contours:
                if len(cnt) < 3:  # Слишком маленькие контуры игнорируем
                    continue
                
                # Упрощаем контур, чтобы уменьшить количество точек
                epsilon = 0.001 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                contour_points = []
                n = approx.ravel()  # Преобразуем в плоский массив координат
                
                for i in range(0, len(n), 2):
                    if i + 1 < len(n):
                        x = n[i]
                        y = n[i + 1]
                        
                        # Преобразование координат из пикселей изображения в координаты робота
                        robot_x = x * self.scale + self.offset_x
                        robot_y = -(y * self.scale + self.offset_y)  # Инверсия Y, т.к. у изображения ось Y вниз
                        
                        # Ограничение рабочей областью робота
                        robot_x = max(-240, min(240, robot_x))
                        robot_y = max(-180, min(180, robot_y))
                        
                        contour_points.append(Point(robot_x, robot_y))
                
                if len(contour_points) > 2:
                    # Замыкаем контур, добавляя первую точку в конец
                    contour_points.append(contour_points[0])
                    self.contours.append(contour_points)
                    self.original_contours.append(contour_points[:])  # Сохраняем копию
            
            self.update()
            return True
            
        except Exception as e:
            print(f"Ошибка распознавания контуров: {e}")
            return False

    def simplify_contours(self, epsilon_factor):
        """
        Упрощает контуры с помощью алгоритма Ramer-Douglas-Peucker.
        При epsilon_factor == 0 восстанавливает исходные контуры.
        Возвращает кортеж (успех, исходное_количество_точек, новое_количество_точек).
        """
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
            
            # Преобразуем точки в формат, понятный OpenCV
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
        """Полностью очищает холст изображения и все связанные с ним данные."""
        self.contours.clear()
        self.original_contours.clear()
        self.original_image = None
        self.display_pixmap = None
        self.image_path = None
        self.update()

    def draw_grid(self, painter):
        """
        Рисует координатную сетку и загруженное изображение (если есть)
        в качестве подложки.
        """
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
        
        # Рисуем фоновое изображение, вписанное в рабочую область
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
        
        # Рисуем оси и рамку (аналогично DrawCanvas)
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
        """Главный метод отрисовки ImageCanvas: сетка, изображение и контуры."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        self.draw_grid(painter)
        
        # Набор цветов для разных контуров
        colors = [Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.cyan, Qt.yellow]
        
        for idx, contour in enumerate(self.contours):
            color = colors[idx % len(colors)]
            
            if len(contour) > 1:
                pen = QPen(color, 2)
                painter.setPen(pen)
                # Рисуем линии между точками контура
                for i in range(len(contour) - 1):
                    p1 = self.to_canvas_coords(contour[i])
                    p2 = self.to_canvas_coords(contour[i + 1])
                    painter.drawLine(p1, p2)
            
            # Рисуем точки контура
            for point in contour:
                canvas_point = self.to_canvas_coords(point)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawEllipse(canvas_point, 3, 3)
        
        painter.setPen(QPen(Qt.darkGray))
        painter.drawText(10, 10, f"Контуров: {len(self.contours)}")


# -----------------------------
# Главное окно приложения
# -----------------------------
class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Основной класс приложения, объединяющий все три вкладки
    и управляющий логикой взаимодействия с пользователем.
    """
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # Инициализация UI из файла ui_main.py

        # Применяем базовые стили
        self.setStyleSheet("""
            QPushButton { 
                padding: 4px; 
                min-height: 20px; 
                font-size: 13px; 
            }
        """)
        self.label.setStyleSheet("font-size: 12px; font-weight: bold; color: #333;")
        for btn in self.findChildren(QPushButton):
            btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # По умолчанию открыта первая вкладка
        self.tabWidget.setCurrentIndex(0)

        # --- Инициализация и добавление холстов для первой и второй вкладок ---
        # Холст для первой вкладки (рисование)
        if self.canvasWidget.layout() is None:
            self.canvasWidget.setLayout(QVBoxLayout())
        self.canvas = DrawCanvas()
        self.canvasWidget.layout().addWidget(self.canvas)

        # Холст для второй вкладки (изображение)
        if self.imageWidget.layout() is None:
            self.imageWidget.setLayout(QVBoxLayout())
        self.image_canvas = ImageCanvas()
        self.imageWidget.layout().addWidget(self.image_canvas)
        self.imageWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_canvas.setMinimumSize(400, 300)

        # --- Инициализация виджетов для третьей вкладки (Контурный экстрактор) ---
        self.original_image = None
        self.processed_image = None
        self.image_path = None

        self.original_image_label = QLabel(self.originalImageWidget)
        self.original_image_label.setAlignment(Qt.AlignCenter)
        layout_orig = QVBoxLayout(self.originalImageWidget)
        layout_orig.setContentsMargins(0, 0, 0, 0)
        layout_orig.addWidget(self.original_image_label)

        self.processed_image_label = QLabel(self.processedImageWidget)
        self.processed_image_label.setAlignment(Qt.AlignCenter)
        layout_proc = QVBoxLayout(self.processedImageWidget)
        layout_proc.setContentsMargins(0, 0, 0, 0)
        layout_proc.addWidget(self.processed_image_label)

        # --- Подключение сигналов и слотов ---
        # Третья вкладка
        self.loadImageButton.clicked.connect(self.load_image_contour)
        self.previewButton.clicked.connect(self.preview_processing)
        self.saveResultButton.clicked.connect(self.save_result)
        self.helpButton_3.clicked.connect(self.show_help)
        self.threshold1Slider.valueChanged.connect(self.update_threshold1_label)
        self.threshold2Slider.valueChanged.connect(self.update_threshold2_label)
        self.thresholdValueSlider.valueChanged.connect(self.update_threshold_value_label)
        self.blurSlider.valueChanged.connect(self.update_blur_label)
        self.qualitySlider.valueChanged.connect(self.update_quality_label)
        self.cannyRadio.toggled.connect(self.toggle_method)
        self.thresholdRadio.toggled.connect(self.toggle_method)
        self.blurCheckBox.toggled.connect(self.toggle_blur)
        self.toggle_method()  # Начальное состояние
        self.update_blur_label(5)

        # Вторая вкладка
        self.epsilonSlider.valueChanged.connect(self.update_epsilon_label)
        self.simplifyButton.clicked.connect(self.simplify_image_contours)

        # Первая вкладка
        self.canvas.setFocus()
        self.saveButton.clicked.connect(self.save_points)
        self.clearButton.clicked.connect(self.clear_all_points)
        self.redButton.clicked.connect(self.toggle_edit_mode)
        self.newLineButton.clicked.connect(self.canvas.new_line)
        self.deleteButton.clicked.connect(self.canvas.delete_last_point)
        self.helpButton.clicked.connect(self.show_help)
        self.uploadButton.clicked.connect(self.load_image_with_message)
        self.clearButton_3.clicked.connect(self.clear_image_canvas)
        self.saveButton_3.clicked.connect(self.save_image_coords)
        self.helpButton_2.clicked.connect(self.show_help)

        # Устанавливаем начальный режим и состояние кнопки редактирования
        self.canvas.set_mode("draw")
        self.redButton.setCheckable(True)
        self.redButton.setChecked(False)
        self.first_time_edit = True  # Флаг для показа подсказки при первом входе в режим редактирования

    # -------------------------
    # Методы для упрощения контуров на второй вкладке
    # -------------------------
    def update_epsilon_label(self, value):
        """Обновляет текстовую метку параметра сглаживания (epsilon)."""
        epsilon = value / 1000.0
        self.epsilonValueLabel.setText(f"{epsilon:.3f}")

    def simplify_image_contours(self):
        """Обработчик кнопки упрощения контуров на второй вкладке."""
        if not self.image_canvas.original_contours:
            QMessageBox.warning(self, "Предупреждение", 
                "Нет контуров для упрощения! Сначала загрузите изображение и распознайте контуры.")
            return
        
        epsilon = self.epsilonSlider.value() / 1000.0
        success, original, simplified = self.image_canvas.simplify_contours(epsilon)
        
        if success:
            if epsilon == 0:
                QMessageBox.information(self, "Успех", 
                    f"Контуры восстановлены в исходное состояние!\nВсего точек: {original}")
            else:
                QMessageBox.information(self, "Успех", 
                    f"Контуры упрощены!\nБыло точек: {original}\nСтало точек: {simplified}\nСжатие: {int((1 - simplified/original)*100)}%")
        else:
            QMessageBox.warning(self, "Предупреждение", "Не удалось упростить контуры.")

    # -------------------------
    # Методы для контурного экстрактора (третья вкладка)
    # -------------------------
    def update_threshold1_label(self, value): self.threshold1ValueLabel.setText(str(value))
    def update_threshold2_label(self, value): self.threshold2ValueLabel.setText(str(value))
    def update_threshold_value_label(self, value): self.thresholdValueLabel.setText(str(value))
    def update_blur_label(self, value):
        size = value
        if size % 2 == 0: size += 1; self.blurSlider.setValue(size)
        self.blurValueLabel.setText(str(size))
    def update_quality_label(self, value): self.qualityValueLabel.setText(f"{value}%")
    def toggle_method(self):
        """Переключает видимость панелей настроек между методом Канни и пороговой обработкой."""
        is_canny = self.cannyRadio.isChecked()
        self.cannySettingsFrame.setVisible(is_canny)
        self.thresholdSettingsFrame.setVisible(not is_canny)
    def toggle_blur(self):
        """Включает/выключает ползунок размытия в зависимости от состояния чекбокса."""
        self.blurSlider.setEnabled(self.blurCheckBox.isChecked())

    def load_image_contour(self):
        """Загружает изображение в контурный экстрактор (третья вкладка)."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)")
        if file_path:
            self.image_path = file_path
            self.imageInfoLabel.setText(f"Загрузка: {os.path.basename(file_path)}")
            try:
                self.original_image = cv2.imread(file_path)
                if self.original_image is None: raise ValueError("Не удалось загрузить изображение")
                height, width = self.original_image.shape[:2]
                channels = self.original_image.shape[2] if len(self.original_image.shape) > 2 else 1
                self.imageInfoLabel.setText(f"Размер: {width}×{height} | Каналы: {channels}")
                self.originalImageInfo.setText(f"Размер: {width}×{height}")
                self.display_original_image()
                QMessageBox.information(self, "Успех", f"Изображение загружено: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображение:\n{str(e)}")
                self.imageInfoLabel.setText("Ошибка загрузки")

    def display_original_image(self):
        """Отображает загруженное изображение в виджете originalImageWidget."""
        if self.original_image is not None:
            display_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            h, w, ch = display_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            widget_width = self.originalImageWidget.width()
            widget_height = self.originalImageWidget.height()
            if widget_width > 10 and widget_height > 10:
                scaled_pixmap = pixmap.scaled(widget_width, widget_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.original_image_label.setPixmap(scaled_pixmap)

    def display_processed_image(self, image):
        """Отображает обработанное изображение в виджете processedImageWidget."""
        if image is not None:
            if len(image.shape) == 2: display_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else: display_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = display_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            widget_width = self.processedImageWidget.width()
            widget_height = self.processedImageWidget.height()
            if widget_width > 10 and widget_height > 10:
                scaled_pixmap = pixmap.scaled(widget_width, widget_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.processed_image_label.setPixmap(scaled_pixmap)
            self.processedImageInfo.setText(f"Размер: {w}×{h}")

    def process_image(self):
        """
        Выполняет обработку изображения (размытие, детектор Канни или пороговая обработка).
        Возвращает обработанное изображение OpenCV или None.
        """
        if self.original_image is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите изображение!")
            return None
        try:
            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            if self.blurCheckBox.isChecked():
                blur_size = self.blurSlider.value()
                if blur_size % 2 == 0: blur_size += 1
                blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
            else:
                blurred = gray
            
            if self.cannyRadio.isChecked():
                threshold1 = self.threshold1Slider.value()
                threshold2 = self.threshold2Slider.value()
                edges = cv2.Canny(blurred, threshold1, threshold2)
                result = 255 - edges  # Инвертируем для рисования черным по белому
            else:
                threshold_value = self.thresholdValueSlider.value()
                _, thresh = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                result = np.ones_like(self.original_image) * 255
                cv2.drawContours(result, contours, -1, (0, 0, 0), 2)
            
            self.processed_image = result
            return result
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке изображения:\n{str(e)}")
            return None

    def preview_processing(self):
        """Обработчик кнопки 'Предпросмотр' на третьей вкладке."""
        result = self.process_image()
        if result is not None:
            self.display_processed_image(result)

    def save_result(self):
        """Сохраняет обработанное изображение с контурами в файл."""
        if self.processed_image is None:
            result = self.process_image()
            if result is None: return
        
        format_map = {"jpg": ".jpg", "png": ".png", "bmp": ".bmp", "tiff": ".tiff"}
        selected_format = self.formatComboBox.currentText()
        ext = format_map.get(selected_format, ".jpg")
        default_name = "contours"
        if self.image_path:
            base_name = os.path.splitext(os.path.basename(self.image_path))[0]
            default_name = f"{base_name}_contours"
        
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить результат", default_name, f"{selected_format.upper()} (*{ext})")
        if filename:
            try:
                save_params = []
                quality = self.qualitySlider.value()
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    save_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
                elif filename.lower().endswith('.png'):
                    save_params = [cv2.IMWRITE_PNG_COMPRESSION, 9 - int(quality / 11.1)]
                
                success = cv2.imwrite(filename, self.processed_image, save_params)
                if success: QMessageBox.information(self, "Успех", "Результат успешно сохранен!")
                else: raise Exception("Не удалось сохранить файл")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")

    # -------------------------
    # Методы для первой и второй вкладок (загрузка, очистка, сохранение)
    # -------------------------
    def load_image_with_message(self):
        """Загружает изображение на второю вкладку и запускает распознавание контуров."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)")
        if file_path:
            if self.image_canvas.load_image(file_path):
                QMessageBox.information(self, "Успех", f"Изображение загружено: {os.path.basename(file_path)}")
                if self.image_canvas.detect_contours():
                    QMessageBox.information(self, "Успех", f"Распознано контуров: {len(self.image_canvas.contours)}")
                else:
                    QMessageBox.warning(self, "Предупреждение", "Не удалось распознать контуры")
            else:
                QMessageBox.critical(self, "Ошибка", "Ошибка загрузки изображения")

    def clear_image_canvas(self):
        """Очищает вторую вкладку после подтверждения."""
        reply = QMessageBox.question(self, 'Подтверждение', 'Очистить изображение и контуры?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.image_canvas.clear()
            QMessageBox.information(self, "Успех", "Изображение и контуры очищены")

    def clear_all_points(self):
        """Очищает холст рисования после подтверждения."""
        reply = QMessageBox.question(self, 'Подтверждение', 'Удалить все точки?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.canvas.clear_all()

    def toggle_edit_mode(self):
        """Переключает режим работы холста для рисования между 'draw' и 'edit'."""
        if self.redButton.isChecked():
            self.canvas.set_mode("edit")
            if self.first_time_edit:
                QMessageBox.information(self, "Режим редактирования", "Режим редактирования: перетаскивайте точки, правая кнопка - удалить")
                self.first_time_edit = False
        else:
            self.canvas.set_mode("draw")

    def save_to_file(self, data, total_points, contours_count=None):
        """Сохраняет подготовленные координаты в файл pict_coord.rtf."""
        try:
            filename = "pict_coord.rtf"
            with open(filename, "w", encoding='utf-8', newline='\r\n') as f:
                f.write(f"{total_points}\n")
                for i in range(0, len(data), 2):
                    f.write(f"{data[i]}\n")
                    f.write(f"{data[i+1]}\n")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"❌ Ошибка сохранения: {e}")
            return False

    def save_points(self):
        """Подготавливает и сохраняет координаты точек с первой вкладки (ручное рисование)."""
        if not self.canvas.points:
            QMessageBox.warning(self, "Предупреждение", "Нет точек для сохранения!")
            return
        
        robot_data = []
        segment_indices = sorted(self.canvas.segments)
        current_idx = 0
        all_indices = segment_indices + [len(self.canvas.points)]  # Добавляем конец списка как последний разделитель
        
        for seg_end in all_indices:
            if current_idx < seg_end:
                # Первая точка каждого сегмента помечается кодом PEN_UP_CODE
                first_point = self.canvas.points[current_idx]
                robot_data.append(int(round(first_point.x)) + PEN_UP_CODE)
                robot_data.append(int(round(first_point.y)))
                # Остальные точки сегмента
                for i in range(current_idx + 1, seg_end):
                    point = self.canvas.points[i]
                    robot_data.append(int(round(point.x)))
                    robot_data.append(int(round(point.y)))
                current_idx = seg_end
                
        QMessageBox.information(self, "Успех", f"Точки успешно подготовлены и сохранены!\nВсего точек: {len(self.canvas.points)}")
        return self.save_to_file(robot_data, len(self.canvas.points))

    def save_image_coords(self):
        """Подготавливает и сохраняет координаты контуров со второй вкладки."""
        if not self.image_canvas.contours:
            QMessageBox.warning(self, "Предупреждение", "Нет контуров для сохранения!")
            return
        
        try:
            robot_data = []
            total_points = 0
            for contour in self.image_canvas.contours:
                if len(contour) < 2: continue
                # Первая точка контура - с кодом подъема пера
                first_point = contour[0]
                robot_data.append(int(round(first_point.x)) + PEN_UP_CODE)
                robot_data.append(int(round(first_point.y)))
                total_points += 1
                # Остальные точки контура
                for i in range(1, len(contour)):
                    point = contour[i]
                    robot_data.append(int(round(point.x)))
                    robot_data.append(int(round(point.y)))
                    total_points += 1

            QMessageBox.information(self, "Успех", f"Контуры изображения сохранены!\nЛиний: {len(self.image_canvas.contours)}\nВсего точек: {total_points}")
            return self.save_to_file(robot_data, total_points, len(self.image_canvas.contours))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"❌ Ошибка сохранения: {e}")
            return False

    def show_help(self):
        """Показывает диалоговое окно с общей справкой о программе."""
        help_text = """
        <h2>Программа для управления роботом-художником</h2>
        <h3>Описание программы:</h3>
        <p>Программа позволяет создавать траектории движения для робота-художника путем рисования точек на координатной сетке или преобразования изображений в координаты.</p>
        <h3>Основные функции:</h3>
        <ul>
            <li><b>Вкладка 1:</b> Ручное рисование точек и сегментов, редактирование и перемещение существующих точек.</li>
            <li><b>Вкладка 2:</b> Загрузка изображений и автоматическое распознавание контуров с их последующим упрощением.</li>
            <li><b>Вкладка 3:</b> Контурный экстрактор - выделение контуров на изображениях с помощью алгоритмов Канни или пороговой обработки.</li>
        </ul>
        <p>Сохранение координат происходит в файл pict_coord.rtf для последующей передачи на контроллер EV3.</p>
        <p><i>© 2026 Робот-художник</i></p>    
        """
        QMessageBox.about(self, "О программе", help_text)


# -----------------------------
# Точка входа в приложение
# -----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)  # Создаем экземпляр приложения
    window = MainWindow()  # Создаем главное окно
    window.show()  # Показываем главное окно
    sys.exit(app.exec_())  # Запускаем главный цикл обработки событий