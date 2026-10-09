import socket
import csv
import queue
import json
from os import path
from time import sleep
from struct import pack, unpack_from
import threading
import packet as pk
from datetime import datetime

import meter   # общий модуль прибора

# ── Глобальные флаги ──────────────────────────────────────────────────────────
stop_thread    = threading.Event()
stop_idt_cycle = threading.Event()

active_IDT         = None
sock_ref           = None
param_value_queue  = queue.Queue()
ustavka_response   = {}
ustavka_lock       = threading.Lock()
wait_for_input_event = threading.Event()
next_idt_event     = threading.Event()

biab_number        = "01"   # задаётся из GUI перед запуском
start_idt          = 0
ustavka_change_idt = 5


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
        print(f"Ошибка при вызове callback: {e}")


# ── CSV ───────────────────────────────────────────────────────────────────────

def _csv_name():
    return f"{get_current_date_str()}БИАБ-200ЛИ_{biab_number}.csv"


def write_to_csv(current_IDT, current_ustavka_IDT, param_value,
                 meas_value, callback=None):
    fault  = abs((current_ustavka_IDT / 10) - meas_value) if meas_value is not None else 0
    status = '' if fault <= 0.1 else 'Не норма'

    with open(_csv_name(), mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            current_IDT + 1,
            current_ustavka_IDT / 10,
            param_value / 10 if param_value is not None else None,
            round(meas_value, 3) if meas_value is not None else None,
            round(fault, 3),
            status,
            datetime.now().strftime("%Y-%m-%d"),
        ])

    if callback:
        safe_callback(callback, (
            current_IDT + 1,
            current_ustavka_IDT / 10,
            param_value / 10 if param_value is not None else None,
            round(meas_value, 3) if meas_value is not None else None,
            round(fault, 3),
            status,
            datetime.now().strftime("%Y-%m-%d"),
        ))


def clean_csv_for_idt(start_idt):
    fn = _csv_name()
    if not path.exists(fn):
        return
    rows = []
    with open(fn, newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                if int(row[0]) != start_idt + 1:
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
                    print("Ошибка при расшифровке сообщения:", e)
        except Exception as e:
            print("Ошибка при получении данных:", e)
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
                type_atm, pnum, plen = unpack_from('<HHB', msg, offset)
                offset += 5
                if plen > 0 and offset + plen <= len(msg):
                    if type_atm == 20 and plen == 2:   # уставка ИДТ (БИАБ-200)
                        raw_value, = unpack_from('<H', msg, offset)
                        print(f"[АТМ-ИДТ] type={type_atm}, pnum={pnum}, value={raw_value}")
                        with ustavka_lock:
                            if raw_value in ustavka_response:
                                ev, _ = ustavka_response[raw_value]
                                ustavka_response[raw_value] = (ev, raw_value)
                                ev.set()
                offset += plen
        else:
            print(f"[INFO] Пакет ID={packet_id}, длина={len(msg)}")


# ── Рабочий поток отправки команд ────────────────────────────────────────────

def send_commands_thread(sock, commands, start_idt, callback, callback_dialog):
    clean_csv_for_idt(start_idt)
    try:
        for name in ["complex_mode", "vkl_atm_biab", "vkl_biab"]:
            cd = commands['short_comm'][name]
            sock.send(pk.Short_Comanda_KU(cd['type_ku'], cd['cod_ku']).message())

        current_IDT = start_idt

        while current_IDT < 12:
            if stop_idt_cycle.is_set():
                break

            globals()['active_IDT'] = current_IDT

            for ust in range(990, 1200 + ustavka_change_idt, ustavka_change_idt):
                if stop_idt_cycle.is_set():
                    break

                with ustavka_lock:
                    ev = threading.Event()
                    ustavka_response[ust] = (ev, None)

                pkt = pk.Short_Comanda_KU(4, current_IDT, 1).set_ustavka(ust, 4)
                sock.send(pkt)

                if ev.wait(timeout=10):
                    _, param = ustavka_response.pop(ust)
                else:
                    param = None
                    print(f"Таймаут для уставки {ust}")

                meas = meter.measure()
                write_to_csv(current_IDT, ust, param, meas, callback)

            if stop_idt_cycle.is_set():
                break

            if callback:
                safe_callback(callback, "Переставьте щупы для следующего ИДТ")

            action = callback_dialog()

            if action == "stop":
                stop_idt_cycle.set()
                break
            elif action == "repeat":
                clean_csv_for_idt(current_IDT)
                continue
            else:
                current_IDT += 1
                continue

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
        meter.configure(meter.MODE_FRES)

        with socket.create_connection((host, port)) as sock:
            sock_ref = sock

            t_send = threading.Thread(
                target=send_commands_thread,
                args=(sock, commands, start_idt, callback, show_probe_dialog),
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
