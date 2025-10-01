from django.core.management.base import BaseCommand

from medical_analysis.enums import AnalysisType
from medical_analysis.file_processor import OCRProcessor, MedicalDataParser
from medical_analysis.models import AnalysisSession
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Тестирование парсера медицинских данных"

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id",
            type=int,
            help="ID сессии для тестирования",
        )
        parser.add_argument(
            "--file-path",
            type=str,
            help="Прямой путь к файлу",
        )

    def handle(self, *args, **options):
        session_id = options.get("session_id")
        file_path = options.get("file_path")

        if not session_id and not file_path:
            self.stdout.write(self.style.ERROR("Укажите --session-id или --file-path"))
            return

        # Получаем путь к файлу
        if session_id:
            try:
                session = AnalysisSession.objects.get(id=session_id)
                file_path = session.temp_file_path
                self.stdout.write(f"Файл из сессии {session_id}: {file_path}")
            except AnalysisSession.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Сессия {session_id} не найдена"))
                return

        if not file_path or not Path(file_path).exists():
            self.stdout.write(self.style.ERROR(f"Файл не существует: {file_path}"))
            return

        # Извлекаем текст
        self.stdout.write(self.style.WARNING("\n=== ИЗВЛЕЧЕНИЕ ТЕКСТА ==="))
        ocr = OCRProcessor()

        try:
            text = ocr.process_file(file_path)
            self.stdout.write(self.style.SUCCESS(f"Извлечено {len(text)} символов"))

            # Показываем первые 1000 символов
            self.stdout.write(self.style.WARNING("\n=== НАЧАЛО ТЕКСТА ==="))
            self.stdout.write(text[:1000])

            # Определяем тип анализа
            parser = MedicalDataParser()
            analysis_type = parser.detect_analysis_type(text)
            self.stdout.write(self.style.SUCCESS(f"\n=== ТИП АНАЛИЗА: {analysis_type} ==="))

            # Парсим данные
            self.stdout.write(self.style.WARNING("\n=== ПАРСИНГ ДАННЫХ ==="))

            if analysis_type == AnalysisType.BLOOD_GENERAL:
                parsed_data = parser.parse_blood_general(text)
            elif analysis_type == AnalysisType.BLOOD_BIOCHEM:
                parsed_data = parser.parse_blood_biochem(text)
            elif analysis_type == AnalysisType.HORMONES:
                parsed_data = parser.parse_hormones(text)
            else:
                parsed_data = {}

            # Показываем результаты
            if parsed_data:
                self.stdout.write(self.style.SUCCESS(f"\nНайдено параметров: {len(parsed_data)}"))
                for key, value in parsed_data.items():
                    self.stdout.write(f"  • {key}: {value}")
            else:
                self.stdout.write(self.style.ERROR("Не удалось распознать параметры"))

                # Показываем что искали
                self.stdout.write(self.style.WARNING("\n=== ИСКАЛИ ПАТТЕРНЫ ==="))
                patterns = (
                    parser.blood_general_patterns if analysis_type == "blood_general" else parser.biochem_patterns
                )
                for param, pattern_list in list(patterns.items())[:5]:  # Первые 5
                    self.stdout.write(f"\n{param}:")
                    for p in pattern_list:
                        self.stdout.write(f"  - {p}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
            import traceback

            self.stdout.write(traceback.format_exc())
