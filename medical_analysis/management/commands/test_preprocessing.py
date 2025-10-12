"""
management command for testing image preprocessing.

location: medical_analysis/management/commands/test_preprocessing.py

usage:
    python manage.py test_preprocessing --file-path /path/to/test.jpg
    python manage.py test_preprocessing --file-path /path/to/test.jpg --save-debug
"""

from django.core.management.base import BaseCommand
from pathlib import Path
import logging
from medical_analysis.image_preprocessor import ImagePreprocessor
import pytesseract
from PIL import Image
from django.utils import timezone

from medical_analysis.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "test image preprocessing pipeline for OCR improvement"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file-path",
            type=str,
            required=True,
            help="path to test image file",
        )
        parser.add_argument(
            "--save-debug",
            action="store_true",
            help="save debug images for each preprocessing step",
        )
        parser.add_argument(
            "--engine",
            type=str,
            choices=["tesseract", "easyocr", "both"],
            default="both",
            help="OCR engine to test",
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        save_debug = options["save_debug"]
        engine = options["engine"]

        if not Path(file_path).exists():
            self.stdout.write(
                self.style.ERROR(f"file not found: {file_path}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS("\n" + "=" * 70)
        )
        self.stdout.write(self.style.SUCCESS("OCR engines comparison"))
        self.stdout.write(
            self.style.SUCCESS("=" * 70)
        )
        self.stdout.write(f"file: {file_path}")
        self.stdout.write(f"save debug: {save_debug}\n")

        if engine in ["tesseract", "both"]:
            self._test_tesseract(file_path, save_debug)

        # easyocr
        if engine in ["easyocr", "both"]:
            self._test_easyocr(file_path, save_debug)

    def _test_easyocr(self, file_path: str, save_debug: bool):
        self.stdout.write(self.style.WARNING("\n=== EasyOCR ==="))
        self.stdout.write("-" * 70)

        preprocessor = ImagePreprocessor(
            apply_denoising=True,
            apply_deskewing=True,
            apply_binarization=True,
        )
        processed_image = preprocessor.process(file_path, save_debug=save_debug)

        start_time = timezone.now()
        ocr_engine = OCREngine(languages=["ru", "en"], use_gpu=False)
        text = ocr_engine.extract_text(processed_image)
        elapsed = (timezone.now() - start_time).total_seconds()

        self.stdout.write(f"\ntime: {elapsed:.2f}s")
        self.stdout.write(f"extracted: {len(text)} chars")

        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("FULL TEXT:")
        self.stdout.write(f"{'='*70}\n")
        self.stdout.write(text)
        self.stdout.write(f"\n{'='*70}")

        self._analyze_text(text, "easyocr")

    def _analyze_text(self, text: str, engine_name: str):
        """analyze text quality"""
        medical_keywords = [
            "гемоглобин",
            "эритроциты",
            "лейкоциты",
            "тромбоциты",
            "глюкоза",
            "белок",
            "креатинин",
            "анализ",
            "результат",
            "нейтрофилы",
            "моноциты",
            "лимфоциты",
            "базофилы",
            "эозинофилы",
        ]

        found_keywords = [kw for kw in medical_keywords if kw in text.lower()]
        digits = sum(c.isdigit() for c in text)

        # check for table structure
        has_table_markers = any(marker in text for marker in [
            "НАИМЕНОВАНИЕ",
            "РЕЗУЛЬТАТ",
            "РЕФЕРЕНСНЫЕ",
            "ЕД. ИЗМ"
        ])

        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"analysis ({engine_name}):")
        self.stdout.write(f"{'='*70}")
        self.stdout.write(f"  total length: {len(text)} chars")
        self.stdout.write(f"  digits found: {digits}")
        self.stdout.write(f"  medical keywords: {len(found_keywords)}")

        if found_keywords:
            for kw in found_keywords:
                self.stdout.write(f"    ✓ {kw}")

        self.stdout.write(f"  table structure detected: {'YES' if has_table_markers else 'NO'}")

        if has_table_markers:
            self.stdout.write(self.style.SUCCESS("    ✓ found table headers"))


    def _test_tesseract(self, file_path: str, save_debug: bool):
        """detailed test with step-by-step analysis"""

        # test each preprocessing step
        self.stdout.write(
            self.style.WARNING("\n1. testing preprocessing steps")
        )
        self.stdout.write("-" * 70)

        preprocessor = ImagePreprocessor()

        try:
            # load original
            image = preprocessor._load_image(file_path)
            self.stdout.write(
                f"✓ loaded image: {image.shape}"
            )

            # grayscale
            if len(image.shape) == 3:
                gray = Image.open(file_path).convert("L")
                self.stdout.write(
                    f"✓ grayscale conversion"
                )

            # full preprocessing
            processed = preprocessor.process(file_path, save_debug=save_debug)
            self.stdout.write(
                f"✓ full preprocessing: {processed.shape}"
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"preprocessing failed: {e}")
            )
            return

        # OCR tests
        self.stdout.write(
            self.style.WARNING("\n2. OCR tests")
        )
        self.stdout.write("-" * 70)

        # original
        start_time = timezone.now()
        original_image = Image.open(file_path)
        custom_config = r"--oem 3 --psm 6 -l rus+eng"
        original_text = pytesseract.image_to_string(
            original_image, config=custom_config
        )
        original_time = (timezone.now() - start_time).total_seconds()

        self.stdout.write(
            f"original OCR: {len(original_text)} chars in {original_time:.2f}s"
        )

        # preprocessed
        start_time = timezone.now()
        pil_processed = Image.fromarray(processed)
        preprocessed_text = pytesseract.image_to_string(
            pil_processed, config=custom_config
        )
        self.stdout.write(f"\nfull preprocessed text:\n{preprocessed_text}")
        preprocessed_time = (timezone.now() - start_time).total_seconds()

        self.stdout.write(
            f"preprocessed OCR: {len(preprocessed_text)} chars in {preprocessed_time:.2f}s"
        )

        # detailed comparison
        self.stdout.write(
            self.style.WARNING("\n3. detailed comparison")
        )
        self.stdout.write("-" * 70)

        self._print_comparison(
            original_text, preprocessed_text,
            original_time, preprocessed_time
        )

        # show samples
        self.stdout.write(
            self.style.WARNING("\n4. text samples")
        )
        self.stdout.write("-" * 70)

        self.stdout.write("\noriginal (first 300 chars):")
        self.stdout.write(original_text[:300])

        self.stdout.write("\npreprocessed (first 300 chars):")
        self.stdout.write(preprocessed_text[:300])

    def _print_comparison(
            self,
            original_text: str,
            preprocessed_text: str,
            original_time: float,
            preprocessed_time: float,
    ):
        """print detailed comparison statistics"""

        # length comparison
        improvement = len(preprocessed_text) - len(original_text)
        improvement_pct = (
            (improvement / len(original_text) * 100)
            if len(original_text) > 0
            else 0
        )

        self.stdout.write(f"\nlength:")
        self.stdout.write(f"  original:     {len(original_text)} chars")
        self.stdout.write(f"  preprocessed: {len(preprocessed_text)} chars")

        if improvement > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  improvement:  +{improvement} chars (+{improvement_pct:.1f}%)"
                )
            )
        elif improvement < 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  change:       {improvement} chars ({improvement_pct:.1f}%)"
                )
            )
        else:
            self.stdout.write(
                f"  change:       no change"
            )

        # time comparison
        self.stdout.write(f"\nprocessing time:")
        self.stdout.write(f"  original:     {original_time:.2f}s")
        self.stdout.write(f"  preprocessed: {preprocessed_time:.2f}s")
        time_overhead = preprocessed_time - original_time
        self.stdout.write(f"  overhead:     +{time_overhead:.2f}s")

        # medical keywords
        medical_keywords = [
            "гемоглобин", "эритроциты", "лейкоциты", "тромбоциты",
            "глюкоза", "белок", "креатинин", "мочевина", "билирубин",
            "холестерин", "ттг", "т4", "анализ", "результат"
        ]

        original_keywords = [
            kw for kw in medical_keywords if kw in original_text.lower()
        ]
        preprocessed_keywords = [
            kw for kw in medical_keywords if kw in preprocessed_text.lower()
        ]

        self.stdout.write(f"\nmedical keywords found:")
        self.stdout.write(f"  original:     {len(original_keywords)}")
        if original_keywords:
            for kw in original_keywords:
                self.stdout.write(f"    ✓ {kw}")

        self.stdout.write(f"  preprocessed: {len(preprocessed_keywords)}")
        if preprocessed_keywords:
            for kw in preprocessed_keywords:
                self.stdout.write(f"    ✓ {kw}")

        keyword_improvement = len(preprocessed_keywords) - len(original_keywords)
        if keyword_improvement > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  improvement:  +{keyword_improvement} keywords"
                )
            )
        elif keyword_improvement < 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  change:       {keyword_improvement} keywords"
                )
            )

        # quality assessment
        self.stdout.write(f"\nquality assessment:")

        # check for common OCR errors
        common_errors = ["|||", "___", "...", "???"]
        original_errors = sum(
            original_text.count(err) for err in common_errors
        )
        preprocessed_errors = sum(
            preprocessed_text.count(err) for err in common_errors
        )

        self.stdout.write(f"  OCR artifacts:")
        self.stdout.write(f"    original:     {original_errors}")
        self.stdout.write(f"    preprocessed: {preprocessed_errors}")

        # digit/letter ratio (medical docs should have many numbers)
        def count_digits(text):
            return sum(c.isdigit() for c in text)

        original_digits = count_digits(original_text)
        preprocessed_digits = count_digits(preprocessed_text)

        self.stdout.write(f"  digits found:")
        self.stdout.write(f"    original:     {original_digits}")
        self.stdout.write(f"    preprocessed: {preprocessed_digits}")

        # overall verdict
        self.stdout.write(
            self.style.WARNING("\noverall verdict:")
        )

        score = 0
        if improvement > 0:
            score += 1
        if keyword_improvement > 0:
            score += 2
        if preprocessed_errors < original_errors:
            score += 1
        if preprocessed_digits > original_digits:
            score += 1

        if score >= 4:
            verdict = "excellent improvement"
            style = self.style.SUCCESS
        elif score >= 2:
            verdict = "moderate improvement"
            style = self.style.WARNING
        else:
            verdict = "minimal or no improvement"
            style = self.style.ERROR

        self.stdout.write(
            style(f"  {verdict} (score: {score}/5)")
        )