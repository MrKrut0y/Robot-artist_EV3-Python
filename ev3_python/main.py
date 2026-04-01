#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

import math

# -------------------------
# ИНИЦИАЛИЗАЦИЯ
# -------------------------

ev3 = EV3Brick()

motorA = Motor(Port.A)   # левая нить
motorB = Motor(Port.B)   # правая нить
motorC = Motor(Port.C)   # перо

# -------------------------
# КОНСТАНТЫ РОБОТА
# -------------------------

B = 150        # половина расстояния между подвесами
H = 460        # высота подвесов
Lmax = 660     # максимальная длина нити

MM_TO_DEG = 18.48

PEN_UP_CODE = 1000

# -------------------------
# ПЕРО
# -------------------------

def pen_up():
    motorC.run_angle(300, 90)
    wait(300)

def pen_down():
    motorC.run_angle(300, -90)
    wait(300)

# -------------------------
# КИНЕМАТИКА
# -------------------------

def coord_to_angles(x, y):
    L1 = math.sqrt((B + x)**2 + (H - y)**2)
    L2 = math.sqrt((B - x)**2 + (H - y)**2)

    angleA = (Lmax - L1) * MM_TO_DEG
    angleB = (Lmax - L2) * MM_TO_DEG

    return angleA, angleB

# -------------------------
# ДВИЖЕНИЕ
# -------------------------

def move_to(x, y):
    angleA, angleB = coord_to_angles(x, y)
    
    motorA.run_target(300, angleA, wait=False)
    motorB.run_target(300, angleB)
    
    wait(100)  # Небольшая пауза для завершения движения

# -------------------------
# ЧТЕНИЕ ФАЙЛА
# -------------------------

def load_points():
    points = []
    
    try:
        with open("pict_coord.rtf", "r", encoding='utf-8') as f:
            # Читаем количество точек, игнорируя пустые строки
            line = f.readline().strip()
            while line == "":
                line = f.readline().strip()
            
            count = int(line)
            
            for i in range(count):
                x_line = f.readline().strip()
                while x_line == "":
                    x_line = f.readline().strip()
                
                y_line = f.readline().strip()
                while y_line == "":
                    y_line = f.readline().strip()
                
                if not x_line or not y_line:
                    break
                    
                x = int(x_line)
                y = int(y_line)
                points.append((x, y))
                
        ev3.screen.print(f"Loaded {len(points)} points")
                
    except FileNotFoundError:
        ev3.screen.print("File not found!")
        return []
    except ValueError as e:
        ev3.screen.print(f"Invalid data: {e}")
        return []
    except Exception as e:
        ev3.screen.print(f"Error: {e}")
        return []
    
    return points

# -------------------------
# РИСОВАНИЕ
# -------------------------

def draw():
    points = load_points()
    
    if not points:
        ev3.screen.print("No points to draw")
        return
    
    pen_is_down = False
    point_count = 0
    
    for x, y in points:
        point_count += 1
        ev3.screen.print(f"Point {point_count}")
        
        if x >= PEN_UP_CODE:
            x = x - PEN_UP_CODE
            
            if pen_is_down:
                pen_up()
                pen_is_down = False
            
            move_to(x, y)
            
            pen_down()
            pen_is_down = True
            
        else:
            if not pen_is_down:
                pen_down()
                pen_is_down = True
            
            move_to(x, y)
        
        wait(100)  # Небольшая пауза между точками

# -------------------------
# ГЛАВНАЯ ПРОГРАММА
# -------------------------

ev3.screen.clear()
ev3.screen.print("Robot artist")
ev3.screen.print("Loading...")

# Начальная позиция
pen_up()
move_to(0, 0)

# Рисование
draw()

# Завершение
pen_up()
move_to(0, 0)

ev3.speaker.beep()
ev3.screen.clear()
ev3.screen.print("Done!")