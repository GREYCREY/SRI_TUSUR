import tkinter as tk
from tkinter import ttk
import threading
import time
import random
from datetime import date
root = tk.Tk()
root.title("Измерение БИАБ-200ЛИ Тестовый")
root.geometry("1000x650")

# ===== Функции =====
def start_test_measurement():
    status_label.config(text="Тестовый запуск...")
    def simulate():
        for i in range(1, 13):  # Пример: IDT 1, 2, 3
            for ust in range(990, 1005, 5):
                fake_value = round(random.uniform(95, 105), 2)
                fault = round(abs((ust / 10) - fake_value), 2)
                status = "OK" if fault <= 0.1 else "НеОК"
                today = date.today()
                tree.insert("", "end", values=(i, ust / 10, fake_value, fake_value, fault, status, today))
                time.sleep(0.3)
        status_label.config(text="Тест завершен")
    threading.Thread(target=simulate).start()

def clear_table():
    for row in tree.get_children():
        tree.delete(row)
    status_label.config(text="Очищено")

# ===== Интерфейс =====
frame = tk.Frame(root)
frame.pack(pady=5)

tk.Label(frame, text="Номер БИАБ:").pack(side="left")
biab_entry = tk.Entry(frame, width=5).pack(side="left", padx=5)
tk.Label(frame, text="Начальный IDT (Тест):").pack(side="left")
idt_entry = tk.Entry(frame, width=5)
idt_entry.insert(0, "10")
idt_entry.pack(side="left", padx=5)

tk.Button(frame, text="Запустить тест", command=start_test_measurement).pack(side="left", padx=5)
tk.Button(frame, text="Остатновить").pack(side="left", padx=5)
tk.Button(frame, text="Очистить", command=clear_table).pack(side="left", padx=5)

        
status_label = tk.Label(root, text="Готово к запуску", bg="#eee", anchor="w")
status_label.pack(fill='x', pady=5)

columns = ("IDT", "Уставка", "Значение БИАБ", "Значение мультиметр", "Погрешность", "Статус", "Дата")
tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150, anchor="center")
tree.pack(expand=True, fill="both", pady=5)

scrollbar = tk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.pack(side="right", fill="y")

root.mainloop()
