import socket
import json
from struct import pack, unpack_from, error
from time import sleep
import threading
from keyboard import is_pressed
import packet as pk
from datetime import datetime, timedelta

# Глобальная переменная для остановки цикла
stop_thread = False

def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    return pack('<H', len(data)) + pack('<Q', int(t_time * 1000)) + data

def send_commands_thread(sock, commands):
    global stop_thread  # Используем глобальную переменную для контроля
    ku_complex = pk.Short_Comanda_KU(1, 998)
    ku_vkl_atm_biab = pk.Short_Comanda_KU(1, 1000)
    ku_vkl_biab = pk.Short_Comanda_KU(1, 286)
    command_for_cycle = ["nabros", "sbros"]

    # Отправка начальных команд
    sock.send(ku_complex.message())
    sock.send(ku_vkl_atm_biab.message())
    sock.send(ku_vkl_biab.message())

    # Бесконечный цикл отправки команд
    while not stop_thread:
        for command_name in command_for_cycle:
            if stop_thread:
                print("Stopping the command cycle")
                break
            command_details = commands['short_comm'][command_name]
            type_ku = command_details['type_ku']
            cod_ku = command_details['cod_ku']
            command = pk.Short_Comanda_KU(type_ku, cod_ku)
            sock.send(command.message())
            sleep(3)

def receive_messages(sock):
    '''Получение и расшифровка сообщений с сервера'''
    global stop_thread
    buffer = b''  # Буфер для накопления данных

    while not stop_thread:
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
                    if param_length == 8:  # Если длина 8 байт, интерпретируем как double
                        param_value, = unpack_from('<d', param_data)
                        param_value = round(param_value, 3)  # Округляем до 3 знаков
                        param_data = param_data[8:]
                    elif param_length == 4:  # Если длина 4 байта, интерпретируем как unsigned int
                        param_value, = unpack_from('<I', param_data)
                        param_value = round(param_value, 3)  # Округляем до 3 знаков
                        param_data = param_data[4:]
                    elif param_length == 1:  # Если длина 1 байт, интерпретируем как unsigned byte
                        param_value, = unpack_from('<B', param_data)
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
    global stop_thread
    # Ожидание нажатия клавиши 'q'
    while not stop_thread:
        if is_pressed('q'):
            print("Key 'q' pressed, stopping the command cycle")
            ku_otkl_biab = pk.Short_Comanda_KU(1, 287)
            ku_otkl_biab = pk.Short_Comanda_KU(1, 1001)
            ku_autonomous_mode = pk.Short_Comanda_KU(1,999)
            stop_commands = [ku_otkl_biab, ku_otkl_biab, ku_autonomous_mode]
            for command in stop_commands:
                sock.send(command.message())
            stop_thread = True
            break

def client_thread(host, port, commands):
    global stop_thread
    try:
        # Установление соединения с сервером
        with socket.create_connection((host, port)) as sock:
            # Запуск потоков для приема сообщений и отправки команд
            send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands))
            receive_thread = threading.Thread(target=receive_messages, args=(sock,))
            send_thread.start()
            receive_thread.start()

            # Ожидание завершения потоков
            send_thread.join()
            receive_thread.join()
    except ConnectionError:
        print("Server connection failed!")
    finally:
        stop_thread = True



if __name__ == "__main__":
    HOST, PORT = "169.254.59.150", 10001

    # Загрузка команд из JSON-файла
    with open('command_biab100.json', 'r') as file:
        commands = json.load(file)

    # Запуск клиента в отдельном потоке
    client_thread_thread = threading.Thread(target=client_thread, args=(HOST, PORT, commands))
    client_thread_thread.start()

    # Запуск потока для прослушивания нажатия клавиши 'q'
    listen_for_keypress_thread = threading.Thread(target=listen_for_keypress)
    listen_for_keypress_thread.start()

    # Ожидание завершения всех потоков
    client_thread_thread.join()
    listen_for_keypress_thread.join()
