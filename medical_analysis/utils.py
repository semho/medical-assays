import re
from typing import Tuple, Optional

from medical_analysis.constants import UNITS_DICT


def get_client_ip(request):
    """Получить IP адрес клиента"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")
    return ip


def get_all_units_list():
    """Получить список всех единиц измерения для autocomplete"""
    return [{"en": unit["en"], "ru": unit["ru"]} for unit in UNITS_DICT.values()]

def parse_value_with_operator(value_str: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Парсит значение с оператором сравнения

    Примеры:
        "123.45" -> (123.45, None)
        "< 0.30" -> (0.30, "<")
        "> 100" -> (100.0, ">")
        "≤ 5.5" -> (5.5, "≤")

    Returns:
        (value, operator) или (None, None) если не удалось распарсить
    """
    if not value_str:
        return None, None

    value_str = str(value_str).strip()

    # Паттерн: опциональный оператор + число
    pattern = r'^([<>≤≥]?)\s*(\d+(?:[.,]\d+)?)$'
    match = re.match(pattern, value_str)

    if not match:
        return None, None

    operator = match.group(1) or None
    value = float(match.group(2).replace(',', '.'))

    return value, operator