from django.core.management import BaseCommand
from django.contrib.auth.models import User
from pathlib import Path
from medical_analysis.models import UserProfile, SecurityLog


class Command(BaseCommand):
    help = "Настройка начальных данных для приложения"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-admin",
            action="store_true",
            help="Создать администратора",
        )
        parser.add_argument(
            "--admin-username",
            type=str,
            default="admin",
            help="Имя пользователя администратора",
        )
        parser.add_argument(
            "--admin-password",
            type=str,
            default="admin123",
            help="Пароль администратора",
        )
        parser.add_argument(
            "--admin-email",
            type=str,
            default="admin@example.com",
            help="Email администратора",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Настройка Medical MVP..."))

        # Создание администратора
        if options["create_admin"]:
            self.create_admin_user(options["admin_username"], options["admin_password"], options["admin_email"])

        # Проверка директорий
        self.check_directories()

        # Создание начальных логов
        self.create_initial_logs()

        self.stdout.write(self.style.SUCCESS("✅ Настройка завершена успешно!"))

    def create_admin_user(self, username, password, email):
        """Создание администратора"""
        try:
            if not User.objects.filter(username=username).exists():
                admin_user = User.objects.create_superuser(username=username, email=email, password=password)

                # Создаем профиль
                UserProfile.objects.get_or_create(user=admin_user, defaults={"language_preference": "ru"})

                self.stdout.write(self.style.SUCCESS(f"👤 Администратор создан: {username}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️  Администратор {username} уже существует"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка создания администратора: {e}"))

    def check_directories(self):
        """Проверка необходимых директорий"""
        from django.conf import settings

        directories = [
            Path(settings.MEDIA_ROOT),
            Path(settings.TEMP_UPLOAD_DIR),
            Path(settings.BASE_DIR) / "logs",
        ]

        for path in directories:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f"📁 Создана директория: {path}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ Директория существует: {path}"))

    def create_initial_logs(self):
        """Создание начальных записей в логах"""
        SecurityLog.objects.create(
            action="SYSTEM_INIT", details="Система Medical MVP инициализирована", ip_address=None
        )

        self.stdout.write(self.style.SUCCESS("📝 Начальные логи созданы"))
