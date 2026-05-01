"""
Gemini LLM service for transcript synthesis.

Uses Gemini's generateContent REST API while reusing the guide synthesis,
chunking, merging, and parsing behavior from the OpenRouter service.
"""

from typing import Optional

import requests

from backend.config import get_settings
from backend.services.openrouter_service import OpenRouterService, TokenUsage
from backend.utils.logger import get_logger
from backend.utils.transcript_chunker import TranscriptChunker

logger = get_logger(__name__)
settings = get_settings()


class GeminiService(OpenRouterService):
    """Service for LLM-based transcript synthesis using Gemini."""

    def __init__(self, model: Optional[str] = None):
        """Initialize Gemini client settings and chunker."""
        if not settings.gemini_api_key:
            raise ValueError(
                "Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )

        self.api_key = settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.base_url = settings.gemini_base_url.rstrip("/")
        self.chunker = TranscriptChunker(max_tokens=settings.max_tokens_per_chunk)
        self.max_retries = 3
        self.retry_delay = 1.0

    def _chat_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, TokenUsage]:
        """Call Gemini's generateContent endpoint and return text plus token usage."""
        system_instruction, contents = self._convert_messages(messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }

        response = requests.post(
            f"{self.base_url}/models/{self.model}:generateContent",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            json=payload,
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        data = response.json()

        content = self._extract_text(data)
        usage_data = data.get("usageMetadata") or {}
        usage = TokenUsage(
            prompt_tokens=int(usage_data.get("promptTokenCount") or 0),
            completion_tokens=int(usage_data.get("candidatesTokenCount") or 0),
            total_tokens=int(usage_data.get("totalTokenCount") or 0),
        )
        if not usage.prompt_tokens:
            usage.prompt_tokens = sum(
                self.chunker.count_tokens(str(message.get("content", "")))
                for message in messages
            )
        if not usage.completion_tokens:
            usage.completion_tokens = self.chunker.count_tokens(content)
        if not usage.total_tokens:
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

        return content, usage

    def _convert_messages(self, messages: list[dict]) -> tuple[Optional[str], list[dict]]:
        """Convert OpenAI-style chat messages to Gemini generateContent format."""
        system_parts: list[str] = []
        contents: list[dict] = []

        for message in messages:
            role = message.get("role", "user")
            text = str(message.get("content", ""))

            if role == "system":
                system_parts.append(text)
                continue

            gemini_role = "model" if role == "assistant" else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": text}],
            })

        return "\n\n".join(system_parts) if system_parts else None, contents

    def _extract_text(self, data: dict) -> str:
        """Extract candidate text from Gemini's response payload."""
        candidates = data.get("candidates") or []
        if not candidates:
            prompt_feedback = data.get("promptFeedback") or {}
            raise ValueError(f"Gemini returned no candidates: {prompt_feedback}")

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text:
            finish_reason = candidates[0].get("finishReason", "unknown")
            raise ValueError(f"Gemini returned an empty response. finishReason={finish_reason}")

        return text
