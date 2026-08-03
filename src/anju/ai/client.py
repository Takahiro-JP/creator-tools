from __future__ import annotations

import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

ResponseModel = TypeVar(
    "ResponseModel",
    bound=BaseModel,
)


def create_gemini_client() -> genai.Client:
    """環境変数からGeminiクライアントを作成する。"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEYが設定されていません。")

    return genai.Client(api_key=api_key)


def generate_structured_content(
    *,
    model_name: str,
    prompt: str,
    response_model: type[ResponseModel],
    temperature: float = 0.3,
) -> ResponseModel:
    """Geminiを呼び出し、構造化された応答を返す。"""
    client = create_gemini_client()

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_model,
            ),
        )
    except Exception as error:
        raise RuntimeError(f"Gemini APIの呼び出しに失敗しました: {error}") from error

    parsed = response.parsed

    if not isinstance(parsed, response_model):
        raise RuntimeError("Geminiの応答を解析できませんでした。")

    return parsed
