import json_open
import time
import sys
import serial

Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()

try:
    ser_a = serial.Serial(port = COMport_Agilent, baudrate=9600, bytesize=8, stopbits=2, timeout=5)  #Настройка RS-232
except serial.SerialException as e:
    print(f"Ошибка при подключении  Agilent`а  к COM порту '{COMport_Agilent}'")
    input("Нажмите клавишу 'Enter' для выхода из консоли")
    sys.exit()
    
def settings_Agilent():
    print("-------------------------------")
    ser_a.write(b'SYST:REM\r\n')                  #включить дистанционное управление
    time.sleep(1)
    print("Дистанционное управление Agilent'ом включено")
    ser_a.write(b'*RST\r\n')                        #сброс
    time.sleep(1)
    print("Сброс всех настроек Agilent'а")
    ser_a.write(b'SENSE:VOLTAGE:DC:NPLC 100\r\n')   #Медленное измерение SLOW 6 DIGIT
    time.sleep(1)
    print("Выставлен режим SLOW 6 DIGIT")
    ser_a.write(b'INPut:IMPedance:AUTO ON\r\n')     # Входное сопротивление 10 ГОм
    time.sleep(1)
    print("Выставлено входное сопротивление 10 ГОм")
    ser_a.write(b'CONF:FRES\r\n')                   #включить 4-проводной режим измерения
    print("-------------------------------")

def Agilent_value():
    ser_a.write(b'INITiate:IMMediate\n')      #Переводит мульти-тр в ожидание сингала запуска
    time.sleep(5)
    ser_a.write(b'FETCH?\r\n')                #пересылает показание из внутренней памяти мульт-ра
    time.sleep(1)
    serialString_a = ser_a.readline()         # Прочитать возвращенное значение
    #print(serialString_a)
    b, c = serialString_a.decode("ASCII").rstrip().split('E')   #Разбить строку на 2 части
    vivod = (float(b) * (10 ** int(c))) #Десятичное числа с запятой
    #print(vivod)
    return(vivod)
