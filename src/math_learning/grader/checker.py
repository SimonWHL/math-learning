"""Answer checker and image annotation for grading."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from math_learning.core.generator import Operation, Problem


@dataclass
class StudentAnswer:
    """A student's answer for a single problem."""

    id: int
    answer: Optional[str] = None  # raw text from OCR
    remainder: Optional[str] = None  # for division problems


@dataclass
class GradeResult:
    """Grading result for a single problem."""

    id: int
    expression: str
    correct_answer: int
    correct_remainder: Optional[int]
    student_answer: Optional[str]
    student_remainder: Optional[str]
    is_correct: bool


@dataclass
class Score:
    """Overall score summary."""

    total: int
    correct: int
    wrong: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total * 100 if self.total > 0 else 0.0


def _parse_int(text: Optional[str]) -> Optional[int]:
    """Try to parse an integer from text, return None if failed."""
    if text is None:
        return None
    # Extract digits only
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return None
    return int(digits)


def check_answers(
    problems: list[Problem],
    student_answers: list[StudentAnswer],
) -> list[GradeResult]:
    """Compare student answers with correct answers.

    Args:
        problems: List of generated problems with correct answers.
        student_answers: List of student answers from OCR.

    Returns:
        List of GradeResult for each problem.
    """
    results: list[GradeResult] = []
    answer_map = {sa.id: sa for sa in student_answers}

    for problem in problems:
        sa = answer_map.get(problem.id)
        student_ans_text = sa.answer if sa else None
        student_rem_text = sa.remainder if sa else None

        is_correct = False
        if sa and student_ans_text is not None:
            parsed_ans = _parse_int(student_ans_text)
            if parsed_ans is not None and parsed_ans == problem.answer:
                if problem.operation == Operation.DIVIDE_REMAINDER:
                    parsed_rem = _parse_int(student_rem_text)
                    is_correct = (
                        parsed_rem is not None and parsed_rem == problem.remainder
                    )
                else:
                    is_correct = True

        results.append(
            GradeResult(
                id=problem.id,
                expression=problem.expression,
                correct_answer=problem.answer,
                correct_remainder=problem.remainder,
                student_answer=student_ans_text,
                student_remainder=student_rem_text,
                is_correct=is_correct,
            )
        )

    return results


def compute_score(results: list[GradeResult]) -> Score:
    """Compute score from grading results."""
    correct = sum(1 for r in results if r.is_correct)
    return Score(total=len(results), correct=correct, wrong=len(results) - correct)


# --- Image Annotation ---

# Colors (BGR)
GREEN = (0, 180, 0)
RED = (0, 0, 220)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _draw_checkmark(img: np.ndarray, center: tuple[int, int], size: int = 20) -> None:
    """Draw a green checkmark at center."""
    x, y = center
    pts = np.array(
        [[x - size, y], [x - size // 3, y + size], [x + size, y - size]],
        dtype=np.int32,
    )
    cv2.polylines(img, [pts], False, GREEN, 3, cv2.LINE_AA)


def _draw_cross(img: np.ndarray, center: tuple[int, int], size: int = 16) -> None:
    """Draw a red cross at center."""
    x, y = center
    cv2.line(img, (x - size, y - size), (x + size, y + size), RED, 3, cv2.LINE_AA)
    cv2.line(img, (x + size, y - size), (x - size, y + size), RED, 3, cv2.LINE_AA)


def _estimate_cell_positions(
    img_height: int, img_width: int, num_problems: int, cols: int = 4
) -> list[tuple[int, int]]:
    """Estimate center positions of each problem cell in the image.

    Assumes the worksheet has a title area at top and problems in a grid.
    """
    # Skip title area (top ~15% of image)
    top_margin = int(img_height * 0.15)
    bottom_margin = int(img_height * 0.05)
    left_margin = int(img_width * 0.05)
    right_margin = int(img_width * 0.05)

    usable_height = img_height - top_margin - bottom_margin
    usable_width = img_width - left_margin - right_margin

    rows = (num_problems + cols - 1) // cols
    cell_w = usable_width // cols
    cell_h = usable_height // rows

    positions = []
    for i in range(num_problems):
        row = i // cols
        col = i % cols
        cx = left_margin + col * cell_w + cell_w // 2
        cy = top_margin + row * cell_h + cell_h // 2
        positions.append((cx, cy))

    return positions


def annotate_image(
    image_bytes: bytes,
    results: list[GradeResult],
    cols: int = 4,
) -> str:
    """Annotate the image with grading marks.

    Args:
        image_bytes: Original image as bytes.
        results: Grading results with correct/wrong info.
        cols: Number of columns in the worksheet grid.

    Returns:
        Base64-encoded annotated image (JPEG).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")

    h, w = img.shape[:2]
    positions = _estimate_cell_positions(h, w, len(results), cols)

    for i, result in enumerate(results):
        if i >= len(positions):
            break
        cx, cy = positions[i]
        # Mark slightly to the right of center (where the answer area is)
        mark_x = cx + w // (cols * 3)
        mark_y = cy

        if result.is_correct:
            _draw_checkmark(img, (mark_x, mark_y))
        else:
            _draw_cross(img, (mark_x, mark_y))
            # Write correct answer in red
            correct_text = str(result.correct_answer)
            if result.correct_remainder is not None:
                correct_text = f"{result.correct_answer}...{result.correct_remainder}"
            cv2.putText(
                img,
                correct_text,
                (mark_x + 20, mark_y + 6),
                FONT,
                0.5,
                RED,
                2,
                cv2.LINE_AA,
            )

    # Draw score at bottom
    score = compute_score(results)
    score_text = f"Score: {score.correct}/{score.total} ({score.accuracy:.0f}%)"
    cv2.putText(img, score_text, (w - 300, h - 20), FONT, 0.8, RED, 2, cv2.LINE_AA)

    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode("utf-8")
