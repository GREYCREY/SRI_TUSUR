import socket
import sys
import serial
import json_open
import csv
import queue
import json
from os import path
from time import sleep
from struct import pack, unpack_from, error
import threading
from keyboard import is_pressed
import packet as pk
from datetime import datetime, timedelta
try:
    from UI import add_result_row, root
except ImportError:
    add_result_row = lambda *args, **kw: None


# Глобальная переменная для остановки цикла
stop_thread = threading.Event()
param_value_queue = queue.Queue()
ustavka_response = {}  # {уставка: (Event, значение)}
ustavka_lock = threading.Lock()  # Для безопасного доступа из разных потоков
wait_for_input_event = threading.Event()
agilent_lock = threading.Lock()  # Блокировка для синхронизации доступа к Agilent
next_idt_event = threading.Event()
start_idt = 0 


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
    sleep(0.1)
    ser_a.write(b'CONF:FRES\r\n')  # Включить 4-проводной режим измерения
    sleep(0.1)
    ser_a.write(b'FRES:NPLC 1\r\n')
    sleep(0.1)
    ser_a.write(b'SAMP:COUN 1\r\n') 
    sleep(0.1)
    ser_a.write(b'TRIG:SOUR IMM\r\n')
    print("-------------------------------")

def Agilent_value():
    """Получение данных с Agilent синхронно"""
    try:
        with agilent_lock:
            ser_a.write(b'INITiate:IMMediate\n')
            sleep(0.5)  # Ожидание завершения измерения
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

def get_current_date_str():
    return datetime.now().strftime("%Y-%m-%d_")

def write_to_csv(current_IDT, current_ustavka_IDT, param_value, agilent_value):
    fault = abs((current_ustavka_IDT/10) - agilent_value)
    status = 'OK' if fault <= 0.1 else 'НеОК'
    file_lable = "БИАБ-200ЛИ"
    file_number = "01"
    file_name=f"{get_current_date_str()}{file_lable}_{file_number}.csv"
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([current_IDT, current_ustavka_IDT/10, param_value/10, agilent_value, fault, status])
        today = datetime.now().strftime("%Y-%m-%d")
        gui_values = ( current_IDT + 1, current_ustavka_IDT / 10,param_value / 10 if param_value is not None else None,agilent_value,
                      fault,status, today)
        root.after(0, add_result_row, gui_values)
        print(f"Текущий IDT:{current_IDT} Уставка:{current_ustavka_IDT/10} Сопротивление:{param_value/10} Agilent:{agilent_value} Погрешность:{fault} Статус:{status}")

def clean_csv_for_idt(start_idt):
    file_lable = "БИАБ-200ЛИ"
    file_number = "01"
    file_name = f"{get_current_date_str()}{file_lable}_{file_number}.csv"

    if not path.exists(file_name):
        return  # Файла ещё нет — ничего не делаем

    rows_to_keep = []
    with open(file_name, mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            if not row:
                continue  # Пропускаем пустые строки
            try:
                row_idt = int(row[0])
                if row_idt != start_idt:
                    rows_to_keep.append(row)
            except (IndexError, ValueError):
                rows_to_keep.append(row)  # Если не число — оставляем на всякий случай

    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows_to_keep)    


def wait_for_input():
    """Ожидание сигнала и затем — нажатия Enter от пользователя"""
    while not stop_thread.is_set():
        next_idt_event.wait()  # ждем, пока send_commands_thread скажет, что пора
        if stop_thread.is_set():
            break
        input("Установите мультиметр на следующий ИДТ и нажмите Enter...")
        wait_for_input_event.set()
        wait_for_input_event.clear()
        next_idt_event.clear()  # готов к следующему сигналу



def send_commands_thread(sock, commands, start_idt):
    # Отправляем стартовые команды
    for name in ["complex_mode", "vkl_atm_biab", "vkl_biab"]:
        cd = commands['short_comm'][name]
        sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

    # Основной цикл по IDT и уставкам
    for current_IDT in range(start_idt, 12):
        for ust in range(990, 1205, 5):
            with ustavka_lock:
                ev = threading.Event()
                ustavka_response[ust] = (ev, None)

            # Отправка уставки
            pkt = pk.Short_Comanda_KU(4, current_IDT, 1).set_ustavka(ust, 4)
            sock.send(pkt)

            # Ожидание ответа (квитанции или ATM)
            if ev.wait(timeout=10):
                _, param = ustavka_response.pop(ust)
            else:
                param = None

            # Измерение Agilent
            ag_val = Agilent_value()

            # Всегда записываем в CSV, даже при ошибках
            write_to_csv(current_IDT, ust, param, ag_val)

        # Переход к следующему IDT
        next_idt_event.set()
        wait_for_input_event.wait()
        wait_for_input_event.clear()

    # Отправляем завершающие команды
    for name in ["otkl_biab", "otkl_atm_biab_kpa", "autonomous_mode"]:
        cd = commands['short_comm'][name]
        sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

        

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
    
    buffer = data
    while len(buffer) >= 2:
        length, = unpack_from('<H', buffer)
        if len(buffer) < 2 + length:
            break
        msg = buffer[:2+length]
        buffer = buffer[2+length:]

        # Считываем временную метку и идентификатор пакета
        timestamp, = unpack_from('<Q', msg, 2)
        packet_id, = unpack_from('<H', msg, 10)

        if packet_id == 1:
            # Квитанция об установке
            kod_vozvrata, = unpack_from('<H', msg, 12)
            kol, = unpack_from('<H', msg, 14)
            if kod_vozvrata == 0:
                # Читаем текстовый параметр — это уставка
                text_bytes = msg[16:]
                null_idx = text_bytes.find(b'\x00')
                if null_idx != -1:
                    val = int(text_bytes[:null_idx].decode('cp1251', errors='ignore'))
                    with ustavka_lock:
                        if val in ustavka_response:
                            ev, _ = ustavka_response[val]
                            ustavka_response[val] = (ev, val)
                            ev.set()

        else:
            # Прочие пакеты (ATM и др.)
            kol, = unpack_from('<H', msg, 12)
            offset = 14
            for _ in range(kol):
                type_atm, pnum, plen = unpack_from('<HHB', msg, offset)
                offset += 5
                if type_atm == 20 and plen == 2:
                    raw, = unpack_from('<h', msg, offset)
                    val = round(raw, 3)
                    with ustavka_lock:
                        if val in ustavka_response:
                            ev, _ = ustavka_response[val]
                            ustavka_response[val] = (ev, val)
                            ev.set()
                offset += plen
              

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
            send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands, start_idt))
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
    HOST, PORT = "192.168.1.231", 10001

    # Загрузка команд из JSON-файла
    with open('command_biab200.json', 'r', encoding='utf-8') as file:
        commands = json.load(file)
    param_value_queue = queue.Queue()
    
    #Вобор стартового ИДТ
    start_idt = 0
    user_input = input("Введите начальный IDT (1–12), по умолчанию 1: ").strip()
    if user_input.isdigit():
        val = int(user_input) - 1
        if 0 <= val <= 11:
            start_idt = val
        else:
            print("Неверное значение. Будет использован IDT = 0.")
    else:
        print("IDT не выбран. Будет использован IDT = 0.")
    clean_csv_for_idt(start_idt)

    # Запуск клиента в отдельном потоке
    client_thread_thread = threading.Thread(target=client_thread, args=(HOST, PORT, commands))
    client_thread_thread.start()

    # Ожидание завершения всех потоков
    client_thread_thread.join()
