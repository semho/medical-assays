from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from medical_analysis.models import AnalysisSession, SecurityLog
from medical_analysis.file_processor import DataRetentionManager


class Command(BaseCommand):
    help = "Очистка данных системы"

    def add_arguments(self, parser):
        parser.add_argument(
            "--expired-files",
            action="store_true",
            help="Очистить просроченные файлы",
        )
        parser.add_argument(
            "--old-logs",
            action="store_true",
            help="Очистить старые логи (старше 90 дней)",
        )
        parser.add_argument(
            "--failed-sessions",
            action="store_true",
            help="Очистить неудачные сессии",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Выполнить всю очистку",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Количество дней для хранения данных",
        )

    def handle(self, *args, **options):
        if options["all"]:
            options["expired_files"] = True
            options["old_logs"] = True
            options["failed_sessions"] = True

        if options["expired_files"]:
            self.cleanup_expired_files()

        if options["old_logs"]:
            self.cleanup_old_logs(options["days"])

        if options["failed_sessions"]:
            self.cleanup_failed_sessions()

        self.stdout.write(self.style.SUCCESS("✅ Очистка завершена"))

    def cleanup_expired_files(self):
        """Очистка просроченных файлов"""
        self.stdout.write("🧹 Очистка просроченных файлов...")

        try:
            DataRetentionManager.cleanup_expired_sessions()
            DataRetentionManager.verify_file_deletion()

            self.stdout.write(self.style.SUCCESS("✅ Просроченные файлы очищены"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка очистки файлов: {e}"))

    def cleanup_old_logs(self, days):
        """Очистка старых логов"""
        self.stdout.write(f"🧹 Очистка логов старше {days} дней...")

        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            deleted_count = SecurityLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]

            self.stdout.write(self.style.SUCCESS(f"✅ Удалено {deleted_count} записей логов"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка очистки логов: {e}"))

    def cleanup_failed_sessions(self):
        """Очистка неудачных сессий"""
        self.stdout.write("🧹 Очистка неудачных сессий...")

        try:
            # Удаляем сессии с ошибками старше 7 дней
            cutoff_date = timezone.now() - timedelta(days=7)
            failed_sessions = AnalysisSession.objects.filter(
                processing_status="error", upload_timestamp__lt=cutoff_date
            )

            deleted_count = failed_sessions.count()
            failed_sessions.delete()

            self.stdout.write(self.style.SUCCESS(f"✅ Удалено {deleted_count} неудачных сессий"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка очистки сессий: {e}"))
