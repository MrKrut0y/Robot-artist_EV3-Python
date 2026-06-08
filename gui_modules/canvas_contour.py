# -*- coding: utf-8 -*-
"""
Контурный экстрактор (вкладка 3).
Обработка изображений методами Канни и пороговой обработки с выводом результата.
"""

import cv2
import numpy as np
import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


class ContourExtractor:
    """Класс для обработки изображений и извлечения контуров."""

    def __init__(self):
        self.original_image = None
        self.processed_image = None
        self.image_path = None

    def load_image(self, image_path):
        """Загружает изображение из файла."""
        try:
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                return False, "Не удалось загрузить изображение"

            self.image_path = image_path
            height, width = self.original_image.shape[:2]
            channels = self.original_image.shape[2] if len(self.original_image.shape) > 2 else 1

            return True, {
                'width': width,
                'height': height,
                'channels': channels,
                'filename': os.path.basename(image_path)
            }
        except Exception as e:
            return False, str(e)

    def process_image(self, method='canny', blur_enabled=False, blur_size=5,
                     threshold1=50, threshold2=150, threshold_value=127):
        """
        Обрабатывает изображение выбранным методом.

        Args:
            method: 'canny' или 'threshold'
            blur_enabled: применять ли размытие
            blur_size: размер ядра размытия (нечетное число)
            threshold1: нижний порог для Canny
            threshold2: верхний порог для Canny
            threshold_value: значение порога для пороговой обработки
        """
        if self.original_image is None:
            return False, "Изображение не загружено"

        try:
            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)

            if blur_enabled:
                if blur_size % 2 == 0:
                    blur_size += 1
                blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
            else:
                blurred = gray

            if method == 'canny':
                edges = cv2.Canny(blurred, threshold1, threshold2)
                result = 255 - edges
            else:
                _, thresh = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                result = np.ones_like(self.original_image) * 255
                cv2.drawContours(result, contours, -1, (0, 0, 0), 2)

            self.processed_image = result
            return True, result

        except Exception as e:
            return False, str(e)

    def save_image(self, filename, quality=95):
        """Сохраняет обработанное изображение."""
        if self.processed_image is None:
            return False, "Нет обработанного изображения для сохранения"

        try:
            save_params = []
            if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                save_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            elif filename.lower().endswith('.png'):
                save_params = [cv2.IMWRITE_PNG_COMPRESSION, 9 - int(quality / 11.1)]

            success = cv2.imwrite(filename, self.processed_image, save_params)
            if success:
                return True, "Файл успешно сохранен"
            else:
                return False, "Не удалось сохранить файл"

        except Exception as e:
            return False, str(e)

    def get_original_image(self):
        """Возвращает исходное изображение."""
        return self.original_image

    def get_processed_image(self):
        """Возвращает обработанное изображение."""
        return self.processed_image


def cv_image_to_pixmap(cv_image):
    """Преобразует изображение OpenCV в QPixmap."""
    if cv_image is None:
        return None

    if len(cv_image.shape) == 2:
        display_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2RGB)
    else:
        display_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

    h, w, ch = display_image.shape
    bytes_per_line = ch * w
    qt_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qt_image)


class ImageDisplayWidget(QWidget):
    """Виджет для отображения изображения с автоматическим масштабированием."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.pixmap = None

    def set_image(self, cv_image):
        """Устанавливает изображение для отображения."""
        self.pixmap = cv_image_to_pixmap(cv_image)
        self.update_display()

    def update_display(self):
        """Обновляет отображение с учетом размера виджета."""
        if self.pixmap:
            widget_width = self.width()
            widget_height = self.height()
            if widget_width > 10 and widget_height > 10:
                scaled_pixmap = self.pixmap.scaled(
                    widget_width, widget_height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Обработчик изменения размера виджета."""
        super().resizeEvent(event)
        self.update_display()
