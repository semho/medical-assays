from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import UserProfile, AnalysisSession, MedicalData, SecurityLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "language_preference", "created_at", "updated_at")
    list_filter = ("language_preference", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("encryption_key", "created_at", "updated_at")

    fieldsets = (
        ("Основная информация", {"fields": ("user", "language_preference")}),
        ("Безопасность", {"fields": ("encryption_key",), "classes": ("collapse",)}),
        ("Временные метки", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "original_filename",
        "analysis_type",
        "status_badge",
        "upload_timestamp",
        "processing_time",
    )
    list_filter = ("processing_status", "analysis_type", "upload_timestamp")
    search_fields = ("user__username", "original_filename", "id")
    readonly_fields = ("upload_timestamp", "processing_started", "processing_completed", "file_deleted_timestamp")

    fieldsets = (
        ("Информация о сессии", {"fields": ("user", "original_filename", "analysis_type")}),
        ("Статус обработки", {"fields": ("processing_status", "error_message")}),
        ("Файлы", {"fields": ("temp_file_path", "file_deleted_timestamp")}),
        ("Временные метки", {"fields": ("upload_timestamp", "processing_started", "processing_completed")}),
    )

    def status_badge(self, obj):
        colors = {"uploading": "#FFA500", "processing": "#1E90FF", "completed": "#28A745", "error": "#DC3545"}
        color = colors.get(obj.processing_status, "#6C757D")
        html = f'<span style="background-color: {color}; color: white; padding: 3px 10px; border-radius: 3px;">{obj.get_processing_status_display()}</span>'
        return mark_safe(html)

    status_badge.short_description = "Статус"

    def processing_time(self, obj):
        if obj.processing_started and obj.processing_completed:
            delta = obj.processing_completed - obj.processing_started
            return f"{delta.total_seconds():.2f} сек"
        return "-"

    processing_time.short_description = "Время обработки"


@admin.register(MedicalData)
class MedicalDataAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "analysis_type", "analysis_date", "created_at", "has_structured_data")
    list_filter = ("analysis_type", "analysis_date", "created_at")
    search_fields = ("user__username", "session__id")
    readonly_fields = ("created_at", "encrypted_results")

    fieldsets = (
        ("Основная информация", {"fields": ("user", "session", "analysis_type", "analysis_date")}),
        ("Зашифрованные данные", {"fields": ("encrypted_results",), "classes": ("collapse",)}),
        ("Дополнительно", {"fields": ("created_at",)}),
    )

    def has_structured_data(self, obj):
        has_general = hasattr(obj, "blood_general")
        has_biochem = hasattr(obj, "blood_biochem")
        has_hormones = hasattr(obj, "hormones")

        if has_general:
            return mark_safe('<span style="color: green;">✓ ОАК</span>')
        elif has_biochem:
            return mark_safe('<span style="color: green;">✓ Биохимия</span>')
        elif has_hormones:
            return mark_safe('<span style="color: green;">✓ Гормоны</span>')
        return mark_safe('<span style="color: gray;">-</span>')

    has_structured_data.short_description = "Структурированные данные"


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "ip_address", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("user__username", "action", "ip_address", "details")
    readonly_fields = ("user", "action", "details", "ip_address", "timestamp")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
