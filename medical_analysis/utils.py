from medical_analysis.constants import UNITS_DICT


def get_client_ip(request):
    """Получить IP адрес клиента"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")
    return ip


def get_all_units_list():
    """Получить список всех единиц измерения для autocomplete"""
    return [{"en": unit["en"], "ru": unit["ru"]} for unit in UNITS_DICT.values()]
