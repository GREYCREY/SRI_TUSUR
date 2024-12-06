#добавил комментарий
import json
from struct import pack, unpack_from, error
from datetime import datetime, timedelta

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



from struct import unpack_from
from datetime import datetime, timedelta

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
                    
                    text_param = param_data[:null_index].decode('utf-8', errors='replace')
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


# Запуск декодирования
decode_packet(data4)
#decode_packet(data1)
#decode_packet(data2)
#decode_packet(data3)