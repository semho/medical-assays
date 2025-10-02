import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import re
from django.conf import settings
from django.utils import timezone

from .constants.keywords_analysis import BLOOD, BIOCHEM, HORMONES
from .constants.paraneter_parser import BLOOD_PARSER, BIOCHEM_PARSER, BLOOD_LEUKO_PARAMS, HORMONES_PARSER, RANGES_PARSER
from .enums import AnalysisType, Status
from .gpt_parser import GPTMedicalParser, format_gpt_result
from .models import AnalysisSession, MedicalData, SecurityLog
from celery import shared_task

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")


class SecureFileProcessor:
    """Безопасный процессор файлов с автоудалением"""

    def __init__(self):
        self.temp_dir = Path(settings.TEMP_UPLOAD_DIR)
        self.temp_dir.mkdir(exist_ok=True)

    def save_temp_file(self, uploaded_file, session: AnalysisSession) -> str:
        """Сохранить файл во временную папку"""
        try:
            # Генерируем безопасное имя файла
            timestamp = int(datetime.now().timestamp())
            safe_filename = f"{session.pk}_{timestamp}_{uploaded_file.name}"
            temp_path = self.temp_dir / safe_filename

            # Сохраняем файл
            with Path.open(temp_path, "wb") as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)

            # Обновляем сессию
            session.temp_file_path = str(temp_path)
            session.processing_status = "processing"
            session.processing_started = timezone.now()
            session.save()

            # Планируем автоудаление
            schedule_file_deletion.s(str(temp_path), session.pk).apply_async()

            security_logger.info(f"Файл сохранен: {safe_filename}, пользователь: {session.user.username}")
            return str(temp_path)

        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            session.processing_status = "error"
            session.error_message = f"Ошибка сохранения файла: {e}"
            session.save()
            raise


class OCRProcessor:
    """Процессор для распознавания текста из медицинских документов"""

    def __init__(self):
        if hasattr(settings, "TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Извлечение текста из PDF"""
        try:
            text = ""
            doc = fitz.open(file_path)  # type: ignore[attr-defined]

            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text()

                # Если текста мало, пробуем OCR на изображении страницы
                if len(text.strip()) < 100:
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")

                    # Сохраняем во временный файл для OCR
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
                        temp_img.write(img_data)
                        temp_img_path = temp_img.name

                    try:
                        ocr_text = self.extract_text_from_image(temp_img_path)
                        text += ocr_text
                    finally:
                        Path(temp_img_path).unlink(missing_ok=True)

            doc.close()
            return text

        except Exception as e:
            logger.error(f"Ошибка извлечения текста из PDF: {e}")
            raise

    def extract_text_from_image(self, file_path: str) -> str:
        """Извлечение текста из изображения"""
        try:
            image = Image.open(file_path)

            # Конфигурация для медицинских документов
            custom_config = r"--oem 3 --psm 6 -l rus+eng"

            text = pytesseract.image_to_string(image, config=custom_config)
            return text

        except Exception as e:
            logger.error(f"Ошибка OCR изображения: {e}")
            raise

    def process_file(self, file_path: str) -> str:
        """Основной метод обработки файла"""
        file_extension = Path(file_path).suffix.lower()

        if file_extension == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif file_extension in [".jpg", ".jpeg", ".png", ".tiff"]:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Неподдерживаемый тип файла: {file_extension}")


class MedicalDataParser:
    """Парсер для извлечения структурированных данных из текста анализов"""

    def __init__(self):
        self.blood_general_patterns = {
            "hemoglobin": [
                r"гемоглобин.*?(\d+[\.,]\d+|\d+)",
                r"hb.*?(\d+[\.,]\d+|\d+)",
                r"hemoglobin.*?(\d+[\.,]\d+|\d+)",
            ],
            "erythrocytes": [r"эритроциты.*?(\d+[\.,]\d+)", r"rbc.*?(\d+[\.,]\d+)", r"red blood cells.*?(\d+[\.,]\d+)"],
            "leukocytes": [r"лейкоциты.*?(\d+[\.,]\d+)", r"wbc.*?(\d+[\.,]\d+)", r"white blood cells.*?(\d+[\.,]\d+)"],
            "platelets": [r"тромбоциты.*?(\d+)", r"plt.*?(\d+)", r"platelets.*?(\d+)"],
            "esr": [r"соэ.*?(\d+)", r"esr.*?(\d+)", r"sed rate.*?(\d+)"],
        }

        self.biochem_patterns = {
            "glucose": [r"глюкоза.*?(\d+[\.,]\d+)", r"glucose.*?(\d+[\.,]\d+)"],
            "total_protein": [r"общий белок.*?(\d+[\.,]?\d*)", r"total protein.*?(\d+[\.,]?\d*)"],
            "creatinine": [r"креатинин.*?(\d+[\.,]?\d*)", r"creatinine.*?(\d+[\.,]?\d*)"],
            "urea": [r"мочевина.*?(\d+[\.,]?\d*)", r"urea.*?(\d+[\.,]?\d*)"],
        }

    def parse_hormones(self, text: str) -> dict[str, float]:
        results = {}
        lines = text.split("\n")

        params_map = HORMONES_PARSER

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            for param_key, keywords in params_map.items():
                if any(keyword in line_lower for keyword in keywords):
                    for offset in range(1, 4):  # Проверяем следующие строки
                        if i + offset >= len(lines):
                            break
                        check_line = lines[i + offset].strip()
                        match = re.search(r"(\d+[\.,]\d+|\d+)\*?", check_line)
                        if match:
                            try:
                                value = float(match.group(1).replace(",", "."))
                                if self._validate_value(param_key, value):  # Расширь _validate_value для гормонов
                                    results[param_key] = value
                                    logger.info(f"Найден {param_key}: {value}")
                                    break
                            except ValueError:
                                continue
                    break

        return results

    def parse_blood_general(self, text: str) -> dict[str, float]:
        """Парсинг ОАК с учетом табличной структуры"""
        results = {}
        lines = text.split("\n")

        # Границы секции ОАК
        start_idx = 0
        end_idx = len(lines)

        for i, line in enumerate(lines):
            if "общий анализ крови" in line.lower() or "cbc" in line.lower():
                start_idx = i
            if "биохимические исследования" in line.lower() or "гормональные" in line.lower():
                end_idx = i
                break

        params_map = BLOOD_PARSER
        leuko_params = BLOOD_LEUKO_PARAMS

        for i in range(start_idx, end_idx):
            if i >= len(lines):
                break

            line_lower = lines[i].lower().strip()

            for param_key, keywords in params_map.items():
                if param_key in results:
                    continue

                # Для лейкоформулы ЯВНО ищем строку с %, а не абсолютное
                if param_key in leuko_params:
                    # Ищем строку типа "Нейтрофилы (Ne), %"
                    if any(keyword in line_lower for keyword in keywords) and "%" in line_lower:
                        for offset in range(1, 4):
                            if i + offset >= len(lines):
                                break

                            check_line = lines[i + offset].strip()
                            match = re.search(r"(\d+[\.,]\d+|\d+)\*?", check_line)

                            if match:
                                try:
                                    value = float(match.group(1).replace(",", "."))
                                    if 0 <= value <= 100:
                                        results[param_key] = value
                                        logger.info(f"Найден {param_key}: {value}%")
                                        break
                                except ValueError:
                                    continue
                        break
                else:
                    # Для остальных параметров - обычный поиск
                    if any(keyword in line_lower for keyword in keywords):
                        for offset in range(1, 4):
                            if i + offset >= len(lines):
                                break

                            check_line = lines[i + offset].strip()
                            match = re.search(r"(\d+[\.,]\d+|\d+)\*?", check_line)

                            if match:
                                try:
                                    value = float(match.group(1).replace(",", "."))
                                    if self._validate_value(param_key, value):
                                        results[param_key] = value
                                        logger.info(f"Найден {param_key}: {value}")
                                        break
                                except ValueError:
                                    continue
                        break

        return results

    def _validate_value(self, param: str, value: float) -> bool:
        """Валидация разумности значения"""
        ranges = RANGES_PARSER

        if param in ranges:
            min_val, max_val = ranges[param]
            return min_val <= value <= max_val

        return True

    def parse_blood_biochem(self, text: str) -> dict[str, float]:
        """Парсинг биохимии с учетом табличной структуры"""
        results = {}
        lines = text.split("\n")

        params_map = BIOCHEM_PARSER

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            for param_key, keywords in params_map.items():
                if any(keyword in line_lower for keyword in keywords):
                    for offset in range(1, 4):  # Проверяем следующие строки
                        if i + offset >= len(lines):
                            break
                        check_line = lines[i + offset].strip()
                        match = re.search(r"(\d+[\.,]\d+|\d+|\d+\.\d+)\*?", check_line)
                        if match:
                            try:
                                value = float(match.group(1).replace(",", "."))
                                if self._validate_value(param_key, value):
                                    # Проверяем, не встречался ли параметр ранее
                                    if param_key not in results:
                                        results[param_key] = {
                                            "value": value,
                                            "unit": self._get_unit(param_key, lines[i : i + offset + 1]),
                                            "reference": self._get_reference(lines[i : i + offset + 1]),
                                            "status": self._determine_status(lines[i : i + offset + 1], value),
                                        }
                                        logger.info(f"Найден {param_key}: {value}")
                                break
                            except ValueError:
                                continue
                    break

        return results

    def _get_unit(self, param_key: str, lines: list[str]) -> str:
        """Извлечение единицы измерения"""
        unit_patterns = {
            "glucose": r"ммоль/л",
            "urea": r"ммоль/л",
            "creatinine": r"мкмоль/л",
            "bilirubin_total": r"мкмоль/л",
            "alt": r"ед/л",
            "ast": r"ед/л",
            "atherogenic_index": r"< \d+\.\d+",  # Для индекса атерогенности
            "gfr_ckd_epi": r"мл/мин/1,73м\^2",
        }
        for line in lines:
            for key, pattern in unit_patterns.items():
                if key == param_key:
                    match = re.search(pattern, line.lower())
                    if match:
                        return match.group(0)
        return ""

    def _get_reference(self, lines: list[str]) -> str:
        """Извлечение референсного диапазона"""
        for line in lines:
            match = re.search(r"(\d+\.\d+ - \d+\.\d+|\d+\.\d+)", line)
            if match:
                return match.group(0)
        return ""

    def _determine_status(self, lines: list[str], value: float) -> str:
        """Определение статуса (норма/повышен/понижен)"""
        for line in lines:
            if "*" in line:
                # Извлечь референсный диапазон
                match = re.search(r"(\d+\.\d+)-(\d+\.\d+)", line)
                if match:
                    low, high = float(match.group(1)), float(match.group(2))
                    return "понижен" if value < low else "повышен"
            match = re.search(r"(\d+\.\d+)-(\d+\.\д+)", line)
            if match:
                low, high = float(match.group(1)), float(match.group(2))
                if low <= value <= high:
                    return "норма"
        return "неизвестно"

    def detect_analysis_type(self, text: str) -> str:
        """Определение типа анализа по содержимому"""
        text_lower = text.lower()

        # Ключевые слова для разных типов анализов
        blood_general_keywords = BLOOD
        biochem_keywords = BIOCHEM
        hormones_keywords = HORMONES

        blood_general_score = sum(1 for keyword in blood_general_keywords if keyword in text_lower)
        biochem_score = sum(1 for keyword in biochem_keywords if keyword in text_lower)
        hormones_score = sum(1 for keyword in hormones_keywords if keyword in text_lower)

        if hormones_score > max(blood_general_score, biochem_score):
            return AnalysisType.HORMONES
        elif blood_general_score > biochem_score:
            return AnalysisType.BLOOD_GENERAL
        elif biochem_score > 0:
            return AnalysisType.BLOOD_BIOCHEM
        else:
            return "unknown"


class FileUploadHandler:
    """Обработчик загрузки файлов с проверками безопасности"""

    def __init__(self):
        self.file_processor = SecureFileProcessor()
        self.max_file_size = settings.FILE_UPLOAD_MAX_MEMORY_SIZE
        self.allowed_extensions = settings.ALLOWED_FILE_EXTENSIONS

    def validate_file(self, uploaded_file) -> bool:
        """Валидация загружаемого файла"""
        # Проверка размера
        if uploaded_file.size > self.max_file_size:
            raise ValueError(f"Файл слишком большой. Максимальный размер: {self.max_file_size // (1024 * 1024)} МБ")

        # Проверка расширения
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise ValueError(f"Неподдерживаемый тип файла: {file_extension}")

        # Проверка MIME типа
        allowed_mime_types = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]

        if getattr(uploaded_file, "content_type", None) and uploaded_file.content_type not in allowed_mime_types:
            raise ValueError(f"Неподдерживаемый MIME тип: {uploaded_file.content_type}")

        return True

    def handle_upload(self, uploaded_file, user) -> AnalysisSession:
        """Основной метод обработки загрузки"""
        try:
            # Валидируем файл
            self.validate_file(uploaded_file)

            # Создаем сессию
            session = AnalysisSession.objects.create(
                user=user, original_filename=uploaded_file.name, processing_status="uploading"
            )

            # Сохраняем файл во временную папку
            temp_path = self.file_processor.save_temp_file(uploaded_file, session)

            # Запускаем асинхронную обработку
            process_medical_file.s(session.pk).apply_async()

            # Логируем загрузку
            SecurityLog.objects.create(
                user=user,
                action="FILE_UPLOADED",
                details=f"Загружен файл: {uploaded_file.name}, размер: {uploaded_file.size} байт",
                ip_address=None,
            )

            return session

        except Exception as e:
            logger.error(f"Ошибка загрузки файла {uploaded_file.name}: {e}")
            raise


class DataRetentionManager:
    """Менеджер для управления жизненным циклом данных"""

    @staticmethod
    def cleanup_expired_sessions():
        """Очистка просроченных сессий и удаление завершенных"""
        from django.utils import timezone

        # 1. Удаляем файлы старше 5 минут без завершенной обработки, они не представляют ценности.
        expired_time = timezone.now() - timedelta(minutes=5)
        expired_sessions = AnalysisSession.objects.filter(
            processing_started__lt=expired_time, processing_status__in=[Status.UPLOADING, Status.PROCESSING]
        )

        for session in expired_sessions:
            path = Path(session.temp_file_path)
            if session.temp_file_path and path.exists():
                try:
                    path.unlink()
                    SecurityLog.objects.create(
                        user=session.user,
                        action="FILE_CLEANUP",
                        details=f"Удален просроченный файл сессии {session.pk}",
                        ip_address=None,
                    )
                except Exception as e:
                    logger.error(f"Ошибка очистки файла сессии {session.pk}: {e}")

            # Удаляем саму сессию
            session.delete()

        # 2. Удаляем ошибочные сессии старше 1 часа
        # TODO: тут для прода сделать 7-30 дней, т.к. для медицины служат доказательной базой(аудита, compliance с GDPR или 152-ФЗ)
        old_completed = AnalysisSession.objects.filter(
            processing_completed__lt=timezone.now() - timedelta(hours=1), processing_status=Status.ERROR
        )
        count_errors = old_completed.count()
        old_completed.delete()

        logger.info(f"Очистка: удалено {expired_sessions.count()} просроченных, {count_errors} ошибочных сессий")

    @staticmethod
    def verify_file_deletion():
        """Проверка, что все файлы действительно удалены"""
        sessions_with_files = AnalysisSession.objects.filter(
            temp_file_path__isnull=False, temp_file_path__gt="", file_deleted_timestamp__isnull=True
        )

        for session in sessions_with_files:
            path = Path(session.temp_file_path)
            if path.exists():
                # Файл еще существует, проверяем время
                file_age = timezone.now() - session.upload_timestamp
                if file_age.total_seconds() > settings.FILE_RETENTION_SECONDS + 10.0:  # +10 сек погрешность
                    try:
                        path.unlink()
                        session.temp_file_path = ""
                        session.file_deleted_timestamp = timezone.now()
                        session.save()

                        SecurityLog.objects.create(
                            user=session.user,
                            action="FORCE_FILE_DELETION",
                            details=f"Принудительно удален файл сессии {session.pk}",
                            ip_address=None,
                        )
                    except Exception as e:
                        logger.error(f"Ошибка принудительного удаления файла {session.temp_file_path}: {e}")
            else:
                # Файл уже не существует, обновляем запись
                session.temp_file_path = ""
                session.file_deleted_timestamp = timezone.now()
                session.save()


@shared_task(queue="default")
def schedule_file_deletion(file_path: str, session_id: int):
    """Планируем удаление файла через 60 секунд"""
    from django.utils import timezone
    import time

    # Ждем 60 секунд
    time.sleep(settings.FILE_RETENTION_SECONDS)

    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()

            # Обновляем информацию в БД
            session = AnalysisSession.objects.get(id=session_id)
            session.file_deleted_timestamp = timezone.now()
            session.temp_file_path = ""
            session.save()

            security_logger.info(f"Файл удален: {file_path}, сессия: {session_id}")

    except Exception as e:
        logger.error(f"Ошибка удаления файла {file_path}: {e}")


@shared_task(queue="default")
def process_medical_file(session_id: int):
    session = None

    try:
        session = AnalysisSession.objects.get(id=session_id)

        if not session.temp_file_path or not Path(session.temp_file_path).exists():
            raise FileNotFoundError("Временный файл не найден")

        # 1. OCR - извлекаем текст
        logger.info(f"=== OCR для сессии {session_id} ===")
        ocr_processor = OCRProcessor()
        extracted_text = ocr_processor.process_file(session.temp_file_path)
        logger.info(f"Извлечено {len(extracted_text)} символов")

        # 2. Определяем тип анализа
        parser = MedicalDataParser()
        analysis_type = parser.detect_analysis_type(extracted_text)
        session.analysis_type = analysis_type
        logger.info(f"Тип анализа: {analysis_type}")

        # 3. Парсинг через GPT (если ключ настроен)
        parsed_data = {}
        parsing_method = "regex"

        if settings.OPENAI_API_KEY:
            try:
                logger.info("=== Парсинг через GPT ===")
                gpt_parser = GPTMedicalParser()
                gpt_result = gpt_parser.parse_analysis(extracted_text, analysis_type)

                if gpt_result and gpt_result.get("parameters"):
                    parsed_data = format_gpt_result(gpt_result)
                    parsing_method = "gpt"

                    logger.info(f"GPT успешно распознал {len(parsed_data)} параметров")
                else:
                    raise ValueError("GPT вернул пустой результат")

            except Exception as e:
                logger.warning(f"GPT парсинг не удался: {e}, используем regex")
                parsing_method = "regex_fallback"

        # 4. Фолбек на regex парсер
        if not parsed_data:
            logger.info("=== Парсинг через regex ===")
            if analysis_type == AnalysisType.BLOOD_GENERAL:
                parsed_data = parser.parse_blood_general(extracted_text)
            elif analysis_type == AnalysisType.BLOOD_BIOCHEM:
                parsed_data = parser.parse_blood_biochem(extracted_text)
            elif analysis_type == AnalysisType.HORMONES:
                parsed_data = parser.parse_hormones(extracted_text)
            else:
                parsed_data = {}

        # 5. Сохраняем зашифрованные данные
        medical_data = MedicalData(
            user=session.user, session=session, analysis_type=analysis_type, analysis_date=timezone.now().date()
        )

        full_data = {
            "parsed_data": parsed_data,
            "raw_text": extracted_text,  # ВСЕГДА сохраняем исходник
            "processing_info": {
                "processed_at": timezone.now().isoformat(),
                "file_name": session.original_filename,
                "analysis_type": analysis_type,
                "parsing_method": parsing_method,
                "parameters_found": len(parsed_data),
            },
        }

        medical_data.encrypt_data(full_data)
        medical_data.save()

        session.processing_status = "completed"
        session.processing_completed = timezone.now()
        session.save()

        SecurityLog.objects.create(
            user=session.user,
            action="FILE_PROCESSED",
            details=f"Файл обработан ({parsing_method}). Найдено параметров: {len(parsed_data)}",
            ip_address=None,
        )

        logger.info(f"✓ Обработка завершена для сессии {session_id}")

    except Exception as e:
        if session:
            session.processing_status = "error"
            session.error_message = str(e)
            session.save()

        logger.error(f"Ошибка обработки сессии {session_id}: {e}", exc_info=True)
        raise