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
def decode_packet(data):
    offset = 0
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

            # Значение параметра
            param_value = data[offset:offset + param_length]
            offset += param_length
            print(f"ЗначПарам: {param_value.hex()}")

# Запуск декодирования
decode_packet(data0)
decode_packet(data1)
decode_packet(data2)
decode_packet(data3)