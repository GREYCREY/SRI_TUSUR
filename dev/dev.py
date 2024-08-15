import os
from pathlib import WindowsPath
from collections import defaultdict
from csv import reader
import pandas as pd
import psutil 
def geting_file_paths():
    directory_path = input("Введите путь к директории с файлами: ")
    if not os.path.isabs(directory_path):
        print("Введенный путь не является абсолютным.")
        return []
    else:
        csv_files = []
        for file in WindowsPath(directory_path).glob('**/*.csv'):
            if file.is_file():
                csv_files.append(str(file))
        return csv_files
def close_open_file(file_path):
    for proc in psutil.process_iter(['pid', 'name', 'open_files']):
        try:
            for open_file in proc.info['open_files'] or []:
                if open_file.path == file_path:
                    print(f"Закрытие файла '{file_path}', который открыт процессом '{proc.info['name']}' (PID: {proc.info['pid']})")
                    proc.terminate()
                    proc.wait(timeout=3)
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False
def read_bom_csv(name_file: WindowsPath):
    readed_list = []
    name_and_family = []
    try:
        with name_file.open(encoding='cp1251', newline='') as vpcsvfile:
            rowreader = reader(vpcsvfile, delimiter=';')
            next(rowreader)  # delete heading string
            next(rowreader)
            for row in rowreader:
                data_pe = [row[0], row[1], row[2], row[3]]
                readed_list.append(data_pe)
            name_and_family = [row[4], row[5], row[6], row[7], row[8], row[9], row[10]]
    except PermissionError:
        print(f"Ошибка: Файл '{name_file}' уже открыт другим приложением.")
    except Exception as e:
        print(f"Ошибка при чтении файла '{name_file}': {e}")
    return readed_list, name_and_family

def is_file_open(file_path):
    # Получаем список всех процессов
    for proc in psutil.process_iter(['pid', 'name', 'open_files']):
        try:
            # Проверяем файлы, открытые каждым процессом
            open_files = proc.info['open_files']
            if open_files:
                for open_file in open_files:
                    if open_file.path == file_path:
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False
file_paths = geting_file_paths()
combined = pd.DataFrame()
for file in file_paths:
    try:
        data = pd.read_csv(file, encoding='cp1251')
        combined = pd.concat([combined, data])
    except PermissionError:
        print(f"Ошибка: Файл '{file}' уже открыт другим приложением.")
        if close_open_file(file):
            print(f"Процесс, удерживающий файл '{file}', был завершен.")
            try:
                data = pd.read_csv(file, encoding='cp1251')
                combined = pd.concat([combined, data])
            except Exception as e:
                print(f"Произошла ошибка при повторном чтении файла '{file}': {e}")
        else:
            print(f"Не удалось завершить процесс, удерживающий файл '{file}'.")
    except Exception as e:
        print(f"Произошла ошибка при чтении файла '{file}': {e}")

try:
    combined.to_csv('combined.csv', encoding='cp1251', index=False, sep=';')
except PermissionError:
    print(f"Ошибка: Не удается записать файл 'combined.csv'. Возможно, он уже открыт другим приложением.")
    
except Exception as e:
    print(f"Произошла ошибка при записи файла 'combined.csv': {e}")

p = WindowsPath(__file__)
t = p.with_name('combined.csv')
a, b = read_bom_csv(t)
name_of_file = p.with_name('answer.csv')
data_file = "combined.csv"
if is_file_open(data_file):
    print("Необходимо закрыть файл combined.csv")

counts = defaultdict(int)
try:
    with open(t, newline='', encoding='cp1251') as csvfile:
        csv_reader = reader(csvfile, delimiter=';')

        next(csv_reader)
        next(csv_reader)
            
        for row in csv_reader:
            key = row[0]
            counts[key] += 1
except PermissionError:
    print(f"Ошибка: Файл '{t}' уже открыт другим приложением.")
except Exception as e:
    print(f"Произошла ошибка при чтении файла '{t}': {e}")

for key, value in counts.items():
    print(f'{key}: {value}')
