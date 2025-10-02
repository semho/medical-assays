"""
Ключевые слова и паттерны для определения типов анализов
"""

from medical_analysis.enums import LaboratoryType

# Ключевые слова для типов анализов
ANALYSIS_KEYWORDS = {
    "blood_general": [
        "гемоглобин",
        "эритроциты",
        "лейкоциты",
        "соэ",
        "hemoglobin",
        "rbc",
        "wbc",
        "общий анализ крови",
        "cbc",
        "complete blood count",
        "тромбоциты",
        "platelets",
        "лейкоформула",
    ],
    "blood_biochem": [
        "глюкоза",
        "белок",
        "креатинин",
        "мочевина",
        "алт",
        "аст",
        "холестерин",
        "glucose",
        "protein",
        "creatinine",
        "urea",
        "alt",
        "ast",
        "bilirubin_total",
        "cholesterol",
        "биохимический анализ",
        "биохимия",
        "biochemistry",
        "липидный профиль",
    ],
    "hormones": [
        "ттг",
        "тироксин",
        "тестостерон",
        "эстрадиол",
        "пролактин",
        "tsh",
        "t4",
        "testosterone",
        "hormone",
        "гормон",
        "гормональный",
        "эндокринология",
    ],
}

# Паттерны единиц измерения
UNIT_PATTERNS = {
    "concentration": [
        r"ммоль/л",
        r"мкмоль/л",
        r"г/л",
        r"мг/л",
        r"mmol/l",
        r"μmol/l",
        r"g/l",
        r"mg/l",
    ],
    "cells": [
        r"\d+\^9/л",
        r"\d+\^12/л",
        r"×10⁹/л",
        r"×10¹²/л",
        r"x10\^9/l",
        r"x10\^12/l",
    ],
    "enzymes": [
        r"ед/л",
        r"ме/л",
        r"u/l",
        r"iu/l",
    ],
    "hormones": [
        r"мме/мл",
        r"мкме/мл",
        r"пмоль/л",
        r"нмоль/л",
        r"пг/мл",
        r"нг/мл",
        r"miu/ml",
        r"μiu/ml",
        r"pmol/l",
        r"nmol/l",
        r"pg/ml",
        r"ng/ml",
    ],
    "percent": [r"%"],
}

# Сигнатуры лабораторий
LABORATORY_SIGNATURES = {
    LaboratoryType.INVITRO.name: [
        "инвитро",
        "invitro",
        "www.invitro.ru",
        "cmd-online.ru",
    ],
    LaboratoryType.HELIX.name: [
        "хеликс",
        "helix",
        "www.helix.ru",
        "cmd helix",
    ],
    LaboratoryType.KDL.name: [
        "кдл",
        "kdl",
        "kdlmed.ru",
        "клинико-диагностическая лаборатория",
    ],
    LaboratoryType.GEMOTEST.name: [
        "гемотест",
        "gemotest",
        "gemotest.ru",
    ],
    LaboratoryType.CMD.name: [
        "цмд",
        "cmd",
        "cmd-online",
        "центр молекулярной диагностики",
    ],
}

# Паттерны для референсных диапазонов
REFERENCE_PATTERNS = [
    r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)",  # 3.5 - 5.5
    r"(\d+\.?\d*)\s*–\s*(\d+\.?\d*)",  # с длинным тире
    r"(\d+\.?\d*)\s*—\s*(\d+\.?\d*)",  # с еще более длинным тире
    r"от\s+(\d+\.?\d*)\s+до\s+(\d+\.?\d*)",  # от X до Y
    r"<\s*(\d+\.?\d*)",  # < 5.5
    r">\s*(\d+\.?\d*)",  # > 3.5
]
