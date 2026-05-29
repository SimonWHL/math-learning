"""Tests for math problem generator."""

import pytest

from math_learning.core.generator import Operation, Problem, generate_problems
from math_learning.generator.word import generate_word


class TestGenerateProblems:
    """Tests for the core problem generator."""

    def test_default_count(self):
        problems = generate_problems(count=20)
        assert len(problems) == 20

    def test_custom_count(self):
        for n in [1, 10, 50, 100, 200]:
            problems = generate_problems(count=n)
            assert len(problems) == n

    def test_count_out_of_range(self):
        with pytest.raises(ValueError):
            generate_problems(count=0)
        with pytest.raises(ValueError):
            generate_problems(count=201)

    def test_empty_operations(self):
        with pytest.raises(ValueError):
            generate_problems(count=10, operations=[])

    def test_addition_range(self):
        """All addition problems should have a + b <= 100, a >= 1, b >= 1."""
        problems = generate_problems(count=200, operations=[Operation.ADD], seed=42)
        for p in problems:
            assert p.operation == Operation.ADD
            assert p.operand_a >= 1
            assert p.operand_b >= 1
            assert p.answer == p.operand_a + p.operand_b
            assert p.answer <= 100

    def test_subtraction_non_negative(self):
        """All subtraction results should be >= 0, a >= b >= 1."""
        problems = generate_problems(count=200, operations=[Operation.SUBTRACT], seed=42)
        for p in problems:
            assert p.operation == Operation.SUBTRACT
            assert p.operand_a >= p.operand_b
            assert p.operand_b >= 1
            assert p.answer == p.operand_a - p.operand_b
            assert p.answer >= 0

    def test_mixed_operations(self):
        """Mixed mode should produce both types."""
        problems = generate_problems(count=100, seed=42)
        ops = {p.operation for p in problems}
        assert Operation.ADD in ops
        assert Operation.SUBTRACT in ops

    def test_sequential_ids(self):
        problems = generate_problems(count=10)
        for i, p in enumerate(problems):
            assert p.id == i + 1

    def test_seed_reproducibility(self):
        p1 = generate_problems(count=20, seed=123)
        p2 = generate_problems(count=20, seed=123)
        assert p1 == p2

    def test_expression_format_add(self):
        p = Problem(id=1, operand_a=23, operand_b=45, operation=Operation.ADD, answer=68)
        assert p.expression == "23 + 45 = ____"

    def test_expression_format_subtract(self):
        p = Problem(id=1, operand_a=87, operand_b=34, operation=Operation.SUBTRACT, answer=53)
        assert p.expression == "87 - 34 = ____"

    def test_divide_remainder_constraints(self):
        """Divisor in [2,9], quotient in [1,9], remainder in [1, divisor-1]."""
        problems = generate_problems(count=200, operations=[Operation.DIVIDE_REMAINDER], seed=42)
        for p in problems:
            assert p.operation == Operation.DIVIDE_REMAINDER
            assert 2 <= p.operand_b <= 9, f"divisor {p.operand_b} out of range"
            assert 1 <= p.answer <= 9, f"quotient {p.answer} out of range"
            assert p.remainder is not None
            assert 1 <= p.remainder <= p.operand_b - 1
            # Verify: dividend = divisor * quotient + remainder
            assert p.operand_a == p.operand_b * p.answer + p.remainder

    def test_divide_remainder_expression(self):
        p = Problem(id=1, operand_a=23, operand_b=5, operation=Operation.DIVIDE_REMAINDER, answer=4, remainder=3)
        assert "÷" in p.expression
        assert "……" in p.expression


class TestGenerateWord:
    """Tests for Word document generation."""

    def test_generates_valid_docx(self):
        problems = generate_problems(count=20, seed=42)
        buffer = generate_word(problems)
        data = buffer.read()
        # DOCX files start with PK (ZIP magic bytes)
        assert data[:2] == b"PK"
        assert len(data) > 100

    def test_empty_problems(self):
        buffer = generate_word([])
        data = buffer.read()
        assert data[:2] == b"PK"

    def test_custom_title(self):
        problems = generate_problems(count=5, seed=1)
        buffer = generate_word(problems, title="测试标题")
        assert buffer.read()[:2] == b"PK"

    def test_large_problem_set(self):
        problems = generate_problems(count=100, seed=42)
        buffer = generate_word(problems)
        data = buffer.read()
        assert len(data) > 1000


class TestAPI:
    """Tests for FastAPI endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from math_learning.web.main import app
        return TestClient(app)

    def test_generate_endpoint(self, client):
        resp = client.post("/api/generate", json={"count": 10, "operations": ["add"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 10
        assert len(data["problems"]) == 10
        assert "+" in data["problems"][0]["expression"]

    def test_generate_default(self, client):
        resp = client.post("/api/generate", json={})
        assert resp.status_code == 200
        assert resp.json()["count"] == 20

    def test_generate_invalid_count(self, client):
        resp = client.post("/api/generate", json={"count": 0})
        assert resp.status_code == 422

    def test_download_endpoint(self, client):
        resp = client.post("/api/download", json={"count": 10})
        assert resp.status_code == 200
        assert "wordprocessingml" in resp.headers["content-type"]
        assert resp.content[:2] == b"PK"

    def test_download_with_seed(self, client):
        resp = client.post("/api/download", json={"count": 5, "seed": 42})
        assert resp.status_code == 200
        assert len(resp.content) > 100
