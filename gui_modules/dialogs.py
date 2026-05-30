# -*- coding: utf-8 -*-
"""
Модуль диалоговых окон.
Содержит окно настроек робота.
"""

from PyQt5.QtWidgets import QDialog, QMessageBox
from ui_settings import Ui_Dialog
from .config import save_config, get_config


class SettingsDialog(QDialog, Ui_Dialog):
    """Диалоговое окно настроек параметров робота."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setModal(True)
        self.setWindowTitle("Настройки робота")

        # Загружаем текущие значения конфигурации
        config = get_config()
        # spinBox = Скорость движения (TRAVEL_SPEED)
        self.spinBox.setValue(config['travel_speed'])
        # spinBox_2 = Скорость рисования (DRAW_SPEED)
        self.spinBox_2.setValue(config['draw_speed'])
        # doubleSpinBox = Масштаб рисунка (SCALE)
        self.doubleSpinBox.setValue(config['scale'])

        # Отключаем автоматические соединения из ui_settings.py
        try:
            self.buttonBox.accepted.disconnect()
            self.buttonBox.rejected.disconnect()
        except:
            pass

        # Привязываем наши обработчики
        self.buttonBox.accepted.connect(self.save_and_accept)
        self.buttonBox.rejected.connect(self.reject)

    def save_and_accept(self):
        """Сохраняет конфигурацию и закрывает окно."""
        # spinBox = Скорость движения (TRAVEL_SPEED)
        travel_speed = self.spinBox.value()
        # spinBox_2 = Скорость рисования (DRAW_SPEED)
        draw_speed = self.spinBox_2.value()
        # doubleSpinBox = Масштаб рисунка (SCALE)
        scale = self.doubleSpinBox.value()

        if save_config(scale, draw_speed, travel_speed):
            QMessageBox.information(
                self,
                "Успех",
                "Конфигурация успешно сохранена в config.cfg!\n"
                "Файл будет использован роботом EV3."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось сохранить файл конфигурации."
            )
