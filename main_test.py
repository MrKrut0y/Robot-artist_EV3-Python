#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

# -----------------------------
# Инициализация
# -----------------------------

ev3 = EV3Brick()

motor_A = Motor(Port.A)
motor_B = Motor(Port.B)
motor_C = Motor(Port.C)  # перо

# -----------------------------
# Тестовая программа
# -----------------------------

ev3.screen.print("Program started")

ev3.speaker.beep()

# поднять перо
motor_C.run_angle(200, 90)

wait(1000)

# тестовое движение
motor_A.run_angle(200, 180)
motor_B.run_angle(200, 180)

wait(1000)

# опустить перо
motor_C.run_angle(200, -90)

ev3.speaker.beep()

ev3.screen.print("Program finished")