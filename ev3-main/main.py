#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import math
import os

# ==============================================================================
# ИНИЦИАЛИЗАЦИЯ И ГЛОБАЛЬНЫЕ НАСТРОЙКИ
# ==============================================================================

# Инициализация интеллектуального блока EV3
ev3 = EV3Brick()

# Автоматическое определение рабочей директории скрипта для относительных путей файлов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Масштабирование рисунка: 1.0 — исходный размер, 1.3 — увеличение на 30%
SCALE = 1.3

# Скорость вращения моторов при рисовании (опущенный маркер), град/сек
DRAW_SPEED = 500

# Скорость перемещения при холостом ходе (поднятый маркер), град/сек
TRAVEL_SPEED = 500

# Координаты последней отрисованной точки на экране EV3 (для непрерывности линий)
last_disp_x = 0
last_disp_y = 0


# ==============================================================================
# СЕРВИСНЫЕ ФУНКЦИИ И РАБОТА С ФАЙЛАМИ
# ==============================================================================

def load_config(filename='config.cfg'):
    """
    Загружает динамические настройки конфигурации из текстового файла.
    
    Ищет файл конфигурации в той же папке, что и запущенный скрипт. 
    Если файл отсутствует или поврежден, сохраняются значения по умолчанию.
    
    Args:
        filename (str): Имя файла конфигурации. По умолчанию 'config.cfg'.
    Returns:
        bool: True, если конфигурация успешно загружена, иначе False.
    """
    global SCALE, DRAW_SPEED, TRAVEL_SPEED
    config_path = os.path.join(BASE_DIR, filename)
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('SCALE='):
                    SCALE = float(line.split('=')[1])
                elif line.startswith('DRAW_SPEED='):
                    DRAW_SPEED = int(line.split('=')[1])
                elif line.startswith('TRAVEL_SPEED='):
                    TRAVEL_SPEED = int(line.split('=')[1])
        return True
    except IOError:
        # В случае отсутствия файла проект продолжит работу на дефолтных параметрах
        return False


def update_display(pen_down, x, y):
    """
    Отображает процесс рисования на экране EV3 в реальном времени.
    
    Масштабирует декартовы координаты под разрешение экрана кубика EV3 (178x128).
    
    Args:
        pen_down (bool): Статус пера (True — рисует линию, False — холостой ход).
        x (float): Текущая координата X на холсте.
        y (float): Текущая координата Y на холсте.
    """
    global last_disp_x, last_disp_y
    
    # Формулы эмпирического масштабирования под физический экран EV3
    x_scaled = round((x + 240) * 0.37)
    y_scaled = round((180 - y) * 0.35)
    
    # Отрисовка линии производится только при опущенном маркере
    if pen_down:
        ev3.screen.draw_line(last_disp_x, last_disp_y, x_scaled, y_scaled)
    
    # Обновление базовой точки для следующего шага
    last_disp_x = x_scaled
    last_disp_y = y_scaled


# ==============================================================================
# КИНЕМАТИКА И УПРАВЛЕНИЕ ДВИЖЕНИЕМ
# ==============================================================================

def calculate_angles(x, y):
    """
    Обратная кинематика для V-plotter систем (двухниточный подвес).
    
    Преобразует целевые декартовы координаты (X, Y) в требуемые углы 
    поворота левого и правого моторов натяжения нитей.
    
    Args:
        x (float): Целевая координата X.
        y (float): Целевая координата Y.
    Returns:
        tuple: (angle_A, angle_B) — целевые углы для энкодеров моторов в градусах.
    """
    # Расчет результирующего масштаба с учетом базового коэффициента системы
    current_scale = 0.83333333 * SCALE
  
    x_real = current_scale * x
    y_real = (current_scale * y) + 280  # +280 мм — базовый отступ вниз от оси моторов
    
    # Расчет требуемой длины нитей по теореме Пифагора:
    # 241 мм — расстояние от центра холста до подвеса мотора по горизонтали
    # 614 мм — константа вертикального смещения базового расчета геометрии станины
    lenA = math.sqrt((241 + x_real)**2 + (614 - y_real)**2)
    lenB = math.sqrt((241 - x_real)**2 + (614 - y_real)**2)
    
    # Конвертация изменения длины нитей (из стартовых 660 мм) в градусы вала энкодера.
    # Коэффициент 18.48 учитывает передаточное число редуктора и диаметр шпули (20мм)
    angle_A = (660 - lenA) * 18.48
    angle_B = (660 - lenB) * 18.48
    
    return angle_A, angle_B


def sync_move(target_A, target_B, speed):
    """
    Синхронизирует движение двух ведущих моторов для получения строго прямой линии.
    
    Рассчитывает пропорциональное распределение скоростей (интерполяцию), 
    чтобы оба мотора одновременно завершали вращение в целевой точке.
    
    Args:
        target_A (float): Целевой угол для левого мотора (Port A).
        target_B (float): Целевой угол для правого мотора (Port B).
        speed (int): Базовая максимальная скорость перемещения.
    """
    curr_A = motorA.angle()
    curr_B = motorB.angle()
    
    # Расчет относительного перемещения (дельта)
    rel_A = target_A - curr_A
    rel_B = target_B - curr_B
    
    abs_A, abs_B = abs(rel_A), abs(rel_B)
    
    # Линейная интерполяция скоростей
    if abs_A >= abs_B and abs_A != 0:
        speed_A = speed
        speed_B = speed * (abs_B / abs_A)
    elif abs_B > abs_A:
        speed_B = speed
        speed_A = speed * (abs_A / abs_B)
    else:
        speed_A = speed_B = speed

    # Асинхронный запуск первого мотора и блокирующий запуск второго для синхронизации
    motorA.run_angle(speed_A, rel_A, wait=False)
    motorB.run_angle(speed_B, rel_B, wait=True)


# ==============================================================================
# ИНИЦИАЛИЗАЦИЯ ЖЕЛЕЗА И ПОДГОТОВКА СТЕНДА
# ==============================================================================

# Конфигурация портов исполнительных механизмов
motorA = Motor(Port.A)   # Левый шаговый мотор (управление натяжением левой нити)
motorB = Motor(Port.B)   # Правый шаговый мотор (управление натяжением правой нити)
motorC = Motor(Port.C)   # Вспомогательный мотор (сервопривод подъема/опускания маркера)

# Сброс и очистка периферии перед стартом
ev3.screen.clear()
ev3.speaker.beep()  # Сигнал готовности системы к чтению конфигурации

# Попытка загрузки файла настроек
if load_config('config.cfg'):
    ev3.screen.print("Config loaded")
    ev3.screen.print("SCALE:", SCALE)
    wait(2000)
else:
    ev3.screen.print("Using defaults")
    wait(2000)

ev3.screen.clear()
wait(1000)

# Принятие текущего физического положения робота (натяжения нитей) за нулевую точку отсчета
motorA.reset_angle(0)
motorB.reset_angle(0)
motorC.reset_angle(0)

# Формирование пути к файлу базы данных координат рисунка
coords_path = os.path.join(BASE_DIR, 'pict_coord.rtf')

# ==============================================================================
# ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ И ОТРИСОВКИ РИСУНКА
# ==============================================================================

try:
    with open(coords_path, 'r') as f:
        # Парсинг заголовка файла для извлечения общего количества точек парсинга
        header = f.readline()
        try:
            points_count = int(''.join(filter(str.isdigit, header)))
        except ValueError:
            points_count = 0
        
        # Пошаговая обработка массива векторов
        for _ in range(points_count):
            line_x = f.readline()
            if not line_x: break
            raw_x = float(line_x.strip())
            
            # Логическое ветвление: распознавание триггера "холостого прыжка" (X > 500)
            if raw_x > 500:
                x = raw_x - 1000
                is_pen_up_move = True  # Маркер должен быть поднят (перемещение без рисования)
            else:
                x = raw_x
                is_pen_up_move = False # Обычный вектор непрерывной линии рисования
            
            line_y = f.readline()
            if not line_y: break
            y = float(line_y.strip())
            
            # Вычисление целевой позиции моторов для текущей итерации координат
            tgt_A, tgt_B = calculate_angles(x, y)
            
            # Алгоритмическая обработка перемещений:
            if is_pen_up_move:
                # Сценарий "Холостой ход": поднимаем маркер, едем на travel-скорости, опускаем маркер
                motorC.run_target(TRAVEL_SPEED, 0)
                sync_move(tgt_A, tgt_B, speed=TRAVEL_SPEED)
                motorC.run_target(TRAVEL_SPEED, 180) # Возврат маркера в рабочее положение на холсте
            else:
                # Сценарий "Отрисовка": линейное интерполированное движение на draw-скорости
                sync_move(tgt_A, tgt_B, speed=DRAW_SPEED)
                
            # Динамическое обновление миниатюры хода выполнения на LCD-дисплее кубика
            update_display(not is_pen_up_move, x, y)

except Exception as e:
    # Защитный блок: вывод ошибок парсинга или механики на экран робота
    ev3.screen.print("Error:", e)
    wait(5000)

# ==============================================================================
# ЗАВЕРШЕНИЕ СЕССИИ И ВОЗВРАТ В ДЕПО
# ==============================================================================

# Безопасный подъем маркера для предотвращения порчи рисунка при возврате
motorC.run_target(TRAVEL_SPEED, 0)

# Расчет траектории и возвращение каретки в программный центр (0, 0)
home_A, home_B = calculate_angles(0, 0)
sync_move(home_A, home_B, speed=TRAVEL_SPEED) 

# Физический возврат моторов в исходное нулевое состояние (ослабление нитей для снятия каретки)
motorA.run_target(TRAVEL_SPEED, 0, wait=False)
motorB.run_target(TRAVEL_SPEED, 0, wait=True)

# Финальный звуковой сигнал об успешном окончании сессии рисования
ev3.speaker.beep()
