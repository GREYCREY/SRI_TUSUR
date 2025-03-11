import n4_17
import Agilent_34401A
import PH
import Poly
import json_open
import sys
import time
import os

izmerenie = 0
nomer_izmereniya = 0
delitel = 0

def resource_path(relative_path):
    """ Получение абсолютного пути к ресурсу, работает как для .py, так и для .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Использование resource_path для получения пути к Address.json
address_json_path = resource_path('Address.json')

# Теперь вы можете открыть файл
with open(address_json_path, 'r') as json_file:
    # Здесь ваш код для работы с файлом
    # Например, загрузка данных из JSON
    import json
    data = json.load(json_file)
    # Продолжайте с использованием переменной data

def main():
    global nomer_izmereniya
    file_path = PH.create_file()
    Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()
    print("Адреса приборов: ", Address)  # Вывести на экран адреса устройств
    Agilent_34401A.settings_Agilent()    #Предварительная настройка мульти-ра
    PH.identity_check_Range_Units()      #Проверка на равенство
    PH.nastroika()                       #Настройка параметров фильтра
    PH.chtenie_param()                   #Вывод параметров фильтра на экран
    if PH.Units_Range[0] == 1 or PH.Units_Range[0] == 3:  # В, мВ
        PH.create_file()                 #Создание файла для значений
        n4_17.calibrator_U()             #Режим калибратора напряжения
        print("-------------------------------")
        n4_17.set_value_calibrator()     #Запись макс. значения ПЩ в калибратор
    if PH.Units_Range[0] == 5 or PH.Units_Range[0] == 7:  # A, мA
        PH.create_file()
        print("-------------------------------")
        PH.opros_shunt()
    try:
        while izmerenie == 0:
            nomer_izmereniya += 1
            print("~~~~~~~~~~~~~~~~~~~~[Измерение №" + str(nomer_izmereniya) + "]~~~~~~~~~~~~~~~~~~~~")
            n4_17.calibrator_value()
            if nomer_izmereniya == 1:
                PH.time_ustavki_PH()
            PH.Results(file_path)
            print("-------------------------------")
            n4_17.polarity_revers()
            n4_17.calibrator_value()
            PH.time_ustavki_PH()
            PH.Results(file_path)
            print("-------------------------------")
            PH.time_mejdu_izmerenie()
            nomer_izmereniya += 1
            print("~~~~~~~~~~~~~~~~~~~~[Измерение №" + str(nomer_izmereniya) + "]~~~~~~~~~~~~~~~~~~~~")
            time.sleep(5)
            n4_17.calibrator_value()
            PH.Results(file_path)
            print("-------------------------------")
            n4_17.polarity_revers()
            n4_17.calibrator_value()
            PH.time_ustavki_PH()
            PH.Results(file_path)
            print("-------------------------------")
            PH.time_mejdu_izmerenie()
    
    except KeyboardInterrupt:
        n4_17.ser.write(b'O0 \r\n')
        Agilent_34401A.ser_a.write(b'SYSTem:LOCal\r\n')
        print("\nИзмерения окончены!")
        n4_17.ser.close()
        Agilent_34401A.ser_a.close()
        PH.nastroika()
        PH.chtenie_param()
        Poly.poly_coeffs_solver(file_path)
        PH.instrument.serial.close()
        input("Нажмите клавишу 'Enter' для выхода из консоли")
if __name__ == "__main__":
    main()
