"""
FastAPI backend application for YouTube-to-Notion Guide Generator.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.models import (
    ChannelListResponse,
    DiscoverVideosRequest,
    DiscoverVideosResponse,
    ErrorResponse,
    HealthResponse,
    InputSourceType,
    NotionSetupRequest,
    NotionSetupResponse,
    ProcessChannelRequest,
    ProcessChannelResponse,
    ProcessVideosRequest,
    ProcessingStatus,
    VideoMetadata,
    VideoProcessingResult,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting YouTube-to-Notion Guide Generator API")
    logger.info(f"Using LLM provider: {settings.llm_provider}")
    if settings.llm_provider.strip().lower() == "gemini":
        logger.info(f"Using Gemini model: {settings.gemini_model}")
    else:
        logger.info(f"Using OpenRouter model: {settings.openrouter_model}")
    yield
    logger.info("Shutting down API")


app = FastAPI(
    title="YouTube-to-Notion Guide Generator",
    description="Convert YouTube technical videos into structured Notion Application Guides",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Streamlit frontend
# In production (Render), we allow all origins since frontend is a separate service
# In development, we restrict to localhost
import os
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

# In production, allow any onrender.com domain
if os.getenv("RENDER") == "true":
    allowed_origins.extend([
        "https://*.onrender.com",
    ])
    # Allow from environment variable if set (for specific frontend URL)
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Health Check ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health status of all services."""
    services = {}
    
    # Check OpenRouter
    try:
        if settings.openrouter_api_key:
            services["openrouter"] = "ok"
        else:
            services["openrouter"] = "not_configured"
    except Exception as e:
        services["openrouter"] = f"error: {str(e)}"

    # Check Gemini
    try:
        if settings.gemini_api_key:
            services["gemini"] = "ok"
        else:
            services["gemini"] = "not_configured"
    except Exception as e:
        services["gemini"] = f"error: {str(e)}"

    active_llm_provider = settings.llm_provider.strip().lower()
    services["active_llm_provider"] = active_llm_provider
    
    # Check Notion
    try:
        if settings.notion_api_key and len(settings.notion_api_key) > 10:
            services["notion"] = "ok"
        else:
            services["notion"] = "not_configured"
    except Exception as e:
        services["notion"] = f"error: {str(e)}"
    
    required_service_names = [active_llm_provider, "notion"]
    overall_status = (
        "healthy"
        if all(services.get(service_name) == "ok" for service_name in required_service_names)
        else "degraded"
    )
    
    return HealthResponse(
        status=overall_status,
        services=services,
        timestamp=datetime.utcnow()
    )


def _summarize_results(results: list[VideoProcessingResult]) -> dict:
    """Build summary counts for a processed batch."""
    return {
        "total": len(results),
        "successful": len([r for r in results if r.status == ProcessingStatus.SUCCESS]),
        "failed": len([r for r in results if r.status == ProcessingStatus.FAILED]),
        "skipped": len([r for r in results if r.status == ProcessingStatus.SKIPPED]),
        "prompt_tokens": sum(r.prompt_tokens for r in results),
        "completion_tokens": sum(r.completion_tokens for r in results),
        "total_tokens": sum(r.total_tokens for r in results),
    }


def _resolve_videos_for_processing(
    youtube,
    source_input: str,
    selected_video_ids: list[str],
    max_videos: int,
) -> tuple[InputSourceType, str, str, list[VideoMetadata]]:
    """
    Resolve user input into a concrete list of videos to process.

    Returns:
        Tuple of (source_type, channel_id, channel_name, videos)
    """
    source_type = youtube.detect_source_type(source_input)

    if source_type == InputSourceType.VIDEO:
        video = youtube.get_video_info(source_input)
        return source_type, video.channel_id, video.channel_name, [video]

    channel_id = youtube.extract_channel_id(source_input)
    channel_info = youtube.get_channel_info(channel_id)

    if selected_video_ids:
        videos = []
        for video_id in selected_video_ids:
            video_info = youtube.get_video_info(video_id)
            if video_info.channel_id and video_info.channel_id != channel_id:
                logger.warning(
                    "Skipping selected video %s because it does not belong to channel %s",
                    video_id,
                    channel_id,
                )
                continue
            videos.append(video_info)
    else:
        videos = youtube.get_latest_videos(channel_id, limit=max_videos)

    return source_type, channel_id, channel_info.channel_name, videos


def _process_video_batch(
    youtube,
    llm,
    notion,
    videos: list[VideoMetadata],
    notion_database_id: str,
) -> list[VideoProcessingResult]:
    """Process each selected video into a Notion guide."""
    import time

    results: list[VideoProcessingResult] = []

    for video in videos:
        video_start = time.time()
        try:
            transcript = youtube.get_transcript(video.video_id)

            if not transcript:
                results.append(VideoProcessingResult(
                    video_id=video.video_id,
                    video_title=video.title,
                    views=video.view_count,
                    video_url=video.url,
                    published_at=video.published_at,
                    duration_seconds=video.duration_seconds,
                    status=ProcessingStatus.SKIPPED,
                    error="No transcript available",
                    processing_time_seconds=time.time() - video_start,
                ))
                continue

            synthesis = llm.synthesize_guide(transcript, video.model_dump())
            page_url, _ = notion.create_guide_page(
                notion_database_id,
                synthesis.guide,
                video.model_dump(),
            )

            results.append(VideoProcessingResult(
                video_id=video.video_id,
                video_title=video.title,
                views=video.view_count,
                video_url=video.url,
                published_at=video.published_at,
                duration_seconds=video.duration_seconds,
                status=ProcessingStatus.SUCCESS,
                notion_page_url=page_url,
                prompt_tokens=synthesis.token_usage.prompt_tokens,
                completion_tokens=synthesis.token_usage.completion_tokens,
                total_tokens=synthesis.token_usage.total_tokens,
                processing_time_seconds=time.time() - video_start,
            ))
        except Exception as e:
            logger.error(f"Error processing video {video.video_id}: {e}")
            results.append(VideoProcessingResult(
                video_id=video.video_id,
                video_title=video.title,
                views=video.view_count,
                video_url=video.url,
                published_at=video.published_at,
                duration_seconds=video.duration_seconds,
                status=ProcessingStatus.FAILED,
                error=str(e),
                processing_time_seconds=time.time() - video_start,
            ))

    return results


# ============ Channel Processing ============

@app.post("/api/v1/discover-videos", response_model=DiscoverVideosResponse)
async def discover_videos(request: DiscoverVideosRequest):
    """
    Discover latest channel videos or inspect a single YouTube video input.
    """
    from backend.services import YouTubeService

    youtube = YouTubeService()

    try:
        source_type = youtube.detect_source_type(request.source_input)

        if source_type == InputSourceType.VIDEO:
            video = youtube.get_video_info(request.source_input)
            return DiscoverVideosResponse(
                source_type=source_type,
                channel_id=video.channel_id,
                channel_name=video.channel_name,
                videos=[video],
                message="Single video detected. You can process it directly.",
            )

        channel_id = youtube.extract_channel_id(request.source_input)
        channel_info = youtube.get_channel_info(channel_id)
        videos = youtube.get_latest_videos(channel_id, limit=request.max_videos)

        return DiscoverVideosResponse(
            source_type=source_type,
            channel_id=channel_id,
            channel_name=channel_info.channel_name,
            videos=videos,
            message=f"Fetched {len(videos)} latest videos for {channel_info.channel_name}.",
        )
    except Exception as e:
        logger.error(f"Failed to discover videos for {request.source_input}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/process-videos", response_model=ProcessChannelResponse)
async def process_videos(request: ProcessVideosRequest):
    """
    Process selected videos from a channel or a direct video URL.
    """
    from backend.services import YouTubeService, NotionService, StorageService, create_llm_service
    import time

    start_time = time.time()
    logger.info(f"Processing source input: {request.source_input}")

    try:
        youtube = YouTubeService()
        try:
            llm = create_llm_service(
                provider=request.llm_provider,
                model=request.llm_model,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        notion = NotionService()
        storage = StorageService()

        source_type, channel_id, channel_name, videos = _resolve_videos_for_processing(
            youtube=youtube,
            source_input=request.source_input,
            selected_video_ids=request.selected_video_ids,
            max_videos=request.max_videos,
        )

        if not videos:
            raise ValueError("No videos found to process.")

        db_id = request.notion_database_id or settings.notion_database_id
        if not db_id:
            db_id, _ = notion.setup_database()

        results = _process_video_batch(
            youtube=youtube,
            llm=llm,
            notion=notion,
            videos=videos,
            notion_database_id=db_id,
        )

        if source_type == InputSourceType.CHANNEL:
            channel_info = youtube.get_channel_info(channel_id)
            storage.save_channel(channel_info.model_dump())

        return ProcessChannelResponse(
            channel_id=channel_id,
            channel_name=channel_name,
            source_type=source_type,
            results=results,
            summary=_summarize_results(results),
            total_processing_time_seconds=time.time() - start_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process source {request.source_input}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/process-channel", response_model=ProcessChannelResponse)
async def process_channel(request: ProcessChannelRequest):
    """
    Backward-compatible wrapper that processes the latest videos from a channel.
    """
    translated_request = ProcessVideosRequest(
        source_input=request.channel_url,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        notion_database_id=request.notion_database_id,
        max_videos=request.max_videos,
    )
    return await process_videos(translated_request)


# ============ Channel List ============

@app.get("/api/v1/channels", response_model=ChannelListResponse)
async def list_channels():
    """List all saved channels."""
    from backend.services import StorageService
    
    storage = StorageService()
    channels = storage.get_all_channels()
    
    return ChannelListResponse(channels=channels)


# ============ Notion Setup ============

@app.post("/api/v1/notion/setup", response_model=NotionSetupResponse)
async def setup_notion_database(request: NotionSetupRequest):
    """Create or verify Notion database for storing guides."""
    from backend.services import NotionService
    
    try:
        notion = NotionService()
        db_id, db_url = notion.setup_database(
            database_name=request.database_name,
            parent_page_id=request.parent_page_id
        )
        
        return NotionSetupResponse(
            database_id=db_id,
            database_url=db_url,
            message=f"Database '{request.database_name}' is ready"
        )
        
    except Exception as e:
        logger.error(f"Failed to setup Notion database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Test Endpoints ============

@app.post("/api/v1/test-youtube")
async def test_youtube(source_input: str):
    """Test YouTube discovery with a channel or video input."""
    from backend.services import YouTubeService
    
    try:
        youtube = YouTubeService()
        source_type = youtube.detect_source_type(source_input)

        if source_type == InputSourceType.VIDEO:
            video = youtube.get_video_info(source_input)
            return {
                "source_type": source_type,
                "channel_id": video.channel_id,
                "videos": [video.model_dump()]
            }

        channel_id = youtube.extract_channel_id(source_input)
        videos = youtube.get_latest_videos(channel_id, limit=3)

        return {
            "source_type": source_type,
            "channel_id": channel_id,
            "videos": [v.model_dump() for v in videos]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/test-openrouter")
async def test_openrouter(transcript: str):
    """Test OpenRouter LLM service with a sample transcript."""
    from backend.services import OpenRouterService
    
    try:
        openrouter = OpenRouterService()
        result = openrouter.synthesize_guide(transcript, {"title": "Test Video"})
        
        return {
            "guide": result.guide.model_dump(),
            "token_usage": result.token_usage.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/test-gemini")
async def test_gemini(transcript: str):
    """Test Gemini LLM service with a sample transcript."""
    from backend.services import GeminiService

    try:
        gemini = GeminiService()
        result = gemini.synthesize_guide(transcript, {"title": "Test Video"})

        return {
            "guide": result.guide.model_dump(),
            "token_usage": result.token_usage.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/test-llm")
async def test_llm(transcript: str):
    """Test the currently configured LLM provider with a sample transcript."""
    from backend.services import create_llm_service

    try:
        llm = create_llm_service()
        result = llm.synthesize_guide(transcript, {"title": "Test Video"})

        return {
            "provider": settings.llm_provider.strip().lower(),
            "guide": result.guide.model_dump(),
            "token_usage": result.token_usage.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
