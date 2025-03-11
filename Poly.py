from openpyxl import load_workbook
from openpyxl.chart import ScatterChart, Reference, Series
from openpyxl.chart.axis import ChartLines
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import PH
import json_open
import minimalmodbus
import struct
import time

Address, COMport_PH, COMport_calibrator, COMport_Agilent = json_open.json_address_modbus()


# Функция для полиномиальной аппроксимации
def poly_fit(xy, p00, p10, p01, p11, p02):
    x, y = xy
    p20 = 0
    return p00 + p10 * x + p01 * y + p11 * x * y + p02 * y**2
     
def poly_coeffs_solver(file_path):
    razr = 0
    for address in Address:    
        # Открываем существующий Excel-файл
        workbook = load_workbook(file_path)
        # Проверяем, существует ли лист для данного address
        sheet_name = f"{str(address)}"
        if sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
        else:
            raise ValueError(f"Лист с названием '{sheet_name}' не найден в файле!")
        # Инициализируем списки для данных
        pschout = []
        temps = []
        vin = []
        # Считываем данные из колонок A (psch), B (temps), C (vin)
        for row_index, row in enumerate(sheet.iter_rows(min_row=2, min_col=1, max_col=4, values_only=True), start=2):
            if PH.Units_Range[0] == 1 or PH.Units_Range[0] == 3:
                psch_val = row[1]  # Данные из колонки 'B' (psch)
                temps_val = row[2]  # Данные из колонки 'C' (temps)
                vin_val = row[0]    # Данные из колонки 'A' (vin)
            if PH.Units_Range[0] == 5 or PH.Units_Range[0] == 7:
                cell_a = row[0] # Получаем значение из колонки A
                if cell_a is not None:  # Проверяем, что в ячейке есть данные
                    cell_a = float(cell_a)
                    # Выполняем расчет и записываем результат в колонку D
                    resI = cell_a / (0.075 / int(PH.Range))
                    sheet[f'D{row_index}'] = resI
                    workbook.save(file_path)
                psch_val = row[1]  # Данные из колонки 'A' (psch)
                temps_val = row[2]  # Данные из колонки 'B' (temps)
                vin_val = resI    # Данные из колонки 'D' (vin)
            # Проверяем, что данные не пустые, перед добавлением в список
            if psch_val is not None and temps_val is not None and vin_val is not None:
                pschout.append(psch_val)
                temps.append(temps_val)
                vin.append(vin_val)
        # Преобразование списков в numpy массивы
        pschout = np.array(pschout)
        temps = np.array(temps)
        vin = np.array(vin)
        # Подготовка данных для аппроксимации
        x_data = np.array(pschout)
        x_data = np.array(x_data, dtype=float)
        y_data = np.array(temps)
        z_data = np.array(vin)
        xy_data = np.vstack((x_data, y_data))
        # Начальные предположения для коэффициентов
        initial_guess = [0, 0, 0, 0, 0]  # Вектор начальных значений
        # Функция для полиномиальной аппроксимации второго порядка
        params, covariance = curve_fit(poly_fit, xy_data, z_data, p0=initial_guess, method='dogbox')
        # Получение коэффициентов полинома
        p00, p10, p01, p11, p02 = params
        p20 = 0
        print("-------------------------------------------------------------------------------")
        print("Коэффициенты полинома ПЩ {address}:")
        print(f"p00: {p00:.6e}, p10: {p10:.9f}, p01: {p01:.6e}, p11: {p11:.6e}, p02: {p02:.6e}")

        # Запись коэффициентов в столбец I начиная с первой свободной строки
        row_idx = 2  # Начинаем со второй строки (если первая — заголовок)
        # Записываем коэффициенты в колонку I
        sheet[f'I{row_idx}'] = p00
        sheet[f'I{row_idx+1}'] = p10
        sheet[f'I{row_idx+2}'] = p01
        sheet[f'I{row_idx+3}'] = p20  # Вставляем p20 = 0
        sheet[f'I{row_idx+4}'] = p11
        sheet[f'I{row_idx+5}'] = p02
        # Сохранение изменений в файл Excel
        workbook.save(file_path)

        # Визуализация исходных данных и аппроксимации
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Построение исходных данных (точки)
        ax.scatter(x_data, y_data, z_data, color='b', label='Данные')

        # Генерация сетки для графика аппроксимации
        x_surf = np.linspace(min(x_data), max(x_data), 100)
        y_surf = np.linspace(min(y_data), max(y_data), 100)
        x_surf, y_surf = np.meshgrid(x_surf, y_surf)
        z_surf = poly_fit((x_surf, y_surf), *params)

        # Построение аппроксимированной поверхности
        ax.plot_surface(x_surf, y_surf, z_surf, color='r', alpha=0.6, label='Аппроксимация')

        # Настройка подписей осей
        ax.set_xlabel('pschout')
        ax.set_ylabel('temps')
        ax.set_zlabel('vin')

        # Показать график
        plt.show()

        # Расчитать погрешности
        error_psch(file_path, workbook, address, p00, p10, p01, p20, p11, p02)
        grafs(address, file_path, workbook)
        print("-------------------------------------------------------------------------------")
        razr = int(input("Записать полученные калибровочные коэффициенты в ПЩ? \n"
        "1) Да. \n"
        "2) Нет. \n"
        "Введите цифру: "))
        print("-------------------------------------------------------------------------------")
        if razr == 1:
            calib_coeffs(address, p00, p10, p01, p20, p11, p02)
            print("Коэффициенты записаны в ПЩ.")
        else:
            print("Коэффициенты сохранены в Excel без записи в ПЩ.")
    
def error_psch(file_path, workbook, address, p00, p10, p01, p20, p11, p02):
    max_abs_f = None  # Для хранения максимального по модулю значения в колонке F
    max_abs_g = None  # Для хранения максимального по модулю значения в колонке G
    sheet_name = f"{str(address)}"
    
    if sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
    else:
        raise ValueError(f"Лист с названием '{sheet_name}' не найден в файле!")

    for row in range(2, sheet.max_row + 1):  # Начинаем со второй строки, так как обычно первая строка это заголовки
        cell_a = sheet[f'A{row}'].value
        cell_b = sheet[f'B{row}'].value
        cell_c = sheet[f'C{row}'].value
        cell_d = sheet[f'D{row}'].value

        # Проверяем, что в ячейках есть данные и они могут быть преобразованы в float
        if cell_a is not None and cell_b is not None and cell_c is not None and cell_d is not None:
            try:
                cell_a = float(cell_a)
                cell_b = float(cell_b)
                cell_c = float(cell_c)
                cell_d = float(cell_d)
            except ValueError as e:
                print(f"Ошибка преобразования значений в строке {row}: {e}")
                continue  # Пропустить эту строку, если произошла ошибка

            if PH.Units_Range[0] == 1 or PH.Units_Range[0] == 3:
                sheet[f'D{row}'] = 100 * ((cell_a - cell_b) / int(PH.Range))
                sheet[f'E{row}'] = p00 + p10 * cell_b + p01 * cell_c + p20 * cell_b**2 + p11 * cell_b * cell_c + p02 * cell_c**2
                cell_e = sheet[f'E{row}'].value
                cell_f = sheet[f'F{row}'] = 100 * ((cell_a - cell_d) / int(PH.Range))

                # Поиск максимального по модулю значения в колонке F
                if max_abs_f is None or abs(cell_f) > abs(max_abs_f):
                    max_abs_f = cell_f

            if PH.Units_Range[0] == 5 or PH.Units_Range[0] == 7:
                sheet[f'E{row}'] = 100 * ((cell_d - cell_b) / int(PH.Range))
                cell_f = sheet[f'F{row}'] = p00 + p10 * cell_b + p01 * cell_c + p20 * cell_b**2 + p11 * cell_b * cell_c + p02 * cell_c**2
                cell_g = sheet[f'G{row}'] = 100 * ((cell_d - cell_f) / int(PH.Range))

                # Поиск максимального по модулю значения в колонке G
                if max_abs_g is None or abs(cell_g) > abs(max_abs_g):
                    max_abs_g = cell_g

    workbook.save(file_path)
    # Вывод максимальных значений на консоль
    if PH.Units_Range[0] == 1 or PH.Units_Range[0] == 3:
        print("-------------------------------------------------------------------------------")
        print(f"Максимальное значение отклонения во всем диапазоне для ПЩ {address}: {max_abs_f:.5e}")
    if PH.Units_Range[0] == 5 or PH.Units_Range[0] == 7:
        print("-------------------------------------------------------------------------------")
        print(f"Максимальное значение отклонения во всем диапазоне для ПЩ {address}: {max_abs_g:.5e}")


def calib_coeffs(address, p00, p10, p01, p20, p11, p02):
    # Создаем экземпляр прибора
    instrument = minimalmodbus.Instrument(COMport_PH, address)
    # Записываем значение 0x3333
    instrument.write_register(42012, 0x3333)
    # Передача коэффициентов
    # Записываем p00, p01, p11, p02 как float
    for register, value in [(43024, p00), (43026, p01), (43030, p11), (43032, p02)]:
        packed_value = struct.pack('>f', value)  # Упаковываем float
        registers = struct.unpack('>HH', packed_value)  # Распаковываем в два 16-битных числа
        # Записываем оба регистра
        instrument.write_register(register, registers[1], functioncode=16)  # Старший регистр
        instrument.write_register(register + 1, registers[0], functioncode=16)  # Младший регистр
    # Записываем p10 как double
    packed_value = struct.pack('>d', p10)  # Упаковка double в 8 байт
    registers = struct.unpack('>HHHH', packed_value)  # Распаковка в 4 16-битных числа
    # Записываем регистры для p10
    instrument.write_register(43020, registers[3], functioncode=16)      # Старший регистр 1
    instrument.write_register(43021, registers[2], functioncode=16)      # Старший регистр 2
    instrument.write_register(43022, registers[1], functioncode=16)      # Младший регистр 1
    instrument.write_register(43023, registers[0], functioncode=16)      # Младший регистр 2
    # p20 передается как целое число
    instrument.write_register(43028, p20)  # p20
    # Записываем значение 0x27D9
    try:
        minimalmodbus.Instrument(COMport_PH, address).write_register(42013, 0x27D9)
    except minimalmodbus.NoResponseError:
        print("Сохранение калибровочных коэффициентов в памяти ПЩ " + str(address))
        print("-------------------------------------------------------------------------------")
        time.sleep(5)

def grafs(address, file_path, workbook):
    
    sheet = workbook[f"{str(address)}"]

    max_row = sheet.max_row

    # Проверяем, что столбцы не пусты (если нужно убедиться, что все строки заполнены)
    while max_row > 2 and (sheet.cell(row=max_row, column=3).value is None or sheet.cell(row=max_row, column=5).value is None):
        max_row -= 1
        
    if PH.Units_Range[0] == 1 or PH.Units_Range[0] == 3:
        # Определяем диапазоны для оси X и Y
        x_values = Reference(sheet, min_col=3, min_row=2, max_row=max_row)  # Столбец для X данных
        y_values = Reference(sheet, min_col=4, min_row=2, max_row=max_row)  # Столбец для Y данных        
    if PH.Units_Range[0] == 5 or PH.Units_Range[0] == 7:
        # Определяем диапазоны для оси X и Y
        x_values = Reference(sheet, min_col=3, min_row=2, max_row=max_row)  # Столбец для X данных
        y_values = Reference(sheet, min_col=5, min_row=2, max_row=max_row)  # Столбец для Y данных
        
    # Создаем точечную диаграмму
    chart = ScatterChart()

    # Убираем название диаграммы
    chart.title = None

    # Настраиваем оси (убираем названия, включаем отображение осей)
    chart.x_axis.title = None  # Убираем название оси X
    chart.y_axis.title = None  # Убираем название оси Y
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.x_axis.majorGridlines = None  # Отключаем сетку для x-оси
    chart.y_axis.majorGridlines = None  # Отключаем сетку для y-оси

        
    # Убираем легенду
    chart.legend = None

    # Указываем тип точечной диаграммы (только маркеры)
    series = Series(y_values, x_values)
    series.marker.symbol = "circle"  # Задаем маркеры (например, круги)
    series.graphicalProperties.line.noFill = True  # Отключаем линии

    # Добавляем серию данных на диаграмму
    chart.series.append(series)

    # Добавляем график на лист
    sheet.add_chart(chart, "L2")  # Место, где появится график (ячейка D4)

    # Определяем диапазоны для оси X и Y для второго графика
    if PH.Units_Range[0] == 1 or PH.Units_Range[0] == 3:
        x_values_2 = Reference(sheet, min_col=3, min_row=2, max_row=max_row)  # Столбец для X данных
        y_values_2 = Reference(sheet, min_col=6, min_row=2, max_row=max_row)  # Используем другие данные для второго графика
    if PH.Units_Range[0] == 5 or PH.Units_Range[0] == 7:
        x_values_2 = Reference(sheet, min_col=3, min_row=2, max_row=max_row)  # Столбец для X данных
        y_values_2 = Reference(sheet, min_col=7, min_row=2, max_row=max_row)  # Используем другие данные для второго графика

    # Создаем второй точечный график
    chart2 = ScatterChart()

    # Настраиваем оси и график для второго графика
    chart2.x_axis.title = None
    chart2.y_axis.title = None
    chart2.x_axis.delete = False
    chart2.y_axis.delete = False
    chart2.x_axis.majorGridlines = None  # Отключаем сетку для x-оси
    chart2.y_axis.majorGridlines = None  # Отключаем сетку для y-оси

    chart2.legend = None
    
    series2 = Series(y_values_2, x_values_2)
    series2.marker.symbol = "circle"
    series2.graphicalProperties.line.noFill = True

    chart2.series.append(series2)

    # Добавляем второй график на лист в ячейку L20
    sheet.add_chart(chart2, "L20")
    
    # Сохраняем изменения в файл
    workbook.save(file_path)

