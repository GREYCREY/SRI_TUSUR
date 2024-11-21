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
    offset = 0
    message_lenght, = struct.unpack_from('<H' , data, offset)
    offset += 2
    print(f"Длинна сообщения: {message_lenght}")
    timestamp, = struct.unpack_from('<Q', data, offset)
    offset +=8
    print(f"Время: {timestamp}")
    # Пакет
    packet, = struct.unpack_from('<H', data, offset)
    offset += 2
    print(f"ПАКЕТ: {packet}")

    # Количество параметров
    kol_param, = struct.unpack_from('<H', data, offset)
    offset += 2
    print(f"КолПарам: {kol_param}")

    # Если КолПарам > 0, то читаем параметры
    if kol_param > 0:
        while offset < len(data):
            # ТипАТМ
            type_atm, = struct.unpack_from('<H', data, offset)
            offset += 2
            print(f"ТипАТМ: {type_atm}")

            # Номер параметра
            param_number, = struct.unpack_from('<H', data, offset)
            offset += 2
            print(f"НомерПарам: {param_number}")

            # Длина параметра
            param_length, = struct.unpack_from('<B', data, offset)
            offset += 1
            print(f"ДлПарам: {param_length}")
            match param_length:
                case 8:
                    param_value = struct.unpack_from('<d', data, offset)
                    print(f"ЗначПарам: {param_value}")
                case 4:
                    param_value = struct.unpack_from('<I', data, offset)
                    print(f"ЗначПарам: {param_value}")
                case 1:
                    param_value = struct.unpack_from('<B', data, offset)
                    print(f"ЗначПарам: {param_value}")
                case _:
                    print("Other")
            # Значение параметра
            
            offset += 8
            #param_value = data[offset:offset + param_length]
            #offset += param_length
            

# Запуск декодирования
decode_packet(data4)
#decode_packet(data1)
#decode_packet(data2)
#decode_packet(data3)