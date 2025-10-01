from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from medical_analysis.models import UserProfile, MedicalData, AnalysisSession
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = "Генерация тестовых данных"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=5,
            help="Количество тестовых пользователей",
        )
        parser.add_argument(
            "--analyses-per-user",
            type=int,
            default=10,
            help="Количество анализов на пользователя",
        )

    def handle(self, *args, **options):
        self.stdout.write("🧪 Генерация тестовых данных...")

        users_count = options["users"]
        analyses_count = options["analyses_per_user"]

        # Создаем тестовых пользователей
        test_users = []
        for i in range(users_count):
            username = f"testuser{i + 1}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f"test{i + 1}@example.com",
                    password="testpass123",
                    first_name=f"Тест{i + 1}",
                    last_name="Пользователь",
                )

                UserProfile.objects.create(user=user, language_preference="ru")

                test_users.append(user)
                self.stdout.write(f"👤 Создан пользователь: {username}")

        # Создаем тестовые анализы
        for user in test_users:
            for j in range(analyses_count):
                # Случайная дата в последние 6 месяцев
                days_ago = random.randint(1, 180)
                analysis_date = timezone.now().date() - timedelta(days=days_ago)

                # Создаем сессию
                session = AnalysisSession.objects.create(
                    user=user,
                    original_filename=f"test_analysis_{j + 1}.pdf",
                    processing_status="completed",
                    analysis_type=random.choice(["blood_general", "blood_biochem"]),
                    upload_timestamp=timezone.now() - timedelta(days=days_ago),
                    processing_completed=timezone.now() - timedelta(days=days_ago),
                    file_deleted_timestamp=timezone.now() - timedelta(days=days_ago),
                )

                # Создаем медицинские данные
                medical_data = MedicalData.objects.create(
                    user=user, session=session, analysis_type=session.analysis_type, analysis_date=analysis_date
                )

                # Генерируем тестовые данные анализов
                if session.analysis_type == "blood_general":
                    test_data = self.generate_blood_general_data()
                else:
                    test_data = self.generate_blood_biochem_data()

                medical_data.encrypt_data({"parsed_data": test_data})
                medical_data.save()

        self.stdout.write(
            self.style.SUCCESS(f"✅ Создано {len(test_users)} пользователей с {analyses_count} анализами каждый")
        )

    def generate_blood_general_data(self):
        """Генерация данных общего анализа крови"""
        return {
            "hemoglobin": round(random.uniform(120, 160), 1),
            "erythrocytes": round(random.uniform(4.0, 5.5), 2),
            "leukocytes": round(random.uniform(4.0, 9.0), 1),
            "platelets": random.randint(150, 400),
            "esr": random.randint(2, 15),
            "neutrophils_seg": round(random.uniform(47, 72), 1),
            "lymphocytes": round(random.uniform(19, 37), 1),
            "monocytes": round(random.uniform(3, 11), 1),
            "eosinophils": round(random.uniform(0.5, 5), 1),
        }

    def generate_blood_biochem_data(self):
        """Генерация данных биохимического анализа"""
        return {
            "glucose": round(random.uniform(3.3, 5.5), 1),
            "total_protein": round(random.uniform(66, 87), 1),
            "albumin": round(random.uniform(35, 52), 1),
            "urea": round(random.uniform(2.5, 8.3), 1),
            "creatinine": random.randint(62, 115),
            "total_bilirubin": round(random.uniform(5, 21), 1),
            "alt": random.randint(10, 45),
            "ast": random.randint(10, 35),
            "total_cholesterol": round(random.uniform(3.0, 5.2), 1),
            "hdl_cholesterol": round(random.uniform(1.0, 2.2), 1),
            "triglycerides": round(random.uniform(0.4, 1.8), 1),
        }
