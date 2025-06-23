import tkinter as tk
from tkinter import ttk
import threading
import json
import biab200 as logic   

HOST = "192.168.1.231"
PORT = 10001

# Загружаем команды
with open("command_biab200.json", encoding="utf-8") as f:
    commands = json.load(f)

root = tk.Tk()
root.title("Измерение БИАБ-200ЛИ")
root.geometry("1000x650")

# Функция старта
def start_measurement():
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

    
    # Запускаем клиент в потоке
    t = threading.Thread(
        target=logic.client_thread,
        args=(HOST, PORT, commands),
        daemon=True
    )
    t.start()

# Функция остановки
def stop_measurement():
    logic.stop_thread.set()
    status_label.config(text="Остановлено")

# Функция добавления строки в таблицу (вызывается из measure_biab.py)
def add_result_row(values):
    tree.insert("", "end", values=values)

# Интерфейс
frame = tk.Frame(root); frame.pack(pady=5)
tk.Label(frame, text="Номер БИАБ:").pack(side="left")
biab_entry = tk.Entry(frame, width=5); biab_entry.insert(0, "01"); biab_entry.pack(side="left", padx=5)
tk.Label(frame, text="Начальный IDT:").pack(side="left")
idt_entry = tk.Entry(frame, width=5); idt_entry.insert(0, "1"); idt_entry.pack(side="left", padx=5)
tk.Button(frame, text="Старт", command=start_measurement).pack(side="left", padx=5)
tk.Button(frame, text="Стоп", command=stop_measurement).pack(side="left", padx=5)
tk.Button(frame, text="Очистить", command=lambda: tree.delete(*tree.get_children())).pack(side="left", padx=5)

status_label = tk.Label(root, text="Готово к запуску", bg="#eee", anchor="w")
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
