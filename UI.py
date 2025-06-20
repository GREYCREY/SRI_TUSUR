import tkinter as tk
from tkinter import ttk
import threading
import biab200 as logic  

HOST = "192.168.1.231"
PORT = 10001

root = tk.Tk()
root.title("Измерение БИАБ-200ЛИ")
root.geometry("1000x650")

# ===== Функции GUI =====
def start_measurement():
    try:
        start_idt = int(idt_entry.get()) - 1
    except ValueError:
        start_idt = 0

    status_label.config(text=f"Запуск измерения с IDT {start_idt + 1}...")

    # Запуск client_thread() из measure_biab.py в отдельном потоке
    t = threading.Thread(target=logic.client_thread, args=(HOST, PORT, commands, start_idt))
    t.start()

def stop_measurement():
    logic.stop_thread.set()
    status_label.config(text="Процесс остановлен пользователем")

def add_result_to_table(values):
    tree.insert("", "end", values=values)

# ===== Интерфейс =====
idt_frame = tk.Frame(root)
idt_frame.pack(pady=5)

tk.Label(idt_frame, text="Начальный IDT (1-12):").pack(side="left")
idt_entry = tk.Entry(idt_frame, width=5)
idt_entry.insert(0, "1")
idt_entry.pack(side="left", padx=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Старт", command=start_measurement).pack(side="left", padx=5)
tk.Button(button_frame, text="Остановить", command=stop_measurement).pack(side="left", padx=5)

status_label = tk.Label(root, text="Готово к запуску", bg="#eee", anchor="w")
status_label.pack(fill='x', pady=5)

columns = ("IDT", "Уставка", "Сопротивление", "Agilent", "Погрешность", "Статус")
tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150, anchor="center")
tree.pack(expand=True, fill="both", pady=5)

# ===== Загрузка JSON-команд =====
import json
with open("command_biab200.json", encoding="utf-8") as f:
    commands = json.load(f)

root.mainloop()
