import asyncio
import json
from struct import pack, unpack
from time import time, sleep

def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    return pack('<H', len(data)) + pack('<Q', int(t_time * 1000)) + data

# Функция отправки сообщений (writer)
async def send_message(writer, command_name, command_details):
    # Закодировать команду
    encoded_command = komm(command_details)
    
    # Получить текущее время
    current_time = time()
    
    # Создать сообщение
    message = mess(encoded_command, current_time)
    
    # Отправить сообщение серверу
    print(f"Sending {command_name}: {message}")
    writer.write(message)
    await writer.drain()
    print(f"Sent {command_name}")

# Функция получения сообщений (reader)
async def receive_message(reader):
    # Ожидание данных от сервера
    data = await reader.read(16384)  # Чтение данных от сервера
    print(f"Received {len(data)} bytes")

    # Пример декодирования сообщения
    command_format = '<HQHBH'
    decoded_message = unpack(command_format, data[:16])  # Декодирование первых 16 байтов
    print(f"Decoded message: {decoded_message}")
    
    return data

# Основная функция
async def client1(host, port):
    # Загрузка команд из JSON-файла
    with open('command_biab100.json', 'r') as file:
        commands = json.load(file)
    
    command_names = ["complex_mode", "vkl_atm_biab", "vkl_biab"]

    # Установление соединения с сервером
    reader, writer = await asyncio.open_connection(host, port)

    # Процесс каждой команды
    for command_name in command_names:
        command_details = commands['short_comm'][command_name]

        # Отправка сообщения
        await send_message(writer, command_name, command_details)

        # Ожидание ответа от сервера
        data = await receive_message(reader)
        time.sleep(5)
        

    # Обработка ответа (можно добавить вашу логику обработки здесь)
    input('Press Enter to close connection')
    # Закрытие соединения
    print("Closing connection")
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    asyncio.run(client1(HOST, PORT))
