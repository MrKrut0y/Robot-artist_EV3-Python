# -*- coding: utf-8 -*-
"""
Базовые модели данных.
Класс Point — координата в системе робота (-240..240, -180..180).
"""

from dataclasses import dataclass
from PyQt5.QtCore import QPoint


@dataclass
class Point:
    """Класс для хранения координат точки в системе робота."""
    x: float
    y: float

    def to_canvas_coords(self, canvas_width: int, canvas_height: int) -> QPoint:
        """
        Преобразует координаты робота в координаты виджета QPoint.
        Центр холста соответствует точке (0,0) робота.
        """
        scale_x = canvas_width / 480
        scale_y = canvas_height / 360
        scale = min(scale_x, scale_y)

        canvas_x = int(canvas_width / 2 + self.x * scale)
        canvas_y = int(canvas_height / 2 - self.y * scale)

        return QPoint(canvas_x, canvas_y)

    @staticmethod
    def from_canvas_coords(pos: QPoint, canvas_width: int, canvas_height: int) -> 'Point':
        """Преобразует координаты точки на холсте обратно в координаты робота."""
        scale_x = canvas_width / 480
        scale_y = canvas_height / 360
        scale = min(scale_x, scale_y)

        x = (pos.x() - canvas_width / 2) / scale
        y = (canvas_height / 2 - pos.y()) / scale

        x = max(-240, min(240, x))
        y = max(-180, min(180, y))

        return Point(x, y)
