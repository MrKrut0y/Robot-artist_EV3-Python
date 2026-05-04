#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, TouchSensor, ColorSensor,
                                 InfraredSensor, UltrasonicSensor, GyroSensor)
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile, ImageFile
import math

from ev3_bluetooth import EV3_Bluetooth
MACADDRESS = '10:B1:DF:5F:2C:FA'

ev3 = EV3Brick()

motorA = Motor(Port.A)   # Левая нить
motorB = Motor(Port.B)   # Правая нить
motorC = Motor(Port.C)   # Подъем/опускание пера

ev = EV3_Bluetooth(MACADDRESS)
ev3.speaker.beep()