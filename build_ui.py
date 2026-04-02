import os
import subprocess

base_dir = os.path.dirname(__file__)
ui_file = os.path.join(base_dir, "main.ui")
py_file = os.path.join(base_dir, "ui_main.py")

# Проверяем, есть ли pyuic5
try:
    subprocess.run(["pyuic5", "--version"], check=True, capture_output=True)
except FileNotFoundError:
    print("pyuic5 не найден. Установите PyQt5-tools или добавьте pyuic5 в PATH.")
    exit(1)

# Конвертация .ui → .py
subprocess.run(f'pyuic5 "{ui_file}" -o "{py_file}"', shell=True)
print(f"✅ Сконвертировано: {ui_file} → {py_file}")
