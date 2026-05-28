import socket
import serial
import csv
import queue
import json
import threading
from os import path
from time import sleep
from struct import pack, unpack_from
from datetime import datetime
import packet as pk


# ──────────────────────────────────────────────────────────────────────────────
# Глобальные флаги и синхронизация
# ──────────────────────────────────────────────────────────────────────────────
stop_thread    = threading.Event()
stop_iae_cycle = threading.Event()

active_IAE          = None   # номер текущего канала ИАЭ (0-based)
sock_ref            = None

ustavka_response    = {}     # {значение_уставки_мВ: (Event, значение | None)}
ustavka_lock        = threading.Lock()

agilent_lock        = threading.Lock()

start_iae           = 0      # стартовый канал (0-based), задаётся из GUI
ustavka_change_iae  = 5      # шаг уставки (в мВ), по умолчанию 5 мВ = 0.005 В

ser_a = None   # Serial-объект Agilent


# ──────────────────────────────────────────────────────────────────────────────
# Agilent – инициализация и измерение DC-напряжения
# ──────────────────────────────────────────────────────────────────────────────

def init_agilent_port(port_name: str):
    """Открыть COM-порт для Agilent 34401A."""
    global ser_a
    try:
        ser_a = serial.Serial(
            port=port_name, baudrate=9600,
            bytesize=8, stopbits=2, timeout=5
        )
    except serial.SerialException as e:
        print(f"[ИАЭ] Ошибка подключения Agilent к '{port_name}': {e}")
        ser_a = None


def settings_Agilent_IAE():
    """Настроить Agilent на измерение постоянного напряжения (DC Voltage)."""
    print("[ИАЭ] Настройка Agilent: DC Voltage")
    ser_a.write(b'SYST:REM\r\n')          # дистанционное управление
    sleep(0.1)
    ser_a.write(b'CONF:VOLT:DC\r\n')      # режим постоянного напряжения
    sleep(0.1)
    ser_a.write(b'VOLT:DC:NPLC 1\r\n')   # интеграция 1 PLC
    sleep(0.1)
    ser_a.write(b'VOLT:DC:RANG:AUTO ON\r\n')  # авторанг
    sleep(0.1)
    ser_a.write(b'SAMP:COUN 1\r\n')
    sleep(0.1)
    ser_a.write(b'TRIG:SOUR IMM\r\n')
    print("[ИАЭ] Agilent готов к измерению напряжения")


def Agilent_voltage() -> float | None:
    """
    Выполнить одиночное измерение DC-напряжения.
    Возвращает значение в ВОЛЬТАХ или None при ошибке.
    """
    try:
        with agilent_lock:
            ser_a.write(b'INITiate:IMMediate\n')
            sleep(0.4)
            ser_a.write(b'FETCH?\r\n')
            raw = ser_a.readline().decode("ASCII").rstrip()
            if 'E' in raw:
                mantissa, exp = raw.split('E')
                return round(float(mantissa) * (10 ** int(exp)), 6)
            return None
    except Exception as e:
        print(f"[ИАЭ] Ошибка Agilent: {e}")
        return None


def close_agilent_port():
    global ser_a
    try:
        if ser_a and ser_a.is_open:
            ser_a.close()
    except Exception as e:
        print(f"[ИАЭ] Ошибка закрытия Agilent: {e}")
    finally:
        ser_a = None


# ──────────────────────────────────────────────────────────────────────────────
# CSV
# ──────────────────────────────────────────────────────────────────────────────

def _csv_filename():
    return f"{datetime.now().strftime('%Y-%m-%d_')}БИАБ-200ЛИ_ИАЭ.csv"


def write_to_csv(iae_idx, ustavka_mv, param_mv, agilent_v, callback=None):
    """
    Запись строки результата в CSV и (опционально) обновление GUI.

    Параметры
    ----------
    iae_idx    : int   – номер канала ИАЭ (0-based)
    ustavka_mv : int   – заданная уставка в мВ (2000-5000)
    param_mv   : int | None – значение уставки из БИАБ (мВ, ATM тип 2)
    agilent_v  : float | None – напряжение с Agilent (В)
    callback   : callable | None
    """
    ustavka_v  = ustavka_mv / 1000
    param_v    = param_mv  / 1000 if param_mv  is not None else None
    agilent_v  = agilent_v if agilent_v is not None else 0.0
    fault      = abs(ustavka_v - agilent_v)
    status     = '' if fault <= 0.01 else 'Не норма'    # допуск ±10 мВ

    with open(_csv_filename(), mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            iae_idx + 1,
            round(ustavka_v, 4),
            round(param_v,   4) if param_v is not None else '',
            round(agilent_v, 4),
            round(fault,     4),
            status,
            datetime.now().strftime("%Y-%m-%d"),
        ])

    if callback:
        _safe_callback(callback, (
            iae_idx + 1,
            round(ustavka_v, 4),
            round(param_v,   4) if param_v is not None else '',
            round(agilent_v, 4),
            round(fault,     4),
            status,
            datetime.now().strftime("%Y-%m-%d"),
        ))


def clean_csv_for_iae(iae_idx: int):
    """Удалить из CSV строки с текущим каналом (для повторного измерения)."""
    fn = _csv_filename()
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


# ──────────────────────────────────────────────────────────────────────────────
# Сетевой уровень
# ──────────────────────────────────────────────────────────────────────────────

def _safe_callback(callback, values):
    try:
        import tkinter as tk
        root = None
        if hasattr(tk, '_default_root') and tk._default_root:
            root = tk._default_root
        if root:
            root.after(0, lambda: callback(values))
    except Exception as e:
        print(f"[ИАЭ] callback error: {e}")


def sock_forced_close():
    global sock_ref
    s, sock_ref = sock_ref, None
    if s:
        try:
            s.shutdown(2)
            s.close()
        except Exception:
            pass


def _send_no_param(sock, type_ku: int, cod_ku: int):
    """Отправить команду без параметров."""
    sock.send(pk.Short_Comanda_KU(type_ku, cod_ku).message())


# ──────────────────────────────────────────────────────────────────────────────
# Приём и декодирование пакетов
# ──────────────────────────────────────────────────────────────────────────────

def receive_messages(sock):
    """Поток приёма сообщений от БИАБ-200ЛИ."""
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
                    _decode_packet(msg)
                except Exception as e:
                    print(f"[ИАЭ] Ошибка декодирования: {e}")
        except Exception as e:
            print(f"[ИАЭ] Ошибка приёма: {e}")
            break


def _decode_packet(data: bytes):
    """Разобрать входящий пакет и обработать АТМ тип 2 (уставки ИАЭ)."""
    buffer = data
    while len(buffer) >= 2:
        length, = unpack_from('<H', buffer)
        if len(buffer) < 2 + length:
            break
        msg    = buffer[:2 + length]
        buffer = buffer[2 + length:]

        # timestamp, = unpack_from('<Q', msg, 2)  # не используем
        packet_id, = unpack_from('<H', msg, 10)

        if packet_id == 4:   # АТМ
            kol, = unpack_from('<H', msg, 12)
            offset = 14

            for _ in range(kol):
                if offset + 5 > len(msg):
                    break
                type_atm, pnum, plen = unpack_from('<HHB', msg, offset)
                offset += 5

                if plen > 0 and offset + plen <= len(msg):
                    # ─── АТМ тип 2: уставка напряжения ИАЭ (ЗЦ2 = WORD_SIGN) ───
                    if type_atm == 2 and plen == 2:
                        raw_val, = unpack_from('<h', msg, offset)   # signed
                        print(f"[АТМ-ИАЭ] тип={type_atm}, канал={pnum}, знач={raw_val} мВ")
                        with ustavka_lock:
                            if raw_val in ustavka_response:
                                ev, _ = ustavka_response[raw_val]
                                ustavka_response[raw_val] = (ev, raw_val)
                                ev.set()
                    # ─── АТМ тип 1: измеренное напряжение ИАЭ (информационно) ──
                    elif type_atm == 1 and plen == 2:
                        meas_val, = unpack_from('<h', msg, offset)
                        print(f"[АТМ-ИАЭ] измерение канал={pnum}: {meas_val} мВ")
                    else:
                        print(f"[INFO] АТМ необработанный: тип={type_atm}, pnum={pnum}")

                offset += plen
        else:
            print(f"[INFO] Пакет ID={packet_id}, длина={len(msg)}")


# ──────────────────────────────────────────────────────────────────────────────
# Основной рабочий поток (отправка команд + измерения)
# ──────────────────────────────────────────────────────────────────────────────

def send_commands_thread(sock, commands: dict, start_iae_idx: int,
                         callback, callback_dialog):
    """
    Главный цикл тестирования ИАЭ:
      - стартовые команды (комплекс, АТМ, БИАБ, контакторы ИАЭ)
      - для каждого канала ИАЭ: перебор уставок напряжения
      - диалог «Переставьте щупы»
      - финишные команды
    """
    clean_csv_for_iae(start_iae_idx)
    try:
        # ── Стартовые команды ─────────────────────────────────────────────────
        # Режим «Комплекс» (TipKU=8, KodKU=1)
        _send_no_param(sock, 8, 1)
        sleep(0.2)
        # Включить АТМ (TipKU=9, KodKU=1)
        _send_no_param(sock, 9, 1)
        sleep(0.2)
        # Включить БИАБ (TipKU=7, KodKU=1)
        _send_no_param(sock, 7, 1)
        sleep(0.2)
        # Подключить контакторы ИАЭ (TipKU=7, KodKU=5)
        _send_no_param(sock, 7, 5)
        sleep(0.5)

        current_IAE = start_iae_idx  # 0-based (0..23)

        while current_IAE < 24:

            if stop_iae_cycle.is_set():
                break

            globals()['active_IAE'] = current_IAE

            # ── Перебор уставок для текущего канала ──────────────────────────
            for ust in range(2000, 5000 + ustavka_change_iae, ustavka_change_iae):

                if stop_iae_cycle.is_set():
                    break

                with ustavka_lock:
                    ev = threading.Event()
                    ustavka_response[ust] = (ev, None)

                # Команда: TipKU=5, KodKU=current_IAE, параметр WORD=ust
                pkt = pk.Short_Comanda_KU(5, current_IAE, 1).set_ustavka(ust, 3)
                sock.send(pkt)

                # Ожидаем подтверждения из АТМ
                if ev.wait(timeout=10):
                    _, param_val = ustavka_response.pop(ust, (None, None))
                else:
                    param_val = None
                    print(f"[ИАЭ] Таймаут для уставки {ust} мВ, канал {current_IAE}")

                # Измерение напряжения прибором
                ag_val = Agilent_voltage()

                # Запись и обновление GUI
                write_to_csv(current_IAE, ust, param_val, ag_val, callback)

            if stop_iae_cycle.is_set():
                break

            # ── Диалог перестановки щупов ────────────────────────────────────
            if callback:
                _safe_callback(callback,
                               f"Переставьте щупы на канал ИАЭ {current_IAE + 2}")

            action = callback_dialog()

            if action == "stop":
                stop_iae_cycle.set()
                break
            elif action == "repeat":
                clean_csv_for_iae(current_IAE)
                continue           # повторить текущий канал
            elif action == "continue":
                current_IAE += 1
                continue
            else:
                current_IAE += 1
                continue

        # ── Финишные команды ──────────────────────────────────────────────────
        # Отключить контакторы ИАЭ (TipKU=7, KodKU=6)
        _send_no_param(sock, 7, 6)
        sleep(0.2)
        # Выключить БИАБ (TipKU=7, KodKU=2)
        _send_no_param(sock, 7, 2)
        sleep(0.2)
        # Отключить АТМ (TipKU=9, KodKU=2)
        _send_no_param(sock, 9, 2)
        sleep(0.2)
        # Режим «Автоном» (TipKU=8, KodKU=2)
        _send_no_param(sock, 8, 2)

    except Exception as e:
        print(f"[ИАЭ] Исключение в рабочем потоке: {e}")
        if callback:
            _safe_callback(callback, f"Ошибка: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Точка входа: запуск клиента
# ──────────────────────────────────────────────────────────────────────────────

def client_thread(host: str, port: int, commands: dict,
                  callback=None, show_probe_dialog=None,
                  com_agilent: str = "COM3"):
    """
    Создать TCP-соединение, настроить Agilent и запустить потоки
    отправки/приёма для тестирования ИАЭ.
    """
    global sock_ref
    init_agilent_port(com_agilent)

    if not ser_a:
        print("[ИАЭ] Agilent не подключён — прерывание.")
        if callback:
            _safe_callback(callback, "Ошибка: Agilent не подключён")
        return

    try:
        settings_Agilent_IAE()

        with socket.create_connection((host, port)) as sock:
            sock_ref = sock

            t_send = threading.Thread(
                target=send_commands_thread,
                args=(sock, commands, start_iae, callback, show_probe_dialog),
                daemon=True,
            )
            t_recv = threading.Thread(
                target=receive_messages,
                args=(sock,),
                daemon=True,
            )

            t_send.start()
            t_recv.start()

            t_send.join()
            t_recv.join()

    except ConnectionError as e:
        print(f"[ИАЭ] Ошибка соединения: {e}")
        if callback:
            _safe_callback(callback, f"Ошибка подключения: {e}")
    finally:
        stop_thread.set()
        sock_forced_close()
        close_agilent_port()
