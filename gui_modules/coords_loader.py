# -*- coding: utf-8 -*-
"""
Модуль для загрузки координат робота из файла pict_coord.rtf.
Парсит формат и возвращает списки точек и сегментов для отображения на холсте.
"""

from typing import List, Tuple
from .models import Point
from .config import PEN_UP_CODE


def load_robot_coords(file_path: str) -> Tuple[List[Point], List[int]]:
    """
    Загружает координаты из файла формата робота (.rtf).

    Формат файла:
    <количество_точек>
    <x1>  # Если x1 > 500, то начало сегмента (x1 - 1000 = реальная координата)
    <y1>
    <x2>
    <y2>
    ...

    Returns:
        Tuple[List[Point], List[int]]: Список точек и индексы начала сегментов
    """
    points = []
    segments = []

    with open(file_path, 'r', encoding='utf-8') as f:
        # Читаем заголовок с количеством точек
        header = f.readline().strip()
        try:
            point_count = int(''.join(filter(str.isdigit, header)))
        except ValueError:
            raise ValueError("Неверный формат файла: отсутствует заголовок с количеством точек")

        # Читаем координаты
        for i in range(point_count):
            x_line = f.readline()
            if not x_line:
                break

            x = float(x_line.strip())

            # Проверяем код поднятого пера
            if x > 500:
                segments.append(len(points))  # Запоминаем индекс начала нового сегмента
                x = x - PEN_UP_CODE  # Вычитаем код, получаем реальную координату

            y_line = f.readline()
            if not y_line:
                break

            y = float(y_line.strip())

            # Добавляем точку
            points.append(Point(x, y))

    return points, segments
