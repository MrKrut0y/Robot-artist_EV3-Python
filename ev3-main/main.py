#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import math

ev3 = EV3Brick()

# Путь к изолированной рабочей директории проекта на EV3
REMOTE_DIR = '/home/robot/plotter/'

# Параметры движения и масштабирования по умолчанию
SCALE = 1.3
DRAW_SPEED = 500
TRAVEL_SPEED = 500

def load_config(filename='config.cfg'):
    # Парсинг файла конфигурации и обновление глобальных параметров
    global SCALE, DRAW_SPEED, TRAVEL_SPEED
    config_path = REMOTE_DIR + filename
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.find('SCALE=') == 0:
                    SCALE = float(line.split('=')[1])
                elif line.find('DRAW_SPEED=') == 0:
                    DRAW_SPEED = int(line.split('=')[1])
                elif line.find('TRAVEL_SPEED=') == 0:
                    TRAVEL_SPEED = int(line.split('=')[1])
        return True
    except Exception:
        return False # Сброс на дефолтные настройки при ошибке чтения

# Инициализация периферии: моторы подвеса (A, B) и маркер (C)
motorA = Motor(Port.A)
motorB = Motor(Port.B)
motorC = Motor(Port.C)

last_disp_x = 0
last_disp_y = 0

def update_display(pen_down, x, y):
    # Отрисовка текущего вектора на LCD-экране блока EV3
    global last_disp_x, last_disp_y
    x_scaled = round((x + 240) * 0.37)
    y_scaled = round((180 - y) * 0.35)
    
    if pen_down:
        ev3.screen.draw_line(last_disp_x, last_disp_y, x_scaled, y_scaled)
    
    last_disp_x = x_scaled
    last_disp_y = y_scaled

def calculate_angles(x, y):
    # Обратная кинематика V-plotter: расчет углов моторов по координатам (X, Y)
    current_scale = 0.83333333 * SCALE
    x_real = current_scale * x
    y_real = (current_scale * y) + 280
    
    # Расчет длин нитей подвеса от моторов до каретки
    lenA = math.sqrt((241 + x_real)**2 + (614 - y_real)**2)
    lenB = math.sqrt((241 - x_real)**2 + (614 - y_real)**2)
    
    # Перевод линейного расстояния в градусы энкодеров
    angle_A = (660 - lenA) * 18.48
    angle_B = (660 - lenB) * 18.48
    
    return angle_A, angle_B

def sync_move(target_A, target_B, speed):
    # Расчет пропорциональных скоростей для линейного перемещения в точку
    curr_A = motorA.angle()
    curr_B = motorB.angle()
    
    rel_A = target_A - curr_A
    rel_B = target_B - curr_B
    abs_A, abs_B = abs(rel_A), abs(rel_B)
    
    if abs_A >= abs_B and abs_A != 0:
        speed_A = speed
        speed_B = speed * (abs_B / abs_A)
    elif abs_B > abs_A:
        speed_B = speed
        speed_A = speed * (abs_A / abs_B)
    else:
        speed_A = speed_B = speed

    # Одновременный запуск моторов с ожиданием завершения движения
    motorA.run_angle(speed_A, rel_A, wait=False)
    motorB.run_angle(speed_B, rel_B, wait=True)

# Подготовка экрана и звуковой сигнал готовности
ev3.screen.clear()
ev3.speaker.beep()

if load_config('config.cfg'):
    ev3.screen.print("Config loaded")
    ev3.screen.print("SCALE:", SCALE)
    wait(2000)
else:
    ev3.screen.print("Using defaults")
    wait(2000)

ev3.screen.clear()
wait(1000)

# Фиксация текущего положения робота как нулевой точки отсчета
motorA.reset_angle(0)
motorB.reset_angle(0)
motorC.reset_angle(0)

coords_path = REMOTE_DIR + 'pict_coord.rtf'

try:
    with open(coords_path, 'r') as f:
        header = f.readline()
        
        # Фильтрация и извлечение количества точек из заголовка rtf
        digits = [char for char in header if char in '0123456789']
        try:
            points_count = int(''.join(digits))
        except Exception:
            points_count = 0
        
        # Цикл обработки и выполнения траектории по точкам
        for _ in range(points_count):
            line_x = f.readline()
            if not line_x: 
                break
            raw_x = float(line_x.strip())
            
            # Проверка флага холостого хода (смещение координаты X)
            if raw_x > 500:
                x = raw_x - 1000
                is_pen_up_move = True
            else:
                x = raw_x
                is_pen_up_move = False
            
            line_y = f.readline()
            if not line_y: 
                break
            y = float(line_y.strip())
            
            tgt_A, tgt_B = calculate_angles(x, y)
            
            if is_pen_up_move:
                motorC.run_target(TRAVEL_SPEED, 0)     # Подъем маркера
                sync_move(tgt_A, tgt_B, speed=TRAVEL_SPEED) # Переход к новой линии
                motorC.run_target(TRAVEL_SPEED, 180)   # Опускание маркера
            else:
                sync_move(tgt_A, tgt_B, speed=DRAW_SPEED)   # Отрисовка вектора
                
            update_display(not is_pen_up_move, x, y)

except Exception as e:
    ev3.screen.print("Error:", e)
    wait(5000)

# Завершение работы: подъем пера и автоматический возврат «домой»
motorC.run_target(TRAVEL_SPEED, 0)

home_A, home_B = calculate_angles(0, 0)
sync_move(home_A, home_B, speed=TRAVEL_SPEED) 

# Полное снятие натяжения нитей подвеса
motorA.run_target(TRAVEL_SPEED, 0, wait=False)
motorB.run_target(TRAVEL_SPEED, 0, wait=True)

ev3.speaker.beep()
