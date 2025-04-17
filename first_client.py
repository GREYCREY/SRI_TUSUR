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

# Глобальная переменная для остановки цикла
stop_thread = threading.Event()
param_value_queue = queue.Queue()
ustavka_response = {}  # {уставка: (Event, значение)}
ustavka_lock = threading.Lock()  # Для безопасного доступа из разных потоков
wait_for_input_event = threading.Event()
agilent_lock = threading.Lock()  # Блокировка для синхронизации доступа к Agilent

Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()
try:
    ser_a = serial.Serial(port=COMport_Agilent, baudrate=9600, bytesize=8, stopbits=2, timeout=5)
except serial.SerialException as e:
    print(f"Ошибка при подключении Agilent к COM порту '{COMport_Agilent}'")
    input("Нажмите клавишу 'Enter' для выхода из консоли")
    sys.exit()

def settings_Agilent():
    print("-------------------------------")
    ser_a.write(b'SYST:REM\r\n')  # Включить дистанционное управление
    sleep(1)
    ser_a.write(b'CONF:FRES\r\n')  # Включить 4-проводной режим измерения
    print("-------------------------------")

def Agilent_value():
    """Получение данных с Agilent синхронно"""
    try:
        with agilent_lock:
            ser_a.write(b'INITiate:IMMediate\n')
            sleep(5)  # Ожидание завершения измерения
            ser_a.write(b'FETCH?\r\n')
            serialString_a = ser_a.readline().decode("ASCII").rstrip()
            if 'E' in serialString_a:
                b, c = serialString_a.split('E')
                value = float(b) * (10 ** int(c))
                return round(value, 6)
            return None
    except Exception as e:
        print("Ошибка при чтении данных Agilent:", e)
        return None


def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    return pack('<H', len(data)) + pack('<Q', int(t_time * 1000)) + data

def write_to_csv(current_IDT, current_ustavka_IDT, param_value, agilent_value, file_name='output.csv'):
    fault = abs(current_ustavka_IDT - (- agilent_value ))
    status = 'OK' if fault <= 0.1 else 'НеОК'
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([current_IDT, current_ustavka_IDT, param_value, agilent_value, fault, status])
        print(f"Текущий IDT:{current_IDT} Уставка:{current_ustavka_IDT} Сопротивление:{param_value} Agilent:{agilent_value} Погрешность:{fault} Статус:{status}")
    


def wait_for_input():
    """Ожидание нажатия Enter после смены ИДТ"""
    while not stop_thread.is_set():
        input("Установите мультиметр на следующий ИДТ и нажмите Enter...")
        wait_for_input_event.set()
        wait_for_input_event.clear()


def send_commands_thread(sock, commands):
    # Начальные команды
    start_commands = ["complex_mode", "vkl_atm_biab", "vkl_biab"]
    for command_name in start_commands:
        command_details = commands['short_comm'][command_name]
        command = pk.Short_Comanda_KU(command_details['type_ku'], command_details['cod_ku'])
        sock.send(command.message())
    
    for current_IDT in range(0, 11):
        
        
        for current_ustavka_IDT in range(990, 1205, 5):
            with ustavka_lock:
                event = threading.Event()
                ustavka_response[current_ustavka_IDT] = (event, None)

            # Отправка уставки
            ustavka_packet = pk.Short_Comanda_KU(4, current_IDT, 1).set_ustavka(current_ustavka_IDT, 4)
            sock.send(ustavka_packet)
            print(f"Отправлена уставка: {current_ustavka_IDT}")

            # Ожидание подтверждения
            if not event.wait(timeout=10):
                print(f"Таймаут подтверждения для уставки {current_ustavka_IDT}")
                continue

            # Получение значения параметра и измерения Agilent
            with ustavka_lock:
                _, param_value = ustavka_response.pop(current_ustavka_IDT, (None, None))
            
            agilent_val = Agilent_value()  # Синхронный запрос к Agilent
            
            if param_value is not None and agilent_val is not None:
                write_to_csv(current_IDT, current_ustavka_IDT, param_value, agilent_val)
                  # Задержка 2 секунды перед следующей уставкой
        wait_for_input_event.wait()  # Ожидание подтверждения смены ИДТ
        wait_for_input_event.clear()
    # Завершающие команды
    end_commands = ["otkl_biab", "otkl_atm_biab_kpa", "autonomous_mode"]
    for command_name in end_commands:
        command_details = commands['short_comm'][command_name]
        command = pk.Short_Comanda_KU(command_details['type_ku'], command_details['cod_ku'])
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
        #print(f"Длина сообщения: {message_length}")

        if len(data) < message_length + 2:  # Проверяем, хватает ли данных для сообщения
            #print("Ошибка: Сообщение выходит за пределы данных!")
            break

        # Извлекаем текущее сообщение
        current_message = data[:message_length + 2]
        data = data[message_length + 2:]  # Убираем обработанную часть

        try:
            # Чтение времени
            timestamp, = unpack_from('<Q', current_message, 2)
            # Преобразуем 100-наносекундные интервалы с 1 января 1601 года в стандартное время
            epoch_start = datetime(1601, 1, 1)
            time_in_seconds = timestamp / 1e7  # 100-наносекундные интервалы -> секунды
            decoded_time = epoch_start + timedelta(seconds=time_in_seconds)
            #print(f"Время: {decoded_time}")

            # Чтение пакета
            packet, = unpack_from('<H', current_message, 10)
           # print(f"Пакет: {packet}")

            if packet == 1:  # Если Пакет = 1, расшифровываем квитанцию
                #print("Расшифровка квитанции")
                
                # Чтение КодВозврата
                kod_vozvrata, = unpack_from('<H', current_message, 12)
                #print(f"КодВозврата: {kod_vozvrata}")

                # Чтение КолПарам
                kol_param, = unpack_from('<H', current_message, 14)
               # print(f"Количество параметров: {kol_param}")

                # Чтение ТекстПарам
                param_data = current_message[16:]  # Срез данных для параметров
                for _ in range(kol_param):
                    # Считываем текст параметра
                    # Строка заканчивается нулевым байтом (STRING0)
                    null_index = param_data.find(b'\x00')
                    if null_index == -1:  # Не найден нулевой байт, значит ошибка
                        #print("Ошибка: Не найден нулевой байт в данных параметра!")
                        break
                    
                    text_param = param_data[:null_index].decode('cp1251', errors='replace')
                    #print(f"ТекстПарам: {text_param}")
                    param_data = param_data[null_index + 1:]  # Убираем прочитанный параметр
            else:
                # Чтение количества параметров
                kol_param, = unpack_from('<H', current_message, 12)
                #print(f"Количество параметров: {kol_param}")

                # Обработка других параметров
                param_data = current_message[14:]  # Срез данных для параметров
                for _ in range(kol_param):
                    if len(param_data) < 5:  # Минимум 5 байт на параметр (тип, номер, длина)
                        #print("Ошибка: Данные параметров выходят за пределы сообщения!")
                        break

                    # Чтение ТипАТМ, Номер параметра и Длины
                    type_atm, param_number, param_length = unpack_from('<HHB', param_data)
                    param_data = param_data[5:]  # Убираем прочитанные 5 байт
                    if len(param_data) < param_length:
                        #print("Ошибка: Недостаточно данных для значения параметра!")
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

def listen_for_keypress(sock,commands):
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
        settings_Agilent()  # Инициализация Agilent один раз
        with socket.create_connection((host, port)) as sock:
            send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands))
            receive_thread = threading.Thread(target=receive_messages, args=(sock,))
            input_thread = threading.Thread(target=wait_for_input)

            send_thread.start()
            receive_thread.start()
            input_thread.start()

            send_thread.join()
            receive_thread.join()
            input_thread.join()
    except ConnectionError:
        print("Ошибка подключения к серверу!")
    finally:
        stop_thread.set()

if __name__ == "__main__":
    HOST, PORT = "192.168.0.231", 10001

    # Загрузка команд из JSON-файла
    with open('command_biab200.json', 'r', encoding='utf-8') as file:
        commands = json.load(file)
    param_value_queue = queue.Queue()

    # Запуск клиента в отдельном потоке
    client_thread_thread = threading.Thread(target=client_thread, args=(HOST, PORT, commands))
    client_thread_thread.start()

    # Ожидание завершения всех потоков
    client_thread_thread.join()
