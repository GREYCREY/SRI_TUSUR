import json_open
import sys
import time
import Agilent_34401A
import os
import openpyxl
import n4_17
import struct
import serial
import minimalmodbus
from openpyxl import Workbook, load_workbook


array_Range = []               #Массив диапазонов
Units_Range = []
Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()

type_device = {
    '1': "В",
    '3': "мВ",
    '5': "А",
    '7': "мА",
}

opros_na_shunt = {
    '1': 60,
    '2': 75,
    '3': 100,
    '4': 150,
    '5': "Внешний шунт не используется, вы хотите продолжить? \n"
}

for address in Address:
    try:
        instrument = minimalmodbus.Instrument(COMport_PH, address)  #RS-485
        instrument.serial.baudrate = 38400
        instrument.serial.bytesize = 8
        instrument.serial.parity = serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.mode = minimalmodbus.MODE_RTU

        Units = instrument.read_register(43014, 0, 3)                        # Единицы измерения
        Range = instrument.read_float(43013, 3, 2)                           # Диапазон измерения
        Units_Range.append(Units)                                            #К созданному массиву добавить значение
        array_Range.append(int(Range))
    except minimalmodbus.serial.SerialException as e:
        # Ошибка подключения к COM порту
        print(f"Ошибка при подключении ПЩ к COM порту '{COMport_PH}'")
        input("Нажмите клавишу 'Enter' для выхода из консоли")
        sys.exit()

    except Exception as e:
        # Ошибка чтения данных
        print(f"Ошибка при чтении данных с адреса '{address}'")
        input("Нажмите клавишу 'Enter' для выхода из консоли")
        sys.exit()

U_shunt = {
    '1': 0.060,
    '2': 0.075,
    '3': 0.100,
    '4': 0.150,
}

U_shunt100 = {
    '1': 6.000,
    '2': 7.500,
    '3': 10.000,
    '4': 15.000,
}

datatime = time.strftime('%Y-%m-%d %H часов %M минут %S секунд', time.localtime())  # Текущее время и дата
if os.path.exists("Result") == False:  # Проверка на наличие папки. Если такой папки нет, создать
    os.mkdir("Result")
os.mkdir("Result/" + str(datatime))

def create_file():
    # Создание папки, если она не существует
    folder_path = os.path.join("Result", str(datatime))
    os.makedirs(folder_path, exist_ok=True)  # Создаем папку, если ее нет
    # Формирование пути и имени файла
    file_name = f"Калибровка ПЩ {str(array_Range[0])} {type_device[str(Units_Range[0])]} с адресами {min(Address)}-{max(Address)}.xlsx"
    file_path = os.path.join(folder_path, file_name)
    # Создаем новый Excel-файл
    workbook = Workbook()
    # Удаляем автоматически созданный первый лист, если он не нужен
    workbook.remove(workbook.active)
    # Создаем листы для каждого address и записываем заголовки
    for address in Address:
        sheet_name = f"{str(address)}"
        sheet = workbook.create_sheet(title=sheet_name)
        # Добавляем заголовки
        if Units_Range[0] == 1 or Units_Range[0] == 3:
            sheet.append(['Поданное знач. с калиб', 'Результат с ПЩ', 'Температура ПЩ*10', 'Δ без корр.', 'Ожидаемые знач. ПЩ', 'Δ c корр.'])
        if Units_Range[0] == 5 or Units_Range[0] == 7:
            sheet.append(['Поданное знач. с калиб', 'Результат с ПЩ', 'Температура ПЩ*10', 'Истинный результат ПЩ', 'Δ без корр.', 'Ожидаемые знач. ПЩ', 'Δ c корр.'])
    # Сохраняем файл
    workbook.save(file_path)

    return file_path

def identity_check_Range_Units():
    if array_Range.count(array_Range[0]) == len(array_Range):          #Проверка на одинаковость диапазонов измерений
        if Units_Range.count(Units_Range[0]) == len(Units_Range):      #Проверка на одинаковость единиц измерений
            print("Диапазон измерения ПЩ составляет +-" + str(array_Range[0]) + type_device[str(Units_Range[0])])

def time_ustavki_PH():   #Задержка между сменой полярности поданного значения
    for sec in range(10, -1, -1):
        sys.stdout.write(("\rУстановка значения на ПЩ. Осталось: {:02d} секунд").format(sec))
        time.sleep(1)
        sys.stdout.flush()
    print("\n")

def time_mejdu_izmerenie():  #Задержка между измерениями
    for sec in range(80, -1, -1):
        sys.stdout.write(("\rДо следующего измерения осталось: {:02d} секунд").format(sec))
        time.sleep(1)
        sys.stdout.flush()
    print("\n")

def nastroika():    #Настройка параметров фильтра ПЩ
    par1 = int(input("Частота выборок АЦП будет равна? \n"
                            "0) 16,7 выб/с    \n"
                            "1) 12,5 выб/с  \n"
                            "2) 10 выб/с  \n"
                            "3) 8,33 выб/с \n"
                            "4) 6,25 выб/с \n"
                            "5) 4,17 выб/с \n"
                            "Введите цифру: "))
    par2 = int(input("Частота выборок АЦП будет равна? \n"
                            "0) отключен    \n"
                            "1) фильтр Бесселя  \n"
                            "2) скользящее среднее  \n"
                            "3) усреднение из N результатов \n"
                            "Введите цифру: "))
    if par2 == 1:
        par3 = int(input("Частота среза будет равна? \n"
                                "0) 2 Гц  \n"
                                "1) 1 Гц  \n"
                                "2) 0,5 Гц  \n"
                                "3) 0,2 Гц \n"
                                "4) 0,1 Гц \n"
                                "5) 0,05 Гц \n"
                                "Введите цифру: "))
    if par2 == 2:
        par3 = int(input("Число выборок будет равно? \n"
                                "0) 10  \n"
                                "1) 25  \n"
                                "2) 50  \n"
                                "3) 100 \n"
                                "Введите цифру: "))
    if par2 == 3:
        par3 = int(input("Число выборок будет равно? \n"
                                "0) 8  \n"
                                "1) 16  \n"
                                "2) 32  \n"
                                "Введите цифру: "))
    for address in Address:
        try:
            par11 = minimalmodbus.Instrument(COMport_PH, address).read_register(42026, 0, 3, True)
            par22 = minimalmodbus.Instrument(COMport_PH, address).read_register(42027, 0, 3, True)
            par33 = minimalmodbus.Instrument(COMport_PH, address).read_register(42028, 0, 3, True)
            if par11 != par1 or par22 != par2 or par33 != par3:
                minimalmodbus.Instrument(COMport_PH, address).write_register(42012, 0x3333)
                minimalmodbus.Instrument(COMport_PH, address).write_register(42026, par1)
                minimalmodbus.Instrument(COMport_PH, address).write_register(42027, par2)   
                minimalmodbus.Instrument(COMport_PH, address).write_register(42028, par3) 
                minimalmodbus.Instrument(COMport_PH, address).write_register(42013, 0x27D9)
            else:
                print("Параметры фильтра прибора с адресом: " + str(address) + ", в изменении не нуждаются")
                time.sleep(1)
        except minimalmodbus.NoResponseError:
            print("Идет запись параметров фильтра прибора с адресом: " + str(address))
            time.sleep(5)

def chtenie_param():
    print("```````````````````````````````````")
    for address in Address:
        par1 = minimalmodbus.Instrument(COMport_PH, address).read_register(42026, 0, 3, True)
        par2 = minimalmodbus.Instrument(COMport_PH, address).read_register(42027, 0, 3, True)
        par3 = minimalmodbus.Instrument(COMport_PH, address).read_register(42028, 0, 3, True)
        print("Прибор с адресом: " + str(address))
#------------------------------------------------------------
        if par1 == 0:
            print("Частота выборок АЦП: 16,7 выб/с")
        if par1 == 1:
            print("Частота выборок АЦП: 12,5 выб/с")
        if par1 == 2:
            print("Частота выборок АЦП: 10 выб/с")
        if par1 == 3:
            print("Частота выборок АЦП: 8,33 выб/с")
        if par1 == 4:
            print("Частота выборок АЦП: 6,25 выб/с")
        if par1 == 5:
            print("Частота выборок АЦП: 4,17 выб/с")
#------------------------------------------------------------
        if par2 == 0:
            print("Тип фильтра: отключен")
        if par2 == 1:
            print("Тип фильтра: фильтр Бесселя")
        if par2 == 2:
            print("Тип фильтра: скользящее среднее")
        if par2 == 3:
            print("Тип фильтра: усреднение из N результатов")
#------------------------------------------------------------
        if par2 == 1:
            if par3 == 0:
                print("Частота среза: 2 Гц")
            if par3 == 1:
                print("Частота среза: 1 Гц")
            if par3 == 2:
                print("Частота среза: 0,5 Гц")
            if par3 == 3:
                print("Частота среза: 0,2 Гц")
            if par3 == 4:
                print("Частота среза: 0,1 Гц")
            if par3 == 5:
                print("Частота среза: 0,05 Гц")
        if par2 == 2:
            if par3 == 0:
                print("Число выборок: 10")
            if par3 == 1:
                print("Число выборок: 25")
            if par3 == 2:
                print("Число выборок: 50")
            if par3 == 3:
                print("Число выборок: 100")
        if par2 == 3:
            if par3 == 0:
                print("Число выборок: 8")
            if par3 == 1:
                print("Число выборок: 16")
            if par3 == 2:
                print("Число выборок: 32")
        print("```````````````````````````````````")
        
def Results(file_path): #Вывод результатов измерений на экран и сохранение в файл
    vivod = Agilent_34401A.Agilent_value()
    print("Agilent", "%.8f" %vivod)
    for address in Address:
        Result = minimalmodbus.Instrument(COMport_PH, address).read_float(42046, 3, 2, 3)  # Результат измерения ПЩ
        Temperature = minimalmodbus.Instrument(COMport_PH, address).read_register(42054, 0, 3, True)  # Температура ПЩ
        Instrument_error = ((vivod - Result) / int(array_Range[0])) * 100  # Погрешность ПЩ
        print("Результат измерения ПЩ (Адрес modbus " + str(address) + ") = %.5f" % Result + type_device[str(Units_Range[0])])
        print("Температура ПЩ*10 =", Temperature)
        # Открываем существующий Excel-файл
        workbook = load_workbook(file_path)
        # Проверяем, существует ли лист для данного address
        sheet_name = f"{str(address)}"
        if sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
        else:
            raise ValueError(f"Лист с названием '{sheet_name}' не найден в файле!")
        # Записываем данные в лист
        sheet.append([
            round(vivod, 8),  # Записываем как число
            round(Result, 6),  # Записываем как число
            Temperature                # Температура
        ])

        # Сохраняем изменения в файл
        workbook.save(file_path)

def opros_shunt():   #Если используется шунт
    opros = 0
    while opros != 1:
        znachenie = int(input("Используется ли внешний шунт для измерения силы тока? \n"
                              "1) Номинальное падение напряжения составляет 60 мВ  \n"
                              "2) Номинальное падение напряжения составляет 75 мВ  \n"
                              "3) Номинальное падение напряжения составляет 100 мВ  \n"
                              "4) Номинальное падение напряжения составляет 150 мВ  \n"
                              "5) Внешний шунт не используется \n"
                              "Введите цифру: "))

        if znachenie == 1 or znachenie == 2 or znachenie == 3 or znachenie == 4:
            opros = int(input(
                "Вы выбрали цифру " + str(znachenie) + " - номинальное падение напряжения ПЩ составляет " +
                str(opros_na_shunt[str(znachenie)]) + " мВ, вы хотите продолжить? \n"
                "1) Да. \n"
                "2) Нет, вернуться назад. \n"
                "Введите цифру: ")
                        )
            delitel = int(input("Используется ли делитель напряжения 100:1? \n"
                "1) Да. \n"
                "2) Нет. \n"
                "Введите цифру: "))
            if delitel == 1:
                print(f"Поданное напряжение с калибратора равняется {str(U_shunt100[str(znachenie)])} В")
            if delitel == 2:
                print(f"Поданное напряжение с калибратора равняется {str(U_shunt[str(znachenie)])} В")
            if delitel != 1 and delitel != 2:
                opros = 0
                continue
            n4_17.calibrator_U()
            n4_17.set_value_calibrator_I(znachenie, delitel)

        if znachenie == 5:
            opros = int(input(
                "Внешний шунт не используется, вы хотите продолжить? \n"
                "1) Да. \n"
                "2) Нет, вернуться назад. \n"
                "Введите цифру: ")
                        )
            n4_17.calibrator_I()
            n4_17.set_value_calibrator()
