#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для удаленного взаимодействия с роботом LEGO EV3 по протоколу SSH/SFTP.
"""

import os
import time
import paramiko

# Параметры авторизации в операционной системе ev3dev
HOSTNAME = 'ev3dev.local'
USERNAME = 'robot'
PASSWORD = 'maker'

# Локальные имена файлов на ПК
LOCAL_MAIN = 'main.py'
LOCAL_COORDS = 'pict_coord.rtf'
LOCAL_CONFIG = 'config.cfg'

# Директории и пути на целевом устройстве EV3
REMOTE_DIR = '/home/robot/plotter'
REMOTE_SCRIPT_PATH = '/home/robot/plotter/main.py'


def get_secure_local_path(filename):
    """
    Формирует абсолютный путь к файлу на ПК.
    Так как скрипт уже находится в ev3-main, берем его родную директорию.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, filename)


def check_local_resources():
    """Проверяет физическое наличие необходимых файлов на ПК в папке ev3-main."""
    path_main = get_secure_local_path(LOCAL_MAIN)
    path_coords = get_secure_local_path(LOCAL_COORDS)

    if not os.path.exists(path_main):
        return False, f"Ошибка: Главная программа робота '{LOCAL_MAIN}' не найдена по пути: {path_main}"
    if not os.path.exists(path_coords):
        return False, f"Ошибка: Файл координат рисунка '{LOCAL_COORDS}' не найден по пути: {path_coords}"
    
    return True, "Все локальные файлы успешно верифицированы."


def execute_robot_deployment():
    """Синхронизирует файлы из ev3-main и запускает робота."""
    files_ok, message = check_local_resources()
    if not files_ok:
        return False, message

    local_main_path = get_secure_local_path(LOCAL_MAIN)
    local_coords_path = get_secure_local_path(LOCAL_COORDS)
    local_config_path = get_secure_local_path(LOCAL_CONFIG)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    #log_messages = ["Установка беспроводного соединения с EV3..."]
    log_messages = [""]
    
    try:
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        log_messages.append("Успешно подключено к операционной системе робота.")
        
        ssh.exec_command(f'mkdir -p {REMOTE_DIR}')
        
        sftp = ssh.open_sftp()
        
        #log_messages.append(f"Синхронизация программы: {LOCAL_MAIN}")
        sftp.put(local_main_path, REMOTE_SCRIPT_PATH)
        sftp.chmod(REMOTE_SCRIPT_PATH, 0o755)
        
        remote_coords_dest = f'{REMOTE_DIR}/{LOCAL_COORDS}'
        #log_messages.append(f"Синхронизация координат холста: {LOCAL_COORDS}")
        sftp.put(local_coords_path, remote_coords_dest)
        
        if os.path.exists(local_config_path):
            remote_config_dest = f'{REMOTE_DIR}/{LOCAL_CONFIG}'
            #log_messages.append(f"Синхронизация файла конфигурации: {LOCAL_CONFIG}")
            sftp.put(local_config_path, remote_config_dest)
        else:
            log_messages.append("Файл настроек отсутствует. Будут применены параметры по умолчанию.")
            
        sftp.close()
        log_messages.append("Все файлы проекта успешно перезаписаны в память робота.")
        
        ssh.exec_command(f'chmod +x {REMOTE_SCRIPT_PATH}')
        
        #log_messages.append("Отправка команды на автономный запуск рисования...")
        run_command = f"bash -c 'nohup brickrun -r -- pybricks-micropython {REMOTE_SCRIPT_PATH} > /dev/null 2>&1 & disown'"
        
        chan = ssh.invoke_shell()
        chan.send(run_command + '\n')
        time.sleep(1.5)
        chan.close()
        
        log_messages.append("\nРобот успешно принял файлы из директории ev3-main и приступил к выполнению.")
        return True, "\n".join(log_messages)
        
    except Exception as error:
        return False, f"Произошла критическая ошибка сетевого взаимодействия:\n{str(error)}"
    finally:
        ssh.close()