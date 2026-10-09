"""
gui_biab200.py — двухвкладочный интерфейс БИАБ-200ЛИ.

Вкладка 1 «ИДТ (Ом)»  — biab200.py,     прибор → MODE_FRES
Вкладка 2 «ИАЭ (В)»   — biab200_iae.py, прибор → MODE_DCV

При переключении вкладок (когда измерение не запущено) прибор
автоматически перенастраивается на нужные единицы.
"""

import tkinter as tk
from tkinter import ttk
import threading
import json, sys, os

import meter
import biab200 as idt_logic
import iae as iae_logic

PORT = 10001

# ── Ресурсы ───────────────────────────────────────────────────────────────────

def resource_path(rel):
    base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base, rel)

with open(resource_path("command_biab200.json"), encoding="utf-8") as _f:
    commands = json.load(_f)

# ── Флаги активных измерений ──────────────────────────────────────────────────
_idt_running = False
_iae_running = False


def any_running():
    return _idt_running or _iae_running


# ══════════════════════════════════════════════════════════════════════════════
# Корневое окно
# ══════════════════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("БИАБ-200ЛИ — Измерения")
root.geometry("1100x700")

# ── Общая панель (над вкладками) ──────────────────────────────────────────────
top = tk.Frame(root, bd=1, relief="groove")
top.pack(fill="x", padx=6, pady=(6, 0))

tk.Label(top, text="IP:").pack(side="left")
ip_entry = tk.Entry(top, width=15)
ip_entry.insert(0, "192.168.0.176")
ip_entry.pack(side="left", padx=4)

tk.Label(top, text="COM прибора:").pack(side="left")
com_entry = tk.Entry(top, width=7)
com_entry.insert(0, "COM3")
com_entry.pack(side="left", padx=4)

tk.Label(top, text="Тип прибора:").pack(side="left")
meter_var = tk.StringVar(value=meter.TYPE_AGILENT)
meter_combo = ttk.Combobox(top, textvariable=meter_var,
                           values=[meter.TYPE_AGILENT, meter.TYPE_GDM79061],
                           width=11, state="readonly")
meter_combo.pack(side="left", padx=4)

tk.Label(top, text="Номер БИАБ:").pack(side="left")
biab_entry = tk.Entry(top, width=5)
biab_entry.insert(0, "01")
biab_entry.pack(side="left", padx=4)

# ── Notebook ──────────────────────────────────────────────────────────────────
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both", padx=6, pady=6)


# ══════════════════════════════════════════════════════════════════════════════
# Общий диалог «Переставьте щупы»
# ══════════════════════════════════════════════════════════════════════════════

def _probe_dialog(title_text, on_stop_cb):
    dialog = tk.Toplevel(root)
    dialog.title("Перестановка щупов")
    dialog.geometry("370x145")
    dialog.grab_set()
    x = root.winfo_x() + root.winfo_width()  // 2 - 185
    y = root.winfo_y() + root.winfo_height() // 2 - 72
    dialog.geometry(f"370x145+{x}+{y}")

    tk.Label(dialog, text=title_text, font=("", 11)).pack(pady=12)
    result = {"action": None}

    def _act(val):
        result["action"] = val
        if val == "stop":
            on_stop_cb()
        dialog.destroy()

    f = tk.Frame(dialog); f.pack()
    tk.Button(f, text="Повторить",  width=11, command=lambda: _act("repeat")).pack(side="left", padx=5)
    tk.Button(f, text="Продолжить", width=11, command=lambda: _act("continue")).pack(side="left", padx=5)
    tk.Button(f, text="Стоп",       width=11, command=lambda: _act("stop")).pack(side="left", padx=5)

    dialog.wait_window()
    return result["action"]


# ══════════════════════════════════════════════════════════════════════════════
# Вкладка 1 — ИДТ
# ══════════════════════════════════════════════════════════════════════════════

tab_idt = ttk.Frame(notebook)
notebook.add(tab_idt, text="  ИДТ (Ом)  ")

# ── Панель управления ИДТ ─────────────────────────────────────────────────────
ctrl_idt = tk.Frame(tab_idt)
ctrl_idt.pack(pady=4)

tk.Label(ctrl_idt, text="Нач. ИДТ (1–12):").pack(side="left")
idt_start = tk.Entry(ctrl_idt, width=4); idt_start.insert(0, "1")
idt_start.pack(side="left", padx=3)

tk.Label(ctrl_idt, text="Шаг уставки:").pack(side="left")
idt_step = tk.Entry(ctrl_idt, width=5); idt_step.insert(0, "5")
idt_step.pack(side="left", padx=3)

status_idt = tk.Label(tab_idt, text="Готов", bg="#eee", anchor="w")
status_idt.pack(fill="x", padx=4)


def update_status_idt(text):
    color = "red" if any(w in text for w in ("Ошибка", "Остановлено")) else "black"
    status_idt.config(text=text, fg=color)
    status_idt.update_idletasks()


def add_row_idt(values):
    if isinstance(values, str):
        update_status_idt(values); return
    iid = tree_idt.insert("", "end", values=values,
                          tags=("bad",) if values[5] == "Не норма" else ())
    tree_idt.see(iid)


def show_probe_idt():
    def on_stop():
        idt_logic.stop_idt_cycle.set()
        idt_logic.stop_thread.set()
        update_status_idt("Остановлено")
        root.after(3000, lambda: btn_start_idt.config(state="normal"))
    return _probe_dialog("Переставьте щупы на следующий ИДТ", on_stop)


def start_idt():
    global _idt_running
    idt_logic.stop_thread.clear()
    idt_logic.stop_idt_cycle.clear()
    idt_logic.ustavka_response.clear()
    idt_logic.active_IDT = None

    try:
        s = max(0, min(11, int(idt_start.get()) - 1))
    except ValueError:
        s = 0
    try:
        step = float(idt_step.get())
    except ValueError:
        step = 5

    # передаём параметры в логику
    idt_logic.biab_number        = biab_entry.get().strip() or "01"
    idt_logic.start_idt          = s
    idt_logic.ustavka_change_idt = step

    btn_start_idt.config(state="disabled")
    btn_stop_idt.config(state="normal")
    btn_start_iae.config(state="disabled")   # блокируем другую вкладку
    _idt_running = True

    update_status_idt(f"Запуск ИДТ: нач. канал {s + 1}, шаг {step}…")

    def _run():
        global _idt_running
        idt_logic.client_thread(
            ip_entry.get(), PORT, commands,
            add_row_idt, show_probe_idt,
            com_entry.get().strip() or "COM3",
            meter_var.get(),
        )
        _idt_running = False
        root.after(0, _idt_done)

    def _idt_done():
        btn_start_idt.config(state="normal")
        btn_stop_idt.config(state="disabled")
        btn_start_iae.config(state="normal")
        update_status_idt("Завершено")

    threading.Thread(target=_run, daemon=True).start()


def stop_idt():
    global _idt_running
    idt_logic.stop_idt_cycle.set()
    idt_logic.stop_thread.set()
    btn_start_idt.config(state="disabled")
    btn_stop_idt.config(state="disabled")
    update_status_idt("Остановлено")
    root.after(3000, lambda: btn_start_idt.config(state="normal"))


btn_start_idt = tk.Button(ctrl_idt, text="Старт", width=8, command=start_idt)
btn_start_idt.pack(side="left", padx=4)
btn_stop_idt  = tk.Button(ctrl_idt, text="Стоп",  width=8, command=stop_idt,
                           state="disabled")
btn_stop_idt.pack(side="left", padx=4)
tk.Button(ctrl_idt, text="Очистить", width=8,
          command=lambda: tree_idt.delete(*tree_idt.get_children())
          ).pack(side="left", padx=4)

# ── Таблица ИДТ ───────────────────────────────────────────────────────────────
cols_idt = ("ИДТ", "Уставка (Ом)", "Знач. БИАБ (Ом)",
            "Знач. прибора (Ом)", "Погрешность (Ом)", "Статус", "Дата")
tree_idt = ttk.Treeview(tab_idt, columns=cols_idt, show="headings")
for c in cols_idt:
    tree_idt.heading(c, text=c)
    tree_idt.column(c, width=145, anchor="center")
tree_idt.tag_configure("bad", foreground="red")
tree_idt.pack(expand=True, fill="both", padx=4, pady=4)
sb_idt = ttk.Scrollbar(tab_idt, orient="vertical", command=tree_idt.yview)
tree_idt.configure(yscrollcommand=sb_idt.set)
sb_idt.pack(side="right", fill="y")


# ══════════════════════════════════════════════════════════════════════════════
# Вкладка 2 — ИАЭ
# ══════════════════════════════════════════════════════════════════════════════

tab_iae = ttk.Frame(notebook)
notebook.add(tab_iae, text="  ИАЭ (В)  ")

# ── Информационная строка ──────────────────────────────────────────────────────
tk.Label(tab_iae,
         text="Диапазон уставок: 2.000–5.000 В  |  Допуск: ±10 мВ",
         bg="#ddeeff", anchor="w", padx=6).pack(fill="x")

# ── Панель управления ИАЭ ─────────────────────────────────────────────────────
ctrl_iae = tk.Frame(tab_iae)
ctrl_iae.pack(pady=4)

tk.Label(ctrl_iae, text="Нач. ИАЭ (1–24):").pack(side="left")
iae_start = tk.Entry(ctrl_iae, width=4); iae_start.insert(0, "1")
iae_start.pack(side="left", padx=3)

tk.Label(ctrl_iae, text="Шаг (мВ):").pack(side="left")
iae_step = tk.Entry(ctrl_iae, width=5); iae_step.insert(0, "5")
iae_step.pack(side="left", padx=3)

status_iae = tk.Label(tab_iae, text="Готов", bg="#eee", anchor="w")
status_iae.pack(fill="x", padx=4)


def update_status_iae(text):
    color = "red" if any(w in text for w in ("Ошибка", "Остановлено")) else "black"
    status_iae.config(text=text, fg=color)
    status_iae.update_idletasks()


def add_row_iae(values):
    if isinstance(values, str):
        update_status_iae(values); return
    iid = tree_iae.insert("", "end", values=values,
                          tags=("bad",) if values[5] == "Не норма" else ())
    tree_iae.see(iid)


def show_probe_iae():
    ch = (iae_logic.active_IAE or 0) + 2
    def on_stop():
        iae_logic.stop_iae_cycle.set()
        iae_logic.stop_thread.set()
        update_status_iae("Остановлено")
        root.after(3000, lambda: btn_start_iae.config(state="normal"))
    return _probe_dialog(f"Переставьте щупы на канал ИАЭ {ch}", on_stop)


def start_iae():
    global _iae_running
    iae_logic.stop_thread.clear()
    iae_logic.stop_iae_cycle.clear()
    iae_logic.ustavka_response.clear()
    iae_logic.active_IAE = None

    try:
        s = max(0, min(23, int(iae_start.get()) - 1))
    except ValueError:
        s = 0
    try:
        step = int(iae_step.get())
        if step < 1:
            step = 5
    except ValueError:
        step = 5

    iae_logic.biab_number        = biab_entry.get().strip() or "01"
    iae_logic.start_iae          = s
    iae_logic.ustavka_change_iae = step

    btn_start_iae.config(state="disabled")
    btn_stop_iae.config(state="normal")
    btn_start_idt.config(state="disabled")   # блокируем другую вкладку
    _iae_running = True

    update_status_iae(
        f"Запуск ИАЭ: нач. канал {s + 1}, шаг {step} мВ ({step/1000:.3f} В)…"
    )

    def _run():
        global _iae_running
        iae_logic.client_thread(
            ip_entry.get(), PORT, commands,
            add_row_iae, show_probe_iae,
            com_entry.get().strip() or "COM3",
            meter_var.get(),
        )
        _iae_running = False
        root.after(0, _iae_done)

    def _iae_done():
        btn_start_iae.config(state="normal")
        btn_stop_iae.config(state="disabled")
        btn_start_idt.config(state="normal")
        update_status_iae("Завершено")

    threading.Thread(target=_run, daemon=True).start()


def stop_iae():
    global _iae_running
    iae_logic.stop_iae_cycle.set()
    iae_logic.stop_thread.set()
    btn_start_iae.config(state="disabled")
    btn_stop_iae.config(state="disabled")
    update_status_iae("Остановлено")
    root.after(3000, lambda: btn_start_iae.config(state="normal"))


btn_start_iae = tk.Button(ctrl_iae, text="Старт", width=8, command=start_iae)
btn_start_iae.pack(side="left", padx=4)
btn_stop_iae  = tk.Button(ctrl_iae, text="Стоп",  width=8, command=stop_iae,
                           state="disabled")
btn_stop_iae.pack(side="left", padx=4)
tk.Button(ctrl_iae, text="Очистить", width=8,
          command=lambda: tree_iae.delete(*tree_iae.get_children())
          ).pack(side="left", padx=4)

# ── Таблица ИАЭ ───────────────────────────────────────────────────────────────
cols_iae = ("ИАЭ", "Уставка (В)", "Знач. БИАБ (В)",
            "Знач. прибора (В)", "Погрешность (В)", "Статус", "Дата")
tree_iae = ttk.Treeview(tab_iae, columns=cols_iae, show="headings")
for c in cols_iae:
    tree_iae.heading(c, text=c)
    tree_iae.column(c, width=145, anchor="center")
tree_iae.tag_configure("bad", foreground="red")
tree_iae.pack(expand=True, fill="both", padx=4, pady=4)
sb_iae = ttk.Scrollbar(tab_iae, orient="vertical", command=tree_iae.yview)
tree_iae.configure(yscrollcommand=sb_iae.set)
sb_iae.pack(side="right", fill="y")


# ══════════════════════════════════════════════════════════════════════════════
# Переключение вкладок → перенастройка прибора
# ══════════════════════════════════════════════════════════════════════════════

def on_tab_changed(event):
    """
    При переходе на вкладку перенастраиваем прибор на нужные единицы,
    если он уже подключён и никакое измерение не запущено.
    Команды прибору отправляем в фоновом потоке, чтобы не блокировать GUI.
    """
    if any_running():
        return                          # не трогаем прибор во время измерения
    if not meter.is_open():
        return                          # прибор не подключён — ничего делать

    tab = notebook.select()
    if tab == str(tab_idt):
        threading.Thread(
            target=meter.configure, args=(meter.MODE_FRES,), daemon=True
        ).start()
        update_status_idt("Прибор → режим сопротивления (Ом)")
    elif tab == str(tab_iae):
        threading.Thread(
            target=meter.configure, args=(meter.MODE_DCV,), daemon=True
        ).start()
        update_status_iae("Прибор → режим напряжения (В)")


notebook.bind("<<NotebookTabChanged>>", on_tab_changed)


# ══════════════════════════════════════════════════════════════════════════════
# Запуск
# ══════════════════════════════════════════════════════════════════════════════

root.mainloop()
