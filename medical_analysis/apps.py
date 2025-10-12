import logging
import sys

from django.apps import AppConfig
logger = logging.getLogger(__name__)

class MedicalAnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "medical_analysis"

    def ready(self):
        """initialize OCR engine on startup"""
        import medical_analysis.signals

        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations']):
            return

        try:
            logger.info("warming up OCR engine...")
            from medical_analysis.ocr_service import get_ocr_service
            get_ocr_service()
            logger.info("OCR engine ready")
        except Exception as e:
            logger.warning(f"OCR warm-up failed: {e}")
