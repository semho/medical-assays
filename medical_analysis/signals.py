from pathlib import Path

from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from medical_analysis.enums import Status
from medical_analysis.models import MedicalData, AnalysisSession, SecurityLog
import logging

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=MedicalData)
def delete_related_session(sender, instance, **kwargs):
    """Удаление связанной сессии при удалении MedicalData, если она не нужна"""
    session = instance.session
    if session:
        # Проверяем, есть ли другие MedicalData, связанные с этой сессией
        other_medical_data = MedicalData.objects.filter(session=session).exclude(id=instance.id).exists()
        if not other_medical_data and session.processing_status in [Status.COMPLETED, Status.ERROR]:
            session_id = session.id
            # Устанавливаем file_deleted_timestamp, если файл ещё существует
            if session.temp_file_path and Path(session.temp_file_path).exists():
                Path(session.temp_file_path).unlink()
                session.file_deleted_timestamp = timezone.now()
                session.save()
                logger.info(f"Удалён файл для сессии {session_id} перед удалением")

            # Удаляем сессию
            session.delete()
            logger.info(f"Удалена сессия {session_id} при удалении анализа {instance.id}")

            # Логируем в SecurityLog
            SecurityLog.objects.create(
                user=instance.user,
                action="SESSION_DELETED",
                details=f"Удалена сессия {session_id} при удалении анализа {instance.id}",
                ip_address=None,  # Можно передать IP, если доступен
            )
