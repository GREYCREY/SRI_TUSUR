import socket
import json
<<<<<<< HEAD
from struct import pack
from time import time, sleep
import threading
import keyboard
import packet as pk

# Глобальная переменная для остановки цикла
stop_thread = False
=======
from struct import pack, unpack
from time import time, sleep
import keyboard
import threading
>>>>>>> a4d257e54e8fd42e57f16e5bfb4dcbdec2ac1972

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
    ku_vkl_30v = pk.Short_Comanda_KU(1, 291) 
    ku_increase_ogr_uab = pk.Short_Comanda_KU(1, 300)
    ku_otkl_30v = pk.Short_Comanda_KU(1, 290)
    ku_nabros = pk.Short_Comanda_KU(1, 310)
    ku_decrease_ogr_uab_precise = pk.Short_Comanda_KU(1, 305)
    ku_sbros = pk.Short_Comanda_KU(1, 311)
    command_for_cycle = [ku_vkl_30v, ku_increase_ogr_uab, ku_otkl_30v, ku_nabros, ku_decrease_ogr_uab_precise, ku_sbros]

<<<<<<< HEAD
    # Отправка начальных команд
    sock.send(ku_complex.message())

    # Бесконечный цикл отправки команд
    while not stop_thread:
        for command in command_for_cycle:
            if stop_thread:
                print("Stopping the command cycle")
                break
            sock.send(command.message())
            sleep(3)

def client_thread(host, port, commands):
    global stop_thread
    try:
        # Установление соединения с сервером
        with socket.create_connection((host, port)) as sock:
            # Запуск потоков для приема сообщений и отправки команд
            send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands))
            send_thread.start()

            # Ожидание завершения отправки сообщений
            send_thread.join()
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
=======
def receive_message(sock):
    data_buffer = b''  # Буфер для хранения данных
    while True:
        # Получаем данные от сервера
        data = sock.recv(16384)
        if data:
            data_buffer += data
            print(f"Received {len(data)} bytes")

            # Пример разбора сообщения, если известен формат (например, первые 2 байта длина, следующие 8 - время, остальные - данные)
            while len(data_buffer) >= 10:  # Достаточно данных для заголовка
                message_len = unpack('<H', data_buffer[:2])[0]  # Длина сообщения (первые 2 байта)
                if len(data_buffer) < message_len + 2:
                    break  # Ждем, пока все данные не придут
                
                message_time = unpack('<Q', data_buffer[2:10])[0]  # Время сообщения (8 байт после длины)
                message_data = data_buffer[10:10 + message_len]  # Остальные данные сообщения

                # Вывод времени и данных
                print(f"Message received at {message_time / 1000:.3f}s: {message_data}")

                # Убираем обработанные данные из буфера
                data_buffer = data_buffer[10 + message_len:]
        else:
            print("No more data received")
            break

def send_commands_thread(sock, commands):
    command_names = ["complex_mode", "vkl_atm_biab", "vkl_biab"]
    command_for_cycle = ["vkl_30v", "increase_ogr_uab", "otkl_30v", "nabros", "decrease_ogr_uab_precise", "sbros"]
    
    # Отправка начальных команд
    for command in command_names:
        command_details = commands['short_comm'][command ]
        send_message(sock, command , command_details)

    # Бесконечный цикл отправки команд
    while True:
        for command in command_for_cycle:
            command_details = commands['short_comm'][command]
            send_message(sock, command, command_details)
            sleep(3)
        
        if keyboard.is_pressed('q'):
            print("Завершение цикла")
            break

def client_thread(host, port, commands):
    # Установление соединения с сервером
    with socket.create_connection((host, port)) as sock:
        # Запуск потоков для приема сообщений и отправки команд
        receive_thread = threading.Thread(target=receive_message, args=(sock,))
        send_thread = threading.Thread(target=send_commands_thread, args=(sock, commands))

        receive_thread.start()
        send_thread.start()

        receive_thread.join()
        send_thread.join()

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007

    # Загрузка команд из JSON-файла
    with open('command_biab100.json', 'r') as file:
        commands = json.load(file)

    # Запуск клиента
    client_thread(HOST, PORT, commands)
>>>>>>> a4d257e54e8fd42e57f16e5bfb4dcbdec2ac1972
