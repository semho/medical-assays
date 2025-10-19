import json
import logging

from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
import base64

from medical_analysis.enums import LanguageChoices, Status, AnalysisType, LaboratoryType, GptModel, SubcriptionType
from medical_analysis.utils.i18n_helpers import get_analysis_type_display, get_subscription_type_display

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    """Профиль пользователя с ключом шифрования"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    encryption_key = models.TextField(help_text="Зашифрованный индивидуальный ключ")
    language_preference = models.CharField(max_length=2, choices=LanguageChoices.choices, default=LanguageChoices.RU)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Профиль {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.encryption_key:
            # Генерируем индивидуальный ключ для пользователя
            key = Fernet.generate_key()
            self.encryption_key = base64.b64encode(key).decode()
        super().save(*args, **kwargs)

    def get_fernet_cipher(self):
        """Получить объект Fernet для шифрования/расшифровки"""
        key = base64.b64decode(self.encryption_key.encode())
        return Fernet(key)

class Subscription(models.Model):
    """Подписка пользователя"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    subscription_type = models.CharField(max_length=10, choices=SubcriptionType, default=SubcriptionType.TRIAL, db_index=True)
    upload_limit = models.PositiveIntegerField(default=5)
    used_uploads = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def can_upload(self):
        if self.subscription_type == SubcriptionType.PAID:
            return True
        return self.used_uploads < self.upload_limit

    def remaining_uploads(self):
        if self.subscription_type == SubcriptionType.PAID:
            return float('inf')
        return self.upload_limit - self.used_uploads

    def __str__(self):
        return f"{self.user.username} - {get_subscription_type_display(self.subscription_type)}"

class AnalysisSession(models.Model):
    """Сессия обработки анализа"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analysis_sessions")
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADING)
    file_deleted_timestamp = models.DateTimeField(null=True, blank=True)
    analysis_type = models.CharField(max_length=20, choices=AnalysisType.choices, null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    temp_file_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    processing_started = models.DateTimeField(null=True, blank=True)
    processing_completed = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-upload_timestamp"]

    def __str__(self):
        return f"Сессия {self.pk} - {self.user.username} - {self.processing_status}"

    def get_analysis_type_display(self):
        return get_analysis_type_display(self.analysis_type)

class MedicalData(models.Model):
    """Зашифрованные медицинские данные"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medical_data")
    session = models.OneToOneField(
        AnalysisSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_data"
    )
    encrypted_results = models.TextField(help_text="Зашифрованные результаты анализов")
    analysis_date = models.DateField(help_text="Дата проведения анализа")
    analysis_type = models.CharField(max_length=20, choices=AnalysisType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False, help_text="Пользователь подтвердил правильность данных")
    laboratory = models.CharField(
        choices=LaboratoryType.choices,
        max_length=50,
        blank=True,
        default=LaboratoryType.UNKNOWN,
        help_text="Лаборатория-источник анализа",
    )

    class Meta:
        ordering = ["-analysis_date", "-created_at"]
        verbose_name = "Медицинские данные"
        verbose_name_plural = "Медицинские данные"

    def __str__(self):
        return f"Анализ {self.analysis_type} - {self.user.username} - {self.analysis_date}"

    def encrypt_and_save(self, data_dict):
        """Шифрование данных перед сохранением"""
        cipher = self.user.profile.get_fernet_cipher()
        json_data = json.dumps(data_dict, ensure_ascii=False).encode()
        encrypted_data = cipher.encrypt(json_data)
        self.encrypted_results = base64.b64encode(encrypted_data).decode()
        self.save()

    def decrypt_data(self):
        """Расшифровка данных"""
        try:
            cipher = self.user.profile.get_fernet_cipher()
            encrypted_bytes = base64.b64decode(self.encrypted_results.encode())
            decrypted_data = cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"Ошибка расшифровки: {e}")
            return None

    def get_analysis_type_display(self):
        return get_analysis_type_display(self.analysis_type)


class SecurityLog(models.Model):
    """Лог безопасности для аудита"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} - {self.timestamp}"

class ParserSettings(models.Model):
    """Настройки парсера медицинских анализов (Singleton)"""

    # GPT настройки
    gpt_enabled = models.BooleanField(
        default=True,
        verbose_name="Использовать GPT",
        help_text="Включить/выключить парсинг через GPT"
    )

    gpt_model = models.CharField(
        max_length=50,
        default=GptModel.GPT_4O_MINI,
        choices=GptModel.choices,
        verbose_name="Модель GPT"
    )

    # Fallback настройки
    fallback_enabled = models.BooleanField(
        default=True,
        verbose_name="Использовать fallback",
        help_text="Переключаться на regex при недоступности GPT"
    )

    # Мониторинг
    log_gpt_costs = models.BooleanField(
        default=True,
        verbose_name="Логировать стоимость",
        help_text="Записывать стоимость GPT-запросов"
    )

    max_cost_per_request = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0.05,
        verbose_name="Макс. стоимость запроса ($)",
        help_text="Предупреждение при превышении"
    )

    # Технические параметры
    max_input_tokens = models.IntegerField(
        default=8000,
        verbose_name="Макс. входных токенов"
    )

    max_output_tokens = models.IntegerField(
        default=2000,
        verbose_name="Макс. выходных токенов"
    )

    temperature = models.FloatField(
        default=0.1,
        verbose_name="Temperature",
        help_text="0.0 - детерминированно, 1.0 - креативно"
    )

    # Метаданные
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Обновлено"
    )

    class Meta:
        verbose_name = "Настройки парсера"
        verbose_name_plural = "Настройки парсера"

    def __str__(self):
        return f"Настройки парсера (GPT: {'вкл' if self.gpt_enabled else 'выкл'})"

    def save(self, *args, **kwargs):
        # Singleton pattern - только одна запись
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Получить текущие настройки (создать если не существует)"""
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            logger.info("Created default parser settings")
        return obj