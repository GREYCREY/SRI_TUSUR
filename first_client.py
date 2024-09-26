import socket
import json
from struct import pack, unpack
from time import time
import keyboard

def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    return pack('<H', len(data)) + pack('<Q', int(t_time * 1000)) + data

def send_message(sock, command_name, command_details):
    # Закодировать команду
    encoded_command = komm(command_details)
    
    # Получить текущее время
    current_time = time()
    
    # Создать сообщение
    message = mess(encoded_command, current_time)
    
    # Отправить сообщение серверу
    print(f"Sending {command_name}: {message}")
    sock.sendall(message)
    print(f"Sent {command_name}")

def receive_message(sock):
    # Ожидание данных от сервера
    data = sock.recv(16384)
    print(f"Received {len(data)} bytes")

    # Пример декодирования сообщения
    command_format = '<HQHBH'
    #decoded_message = unpack(command_format, data[:16])
    #print(f"Decoded message: {decoded_message}")

    return data

def client1(host, port):
    # Загрузка команд из JSON-файла
    with open('command_biab100.json', 'r') as file:
        commands = json.load(file)
    
    command_names = ["complex_mode", "vkl_atm_biab", "vkl_biab"]
    command_for_cycle = ["vkl_30v", "increase_ogr_uab", "otkl_30v", "nabros", "decrease_ogr_uab_precise", "sbros"]

    # Установление соединения с сервером
    with socket.create_connection((host, port)) as sock:
        # Процесс каждой команды
        for command_name in command_names:
            command_details = commands['short_comm'][command_name]

            # Отправка сообщения
            send_message(sock, command_name, command_details)

            # Ожидание ответа от сервера
            data = receive_message(sock)

        while True:
            for command in command_for_cycle:
                command_details = commands['short_comm'][command]
                send_message(sock, command, command_details)
            
            if keyboard.is_pressed('q'):
                print("Завершение цикла")
                break

        input('Press Enter to close connection')
        print("Closing connection")

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    client1(HOST, PORT)
