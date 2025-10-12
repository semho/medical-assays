import logging
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    def __init__(
        self,
        target_dpi: int = 300,
        apply_denoising: bool = True,
        apply_deskewing: bool = True,
        apply_binarization: bool = True,
        noise_kernel_size: int = 3,
        min_dpi_for_upscale: int = 200,
        skew_range: float = 10.0,
    ):
        self.target_dpi = target_dpi
        self.apply_denoising = apply_denoising
        self.apply_deskewing = apply_deskewing
        self.apply_binarization = apply_binarization
        self.noise_kernel_size = noise_kernel_size
        self.min_dpi_for_upscale = min_dpi_for_upscale
        self.skew_range = skew_range

    def process(self, image_path: str, save_debug: bool = False) -> np.ndarray:
        logger.info(f"starting preprocessing: {image_path}")

        image = self._load_image(image_path)
        logger.debug(f"loaded image: {image.shape}")

        # step 1: grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if save_debug:
            self._save_debug_image(gray, image_path, "01_grayscale")

        # step 2: smart resize
        estimated_dpi = gray.shape[1] / 8.3
        logger.debug(f"estimated DPI: {estimated_dpi:.0f}")
        resized = self._smart_resize(gray, estimated_dpi)

        if save_debug:
            self._save_debug_image(resized, image_path, "02_resized")

        current = resized

        # step 3: noise reduction
        if self.apply_denoising:
            current = self._adaptive_denoise(current)

        if save_debug:
            self._save_debug_image(current, image_path, "03_denoised")

        # step 4: contrast enhancement
        current = self._enhance_contrast(current)

        if save_debug:
            self._save_debug_image(current, image_path, "04_enhanced")

        # step 5: deskew
        if self.apply_deskewing:
            angle = self._detect_skew(current)
            logger.debug(f"skew angle: {angle:.2f}°")
            if abs(angle) > 0.3:
                current = self._rotate_image(current, angle)
            else:
                logger.debug("no significant skew")

        if save_debug:
            self._save_debug_image(current, image_path, "05_deskewed")

        # step 6: adaptive binarization
        if self.apply_binarization:
            current = self._adaptive_binarize(current)

        if save_debug:
            self._save_debug_image(current, image_path, "06_binary")

        # step 7: morphological cleanup
        current = self._morphological_cleanup(current)

        if save_debug:
            self._save_debug_image(current, image_path, "07_final")

        logger.info(f"preprocessing complete: {current.shape}")
        return current

    def _smart_resize(self, image: np.ndarray, estimated_dpi: float) -> np.ndarray:
        height, width = image.shape[:2]

        if estimated_dpi < self.min_dpi_for_upscale:
            scale = self.target_dpi / estimated_dpi
            new_width = int(width * scale)
            new_height = int(height * scale)
            return cv2.resize(
                image, (new_width, new_height), interpolation=cv2.INTER_CUBIC
            )
        elif estimated_dpi > 400:
            scale = self.target_dpi / estimated_dpi
            new_width = int(width * scale)
            new_height = int(height * scale)
            return cv2.resize(
                image, (new_width, new_height), interpolation=cv2.INTER_AREA
            )

        return image

    def _adaptive_denoise(self, image: np.ndarray) -> np.ndarray:
        """adaptive noise reduction based on local variance"""
        noise_level = np.std(image)
        logger.debug(f"noise level: {noise_level:.1f}")

        if noise_level > 20:
            # high noise: bilateral filter
            denoised = cv2.bilateralFilter(image, 5, 50, 50)
        elif noise_level > 10:
            # medium noise: non-local means
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        else:
            # low noise: skip
            denoised = image

        return denoised

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """adaptive histogram equalization with unsharp masking"""
        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)

        # unsharp masking
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
        unsharp = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)

        return np.clip(unsharp, 0, 255).astype(np.uint8)

    def _detect_skew(self, image: np.ndarray) -> float:
        """hough transform for skew detection"""
        # edge detection
        edges = cv2.Canny(image, 50, 150, apertureSize=3)

        # hough line transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

        if lines is None:
            logger.debug("no lines detected")
            return 0.0

        # collect angles
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            # filter near-horizontal lines
            if abs(angle) < self.skew_range:
                angles.append(angle)

        if not angles:
            logger.debug("no valid angles")
            return 0.0

        # median angle (robust to outliers)
        median_angle = np.median(angles)
        logger.debug(f"detected {len(angles)} lines, median: {median_angle:.2f}°")

        return median_angle

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """rotate with border replication"""
        height, width = image.shape
        center = (width // 2, height // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            M,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

        return rotated

    def _adaptive_binarize(self, image: np.ndarray) -> np.ndarray:
        """adaptive thresholding with Otsu fallback"""
        # try adaptive threshold
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        # check if mostly white or black
        mean_val = np.mean(binary)
        if mean_val < 50 or mean_val > 200:
            # fallback to Otsu
            _, binary = cv2.threshold(
                image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            logger.debug("used Otsu threshold")
        else:
            logger.debug("used adaptive threshold")

        # ensure black text on white background
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)

        return binary

    def _morphological_cleanup(self, image: np.ndarray) -> np.ndarray:
        """remove small noise and connect broken characters"""
        # remove small dots
        kernel_small = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel_small)

        # connect broken chars
        kernel_connect = np.ones((1, 2), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_connect)

        return cleaned

    def _load_image(self, image_path: str) -> np.ndarray:
        image = cv2.imread(image_path)
        if image is None:
            pil_image = Image.open(image_path)
            image = np.array(pil_image)
            if len(image.shape) == 3 and image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        return image

    def _save_debug_image(
        self, image: np.ndarray, original_path: str, suffix: str
    ) -> None:
        try:
            debug_dir = Path(original_path).parent / "debug_preprocessing"
            debug_dir.mkdir(exist_ok=True)
            filename = Path(original_path).stem
            debug_path = debug_dir / f"{filename}_{suffix}.png"
            cv2.imwrite(str(debug_path), image)
        except Exception as e:
            logger.warning(f"failed to save debug image: {e}")


def preprocess_for_ocr(image_path: str, save_debug: bool = False) -> np.ndarray:
    preprocessor = ImagePreprocessor(
        apply_denoising=True,
        apply_deskewing=True,
        apply_binarization=True,
    )
    return preprocessor.process(image_path, save_debug=save_debug)