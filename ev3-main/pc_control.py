#!/usr/bin/env python3
"""
Robot-Artist EV3: PC Remote Control & Automation Script (Force Overwrite Version)

Этот скрипт запускается на ПК. Он принудительно перезаписывает все файлы проекта 
(main.py, config.cfg, pict_coord.rtf) в папке робота без каких-либо проверок,
после чего запускает программу рисования в автономном фоновом режиме.
"""

import os
import sys
import time
import paramiko

# ==============================================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ И ПУТИ К ФАЙЛАМ
# ==============================================================================

HOSTNAME = 'ev3dev.local'
USERNAME = 'robot'
PASSWORD = 'maker'

# Локальные файлы на ПК (должны лежать в одной папке со скриптом)
LOCAL_MAIN = 'main.py'
LOCAL_COORDS = 'pict_coord.rtf'
LOCAL_CONFIG = 'config.cfg'

# Удаленные пути на роботе EV3
REMOTE_DIR = '/home/robot/plotter'
REMOTE_SCRIPT_PATH = '/home/robot/plotter/main.py'


def check_local_files():
    """Проверяет наличие обязательных файлов на ПК перед отправкой."""
    if not os.path.exists(LOCAL_MAIN):
        print(f"❌ Ошибка: Главная программа '{LOCAL_MAIN}' не найдена в папке на ПК!")
        sys.exit(1)
    if not os.path.exists(LOCAL_COORDS):
        print(f"❌ Ошибка: Файл координат рисунка '{LOCAL_COORDS}' не найден в папке на ПК!")
        sys.exit(1)


def main():
    """Алгоритм полной принудительной перезаписи данных и запуска."""
    check_local_files()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("==============================================================================")
    print(f"🔗 Установка беспроводного соединения с EV3 ({HOSTNAME})...")
    print("==============================================================================")
    
    try:
        # 1. Подключение к роботу по Bluetooth PAN
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("✅ Успешно подключено к операционной системе робота!")
        
        # Гарантируем наличие директории на роботе
        ssh.exec_command(f'mkdir -p {REMOTE_DIR}')
        
        # 2. Инициализация SFTP-сессии
        print("📦 Открытие SFTP-сессии для полной перезаписи папки plotter...")
        sftp = ssh.open_sftp()
        
        # Шаг А: Принудительная заливка main.py
        print(f"   -> Перезапись программы: {LOCAL_MAIN} -> {REMOTE_SCRIPT_PATH}")
        sftp.put(LOCAL_MAIN, REMOTE_SCRIPT_PATH)
        sftp.chmod(REMOTE_SCRIPT_PATH, 0o755)  # Сразу даем права на исполнение (rwxr-xr-x)
        
        # Шаг Б: Принудительная заливка координат холста
        remote_coords_path = f'{REMOTE_DIR}/{LOCAL_COORDS}'
        print(f"   -> Перезапись координат: {LOCAL_COORDS} -> {remote_coords_path}")
        sftp.put(LOCAL_COORDS, remote_coords_path)
        
        # Шаг В: Принудительная заливка настроек конфигурации (если есть на ПК)
        if os.path.exists(LOCAL_CONFIG):
            remote_config_path = f'{REMOTE_DIR}/{LOCAL_CONFIG}'
            print(f"   -> Перезапись настроек: {LOCAL_CONFIG} -> {remote_config_path}")
            sftp.put(LOCAL_CONFIG, remote_config_path)
        else:
            print(f"   -> Файл '{LOCAL_CONFIG}' отсутствует на ПК. Настройки робота не изменятся.")
            
        sftp.close()
        print("✅ Все файлы успешно перезаписаны внутри робота!")
        
        # 3. Страховочное закрепление прав на исполнение через SSH-команду
        ssh.exec_command(f'chmod +x {REMOTE_SCRIPT_PATH}')
        
        # 4. Удаленный фоновый запуск через shell-канал
        print("\n🚀 [ПК -> EV3]: Отправка команды на запуск рисования...")
        
        # Полный разрыв связи процесса с SSH-сессией с помощью nohup и disown
        run_command = f"bash -c 'nohup brickrun -r -- pybricks-micropython {REMOTE_SCRIPT_PATH} > /dev/null 2>&1 & disown'"
        
        # Открываем интерактивный терминал, шлем команду и держим паузу, чтобы ОС робота переварила запуск
        chan = ssh.invoke_shell()
        chan.send(run_command + '\n')
        time.sleep(1.5)
        chan.close()
        
        print("🤖 Робот успешно принял новые файлы и приступил к работе!")
        print("📺 Процесс отрисовки векторов транслируется на LCD-экран кубика EV3.")
        print("------------------------------------------------------------------------------")
        print("🏁 Сессия управления завершена. Программу на ПК можно закрывать.")
        print("==============================================================================")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время передачи данных или запуска: {e}")
    finally:
        ssh.close()


if __name__ == '__main__':
    main()