import tkinter as tk
from tkinter import ttk
import threading
import json
import sys
import os

import biab200 as idt_logic   # существующий модуль ИДТ
import iae    as iae_logic    # новый модуль ИАЭ

PORT = 10001


# ──────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────────────────────────

def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


with open(resource_path("command_biab200.json"), encoding="utf-8") as _f:
    commands = json.load(_f)


# ══════════════════════════════════════════════════════════════════════════════
# Главное окно + Notebook
# ══════════════════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("БИАБ-200ЛИ – Измерения")
root.geometry("1050x680")

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both", padx=5, pady=5)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 – ИДТ  (существующая функциональность)
# ══════════════════════════════════════════════════════════════════════════════

tab_idt = ttk.Frame(notebook)
notebook.add(tab_idt, text="  ИДТ (сопротивление)  ")


# ── Диалог перестановки щупов ИДТ ────────────────────────────────────────────

def show_probe_dialog_idt():
    dialog = tk.Toplevel(root)
    dialog.title("ИДТ – Перестановка щупов")
    dialog.geometry("360x150")
    dialog.grab_set()
    x = root.winfo_x() + (root.winfo_width()  // 2) - 180
    y = root.winfo_y() + (root.winfo_height() // 2) - 75
    dialog.geometry(f"360x150+{x}+{y}")

    tk.Label(dialog, text="Переставьте щупы на следующий ИДТ",
             font=("", 11)).pack(pady=12)

    result = {"action": None}

    def on_stop():
        result["action"] = "stop"
        idt_logic.stop_idt_cycle.set()
        idt_logic.stop_thread.set()
        update_status_idt("Остановлено")
        root.after(3000, lambda: btn_start_idt.config(state="normal"))
        dialog.destroy()

    def on_repeat():
        result["action"] = "repeat"
        dialog.destroy()

    def on_continue():
        result["action"] = "continue"
        dialog.destroy()

    f = tk.Frame(dialog); f.pack(pady=8)
    tk.Button(f, text="Повторить",  width=11, command=on_repeat).pack(side="left", padx=5)
    tk.Button(f, text="Продолжить", width=11, command=on_continue).pack(side="left", padx=5)
    tk.Button(f, text="Стоп",       width=11, command=on_stop).pack(side="left", padx=5)

    dialog.wait_window()
    return result["action"]


# ── Управляющая панель ИДТ ────────────────────────────────────────────────────

ctrl_idt = tk.Frame(tab_idt)
ctrl_idt.pack(pady=6)

tk.Label(ctrl_idt, text="IP:").pack(side="left")
host_idt = tk.Entry(ctrl_idt, width=18); host_idt.insert(0, "192.168.0.176")
host_idt.pack(side="left", padx=4)

tk.Label(ctrl_idt, text="COM Agilent:").pack(side="left")
com_idt = tk.Entry(ctrl_idt, width=7); com_idt.insert(0, "COM3")
com_idt.pack(side="left", padx=4)

tk.Label(ctrl_idt, text="Номер БИАБ:").pack(side="left")
biab_idt = tk.Entry(ctrl_idt, width=5); biab_idt.insert(0, "01")
biab_idt.pack(side="left", padx=4)

tk.Label(ctrl_idt, text="Нач. ИДТ (1–12):").pack(side="left")
idt_start_entry = tk.Entry(ctrl_idt, width=4); idt_start_entry.insert(0, "1")
idt_start_entry.pack(side="left", padx=4)

tk.Label(ctrl_idt, text="Шаг уставки:").pack(side="left")
idt_step_entry = tk.Entry(ctrl_idt, width=5); idt_step_entry.insert(0, "5")
idt_step_entry.pack(side="left", padx=4)

status_idt = tk.Label(tab_idt, text="Готов", bg="#eee", anchor="w", relief="flat")
status_idt.pack(fill="x", padx=4)

def update_status_idt(text: str):
    color = "red" if "Ошибка" in text or "Остановлено" in text else "black"
    status_idt.config(text=text, fg=color)
    status_idt.update_idletasks()


def add_row_idt(values):
    if isinstance(values, str):
        update_status_idt(values)
        return
    iid = tree_idt.insert("", "end", values=values)
    tree_idt.see(iid)


def start_idt():
    idt_logic.stop_thread.clear()
    idt_logic.stop_idt_cycle.clear()
    idt_logic.wait_for_input_event.clear()
    idt_logic.next_idt_event.clear()
    idt_logic.ustavka_response.clear()
    idt_logic.active_IDT = None

    btn_start_idt.config(state="disabled")
    btn_stop_idt.config(state="normal")

    try:
        s_iae = max(0, min(11, int(idt_start_entry.get()) - 1))
    except ValueError:
        s_iae = 0
    try:
        step = float(idt_step_entry.get())
    except ValueError:
        step = 5

    idt_logic.start_idt           = s_iae
    idt_logic.ustavka_change_idt  = step

    update_status_idt(f"Запуск ИДТ: нач. канал {s_iae + 1}, шаг {step}…")

    t = threading.Thread(
        target=idt_logic.client_thread,
        args=(host_idt.get(), PORT, commands,
              add_row_idt, show_probe_dialog_idt,
              com_idt.get().strip() or "COM3"),
        daemon=True,
    )
    t.start()


def stop_idt():
    idt_logic.stop_idt_cycle.set()
    idt_logic.stop_thread.set()
    btn_start_idt.config(state="disabled")
    btn_stop_idt.config(state="disabled")
    update_status_idt("Остановлено")
    root.after(3000, lambda: btn_start_idt.config(state="normal"))


# Кнопки ИДТ
btn_start_idt = tk.Button(ctrl_idt, text="Старт", width=8, command=start_idt)
btn_start_idt.pack(side="left", padx=4)

btn_stop_idt = tk.Button(ctrl_idt, text="Стоп", width=8, command=stop_idt)
btn_stop_idt.pack(side="left", padx=4)

tk.Button(ctrl_idt, text="Очистить", width=8,
          command=lambda: tree_idt.delete(*tree_idt.get_children())
          ).pack(side="left", padx=4)

# Таблица ИДТ
cols_idt = ("ИДТ", "Уставка (Ом)", "Знач. БИАБ (Ом)",
            "Знач. прибора (Ом)", "Погрешность (Ом)", "Статус", "Дата")
tree_idt = ttk.Treeview(tab_idt, columns=cols_idt, show="headings")
for c in cols_idt:
    tree_idt.heading(c, text=c)
    tree_idt.column(c, width=138, anchor="center")
tree_idt.pack(expand=True, fill="both", pady=4, padx=4)

sb_idt = ttk.Scrollbar(tab_idt, orient="vertical", command=tree_idt.yview)
tree_idt.configure(yscrollcommand=sb_idt.set)
sb_idt.pack(side="right", fill="y")

# Раскраска строк «Не норма»
tree_idt.tag_configure("bad", foreground="red")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 – ИАЭ  (новая вкладка)
# ══════════════════════════════════════════════════════════════════════════════

tab_iae = ttk.Frame(notebook)
notebook.add(tab_iae, text="  ИАЭ (напряжение)  ")


# ── Диалог перестановки щупов ИАЭ ────────────────────────────────────────────

def show_probe_dialog_iae():
    dialog = tk.Toplevel(root)
    dialog.title("ИАЭ – Перестановка щупов")
    dialog.geometry("380x160")
    dialog.grab_set()
    x = root.winfo_x() + (root.winfo_width()  // 2) - 190
    y = root.winfo_y() + (root.winfo_height() // 2) - 80
    dialog.geometry(f"380x160+{x}+{y}")

    ch = (iae_logic.active_IAE or 0) + 2   # следующий канал (1-based)
    tk.Label(dialog,
             text=f"Переставьте щупы на канал ИАЭ {ch}",
             font=("", 11)).pack(pady=14)

    result = {"action": None}

    def on_stop():
        result["action"] = "stop"
        iae_logic.stop_iae_cycle.set()
        iae_logic.stop_thread.set()
        update_status_iae("Остановлено")
        root.after(3000, lambda: btn_start_iae.config(state="normal"))
        dialog.destroy()

    def on_repeat():
        result["action"] = "repeat"
        dialog.destroy()

    def on_continue():
        result["action"] = "continue"
        dialog.destroy()

    f = tk.Frame(dialog); f.pack(pady=8)
    tk.Button(f, text="Повторить",  width=11, command=on_repeat).pack(side="left", padx=5)
    tk.Button(f, text="Продолжить", width=11, command=on_continue).pack(side="left", padx=5)
    tk.Button(f, text="Стоп",       width=11, command=on_stop).pack(side="left", padx=5)

    dialog.wait_window()
    return result["action"]


# ── Управляющая панель ИАЭ ────────────────────────────────────────────────────

ctrl_iae = tk.Frame(tab_iae)
ctrl_iae.pack(pady=6)

tk.Label(ctrl_iae, text="IP:").pack(side="left")
host_iae = tk.Entry(ctrl_iae, width=18); host_iae.insert(0, "192.168.0.176")
host_iae.pack(side="left", padx=4)

tk.Label(ctrl_iae, text="COM Agilent:").pack(side="left")
com_iae = tk.Entry(ctrl_iae, width=7); com_iae.insert(0, "COM3")
com_iae.pack(side="left", padx=4)

tk.Label(ctrl_iae, text="Номер БИАБ:").pack(side="left")
biab_iae = tk.Entry(ctrl_iae, width=5); biab_iae.insert(0, "01")
biab_iae.pack(side="left", padx=4)

tk.Label(ctrl_iae, text="Нач. ИАЭ (1–24):").pack(side="left")
iae_start_entry = tk.Entry(ctrl_iae, width=4); iae_start_entry.insert(0, "1")
iae_start_entry.pack(side="left", padx=4)

tk.Label(ctrl_iae, text="Шаг (мВ):").pack(side="left")
iae_step_entry = tk.Entry(ctrl_iae, width=5); iae_step_entry.insert(0, "5")
iae_step_entry.pack(side="left", padx=4)

# ── Информационная строка о допуске ──────────────────────────────────────────
info_iae = tk.Label(tab_iae,
    text="Диапазон уставок ИАЭ: 2.000–5.000 В  |  Допуск: ±10 мВ",
    bg="#ddeeff", anchor="w", relief="flat", padx=6)
info_iae.pack(fill="x", padx=4)

status_iae = tk.Label(tab_iae, text="Готов", bg="#eee", anchor="w", relief="flat")
status_iae.pack(fill="x", padx=4)


def update_status_iae(text: str):
    color = "red" if "Ошибка" in text or "Остановлено" in text else "black"
    status_iae.config(text=text, fg=color)
    status_iae.update_idletasks()


def add_row_iae(values):
    if isinstance(values, str):
        update_status_iae(values)
        return
    iid = tree_iae.insert("", "end", values=values,
                           tags=("bad",) if values[5] == "Не норма" else ())
    tree_iae.see(iid)


def start_iae_measurement():
    iae_logic.stop_thread.clear()
    iae_logic.stop_iae_cycle.clear()
    iae_logic.ustavka_response.clear()
    iae_logic.active_IAE = None

    btn_start_iae.config(state="disabled")
    btn_stop_iae.config(state="normal")

    try:
        s = max(0, min(23, int(iae_start_entry.get()) - 1))
    except ValueError:
        s = 0
    try:
        step = int(iae_step_entry.get())
        if step < 1:
            step = 5
    except ValueError:
        step = 5

    iae_logic.start_iae          = s
    iae_logic.ustavka_change_iae = step

    update_status_iae(
        f"Запуск ИАЭ: нач. канал {s + 1}, шаг {step} мВ "
        f"({step / 1000:.3f} В)…"
    )

    t = threading.Thread(
        target=iae_logic.client_thread,
        args=(host_iae.get(), PORT, commands,
              add_row_iae, show_probe_dialog_iae,
              com_iae.get().strip() or "COM3"),
        daemon=True,
    )
    t.start()


def stop_iae_measurement():
    iae_logic.stop_iae_cycle.set()
    iae_logic.stop_thread.set()
    btn_start_iae.config(state="disabled")
    btn_stop_iae.config(state="disabled")
    update_status_iae("Остановлено")
    root.after(3000, lambda: btn_start_iae.config(state="normal"))


# Кнопки ИАЭ
btn_start_iae = tk.Button(ctrl_iae, text="Старт", width=8,
                           command=start_iae_measurement)
btn_start_iae.pack(side="left", padx=4)

btn_stop_iae = tk.Button(ctrl_iae, text="Стоп", width=8,
                          command=stop_iae_measurement)
btn_stop_iae.pack(side="left", padx=4)

tk.Button(ctrl_iae, text="Очистить", width=8,
          command=lambda: tree_iae.delete(*tree_iae.get_children())
          ).pack(side="left", padx=4)

# Таблица ИАЭ
cols_iae = ("ИАЭ", "Уставка (В)", "Знач. БИАБ (В)",
            "Знач. прибора (В)", "Погрешность (В)", "Статус", "Дата")
tree_iae = ttk.Treeview(tab_iae, columns=cols_iae, show="headings")
for c in cols_iae:
    tree_iae.heading(c, text=c)
    tree_iae.column(c, width=138, anchor="center")
tree_iae.pack(expand=True, fill="both", pady=4, padx=4)
tree_iae.tag_configure("bad", foreground="red")

sb_iae = ttk.Scrollbar(tab_iae, orient="vertical", command=tree_iae.yview)
tree_iae.configure(yscrollcommand=sb_iae.set)
sb_iae.pack(side="right", fill="y")


# ══════════════════════════════════════════════════════════════════════════════
# Запуск
# ══════════════════════════════════════════════════════════════════════════════

root.mainloop()