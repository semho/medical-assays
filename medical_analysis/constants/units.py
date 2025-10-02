"""Единицы измерения для медицинских параметров (EN/RU)"""

UNITS_DICT = {
    # Концентрация в крови
    "mmol_l": {"en": "mmol/L", "ru": "ммоль/л"},
    "umol_l": {"en": "μmol/L", "ru": "мкмоль/л"},
    "g_l": {"en": "g/L", "ru": "г/л"},
    "mg_l": {"en": "mg/L", "ru": "мг/л"},
    "mg_dl": {"en": "mg/dL", "ru": "мг/дл"},
    # Клеточные показатели
    "x10_9_l": {"en": "×10⁹/L", "ru": "×10⁹/л"},
    "x10_12_l": {"en": "×10¹²/L", "ru": "×10¹²/л"},
    "thou_ul": {"en": "thou/μL", "ru": "тыс/мкл"},
    # Ферменты
    "u_l": {"en": "U/L", "ru": "Ед/л"},
    "iu_l": {"en": "IU/L", "ru": "МЕ/л"},
    # Гормоны
    "miu_ml": {"en": "mIU/mL", "ru": "мМЕ/мл"},
    "uiu_ml": {"en": "μIU/mL", "ru": "мкМЕ/мл"},
    "pmol_l": {"en": "pmol/L", "ru": "пмоль/л"},
    "nmol_l": {"en": "nmol/L", "ru": "нмоль/л"},
    "pg_ml": {"en": "pg/mL", "ru": "пг/мл"},
    "ng_ml": {"en": "ng/mL", "ru": "нг/мл"},
    "ng_dl": {"en": "ng/dL", "ru": "нг/дл"},
    # Процентные и относительные
    "percent": {"en": "%", "ru": "%"},
    "ratio": {"en": "ratio", "ru": "отношение"},
    # Скорость и время
    "mm_h": {"en": "mm/h", "ru": "мм/ч"},
    "ml_min": {"en": "mL/min", "ru": "мл/мин"},
    "ml_min_1_73": {"en": "mL/min/1.73m²", "ru": "мл/мин/1,73м²"},
    # Специальные единицы
    "fl": {"en": "fL", "ru": "фл"},
    "pg": {"en": "pg", "ru": "пг"},
    # Без единиц
    "none": {"en": "", "ru": ""},
}

# Алиасы для распознавания
UNIT_ALIASES = {
    "ммоль/л": "mmol_l",
    "mmol/l": "mmol_l",
    "мкмоль/л": "umol_l",
    "μmol/l": "umol_l",
    "umol/l": "umol_l",
    "г/л": "g_l",
    "g/l": "g_l",
    "мг/л": "mg_l",
    "mg/l": "mg_l",
    "мг/дл": "mg_dl",
    "mg/dl": "mg_dl",
    "10^9/л": "x10_9_l",
    "×10⁹/л": "x10_9_l",
    "x10^9/l": "x10_9_l",
    "10^12/л": "x10_12_l",
    "×10¹²/л": "x10_12_l",
    "x10^12/l": "x10_12_l",
    "тыс/мкл": "thou_ul",
    "ед/л": "u_l",
    "u/l": "u_l",
    "ме/л": "iu_l",
    "iu/l": "iu_l",
    "мме/мл": "miu_ml",
    "мкме/мл": "uiu_ml",
    "miu/ml": "miu_ml",
    "μiu/ml": "uiu_ml",
    "пмоль/л": "pmol_l",
    "pmol/l": "pmol_l",
    "нмоль/л": "nmol_l",
    "nmol/l": "nmol_l",
    "пг/мл": "pg_ml",
    "pg/ml": "pg_ml",
    "нг/мл": "ng_ml",
    "ng/ml": "ng_ml",
    "нг/дл": "ng_dl",
    "ng/dl": "ng_dl",
    "%": "percent",
    "мм/ч": "mm_h",
    "mm/h": "mm_h",
    "мл/мин": "ml_min",
    "ml/min": "ml_min",
    "мл/мин/1,73м²": "ml_min_1_73",
    "мл/мин/1,73м^2": "ml_min_1_73",
    "ml/min/1.73m²": "ml_min_1_73",
    "фл": "fl",
    "fl": "fl",
    "пг": "pg",
    "pg": "pg",
}


def normalize_unit(unit_str: str) -> str:
    """Нормализация единицы измерения к стандартному виду"""
    if not unit_str:
        return ""

    unit_lower = unit_str.lower().strip()
    unit_key = UNIT_ALIASES.get(unit_lower)

    if unit_key:
        return UNITS_DICT[unit_key]["ru"]

    return unit_str
