import tkinter as tk
from tkinter import ttk
import threading
import json
import biab200 as logic
import sys, os   

PORT = 10001

# Загружаем команды

def show_probe_dialog():
    dialog = tk.Toplevel()
    dialog.title("Перестановка щупов")
    dialog.geometry("350x150")
    dialog.grab_set()   # окно модальное

    tk.Label(dialog, text="Переставьте щупы на следующий IDT").pack(pady=10)

    result = {"action": None}

    def on_repeat():
        result["action"] = "repeat"
        dialog.destroy()

    def on_continue():
        result["action"] = "continue"
        dialog.destroy()

    def on_stop():
        result["action"] = "stop"
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Повторить", width=10, command=on_repeat).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Продолжить", width=10, command=on_continue).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Стоп", width=10, command=on_stop).pack(side="left", padx=5)

    dialog.wait_window()
    return result["action"]

root = tk.Tk()
root.title("Измерение БИАБ-200ЛИ")
root.geometry("1000x650")

# Функция старта
def start_measurement():
    logic.stop_idt_cycle.clear
    # читаем поля
    biab_num = biab_entry.get().strip() or "01"
    try:
        start_idt = int(idt_entry.get()) - 1
    except ValueError:
        start_idt = 0

    status_label.config(text=f"Запуск: БИАБ {biab_num}, IDT {start_idt+1}…")
    # Устанавливаем глобальные параметры в logic
    logic.start_idt = start_idt
    logic.stop_thread.clear()   # сброс флага остановки

    host = HOST.get()
    # Запускаем клиент в потоке
    com_agilent = com_entry.get().strip() or "COM3"
    t = threading.Thread(
        target=logic.client_thread,
        args=(host, PORT, commands, add_result_row, com_agilent, show_probe_dialog),
        daemon=True
    )
    t.start()

# Функция остановки
def stop_measurement():
    logic.stop_idt_cycle.set() 
    status_label.config(text="Остановлено")

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

with open(resource_path("command_biab200.json"), encoding="utf-8") as f:
    commands = json.load(f)
    
# Функция добавления строки в таблицу (вызывается из measure_biab.py)
def add_result_row(values):
    
    if isinstance(values, str):
        update_status(values)
        return
    
    item_id = tree.insert("", "end", values=values)
    tree.yview_moveto(1.0)  # прокручивает в самый низ
    tree.see(item_id)       

'''def continue_measurement():
    logic.wait_for_input_event.set()
'''
def update_status(text, color="black"):
    if color is None:
        color = "red" if "Ошибка" in text else "black"
    status_label.config(text=text, fg=color)
    status_label.update_idletasks()
    
# Интерфейс
frame = tk.Frame(root); frame.pack(pady=5)

tk.Label(frame, text="IP:").pack(side="left")
HOST = tk.Entry(frame, width=20)
HOST.insert(0,"192.168.0.176")
HOST.pack(side="left", padx=5)

tk.Label(frame, text="COM Agilent:").pack(side="left")
com_entry = tk.Entry(frame, width=8)
com_entry.insert(0, "COM3")  # значение по умолчанию
com_entry.pack(side="left", padx=5)

tk.Label(frame, text="Номер БИАБ:").pack(side="left")
biab_entry = tk.Entry(frame, width=5); biab_entry.insert(0, "01"); biab_entry.pack(side="left", padx=5)

tk.Label(frame, text="Начальный IDT:").pack(side="left")
idt_entry = tk.Entry(frame, width=5); idt_entry.insert(0, "1"); idt_entry.pack(side="left", padx=5)

tk.Button(frame, text="Старт", command=start_measurement).pack(side="left", padx=5)

#tk.Button(frame, text= "Продолжить ", command= continue_measurement).pack(side="left", padx=5)

tk.Button(frame, text="Стоп", command=stop_measurement).pack(side="left", padx=5)

tk.Button(frame, text="Очистить", command=lambda: tree.delete(*tree.get_children())).pack(side="left", padx=5)


status_label = tk.Label(root, text="", bg="#eee", anchor="w")
status_label.pack(fill="x", pady=5)

columns = ("IDT","Уставка","Знач. БИАБ","Знач. прибора","Погрешность","Статус","Дата")
tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=130, anchor="center")
tree.pack(expand=True, fill="both", pady=5)

scrollbar = tk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.pack(side="right", fill="y")

root.mainloop()
