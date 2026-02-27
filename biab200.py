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
import packet as pk
from datetime import datetime, timedelta



# Глобальная переменная для остановки цикла
stop_thread = threading.Event()
stop_idt_cycle = threading.Event()
# глобальная переменная для синхронизации decode_packet
active_IDT = None
sock_ref = None
param_value_queue = queue.Queue()
ustavka_response = {}  # {уставка: (Event, значение)}
ustavka_lock = threading.Lock()  # Для безопасного доступа из разных потоков
wait_for_input_event = threading.Event()
agilent_lock = threading.Lock()  # Блокировка для синхронизации доступа к Agilent
next_idt_event = threading.Event()
start_idt = 0 


ser_a = None  # глобальная переменная для подключения Agilent

def init_agilent_port(port_name):
    """Инициализация Agilent по выбранному COM-порту"""
    global ser_a
    try:
        ser_a = serial.Serial(port=port_name, baudrate=9600, bytesize=8, stopbits=2, timeout=5)
    except serial.SerialException as e:
        print(f"Ошибка при подключении Agilent к COM порту '{port_name}': {e}")
        ser_a = None


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
        return 0


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

def safe_callback(callback, values):
    """
    Безопасный вызов callback в главном потоке
    """
    try:
        import tkinter as tk
        # Получаем корневое окно, если оно существует
        root = None
        if hasattr(tk, '_default_root') and tk._default_root:
            root = tk._default_root
        else:
            # Пытаемся найти существующее окно
            for widget in tk._default_root.winfo_children() if hasattr(tk, '_default_root') and tk._default_root else []:
                if isinstance(widget, tk.Tk):
                    root = widget
                    break
        
        if root:
            root.after(0, lambda: callback(values))
        else:
            print("Не удалось найти корневое окно Tk для callback")
    except Exception as e:
        print(f"Ошибка при вызове callback: {e}")   

def write_to_csv(current_IDT, current_ustavka_IDT, param_value, agilent_value, callback=None):
    """
    Запись результатов с возможностью callback в GUI
    """
    fault = abs((current_ustavka_IDT/10) - agilent_value) if agilent_value is not None else 0
    status = '' if fault <= 0.1 else 'Не норма'
    
    # Запись в CSV файл
    file_lable = "БИАБ-200ЛИ"
    file_number = "01"
    file_name = f"{get_current_date_str()}{file_lable}_{file_number}.csv"
    
    with open(file_name, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            current_IDT + 1, 
            current_ustavka_IDT / 10,
            param_value / 10 if param_value is not None else None,
            round(agilent_value, 3),
            round(fault, 3),
            status,
            datetime.now().strftime("%Y-%m-%d")
        ])
    
    # Вызов callback для обновления GUI
    if callback:
        gui_values = (
            current_IDT + 1,
            current_ustavka_IDT / 10,
            param_value / 10 if param_value is not None else None,
            round(agilent_value, 3),
            round(fault, 3),
            status,
            datetime.now().strftime("%Y-%m-%d")
        )
        # Безопасный вызов callback в главном потоке
        safe_callback(callback, gui_values)
        

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


def close_agilent_port():
    global ser_a
    try:
        if ser_a and ser_a.is_open:
            ser_a.close()
    except Exception as e:
        print("Ошибка при закрытии Agilent:", e)
    finally:
        ser_a = None

        


def send_commands_thread(sock, commands, callback, callback_dialog):
    
    clean_csv_for_idt(start_idt)
    try:
        # Отправляем стартовые команды
        for name in ["complex_mode", "vkl_atm_biab", "vkl_biab"]:
            cd = commands['short_comm'][name]
            sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

        global start_idt

        current_IDT = start_idt

        # Основной цикл — теперь while
        while current_IDT < 12:

            # Проверка глобального флага остановки
            if stop_idt_cycle.is_set():
                break

            globals()['active_IDT'] = current_IDT
            
            clean_csv_for_idt(current_IDT + 1)

            # ---- ИЗМЕРЕНИЕ ВСЕХ УСТАВОК ДЛЯ ЭТОГО IDT ----
            for ust in range(990, 1205, 5):

                if stop_idt_cycle.is_set():
                    break

                with ustavka_lock:
                    ev = threading.Event()
                    ustavka_response[ust] = (ev, None)

                # Отправка уставки
                pkt = pk.Short_Comanda_KU(4, current_IDT, 1).set_ustavka(ust, 4)
                sock.send(pkt)

                # Ждём ответа / ATM
                if ev.wait(timeout=10):
                    _, param = ustavka_response.pop(ust)
                else:
                    param = None
                    print(f"Таймаут ожидания ответа для уставки {ust}")

                # Измерение Agilent
                ag_val = Agilent_value()

                # Записываем в CSV и обновляем GUI
                write_to_csv(current_IDT, ust, param, ag_val, callback)

            # Если остановили во время измерений
            if stop_idt_cycle.is_set():
                break

            # ---- ДИАЛОГ ПОСЛЕ IDT ----
            if callback:
                safe_callback(callback, "Переставьте щупы для следующего IDT")

            action = callback_dialog()  # <- вызывается модальное окно

            if action == "stop":
                stop_idt_cycle.set()
                break

            elif action == "repeat":
                # просто начинаем while сначала, но IDT не изменяем
                continue

            elif action == "continue":
                current_IDT += 1
                continue

            else:
                # На всякий случай — поведение по умолчанию
                current_IDT += 1
                continue
            

        # Отправляем завершающие команды
        for name in ["otkl_biab", "otkl_atm_biab_kpa", "autonomous_mode"]:
            cd = commands['short_comm'][name]
            sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

    except Exception as e:
        if callback:
            safe_callback(callback, f"Ошибка: {e}")

        
        

def receive_messages(sock):
    '''Получение и расшифровка сообщений с сервера'''
    buffer = b''  # Буфер для накопления данных

    while not stop_thread.is_set():
        try:
            # Получаем данные из сокета
            chunk = sock.recv(16384)
            if stop_thread.is_set():
                return
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

        if packet_id == 4:
            kol, = unpack_from('<H', msg, 12)  # количество параметров
            offset = 14

            for _ in range(kol):
                type_atm, pnum, plen = unpack_from('<HHB', msg, offset)
                offset += 5

                if plen > 0 and offset + plen <= len(msg):
                    # --- Обработка уставок ИДТ ---
                    if type_atm == 20 and plen == 2:  # Уставка сопротивления ИДТ
                        raw_value, = unpack_from('<H', msg, offset)
                        ustavka_value = raw_value  # храним как есть (990...1200)

                        print(f"[АТМ] type={type_atm}, pnum={pnum}, value={ustavka_value}")

                        with ustavka_lock:
                            if ustavka_value in ustavka_response:
                                ev, _ = ustavka_response[ustavka_value]
                                ustavka_response[ustavka_value] = (ev, ustavka_value)
                                ev.set()

                offset += plen

        else:
            # Остальные пакеты игнорируем
            print(f"[INFO] Необработанный пакет: ID={packet_id}, длина={len(msg)}")
              

def sock_forced_close():
    global sock_ref
    if sock_ref:
        try:
            sock_ref.shutdown(2)
            sock_ref.close()
        except:
            pass
    sock_ref = None


def client_thread(host, port, commands, callback=None, show_probe_dialog=None, com_agilent="COM3"):
    global sock_ref
    init_agilent_port(com_agilent)

    if not ser_a:
        print("Agilent не подключен — прерывание работы.")
        return

    try:
        settings_Agilent()

        # создаём сокет
        with socket.create_connection((host, port)) as sock:
            sock = socket.create_connection((host, port))
            sock_ref = sock  # <-- теперь sock существует

            send_thread = threading.Thread(
                target=send_commands_thread,
                args=(sock, commands, callback, show_probe_dialog)
            )
            receive_thread = threading.Thread(
                target=receive_messages,
                args=(sock,)
            )
            
            send_thread.start()
            receive_thread.start()

            while send_thread.is_alive() or receive_thread.is_alive():
                if stop_thread.is_set():
                    break
                sleep(0.1)
                
    except ConnectionError as e:
        if callback:
            safe_callback(callback, f"Ошибка подключения: {e}")

    finally:
        try:
            if sock:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
        except:
            pass

        sock_ref = None
        close_agilent_port()


if __name__ == "__main__":
    HOST, PORT = "192.168.0.176", 10001

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
