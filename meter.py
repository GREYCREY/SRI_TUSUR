"""
meter.py — общий модуль для работы с измерительным прибором.

Поддерживает два типа приборов:
  TYPE_AGILENT  — Agilent 34401A (9600 8-N-2, команды 34401A SCPI)
  TYPE_GDM79061 — GW Instek GDM-79061 (9600 8-N-1, нативный набор GDM-906X)

Поддерживает два режима измерения:
  MODE_FRES — 4-проводное сопротивление (для ИДТ)
  MODE_DCV  — постоянное напряжение    (для ИАЭ)

Является единственным владельцем serial-соединения. Оба модуля
(biab200.py и biab200_iae.py) работают только через функции этого модуля.
"""

import serial
import threading
from time import sleep

# ── Публичные константы ───────────────────────────────────────────────────────
MODE_FRES = "fres"
MODE_DCV  = "dcv"

TYPE_AGILENT  = "agilent"
TYPE_GDM79061 = "gdm79061"

# ── Состояние модуля ──────────────────────────────────────────────────────────
_ser: serial.Serial | None = None
_lock          = threading.Lock()
_current_mode: str | None  = None
_meter_type:   str         = TYPE_AGILENT


# ─────────────────────────────────────────────────────────────────────────────
# Управление соединением
# ─────────────────────────────────────────────────────────────────────────────

def open_port(port_name: str, meter_type: str = TYPE_AGILENT) -> bool:
    """Открыть COM-порт. Возвращает True при успехе."""
    global _ser, _meter_type, _current_mode
    close_port()                       # закрыть старое соединение, если было
    _meter_type   = meter_type
    _current_mode = None

    stopbits = (2 if meter_type == TYPE_AGILENT
                else 1)
    try:
        _ser = serial.Serial(
            port=port_name, baudrate=9600,
            bytesize=8, parity= 'N',
            stopbits=stopbits, timeout=5,
        )
        print(f"[Meter] Открыт: {meter_type} на {port_name}")
        return True
    except serial.SerialException as e:
        print(f"[Meter] Ошибка открытия '{port_name}': {e}")
        _ser = None
        return False


def is_open() -> bool:
    return bool(_ser and _ser.is_open)


def close_port():
    """Закрыть порт. Для GDM предварительно снимает дистанционный режим."""
    global _ser, _current_mode
    try:
        if _ser and _ser.is_open:
            if _meter_type == TYPE_GDM79061:
                _ser.write(b"SYSTem:LOCal\n")
                sleep(0.1)
            _ser.close()
    except Exception as e:
        print(f"[Meter] Ошибка закрытия: {e}")
    finally:
        _ser = None
        _current_mode = None


# ─────────────────────────────────────────────────────────────────────────────
# Конфигурация и измерение (публичный интерфейс)
# ─────────────────────────────────────────────────────────────────────────────

def configure(mode: str):
    """
    Настроить прибор на нужный режим измерения.
    Вызов с уже установленным режимом — безопасен (пропускается).
    """
    global _current_mode
    if not is_open():
        return
    if mode == _current_mode:
        return
    with _lock:
        if _meter_type == TYPE_AGILENT:
            _cfg_agilent(mode)
        else:
            _cfg_gdm(mode)
        _current_mode = mode


def measure() -> float | None:
    """
    Выполнить одиночное измерение в текущем режиме.
    Возвращает float (Ом или В) или None при ошибке/перегрузке.
    """
    if not is_open():
        return None
    return _meas_agilent() if _meter_type == TYPE_AGILENT else _meas_gdm()


def current_mode() -> str | None:
    return _current_mode


# ─────────────────────────────────────────────────────────────────────────────
# Agilent 34401A
# ─────────────────────────────────────────────────────────────────────────────

def _send_a(cmd: bytes):
    _ser.write(cmd)
    sleep(0.1)


def _cfg_agilent(mode: str):
    print(f"[Agilent] Настройка → {mode}")
    _send_a(b'SYST:REM\r\n')
    if mode == MODE_FRES:
        _send_a(b'CONF:FRES\r\n')
        _send_a(b'FRES:NPLC 1\r\n')
    else:                              # DCV
        _send_a(b'CONF:VOLT:DC 10\r\n')
        _send_a(b'VOLT:DC:NPLC 1\r\n')
    _send_a(b'SAMP:COUN 1\r\n')
    _send_a(b'TRIG:SOUR IMM\r\n')
    print(f"[Agilent] Готов: {mode}")


def _meas_agilent() -> float | None:
    try:
        with _lock:
            _ser.write(b'INITiate:IMMediate\n')
            sleep(0.5)
            _ser.write(b'FETCH?\r\n')
            raw = _ser.readline().decode("ASCII").rstrip()
        if 'E' in raw:
            m, e = raw.split('E')
            val  = float(m) * (10 ** int(e))
            if abs(val) > 1e30:
                print(f"[Agilent] Перегрузка: {raw}")
                return None
            return round(val, 6)
        return None
    except Exception as ex:
        print(f"[Agilent] Ошибка измерения: {ex}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GW Instek GDM-79061  (нативный набор команд GDM-906X)
# ─────────────────────────────────────────────────────────────────────────────

def _send_g(cmd: str):
    _ser.write((cmd + "\n").encode("ASCII"))
    sleep(0.1)


def _cfg_gdm(mode: str):
    print(f"[GDM-79061] Настройка → {mode}")
    _send_g("SYSTem:REMote")
    if mode == MODE_FRES:
        _send_g("CONFigure:FRESistance")
        _send_g("SENSe:FRESistance:NPLCycles 1")
        _send_g("SENSe:FRESistance:AZ:STATe ON")
    else:                              # DCV
        _send_g("CONFigure:VOLTage:DC 10")
        _send_g("SENSe:VOLTage:DC:NPLCycles 1")
        _send_g("SENSe:VOLTage:DC:AZ:STATe ON")
    _send_g("SAMPle:COUNt 1")
    _send_g("TRIGger:SOURce IMMediate")
    print(f"[GDM-79061] Готов: {mode}")


def _meas_gdm() -> float | None:
    """READ? блокирует прибор до конца интеграции и сразу отдаёт результат."""
    try:
        with _lock:
            _ser.write(b"READ?\n")
            raw = _ser.readline().decode("ASCII", errors="replace").rstrip()
        val = float(raw)
        if abs(val) > 1e30:
            print(f"[GDM-79061] Перегрузка: {raw}")
            return None
        return round(val, 6)
    except Exception as ex:
        print(f"[GDM-79061] Ошибка измерения: {ex}")
        return None
