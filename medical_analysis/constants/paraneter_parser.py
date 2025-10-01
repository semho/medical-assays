GPT_PARSER_ALIASES = {
    "wbc": "leukocytes",
    "white_blood_cells": "leukocytes",
    "rbc": "erythrocytes",
    "red_blood_cells": "erythrocytes",
    "hgb": "hemoglobin",
    "hb": "hemoglobin",
    "plt": "platelets",
    "hct": "hematocrit",
    # Процентные варианты лейкоформулы
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

RANGES_PARSER = {
    "hemoglobin": (50, 250),
    "erythrocytes": (1, 10),
    "leukocytes": (1, 50),
    "platelets": (50, 1000),
    "hematocrit": (10, 80),
    "esr": (0, 50),  # СОЭ редко бывает > 50
    "neutrophils": (0, 100),
    "lymphocytes": (0, 100),
    "monocytes": (0, 50),
    "eosinophils": (0, 50),
    "basophils": (0, 20),
    "tsh": (0.1, 10),
    "free_t4": (5, 30),
}

BLOOD_PARSER = {
    "hemoglobin": ["гемоглобин", "hgb", "hb"],
    "erythrocytes": ["эритроциты", "rbc"],
    "leukocytes": ["лейкоциты", "wbc"],
    "platelets": ["тромбоциты", "plt", "platelets"],
    "hematocrit": ["гематокрит", "hct"],
    "esr": ["соэ (метод", "скорости оседания эритроцитов"],  # Более специфичный поиск
    "neutrophils": ["нейтрофилы", "neutrophils", "ne"],
    "lymphocytes": ["лимфоциты", "lymphocytes", "lymf"],
    "monocytes": ["моноциты", "monocytes", "mon"],
    "eosinophils": ["эозинофилы", "eosinophils", "eo"],
    "basophils": ["базофилы", "basophils", "ba"],
}

# Параметры лейкоформулы (нужны проценты)
BLOOD_LEUKO_PARAMS = ["neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]

BIOCHEM_PARSER = {
    "glucose": ["глюкоза", "glucose"],
    "creatinine": ["креатинин", "creatinine"],
    "urea": ["мочевина", "urea"],
    "alt": ["алт", "аланинаминотрансфераза"],
    "ast": ["аст", "аспартатаминотрансфераза"],
    "bilirubin_total": ["билирубин общий", "total bilirubin"],
    "cholesterol": ["холестерин общий", "total cholesterol"],
    "atherogenic_index": ["индекс атерогенности"],
}

HORMONES_PARSER = {
    "tsh": ["ттг", "tsh", "thyroid stimulating hormone"],
    "free_t4": ["свободный т4", "free t4", "ft4"],
    "free_t3": ["свободный т3", "free t3", "ft3"],
    "testosterone": ["тестостерон", "testosterone"],
    "estradiol": ["эстрадиол", "estradiol"],
    "prolactin": ["пролактин", "prolactin"],
    "cortisol": ["кортизол", "cortisol"],
}
