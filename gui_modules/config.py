# -*- coding: utf-8 -*-
"""
Модуль для работы с конфигурацией робота.
Управляет глобальными параметрами: масштаб, скорости движения и рисования.
"""

import os

# Глобальные переменные конфигурации робота (значения по умолчанию)
SCALE = 1.3
DRAW_SPEED = 800
TRAVEL_SPEED = 800

# Специальный код для координат X первой точки каждого сегмента
PEN_UP_CODE = 1000


def save_config(scale, draw_speed, travel_speed, filename='config.cfg'):
    """
    Сохраняет конфигурацию в файл.
    Возвращает True при успехе, False при ошибке.
    """
    global SCALE, DRAW_SPEED, TRAVEL_SPEED

    SCALE = scale
    DRAW_SPEED = draw_speed
    TRAVEL_SPEED = travel_speed

    try:
        ev3_dir = os.path.join(os.path.dirname(__file__), '..', 'ev3-main')
        filepath = os.path.join(ev3_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"SCALE={SCALE}\n")
            f.write(f"DRAW_SPEED={DRAW_SPEED}\n")
            f.write(f"TRAVEL_SPEED={TRAVEL_SPEED}\n")
        return True
    except Exception as e:
        print(f"Ошибка записи config.cfg: {e}")
        return False


def get_config():
    """Возвращает текущие значения конфигурации."""
    return {
        'scale': SCALE,
        'draw_speed': DRAW_SPEED,
        'travel_speed': TRAVEL_SPEED
    }
