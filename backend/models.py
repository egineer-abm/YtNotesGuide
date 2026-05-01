"""
Pydantic models for request/response schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


# ============ Enums ============

class ProcessingStatus(str, Enum):
    """Status of video processing."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class CodeSnippetType(str, Enum):
    """Whether code snippet is verbatim or suggested."""
    EXPLICIT = "explicit"
    SUGGESTED = "suggested"


class InputSourceType(str, Enum):
    """Supported kinds of YouTube input."""
    CHANNEL = "channel"
    VIDEO = "video"


# ============ YouTube Models ============

class VideoMetadata(BaseModel):
    """Metadata for a YouTube video."""
    video_id: str
    title: str
    channel_id: str
    channel_name: str
    view_count: int
    duration_seconds: int
    published_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    url: str


class ChannelInfo(BaseModel):
    """Information about a YouTube channel."""
    channel_id: str
    channel_name: str
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None
    last_processed: Optional[datetime] = None


# ============ LLM Output Models ============

class CodeSnippet(BaseModel):
    """A code snippet extracted from transcript."""
    language: str = Field(description="Programming language")
    code: str = Field(description="The code snippet")
    description: str = Field(default="", description="What this code does")
    explicit_or_suggested: CodeSnippetType = Field(
        description="Whether code is verbatim from transcript or suggested"
    )


class ToolOrApp(BaseModel):
    """A tool, app, or resource mentioned in the video."""
    name: str = Field(description="Name of the tool/app")
    purpose: str = Field(description="What it's used for")
    url: Optional[str] = Field(default=None, description="Website or link if mentioned")


class ApplicationGuide(BaseModel):
    """Structured output from LLM synthesis."""
    big_idea: str = Field(
        description="Main insight in 1-3 sentences",
        max_length=500
    )
    key_terms: list[str] = Field(
        description="5-10 important technical terms with brief definitions",
        min_length=1,
        max_length=15
    )
    tools_and_apps: list[ToolOrApp] = Field(
        default_factory=list,
        description="Tools, apps, platforms, or services mentioned"
    )
    apply_5min: list[str] = Field(
        description="3-5 actionable items for immediate application",
        min_length=1,
        max_length=10
    )
    implementation_steps: list[str] = Field(
        description="Detailed step-by-step implementation guide",
        min_length=1,
        max_length=20
    )
    code_snippets: list[CodeSnippet] = Field(
        default_factory=list,
        description="Code examples with descriptions"
    )
    resources: list[str] = Field(
        default_factory=list,
        description="URLs, documentation links, or resources mentioned"
    )
    key_timestamps: list[str] = Field(
        default_factory=list,
        description="Important moments in the video (e.g., '5:30 - Setting up the project')"
    )


# ============ API Request Models ============

class ProcessChannelRequest(BaseModel):
    """Request to process a YouTube channel."""
    channel_url: str = Field(description="YouTube channel URL or ID")
    llm_provider: Optional[Literal["openrouter", "gemini"]] = Field(
        default=None,
        description="Optional LLM provider override: openrouter or gemini"
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="Optional model override for the selected provider"
    )
    notion_database_id: Optional[str] = Field(
        default=None,
        description="Notion database ID (optional, will use default if not provided)"
    )
    max_videos: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of videos to process"
    )


class DiscoverVideosRequest(BaseModel):
    """Request to discover videos from a channel or a single video input."""
    source_input: str = Field(description="YouTube channel/video URL, handle, or ID")
    max_videos: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of latest videos to return for a channel"
    )


class ProcessVideosRequest(BaseModel):
    """Request to process specific videos from a channel or a single video input."""
    source_input: str = Field(description="YouTube channel/video URL, handle, or ID")
    llm_provider: Optional[Literal["openrouter", "gemini"]] = Field(
        default=None,
        description="Optional LLM provider override: openrouter or gemini"
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="Optional model override for the selected provider"
    )
    selected_video_ids: list[str] = Field(
        default_factory=list,
        description="Specific video IDs selected by the user"
    )
    notion_database_id: Optional[str] = Field(
        default=None,
        description="Notion database ID (optional, will use default if not provided)"
    )
    max_videos: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of latest videos to process when no selection is provided"
    )


class NotionSetupRequest(BaseModel):
    """Request to set up Notion database."""
    database_name: str = Field(
        default="Application Guides",
        description="Name for the Notion database"
    )
    parent_page_id: Optional[str] = Field(
        default=None,
        description="Parent page ID (optional)"
    )


# ============ API Response Models ============

class VideoProcessingResult(BaseModel):
    """Result of processing a single video."""
    video_id: str
    video_title: str
    views: int
    video_url: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: ProcessingStatus
    notion_page_url: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class ProcessChannelResponse(BaseModel):
    """Response from processing a channel."""
    channel_id: str
    channel_name: str
    source_type: InputSourceType = Field(default=InputSourceType.CHANNEL)
    results: list[VideoProcessingResult]
    summary: dict = Field(
        description="Summary statistics: total, successful, failed, skipped"
    )
    total_processing_time_seconds: float


class DiscoverVideosResponse(BaseModel):
    """Response with available videos for a given source."""
    source_type: InputSourceType
    channel_id: str
    channel_name: str
    videos: list[VideoMetadata]
    message: str


class ChannelListResponse(BaseModel):
    """Response listing saved channels."""
    channels: list[ChannelInfo]


class NotionSetupResponse(BaseModel):
    """Response from Notion database setup."""
    database_id: str
    database_url: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: dict = Field(description="Status of each service")
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    error_code: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
