# -*- coding: utf-8 -*-
"""
Модуль главного окна приложения.
Объединяет все вкладки и управляет логикой взаимодействия.
"""

import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QMessageBox, QFileDialog, QSizePolicy,
    QPushButton, QVBoxLayout, QDialog
)
from PyQt5.QtCore import Qt
from ui_main import Ui_MainWindow

# --- ДИНАМИЧЕСКИЙ ИМПОРТ ИЗ ПАПКИ ev3-main ДЛЯ PYLANCE ---
# Находим корень проекта (на уровень выше gui_modules)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Путь к папке со скриптами робота
EV3_MAIN_PATH = os.path.join(PROJECT_ROOT, 'ev3-main')

# Добавляем в пути поиска, чтобы среда разработки увидела remote_control.py
if EV3_MAIN_PATH not in sys.path:
    sys.path.insert(0, EV3_MAIN_PATH)

from remote_control import execute_robot_deployment # type: ignore

from .config import load_config, PEN_UP_CODE
from .dialogs import SettingsDialog
from .canvas_draw import DrawCanvas
from .canvas_image import ImageCanvas
from .canvas_contour import ContourExtractor, ImageDisplayWidget

class MainWindow(QMainWindow, Ui_MainWindow):
    """Основной класс приложения."""

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        load_config()

        self.setStyleSheet("""
            QPushButton {
                padding: 4px;
                min-height: 20px;
                font-size: 13px;
            }
        """)
        self.label.setStyleSheet("font-size: 12px; font-weight: bold; color: #333;")

        for btn in self.findChildren(QPushButton):
            btn.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)

        self.tabWidget.setCurrentIndex(0)

        self._setup_tab1()
        self._setup_tab2()
        self._setup_tab3()
        self._connect_signals()

        self.canvas.setFocus()
        self.canvas.set_mode("draw")
        self.redButton.setCheckable(True)
        self.redButton.setChecked(False)

    def _setup_tab1(self):
        """Настройка первой вкладки (ручное рисование)."""
        self.canvas = DrawCanvas(self.tab)
        self.canvas.setObjectName("canvas")
        self.horizontalLayout.addWidget(self.canvas)
        self.canvas.points_changed.connect(self.update_points_info)

    def _setup_tab2(self):
        """Настройка второй вкладки (контуры изображений)."""
        self.image_canvas = ImageCanvas(self.tab_2)
        self.horizontalLayout_2.addWidget(self.image_canvas)

    def _setup_tab3(self):
        """Настройка третьей вкладки (экстрактор контуров)."""
        self.contour_extractor = ContourExtractor()
        self.input_image_widget = ImageDisplayWidget(self.originalImageGroup)
        self.output_image_widget = ImageDisplayWidget(self.processedImageGroup)

        for i in range(self.gridLayout_3.count()):
            item = self.gridLayout_3.itemAt(i)
            if item and item.widget():
                item.widget().hide()

        self.gridLayout_3.addWidget(self.input_image_widget, 0, 0)
        self.gridLayout_3.addWidget(self.output_image_widget, 0, 1)

    def _connect_signals(self):
        """Подключение обработчиков сигналов интерфейса."""
        self.blueButton.clicked.connect(self.set_draw_mode)
        self.redButton.clicked.connect(self.set_edit_mode)
        self.clearButton.clicked.connect(self.clear_canvas)
        self.saveButton.clicked.connect(self.save_draw_points)
        self.settingsButton.clicked.connect(self.open_settings)
        self.helpButton.clicked.connect(self.show_help)

        self.selectImageButton.clicked.connect(self.load_image_tab2)
        self.clearImageButton.clicked.connect(self.clear_tab2)
        self.saveResultButton_2.clicked.connect(self.save_image_contours)
        self.helpButton_2.clicked.connect(self.show_help)

        self.openImageButton.clicked.connect(self.load_image_tab3)
        self.previewButton.clicked.connect(self.process_image_tab3)
        self.saveResultButton.clicked.connect(self.save_processed_image)
        self.helpButton_3.clicked.connect(self.show_help)

        self.blurCheckBox.toggled.connect(self.process_image_tab3)
        self.methodComboBox.currentIndexChanged.connect(self.on_method_changed)
        self.slider1.valueChanged.connect(self.process_image_tab3)
        self.slider2.valueChanged.connect(self.process_image_tab3)

        # Подключение обработчика для кнопки запуска на роботе EV3.
        # Если в ui_main определена кнопка запуска, связываем ее.
        if hasattr(self, 'runEV3Button'):
            self.runEV3Button.clicked.connect(self.run_on_ev3)
        elif hasattr(self, 'pushButton_run'):  # Пример альтернативного имени кнопки
            self.pushButton_run.clicked.connect(self.run_on_ev3)
        else:
            # Если кнопки в UI нет, вы можете привязать ее к любому другому действию,
            # либо она будет вызвана при сохранении
            pass

    def get_secure_app_path(self, filename):
        """Формирует абсолютный путь к файлу внутри папки ev3-main."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_dir = os.path.join(project_root, 'ev3-main')
            
        return os.path.join(target_dir, filename)

    def set_draw_mode(self):
        self.canvas.set_mode("draw")
        self.redButton.setChecked(False)
        self.blueButton.setChecked(True)

    def set_edit_mode(self):
        self.canvas.set_mode("edit")
        self.blueButton.setChecked(False)
        self.redButton.setChecked(True)

    def clear_canvas(self):
        self.canvas.clear()
        self.update_points_info(0, 0)

    def update_points_info(self, total_points, segments_count):
        self.label.setText(f"Точек: {total_points} | Сегментов: {segments_count}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def save_to_file(self, data, count, filename='pict_coord.rtf'):
        """Внутренний метод записи массива координат в файл на ПК."""
        target_path = self.get_secure_app_path(filename)
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(f"{count}\n")
                for i in range(0, len(data), 2):
                    f.write(f"{data[i]}\n")
                    f.write(f"{data[i+1]}\n")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка файловой системы", f"Не удалось записать файл {filename}: {e}")
            return False

    def save_draw_points(self):
        """Сохранение траекторий ручного рисования (Вкладка 1)."""
        if not self.canvas.points:
            QMessageBox.warning(self, "Предупреждение", "Холст пуст! Нет данных для сохранения.")
            return

        try:
            robot_data = []
            total_points = 0
            start_idx = 0

            for seg_idx in self.canvas.segments:
                if seg_idx > start_idx:
                    for i in range(start_idx, seg_idx):
                        pt = self.canvas.points[i]
                        x_val = int(round(pt.x)) + PEN_UP_CODE if i == start_idx else int(round(pt.x))
                        robot_data.append(x_val)
                        robot_data.append(int(round(pt.y)))
                        total_points += 1
                start_idx = seg_idx

            if start_idx < len(self.canvas.points):
                for i in range(start_idx, len(self.canvas.points)):
                    pt = self.canvas.points[i]
                    x_val = int(round(pt.x)) + PEN_UP_CODE if i == start_idx else int(round(pt.x))
                    robot_data.append(x_val)
                    robot_data.append(int(round(pt.y)))
                    total_points += 1

            if self.save_to_file(robot_data, total_points):
                QMessageBox.information(
                    self, "Успех",
                    f"Координаты сохранены в файл pict_coord.rtf!\nВсего точек: {total_points}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка конвертации координат: {e}")

    def load_image_tab2(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "",
            "Изображения (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            success, msg = self.image_canvas.load_image(file_path)
            if success:
                self.label_8.setText(f"Размер: {msg['width']}x{msg['height']}")
                self.horizontalSlider.setValue(50)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображение: {msg}")

    def clear_tab2(self):
        self.image_canvas.clear()
        self.label_8.setText("Размер: -")

    def save_image_contours(self):
        """Сохранение траекторий автоматических контуров (Вкладка 2)."""
        if not self.image_canvas.contours:
            QMessageBox.warning(self, "Предупреждение", "Контуры отсутствуют!")
            return

        try:
            robot_data = []
            total_points = 0

            for contour in self.image_canvas.contours:
                if not contour:
                    continue
                for i, point in enumerate(contour):
                    x_val = int(round(point.x)) + PEN_UP_CODE if i == 0 else int(round(point.x))
                    robot_data.append(x_val)
                    robot_data.append(int(round(point.y)))
                    total_points += 1

            if self.save_to_file(robot_data, total_points):
                QMessageBox.information(
                    self, "Успех",
                    f"Контуры сохранены в pict_coord.rtf!\nЛиний: {len(self.image_canvas.contours)}\nВсего точек: {total_points}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")

    def load_image_tab3(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "",
            "Изображения (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            success, info = self.contour_extractor.load_image(file_path)
            if success:
                self.originalImageInfo.setText(f"Размер: {info['width']}x{info['height']}")
                self.input_image_widget.set_image(self.contour_extractor.original_image)
                self.process_image_tab3()
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить: {info}")

    def on_method_changed(self, index):
        if index == 0:
            self.labelSlider1.setText("Порог 1:")
            self.labelSlider2.setText("Порог 2:")
            self.slider1.setRange(0, 255)
            self.slider2.setRange(0, 255)
            self.slider1.setValue(50)
            self.slider2.setValue(150)
        else:
            self.labelSlider1.setText("Значение порога:")
            self.labelSlider2.setText("Не используется:")
            self.slider1.setRange(0, 255)
            self.slider1.setValue(127)

        self.process_image_tab3()

    def process_image_tab3(self):
        if self.contour_extractor.original_image is None:
            return

        method = 'canny' if self.methodComboBox.currentIndex() == 0 else 'threshold'
        blur = self.blurCheckBox.isChecked()
        val1 = self.slider1.value()
        val2 = self.slider2.value()

        success, msg = self.contour_extractor.process_image(
            method=method, blur_enabled=blur, blur_size=5,
            threshold1=val1, threshold2=val2, threshold_value=val1
        )

        if success:
            self.output_image_widget.set_image(self.contour_extractor.processed_image)
            h, w = self.contour_extractor.processed_image.shape[:2]
            self.processedImageInfo.setText(f"Размер: {w}x{h}")
        else:
            print(f"Ошибка обработки: {msg}")

    def save_processed_image(self):
        if self.contour_extractor.processed_image is None:
            QMessageBox.warning(self, "Предупреждение", "Нет обработанного изображения для сохранения!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить изображение", "result.jpg",
            "Изображения (*.jpg *.png *.bmp)"
        )
        if file_path:
            try:
                import cv2
                cv2.imwrite(file_path, self.contour_extractor.processed_image)
                QMessageBox.information(self, "Успех", "Изображение успешно сохранено на ПК.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def run_on_ev3(self):
        """Слот обработки нажатия кнопки запуска на роботе EV3."""
        # Вызываем функцию развертывания и принудительной перезаписи файлов на роботе
        success, result_message = execute_robot_deployment()
        
        if success:
            QMessageBox.information(self, "Успех развертывания проекта", result_message)
        else:
            QMessageBox.critical(self, "Ошибка удаленного управления", result_message)

    def show_help(self):
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
        QMessageBox.information(self, "Справка", help_text)
