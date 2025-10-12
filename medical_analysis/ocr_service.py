import logging
from typing import Optional
import numpy as np
from medical_analysis.image_preprocessor import ImagePreprocessor
from medical_analysis.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


class OCRService:
    """unified OCR service with preprocessing"""

    def __init__(self, use_gpu: bool = False):
        self.preprocessor = ImagePreprocessor(
            apply_denoising=True,
            apply_deskewing=True,
            apply_binarization=True,
        )
        self.ocr_engine = OCREngine(languages=["ru", "en"], use_gpu=use_gpu)

    def extract_text_from_file(
            self,
            image_path: str,
            save_debug: bool = False
    ) -> str:
        """extract text from image file"""
        logger.info(f"processing image: {image_path}")

        # preprocess
        processed_image = self.preprocessor.process(
            image_path,
            save_debug=save_debug
        )

        # OCR
        text = self.ocr_engine.extract_text(processed_image)

        logger.info(f"extracted {len(text)} characters")
        return text

    def extract_text_from_array(self, image: np.ndarray) -> str:
        """extract text from numpy array (already preprocessed)"""
        return self.ocr_engine.extract_text(image)


# singleton instance
_service_instance: Optional[OCRService] = None


def get_ocr_service(use_gpu: bool = False) -> OCRService:
    """get or create OCR service singleton"""
    global _service_instance
    if _service_instance is None:
        _service_instance = OCRService(use_gpu=use_gpu)
    return _service_instance