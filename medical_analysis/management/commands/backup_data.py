from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from medical_analysis.models import UserProfile, MedicalData, AnalysisSession
import json
import os
from datetime import datetime


class Command(BaseCommand):
    help = "Создание резервной копии данных"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default="./backups",
            help="Директория для сохранения бэкапа",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="ID конкретного пользователя для бэкапа",
        )
        parser.add_argument(
            "--include-raw-data",
            action="store_true",
            help="Включить сырые данные анализов",
        )

    def handle(self, *args, **options):
        output_dir = options["output_dir"]
        user_id = options.get("user_id")
        include_raw = options["include_raw_data"]

        # Создаем директорию
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if user_id:
            self.backup_user_data(user_id, output_dir, timestamp, include_raw)
        else:
            self.backup_all_data(output_dir, timestamp, include_raw)

        self.stdout.write(self.style.SUCCESS(f"✅ Бэкап завершен в {output_dir}"))

    def backup_user_data(self, user_id, output_dir, timestamp, include_raw):
        """Бэкап данных конкретного пользователя"""
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f"📦 Создание бэкапа для пользователя {user.username}...")

            backup_data = {
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "date_joined": user.date_joined.isoformat(),
                },
                "profile": {},
                "medical_data": [],
                "created_at": datetime.now().isoformat(),
            }

            # Профиль
            try:
                profile = user.profile
                backup_data["profile"] = {
                    "language_preference": profile.language_preference,
                    "created_at": profile.created_at.isoformat(),
                }
            except UserProfile.DoesNotExist:
                pass

            # Медицинские данные
            medical_data = MedicalData.objects.filter(user=user)
            for data in medical_data:
                decrypted = data.decrypt_data() if include_raw else None

                item = {
                    "analysis_date": data.analysis_date.isoformat(),
                    "analysis_type": data.analysis_type,
                    "created_at": data.created_at.isoformat(),
                }

                if decrypted and include_raw:
                    item["parsed_data"] = decrypted.get("parsed_data", {})

                backup_data["medical_data"].append(item)

            # Сохраняем в файл
            filename = f"user_{user_id}_backup_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            self.stdout.write(f"✅ Бэкап сохранен: {filename}")

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Пользователь с ID {user_id} не найден"))

    def backup_all_data(self, output_dir, timestamp, include_raw):
        """Полный бэкап всех данных"""
        self.stdout.write("📦 Создание полного бэкапа...")

        # Статистика
        stats = {
            "total_users": User.objects.count(),
            "total_analyses": MedicalData.objects.count(),
            "total_sessions": AnalysisSession.objects.count(),
            "backup_created": datetime.now().isoformat(),
        }

        # Сохраняем статистику
        stats_filename = f"backup_stats_{timestamp}.json"
        stats_filepath = os.path.join(output_dir, stats_filename)

        with open(stats_filepath, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        self.stdout.write(f"✅ Статистика сохранена: {stats_filename}")

        # Создаем бэкапы для каждого пользователя
        for user in User.objects.all():
            self.backup_user_data(user.id, output_dir, timestamp, include_raw)

        self.stdout.write(f"✅ Создано {User.objects.count()} пользовательских бэкапов")
