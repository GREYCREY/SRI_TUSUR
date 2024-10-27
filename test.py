import json
import struct
import time
import packet as pk
with open('command_biab100.json', 'r') as file:
    commands = json.load(file)

# Имена команд для кодирования
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