from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
from .models import AnalysisSession, SecurityLog
from .file_processor import DataRetentionManager
from pathlib import Path

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")


@shared_task(queue="default")
def cleanup_expired_files():
    """Очистка просроченных файлов"""
    try:
        DataRetentionManager.cleanup_expired_sessions()
        logger.info("Очистка просроченных файлов выполнена")
        return "Очистка выполнена успешно"
    except Exception as e:
        logger.error(f"Ошибка очистки файлов: {e}")
        return f"Ошибка: {str(e)}"


@shared_task(queue="default")
def verify_file_deletion():
    """Проверка удаления файлов"""
    try:
        DataRetentionManager.verify_file_deletion()
        logger.info("Проверка удаления файлов выполнена")
        return "Проверка выполнена успешно"
    except Exception as e:
        logger.error(f"Ошибка проверки удаления файлов: {e}")
        return f"Ошибка: {str(e)}"


@shared_task(queue="default")
def cleanup_old_security_logs():
    """Очистка старых логов безопасности (старше 90 дней)"""
    try:
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_count = SecurityLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]

        logger.info(f"Удалено {deleted_count} старых записей логов безопасности")

        # Логируем действие
        SecurityLog.objects.create(
            action="LOG_CLEANUP", details=f"Удалено {deleted_count} старых записей логов", ip_address=None
        )

        return f"Удалено {deleted_count} записей"
    except Exception as e:
        logger.error(f"Ошибка очистки логов: {e}")
        return f"Ошибка: {str(e)}"


@shared_task(queue="default")
def system_health_check():
    """Проверка состояния системы"""
    try:
        health_data = {
            "timestamp": timezone.now(),
            "active_sessions": AnalysisSession.objects.filter(
                processing_status__in=["uploading", "processing"]
            ).count(),
            "completed_today": AnalysisSession.objects.filter(processing_completed__date=timezone.now().date()).count(),
            "error_sessions": AnalysisSession.objects.filter(
                processing_status="error", upload_timestamp__gte=timezone.now() - timedelta(hours=24)
            ).count(),
        }

        # Проверяем наличие файлов, которые должны быть удалены
        orphaned_sessions = AnalysisSession.objects.filter(
            temp_file_path__isnull=False,
            temp_file_path__gt="",
            file_deleted_timestamp__isnull=True,
            upload_timestamp__lt=timezone.now() - timedelta(minutes=2),
        )

        health_data["orphaned_files"] = orphaned_sessions.count()

        # Если есть потерянные файлы, принудительно удаляем их
        for session in orphaned_sessions:
            path = Path(session.temp_file_path)
            if path.exists():
                try:
                    path.unlink()
                    session.temp_file_path = ""
                    session.file_deleted_timestamp = timezone.now()
                    session.save()

                    SecurityLog.objects.create(
                        user=session.user,
                        action="ORPHANED_FILE_CLEANUP",
                        details=f"Удален потерянный файл сессии {session.pk}",
                        ip_address=None,
                    )
                except Exception as e:
                    logger.error(f"Ошибка удаления потерянного файла {session.temp_file_path}: {e}")

        logger.info(f"Проверка системы: {health_data}")

        # Логируем в систему безопасности, если есть проблемы
        if health_data["error_sessions"] > 10:
            SecurityLog.objects.create(
                action="HIGH_ERROR_RATE",
                details=f"Высокий уровень ошибок: {health_data['error_sessions']} за 24 часа",
                ip_address=None,
            )

        return health_data

    except Exception as e:
        logger.error(f"Ошибка проверки системы: {e}")
        return f"Ошибка: {str(e)}"


@shared_task(queue="default")
def send_processing_notification(user_id, session_id, status):
    """Отправка уведомления о статусе обработки"""
    try:
        from django.contrib.auth.models import User
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        user = User.objects.get(id=user_id)
        session = AnalysisSession.objects.get(id=session_id)

        # Отправляем WebSocket уведомление
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "processing_update",
                    "message": {
                        "session_id": session_id,
                        "status": status,
                        "filename": session.original_filename,
                        "timestamp": timezone.now().isoformat(),
                    },
                },
            )

        logger.info(f"Уведомление отправлено пользователю {user_id} о статусе {status}")
        return "Уведомление отправлено"

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")
        return f"Ошибка: {str(e)}"


@shared_task(queue="default")
def generate_user_report(user_id, report_type="monthly"):
    """Генерация отчета для пользователя"""
    try:
        from django.contrib.auth.models import User
        from .models import MedicalData

        user = User.objects.get(id=user_id)

        # Определяем период
        if report_type == "monthly":
            start_date = timezone.now() - timedelta(days=30)
        elif report_type == "weekly":
            start_date = timezone.now() - timedelta(days=7)
        else:
            start_date = timezone.now() - timedelta(days=365)

        # Получаем данные пользователя
        medical_data = MedicalData.objects.filter(user=user, created_at__gte=start_date).order_by("analysis_date")

        report_data = {
            "user_id": user_id,
            "period": report_type,
            "total_analyses": medical_data.count(),
            "analysis_types": {},
            "trends": [],
            "generated_at": timezone.now().isoformat(),
        }

        # Анализируем типы анализов
        for data in medical_data:
            analysis_type = data.analysis_type
            if analysis_type not in report_data["analysis_types"]:
                report_data["analysis_types"][analysis_type] = 0
            report_data["analysis_types"][analysis_type] += 1

        logger.info(f"Отчет {report_type} создан для пользователя {user_id}")

        # Здесь можно добавить отправку отчета по email
        # send_report_email.delay(user_id, report_data)

        return report_data

    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        return f"Ошибка: {str(e)}"
