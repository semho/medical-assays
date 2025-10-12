import logging
from typing import List, Tuple
import numpy as np
import easyocr

logger = logging.getLogger(__name__)


class OCREngine:
    def __init__(self, languages: List[str] = None, use_gpu: bool = False):
        self.languages = languages or ["ru", "en"]
        self.use_gpu = use_gpu
        self._reader = None

    @property
    def reader(self):
        """lazy initialization"""
        if self._reader is None:
            logger.info(f"initializing EasyOCR: {self.languages}, GPU={self.use_gpu}")
            self._reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                verbose=False,
            )
        return self._reader

    def extract_text(self, image: np.ndarray) -> str:
        """extract text from preprocessed image"""
        results = self.reader.readtext(
            image,
            detail=0,  # only text, no bboxes
            paragraph=True,  # merge lines into paragraphs
        )

        # join results with newlines
        text = "\n".join(results)
        logger.debug(f"extracted {len(text)} characters")

        return text

    def extract_text_with_boxes(
        self, image: np.ndarray
    ) -> List[Tuple[List[List[int]], str, float]]:
        """extract text with bounding boxes and confidence"""
        results = self.reader.readtext(image, detail=1)
        logger.debug(f"detected {len(results)} text regions")
        return results


# function for backward compatibility
def extract_text_easyocr(image: np.ndarray) -> str:
    engine = OCREngine()
    return engine.extract_text(image)