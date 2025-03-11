import time
import json
import json_open
import PH
import serial

Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()

try:
    ser = serial.Serial(port = COMport_calibrator, baudrate=9600, bytesize=8, stopbits=1, timeout=1)  #RS-232
except serial.SerialException:
    print(f"Ошибка при подключении калибратора к COM порту '{COMport_calibrator}'")
    input("Нажмите клавишу 'Enter' для выхода из консоли")
    sys.exit()

def calibrator_U():
    ser.write(b'MU\r\n')                #Включить режим калибратора напряжения
    time.sleep(1)
    ser.write(b'RA\r\n')                #Включить на калибраторе автоматический выбор предела
    time.sleep(1)

def calibrator_I():
    ser.write(b'MA\r\n')                #Включить режим калибратора тока
    time.sleep(1)
    ser.write(b'RA\r\n')                #Включить на калибраторе автоматический выбор предела
    time.sleep(5)
    

def set_value_calibrator():
    cmndStr = "S" + str(PH.array_Range[0]) + "\r\n"  # Устанавить значение напряжения на калибраторе
    ser.write(cmndStr.encode("ASCII"))
    time.sleep(1)
    ser.write(b'O1\r\n')             # Подключить выход калибратора
    time.sleep(1)

def set_value_calibrator_I(znachenie, delitel):
    if delitel == 1:
        cmndStr = "S" + str(PH.U_shunt100[str(znachenie)]) + "\r\n"
    else:
        cmndStr = "S" + str(PH.U_shunt[str(znachenie)]) + "\r\n"  # Устанавить значение напряжения на калибраторе
    ser.write(cmndStr.encode("ASCII"))
    time.sleep(1)
    ser.write(b'O1\r\sn')             # Подключить выход калибратора
    time.sleep(1)

def calibrator_value():
    ser.write(b'V \r\n')  # Отправляем команду на получение значения напряжения
    serialString = ser.readline().decode("ASCII").rstrip()
    if not serialString:  # Проверяем, что строка не пустая
        time.sleep(0.1)
        ser.write(b'V \r\n')  # Отправляем команду на получение значения напряжения
        serialString = ser.readline().decode("ASCII").rstrip()
        print("Поданное напряжение с калибратора", serialString.replace("M", "="), "В")
    else:
        print("Поданное напряжение с калибратора", serialString.replace("M", "="), "В")
    time.sleep(1)

def polarity_revers():
    ser.write(b'K11\r\n')
    time.sleep(1)
