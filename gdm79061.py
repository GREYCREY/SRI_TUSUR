

import serial
import threading
from time import sleep

# ──────────────────────────────────────────────────────────────────────────────
# Константы конфигурации RS-232 для GDM-79061
# ──────────────────────────────────────────────────────────────────────────────
# На самом приборе должно быть установлено:
#   Remote Control → Configure RS232 Interface:
#     Baud Rate = 9600
#     FlowCtrl  = None
#     TX Term   = LF  (или CR+LF)

GDM_BAUD     = 9600
GDM_BYTESIZE = 8
GDM_PARITY   = serial.PARITY_NONE
GDM_STOPBITS = serial.STOPBITS_ONE   # GDM-906X: строго 8-N-1
GDM_TIMEOUT  = 6                     # секунд; READ? занимает до ~1 PLC + накладные

# ──────────────────────────────────────────────────────────────────────────────
# Состояние
# ──────────────────────────────────────────────────────────────────────────────
_ser: serial.Serial | None = None
_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
# Открытие / закрытие порта
# ──────────────────────────────────────────────────────────────────────────────

def open_port(port_name: str) -> bool:
    """
    Открыть COM-порт для GDM-79061.
    Возвращает True при успехе.
    """
    global _sers
    try:
        _ser = serial.Serial(
            port=port_name,
            baudrate=GDM_BAUD,
            bytesize=GDM_BYTESIZE,
            parity=GDM_PARITY,
            stopbits=GDM_STOPBITS,
            timeout=GDM_TIMEOUT,
        )
        print(f"[GDM-79061] Порт {port_name} открыт (9600 8-N-1)")
        return True
    except serial.SerialException as e:
        print(f"[GDM-79061] Ошибка открытия порта '{port_name}': {e}")
        _ser = None
        return False


def close_port():
    """Вернуть прибор в местный режим и закрыть порт."""
    global _ser
    if _ser and _ser.is_open:
        try:
            _send_cmd("SYSTem:LOCal")          # снять дистанционное управление
            sleep(0.1)
            _ser.close()
        except Exception as e:
            print(f"[GDM-79061] Ошибка закрытия: {e}")
        finally:
            _ser = None


def is_open() -> bool:
    return bool(_ser and _ser.is_open)


# ──────────────────────────────────────────────────────────────────────────────
# Низкоуровневые операции
# ──────────────────────────────────────────────────────────────────────────────

def _send_cmd(cmd: str):
    """Отправить команду с завершителем LF."""
    if _ser and _ser.is_open:
        _ser.write((cmd + "\n").encode("ASCII"))


def _query(cmd: str) -> str:
    """
    Отправить запрос и получить ответ.
    READ? блокирует прибор до конца измерения — timeout порта должен быть
    достаточно большим (GDM_TIMEOUT).
    """
    if not (_ser and _ser.is_open):
        return ""
    _send_cmd(cmd)
    raw = _ser.readline()
    return raw.decode("ASCII", errors="replace").rstrip()


def _parse_value(raw: str) -> float | None:
    """
    Разобрать ответ вида '+1.234500E+00' в float.
    Возвращает None при перегрузке (|x| > 1e30) или ошибке.
    """
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = float(raw)
        if abs(value) > 1e30:                  # перегрузка / обрыв цепи
            print(f"[GDM-79061] Перегрузка: {raw}")
            return None
        return value
    except ValueError:
        print(f"[GDM-79061] Не удалось распарсить: {raw!r}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Настройка — DC-напряжение (для ИАЭ, диапазон 2–5 В)
# ──────────────────────────────────────────────────────────────────────────────

def configure_dcv(nplc: float = 1.0, rang: float = 10.0):
    """
    Настроить GDM-79061 на измерение постоянного напряжения.

    Параметры
    ---------
    nplc : количество периодов сети для интеграции (0.001 … 100)
    rang : диапазон, В. Для ИАЭ (2–5 В) оптимально rang=10.
    """
    print("[GDM-79061] Настройка: DC Voltage")
    _send_cmd("SYSTem:REMote")                   # дистанционное управление
    sleep(0.15)
    _send_cmd(f"CONFigure:VOLTage:DC {rang}")     # режим DC + диапазон
    sleep(0.15)
    _send_cmd(f"SENSe:VOLTage:DC:NPLCycles {nplc}")  # интеграция
    sleep(0.10)
    _send_cmd("SENSe:VOLTage:DC:AZ:STATe ON")    # Autozero вкл. (точность)
    sleep(0.10)
    _send_cmd("TRIGger:SOURce IMMediate")         # внутренний триггер
    sleep(0.10)
    _send_cmd("SAMPle:COUNt 1")                   # одно измерение на запрос
    sleep(0.10)
    print("[GDM-79061] Готов: DC Voltage, диапазон "
          f"{rang} В, NPLC={nplc}")


# ──────────────────────────────────────────────────────────────────────────────
# Настройка — 4-проводное сопротивление (для ИДТ)
# ──────────────────────────────────────────────────────────────────────────────

def configure_fres(nplc: float = 1.0):
    """
    Настроить GDM-79061 на 4-проводное измерение сопротивления.
    (Аналог CONF:FRES + FRES:NPLC в коде Agilent.)
    """
    print("[GDM-79061] Настройка: 4-Wire Resistance")
    _send_cmd("SYSTem:REMote")
    sleep(0.15)
    _send_cmd("CONFigure:FRESistance")            # 4-проводное сопротивление
    sleep(0.15)
    _send_cmd(f"SENSe:FRESistance:NPLCycles {nplc}")
    sleep(0.10)
    _send_cmd("SENSe:FRESistance:AZ:STATe ON")   # Autozero
    sleep(0.10)
    _send_cmd("TRIGger:SOURce IMMediate")
    sleep(0.10)
    _send_cmd("SAMPle:COUNt 1")
    sleep(0.10)
    print(f"[GDM-79061] Готов: 4W Resistance, NPLC={nplc}")


# ──────────────────────────────────────────────────────────────────────────────
# Измерения
# ──────────────────────────────────────────────────────────────────────────────

def measure_voltage() -> float | None:
    """
    Одиночное измерение DC-напряжения (В).

    READ? на GDM-906X: выполняет одно измерение и сразу возвращает результат.
    Не требует пары INITiate + sleep + FETCh? — прибор блокируется на время
    интеграции, поэтому timeout порта должен быть > NPLC / (50 Гц) + ~0.5 с.
    """
    with _lock:
        raw = _query("READ?")
    return _parse_value(raw)


def measure_resistance() -> float | None:
    """
    Одиночное 4-проводное измерение сопротивления (Ом).
    """
    with _lock:
        raw = _query("READ?")
    return _parse_value(raw)


def query_idn() -> str:
    """Вернуть строку идентификации прибора (*IDN?)."""
    with _lock:
        return _query("*IDN?")


# ──────────────────────────────────────────────────────────────────────────────
# Быстрая самопроверка (запустить из командной строки)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"

    if not open_port(port):
        sys.exit(1)

    print("IDN:", query_idn())

    print("\n--- Тест DC-напряжения ---")
    configure_dcv(nplc=1, rang=10)
    for i in range(3):
        v = measure_voltage()
        print(f"  Измерение {i+1}: {v} В")
        sleep(0.2)

    print("\n--- Тест 4-проводного сопротивления ---")
    configure_fres(nplc=1)
    for i in range(3):
        r = measure_resistance()
        print(f"  Измерение {i+1}: {r} Ом")
        sleep(0.2)

    close_port()
    print("\nГотово.")
