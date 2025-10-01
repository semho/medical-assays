from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, AnalysisSession, MedicalData, SecurityLog


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя"""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для профиля пользователя"""

    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ["user", "language_preference", "created_at", "updated_at"]
        read_only_fields = ["user", "created_at", "updated_at"]
        # Исключаем encryption_key из API для безопасности


class AnalysisSessionSerializer(serializers.ModelSerializer):
    """Сериализатор для сессии анализа"""

    user = serializers.StringRelatedField(read_only=True)
    processing_duration = serializers.SerializerMethodField()
    file_exists = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisSession
        fields = [
            "id",
            "user",
            "upload_timestamp",
            "processing_status",
            "file_deleted_timestamp",
            "analysis_type",
            "original_filename",
            "error_message",
            "processing_started",
            "processing_completed",
            "processing_duration",
            "file_exists",
        ]
        read_only_fields = ["temp_file_path"]  # Скрываем путь к файлу

    def get_processing_duration(self, obj):
        """Вычислить длительность обработки"""
        if obj.processing_started and obj.processing_completed:
            duration = obj.processing_completed - obj.processing_started
            return duration.total_seconds()
        return None

    def get_file_exists(self, obj):
        """Проверить, существует ли временный файл"""
        return bool(obj.temp_file_path and obj.file_deleted_timestamp is None)


class MedicalDataSerializer(serializers.ModelSerializer):
    """Сериализатор для медицинских данных"""

    user = serializers.StringRelatedField(read_only=True)
    session = AnalysisSessionSerializer(read_only=True)
    decrypted_data = serializers.SerializerMethodField()

    class Meta:
        model = MedicalData
        fields = ["id", "user", "session", "analysis_date", "analysis_type", "created_at", "decrypted_data"]
        # Исключаем encrypted_results из API

    def get_decrypted_data(self, obj):
        """Получить расшифрованные данные"""
        decrypted = obj.decrypt_data()
        if decrypted:
            # Возвращаем только parsed_data, скрываем raw_text
            return decrypted.get("parsed_data", {})
        return None


class FileUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки файлов"""

    file = serializers.FileField(help_text="PDF или изображение с результатами анализов")

    def validate_file(self, value):
        """Валидация загружаемого файла"""
        from django.conf import settings
        from pathlib import Path

        # Проверка размера
        if value.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            raise serializers.ValidationError(
                f"Файл слишком большой. Максимальный размер: {settings.FILE_UPLOAD_MAX_MEMORY_SIZE // (1024 * 1024)} МБ"
            )

        # Проверка расширения
        file_extension = Path(value.name).suffix.lower()
        if file_extension not in settings.ALLOWED_FILE_EXTENSIONS:
            raise serializers.ValidationError(
                f"Неподдерживаемый тип файла: {file_extension}. "
                f"Разрешены: {', '.join(settings.ALLOWED_FILE_EXTENSIONS)}"
            )

        return value


class SecurityLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов безопасности"""

    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SecurityLog
        fields = ["id", "user", "action", "details", "ip_address", "timestamp"]
        read_only_fields = ["id", "timestamp"]


class AnalysisStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики анализов"""

    total_analyses = serializers.IntegerField()
    by_type = serializers.DictField()
    recent_count = serializers.IntegerField()
    processing_stats = serializers.DictField()


class TrendAnalysisSerializer(serializers.Serializer):
    """Сериализатор для анализа трендов"""

    parameter = serializers.CharField()
    values = serializers.ListField(child=serializers.DictField())
    trend = serializers.CharField()  # 'improving', 'declining', 'stable'
    trend_percentage = serializers.FloatField()
    recommendations = serializers.ListField(child=serializers.CharField())


class ComparisonResultSerializer(serializers.Serializer):
    """Сериализатор для результатов сравнения"""

    analysis1 = serializers.DictField()
    analysis2 = serializers.DictField()
    differences = serializers.DictField()
    summary = serializers.DictField()


class HealthReportSerializer(serializers.Serializer):
    """Сериализатор для медицинского отчета"""

    user_info = serializers.DictField()
    analysis_period = serializers.DictField()
    key_findings = serializers.ListField(child=serializers.CharField())
    trends = serializers.ListField(child=TrendAnalysisSerializer())
    recommendations = serializers.ListField(child=serializers.CharField())
    generated_at = serializers.DateTimeField()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    language_preference = serializers.ChoiceField(choices=[("ru", "Русский"), ("en", "English")], default="ru")

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm", "first_name", "last_name", "language_preference"]

    def validate(self, attrs):
        """Валидация паролей"""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs

    def validate_email(self, value):
        """Валидация email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def create(self, validated_data):
        """Создание пользователя с профилем"""
        from django.db import transaction

        language_preference = validated_data.pop("language_preference", "ru")
        validated_data.pop("password_confirm")

        with transaction.atomic():
            # Создаем пользователя
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
            )

            # Создаем профиль
            UserProfile.objects.create(user=user, language_preference=language_preference)

            # Логируем регистрацию
            SecurityLog.objects.create(
                user=user,
                action="USER_REGISTERED",
                details=f"Новый пользователь зарегистрировался: {user.username}",
                ip_address=None,
            )

        return user


class UserLoginSerializer(serializers.Serializer):
    """Сериализатор для входа пользователя"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Валидация данных входа"""
        from django.contrib.auth import authenticate

        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)

            if not user:
                raise serializers.ValidationError("Неверное имя пользователя или пароль")

            if not user.is_active:
                raise serializers.ValidationError("Аккаунт деактивирован")

            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Необходимо указать имя пользователя и пароль")


class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Валидация смены пароля"""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("Новые пароли не совпадают")
        return attrs

    def validate_old_password(self, value):
        """Проверка старого пароля"""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value


class DataExportSerializer(serializers.Serializer):
    """Сериализатор для экспорта данных"""

    format = serializers.ChoiceField(choices=[("json", "JSON"), ("csv", "CSV"), ("pdf", "PDF")], default="json")
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    analysis_types = serializers.ListField(child=serializers.CharField(), required=False)
    include_raw_data = serializers.BooleanField(default=False)

    def validate(self, attrs):
        """Валидация параметров экспорта"""
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError("Дата начала не может быть больше даты окончания")

        return attrs
