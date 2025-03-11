import json

def json_address_modbus():
    with open("Address.json", "r") as json_file:  # Открываем файл json и читаем значение адреса модбас
        a = json.load(json_file)  # Переменной присвоить обработанный словарь файла
        Address = a['Modbus']['Address']
        COMport_PH = a['Modbus']['COMport_PH']
        COMport_calibrator = a['Modbus']['COMprot_calibrator']
        COMport_Agilent = a['Modbus']['COMport_Agilent']
        return Address, COMport_PH, COMport_calibrator, COMport_Agilent

