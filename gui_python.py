#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа GUI-приложения робота-художника.

Запуск: python gui_python.py

Модули:
  gui_modules/config.py       — конфигурация (масштаб, скорости)
  gui_modules/models.py       — модель Point
  gui_modules/dialogs.py      — диалог настроек робота
  gui_modules/canvas_draw.py  — холст ручного рисования (вкладка 1)
  gui_modules/canvas_image.py — холст изображений (вкладка 2)
  gui_modules/canvas_contour.py — контурный экстрактор (вкладка 3)
  gui_modules/main_window.py  — главное окно
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
