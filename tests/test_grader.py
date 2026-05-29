"""Tests for the grader module (checker + API)."""

import io
import json

import cv2
import numpy as np
import pytest

from math_learning.core.generator import Operation, Problem, generate_problems
from math_learning.grader.checker import (
    GradeResult,
    Score,
    StudentAnswer,
    annotate_image,
    check_answers,
    compute_score,
)


def _make_test_image(width: int = 800, height: int = 1000) -> bytes:
    """Create a simple test image that looks like a worksheet."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    # Draw some text-like marks
    cv2.putText(img, "Math Test", (300, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    _, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()


class TestCheckAnswers:
    """Tests for answer checking logic."""

    def test_all_correct_addition(self):
        problems = [
            Problem(id=1, operand_a=23, operand_b=45, operation=Operation.ADD, answer=68),
            Problem(id=2, operand_a=10, operand_b=20, operation=Operation.ADD, answer=30),
        ]
        student = [
            StudentAnswer(id=1, answer="68"),
            StudentAnswer(id=2, answer="30"),
        ]
        results = check_answers(problems, student)
        assert all(r.is_correct for r in results)

    def test_wrong_answer(self):
        problems = [
            Problem(id=1, operand_a=23, operand_b=45, operation=Operation.ADD, answer=68),
        ]
        student = [StudentAnswer(id=1, answer="58")]
        results = check_answers(problems, student)
        assert not results[0].is_correct

    def test_unanswered(self):
        problems = [
            Problem(id=1, operand_a=10, operand_b=20, operation=Operation.ADD, answer=30),
        ]
        student = [StudentAnswer(id=1, answer=None)]
        results = check_answers(problems, student)
        assert not results[0].is_correct

    def test_division_correct(self):
        problems = [
            Problem(id=1, operand_a=23, operand_b=5, operation=Operation.DIVIDE_REMAINDER, answer=4, remainder=3),
        ]
        student = [StudentAnswer(id=1, answer="4", remainder="3")]
        results = check_answers(problems, student)
        assert results[0].is_correct

    def test_division_wrong_remainder(self):
        problems = [
            Problem(id=1, operand_a=23, operand_b=5, operation=Operation.DIVIDE_REMAINDER, answer=4, remainder=3),
        ]
        student = [StudentAnswer(id=1, answer="4", remainder="2")]
        results = check_answers(problems, student)
        assert not results[0].is_correct

    def test_division_missing_remainder(self):
        problems = [
            Problem(id=1, operand_a=23, operand_b=5, operation=Operation.DIVIDE_REMAINDER, answer=4, remainder=3),
        ]
        student = [StudentAnswer(id=1, answer="4", remainder=None)]
        results = check_answers(problems, student)
        assert not results[0].is_correct

    def test_mixed_types(self):
        problems = generate_problems(count=20, seed=42)
        # All correct
        student = [
            StudentAnswer(
                id=p.id,
                answer=str(p.answer),
                remainder=str(p.remainder) if p.remainder is not None else None,
            )
            for p in problems
        ]
        results = check_answers(problems, student)
        assert all(r.is_correct for r in results)


class TestComputeScore:
    def test_perfect_score(self):
        results = [GradeResult(id=1, expression="1+1", correct_answer=2, correct_remainder=None,
                               student_answer="2", student_remainder=None, is_correct=True)]
        score = compute_score(results)
        assert score.total == 1
        assert score.correct == 1
        assert score.wrong == 0
        assert score.accuracy == 100.0

    def test_zero_score(self):
        results = [
            GradeResult(id=i, expression="", correct_answer=0, correct_remainder=None,
                        student_answer="0", student_remainder=None, is_correct=False)
            for i in range(5)
        ]
        score = compute_score(results)
        assert score.correct == 0
        assert score.accuracy == 0.0


class TestAnnotateImage:
    def test_annotates_valid_image(self):
        img_bytes = _make_test_image()
        results = [
            GradeResult(id=1, expression="1+1=____", correct_answer=2, correct_remainder=None,
                        student_answer="2", student_remainder=None, is_correct=True),
            GradeResult(id=2, expression="3+4=____", correct_answer=7, correct_remainder=None,
                        student_answer="5", student_remainder=None, is_correct=False),
        ]
        annotated_b64 = annotate_image(img_bytes, results)
        assert len(annotated_b64) > 100  # Should produce a non-trivial base64 string

    def test_invalid_image_raises(self):
        results = [
            GradeResult(id=1, expression="1+1=____", correct_answer=2, correct_remainder=None,
                        student_answer="2", student_remainder=None, is_correct=True),
        ]
        with pytest.raises(ValueError):
            annotate_image(b"not an image", results)


class TestGradeAPI:
    """Tests for grading API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from math_learning.web.main import app
        return TestClient(app)

    def test_recheck_endpoint(self, client):
        """Test the recheck API with manual answers."""
        resp = client.post("/api/grade/recheck", json={
            "problems": [
                {"id": 1, "student_answer": "68", "student_remainder": None},
                {"id": 2, "student_answer": "53", "student_remainder": None},
            ],
            "count": 2,
            "operations": ["add", "subtract"],
            "seed": 42,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "problems" in data
        assert "score" in data
        assert data["ocr_mode_used"] == "manual"
        assert data["score"]["total"] == 2

    def test_recheck_with_division(self, client):
        resp = client.post("/api/grade/recheck", json={
            "problems": [
                {"id": 1, "student_answer": "4", "student_remainder": "3"},
            ],
            "count": 1,
            "operations": ["divide_remainder"],
            "seed": 42,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["problems"][0]["correct_remainder"] is not None

    def test_ocr_config_get(self, client):
        resp = client.get("/api/config/ocr")
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert "base_url" in data
        assert "model" in data

    def test_ocr_config_update(self, client):
        resp = client.post("/api/config/ocr", json={
            "api_key": "test-key-12345678",
            "model": "gpt-4o-mini",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "****" in data["api_key"]  # Key should be masked
        assert data["model"] == "gpt-4o-mini"

    def test_grade_no_image_fails(self, client):
        """Grade endpoint should fail without image."""
        resp = client.post("/api/grade", data={
            "count": "10",
            "operations": '["add"]',
        })
        assert resp.status_code == 422  # Missing required file
