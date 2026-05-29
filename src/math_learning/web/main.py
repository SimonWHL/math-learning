"""FastAPI application for math problem generation and grading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from math_learning.core.generator import Operation, generate_problems
from math_learning.generator.word import generate_word
from math_learning.grader.checker import (
    GradeResult,
    Score,
    StudentAnswer,
    annotate_image,
    check_answers,
    compute_score,
)
from math_learning.grader.ocr_cloud import get_config, ocr_cloud, set_config

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


# --- Grading Models ---


class GradeResultOut(BaseModel):
    id: int
    expression: str
    correct_answer: int
    correct_remainder: Optional[int] = None
    student_answer: Optional[str] = None
    student_remainder: Optional[str] = None
    is_correct: bool


class ScoreOut(BaseModel):
    total: int
    correct: int
    wrong: int
    accuracy: float


class GradeResponse(BaseModel):
    problems: list[GradeResultOut]
    annotated_image: str
    score: ScoreOut
    ocr_mode_used: str


class RecheckStudentAnswer(BaseModel):
    id: int
    student_answer: Optional[str] = None
    student_remainder: Optional[str] = None


class RecheckRequest(BaseModel):
    problems: list[RecheckStudentAnswer]
    count: int
    operations: list[Operation]
    seed: Optional[int] = None


class OcrConfigUpdate(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""


# --- Grading Endpoints ---


@app.post("/api/grade", response_model=GradeResponse)
async def grade(
    image: UploadFile = File(...),
    count: int = Form(...),
    operations: str = Form(default='["add","subtract"]'),
    seed: Optional[int] = Form(default=None),
    ocr_mode: str = Form(default="local"),
    api_key: Optional[str] = Form(default=None),
    base_url: Optional[str] = Form(default=None),
    model: Optional[str] = Form(default=None),
) -> GradeResponse:
    """Grade a student worksheet photo."""
    # Parse operations
    try:
        ops_list = json.loads(operations)
        ops = [Operation(op) for op in ops_list]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid operations: {e}")

    # Generate problems with same seed
    try:
        problems = generate_problems(count=count, operations=ops, seed=seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Read image
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

    # Run OCR
    mode_used = ocr_mode
    if ocr_mode == "cloud":
        try:
            student_answers = await ocr_cloud(
                image_bytes, problems,
                api_key=api_key, base_url=base_url, model=model,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Cloud OCR failed: {e}")
    else:
        try:
            from math_learning.grader.ocr_local import ocr_local
            student_answers = ocr_local(image_bytes, len(problems))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Local OCR failed: {e}")

    # Check answers
    results = check_answers(problems, student_answers)
    score = compute_score(results)

    # Annotate image
    try:
        annotated = annotate_image(image_bytes, results)
    except Exception as e:
        annotated = ""

    return GradeResponse(
        problems=[
            GradeResultOut(
                id=r.id,
                expression=r.expression,
                correct_answer=r.correct_answer,
                correct_remainder=r.correct_remainder,
                student_answer=r.student_answer,
                student_remainder=r.student_remainder,
                is_correct=r.is_correct,
            )
            for r in results
        ],
        annotated_image=annotated,
        score=ScoreOut(
            total=score.total,
            correct=score.correct,
            wrong=score.wrong,
            accuracy=score.accuracy,
        ),
        ocr_mode_used=mode_used,
    )


@app.post("/api/grade/recheck", response_model=GradeResponse)
async def recheck(req: RecheckRequest) -> GradeResponse:
    """Recheck with manually corrected student answers (no re-OCR)."""
    try:
        problems = generate_problems(
            count=req.count, operations=req.operations, seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    student_answers = [
        StudentAnswer(id=p.id, answer=p.student_answer, remainder=p.student_remainder)
        for p in req.problems
    ]

    results = check_answers(problems, student_answers)
    score = compute_score(results)

    return GradeResponse(
        problems=[
            GradeResultOut(
                id=r.id,
                expression=r.expression,
                correct_answer=r.correct_answer,
                correct_remainder=r.correct_remainder,
                student_answer=r.student_answer,
                student_remainder=r.student_remainder,
                is_correct=r.is_correct,
            )
            for r in results
        ],
        annotated_image="",
        score=ScoreOut(
            total=score.total,
            correct=score.correct,
            wrong=score.wrong,
            accuracy=score.accuracy,
        ),
        ocr_mode_used="manual",
    )


@app.get("/api/config/ocr")
async def get_ocr_config() -> dict:
    """Get current OCR cloud config (key masked)."""
    return get_config()


@app.post("/api/config/ocr")
async def update_ocr_config(req: OcrConfigUpdate) -> dict:
    """Update OCR cloud config."""
    return set_config(api_key=req.api_key, base_url=req.base_url, model=req.model)


# Serve frontend static files in production
_frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    # Mount static assets (js/css/images) under /assets
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve frontend for all GET requests (SPA fallback)."""
        # Try to serve the exact file first
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        # Fall back to index.html for SPA routing
        return FileResponse(str(_frontend_dist / "index.html"))
