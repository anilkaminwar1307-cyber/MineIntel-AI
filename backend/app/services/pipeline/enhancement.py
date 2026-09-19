"""
Document Enhancement Service — Computer vision preprocessing pipeline for noisy/skewed documents.
Includes deskewing, rotation correction, CLAHE contrast enhancement, denoising, sharpening,
adaptive thresholding, shadow reduction, deterministic upscaling, and multi-version candidate generation.
"""
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import cv2
from PIL import Image
import io


class DocumentEnhancementService:
    @classmethod
    def enhance_image(
        cls,
        image_bytes: bytes,
        deskew: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
        sharpen: bool = True,
        binarize: bool = False,
        upscale_if_small: bool = True,
        rotation_correction: int = 0
    ) -> Tuple[bytes, List[str]]:
        """
        Applies deterministic computer vision enhancement operations to image bytes.
        Never fabricates text or modifies factual characters.
        Returns: (enhanced_image_bytes, operations_applied)
        """
        operations_applied: List[str] = []
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes, []

            h, w = img.shape[:2]

            # 1. Rotation correction (90, 180, 270)
            if rotation_correction in (90, 180, 270):
                if rotation_correction == 90:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif rotation_correction == 180:
                    img = cv2.rotate(img, cv2.ROTATE_180)
                elif rotation_correction == 270:
                    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                operations_applied.append(f"Rotation correction ({rotation_correction}°)")
                h, w = img.shape[:2]

            # 2. Safe deterministic upscaling if small (< 1000px on min dimension)
            if upscale_if_small and min(h, w) < 900:
                scale = min(2.0, 1200.0 / min(h, w))
                if scale > 1.15:
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
                    operations_applied.append(f"Safe upscaling ({scale:.1f}x bicubic)")
                    h, w = img.shape[:2]

            # 3. Deskew using Hough line transform
            if deskew:
                gray_for_skew = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray_for_skew, 50, 150, apertureSize=3)
                lines = cv2.HoughLines(edges, 1, np.pi / 180, 120)
                if lines is not None and len(lines) > 0:
                    angles = []
                    for line in lines[:30]:
                        _, theta = line[0]
                        deg = (theta * 180 / np.pi) - 90
                        if -45 < deg < 45:
                            angles.append(deg)
                    if angles:
                        median_angle = float(np.median(angles))
                        if abs(median_angle) > 0.8:
                            center = (w // 2, h // 2)
                            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                            img = cv2.warpAffine(
                                img, M, (w, h),
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE
                            )
                            operations_applied.append(f"Deskew ({median_angle:.1f}°)")

            # 4. Shadow reduction & contrast enhancement (CLAHE)
            if enhance_contrast:
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                # Background illumination normalization via morphological closing
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
                background = cv2.morphologyEx(l, cv2.MORPH_CLOSE, kernel)
                # Divide to remove shadows
                diff = cv2.divide(l, background, scale=255)
                # Apply CLAHE
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                cl = clahe.apply(diff)
                limg = cv2.merge((cl, a, b))
                img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
                operations_applied.append("Shadow reduction & CLAHE contrast")

            # 5. Denoising
            if denoise:
                # Fast bilateral filter or non-local means depending on size
                if w * h > 2000000:
                    img = cv2.bilateralFilter(img, 9, 75, 75)
                else:
                    img = cv2.fastNlMeansDenoisingColored(img, None, 6, 6, 7, 21)
                operations_applied.append("Denoising")

            # 6. Sharpening (Unsharp Mask)
            if sharpen and not binarize:
                gaussian = cv2.GaussianBlur(img, (0, 0), 2.0)
                img = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
                operations_applied.append("Unsharp mask sharpening")

            # 7. Optional Binarization
            if binarize:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                thresh = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 15, 4
                )
                img = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                operations_applied.append("Adaptive Gaussian binarization")

            success, encoded_img = cv2.imencode(".png", img)
            if success:
                return encoded_img.tobytes(), operations_applied

            return image_bytes, operations_applied

        except Exception as e:
            return image_bytes, operations_applied

    @classmethod
    def generate_candidates(cls, image_bytes: bytes) -> Dict[str, bytes]:
        """
        Multi-version enhancement candidate generation:
        1. 'original': Raw source bytes
        2. 'enhanced_grayscale': CLAHE + Deskew + Denoise + Sharpen
        3. 'adaptive_threshold': Adaptive Gaussian binarization
        4. 'contrast_sharpened': High contrast with CLAHE
        """
        candidates: Dict[str, bytes] = {
            "original": image_bytes
        }

        # Candidate 2: Enhanced grayscale / CLAHE
        enh_bytes, _ = cls.enhance_image(
            image_bytes,
            deskew=True,
            denoise=True,
            enhance_contrast=True,
            sharpen=True,
            binarize=False
        )
        candidates["enhanced_grayscale"] = enh_bytes

        # Candidate 3: Adaptive threshold
        thresh_bytes, _ = cls.enhance_image(
            image_bytes,
            deskew=True,
            denoise=True,
            enhance_contrast=True,
            sharpen=False,
            binarize=True
        )
        candidates["adaptive_threshold"] = thresh_bytes

        # Candidate 4: Contrast sharpened
        sharp_bytes, _ = cls.enhance_image(
            image_bytes,
            deskew=True,
            denoise=False,
            enhance_contrast=True,
            sharpen=True,
            binarize=False
        )
        candidates["contrast_sharpened"] = sharp_bytes

        return candidates
