#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, TouchSensor, ColorSensor,
                                 InfraredSensor, UltrasonicSensor, GyroSensor)
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile, ImageFile
import math

# Инициализация контроллера и периферии
ev3 = EV3Brick()

# Конфигурация моторов
motorA = Motor(Port.A)   # Левая нить
motorB = Motor(Port.B)   # Правая нить
motorC = Motor(Port.C)   # Подъем/опускание пера

# Глобальные переменные для отрисовки пути на экране EV3
last_disp_x = 0
last_disp_y = 0

def update_display(pen_down, x_scratch, y_scratch): 
    global last_disp_x, last_disp_y
    x_scaled = round((x_scratch + 240) * 0.37)
    y_scaled = round((180 - y_scratch) * 0.35)
    
    if pen_down:
        ev3.screen.draw_line(last_disp_x, last_disp_y, x_scaled, y_scaled)
    
    last_disp_x = x_scaled
    last_disp_y = y_scaled

def calculate_angles(x_scratch, y_scratch):
    # ИСПРАВЛЕНИЕ 1: Прямое соответствие осей без поворота на 90 градусов!
    # (Мы убрали перекрестные умножения, которые были в Scratch)
    x_real = 0.83333333 * x_scratch
    y_real = 0.83333333 * y_scratch + 280
    
    # Расчет длин нитей L1 и L2 по теореме Пифагора
    lenA = math.sqrt((241 + x_real)**2 + (614 - y_real)**2)
    lenB = math.sqrt((241 - x_real)**2 + (614 - y_real)**2)
    
    # Перевод изменения длины в градусы мотора
    angle_A = (660 - lenA) * 18.48
    angle_B = (660 - lenB) * 18.48
    
    return angle_A, angle_B

def sync_move(target_A, target_B, speed): 
    curr_A = motorA.angle()
    curr_B = motorB.angle()
    
    rel_A = target_A - curr_A
    rel_B = target_B - curr_B
    
    abs_A, abs_B = abs(rel_A), abs(rel_B)
    
    # Рассчитываем пропорциональные скорости
    if abs_A >= abs_B and abs_A != 0:
        speed_A = speed
        speed_B = speed * (abs_B / abs_A)
    elif abs_B > abs_A:
        speed_B = speed
        speed_A = speed * (abs_A / abs_B)
    else:
        speed_A = speed_B = speed

    motorA.run_angle(speed_A, rel_A, wait=False)
    motorB.run_angle(speed_B, rel_B, wait=True)

ev3.screen.clear()
ev3.speaker.beep()
wait(1000)

# Сброс энкодеров в стартовой точке
motorA.reset_angle(0)
motorB.reset_angle(0)
motorC.reset_angle(0)

try:
    with open('pict_coord.rtf', 'r') as f:
        # Читаем первую строку (количество точек)
        header = f.readline()
        try:
            # ИСПРАВЛЕНИЕ 2: Убрали "- 1". Теперь считываются все точки до конца!
            points_count = int(''.join(filter(str.isdigit, header)))
        except:
            points_count = 0

        for _ in range(points_count):
            line_x = f.readline()
            if not line_x: break
            raw_x = float(line_x.strip())
            
            # Проверяем флаг поднятого пера
            if raw_x > 500:
                x_scratch = raw_x - 1000
                is_pen_up_move = True  # Это прыжок к новой линии
            else:
                x_scratch = raw_x
                is_pen_up_move = False # Это обычная точка линии
            
            line_y = f.readline()
            if not line_y: break
            y_scratch = float(line_y.strip())
            
            # 1. Считаем углы для новой точки
            tgt_A, tgt_B = calculate_angles(x_scratch, y_scratch)
            
            # 2. ЕСЛИ ЭТО ПРЫЖОК: сначала поднимаем перо, потом едем
            if is_pen_up_move:
                motorC.run_target(300, 0) # Поднять
                sync_move(tgt_A, tgt_B, speed=300)
                motorC.run_target(300, 180) # Опустить ПРИЕХАВ в начало новой линии
            
            # 3. ЕСЛИ ЭТО ПРОДОЛЖЕНИЕ ЛИНИИ: просто едем (перо уже внизу)
            else:
                sync_move(tgt_A, tgt_B, speed=500)
                
            # Обновляем миниатюру на экране
            update_display(not is_pen_up_move, x_scratch, y_scratch)

except Exception as e:
    ev3.screen.print("Error:", e)
    wait(5000)

motorC.run_target(300, 0) # Поднять перо в конце

# Возврат в физический "дом" (0,0)
home_A, home_B = calculate_angles(0, 0)
# ИСПРАВЛЕНИЕ 3: Снизили скорость до 300, чтобы не было бешеных рывков в конце
sync_move(home_A, home_B, speed=500) 

ev3.speaker.beep()
