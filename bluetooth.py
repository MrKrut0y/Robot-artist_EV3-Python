import socket
import paramiko
import os

# Список стандартных IP для EV3 (Bluetooth PAN и USB)
POSSIBLE_IPS = ["10.42.0.3", "169.254.1.2", "169.254.10.1", "10.0.0.1"]

def find_robot_ip():
    """Автоматический поиск активного IP-адреса робота"""
    for ip in POSSIBLE_IPS:
        try:
            # Проверяем доступность порта SSH (22)
            with socket.create_connection((ip, 22), timeout=0.5):
                return ip
        except (socket.timeout, ConnectionRefusedError, OSError):
            continue
    return None

def upload_and_run_on_ev3(local_coord_file, robot_script="main.py"):
    """Подключение, передача координат и запуск программы на роботе"""
    ip = find_robot_ip()
    if not ip:
        return False, "Робот не найден. Проверьте Bluetooth-сопряжение."

    transport = paramiko.Transport((ip, 22))
    try:
        transport.connect(username="robot", password="maker")
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Путь на роботе
        remote_dir = "/home/robot/pr1"
        sftp.execute(f"mkdir -p {remote_dir}") # Создаем папку если нет
        
        # Передаем файл с координатами
        sftp.put(local_coord_file, f"{remote_dir}/pict_coord.rtf")
        sftp.close()

        # Запуск скрипта через SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username="robot", password="maker")
        
        # Запуск в фоновом режиме или с ожиданием вывода
        cmd = f"brickrun -r -- pybricks-micropython {remote_dir}/{robot_script}"
        ssh.exec_command(cmd)
        
        return True, f"Успешно запущено на {ip}"
    except Exception as e:
        return False, str(e)
    finally:
        transport.close()