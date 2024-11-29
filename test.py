#добавил комментарий
import json
import struct

import time
import packet as pk
with open('command_biab100.json', 'r') as file:
    commands = json.load(file)

# Имена команд для кодирования
def encoding():
    command_names = ["vkl_30v", "increase_ogr_uab", "otkl_30v", "nabros", "decrease_ogr_uab_precise", "sbros"]

    # Обработка и кодирование каждой команды
    for command_name in command_names:
        command_details = commands['short_comm'][command_name]
        type_ku = command_details['type_ku']
        cod_ku = command_details['cod_ku']
        
        # Создание экземпляра команды
        command = pk.Short_Comanda_KU(type_ku, cod_ku)
        
        # Получение закодированного сообщения
        encoded_command = command.message()
        
        print(f"Encoded {command_name}: {command}")
data0 = b'3\x00\xd0\x87\xe1\xa3\xb1#\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08\x00\x00\x00\x00-\xb2\xf5?'
data1 = b'\x80\xd5\xd6\xa3\xb1#\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08\x00\x00\x00\x00-\xb2\xf5?'
data2 = b'3\x00\x90\xfd\xab\xea\xad#\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x00\x00\x00\x00\x00\x00-\xb2\xf5?'
data3 = b'@\x17\x03\xeb\xad#\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x00\x00\x00\xa0\x900\x00\x00\x00-\xb2\xf5?'
data4 = b'3\x000\xcf!\x9bw,\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x9a\x99\x99\x99\x99\x99\xb9\xbf\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08o\x12\x83\xc0\xca\xa1\xf5?3\x00\x80\x81,\x9bw,\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x9a\x99\x99\x99\x99\x99\xb9\xbf\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08o\x12\x83\xc0\xca\xa1\xf5?\x10\x00\xb0\x08.\x9bw,\xdb\x01\x01\x00\x02\x00\x00\x00\x00\x00#\x00\xc0\xd7>\x9bw,\xdb\x01\x01\x00\x02\x00\x02\x00\x01\x00\xea\xee\xec\xe0\xed\xe4\xe0 \xe7\xe0\xef\xf0\xe5\xf8\xe5\xed\xe0!\x003\x000\xb5R\x9bw,\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x9a\x99\x99\x99\x99\x99\xb9\xbf\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08\xd9\xce\xf7S\xe3\xa5\xf5?3\x00\x80g]\x9bw,\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x9a\x99\x99\x99\x99\x99\xb9\xbf\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08\xd9\xce\xf7S\xe3\xa5\xf5?3\x000\x9b\x83\x9bw,\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x9a\x99\x99\x99\x99\x99\xb9\xbf\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08o\x12\x83\xc0\xca\xa1\xf5?3\x00\x80M\x8e\x9bw,\xdb\x01\x04\x00\x03\x00\x01\x00\x01\x00\x08\x9a\x99\x99\x99\x99\x99\xb9\xbf\x01\x00\x02\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x08o\x12\x83\xc0\xca\xa1\xf5?3\x00'



def decode_packet(data):
    while len(data) > 2:  # Минимум 2 байта для длины сообщения
        # Чтение длины сообщения
        message_length, = struct.unpack_from('<H', data)
        print(f"Длина сообщения: {message_length}")

        if len(data) < message_length + 2:  # Проверяем, хватает ли данных для сообщения
            print("Ошибка: Сообщение выходит за пределы данных!")
            break

        # Извлекаем текущее сообщение
        current_message = data[:message_length + 2]
        data = data[message_length + 2:]  # Убираем обработанную часть

        try:
            # Чтение времени
            timestamp, = struct.unpack_from('<Q', current_message, 2)
            print(f"Время: {timestamp}")

            # Чтение пакета
            packet, = struct.unpack_from('<H', current_message, 10)
            print(f"Пакет: {packet}")

            # Чтение количества параметров
            kol_param, = struct.unpack_from('<H', current_message, 12)
            print(f"Количество параметров: {kol_param}")

            # Обработка параметров
            param_data = current_message[14:]  # Срез данных для параметров
            for _ in range(kol_param):
                if len(param_data) < 5:  # Минимум 5 байт на параметр (тип, номер, длина)
                    print("Ошибка: Данные параметров выходят за пределы сообщения!")
                    break

                # Чтение ТипАТМ, Номер параметра и Длины
                type_atm, param_number, param_length = struct.unpack_from('<HHB', param_data)
                param_data = param_data[5:]  # Убираем прочитанные 5 байт
                print(f"Тип АТМ: {type_atm}, Номер параметра: {param_number}, Длина параметра: {param_length}")

                if len(param_data) < param_length:
                    print("Ошибка: Недостаточно данных для значения параметра!")
                    break

                # Чтение значения параметра
                if param_length == 8:  # Если длина 8 байт, интерпретируем как double
                    param_value, = struct.unpack_from('<d', param_data)
                    print(f"Значение параметра: {param_value}")
                    param_data = param_data[8:]
                elif param_length == 4:  # Если длина 4 байта, интерпретируем как unsigned int
                    param_value, = struct.unpack_from('<I', param_data)
                    print(f"Значение параметра: {param_value}")
                    param_data = param_data[4:]
                elif param_length == 1:  # Если длина 1 байт, интерпретируем как unsigned byte
                    param_value, = struct.unpack_from('<B', param_data)
                    print(f"Значение параметра: {param_value}")
                    param_data = param_data[1:]
                else:  # Для других длин, обрабатываем как текст или пропускаем
                    param_value = param_data[:param_length].decode('utf-8', errors='replace')
                    print(f"Значение параметра (текст): {param_value}")
                    param_data = param_data[param_length:]

        except struct.error:
            print("Ошибка: Неверная структура данных!")
            break

        print("Конец сообщения\n")

# Запуск декодирования
decode_packet(data4)
#decode_packet(data1)
#decode_packet(data2)
#decode_packet(data3)