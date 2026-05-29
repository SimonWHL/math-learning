"""Local OCR using EasyOCR for handwritten answer recognition."""

from __future__ import annotations

import re
from typing import Optional

import cv2
import numpy as np

from math_learning.grader.checker import StudentAnswer

# Lazy-initialized singleton
_reader = None


def _get_reader():
    """Get or create EasyOCR reader instance."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def _preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Preprocess image for better OCR accuracy."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive thresholding for better text contrast
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )

    # Slight denoise
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

    return denoised


def _estimate_answer_regions(
    img_height: int, img_width: int, num_problems: int, cols: int = 4
) -> list[dict]:
    """Estimate bounding boxes for each problem's answer area.

    Returns list of dicts with 'id', 'bbox' (x1, y1, x2, y2).
    The answer area is the right portion of each cell (after '=').
    """
    top_margin = int(img_height * 0.15)
    bottom_margin = int(img_height * 0.05)
    left_margin = int(img_width * 0.05)
    right_margin = int(img_width * 0.05)

    usable_height = img_height - top_margin - bottom_margin
    usable_width = img_width - left_margin - right_margin

    rows = (num_problems + cols - 1) // cols
    cell_w = usable_width // cols
    cell_h = usable_height // rows

    regions = []
    for i in range(num_problems):
        row = i // cols
        col = i % cols
        # Answer area: right 50% of cell
        x1 = left_margin + col * cell_w + cell_w // 2
        y1 = top_margin + row * cell_h
        x2 = left_margin + (col + 1) * cell_w
        y2 = top_margin + (row + 1) * cell_h
        regions.append({"id": i + 1, "bbox": (x1, y1, x2, y2)})

    return regions


def _extract_number_from_text(text: str) -> Optional[str]:
    """Extract a number from OCR text."""
    # Remove common OCR artifacts
    cleaned = text.replace("=", "").replace("一", "").replace("—", "")
    # Find digit sequences
    match = re.search(r"\d+", cleaned)
    return match.group(0) if match else None


def _match_detections_to_regions(
    ocr_results: list, regions: list[dict]
) -> list[StudentAnswer]:
    """Match OCR text detections to problem answer regions.

    ocr_results: list of [(bbox, text, confidence), ...] from easyocr.
    """
    answers: list[StudentAnswer] = []

    for region in regions:
        x1, y1, x2, y2 = region["bbox"]

        # Find OCR detections that fall within this region
        region_texts: list[tuple[str, float, float, float]] = []
        for item in ocr_results:
            if not item:
                continue
            # easyocr format: (bbox, text, confidence)
            bbox = item[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = item[1]
            conf = item[2]

            # Center of detected text
            det_cx = sum(p[0] for p in bbox) / 4
            det_cy = sum(p[1] for p in bbox) / 4

            # Check if detection center is within the region (with margin)
            margin_x = (x2 - x1) * 0.3
            margin_y = (y2 - y1) * 0.3
            if (
                x1 - margin_x <= det_cx <= x2 + margin_x
                and y1 - margin_y <= det_cy <= y2 + margin_y
            ):
                region_texts.append((text, conf, det_cx, det_cy))

        # Sort by x position (left to right), then by confidence
        region_texts.sort(key=lambda t: (t[2], -t[1]))

        # For division problems: answer might be "商......余数"
        # Take the first number as answer, second as remainder
        all_numbers: list[str] = []
        for text, conf, _, _ in region_texts:
            num = _extract_number_from_text(text)
            if num:
                all_numbers.append(num)

        student_answer = all_numbers[0] if all_numbers else None
        student_remainder = all_numbers[1] if len(all_numbers) > 1 else None

        answers.append(
            StudentAnswer(
                id=region["id"],
                answer=student_answer,
                remainder=student_remainder,
            )
        )

    return answers


def ocr_local(image_bytes: bytes, num_problems: int, cols: int = 4) -> list[StudentAnswer]:
    """Run local OCR on a worksheet image.

    Args:
        image_bytes: Image file bytes.
        num_problems: Number of problems in the worksheet.
        cols: Number of columns in the grid layout.

    Returns:
        List of StudentAnswer with extracted answers.
    """
    processed = _preprocess_image(image_bytes)
    h, w = processed.shape[:2]

    reader = _get_reader()
    ocr_results_raw = reader.readtext(processed)

    # Convert easyocr format: [(bbox, text, confidence), ...]
    ocr_results = ocr_results_raw

    regions = _estimate_answer_regions(h, w, num_problems, cols)
    return _match_detections_to_regions(ocr_results, regions)
