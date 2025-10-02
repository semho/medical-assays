"""
Единая база знаний о медицинских параметрах
Все данные о параметрах в одном месте
"""

PARAMETERS = {
    # ========== ОБЩИЙ АНАЛИЗ КРОВИ ==========
    "hemoglobin": {
        "names_ru": ["Гемоглобин"],
        "aliases": ["hemoglobin", "hgb", "hb"],
        "type": "blood_general",
        "units": ["г/л", "g/L"],
        "reference": {"male": (130, 170), "female": (120, 150)},
        "range": (50, 250),
        "keywords": ["гемоглобин", "hgb", "hb"],
    },
    "erythrocytes": {
        "names_ru": ["Эритроциты"],
        "aliases": ["erythrocytes", "rbc", "red_blood_cells"],
        "type": "blood_general",
        "units": ["×10¹²/л", "×10^12/L"],
        "reference": {"male": (4.3, 5.7), "female": (3.8, 5.1)},
        "range": (1, 10),
        "keywords": ["эритроциты", "rbc"],
    },
    "leukocytes": {
        "names_ru": ["Лейкоциты"],
        "aliases": ["leukocytes", "wbc", "white_blood_cells"],
        "type": "blood_general",
        "units": ["×10⁹/л", "×10^9/L"],
        "reference": (3.89, 9.23),
        "range": (1, 50),
        "keywords": ["лейкоциты", "wbc"],
    },
    "platelets": {
        "names_ru": ["Тромбоциты"],
        "aliases": ["platelets", "plt"],
        "type": "blood_general",
        "units": ["×10⁹/л", "×10^9/L"],
        "reference": (150, 400),
        "range": (50, 1000),
        "keywords": ["тромбоциты", "plt", "platelets"],
    },
    "hematocrit": {
        "names_ru": ["Гематокрит"],
        "aliases": ["hematocrit", "hct"],
        "type": "blood_general",
        "units": ["%"],
        "reference": {"male": (40, 48), "female": (36, 42)},
        "range": (10, 80),
        "keywords": ["гематокрит", "hct"],
    },
    "esr": {
        "names_ru": ["СОЭ"],
        "aliases": ["esr", "esr_westergren"],
        "type": "blood_general",
        "units": ["мм/ч", "mm/h"],
        "reference": {"male": (0, 10), "female": (0, 15)},
        "range": (0, 50),
        "keywords": ["соэ (метод", "скорости оседания эритроцитов"],
    },
    # Лейкоформула
    "neutrophils_percentage": {
        "names_ru": ["Нейтрофилы %"],
        "aliases": ["neutrophils", "neutrophils_percentage", "neutrophils_percent", "ne_percent"],
        "type": "blood_general",
        "units": ["%"],
        "reference": (47, 72),
        "range": (0, 100),
        "keywords": ["нейтрофилы", "neutrophils", "ne"],
    },
    "lymphocytes_percentage": {
        "names_ru": ["Лимфоциты %"],
        "aliases": ["lymphocytes", "lymphocytes_percentage", "lymphocytes_percent", "lymf_percent"],
        "type": "blood_general",
        "units": ["%"],
        "reference": (19, 37),
        "range": (0, 100),
        "keywords": ["лимфоциты", "lymphocytes", "lymf"],
    },
    "monocytes_percentage": {
        "names_ru": ["Моноциты %"],
        "aliases": ["monocytes", "monocytes_percentage", "monocytes_percent", "mon_percent"],
        "type": "blood_general",
        "units": ["%"],
        "reference": (3, 11),
        "range": (0, 50),
        "keywords": ["моноциты", "monocytes", "mon"],
    },
    "eosinophils_percentage": {
        "names_ru": ["Эозинофилы %"],
        "aliases": ["eosinophils", "eosinophils_percentage", "eosinophils_percent", "eo_percent"],
        "type": "blood_general",
        "units": ["%"],
        "reference": (0.5, 5),
        "range": (0, 50),
        "keywords": ["эозинофилы", "eosinophils", "eo"],
    },
    "basophils_percentage": {
        "names_ru": ["Базофилы %"],
        "aliases": ["basophils", "basophils_percentage", "basophils_percent", "ba_percent"],
        "type": "blood_general",
        "units": ["%"],
        "reference": (0, 1),
        "range": (0, 20),
        "keywords": ["базофилы", "basophils", "ba"],
    },
    # ========== БИОХИМИЯ ==========
    "glucose": {
        "names_ru": ["Глюкоза"],
        "aliases": ["glucose", "sugar"],
        "type": "blood_biochem",
        "units": ["ммоль/л", "mmol/L"],
        "reference": (3.3, 5.5),
        "range": (1, 30),
        "keywords": ["глюкоза", "glucose"],
    },
    "creatinine": {
        "names_ru": ["Креатинин в крови"],
        "aliases": ["creatinine"],
        "type": "blood_biochem",
        "units": ["мкмоль/л", "μmol/L"],
        "reference": {"male": (62, 106), "female": (44, 80)},
        "range": (20, 500),
        "keywords": ["креатинин", "creatinine"],
    },
    "urea": {
        "names_ru": ["Мочевина"],
        "aliases": ["urea"],
        "type": "blood_biochem",
        "units": ["ммоль/л", "mmol/L"],
        "reference": (2.76, 8.07),
        "range": (1, 50),
        "keywords": ["мочевина", "urea"],
    },
    "bilirubin_total": {
        "names_ru": ["Билирубин общий"],
        "aliases": ["bilirubin_total", "total_bilirubin"],
        "type": "blood_biochem",
        "units": ["мкмоль/л", "μmol/L"],
        "reference": (5, 21),
        "range": (0, 500),
        "keywords": ["билирубин общий", "total bilirubin"],
    },
    "alt": {
        "names_ru": ["АЛТ (аланинаминотрансфераза)"],
        "aliases": ["alt", "alat", "alanine_aminotransferase"],
        "type": "blood_biochem",
        "units": ["Ед/л", "U/L"],
        "reference": {"male": (0, 41), "female": (0, 33)},
        "range": (0, 500),
        "keywords": ["алт", "аланинаминотрансфераза"],
    },
    "ast": {
        "names_ru": ["АСТ (аспартатаминотрансфераза)"],
        "aliases": ["ast", "asat", "aspartate_aminotransferase"],
        "type": "blood_biochem",
        "units": ["Ед/л", "U/L"],
        "reference": {"male": (0, 37), "female": (0, 31)},
        "range": (0, 500),
        "keywords": ["аст", "аспартатаминотрансфераза"],
    },
    "cholesterol": {
        "names_ru": ["Холестерин общий"],
        "aliases": ["cholesterol", "total_cholesterol"],
        "type": "blood_biochem",
        "units": ["ммоль/л", "mmol/L"],
        "reference": (3.0, 5.2),
        "range": (1, 20),
        "keywords": ["холестерин общий", "total cholesterol"],
    },
    "gfr_ckd_epi": {
        "names_ru": ["Скорость клубочковой фильтрации (СКФ), расчет по формуле CKD-EPI"],
        "aliases": ["gfr_ckd_epi", "gfr", "egfr"],
        "type": "blood_biochem",
        "units": ["мл/мин/1,73м²", "mL/min/1.73m²"],
        "reference": (90, 120),
        "range": (5, 150),
        "keywords": ["скф", "gfr", "ckd-epi"],
    },
    # ========== ГОРМОНЫ ==========
    "tsh": {
        "names_ru": ["ТТГ (тиреотропный гормон)"],
        "aliases": ["tsh", "thyroid_stimulating_hormone"],
        "type": "hormones",
        "units": ["мМЕ/мл", "mIU/mL", "мкМЕ/мл"],
        "reference": (0.27, 4.2),
        "range": (0.1, 10),
        "keywords": ["ттг", "tsh", "thyroid stimulating hormone"],
    },
    "free_t4": {
        "names_ru": ["Свободный Т4"],
        "aliases": ["free_t4", "ft4", "free_thyroxine"],
        "type": "hormones",
        "units": ["пмоль/л", "pmol/L"],
        "reference": (12.0, 22.0),
        "range": (5, 30),
        "keywords": ["свободный т4", "free t4", "ft4"],
    },
    "free_t3": {
        "names_ru": ["Свободный Т3"],
        "aliases": ["free_t3", "ft3", "free_triiodothyronine"],
        "type": "hormones",
        "units": ["пмоль/л", "pmol/L"],
        "reference": (3.1, 6.8),
        "range": (1, 15),
        "keywords": ["свободный т3", "free t3", "ft3"],
    },
    "testosterone": {
        "names_ru": ["Тестостерон"],
        "aliases": ["testosterone"],
        "type": "hormones",
        "units": ["нмоль/л", "nmol/L"],
        "reference": {"male": (7.6, 31.4), "female": (0.29, 1.67)},
        "range": (0, 50),
        "keywords": ["тестостерон", "testosterone"],
    },
    "estradiol": {
        "names_ru": ["Эстрадиол"],
        "aliases": ["estradiol", "e2"],
        "type": "hormones",
        "units": ["пг/мл", "pg/mL"],
        "reference": (25.8, 60.7),  # Зависит от фазы цикла
        "range": (5, 500),
        "keywords": ["эстрадиол", "estradiol"],
    },
    "prolactin": {
        "names_ru": ["Пролактин"],
        "aliases": ["prolactin", "prl"],
        "type": "hormones",
        "units": ["нг/мл", "ng/mL", "мМЕ/мл"],
        "reference": {"male": (2.5, 17), "female": (4.5, 33)},
        "range": (0, 100),
        "keywords": ["пролактин", "prolactin"],
    },
    "cortisol": {
        "names_ru": ["Кортизол"],
        "aliases": ["cortisol"],
        "type": "hormones",
        "units": ["нмоль/л", "nmol/L"],
        "reference": (138, 690),  # Утренний
        "range": (0, 1500),
        "keywords": ["кортизол", "cortisol"],
    },
}

# ========== ГЕНЕРИРУЕМЫЕ СЛОВАРИ ==========

# Русские названия для всех алиасов
PARAMETER_NAMES_RU = {}
for param_key, param in PARAMETERS.items():
    ru_name = param["names_ru"][0]
    for alias in param["aliases"]:
        PARAMETER_NAMES_RU[alias.lower()] = ru_name

# Маппинг типов
PARAMETER_TYPE_MAP = {}
for param_key, param in PARAMETERS.items():
    for alias in param["aliases"]:
        PARAMETER_TYPE_MAP[alias.lower()] = param["type"]

# Валидационные диапазоны
RANGES_PARSER = {alias.lower(): param["range"] for param_key, param in PARAMETERS.items() for alias in param["aliases"]}

# Парсеры по типам анализов
BLOOD_PARSER = {}
BIOCHEM_PARSER = {}
HORMONES_PARSER = {}

for param_key, param in PARAMETERS.items():
    if param["type"] == "blood_general":
        BLOOD_PARSER[param_key] = param["keywords"]
    elif param["type"] == "blood_biochem":
        BIOCHEM_PARSER[param_key] = param["keywords"]
    elif param["type"] == "hormones":
        HORMONES_PARSER[param_key] = param["keywords"]

# Лейкоформула (параметры с %)
BLOOD_LEUKO_PARAMS = [
    "neutrophils_percentage",
    "lymphocytes_percentage",
    "monocytes_percentage",
    "eosinophils_percentage",
    "basophils_percentage",
]

# Алиасы для GPT парсера
GPT_PARSER_ALIASES = {
    "wbc": "leukocytes",
    "white_blood_cells": "leukocytes",
    "rbc": "erythrocytes",
    "red_blood_cells": "erythrocytes",
    "hgb": "hemoglobin",
    "hb": "hemoglobin",
    "plt": "platelets",
    "hct": "hematocrit",
    "neutrophils_ne": "neutrophils_percentage",
    "ne_percent": "neutrophils_percentage",
    "lymphocytes_lymf": "lymphocytes_percentage",
    "lymf_percent": "lymphocytes_percentage",
    "monocytes_mon": "monocytes_percentage",
    "mon_percent": "monocytes_percentage",
    "eosinophils_eo": "eosinophils_percentage",
    "eo_percent": "eosinophils_percentage",
    "basophils_ba": "basophils_percentage",
    "ba_percent": "basophils_percentage",
}


# Вспомогательные функции
def get_parameter_info(params_key: str) -> dict:
    """Получить полную информацию о параметре"""
    param_key_lower = params_key.lower()

    # Ищем в алиасах
    for key, params in PARAMETERS.items():
        if param_key_lower in [a.lower() for a in params["aliases"]]:
            return {
                "canonical_key": key,
                "ru_name": params["names_ru"][0],
                "type": params["type"],
                "units": params["units"],
                "reference": params["reference"],
                "range": params["range"],
            }

    return None


def get_reference_range(params_key: str, gender: str = None) -> tuple:
    """Получить референсный диапазон для параметра"""
    info = get_parameter_info(params_key)
    if not info:
        return None

    ref = info["reference"]

    # Если референс зависит от пола
    if isinstance(ref, dict):
        if gender and gender.lower() in ref:
            return ref[gender.lower()]
        # Возвращаем средний диапазон
        male_range = ref.get("male", (0, 0))
        female_range = ref.get("female", (0, 0))
        return (min(male_range[0], female_range[0]), max(male_range[1], female_range[1]))

    return ref


def validate_value(params_key: str, value: float) -> bool:
    """Проверить, что значение в допустимом диапазоне"""
    param_key_lower = params_key.lower()

    if param_key_lower in RANGES_PARSER:
        min_val, max_val = RANGES_PARSER[param_key_lower]
        return min_val <= value <= max_val

    return True  # Если нет диапазона, считаем валидным
