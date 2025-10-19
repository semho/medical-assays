from enum import Enum
from django.utils.translation import gettext as _
from django.db import models


class LanguageChoices(models.TextChoices):
    RU = "ru", "Русский"
    EN = "en", "English"


class Status(models.TextChoices):
    UPLOADING = "uploading", _("Загрузка")
    PROCESSING = "processing", _("Обработка")
    OCR = "ocr", _("Распознавание текста")
    PARSING = "parsing", _("Анализ данных")
    COMPLETED = "completed", _("Завершено")
    ERROR = "error", _("Ошибка")


class AnalysisType(models.TextChoices):
    BLOOD_GENERAL = "blood_general", _("Общий анализ крови")
    BLOOD_BIOCHEM = "blood_biochem", _("Биохимический анализ")
    HORMONES = "hormones", _("Гормональные анализы")
    OTHER = "other", _("Другие анализы")


class LaboratoryType(models.TextChoices):
    INVITRO = "invitro", _("Инвитро")
    HELIX = "helix", _("Хеликс")
    KDL = "kdl", _("КДЛ")
    GEMOTEST = "gemotest", _("Гемотестм")
    CMD = "cmd", _("ЦМД")
    CITILAB = "citilab", _("Ситилаб")
    UNKNOWN = "unknown", _("Неизвестно")

class GptModel(models.TextChoices):
    GPT_4O_MINI = "gpt-4o-mini", "GPT-4o Mini (быстрый, дешёвый)"
    GPT_4O = "gpt-4o", "GPT-4o (медленный, дорогой, точный)"