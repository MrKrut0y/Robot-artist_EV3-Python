# -*- coding: utf-8 -*-
"""
Диалоговые окна приложения.
Содержит окно настроек параметров робота (скорость, масштаб).
"""

from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import Qt
from ui_settings import Ui_Dialog
from .config import save_config, get_config


class SettingsDialog(QDialog, Ui_Dialog):
    """Окно настроек: скорость движения, скорость рисования, масштаб."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setModal(True)
        self.setWindowTitle("Настройки робота")

        # Убираем кнопку справки из заголовка окна
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        config = get_config()
        self.spinBox.setValue(config['travel_speed'])
        self.spinBox_2.setValue(config['draw_speed'])
        self.doubleSpinBox.setValue(config['scale'])

        try:
            self.buttonBox.accepted.disconnect()
            self.buttonBox.rejected.disconnect()
        except:
            pass

        self.buttonBox.accepted.connect(self.save_and_accept)
        self.buttonBox.rejected.connect(self.reject)

    def save_and_accept(self):
        """Сохраняет настройки в config.cfg и закрывает окно."""
        travel_speed = self.spinBox.value()
        draw_speed = self.spinBox_2.value()
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
