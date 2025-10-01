from django.apps import AppConfig


class MedicalAnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "medical_analysis"

    def ready(self):
        import medical_analysis.signals
