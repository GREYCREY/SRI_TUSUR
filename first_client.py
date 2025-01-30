import socket
import json
from struct import pack, unpack_from, error
import numpy as np
from time import sleep
import threading
from keyboard import is_pressed
import packet as pk
from datetime import datetime, timedelta

# Глобальная переменная для остановки цикла
stop_thread = threading.Event()

def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    return pack('<H', len(data)) + pack('<Q', int(t_time * 1000)) + data

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
    
    while not stop_thread.is_set(): 
        for setting in range(2900 , 4100, 200): 
            print(setting) 
            if stop_thread.is_set(): 
                print("Stopping the command cycle") 
                break 
            command = pk.Short_Comanda_KU(5, 0, 1) 
            #print(command.message()) 
            sock.send(command.set_ustavka(setting, 3)) 
            sleep(5) 
        for invers_setting in np.arange(4100, 2900, -200): 
            print(invers_setting) 
            if stop_thread.is_set(): 
                print("Stopping the command cycle") 
                break 
            invers_command = pk.Short_Comanda_KU(5, 0, 1) 
            #print(command.message()) 
            sock.send(invers_command.set_ustavka(invers_setting, 3)) 
            sleep(5)

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
    '''Расшифровка сообщения'''
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
        data = data[message_length + 2:]  # Убираем обработанную часть

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
                print("Расшифровка квитанции")
                
                # Чтение КодВозврата
                kod_vozvrata, = unpack_from('<H', current_message, 12)
                print(f"КодВозврата: {kod_vozvrata}")

                # Чтение КолПарам
                kol_param, = unpack_from('<H', current_message, 14)
                print(f"Количество параметров: {kol_param}")

                # Чтение ТекстПарам
                param_data = current_message[16:]  # Срез данных для параметров
                for _ in range(kol_param):
                    # Считываем текст параметра
                    # Строка заканчивается нулевым байтом (STRING0)
                    null_index = param_data.find(b'\x00')
                    if null_index == -1:  # Не найден нулевой байт, значит ошибка
                        print("Ошибка: Не найден нулевой байт в данных параметра!")
                        break
                    
                    text_param = param_data[:null_index].decode('cp1251', errors='replace')
                    print(f"ТекстПарам: {text_param}")
                    param_data = param_data[null_index + 1:]  # Убираем прочитанный параметр
            else:
                # Чтение количества параметров
                kol_param, = unpack_from('<H', current_message, 12)
                print(f"Количество параметров: {kol_param}")

                # Обработка других параметров
                param_data = current_message[14:]  # Срез данных для параметров
                for _ in range(kol_param):
                    if len(param_data) < 5:  # Минимум 5 байт на параметр (тип, номер, длина)
                        print("Ошибка: Данные параметров выходят за пределы сообщения!")
                        break

                    # Чтение ТипАТМ, Номер параметра и Длины
                    type_atm, param_number, param_length = unpack_from('<HHB', param_data)
                    param_data = param_data[5:]  # Убираем прочитанные 5 байт
                    print(f"Тип АТМ: {type_atm}, Номер параметра: {param_number}, Длина параметра: {param_length}")

                    if len(param_data) < param_length:
                        print("Ошибка: Недостаточно данных для значения параметра!")
                        break

                    # Чтение значения параметра
                    if param_length == 2:  
                        param_value, = unpack_from('<h', param_data)
                        param_value = round(param_value, 3) 
                        param_data = param_data[8:]
                    elif param_length == 1:  
                        param_value, = unpack_from('<B', param_data)
                        param_value = round(param_value, 3)  
                        param_data = param_data[4:]
                    elif param_length == 4:  
                        param_value, = unpack_from('<f', param_data)
                        param_data = param_data[1:]
                    else:  # Для других длин, обрабатываем как текст или пропускаем
                        param_value = param_data[:param_length].decode('utf-8', errors='replace')
                        param_data = param_data[param_length:]

                    # Проверяем, изменилось ли значение параметра
                    if param_value != previous_param_value:
                        print(f"Значение параметра: {param_value}")
                        previous_param_value = param_value  # Обновляем предыдущее значение
                    else:
                        print("Параметр не изменился, пропускаем вывод")

        except error:
            print("Ошибка: Неверная структура данных!")
            break

        print("Конец сообщения\n")

def listen_for_keypress(sock):
    # Ожидание нажатия клавиши 'q'
    while not stop_thread.is_set():
        if is_pressed('q'):
            print("Key 'q' pressed, stopping the command cycle")
            ku_otkl_biab = pk.Short_Comanda_KU(1, 287)
            ku_otkl_atm_biab = pk.Short_Comanda_KU(1, 1001)
            ku_autonomous_mode = pk.Short_Comanda_KU(1, 999)
            stop_commands = [ku_otkl_biab, ku_otkl_atm_biab, ku_autonomous_mode]
            for command in stop_commands:
                sock.send(command.message())
            stop_thread.set()
            break

def client_thread(host, port, commands):
    try:
        # Установление соединения с сервером
        with socket.create_connection((host, port)) as sock:
            # Запуск потоков для приема сообщений и отправки команд
            send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands))
            '''receive_thread = threading.Thread(target=receive_messages, args=(sock,))'''
            send_thread.start()
            '''receive_thread.start()'''

            # Запуск потока для прослушивания нажатия клавиши 'q'
            keypress_thread = threading.Thread(target=listen_for_keypress, args=(sock,))
            keypress_thread.start()

            # Ожидание завершения потоков
            send_thread.join()
            '''receive_thread.join()'''
            keypress_thread.join()
    except ConnectionError:
        print("Server connection failed!")
    finally:
        stop_thread.set()

if __name__ == "__main__":
    HOST, PORT = "192.168.1.150q", 10001

    # Загрузка команд из JSON-файла
    with open('command_biab200.json', 'r', encoding='utf-8') as file:
        commands = json.load(file)

    # Запуск клиента в отдельном потоке
    client_thread_thread = threading.Thread(target=client_thread, args=(HOST, PORT, commands))
    client_thread_thread.start()

    # Ожидание завершения всех потоков
    client_thread_thread.join()
