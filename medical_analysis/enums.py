from enum import Enum

from django.db import models


class LanguageChoices(models.TextChoices):
    RU = "ru", "Русский"
    EN = "en", "English"


class Status(models.TextChoices):
    UPLOADING = "uploading", "Загрузка"
    PROCESSING = "processing", "Обработка"
    COMPLETED = "completed", "Завершено"
    ERROR = "error", "Ошибка"


class AnalysisType(models.TextChoices):
    BLOOD_GENERAL = "blood_general", "Общий анализ крови"
    BLOOD_BIOCHEM = "blood_biochem", "Биохимический анализ"
    HORMONES = "hormones", "Гормональные анализы"
    OTHER = "other", "Другие анализы"


class LaboratoryType(models.TextChoices):
    INVITRO = "invitro", "Инвитро"
    HELIX = "helix", "Хеликс"
    KDL = "kdl", "КДЛ"
    GEMOTEST = "gemotest", "Гемотест"
    CMD = "cmd", "ЦМД"
    UNKNOWN = "unknown", "Неизвестно"
