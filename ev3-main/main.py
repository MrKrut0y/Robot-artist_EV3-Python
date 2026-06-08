#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import math

ev3 = EV3Brick()

# Путь к изолированной рабочей директории проекта на EV3
REMOTE_DIR = '/home/robot/plotter/'

# Глобальный коэффициент масштабирования рисунка
# 1.0 - оригинальный размер, 1.3 - увеличение на 30%
SCALE = 1.3

# Скорость рисования (движение с опущенным пером)
DRAW_SPEED = 800

# Скорость перемещения (движение с поднятым пером и возврат домой)
TRAVEL_SPEED = 800

def load_config(filename='config.cfg'):
    # Загружает конфигурацию из файла
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
        # Если файл не найден или ошибка чтения - используем значения по умолчанию
        return False

# Конфигурация моторов
motorA = Motor(Port.A)   # Левая нить
motorB = Motor(Port.B)   # Правая нить
motorC = Motor(Port.C)   # Подъем/опускание пера

last_disp_x = 0
last_disp_y = 0

def update_display(pen_down, x, y):
    # Отображает процесс рисования на экране EV3 в реальном времени.
    global last_disp_x, last_disp_y
    x_scaled = round((x + 240) * 0.37)
    y_scaled = round((180 - y) * 0.35)
    
    if pen_down:
        ev3.screen.draw_line(last_disp_x, last_disp_y, x_scaled, y_scaled)
    
    last_disp_x = x_scaled
    last_disp_y = y_scaled

def calculate_angles(x, y):

    # Преобразует декартовы координаты (X, Y) в углы поворота моторов.
    # Использует обратную кинематику для V-plotter систем.
    
    # Масштабирование координат
    current_scale = 0.83333333 * SCALE
    x_real = current_scale * x
    y_real = (current_scale * y) + 280 # +280 - базовый отступ вниз от оси моторов
    
    # Расчет длин нитей подвеса от моторов до каретки
    lenA = math.sqrt((241 + x_real)**2 + (614 - y_real)**2)
    lenB = math.sqrt((241 - x_real)**2 + (614 - y_real)**2)
    
    # Конвертация длины нити в градусы энкодера (вал 20мм)
    # Коэффициент 18.48 учитывает передаточное число и диаметр вала
    angle_A = (660 - lenA) * 18.48
    angle_B = (660 - lenB) * 18.48
    
    return angle_A, angle_B

def sync_move(target_A, target_B, speed):

    # Синхронизирует движение двух моторов для получения прямой линии.
    
    curr_A = motorA.angle()
    curr_B = motorB.angle()
    
    rel_A = target_A - curr_A
    rel_B = target_B - curr_B

    abs_A, abs_B = abs(rel_A), abs(rel_B)
    
    # Расчет скоростей для одновременного прибытия моторов в точку
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
wait(1000)

# Принимаем текущую позицию за нулевую точку отсчета
motorA.reset_angle(0)
motorB.reset_angle(0)
motorC.reset_angle(0)

coords_path = REMOTE_DIR + 'pict_coord.rtf'

try:
    with open(coords_path, 'r') as f:
        # Чтение заголовка с количеством точек
        header = f.readline()
        try:
            points_count = int(''.join(filter(str.isdigit, header)))
        except:
            points_count = 0
        
        # Основной цикл обработки координат
        for _ in range(points_count):
            line_x = f.readline()
            if not line_x: break
            raw_x = float(line_x.strip())
            
            # Распознавание кода "поднятого пера" (> 500)
            if raw_x > 500:
                x = raw_x - 1000
                is_pen_up_move = True  # Это прыжок к новой линии
            else:
                x = raw_x
                is_pen_up_move = False # Это обычная точка линии
            
            line_y = f.readline()
            if not line_y: break
            y = float(line_y.strip())
            
            # 1. Считаем углы для новой точки
            tgt_A, tgt_B = calculate_angles(x, y)
            
            # 2. ЕСЛИ ЭТО ПРЫЖОК: сначала поднимаем перо, потом едем
            if is_pen_up_move:
                motorC.run_target(TRAVEL_SPEED, 0)     # Подъем маркера
                sync_move(tgt_A, tgt_B, speed=TRAVEL_SPEED) # Переход к новой линии
                motorC.run_target(TRAVEL_SPEED, 180)  # Опустить маркер ПРИЕХАВ в начало новой линии
            
            # 3. ЕСЛИ ЭТО ПРОДОЛЖЕНИЕ ЛИНИИ: просто едем (перо уже внизу)
            else:
                # Обычное рисование линии
                sync_move(tgt_A, tgt_B, speed=DRAW_SPEED)
                
            # Обновляем миниатюру на экране
            update_display(not is_pen_up_move, x, y)

# Оповещение ошибки
except Exception as e:
    ev3.screen.print("Error:", e)
    ev3.speaker.beep()
    ev3.speaker.beep()
    ev3.speaker.beep()
    wait(5000)

# --- Завершение работы ---
motorC.run_target(TRAVEL_SPEED, 0) # Поднять перо в конце

# Возврат в центр и плавный спуск в исходную точку
home_A, home_B = calculate_angles(0, 0)
sync_move(home_A, home_B, speed=TRAVEL_SPEED) 

# Полное снятие натяжения нитей подвеса
motorA.run_target(TRAVEL_SPEED, 0, wait=False)
motorB.run_target(TRAVEL_SPEED, 0, wait=True)

ev3.speaker.beep()
