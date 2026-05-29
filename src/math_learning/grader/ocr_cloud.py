"""Cloud AI Vision model for handwritten answer recognition.

Supports OpenAI-compatible APIs (GPT-4o, Claude, etc.).
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

import httpx

from math_learning.core.generator import Problem
from math_learning.grader.checker import StudentAnswer

# Default config (can be overridden via set_config)
_config: dict = {
    "api_key": os.environ.get("AI_VISION_API_KEY", ""),
    "base_url": os.environ.get("AI_VISION_BASE_URL", "https://api.openai.com/v1"),
    "model": os.environ.get("AI_VISION_MODEL", "gpt-4o"),
}


def set_config(api_key: str = "", base_url: str = "", model: str = "") -> dict:
    """Update cloud OCR config. Returns current config (keys masked)."""
    if api_key:
        _config["api_key"] = api_key
    if base_url:
        _config["base_url"] = base_url
    if model:
        _config["model"] = model
    return get_config()


def get_config() -> dict:
    """Return config with masked API key."""
    masked = {**_config}
    if masked["api_key"]:
        key = masked["api_key"]
        masked["api_key"] = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
    return masked


_SYSTEM_PROMPT = """你是一个口算试卷批改助手。用户会给你一张学生做完的口算试卷照片和题目列表。
请识别每道题空白处学生手写的数字答案，以 JSON 格式返回。

对于加减法题，每道题只有一个答案。
对于有余数除法题，有商和余数两个答案。

请严格按照以下 JSON 格式返回，不要包含其他文字：
{
  "answers": [
    {"id": 1, "answer": "68"},
    {"id": 2, "answer": "35", "remainder": "3"}
  ]
}

如果某道题学生没有作答或无法识别，answer 设为 null。"""


def _build_user_message(
    image_b64: str, problems: list[Problem]
) -> list[dict]:
    """Build the user message with image and problem list."""
    problem_lines = []
    for p in problems:
        line = f"第{p.id}题: {p.expression}"
        if p.remainder is not None:
            line += " (有余数除法，需填商和余数)"
        problem_lines.append(line)

    text = "以下是题目列表，请识别照片中每道题的学生答案：\n" + "\n".join(problem_lines)

    return [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        },
        {"type": "text", "text": text},
    ]


async def ocr_cloud(
    image_bytes: bytes,
    problems: list[Problem],
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> list[StudentAnswer]:
    """Use cloud AI vision to recognize student answers.

    Args:
        image_bytes: Image file bytes.
        problems: List of problems for context.
        api_key: Override API key (optional).
        base_url: Override base URL (optional).
        model: Override model name (optional).

    Returns:
        List of StudentAnswer.
    """
    key = api_key or _config["api_key"]
    url = base_url or _config["base_url"]
    mdl = model or _config["model"]

    if not key:
        raise ValueError("AI Vision API key not configured. Set it in settings or AI_VISION_API_KEY env var.")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": mdl,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(image_b64, problems)},
        ],
        "max_tokens": 2000,
        "temperature": 0,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return _parse_ai_response(content, len(problems))


def _parse_ai_response(content: str, num_problems: int) -> list[StudentAnswer]:
    """Parse the AI's JSON response into StudentAnswer list."""
    # Try to extract JSON from the response (might have markdown fences)
    text = content.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # If JSON parsing fails, return empty answers
        return [StudentAnswer(id=i + 1) for i in range(num_problems)]

    ai_answers = {item["id"]: item for item in data.get("answers", [])}

    results: list[StudentAnswer] = []
    for i in range(1, num_problems + 1):
        item = ai_answers.get(i, {})
        results.append(
            StudentAnswer(
                id=i,
                answer=item.get("answer"),
                remainder=item.get("remainder"),
            )
        )
    return results
