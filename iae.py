"""
biab200_iae.py — логика тестирования ИАЭ для БИАБ-200ЛИ.

Структура намеренно зеркалирует biab200.py (ИДТ), чтобы оба модуля
выглядели единообразно.

Отличия от ИДТ:
  • 24 канала (0–23) вместо 12
  • Уставки 2000–5000 мВ (2.000–5.000 В), тип WORD
  • Команда уставки: TipKU=5, KodKU=канал, set_ustavka(ust, 3)
  • АТМ тип 2  (тип 20 у ИДТ), значение signed short (<h), единицы мВ
  • Дополнительные стартовые/финишные команды для контакторов ИАЭ
  • Прибор: MODE_DCV (DC-напряжение) вместо MODE_FRES
"""

import socket
import csv
import queue
import json
from os import path
from time import sleep
from struct import unpack_from
import threading
import packet as pk
from datetime import datetime

import meter   # общий модуль прибора

# ── Глобальные флаги ──────────────────────────────────────────────────────────
stop_thread    = threading.Event()
stop_iae_cycle = threading.Event()

active_IAE         = None
sock_ref           = None
ustavka_response   = {}
ustavka_lock       = threading.Lock()

biab_number        = "01"   # задаётся из GUI перед запуском
start_iae          = 0      # стартовый канал (0-based)
ustavka_change_iae = 5      # шаг уставки, мВ


# ── Вспомогательные функции ───────────────────────────────────────────────────

def get_current_date_str():
    return datetime.now().strftime("%Y-%m-%d_")


def safe_callback(callback, values):
    try:
        import tkinter as tk
        root = None
        if hasattr(tk, '_default_root') and tk._default_root:
            root = tk._default_root
        if root:
            root.after(0, lambda: callback(values))
        else:
            print("Не удалось найти корневое окно Tk для callback")
    except Exception as e:
        print(f"[ИАЭ] Ошибка callback: {e}")


# ── CSV ───────────────────────────────────────────────────────────────────────

def _csv_name():
    return f"{get_current_date_str()}БИАБ-200ЛИ_ИАЭ_{biab_number}.csv"


def write_to_csv(current_IAE, ustavka_mv, param_mv, meas_v, callback=None):
    """
    current_IAE  : int        — канал 0-based
    ustavka_mv   : int        — заданная уставка, мВ (2000–5000)
    param_mv     : int|None   — подтверждение из АТМ, мВ
    meas_v       : float|None — измеренное прибором напряжение, В
    """
    ust_v    = ustavka_mv / 1000
    param_v  = param_mv  / 1000 if param_mv  is not None else None
    meas_v   = meas_v           if meas_v    is not None else 0.0
    fault    = abs(ust_v - meas_v)
    status   = '' if fault <= 0.010 else 'Не норма'    # допуск ±10 мВ

    with open(_csv_name(), mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            current_IAE + 1,
            round(ust_v,   4),
            round(param_v, 4) if param_v is not None else None,
            round(meas_v,  4),
            round(fault,   4),
            status,
            datetime.now().strftime("%Y-%m-%d"),
        ])

    if callback:
        safe_callback(callback, (
            current_IAE + 1,
            round(ust_v,   4),
            round(param_v, 4) if param_v is not None else None,
            round(meas_v,  4),
            round(fault,   4),
            status,
            datetime.now().strftime("%Y-%m-%d"),
        ))


def clean_csv_for_iae(iae_idx):
    fn = _csv_name()
    if not path.exists(fn):
        return
    rows = []
    with open(fn, newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                if int(row[0]) != iae_idx + 1:
                    rows.append(row)
            except (IndexError, ValueError):
                rows.append(row)
    with open(fn, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)


# ── Сетевые функции ───────────────────────────────────────────────────────────

def sock_forced_close():
    global sock_ref
    s, sock_ref = sock_ref, None
    if s:
        try:
            s.shutdown(2)
            s.close()
        except Exception:
            pass


# ── Декодирование пакетов ─────────────────────────────────────────────────────

def receive_messages(sock):
    buffer = b''
    while not stop_thread.is_set():
        try:
            chunk = sock.recv(16384)
            if stop_thread.is_set():
                return
            if not chunk:
                break
            buffer += chunk
            while len(buffer) >= 2:
                msg_len = unpack_from('<H', buffer)[0]
                if len(buffer) < 2 + msg_len:
                    break
                msg    = buffer[:2 + msg_len]
                buffer = buffer[2 + msg_len:]
                try:
                    decode_packet(msg)
                except Exception as e:
                    print("[ИАЭ] Ошибка расшифровки:", e)
        except Exception as e:
            print("[ИАЭ] Ошибка приёма:", e)
            break


def decode_packet(data):
    buffer = data
    while len(buffer) >= 2:
        length, = unpack_from('<H', buffer)
        if len(buffer) < 2 + length:
            break
        msg    = buffer[:2 + length]
        buffer = buffer[2 + length:]

        packet_id, = unpack_from('<H', msg, 10)

        if packet_id == 4:
            kol, = unpack_from('<H', msg, 12)
            offset = 14
            for _ in range(kol):
                if offset + 5 > len(msg):
                    break
                type_atm, pnum, plen = unpack_from('<HHB', msg, offset)
                offset += 5
                if plen > 0 and offset + plen <= len(msg):
                    if type_atm == 2 and plen == 2:   # уставка ИАЭ (signed, мВ)
                        raw_val, = unpack_from('<h', msg, offset)
                        print(f"[АТМ-ИАЭ] type={type_atm}, канал={pnum}, {raw_val} мВ")
                        with ustavka_lock:
                            if raw_val in ustavka_response:
                                ev, _ = ustavka_response[raw_val]
                                ustavka_response[raw_val] = (ev, raw_val)
                                ev.set()
                offset += plen
        else:
            print(f"[INFO-ИАЭ] Пакет ID={packet_id}, длина={len(msg)}")


# ── Рабочий поток отправки команд ────────────────────────────────────────────

def send_commands_thread(sock, commands, start_iae_idx, callback, callback_dialog):
    clean_csv_for_iae(start_iae_idx)
    try:
        # Стартовые команды — общие с ИДТ
        for name in ["complex_mode", "vkl_atm_biab", "vkl_biab"]:
            cd = commands['short_comm'][name]
            sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

        # Подключить контакторы ИАЭ (TipKU=7, KodKU=5)
        sock.send(pk.Short_Comanda_KU(7, 5).message())
        sleep(0.5)

        current_IAE = start_iae_idx

        while current_IAE < 24:
            if stop_iae_cycle.is_set():
                break

            globals()['active_IAE'] = current_IAE

            for ust in range(2000, 5000 + ustavka_change_iae, ustavka_change_iae):
                if stop_iae_cycle.is_set():
                    break

                with ustavka_lock:
                    ev = threading.Event()
                    ustavka_response[ust] = (ev, None)

                # TipKU=5, KodKU=канал, параметр WORD
                pkt = pk.Short_Comanda_KU(5, current_IAE, 1).set_ustavka(ust, 3)
                sock.send(pkt)

                if ev.wait(timeout=10):
                    _, param = ustavka_response.pop(ust)
                else:
                    param = None
                    print(f"[ИАЭ] Таймаут для уставки {ust} мВ, канал {current_IAE}")

                meas = meter.measure()
                write_to_csv(current_IAE, ust, param, meas, callback)

            if stop_iae_cycle.is_set():
                break

            if callback:
                safe_callback(callback,
                               f"Переставьте щупы на канал ИАЭ {current_IAE + 2}")

            action = callback_dialog()

            if action == "stop":
                stop_iae_cycle.set()
                break
            elif action == "repeat":
                clean_csv_for_iae(current_IAE)
                continue
            else:
                current_IAE += 1
                continue

        # Финишные команды
        sock.send(pk.Short_Comanda_KU(7, 6).message())  # Откл. контакторы ИАЭ
        for name in ["otkl_biab", "otkl_atm_biab_kpa", "autonomous_mode"]:
            cd = commands['short_comm'][name]
            sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

    except Exception as e:
        if callback:
            safe_callback(callback, f"Ошибка: {e}")


# ── Точка входа ───────────────────────────────────────────────────────────────

def client_thread(host, port, commands, callback=None,
                  show_probe_dialog=None, com_port="COM3",
                  meter_type=meter.TYPE_AGILENT):
    global sock_ref

    if not meter.open_port(com_port, meter_type):
        if callback:
            safe_callback(callback, "Ошибка: прибор не подключён")
        return

    try:
        meter.configure(meter.MODE_DCV)

        with socket.create_connection((host, port)) as sock:
            sock_ref = sock

            t_send = threading.Thread(
                target=send_commands_thread,
                args=(sock, commands, start_iae, callback, show_probe_dialog),
            )
            t_recv = threading.Thread(
                target=receive_messages,
                args=(sock,),
            )
            t_send.start()
            t_recv.start()
            t_send.join()
            t_recv.join()

    except ConnectionError as e:
        if callback:
            safe_callback(callback, f"Ошибка подключения: {e}")
    finally:
        stop_thread.set()
        sock_forced_close()
        meter.close_port()
