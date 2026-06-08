# -*- coding: utf-8 -*-
"""
Модуль для конвертации международного формата G-кода (.nc, .gcode, .txt)
в упрощенный формат координат робота-художника (pict_coord.rtf).
"""

import os
import re
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from .config import PEN_UP_CODE  # Импортируем константу (обычно 255)

class GCodeConverter:
    """Класс для выбора, парсинга и конвертации G-кода."""

    @staticmethod
    def convert_gcode_to_robot_format(parent_window):
        """
        Открывает диалог выбора файла G-кода, парсит его и сохраняет результат
        в папку ev3-main в файл pict_coord.rtf.
        """
        # 1. Диалог выбора файла G-кода
        file_path, _ = QFileDialog.getOpenFileName(
            parent_window,
            "Выбрать файл G-кода",
            "",
            "G-Code файлы (*.gcode *.nc *.txt *.tap);;Все файлы (*.*)"
        )
        
        if not file_path:
            return  # Пользователь отменил выбор

        # 2. Определение целевого пути для сохранения (папка ev3-main)
        # Находим корень проекта (на уровень выше папки gui_modules)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_dir = os.path.join(project_root, 'ev3-main') # Исправлено под вашу структуру проекта
        
        # Создаем папку, если её физически нет
        os.makedirs(target_dir, exist_ok=True)
        output_file = os.path.join(target_dir, "pict_coord.rtf")

        try:
            # Регулярные выражения для поиска команд и координат (без учета регистра)
            g_regex = re.compile(r'[GG](\d+)', re.IGNORECASE)
            x_regex = re.compile(r'[XX]([0-9.-]+)', re.IGNORECASE)
            y_regex = re.compile(r'[YY]([0-9.-]+)', re.IGNORECASE)
            z_regex = re.compile(r'[ZZ]([0-9.-]+)', re.IGNORECASE)

            robot_lines = []
            
            # Текущее состояние (модальные значения ЧПУ)
            curr_x = 0
            curr_y = 0
            is_pen_up = True  # По умолчанию считаем, что перо поднято
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for line in lines:
                # Очищаем строку от комментариев (все, что после семиколона ; или внутри скобок)
                line = re.sub(r';.*', '', line)
                line = re.sub(r'\(.*\)', '', line).strip()
                
                if not line:
                    continue

                # Ищем управляющие маркеры в строке
                g_match = g_regex.search(line)
                x_match = x_regex.search(line)
                y_match = y_regex.search(line)
                z_match = z_regex.search(line)

                # Проверяем изменение состояния пера через G0/G1
                if g_match:
                    g_code = int(g_match.group(1))
                    if g_code == 0:    # G00 / G0 - Быстрое перемещение (перо ВВЕРХ)
                        is_pen_up = True
                    elif g_code == 1:  # G01 / G1 - Линейная интерполяция (перо ВНИЗ)
                        is_pen_up = False

                # Проверяем изменение состояния пера через ось Z (Inkscape стиль)
                if z_match:
                    z_val = float(z_match.group(1))
                    if z_val > 0:      # Z > 0 обычно означает безопасную высоту подъема инструмента
                        is_pen_up = True
                    else:              # Z <= 0 означает врезание / рисование
                        is_pen_up = False

                # Если в строке есть новые координаты, обновляем их
                coord_changed = False
                if x_match:
                    curr_x = int(round(float(x_match.group(1))))
                    coord_changed = True
                if y_match:
                    # В ЧПУ координатах Y часто инвертирован относительно экранов, 
                    # но здесь мы просто забираем чистые значения
                    curr_y = int(round(float(y_match.group(1))))
                    coord_changed = True

                # Если координаты изменились, записываем точку в формате робота
                if coord_changed:
                    code = PEN_UP_CODE if is_pen_up else 0
                    robot_lines.append(f"{code} {curr_x} {curr_y}\n")

            # 3. Запись результатов в итоговый файл
            if not robot_lines:
                QMessageBox.warning(
                    parent_window, 
                    "Внимание", 
                    "Файл успешно прочитан, но в нем не найдено совместимых траекторий движения X/Y!"
                )
                return

            with open(output_file, "w", encoding="utf-8") as out_f:
                out_f.writelines(robot_lines)

            QMessageBox.information(
                parent_window,
                "Успешная конвертация",
                f"G-код успешно обработан!\n\n"
                f"Считано строк: {len(lines)}\n"
                f"Сгенерировано точек: {len(robot_lines)}\n"
                f"Файл сохранен в: ev3-main/{os.path.basename(output_file)}"
            )

        except Exception as e:
            QMessageBox.critical(
                parent_window, 
                "Ошибка конвертации", 
                f"Произошел сбой при трансляции G-кода:\n{str(e)}"
            )