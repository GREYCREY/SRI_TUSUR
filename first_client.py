import socket
import sys
import serial
import json_open
import csv
import queue
import json
from time import sleep
from struct import pack, unpack_from, error
import threading
from keyboard import is_pressed
import packet as pk
from datetime import datetime, timedelta

# Глобальные переменные для управления потоками
stop_thread = threading.Event()
param_value_queue = queue.Queue()
ustavka_response = {}  # {уставка: (Event, значение)}
ustavka_lock = threading.Lock()  # Для безопасного доступа из разных потоков
wait_for_input_event = threading.Event()
agilent_value_event = threading.Event()  # Событие для ожидания значения от Agilent
current_agilent_value = None  # Текущее значение от Agilent
agilent_value_lock = threading.Lock()  # Блокировка для синхронизации доступа к current_agilent_value

Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()
try:
    ser_a = serial.Serial(port=COMport_Agilent, baudrate=9600, bytesize=8, stopbits=2, timeout=5)  # Настройка RS-232
except serial.SerialException as e:
    print(f"Ошибка при подключении Agilent к COM порту '{COMport_Agilent}'")
    input("Нажмите клавишу 'Enter' для выхода из консоли")
    sys.exit()
agilent_lock = threading.Lock()  # Блокировка для синхронизации
agilent_stop_event = threading.Event()  # Событие остановки

def settings_Agilent():
    print("-------------------------------")
    ser_a.write(b'SYST:REM\r\n')                  #включить дистанционное управление
    sleep(1)
    ser_a.write(b'CONF:FRES\r\n')                   #включить 4-проводной режим измерения
    print("-------------------------------")

def Agilent_value():
    """Получение данных с Agilent"""
    ser_a.write(b'INITiate:IMMediate\n')
    sleep(5)  # Ожидание завершения измерения
    ser_a.write(b'FETCH?\r\n')
    sleep(1)
    serialString_a = ser_a.readline()
    try:
        b, c = serialString_a.decode("ASCII").rstrip().split('E')
        value = float(b) * (10 ** int(c))
        return round(value, 6)
    except Exception as e:
        print("Ошибка при чтении данных Agilent:", e)
        return None

def agilent_thread(file_name='output.csv'):
    """Поток получения данных с Agilent и запись в CSV"""
    settings_Agilent()
    while not agilent_stop_event.is_set():
        with agilent_lock:
            value = Agilent_value()
            if value is not None:
                with agilent_value_lock:
                    current_agilent_value = value
                    agilent_value_event.set()  # Сигнализируем, что новое значение получено
                
                # Открываем CSV файл и добавляем данные
                with open(file_name, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Agilent", value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                    print(f"Agilent Value: {value}")
        sleep(10)  # Период опроса прибора

def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    return pack('<H', len(data)) + pack('<Q', int(t_time * 1000)) + data

def write_to_csv(current_IDT, current_ustavka_IDT, param_value, agilent_value, file_name='output.csv'):
    # Расчет погрешности
    fault = abs(current_ustavka_IDT - param_value)
    status = 'OK' if fault <= 0.1 else 'НеОК'
    
    # Запись данных в CSV-файл
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            current_IDT, 
            current_ustavka_IDT, 
            param_value, 
            agilent_value,
            fault, 
            status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        print(f"Текущий IDT:{current_IDT} Уставка:{current_ustavka_IDT} Сопротивление:{param_value} Agilent:{agilent_value} Погрешность:{fault} Статус:{status}")

def wait_for_input():
    """Функция ожидания нажатия клавиши Enter"""
    while not stop_thread.is_set():
        input("Установите мультиметр на следующий ИДТ и нажмите Enter...")
        wait_for_input_event.set()  # Разрешаем продолжить выполнение программы
        wait_for_input_event.clear()  # Сбрасываем событие для следующего ожидания

def send_commands_thread(sock, commands):
    # Отправка начальных команд
    start_commands = ["complex_mode","vkl_atm_biab","vkl_biab"]
    for command_name in start_commands:
        if stop_thread.is_set():
            print("Stopping the command cycle")
            break
        command_details = commands['short_comm'][command_name]
        type_ku = command_details['type_ku']
        cod_ku = command_details['cod_ku']
        command = pk.Short_Comanda_KU(type_ku, cod_ku)
        sock.send(command.message())
    
    for current_IDT in range(0, 11):
        for current_ustavka_IDT in range(990, 1205, 5):
            with ustavka_lock:
                event = threading.Event()
                ustavka_response[current_ustavka_IDT] = (event, None)

            # Отправка уставки
            ustavka_IDT = pk.Short_Comanda_KU(4, current_IDT, 1)
            sock.send(ustavka_IDT.set_ustavka(current_ustavka_IDT, 4))
            print(f"Отправлена уставка: {current_ustavka_IDT}")
            
            # Ожидание ответа от устройства
            if not event.wait(timeout=10):  # Ждем 10 секунд
                print(f"Ошибка: не получили ответ на уставку {current_ustavka_IDT}")
                continue

            # Получаем значение от устройства
            with ustavka_lock:
                _, param_value = ustavka_response.pop(current_ustavka_IDT, (None, None))

            # Ожидаем новое значение от Agilent
            agilent_value_event.clear()
            with agilent_value_lock:
                agilent_value = current_agilent_value
            
            # Если значение еще не получено, ждем
            if agilent_value is None:
                print("Ожидание значения от Agilent...")
                agilent_value_event.wait(timeout=15)
                with agilent_value_lock:
                    agilent_value = current_agilent_value
            
            if param_value is not None and agilent_value is not None:
                write_to_csv(current_IDT, current_ustavka_IDT, param_value, agilent_value)
        
        # Ожидание подтверждения оператора для перехода к следующему ИДТ
        wait_for_input_event.wait()
    
    # Отправка завершающих команд
    sleep(10)
    end_commands = ["otkl_biab", "otkl_atm_biab_kpa", "autonomous_mode"]
    for command_name in end_commands:
        if stop_thread.is_set():
            print("Stopping the command cycle")
            break
        command_details = commands['short_comm'][command_name]
        type_ku = command_details['type_ku']
        cod_ku = command_details['cod_ku']
        command = pk.Short_Comanda_KU(type_ku, cod_ku)
        sock.send(command.message())

def receive_messages(sock):
    '''Получение и расшифровка сообщений с сервера'''
    buffer = b''  # Буфер для накопления данных

    while not stop_thread.is_set():
        try:
            # Получаем данные из сокета
            chunk = sock.recv(16384)
            if not chunk:
                break  # Если данных нет, завершаем цикл
            buffer += chunk  # Добавляем полученные данные в буфер

            # Если в буфере есть хотя бы два байта для длины сообщения
            while len(buffer) >= 2:
                # Читаем длину сообщения (первые 2 байта)
                message_length = unpack_from('<H', buffer)[0]

                # Проверяем, хватает ли данных для полного сообщения
                if len(buffer) < 2 + message_length:
                    break  # Если данных не хватает, выходим из цикла для получения оставшихся данных
                
                # Извлекаем полное сообщение
                message_data = buffer[:2 + message_length]
                buffer = buffer[2 + message_length:]  # Удаляем из буфера обработанные данные

                # Декодируем сообщение с помощью функции decode_packet
                try:
                    decode_packet(message_data)
                except Exception as e:
                    print("Ошибка при расшифровке сообщения:", e)

        except Exception as e:
            print("Ошибка при получении данных:", e)
            break

def decode_packet(data):
    previous_param_value = None  # Переменная для хранения предыдущего значения параметра
    
    while len(data) > 2:  # Минимум 2 байта для длины сообщения
        # Чтение длины сообщения
        message_length, = unpack_from('<H', data)
        print(f"Длина сообщения: {message_length}")

        if len(data) < message_length + 2:  # Проверяем, хватает ли данных для сообщения
            print("Ошибка: Сообщение выходит за пределы данных!")
            break

        # Извлекаем текущее сообщение
        current_message = data[:message_length + 2]
        data = data[message_length + 2:]  # Убираем прочитанную часть

        try:
            # Чтение времени
            timestamp, = unpack_from('<Q', current_message, 2)
            # Преобразуем 100-наносекундные интервалы с 1 января 1601 года в стандартное время
            epoch_start = datetime(1601, 1, 1)
            time_in_seconds = timestamp / 1e7  # 100-наносекундные интервалы -> секунды
            decoded_time = epoch_start + timedelta(seconds=time_in_seconds)
            print(f"Время: {decoded_time}")

            # Чтение пакета
            packet, = unpack_from('<H', current_message, 10)
            print(f"Пакет: {packet}")

            if packet == 1:  # Если Пакет = 1, расшифровываем квитанцию
                # Чтение КодВозврата
                kod_vozvrata, = unpack_from('<H', current_message, 12)
                # Чтение КолПарам
                kol_param, = unpack_from('<H', current_message, 14)

                # Чтение ТекстПарам
                param_data = current_message[16:]  # Срез данных для параметров
                for _ in range(kol_param):
                    null_index = param_data.find(b'\x00')
                    if null_index == -1:
                        break
                    text_param = param_data[:null_index].decode('cp1251', errors='replace')
                    param_data = param_data[null_index + 1:]  # Убираем прочитанный параметр
            else:
                # Чтение количества параметров
                kol_param, = unpack_from('<H', current_message, 12)

                # Обработка других параметров
                param_data = current_message[14:]  # Срез данных для параметров
                for _ in range(kol_param):
                    if len(param_data) < 5:
                        break

                    # Чтение ТипАТМ, Номер параметра и Длины
                    type_atm, param_number, param_length = unpack_from('<HHB', param_data)
                    param_data = param_data[5:]  # Убираем прочитанные 5 байт
                    if len(param_data) < param_length:
                        break
                    if type_atm == 20:
                        param_value, = unpack_from('<h', param_data)
                        param_value = round(param_value, 3)

                        with ustavka_lock:
                            if param_value in ustavka_response:
                                event, _ = ustavka_response[param_value]
                                ustavka_response[param_value] = (event, param_value)
                                event.set()  # Разблокируем `send_commands_thread`

        except Exception as e:
            print("Ошибка при обработке пакета:", e)               

def listen_for_keypress(sock, commands):
    # Ожидание нажатия клавиши 'q'
    while not stop_thread.is_set():
        if is_pressed('q'):
            print("Key 'q' pressed, stopping the command cycle")
            
            stop_commands = ["otkl_biab", "otkl_atm_biab_kpa", "autonomous_mode"]
            
            for command_name in stop_commands:
                command_details = commands['short_comm'][command_name]
                type_ku = command_details['type_ku']
                cod_ku = command_details['cod_ku']
                command = pk.Short_Comanda_KU(type_ku, cod_ku)
                sock.send(command.message())
            break

def client_thread(host, port, commands):
    try:
        with socket.create_connection((host, port)) as sock:
            send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands))
            receive_thread = threading.Thread(target=receive_messages, args=(sock,))
            agilent_thread_instance = threading.Thread(target=agilent_thread)
            input_thread = threading.Thread(target=wait_for_input)
            keypress_thread = threading.Thread(target=listen_for_keypress, args=(sock, commands))

            send_thread.start()
            receive_thread.start()
            agilent_thread_instance.start()
            input_thread.start()
            keypress_thread.start()

            send_thread.join()
            receive_thread.join()
            agilent_thread_instance.join()
            input_thread.join()
            keypress_thread.join()
    except ConnectionError:
        print("Server connection failed!")
    finally:
        stop_thread.set()
        agilent_stop_event.set()

if __name__ == "__main__":
    HOST, PORT = "192.168.1.231", 10001

    # Загрузка команд из JSON-файла
    with open('command_biab200.json', 'r', encoding='utf-8') as file:
        commands = json.load(file)
    param_value_queue = queue.Queue()

    # Запуск клиента в отдельном потоке
    client_thread_thread = threading.Thread(target=client_thread, args=(HOST, PORT, commands))
    client_thread_thread.start()

    # Ожидание завершения всех потоков
    client_thread_thread.join()