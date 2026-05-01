"""
OpenRouter LLM service for transcript synthesis.
Generates structured Application Guides from video transcripts.
"""

import json
import time
from dataclasses import dataclass
from typing import Optional

import requests

from backend.config import get_settings
from backend.models import ApplicationGuide, CodeSnippet, CodeSnippetType, ToolOrApp
from backend.utils.logger import get_logger
from backend.utils.transcript_chunker import TranscriptChunker

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TokenUsage:
    """Token usage reported by OpenRouter."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage") -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens

    def model_dump(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class GuideSynthesisResult:
    """Application guide plus generation token usage."""

    guide: ApplicationGuide
    token_usage: TokenUsage


class OpenRouterService:
    """Service for LLM-based transcript synthesis using OpenRouter."""

    def __init__(self, model: Optional[str] = None):
        """Initialize OpenRouter client settings and chunker."""
        if not settings.openrouter_api_key:
            raise ValueError(
                "OpenRouter API key is not configured. Set openrouter_api_key or OPENROUTER_API_KEY."
            )

        self.api_key = settings.openrouter_api_key
        self.model = model or settings.openrouter_model
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.chunker = TranscriptChunker(max_tokens=settings.max_tokens_per_chunk)
        self.max_retries = 3
        self.retry_delay = 1.0

    def synthesize_guide(
        self,
        transcript: str,
        video_metadata: dict,
    ) -> GuideSynthesisResult:
        """
        Synthesize an Application Guide from a video transcript.

        Args:
            transcript: Video transcript text
            video_metadata: Video metadata (title, etc.)

        Returns:
            GuideSynthesisResult with structured content and token usage
        """
        video_title = video_metadata.get("title", "Unknown Video")

        if self.chunker.needs_chunking(transcript):
            logger.info(f"Transcript needs chunking for '{video_title}'")
            return self._synthesize_chunked(transcript, video_metadata)

        return self._synthesize_single(transcript, video_metadata)

    def _chat_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, TokenUsage]:
        """Call OpenRouter's OpenAI-compatible chat completions endpoint."""
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.openrouter_site_url,
                "X-Title": settings.openrouter_app_name,
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()

        content = payload["choices"][0]["message"]["content"]
        usage_data = payload.get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=int(usage_data.get("prompt_tokens") or 0),
            completion_tokens=int(usage_data.get("completion_tokens") or 0),
            total_tokens=int(usage_data.get("total_tokens") or 0),
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

    def _synthesize_single(
        self,
        transcript: str,
        video_metadata: dict,
    ) -> GuideSynthesisResult:
        """
        Synthesize guide from a single transcript chunk.

        Args:
            transcript: Video transcript text
            video_metadata: Video metadata

        Returns:
            GuideSynthesisResult
        """
        video_title = video_metadata.get("title", "Unknown Video")

        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(transcript, video_title)

        for attempt in range(self.max_retries):
            try:
                content, usage = self._chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=settings.response_max_tokens,
                )
                guide = self._parse_response(content)

                logger.info(
                    "Successfully synthesized guide for '%s' using %s total tokens",
                    video_title,
                    usage.total_tokens,
                )
                return GuideSynthesisResult(guide=guide, token_usage=usage)

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for '{video_title}': {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise

        raise RuntimeError(f"Failed to synthesize guide after {self.max_retries} attempts")

    def _synthesize_chunked(
        self,
        transcript: str,
        video_metadata: dict,
    ) -> GuideSynthesisResult:
        """
        Synthesize guide from a long transcript by processing chunks.

        Args:
            transcript: Long video transcript
            video_metadata: Video metadata

        Returns:
            Merged GuideSynthesisResult
        """
        video_title = video_metadata.get("title", "Unknown Video")
        chunks = self.chunker.chunk_transcript(transcript)
        total_usage = TokenUsage()

        logger.info(f"Processing {len(chunks)} chunks for '{video_title}'")

        chunk_guides = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
            result = self._synthesize_single(
                chunk,
                {
                    **video_metadata,
                    "title": f"{video_title} (Part {i + 1}/{len(chunks)})",
                },
            )
            chunk_guides.append(result.guide)
            total_usage.add(result.token_usage)

        merge_result = self._merge_guides(chunk_guides, video_metadata)
        total_usage.add(merge_result.token_usage)
        return GuideSynthesisResult(guide=merge_result.guide, token_usage=total_usage)

    def _merge_guides(
        self,
        guides: list[ApplicationGuide],
        video_metadata: dict,
    ) -> GuideSynthesisResult:
        """
        Merge multiple chunk guides into a single coherent guide.

        Args:
            guides: List of ApplicationGuide from chunks
            video_metadata: Original video metadata

        Returns:
            Merged GuideSynthesisResult
        """
        if len(guides) == 1:
            return GuideSynthesisResult(guide=guides[0], token_usage=TokenUsage())

        video_title = video_metadata.get("title", "Unknown Video")
        guides_json = json.dumps([g.model_dump() for g in guides], indent=2)

        merge_prompt = f"""You are merging multiple partial summaries of the same video "{video_title}" into one coherent Application Guide.

Here are the partial guides from different sections of the video:

{guides_json}

Create a single, unified Application Guide that:
1. Combines the big ideas into one coherent 1-3 sentence summary
2. Merges key terms (remove duplicates, keep most important 5-10)
3. Merges tools_and_apps (remove duplicates, keep purpose and URL where available)
4. Combines apply_5min actions (keep 3-5 most actionable)
5. Merges implementation steps into a logical sequence
6. Combines all unique code snippets
7. Combines resources and key_timestamps

Return a JSON object with this exact structure:
{{
  "big_idea": "string",
  "key_terms": ["string"],
  "tools_and_apps": [{{"name": "string", "purpose": "string", "url": null}}],
  "apply_5min": ["string"],
  "implementation_steps": ["string"],
  "code_snippets": [{{"language": "string", "code": "string", "description": "string", "explicit_or_suggested": "explicit|suggested"}}],
  "resources": ["string"],
  "key_timestamps": ["string"]
}}"""

        try:
            content, usage = self._chat_completion(
                messages=[
                    {"role": "system", "content": "You merge and consolidate technical content summaries."},
                    {"role": "user", "content": merge_prompt},
                ],
                temperature=0.2,
                max_tokens=settings.response_max_tokens,
            )
            return GuideSynthesisResult(guide=self._parse_response(content), token_usage=usage)

        except Exception as e:
            logger.error(f"Failed to merge guides: {e}")
            return GuideSynthesisResult(guide=guides[0], token_usage=TokenUsage())

    def _get_system_prompt(self) -> str:
        """Get the system prompt for guide synthesis."""
        return """You are an expert technical content analyzer and educator. Your task is to deeply analyze video transcripts and create comprehensive, actionable Application Guides.

You MUST respond with a valid JSON object matching this exact schema:
{
  "big_idea": "The core insight in 1-3 sentences. What's the main takeaway that changes how someone works?",
  "key_terms": ["5-10 important technical terms WITH brief definitions, e.g., 'API Gateway - A server that acts as an entry point for microservices'"],
  "tools_and_apps": [
    {
      "name": "Name of tool/app/platform",
      "purpose": "What it's used for in this context",
      "url": "Website URL if mentioned, or null"
    }
  ],
  "apply_5min": ["3-5 SPECIFIC actions someone can take RIGHT NOW in the next 5 minutes"],
  "implementation_steps": ["Detailed step-by-step guide. Be SPECIFIC with commands, settings, and configurations"],
  "code_snippets": [
    {
      "language": "programming language",
      "code": "the actual code - preserve formatting",
      "description": "What this code does and when to use it",
      "explicit_or_suggested": "explicit if verbatim from transcript, suggested if you're providing an example"
    }
  ],
  "resources": ["Any URLs, documentation links, GitHub repos, or resources mentioned"],
  "key_timestamps": ["Important moments like '5:30 - Setting up the database', '12:00 - Deploying to production'"]
}

CRITICAL GUIDELINES:
1. EXTRACT ALL TOOLS/APPS/PLATFORMS mentioned (VS Code, GitHub, AWS, Vercel, etc.)
2. PRESERVE EXACT CODE if mentioned - don't paraphrase code
3. Include SPECIFIC commands (npm install, pip install, docker commands, etc.)
4. Note any SETTINGS or CONFIGURATIONS mentioned
5. If the video shows a workflow, capture the EXACT steps
6. Include ANY URLs or links mentioned
7. Make implementation_steps detailed enough that someone could follow along
8. For code_snippets, include a description of what each snippet does"""

    def _get_user_prompt(self, transcript: str, video_title: str) -> str:
        """Get the user prompt for guide synthesis."""
        return f"""Analyze this transcript from the video "{video_title}" and create a COMPREHENSIVE Application Guide.

TRANSCRIPT:
{transcript}

ANALYZE THOROUGHLY AND EXTRACT:
1. The MAIN INSIGHT (big_idea) - what's the core message?
2. KEY TERMS with definitions - technical vocabulary used
3. ALL TOOLS & APPS mentioned (software, platforms, services, libraries)
4. IMMEDIATE ACTIONS (apply_5min) - what can someone do RIGHT NOW?
5. DETAILED IMPLEMENTATION STEPS - specific enough to follow along
6. ALL CODE SNIPPETS - preserve exact code, add descriptions
7. RESOURCES - any URLs, docs, repos mentioned
8. KEY TIMESTAMPS - important moments in the video

Be THOROUGH and SPECIFIC. Don't generalize - extract actual details from the transcript.

Return ONLY a valid JSON object."""

    def _parse_response(self, content: str) -> ApplicationGuide:
        """
        Parse LLM response into ApplicationGuide.

        Args:
            content: JSON string from LLM

        Returns:
            ApplicationGuide object
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            data = self._extract_json(content)

        code_snippets = []
        for snippet in self._as_list(data.get("code_snippets")):
            if isinstance(snippet, dict):
                snippet_type = snippet.get("explicit_or_suggested", "suggested")
                if snippet_type not in ["explicit", "suggested"]:
                    snippet_type = "suggested"

                code_snippets.append(
                    CodeSnippet(
                        language=str(snippet.get("language") or "text"),
                        code=str(snippet.get("code") or ""),
                        description=str(snippet.get("description") or ""),
                        explicit_or_suggested=CodeSnippetType(snippet_type),
                    )
                )

        tools_and_apps = []
        for tool in self._as_list(data.get("tools_and_apps")):
            if isinstance(tool, dict):
                tools_and_apps.append(
                    ToolOrApp(
                        name=str(tool.get("name") or "Unknown"),
                        purpose=str(tool.get("purpose") or ""),
                        url=tool.get("url"),
                    )
                )

        key_terms = self._string_list(data.get("key_terms"), ["No key terms extracted"])
        apply_5min = self._string_list(data.get("apply_5min"), ["Review the generated guide"])
        implementation_steps = self._string_list(
            data.get("implementation_steps"),
            ["Review the transcript and identify the next implementation step"],
        )

        return ApplicationGuide(
            big_idea=self._truncate(str(data.get("big_idea") or "No summary available"), 500),
            key_terms=key_terms[:15],
            tools_and_apps=tools_and_apps,
            apply_5min=apply_5min[:10],
            implementation_steps=implementation_steps[:20],
            code_snippets=code_snippets,
            resources=self._string_list(data.get("resources"), [])[:10],
            key_timestamps=self._string_list(data.get("key_timestamps"), [])[:10],
        )

    def _as_list(self, value) -> list:
        """Return list values as-is and wrap simple scalar values."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _string_list(self, value, fallback: list[str]) -> list[str]:
        """Normalize model output into a non-empty list of strings when required."""
        items = []
        for item in self._as_list(value):
            if isinstance(item, dict):
                item = json.dumps(item, ensure_ascii=False)
            text = str(item).strip()
            if text:
                items.append(text)
        return items or fallback

    def _truncate(self, value: str, max_length: int) -> str:
        """Trim strings to model schema limits."""
        value = value.strip()
        if len(value) <= max_length:
            return value
        return value[: max_length - 3].rstrip() + "..."

    def _extract_json(self, content: str) -> dict:
        """
        Attempt to extract JSON from a malformed response.

        Args:
            content: Potentially malformed JSON string

        Returns:
            Parsed dictionary
        """
        import re

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {
            "big_idea": "Failed to parse response",
            "key_terms": ["No key terms extracted"],
            "apply_5min": ["Review the transcript manually"],
            "implementation_steps": ["Retry guide generation or review the transcript manually"],
            "code_snippets": [],
            "tools_and_apps": [],
            "resources": [],
            "key_timestamps": [],
        }
