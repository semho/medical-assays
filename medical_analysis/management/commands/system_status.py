from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from medical_analysis.models import AnalysisSession, MedicalData, SecurityLog
import os
import psutil


class Command(BaseCommand):
    help = "Проверка статуса системы"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("📊 Статус системы Medical MVP"))
        self.stdout.write("=" * 50)

        # Статистика базы данных
        self.show_database_stats()

        # Статистика файлов
        self.show_file_stats()

        # Производительность системы
        self.show_system_performance()

        # Статистика безопасности
        self.show_security_stats()

        # Проверка здоровья сервисов
        self.check_services_health()

    def show_database_stats(self):
        """Статистика базы данных"""
        self.stdout.write("\n📊 База данных:")

        total_users = AnalysisSession.objects.values("user").distinct().count()
        total_sessions = AnalysisSession.objects.count()
        completed_sessions = AnalysisSession.objects.filter(processing_status="completed").count()
        failed_sessions = AnalysisSession.objects.filter(processing_status="error").count()
        active_sessions = AnalysisSession.objects.filter(processing_status__in=["uploading", "processing"]).count()

        total_analyses = MedicalData.objects.count()

        self.stdout.write(f"  👥 Пользователей: {total_users}")
        self.stdout.write(f"  📋 Всего сессий: {total_sessions}")
        self.stdout.write(f"  ✅ Завершенных: {completed_sessions}")
        self.stdout.write(f"  ❌ Ошибок: {failed_sessions}")
        self.stdout.write(f"  ⏳ Активных: {active_sessions}")
        self.stdout.write(f"  🔬 Анализов: {total_analyses}")

        # Проверка подключения к БД
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write("  🟢 Подключение к БД: OK")
        except Exception as e:
            self.stdout.write(f"  🔴 Подключение к БД: ERROR - {e}")

    def show_file_stats(self):
        """Статистика файлов"""
        self.stdout.write("\n📁 Файловая система:")

        from django.conf import settings

        # Проверяем директории
        temp_dir = settings.TEMP_UPLOAD_DIR
        media_dir = settings.MEDIA_ROOT

        if os.path.exists(temp_dir):
            temp_files = len([f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))])
            self.stdout.write(f"  📂 Временных файлов: {temp_files}")
        else:
            self.stdout.write("  📂 Директория temp_uploads не найдена")

        if os.path.exists(media_dir):
            media_files = len([f for f in os.listdir(media_dir) if os.path.isfile(os.path.join(media_dir, f))])
            self.stdout.write(f"  🖼️  Медиа файлов: {media_files}")
        else:
            self.stdout.write("  🖼️  Директория media не найдена")

        # Проверяем файлы, которые должны быть удалены
        orphaned_sessions = AnalysisSession.objects.filter(
            temp_file_path__isnull=False,
            temp_file_path__gt="",
            file_deleted_timestamp__isnull=True,
            upload_timestamp__lt=timezone.now() - timezone.timedelta(minutes=2),
        ).count()

        if orphaned_sessions > 0:
            self.stdout.write(f"  ⚠️  Потерянных файлов: {orphaned_sessions}")
        else:
            self.stdout.write("  🟢 Потерянных файлов: 0")

    def show_system_performance(self):
        """Производительность системы"""
        self.stdout.write("\n⚡ Производительность:")

        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self.stdout.write(f"  🖥️  CPU: {cpu_percent}%")

            # Память
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            self.stdout.write(f"  💾 RAM: {memory_percent}% ({memory_used:.1f}/{memory_total:.1f} GB)")

            # Диск
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB
            self.stdout.write(f"  💿 Диск: {disk_percent}% (свободно: {disk_free:.1f} GB)")

        except ImportError:
            self.stdout.write("  ⚠️  psutil не установлен, статистика недоступна")
        except Exception as e:
            self.stdout.write(f"  ❌ Ошибка получения статистики: {e}")

    def show_security_stats(self):
        """Статистика безопасности"""
        self.stdout.write("\n🔒 Безопасность:")

        # Логи за последние 24 часа
        recent_logs = SecurityLog.objects.filter(timestamp__gte=timezone.now() - timezone.timedelta(hours=24))

        total_recent_logs = recent_logs.count()
        failed_logins = recent_logs.filter(action="USER_LOGIN_FAILED").count()
        file_accesses = recent_logs.filter(action="DATA_ACCESS").count()
        file_uploads = recent_logs.filter(action="FILE_UPLOADED").count()

        self.stdout.write(f"  📝 Событий за 24ч: {total_recent_logs}")
        self.stdout.write(f"  🔑 Неудачных входов: {failed_logins}")
        self.stdout.write(f"  📊 Доступов к данным: {file_accesses}")
        self.stdout.write(f"  📤 Загрузок файлов: {file_uploads}")

        # Проверяем подозрительную активность
        if failed_logins > 10:
            self.stdout.write("  🚨 ВНИМАНИЕ: Высокое количество неудачных входов!")

        # Файлы, которые не были удалены
        undeleted_files = AnalysisSession.objects.filter(
            temp_file_path__isnull=False, temp_file_path__gt="", file_deleted_timestamp__isnull=True
        ).count()

        if undeleted_files == 0:
            self.stdout.write("  🟢 Все файлы удалены согласно политике")
        else:
            self.stdout.write(f"  ⚠️  Неудаленных файлов: {undeleted_files}")

    def check_services_health(self):
        """Проверка здоровья сервисов"""
        self.stdout.write("\n🏥 Здоровье сервисов:")

        # Проверка Redis
        try:
            from django_redis import get_redis_connection

            redis_conn = get_redis_connection("default")
            redis_conn.ping()
            self.stdout.write("  🟢 Redis: OK")
        except Exception as e:
            self.stdout.write(f"  🔴 Redis: ERROR - {e}")

        # Проверка Celery через RabbitMQ
        try:
            from celery import Celery
            from medical_mvp.settings import CELERY_BROKER_URL

            temp_app = Celery()
            temp_app.conf.broker_url = CELERY_BROKER_URL
            temp_app.conf.broker_connection_timeout = 2

            inspect = temp_app.control.inspect(timeout=2)
            stats = inspect.stats()

            if stats:
                active_workers = len(stats)
                self.stdout.write(f"  🟢 Celery: OK ({active_workers} workers)")
            else:
                self.stdout.write("  🔴 Celery: No active workers")
        except Exception as e:
            self.stdout.write(f"  🔴 Celery: ERROR - {str(e)}")

        # Проверка Tesseract
        try:
            import subprocess

            result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.split("\n")[0]
                self.stdout.write(f"  🟢 Tesseract: OK ({version})")
            else:
                self.stdout.write("  🔴 Tesseract: ERROR")
        except Exception as e:
            self.stdout.write(f"  🔴 Tesseract: ERROR - {e}")
