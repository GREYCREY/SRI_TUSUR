import socket
import json
from struct import pack
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
    ku_vkl_30v = pk.Short_Comanda_KU(1, 291) 
    ku_increase_ogr_uab = pk.Short_Comanda_KU(1, 300)
    ku_otkl_30v = pk.Short_Comanda_KU(1, 290)
    ku_nabros = pk.Short_Comanda_KU(1, 310)
    ku_decrease_ogr_uab_precise = pk.Short_Comanda_KU(1, 305)
    ku_sbros = pk.Short_Comanda_KU(1, 311)
    command_for_cycle = [ku_vkl_30v, ku_increase_ogr_uab, ku_otkl_30v, ku_nabros, ku_decrease_ogr_uab_precise, ku_sbros]

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
#ss
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
            print('')
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
