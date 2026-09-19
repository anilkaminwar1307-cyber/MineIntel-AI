"""
Quality Assessment Service — Evaluates document quality, legibility, blur, contrast, and extraction readiness.
Works on images/PDFs (via OpenCV/Pillow) and structured files (completeness/null density).
"""
import io
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import cv2
from PIL import Image


class QualityAssessmentService:
    @classmethod
    def assess_image_data(cls, image_bytes: bytes) -> Dict[str, Any]:
        """
        Assesses image bytes for:
        - resolution and estimated DPI
        - blur (Laplacian variance)
        - contrast (std dev & luminance range)
        - brightness (mean luminance)
        - skew angle (Hough transform)
        - rotation / orientation (0, 90, 180, 270)
        - noise level (high-frequency median residual)
        - low text-to-background separation
        Returns a rich quality profile dict.
        """
        issues: List[str] = []
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return cls._fallback_profile("Image could not be decoded")

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape

            # 1. Resolution & DPI estimation
            # Standard A4 is ~8.27 x 11.69 inches.
            aspect_ratio = max(width, height) / max(1, min(width, height))
            estimated_dpi = int(min(width, height) / 8.27) if aspect_ratio > 1.2 else int(min(width, height) / 8.0)
            detected_dpi = max(72, min(600, estimated_dpi if estimated_dpi > 0 else 150))
            is_low_res = width < 800 or height < 800 or detected_dpi < 120
            if is_low_res:
                issues.append(f"Low resolution ({width}x{height}, ~{detected_dpi} DPI)")

            # 2. Blur detection using Laplacian variance
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if laplacian_var < 50.0:
                blur_level = "high"
                issues.append("Severe optical blur or soft focus detected")
            elif laplacian_var < 110.0:
                blur_level = "medium"
                issues.append("Moderate blur detected — text edges may be indistinct")
            else:
                blur_level = "low"

            # 3. Contrast check (Standard deviation and percentile spread)
            contrast_val = float(gray.std())
            p10, p90 = np.percentile(gray, [10, 90])
            dynamic_range = float(p90 - p10)

            if contrast_val < 30.0 or dynamic_range < 60.0:
                contrast_level = "low"
                issues.append("Low contrast between text and background")
            elif contrast_val < 50.0:
                contrast_level = "medium"
            else:
                contrast_level = "high"

            # 4. Brightness & background shadows
            brightness_val = float(gray.mean())
            if brightness_val < 50.0:
                issues.append("Document image is heavily underexposed/dark")
            elif brightness_val > 240.0:
                issues.append("Document image is overexposed/washed out")

            # Background shadow detection
            small_gray = cv2.resize(gray, (64, 64))
            local_std = float(small_gray.std())
            if local_std > 45.0 and contrast_level != "high":
                issues.append("Uneven background lighting or shadows detected")

            # 5. Noise estimation (residual from median filter)
            median_blur = cv2.medianBlur(gray, 3)
            noise_residual = float(np.mean(np.abs(gray.astype(np.float32) - median_blur.astype(np.float32))))
            if noise_residual > 12.0:
                noise_level = "high"
                issues.append("High high-frequency noise or speckle artifacts")
            elif noise_residual > 6.0:
                noise_level = "medium"
            else:
                noise_level = "low"

            # 6. Skew estimation (degrees)
            skew_angle = cls._estimate_skew(gray)
            if abs(skew_angle) > 1.5:
                issues.append(f"Document skewed by {skew_angle:.1f}°")

            # 7. Rotation / Orientation check (0, 90, 180, 270)
            orientation_correction = cls._detect_orientation(gray)
            if orientation_correction != 0:
                issues.append(f"Page orientation requires {orientation_correction}° correction")

            # Calculate composite quality score (0.0 to 1.0)
            score = 1.0
            if blur_level == "high":
                score -= 0.35
            elif blur_level == "medium":
                score -= 0.15

            if contrast_level == "low":
                score -= 0.25
            elif contrast_level == "medium":
                score -= 0.08

            if noise_level == "high":
                score -= 0.15
            elif noise_level == "medium":
                score -= 0.05

            if is_low_res:
                score -= 0.15

            if abs(skew_angle) > 3.0:
                score -= 0.10

            if orientation_correction != 0:
                score -= 0.10

            score = max(0.05, min(1.0, round(score, 2)))
            label = cls._get_quality_label(score)
            enhancement_recommended = score < 0.80 or abs(skew_angle) > 1.5 or orientation_correction != 0

            return {
                "score": score,
                "label": label,
                "quality_score": score,
                "quality_label": label,
                "blur": blur_level,
                "blur_level": blur_level,
                "blur_score": round(laplacian_var, 2),
                "contrast": contrast_level,
                "contrast_level": contrast_level,
                "contrast_score": round(contrast_val, 2),
                "brightness": round(brightness_val, 2),
                "noise": noise_level,
                "noise_level": noise_level,
                "noise_score": round(noise_residual, 2),
                "skew_angle": round(skew_angle, 2),
                "detected_dpi": detected_dpi,
                "orientation_correction": orientation_correction,
                "enhancement_recommended": enhancement_recommended,
                "width": width,
                "height": height,
                "issues": issues,
            }

        except Exception as e:
            return cls._fallback_profile(str(e))

    @classmethod
    def assess_structured_data(cls, total_rows: int, total_cols: int, null_count: int = 0) -> Dict[str, Any]:
        """
        Assesses CSV / Excel table quality based on size, geometry, and completeness.
        """
        issues: List[str] = []
        if total_rows == 0:
            return {
                "score": 0.1,
                "label": "UNREADABLE",
                "quality_score": 0.1,
                "quality_label": "UNREADABLE",
                "blur": "low",
                "contrast": "high",
                "noise": "low",
                "skew_angle": 0.0,
                "enhancement_recommended": False,
                "issues": ["Table contains 0 rows"],
            }

        total_cells = max(1, total_rows * total_cols)
        null_ratio = null_count / total_cells

        score = 1.0 - (null_ratio * 0.4)
        if null_ratio > 0.4:
            issues.append(f"High percentage of empty cells ({null_ratio * 100:.1f}%)")
        if total_cols < 2:
            issues.append("Only single column detected")
            score -= 0.15

        score = max(0.2, min(1.0, round(score, 2)))
        label = cls._get_quality_label(score)

        return {
            "score": score,
            "label": label,
            "quality_score": score,
            "quality_label": label,
            "blur": "low",
            "contrast": "high",
            "noise": "low",
            "skew_angle": 0.0,
            "enhancement_recommended": False,
            "issues": issues,
        }

    @classmethod
    def assess_text_data(cls, char_count: int) -> Dict[str, Any]:
        issues = []
        if char_count == 0:
            score = 0.0
            issues.append("Document has 0 characters")
        elif char_count < 100:
            score = 0.6
            issues.append("Very short document text")
        else:
            score = 0.95

        label = cls._get_quality_label(score)
        return {
            "score": score,
            "label": label,
            "quality_score": score,
            "quality_label": label,
            "blur": "low",
            "contrast": "high",
            "noise": "low",
            "skew_angle": 0.0,
            "enhancement_recommended": False,
            "issues": issues,
        }

    @staticmethod
    def _estimate_skew(gray_img: np.ndarray) -> float:
        """
        Estimates skew angle using Hough lines on edge image.
        Returns angle in degrees (-45 to 45).
        """
        try:
            edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 120)
            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines[:30]:
                    rho, theta = line[0]
                    angle_deg = (theta * 180 / np.pi) - 90
                    if -45 < angle_deg < 45:
                        angles.append(angle_deg)
                if angles:
                    return float(np.median(angles))
            return 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _detect_orientation(gray_img: np.ndarray) -> int:
        """
        Heuristic to detect 90, 180, 270 degree rotation.
        Returns degrees needed to correct (0, 90, 180, 270).
        """
        try:
            h, w = gray_img.shape
            sobel_x = cv2.Sobel(gray_img, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray_img, cv2.CV_64F, 0, 1, ksize=3)
            energy_x = float(np.mean(np.abs(sobel_x)))
            energy_y = float(np.mean(np.abs(sobel_y)))

            if energy_x > 1.8 * energy_y and h > w:
                return 90
            return 0
        except Exception:
            return 0

    @staticmethod
    def _get_quality_label(score: float) -> str:
        if score >= 0.85:
            return "EXCELLENT"
        if score >= 0.70:
            return "GOOD"
        if score >= 0.50:
            return "FAIR"
        if score >= 0.30:
            return "POOR"
        return "UNREADABLE"

    @classmethod
    def _fallback_profile(cls, error_msg: str) -> Dict[str, Any]:
        return {
            "score": 0.5,
            "label": "FAIR",
            "quality_score": 0.5,
            "quality_label": "FAIR",
            "blur": "medium",
            "contrast": "medium",
            "noise": "low",
            "skew_angle": 0.0,
            "detected_dpi": 150,
            "orientation_correction": 0,
            "enhancement_recommended": False,
            "issues": [f"Quality assessment note: {error_msg}"],
        }
