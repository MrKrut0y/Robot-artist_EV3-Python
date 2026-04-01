import sys
import os

# Проверка версии Python
if sys.version_info < (3, 10):
    from PyQt5.QtWidgets import QMessageBox, QApplication
    
    app = QApplication(sys.argv)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Ошибка")
    msg.setText("Неподдерживаемая версия Python")
    msg.setInformativeText(
        f"Ваша версия Python: {sys.version_info.major}.{sys.version_info.minor}\n\n"
        "Для работы программы требуется Python 3.10 или выше.\n\n"
        "Пожалуйста, обновите Python:\n"
        "https://www.python.org/downloads/"
    )
    msg.exec_()
    sys.exit(1)
import subprocess
import math
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox, 
    QFileDialog, QSizePolicy
)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QImage, QFont
from PyQt5.QtCore import QPoint
from ui_main import Ui_MainWindow


# Константы для робота-художника
PEN_UP_CODE = 1000


@dataclass
class Point:
    x: float
    y: float
    
    def to_canvas_coords(self, canvas_width: int, canvas_height: int) -> QPoint:
        """Преобразует координаты для отображения на canvas"""
        # Масштабируем координаты под размер виджета
        scale_x = canvas_width / 480  # 480 - ширина рабочей области (-240..240)
        scale_y = canvas_height / 360  # 360 - высота рабочей области (-180..180)
        scale = min(scale_x, scale_y)  # Сохраняем пропорции
        
        # Вычисляем реальные координаты на виджете с учетом масштаба
        canvas_x = int(canvas_width / 2 + self.x * scale)
        canvas_y = int(canvas_height / 2 - self.y * scale)
        
        return QPoint(canvas_x, canvas_y)
    
    @staticmethod
    def from_canvas_coords(pos: QPoint, canvas_width: int, canvas_height: int) -> 'Point':
        """Создает точку из координат канваса"""
        # Масштабируем обратно
        scale_x = canvas_width / 480
        scale_y = canvas_height / 360
        scale = min(scale_x, scale_y)
        
        # Получаем координаты относительно центра с учетом масштаба
        x = (pos.x() - canvas_width / 2) / scale
        y = (canvas_height / 2 - pos.y()) / scale
        
        # Ограничиваем рабочей областью
        x = max(-240, min(240, x))
        y = max(-180, min(180, y))
        
        return Point(x, y)


# -----------------------------
# Класс холста для рисования точек (1 вкладка)
# -----------------------------
class DrawCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(200, 150)

        # Режимы: "draw" (рисование) / "edit" (редактирование)
        self.mode = "draw"
        
        # Данные точек
        self.points: List[Point] = []  # Все точки
        
        # Для отслеживания сегментов (линий)
        self.segments: List[int] = []  # Индексы начала новых сегментов
        
        # Для редактирования
        self.selected_point_index = -1
        self.selected_point = None

    # -------------------------
    # Преобразование координат
    # -------------------------
    def to_model_coords(self, pos):
        return Point.from_canvas_coords(pos, self.width(), self.height())

    def to_canvas_coords(self, point):
        return point.to_canvas_coords(self.width(), self.height())

    # -------------------------
    # Ограничение области
    # -------------------------
    def inside_area(self, x, y):
        return abs(x) <= 240 and abs(y) <= 180

    # -------------------------
    # Переключение режима
    # -------------------------
    def set_mode(self, mode):
        self.mode = mode
        if mode == "draw":
            self.selected_point_index = -1
            self.selected_point = None
        self.update()

    # -------------------------
    # Новая линия (пробел)
    # -------------------------
    def new_line(self):
        if self.points:
            self.segments.append(len(self.points))
        self.update()

    # -------------------------
    # Удаление последней точки (клавиша X)
    # -------------------------
    def delete_last_point(self):
        if self.points:
            self.points.pop()
            
            if len(self.points) in self.segments:
                self.segments.remove(len(self.points))
            
            self.update()

    # -------------------------
    # Очистка всех точек
    # -------------------------
    def clear_all(self):
        self.points.clear()
        self.segments.clear()
        self.selected_point_index = -1
        self.selected_point = None
        self.update()

    # -------------------------
    # Обработка клавиш
    # -------------------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.new_line()
            if hasattr(self.parent(), 'newLineButton'):
                self.parent().newLineButton.animateClick(100)

        if event.key() == Qt.Key_X:
            self.delete_last_point()
            if hasattr(self.parent(), 'deleteButton'):
                self.parent().deleteButton.animateClick(100)

    # -------------------------
    # Поиск ближайшей точки
    # -------------------------
    def find_closest_point(self, pos, max_dist=20):
        closest_idx = -1
        min_dist = max_dist + 1
        
        for i, point in enumerate(self.points):
            canvas_point = self.to_canvas_coords(point)
            dist = math.sqrt((pos.x() - canvas_point.x())**2 + (pos.y() - canvas_point.y())**2)
            
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        
        return closest_idx

    # -------------------------
    # Мышь нажата
    # -------------------------
    def mousePressEvent(self, event):
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

    # -------------------------
    # Движение мыши
    # -------------------------
    def mouseMoveEvent(self, event):
        if self.mode == "edit" and self.selected_point_index >= 0:
            if event.buttons() & Qt.LeftButton:
                new_point = self.to_model_coords(event.pos())
                
                if not self.inside_area(new_point.x, new_point.y):
                    return
                
                self.points[self.selected_point_index] = new_point
                self.selected_point = new_point
                
                self.update()

    # -------------------------
    # Отпускание кнопки
    # -------------------------
    def mouseReleaseEvent(self, event):
        if self.mode == "edit":
            if event.button() == Qt.LeftButton and self.selected_point_index >= 0:
                self.selected_point_index = -1
                self.selected_point = None

    # -------------------------
    # Рисование сетки
    # -------------------------
    def draw_grid(self, painter):
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

    # -------------------------
    # Рисование
    # -------------------------
    def paintEvent(self, event):
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


# -----------------------------
# Класс холста для отображения изображения (2 вкладка)
# -----------------------------
class ImageCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.setMinimumSize(200, 150)

        # Данные для отображения
        self.contours: List[List[Point]] = []  # Список контуров (каждый контур - список точек)
        self.original_image = None  # Исходное изображение (numpy array)
        self.display_pixmap = None  # QPixmap для отображения
        self.image_path = None  # Путь к загруженному изображению
        
        # Для расчета центрирования
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

    # -------------------------
    # Преобразование координат
    # -------------------------
    def to_canvas_coords(self, point):
        return point.to_canvas_coords(self.width(), self.height())

    # -------------------------
    # Загрузка изображения
    # -------------------------
    def load_image(self, image_path):
        try:
            # Загружаем изображение через OpenCV
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                return False
            
            self.image_path = image_path
            
            # Конвертируем для отображения в QPixmap
            rgb_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.display_pixmap = QPixmap.fromImage(qt_image)
            
            self.contours.clear()  # Очищаем старые контуры
            self.update()
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return False

    # -------------------------
    # Распознавание контуров (как в tkinter программе)
    # -------------------------
    def detect_contours(self):
        if self.original_image is None:
            return False
        
        try:
            # Получаем размеры изображения
            img_height, img_width = self.original_image.shape[:2]
            
            # Масштабируем координаты под рабочую область робота (-240..240, -180..180)
            scale_x = 460 / img_width   # 460 для отступа от краев
            scale_y = 340 / img_height  # 340 для отступа от краев
            self.scale = min(scale_x, scale_y)
            
            # Смещение для центрирования
            self.offset_x = (480 - img_width * self.scale) / 2 - 240
            self.offset_y = (360 - img_height * self.scale) / 2 - 180
            
            # Конвертируем в оттенки серого и инвертируем (как в tkinter программе)
            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            img = cv2.bitwise_not(gray)
            
            # Применяем пороговую обработку
            _, threshold = cv2.threshold(img, 110, 255, cv2.THRESH_BINARY)
            
            # Находим контуры
            contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Очищаем старые контуры
            self.contours.clear()
            
            for cnt in contours:
                if len(cnt) < 3:
                    continue
                
                # Аппроксимируем контур
                epsilon = 0.001 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                # Получаем точки контура
                contour_points = []
                n = approx.ravel()
                
                for i in range(0, len(n), 2):
                    if i + 1 < len(n):
                        x = n[i]
                        y = n[i + 1]
                        
                        # Масштабируем координаты
                        robot_x = x * self.scale + self.offset_x
                        robot_y = -(y * self.scale + self.offset_y)  # Инвертируем Y
                        
                        # Ограничиваем рабочей областью
                        robot_x = max(-240, min(240, robot_x))
                        robot_y = max(-180, min(180, robot_y))
                        
                        contour_points.append(Point(robot_x, robot_y))
                
                # Замыкаем контур (добавляем первую точку в конец)
                if len(contour_points) > 2:
                    contour_points.append(contour_points[0])
                    self.contours.append(contour_points)
            
            self.update()
            return True
            
        except Exception as e:
            print(f"Ошибка распознавания контуров: {e}")
            return False

    # -------------------------
    # Очистка
    # -------------------------
    def clear(self):
        self.contours.clear()
        self.original_image = None
        self.display_pixmap = None
        self.image_path = None
        self.update()

    # -------------------------
    # Рисование сетки
    # -------------------------
    def draw_grid(self, painter):
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
        
        # Заливаем фон белым
        painter.fillRect(self.rect(), Qt.white)
        
        # Если есть изображение, отображаем его
        if self.display_pixmap:
            # Масштабируем изображение под рабочую область
            scaled_pixmap = self.display_pixmap.scaled(
                int(480 * scale), int(360 * scale),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            # Рисуем изображение по центру
            painter.drawPixmap(
                int(center_x - scaled_pixmap.width() / 2),
                int(center_y - scaled_pixmap.height() / 2),
                scaled_pixmap
            )
        
        # Рисуем сетку
        pen = QPen(QColor(200, 200, 200), 1, Qt.DashLine)
        painter.setPen(pen)
        
        painter.drawLine(int(center_x), 0, int(center_x), h)
        painter.drawLine(0, int(center_y), w, int(center_y))
        
        # Границы рабочей области
        pen.setColor(Qt.red)
        pen.setWidth(2)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(left, top, int(480 * scale), int(360 * scale))
        
        # Отметки по осям
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

    # -------------------------
    # Рисование
    # -------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Рисуем сетку и изображение
        self.draw_grid(painter)
        
        # Рисуем контуры разными цветами
        colors = [Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.cyan, Qt.yellow]
        
        for idx, contour in enumerate(self.contours):
            color = colors[idx % len(colors)]
            
            # Рисуем линии между точками контура
            if len(contour) > 1:
                pen = QPen(color, 2)
                painter.setPen(pen)
                
                for i in range(len(contour) - 1):
                    p1 = self.to_canvas_coords(contour[i])
                    p2 = self.to_canvas_coords(contour[i + 1])
                    painter.drawLine(p1, p2)
            
            # Рисуем сами точки
            for point in contour:
                canvas_point = self.to_canvas_coords(point)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawEllipse(canvas_point, 3, 3)
        
        # Информация
        painter.setPen(QPen(Qt.darkGray))
        painter.drawText(10, 10, f"Контуров: {len(self.contours)}")


# -----------------------------
# Главное окно
# -----------------------------
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Устанавливаем первую вкладку активной
        self.tabWidget.setCurrentIndex(0)

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

        # Устанавливаем политику размера для холста на второй вкладке
        self.imageWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_canvas.setMinimumSize(400, 300)

        # Устанавливаем фокус на холст для обработки клавиш
        self.canvas.setFocus()

        # Подключение кнопок первой вкладки (включая кнопку справки)
        self.saveButton.clicked.connect(self.save_points)
        self.pushRun.clicked.connect(self.run_ev3_program)
        self.clearButton.clicked.connect(self.clear_all_points)
        self.redButton.clicked.connect(self.toggle_edit_mode)
        self.newLineButton.clicked.connect(self.canvas.new_line)
        self.deleteButton.clicked.connect(self.canvas.delete_last_point)
        self.helpButton.clicked.connect(self.show_help)  # Кнопка справки на первой вкладке

        # Подключение кнопок второй вкладки (включая кнопку справки)
        self.uploadButton.clicked.connect(self.load_image_with_message)
        self.clearButton_3.clicked.connect(self.clear_image_canvas)
        self.saveButton_3.clicked.connect(self.save_image_coords)
        self.helpButton_2.clicked.connect(self.show_help)  # Кнопка справки на второй вкладке

        # Устанавливаем начальный режим
        self.canvas.set_mode("draw")
        
        # Делаем кнопку редактирования переключаемой
        self.redButton.setCheckable(True)
        self.redButton.setChecked(False)
        
        # Переменная для отслеживания первого переключения
        self.first_time_edit = True

    # -------------------------
    # Загрузка изображения с сообщением
    # -------------------------
    def load_image_with_message(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            if self.image_canvas.load_image(file_path):
                QMessageBox.information(self, "Успех", 
                    f"Изображение загружено: {os.path.basename(file_path)}")
                if self.image_canvas.detect_contours():
                    QMessageBox.information(self, "Успех", 
                        f"Распознано контуров: {len(self.image_canvas.contours)}")
                else:
                    QMessageBox.warning(self, "Предупреждение", "Не удалось распознать контуры")
            else:
                QMessageBox.critical(self, "Ошибка", "Ошибка загрузки изображения")

    # -------------------------
    # Очистка холста на второй вкладке
    # -------------------------
    def clear_image_canvas(self):
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Очистить изображение и контуры?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.image_canvas.clear()
            QMessageBox.information(self, "Успех", "Изображение и контуры очищены")

    # -------------------------
    # Очистка всех точек на первой вкладке
    # -------------------------
    def clear_all_points(self):
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Удалить все точки?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.canvas.clear_all()

    # -------------------------
    # Переключение режима редактирования
    # -------------------------
    def toggle_edit_mode(self):
        if self.redButton.isChecked():
            self.canvas.set_mode("edit")
            if self.first_time_edit:
                QMessageBox.information(self, "Режим редактирования", 
                    "Режим редактирования: перетаскивайте точки, правая кнопка - удалить")
                self.first_time_edit = False
        else:
            self.canvas.set_mode("draw")

    # -------------------------
    # Сохранение точек в формате для робота (общий метод)
    # -------------------------
    def save_to_file(self, data, total_points, contours_count=None):
        """Сохраняет данные в файл pict_coord.rtf с кодировкой UTF-8 и CRLF"""
        try:
            filename = "pict_coord.rtf"
            with open(filename, "w", encoding='utf-8', newline='\r\n') as f:
                f.write(f"{total_points}\n")
                for i in range(0, len(data), 2):
                    f.write(f"{data[i]}\n")
                    f.write(f"{data[i+1]}\n")
            
            if contours_count is not None:
                QMessageBox.information(self, "Успех", 
                    f"✔ Координаты сохранены в {filename}\nВсего точек: {total_points}\nКонтуров: {contours_count}")
            else:
                segments_count = len(self.canvas.segments) + 1 if self.canvas.points else 0
                QMessageBox.information(self, "Успех", 
                    f"✔ Координаты сохранены в {filename}\nВсего точек: {total_points}\nСегментов: {segments_count}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"❌ Ошибка сохранения: {e}")

    # -------------------------
    # Сохранение точек с первой вкладки
    # -------------------------
    def save_points(self):
        if not self.canvas.points:
            QMessageBox.warning(self, "Предупреждение", "Нет точек для сохранения!")
            return
        
        # Формируем данные для робота
        robot_data = []
        segment_indices = sorted(self.canvas.segments)
        
        current_idx = 0
        for seg_idx in segment_indices:
            if current_idx < seg_idx:
                # Первая точка сегмента с PEN_UP_CODE
                first_point = self.canvas.points[current_idx]
                robot_x = -first_point.y
                robot_y = first_point.x
                robot_data.append(int(round(robot_x)) + PEN_UP_CODE)
                robot_data.append(int(round(robot_y)))
                
                # Остальные точки сегмента
                for i in range(current_idx + 1, seg_idx):
                    point = self.canvas.points[i]
                    robot_x = -point.y
                    robot_y = point.x
                    robot_data.append(int(round(robot_x)))
                    robot_data.append(int(round(robot_y)))
                
                current_idx = seg_idx
        
        # Последний сегмент
        if current_idx < len(self.canvas.points):
            first_point = self.canvas.points[current_idx]
            robot_x = -first_point.y
            robot_y = first_point.x
            robot_data.append(int(round(robot_x)) + PEN_UP_CODE)
            robot_data.append(int(round(robot_y)))
            
            for i in range(current_idx + 1, len(self.canvas.points)):
                point = self.canvas.points[i]
                robot_x = -point.y
                robot_y = point.x
                robot_data.append(int(round(robot_x)))
                robot_data.append(int(round(robot_y)))
        
        # Сохраняем в файл
        self.save_to_file(robot_data, len(self.canvas.points))

    # -------------------------
    # Сохранение координат с изображения (как в tkinter программе)
    # -------------------------
    def save_image_coords(self):
        if not self.image_canvas.contours:
            QMessageBox.warning(self, "Предупреждение", "Нет контуров для сохранения!")
            return
        
        try:
            # Собираем все точки контуров в формате для робота
            robot_data = []
            total_points = 0
            
            for contour in self.image_canvas.contours:
                if len(contour) < 2:
                    continue
                
                # Первая точка контура с PEN_UP_CODE
                first_point = contour[0]
                robot_x = -first_point.y
                robot_y = first_point.x
                robot_data.append(int(round(robot_x)) + PEN_UP_CODE)
                robot_data.append(int(round(robot_y)))
                total_points += 1
                
                # Остальные точки контура
                for i in range(1, len(contour)):
                    point = contour[i]
                    robot_x = -point.y
                    robot_y = point.x
                    robot_data.append(int(round(robot_x)))
                    robot_data.append(int(round(robot_y)))
                    total_points += 1
            
            # Сохраняем в файл
            self.save_to_file(robot_data, total_points, len(self.image_canvas.contours))
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"❌ Ошибка сохранения: {e}")

    # -------------------------
    # Показать справку
    # -------------------------
    def show_help(self):
        """Показывает справку о программе"""
        help_text = """
        <h2>Программа для управления роботом-художником</h2>
                
        <h3>Описание программы:</h3>
        <p>Программа позволяет создавать траектории движения для робота-художника путем
    рисования точек на координатной сетке или преобразования изображений в координаты.</p>
        
        <h3>Основные функции:</h3>
        <ul>
            <li>Рисование точек на холсте с координатной сеткой</li>
            <li>Создание отдельных сегментов (линий) из точек</li>
            <li>Редактирование и перемещение существующих точек</li>
            <li>Загрузка изображений и автоматическое распознавание контуров</li>
            <li>Сохранение координат в файл для передачи на робота</li>
            <li>Запуск программы на EV3 через pybricksdev</li>
        </ul>
        
        <h3>Управление:</h3>
        <ul>
            <li>Левая кнопка мыши: добавить точку</li>
            <li>Правая кнопка мыши: удалить ближайшую точку</li>
            <li>Пробел: начать новый сегмент</li>
            <li>X: удалить последнюю точку</li>
            <li>Режим редактирования: перетаскивание точек</li>
        </ul>
        
        <h3>Подключение EV3 к компьютеру:</h3>
        <ol>
            <li>Подготовить microSD карту с прошивкой EV3 MicroPython</li>
            <li>Вставить microSD карту в EV3</li>
            <li>Включить EV3</li>
            <li>Подключить EV3 к компьютеру через mini-USB кабель</li>
            <li>Дождаться пока EV3 загрузится</li>
        </ol>
        
        <p><b>Важно:</b> После этого программа сможет отправлять код на EV3 и запускать его. 
        Если EV3 не подключён к компьютеру, запуск программы на роботе будет невозможен.</p>
        
        <p><i>© 2026 Робот-художник</i></p>    
        """
        
        QMessageBox.about(self, "О программе", help_text)

    # -------------------------
    # Запуск EV3
    # -------------------------
    def run_ev3_program(self):
        try:
            # Определяем директорию, где находится EXE файл
            if getattr(sys, 'frozen', False):
                # Запуск из скомпилированного EXE
                base_dir = os.path.dirname(sys.executable)
            else:
                # Запуск из исходного кода
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            main_file = os.path.join(base_dir, "main.py")
            
            # Проверяем существование файла
            if not os.path.exists(main_file):
                QMessageBox.critical(self, "Ошибка", 
                    f"Файл main.py не найден!\n\n"
                    f"Убедитесь, что файл main.py находится в той же папке, что и программа:\n{base_dir}")
                return
            
            # Пробуем разные варианты команды
            commands = [
                ["pybricksdev", "run", "usb", main_file],
                ["pybricksdev", "run", "--connection-type", "usb", main_file],
                ["pybricksdev", "run", main_file, "--connection-type", "usb"],
            ]
            
            success = False
            last_error = ""
            
            for cmd in commands:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    # Если команда выполнилась успешно или дала какой-то вывод
                    if result.returncode == 0 or result.stdout or result.stderr:
                        output_text = ""
                        if result.stdout:
                            output_text += f"STDOUT:\n{result.stdout}\n"
                        if result.stderr:
                            output_text += f"STDERR:\n{result.stderr}\n"
                        
                        if result.returncode == 0:
                            QMessageBox.information(self, "Успех", 
                                f"Программа успешно запущена на EV3\n\n{output_text}")
                        else:
                            QMessageBox.warning(self, "Предупреждение", 
                                f"Программа завершилась с кодом {result.returncode}\n\n{output_text}")
                        
                        success = True
                        break
                        
                except Exception as e:
                    last_error = str(e)
                    continue
            
            if not success:
                # Если ни одна команда не сработала, показываем информацию по установке
                error_msg = (
                    "Не удалось запустить программу на EV3.\n\n"
                    "Возможные причины:\n"
                    "1. EV3 не подключен к компьютеру\n"
                    "2. Не установлен pybricksdev\n"
                    "3. Неправильная версия pybricksdev\n\n"
                    "Установка pybricksdev:\n"
                    "pip install pybricksdev\n\n"
                    "Проверка подключения EV3:\n"
                    "pybricksdev usb list\n"
                )
                
                if last_error:
                    error_msg += f"\nПоследняя ошибка: {last_error}"
                
                QMessageBox.critical(self, "Ошибка подключения", error_msg)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка запуска: {str(e)}")

# -----------------------------
# Запуск приложения
# -----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())