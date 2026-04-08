import paramiko
import os
import socket
import subprocess

# Стандартные IP, которые Windows/EV3 используют для Bluetooth PAN
POSSIBLE_IPS = ["10.42.0.3", "169.254.1.2", "169.254.10.1", "10.0.0.1"]

def find_robot_ip():
    """Проверяет доступность робота по списку типичных адресов"""
    print("🔍 Поиск робота в сети Bluetooth...")
    for ip in POSSIBLE_IPS:
        try:
            # Быстрая проверка: пробуем открыть порт SSH (22)
            with socket.create_connection((ip, 22), timeout=0.5):
                print(f"✨ Робот обнаружен на адресе: {ip}")
                return ip
        except (socket.timeout, ConnectionRefusedError, OSError):
            continue
    return None

def send_and_run(local_file):
    robot_ip = find_robot_ip()
    
    if not robot_ip:
        print("❌ Робот не найден. Убедитесь, что:")
        print("1. EV3 сопряжен с Windows по Bluetooth.")
        print("2. В настройках EV3 включен 'Bluetooth' и 'iPhone/iPad' (или 'Bluetooth PAN').")
        return

    # Настройки доступа
    username = "robot"
    password = "maker"
    remote_dir = "/home/robot/pr1"
    remote_file = f"{remote_dir}/main.py"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(robot_ip, username=username, password=password, timeout=5)
        
        # Передача файла
        sftp = ssh.open_sftp()
        try:
            ssh.exec_command(f"mkdir -p {remote_dir}")
            sftp.put(local_file, remote_file)
            print(f"⬆️ Файл {local_file} успешно передан.")
        finally:
            sftp.close()

        # Запуск
        # Используем полный путь к интерпретатору MicroPython
        cmd = f"brickrun -r -- pybricks-micropython {remote_file}"
        print(f"🚀 Запуск...")
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Вывод логов в реальном времени
        for line in stdout:
            print(f"🤖: {line.strip()}")
        for line in stderr:
            print(f"❌: {line.strip()}")

    except Exception as e:
        print(f"🔴 Ошибка связи: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    # Укажи имя своего файла здесь
    send_and_run("main.py")