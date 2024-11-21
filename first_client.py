import socket
import json
from struct import pack, unpack
from time import time, sleep
import threading
import keyboard
import packet as pk

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
    command_for_cycle = ["vkl_30v", "increase_ogr_uab", "otkl_30v", "nabros", "decrease_ogr_uab_precise", "sbros"]

    # Отправка начальных команд
    sock.send(ku_complex.message())

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
                message_length = unpack('<H', buffer[:2])[0]

                # Проверяем, хватает ли данных для полного сообщения
                if len(buffer) < 2 + message_length:
                    break  # Если данных не хватает, выходим из цикла для получения оставшихся данных
                
                # Извлекаем полное сообщение
                message_data = buffer[2:2 + message_length]
                buffer = buffer[2 + message_length:]  # Удаляем из буфера обработанные данные

                # Расшифровка сообщения по формату 'HQHBH' (пример, нужно подстроить под ваш формат)
                try:
                    data = unpack('<hhhhh', message_data)
                    print("Received decoded message:", data)
                except Exception as e:
                    print("Error decoding message:", e)
                    continue

        except Exception as e:
            print("Error receiving message:", e)
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

def listen_for_keypress():
    global stop_thread
    # Ожидание нажатия клавиши 'q'
    while not stop_thread:
        if keyboard.is_pressed('q'):
            print("Key 'q' pressed, stopping the command cycle")
            stop_thread = True
            break

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 10001

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
