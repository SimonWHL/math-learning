"""Math problem generator for arithmetic within 100."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Operation(str, Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    DIVIDE_REMAINDER = "divide_remainder"


@dataclass
class Problem:
    """A single math problem."""

    id: int
    operand_a: int
    operand_b: int
    operation: Operation
    answer: int
    remainder: Optional[int] = None

    @property
    def expression(self) -> str:
        """Return formatted expression."""
        if self.operation == Operation.ADD:
            return f"{self.operand_a} + {self.operand_b} = ____"
        elif self.operation == Operation.SUBTRACT:
            return f"{self.operand_a} - {self.operand_b} = ____"
        else:
            return f"{self.operand_a} ÷ {self.operand_b} = ____ …… ____"


def _generate_addition(rng: random.Random) -> Problem:
    """Generate an addition problem where a + b <= 100, a >= 1, b >= 1."""
    a = rng.randint(1, 99)
    b = rng.randint(1, 100 - a)
    return Problem(
        id=0,
        operand_a=a,
        operand_b=b,
        operation=Operation.ADD,
        answer=a + b,
    )


def _generate_subtraction(rng: random.Random) -> Problem:
    """Generate a subtraction problem where a - b >= 0, a >= 1, b >= 1."""
    a = rng.randint(2, 100)
    b = rng.randint(1, a)
    return Problem(
        id=0,
        operand_a=a,
        operand_b=b,
        operation=Operation.SUBTRACT,
        answer=a - b,
    )


def _generate_divide_remainder(rng: random.Random) -> Problem:
    """Generate a division-with-remainder problem.

    Constraints: divisor (b) in [2, 9], quotient in [1, 9], remainder in [1, b-1].
    dividend (a) = b * quotient + remainder.
    """
    b = rng.randint(2, 9)
    quotient = rng.randint(1, 9)
    r = rng.randint(1, b - 1)
    a = b * quotient + r
    return Problem(
        id=0,
        operand_a=a,
        operand_b=b,
        operation=Operation.DIVIDE_REMAINDER,
        answer=quotient,
        remainder=r,
    )


_GENERATORS = {
    Operation.ADD: _generate_addition,
    Operation.SUBTRACT: _generate_subtraction,
    Operation.DIVIDE_REMAINDER: _generate_divide_remainder,
}


def generate_problems(
    count: int,
    operations: Optional[list[Operation]] = None,
    seed: Optional[int] = None,
) -> list[Problem]:
    """Generate a list of math problems.

    Args:
        count: Number of problems to generate (1-200).
        operations: List of operation types. Defaults to both add and subtract.
        seed: Random seed for reproducibility. None for random.

    Returns:
        List of Problem instances with sequential IDs.

    Raises:
        ValueError: If count is out of range or operations list is empty.
    """
    if not 1 <= count <= 200:
        raise ValueError(f"count must be between 1 and 200, got {count}")

    if operations is None:
        operations = [Operation.ADD, Operation.SUBTRACT]

    if not operations:
        raise ValueError("operations list cannot be empty")

    rng = random.Random(seed)
    problems: list[Problem] = []

    for i in range(count):
        op = rng.choice(operations)
        problem = _GENERATORS[op](rng)
        problem.id = i + 1
        problems.append(problem)

    return problems
