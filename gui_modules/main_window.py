# -*- coding: utf-8 -*-
"""
Модуль главного окна приложения.
Объединяет все вкладки и управляет логикой взаимодействия.
"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QMessageBox, QFileDialog, QSizePolicy,
    QPushButton, QVBoxLayout, QDialog
)
from PyQt5.QtCore import Qt
from ui_main import Ui_MainWindow
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
        self.first_time_edit = True

    def _setup_tab1(self):
        """Инициализация первой вкладки (ручное рисование)."""
        if self.canvasWidget.layout() is None:
            self.canvasWidget.setLayout(QVBoxLayout())
        self.canvas = DrawCanvas()
        self.canvasWidget.layout().addWidget(self.canvas)

    def _setup_tab2(self):
        """Инициализация второй вкладки (изображения)."""
        if self.imageWidget.layout() is None:
            self.imageWidget.setLayout(QVBoxLayout())
        self.image_canvas = ImageCanvas()
        self.imageWidget.layout().addWidget(self.image_canvas)
        self.imageWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_canvas.setMinimumSize(400, 300)

    def _setup_tab3(self):
        """Инициализация третьей вкладки (контурный экстрактор)."""
        self.contour_extractor = ContourExtractor()

        self.original_display = ImageDisplayWidget(self.originalImageWidget)
        layout_orig = QVBoxLayout(self.originalImageWidget)
        layout_orig.setContentsMargins(0, 0, 0, 0)
        layout_orig.addWidget(self.original_display)

        self.processed_display = ImageDisplayWidget(self.processedImageWidget)
        layout_proc = QVBoxLayout(self.processedImageWidget)
        layout_proc.setContentsMargins(0, 0, 0, 0)
        layout_proc.addWidget(self.processed_display)

    def _connect_signals(self):
        """Подключение всех сигналов и слотов."""
        # Кнопка "Настройки робота" (pushButton в ui_main.py)
        if hasattr(self, 'pushButton'):
            self.pushButton.clicked.connect(self.open_settings)

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
        self.epsilonSlider.valueChanged.connect(self.update_epsilon_label)
        self.simplifyButton.clicked.connect(self.simplify_image_contours)

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
        self.toggle_method()
        self.update_blur_label(5)

    def open_settings(self):
        """Открывает окно настроек робота."""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def update_epsilon_label(self, value):
        epsilon = value / 1000.0
        self.epsilonValueLabel.setText(f"{epsilon:.3f}")

    def simplify_image_contours(self):
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

    def update_threshold1_label(self, value): self.threshold1ValueLabel.setText(str(value))
    def update_threshold2_label(self, value): self.threshold2ValueLabel.setText(str(value))
    def update_threshold_value_label(self, value): self.thresholdValueLabel.setText(str(value))

    def update_blur_label(self, value):
        size = value
        if size % 2 == 0:
            size += 1
            self.blurSlider.setValue(size)
        self.blurValueLabel.setText(str(size))

    def update_quality_label(self, value): self.qualityValueLabel.setText(f"{value}%")

    def toggle_method(self):
        is_canny = self.cannyRadio.isChecked()
        self.cannySettingsFrame.setVisible(is_canny)
        self.thresholdSettingsFrame.setVisible(not is_canny)

    def toggle_blur(self):
        self.blurSlider.setEnabled(self.blurCheckBox.isChecked())

    def load_image_contour(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            success, result = self.contour_extractor.load_image(file_path)
            if success:
                self.imageInfoLabel.setText(
                    f"Размер: {result['width']}×{result['height']} | Каналы: {result['channels']}"
                )
                self.originalImageInfo.setText(f"Размер: {result['width']}×{result['height']}")
                self.original_display.set_image(self.contour_extractor.get_original_image())
                QMessageBox.information(self, "Успех", f"Изображение загружено: {result['filename']}")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображение:\n{result}")
                self.imageInfoLabel.setText("Ошибка загрузки")

    def preview_processing(self):
        method = 'canny' if self.cannyRadio.isChecked() else 'threshold'
        success, result = self.contour_extractor.process_image(
            method=method,
            blur_enabled=self.blurCheckBox.isChecked(),
            blur_size=self.blurSlider.value(),
            threshold1=self.threshold1Slider.value(),
            threshold2=self.threshold2Slider.value(),
            threshold_value=self.thresholdValueSlider.value()
        )

        if success:
            self.processed_display.set_image(result)
            h, w = result.shape[:2] if len(result.shape) == 2 else result.shape[:2]
            self.processedImageInfo.setText(f"Размер: {w}×{h}")
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке:\n{result}")

    def save_result(self):
        if self.contour_extractor.get_processed_image() is None:
            self.preview_processing()
            if self.contour_extractor.get_processed_image() is None:
                return

        format_map = {"jpg": ".jpg", "png": ".png", "bmp": ".bmp", "tiff": ".tiff"}
        selected_format = self.formatComboBox.currentText()
        ext = format_map.get(selected_format, ".jpg")
        default_name = "contours"

        if self.contour_extractor.image_path:
            base_name = os.path.splitext(os.path.basename(self.contour_extractor.image_path))[0]
            default_name = f"{base_name}_contours"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результат", default_name,
            f"{selected_format.upper()} (*{ext})"
        )

        if filename:
            quality = self.qualitySlider.value()
            success, message = self.contour_extractor.save_image(filename, quality)
            if success:
                QMessageBox.information(self, "Успех", "Результат успешно сохранен!")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{message}")

    def load_image_with_message(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
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
        reply = QMessageBox.question(
            self, 'Подтверждение', 'Очистить изображение и контуры?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.image_canvas.clear()
            QMessageBox.information(self, "Успех", "Изображение и контуры очищены")

    def clear_all_points(self):
        reply = QMessageBox.question(
            self, 'Подтверждение', 'Удалить все точки?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.canvas.clear_all()

    def toggle_edit_mode(self):
        if self.redButton.isChecked():
            self.canvas.set_mode("edit")
            if self.first_time_edit:
                QMessageBox.information(
                    self, "Режим редактирования",
                    "Режим редактирования: перетаскивайте точки, правая кнопка - удалить"
                )
                self.first_time_edit = False
        else:
            self.canvas.set_mode("draw")

    def save_to_file(self, data, total_points):
        """Сохраняет координаты в файл pict_coord.rtf."""
        try:
            filename = "pict_coord.rtf"
            with open(filename, "w", encoding='utf-8', newline='\r\n') as f:
                f.write(f"{total_points}\n")
                for i in range(0, len(data), 2):
                    f.write(f"{data[i]}\n")
                    f.write(f"{data[i+1]}\n")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")
            return False

    def save_points(self):
        """Сохраняет точки с первой вкладки."""
        if not self.canvas.points:
            QMessageBox.warning(self, "Предупреждение", "Нет точек для сохранения!")
            return

        robot_data = []
        segment_indices = sorted(self.canvas.segments)
        current_idx = 0
        all_indices = segment_indices + [len(self.canvas.points)]

        for seg_end in all_indices:
            if current_idx < seg_end:
                first_point = self.canvas.points[current_idx]
                robot_data.append(int(round(first_point.x)) + PEN_UP_CODE)
                robot_data.append(int(round(first_point.y)))
                for i in range(current_idx + 1, seg_end):
                    point = self.canvas.points[i]
                    robot_data.append(int(round(point.x)))
                    robot_data.append(int(round(point.y)))
                current_idx = seg_end

        if self.save_to_file(robot_data, len(self.canvas.points)):
            QMessageBox.information(
                self, "Успех",
                f"Точки успешно сохранены в pict_coord.rtf!\nВсего точек: {len(self.canvas.points)}"
            )

    def save_image_coords(self):
        """Сохраняет контуры со второй вкладки."""
        if not self.image_canvas.contours:
            QMessageBox.warning(self, "Предупреждение", "Нет контуров для сохранения!")
            return

        try:
            robot_data = []
            total_points = 0
            for contour in self.image_canvas.contours:
                if len(contour) < 2:
                    continue
                first_point = contour[0]
                robot_data.append(int(round(first_point.x)) + PEN_UP_CODE)
                robot_data.append(int(round(first_point.y)))
                total_points += 1
                for i in range(1, len(contour)):
                    point = contour[i]
                    robot_data.append(int(round(point.x)))
                    robot_data.append(int(round(point.y)))
                    total_points += 1

            if self.save_to_file(robot_data, total_points):
                QMessageBox.information(
                    self, "Успех",
                    f"Контуры сохранены в pict_coord.rtf!\nЛиний: {len(self.image_canvas.contours)}\nВсего точек: {total_points}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")

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
        QMessageBox.about(self, "О программе", help_text)
