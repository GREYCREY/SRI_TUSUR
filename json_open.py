import json
import sys
import os

def resource_path(relative_path):
    """Возвращает корректный путь к ресурсу как при запуске из .py, так и из .exe"""
    if hasattr(sys, '_MEIPASS'):  # PyInstaller создаёт временную папку _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def json_address_modbus():
    path_to_json = resource_path("Address.json")
    with open(path_to_json, "r", encoding="utf-8") as json_file:  # Открываем файл json и читаем значение адреса модбас
        a = json.load(json_file)  # Переменной присвоить обработанный словарь файла
        Address = a['Modbus']['Address']
        COMport_PH = a['Modbus']['COMport_PH']
        COMport_calibrator = a['Modbus']['COMprot_calibrator']
        COMport_Agilent = a['Modbus']['COMport_Agilent']
        return Address, COMport_PH, COMport_calibrator, COMport_Agilent

