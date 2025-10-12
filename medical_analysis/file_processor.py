import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pytesseract
import fitz  # PyMuPDF
import re
from django.conf import settings
from django.utils import timezone

from .constants import (
    PARAMETER_TYPE_MAP,
    LABORATORY_SIGNATURES,
    HORMONES_PARSER,
    BLOOD_PARSER,
    BLOOD_LEUKO_PARAMS,
    RANGES_PARSER,
    BIOCHEM_PARSER,
    ANALYSIS_KEYWORDS,
)
from .enums import AnalysisType, Status, LaboratoryType
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
        from medical_analysis.ocr_service import get_ocr_service
        self.ocr_service = get_ocr_service()

        # tesseract для PDF fallback
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
        """извлечение текста из изображения используя EasyOCR"""
        try:
            logger.info(f"OCR изображения: {file_path}")
            text = self.ocr_service.extract_text_from_file(file_path)
            logger.info(f"извлечено {len(text)} символов")
            return text

        except Exception as e:
            logger.error(f"ошибка OCR изображения: {e}")
            raise

    def process_file(self, file_path: str) -> str:
        """основной метод обработки файла"""
        file_extension = Path(file_path).suffix.lower()

        if file_extension == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif file_extension in [".jpg", ".jpeg", ".png", ".tiff"]:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"неподдерживаемый тип файла: {file_extension}")


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

    def _get_hormone_unit(self, param_key: str, lines: list[str]) -> str:
        """извлечение единицы измерения для гормонов"""
        unit_patterns = {
            "tsh": r"мкме/мл|μiu/ml",
            "free_t4": r"пмоль/л|pmol/l",
            "free_t3": r"пмоль/л|pmol/l",
            "testosterone": r"нмоль/л|nmol/l",
            "estradiol": r"пг/мл|pg/ml",
            "progesterone": r"нмоль/л|nmol/l",
            "cortisol": r"нмоль/л|nmol/l",
        }

        for line in lines:
            line_lower = line.lower()
            if param_key in unit_patterns:
                match = re.search(unit_patterns[param_key], line_lower)
                if match:
                    return match.group(0)

            # общий поиск единиц измерения
            common_units = re.search(r"(мкме/мл|пмоль/л|нмоль/л|пг/мл|μiu/ml|pmol/l|nmol/l|pg/ml)", line_lower)
            if common_units:
                return common_units.group(0)

        return ""

    def parse_hormones(self, text: str) -> dict:
        """парсинг гормональных анализов с полной структурой"""
        results = {}
        lines = text.split("\n")

        params_map = HORMONES_PARSER

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            for param_key, keywords in params_map.items():
                if any(keyword in line_lower for keyword in keywords):
                    for offset in range(1, 4):
                        if i + offset >= len(lines):
                            break

                        check_line = lines[i + offset].strip()
                        match = re.search(r"(\d+[\.,]\d+|\d+)\*?", check_line)

                        if match:
                            try:
                                value = float(match.group(1).replace(",", "."))
                                if param_key not in results:
                                    results[param_key] = {
                                        "value": value,
                                        "unit": self._get_hormone_unit(param_key, lines[i:i + offset + 1]),
                                        "reference": self._get_reference(lines[i:i + offset + 1]),
                                        "status": self._determine_status(lines[i:i + offset + 1], value),
                                    }
                                    logger.info(f"найден {param_key}: {value}")
                                break
                            except ValueError:
                                continue
                    break

        return results
    def parse_blood_general(self, text: str) -> dict:
        """парсинг общего анализа крови с полной структурой"""
        results = {}
        lines = text.split("\n")

        params_map = BLOOD_PARSER
        leuko_params_map = BLOOD_LEUKO_PARAMS

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            for param_key, keywords in {**params_map, **leuko_params_map}.items():
                if any(keyword in line_lower for keyword in keywords):
                    # для процентных значений
                    if param_key in leuko_params_map:
                        for offset in range(1, 4):
                            if i + offset >= len(lines):
                                break

                            check_line = lines[i + offset].strip()
                            match = re.search(r"(\d+[\.,]\d+|\d+)%?", check_line)

                            if match:
                                try:
                                    value = float(match.group(1).replace(",", "."))
                                    if 0 <= value <= 100:
                                        results[param_key] = {
                                            "value": value,
                                            "unit": "%",
                                            "reference": self._get_reference(lines[i:i + offset + 1]),
                                            "status": self._determine_status(lines[i:i + offset + 1], value),
                                        }
                                        logger.info(f"найден {param_key}: {value}%")
                                        break
                                except ValueError:
                                    continue
                        break
                    else:
                        # для остальных параметров
                        for offset in range(1, 4):
                            if i + offset >= len(lines):
                                break

                            check_line = lines[i + offset].strip()
                            match = re.search(r"(\d+[\.,]\d+|\d+)\*?", check_line)

                            if match:
                                try:
                                    value = float(match.group(1).replace(",", "."))
                                    if self._validate_value(param_key, value):
                                        results[param_key] = {
                                            "value": value,
                                            "unit": self._get_unit(param_key, lines[i:i + offset + 1]),
                                            "reference": self._get_reference(lines[i:i + offset + 1]),
                                            "status": self._determine_status(lines[i:i + offset + 1], value),
                                        }
                                        logger.info(f"найден {param_key}: {value}")
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

    def parse_blood_biochem(self, text: str) -> dict:
        """парсинг биохимии с полной структурой"""
        results = {}
        lines = text.split("\n")

        params_map = BIOCHEM_PARSER

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            for param_key, keywords in params_map.items():
                if any(keyword in line_lower for keyword in keywords):
                    for offset in range(1, 4):
                        if i + offset >= len(lines):
                            break

                        check_line = lines[i + offset].strip()
                        match = re.search(r"(\d+[\.,]\d+|\d+|\d+\.\d+)\*?", check_line)

                        if match:
                            try:
                                value = float(match.group(1).replace(",", "."))
                                if self._validate_value(param_key, value):
                                    if param_key not in results:
                                        results[param_key] = {
                                            "value": value,
                                            "unit": self._get_unit(param_key, lines[i:i + offset + 1]),
                                            "reference": self._get_reference(lines[i:i + offset + 1]),
                                            "status": self._determine_status(lines[i:i + offset + 1], value),
                                        }
                                        logger.info(f"найден {param_key}: {value}")
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
        blood_general_keywords = ANALYSIS_KEYWORDS.get("blood_general")
        biochem_keywords = ANALYSIS_KEYWORDS.get("biochem")
        hormones_keywords = ANALYSIS_KEYWORDS.get("hormones")

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
    """
    Обработка медицинского файла с групповым парсингом всех типов анализов
    """
    session = None

    try:
        session = AnalysisSession.objects.get(id=session_id)
        session.processing_started = timezone.now()
        session.processing_status = Status.PROCESSING
        session.save(update_fields=["processing_started", "processing_status"])

        if not session.temp_file_path or not Path(session.temp_file_path).exists():
            raise FileNotFoundError("Временный файл не найден")

        # 1. OCR - извлекаем текст
        logger.info(f"=== Сессия {session_id}: OCR ===")
        session.processing_status = Status.OCR
        session.save(update_fields=["processing_status"])

        ocr_processor = OCRProcessor()
        extracted_text = ocr_processor.process_file(session.temp_file_path)
        logger.info(f"Извлечено {len(extracted_text)} символов")

        # 2. НОВОЕ: Групповой парсинг всех типов
        logger.info(f"=== Сессия {session_id}: Групповой парсинг ===")
        session.processing_status = Status.PARSING
        session.save(update_fields=["processing_status"])

        grouped_parser = GroupedAnalysisParser()
        grouped_results = grouped_parser.parse_all_types(extracted_text)

        # Определяем лабораторию
        laboratory = grouped_results["_metadata"]["laboratory"]
        parsing_method = grouped_results["_metadata"]["parsing_method"]

        # Определяем основной тип для совместимости
        primary_type = grouped_parser.determine_primary_type(grouped_results)
        session.analysis_type = primary_type
        session.save()

        logger.info(f"Лаборатория: {laboratory}")
        logger.info(f"Основной тип: {primary_type}")
        logger.info(f"Метод парсинга: {parsing_method}")

        # 3. Подготавливаем объединённые данные для старого формата (для совместимости)
        # Объединяем все параметры в один словарь для отображения
        all_parameters = {}
        for analysis_type in [
            AnalysisType.BLOOD_GENERAL,
            AnalysisType.BLOOD_BIOCHEM,
            AnalysisType.HORMONES,
            AnalysisType.OTHER,
        ]:
            all_parameters.update(grouped_results.get(analysis_type, {}))

        # 4. Подсчитываем статистику
        params_by_type = {
            "blood_general": len(grouped_results.get("blood_general", {})),
            "blood_biochem": len(grouped_results.get("blood_biochem", {})),
            "hormones": len(grouped_results.get("hormones", {})),
            "other": len(grouped_results.get("other", {})),
        }

        total_params = sum(params_by_type.values())
        logger.info(f"Всего распознано параметров: {total_params}")

        # 5. Создаём запись MedicalData
        medical_data = MedicalData(
            user=session.user,
            session=session,
            analysis_type=primary_type,
            analysis_date=timezone.now().date(),
            laboratory=laboratory,
            is_confirmed=False,  # Требует подтверждения пользователем
        )

        # 6. Формируем полную структуру данных для сохранения
        full_data = {
            # Групповые данные (новый формат)
            "grouped_data": {
                "blood_general": grouped_results.get("blood_general", {}),
                "blood_biochem": grouped_results.get("blood_biochem", {}),
                "hormones": grouped_results.get("hormones", {}),
                "other": grouped_results.get("other", {}),
            },
            # Объединённые данные (старый формат для совместимости)
            "parsed_data": all_parameters,
            # Метаданные
            "raw_text": extracted_text,
            "processing_info": {
                "processed_at": timezone.now().isoformat(),
                "file_name": session.original_filename,
                "primary_type": primary_type,
                "laboratory": laboratory,
                "parsing_method": parsing_method,
                "total_parameters": total_params,
                "parameters_by_type": params_by_type,
            },
        }

        # 7. Шифруем и сохраняем
        medical_data.encrypt_and_save(full_data)

        # 8. Обновляем статус сессии
        session.processing_status = Status.COMPLETED
        session.processing_completed = timezone.now()
        session.save()

        # 9. Планируем удаление временного файла
        schedule_file_deletion.apply_async(
            args=[session.temp_file_path, session_id], countdown=settings.FILE_RETENTION_SECONDS
        )

        # 10. Логируем успех
        SecurityLog.objects.create(
            user=session.user,
            action="FILE_PROCESSED",
            details=f"Файл обработан ({parsing_method}, лаб: {laboratory}). "
            f"Найдено параметров: {total_params} "
            f"(ОАК: {params_by_type['blood_general']}, "
            f"Биохимия: {params_by_type['blood_biochem']}, "
            f"Гормоны: {params_by_type['hormones']})",
            ip_address=None,
        )

        logger.info(f"✓ Сессия {session_id} успешно обработана")
        return f"Success: {total_params} parameters found"

    except Exception as e:
        logger.error(f"Ошибка обработки сессии {session_id}: {e}", exc_info=True)

        if session:
            session.processing_status = Status.ERROR
            session.error_message = str(e)
            session.processing_completed = timezone.now()
            session.save()

            # Всё равно планируем удаление файла
            if session.temp_file_path and Path(session.temp_file_path).exists():
                schedule_file_deletion.apply_async(
                    args=[session.temp_file_path, session_id],
                    countdown=10,  # Удаляем через 10 секунд при ошибке
                )

        raise


class GroupedAnalysisParser:
    """
    Парсер, который распознаёт ВСЕ типы анализов из одного файла
    и группирует параметры по типам
    """

    def __init__(self):
        self.gpt_parser = GPTMedicalParser() if settings.OPENAI_API_KEY else None
        self.laboratory = LaboratoryType.UNKNOWN

    def detect_laboratory(self, text: str) -> str:
        """Определение лаборатории по характерным меткам"""
        text_lower = text.lower()

        for lab, signatures in LABORATORY_SIGNATURES.items():
            if any(sig in text_lower for sig in signatures):
                logger.info(f"Обнаружена лаборатория: {lab}")
                return lab

        return self.laboratory

    def parse_all_types(self, text: str) -> dict:
        """
        Парсинг всех типов анализов из текста
        Возвращает структуру: {'blood_general': {...}, 'blood_biochem': {...}, 'hormones': {...}}
        """
        logger.info("=== Групповой парсинг всех типов ===")

        # Определяем лабораторию
        self.laboratory = self.detect_laboratory(text)

        grouped_results = {
            "blood_general": {},
            "blood_biochem": {},
            "hormones": {},
            "other": {},
            "_metadata": {
                "laboratory": self.laboratory,
                "parsing_method": None,
            },
        }

        # Если есть GPT - используем его для каждого типа
        if self.gpt_parser:
            grouped_results = self._parse_with_gpt(text, grouped_results)
        else:
            grouped_results = self._parse_with_regex(text, grouped_results)

        # Классифицируем параметры по типам
        grouped_results = self._classify_parameters(grouped_results)

        # Подсчитываем статистику
        total_params = sum(len(grouped_results[t]) for t in ["blood_general", "blood_biochem", "hormones", "other"])
        logger.info(f"Всего распознано параметров: {total_params}")
        logger.info(f"  - Общий анализ: {len(grouped_results['blood_general'])}")
        logger.info(f"  - Биохимия: {len(grouped_results['blood_biochem'])}")
        logger.info(f"  - Гормоны: {len(grouped_results['hormones'])}")
        logger.info(f"  - Прочее: {len(grouped_results['other'])}")

        return grouped_results

    def _parse_with_gpt(self, text: str, grouped_results: dict) -> dict:
        """Парсинг с использованием GPT для каждого типа"""

        if not self.gpt_parser:
            logger.info("GPT parser not initialized")
            return self._parse_with_regex(text, grouped_results)

        # Проверяем включён ли GPT
        if not self.gpt_parser.is_enabled():
            logger.info("GPT parsing disabled, using regex fallback")
            grouped_results["_metadata"]["parsing_method"] = "regex (gpt_disabled)"
            return self._parse_with_regex(text, grouped_results)

        logger.info("Используем GPT для парсинга")
        all_parameters = {}

        try:
            # Пробуем каждый промпт
            for analysis_type in [AnalysisType.BLOOD_GENERAL, AnalysisType.BLOOD_BIOCHEM, AnalysisType.HORMONES]:
                try:
                    logger.info(f"GPT парсинг: {analysis_type}")
                    gpt_result = self.gpt_parser.parse_analysis(text, analysis_type, laboratory=self.laboratory)

                    if gpt_result and gpt_result.get("parameters"):
                        formatted = format_gpt_result(gpt_result)
                        all_parameters.update(formatted)
                        logger.info(f"  + {len(formatted)} параметров")

                except Exception as e:
                    logger.warning(f"Ошибка GPT парсинга {analysis_type}: {e}")
                    # check fallback setting
                    if self.gpt_parser.settings.fallback_enabled:
                        logger.info("falling back to regex due to error")
                        return self._parse_with_regex(text, grouped_results)
                    else:
                        logger.warning("fallback disabled, continuing with other analysis types")
                        continue

            # Если GPT что-то нашёл
            if all_parameters:
                grouped_results["_metadata"]["parsing_method"] = "gpt"
                # Параметры будут классифицированы позже
                grouped_results["_raw_parameters"] = all_parameters
            else:
                # fallback to regex if enabled
                if self.gpt_parser.settings.fallback_enabled:
                    logger.info("gpt returned no results, using regex")
                    grouped_results = self._parse_with_regex(text, grouped_results)
                else:
                    logger.warning("gpt returned no results and fallback disabled")

            return grouped_results
        except Exception as e:
            logger.error(f"GPT parsing error: {e}")

            # Проверяем fallback
            if self.gpt_parser.settings.fallback_enabled:
                logger.info("Falling back to regex due to error")
                return self._parse_with_regex(text, grouped_results)
            else:
                logger.warning("Fallback disabled, returning empty results")
                return grouped_results

    def _parse_with_regex(self, text: str, grouped_results: dict) -> dict:
        """Фолбек на regex парсинг"""
        logger.info("Используем regex для парсинга")
        grouped_results["_metadata"]["parsing_method"] = "regex"

        parser = MedicalDataParser()

        # Парсим каждый тип отдельно
        try:
            bg_data = parser.parse_blood_general(text)
            if bg_data:
                grouped_results["_raw_parameters"] = grouped_results.get("_raw_parameters", {})
                grouped_results["_raw_parameters"].update(bg_data)
                logger.info(f"Regex: общий анализ - {len(bg_data)} параметров")
        except Exception as e:
            logger.warning(f"Ошибка regex парсинга ОАК: {e}")

        try:
            bc_data = parser.parse_blood_biochem(text)
            if bc_data:
                grouped_results["_raw_parameters"] = grouped_results.get("_raw_parameters", {})
                grouped_results["_raw_parameters"].update(bc_data)
                logger.info(f"Regex: биохимия - {len(bc_data)} параметров")
        except Exception as e:
            logger.warning(f"Ошибка regex парсинга биохимии: {e}")

        try:
            h_data = parser.parse_hormones(text)
            if h_data:
                grouped_results["_raw_parameters"] = grouped_results.get("_raw_parameters", {})
                grouped_results["_raw_parameters"].update(h_data)
                logger.info(f"Regex: гормоны - {len(h_data)} параметров")
        except Exception as e:
            logger.warning(f"Ошибка regex парсинга гормонов: {e}")

        return grouped_results

    def _classify_parameters(self, grouped_results: dict) -> dict:
        """Классификация параметров по типам анализов"""
        raw_params = grouped_results.pop("_raw_parameters", {})

        if not raw_params:
            return grouped_results

        logger.info(f"Классификация {len(raw_params)} параметров")

        for param_key, param_value in raw_params.items():
            # Определяем тип параметра
            param_type = PARAMETER_TYPE_MAP.get(param_key.lower())

            if param_type == "blood_general":
                grouped_results["blood_general"][param_key] = param_value
            elif param_type == "blood_biochem":
                grouped_results["blood_biochem"][param_key] = param_value
            elif param_type == "hormones":
                grouped_results["hormones"][param_key] = param_value
            else:
                # Неизвестный параметр - кладём в other
                grouped_results["other"][param_key] = param_value
                logger.warning(f"Неизвестный тип для параметра: {param_key}")

        return grouped_results

    def determine_primary_type(self, grouped_results: dict) -> str:
        """Определение основного типа анализа для совместимости"""
        # Считаем количество параметров в каждом типе
        counts = {
            "blood_general": len(grouped_results.get("blood_general", {})),
            "blood_biochem": len(grouped_results.get("blood_biochem", {})),
            "hormones": len(grouped_results.get("hormones", {})),
        }

        # Возвращаем тип с максимальным количеством параметров
        if counts["blood_general"] > 0 and counts["blood_general"] >= max(counts["blood_biochem"], counts["hormones"]):
            return AnalysisType.BLOOD_GENERAL
        elif counts["blood_biochem"] > 0 and counts["blood_biochem"] >= counts["hormones"]:
            return AnalysisType.BLOOD_BIOCHEM
        elif counts["hormones"] > 0:
            return AnalysisType.HORMONES
        else:
            return AnalysisType.BLOOD_GENERAL  # дефолт
