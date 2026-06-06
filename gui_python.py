#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Программа для управления роботом-художником EV3.

Основные возможности:
1. Ручное рисование траекторий точками
2. Автоматическое распознавание контуров из изображений
3. Контурный экстрактор с методами Канни и пороговой обработки
4. Настройка параметров робота (скорость, масштаб)
5. Экспорт координат в формат для EV3

Структура модулей:
- gui_modules/config.py - управление конфигурацией
- gui_modules/models.py - базовые модели данных
- gui_modules/dialogs.py - диалоговые окна
- gui_modules/canvas_draw.py - холст для ручного рисования
- gui_modules/canvas_image.py - холст для работы с изображениями
- gui_modules/canvas_contour.py - контурный экстрактор
- gui_modules/main_window.py - главное окно приложения
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui_modules.main_window import MainWindow


def main():
    """Точка входа в приложение."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
