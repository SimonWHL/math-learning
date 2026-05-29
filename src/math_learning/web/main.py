"""FastAPI application for math problem generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from math_learning.core.generator import Operation, generate_problems
from math_learning.generator.word import generate_word

app = FastAPI(title="Math Learning API", version="0.1.0")

# CORS for dev frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    """Request body for problem generation."""

    count: int = Field(default=20, ge=1, le=200, description="Number of problems")
    operations: list[Operation] = Field(
        default=[Operation.ADD, Operation.SUBTRACT],
        description="Operation types to include",
    )
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class ProblemOut(BaseModel):
    """Single problem in API response."""

    id: int
    expression: str
    answer: int
    remainder: Optional[int] = None


class GenerateResponse(BaseModel):
    """Response with generated problems."""

    problems: list[ProblemOut]
    count: int


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    """Generate math problems and return JSON for preview."""
    try:
        problems = generate_problems(
            count=req.count,
            operations=req.operations,
            seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return GenerateResponse(
        problems=[
            ProblemOut(id=p.id, expression=p.expression, answer=p.answer, remainder=p.remainder)
            for p in problems
        ],
        count=len(problems),
    )


@app.post("/api/download")
async def download(req: GenerateRequest) -> StreamingResponse:
    """Generate a Word document and return it as a download."""
    try:
        problems = generate_problems(
            count=req.count,
            operations=req.operations,
            seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    buffer = generate_word(problems)
    encoded_filename = quote(f"口算练习_{len(problems)}题.docx")

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


# Serve frontend static files in production
_frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
