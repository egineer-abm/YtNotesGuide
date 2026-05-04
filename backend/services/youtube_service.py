"""
YouTube service for video discovery and transcript extraction.
Uses opentube for public metadata and youtube-transcript-api for transcripts.
"""

import io
import re
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import opentube
from youtube_transcript_api import YouTubeTranscriptApi

from backend.config import get_settings
from backend.models import ChannelInfo, InputSourceType, VideoMetadata
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class YouTubeAuthenticationError(RuntimeError):
    """Raised when YouTube blocks public metadata or transcript access."""


class YouTubeService:
    """Service for interacting with YouTube content."""

    VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")

    def detect_source_type(self, source_input: str) -> InputSourceType:
        """Detect whether the input refers to a channel or a single video."""
        return InputSourceType.VIDEO if self.is_video_input(source_input) else InputSourceType.CHANNEL

    def is_video_input(self, source_input: str) -> bool:
        """Check whether the input refers to a single YouTube video."""
        source_input = source_input.strip()

        if self.VIDEO_ID_PATTERN.fullmatch(source_input):
            return True

        return any(
            marker in source_input
            for marker in ("youtu.be/", "watch?v=", "youtube.com/shorts/", "youtube.com/live/")
        )

    def extract_video_id(self, url_or_id: str) -> str:
        """Extract a YouTube video ID from a URL or return it directly."""
        url_or_id = url_or_id.strip()

        if self.VIDEO_ID_PATTERN.fullmatch(url_or_id):
            return url_or_id

        parsed = urlparse(url_or_id)
        host = parsed.netloc.lower()

        if "youtu.be" in host:
            video_id = parsed.path.strip("/").split("/")[0]
            if self.VIDEO_ID_PATTERN.fullmatch(video_id):
                return video_id

        if "youtube.com" in host:
            query_video_id = parse_qs(parsed.query).get("v", [None])[0]
            if query_video_id and self.VIDEO_ID_PATTERN.fullmatch(query_video_id):
                return query_video_id

            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2 and path_parts[0] in {"shorts", "live", "embed"}:
                candidate = path_parts[1]
                if self.VIDEO_ID_PATTERN.fullmatch(candidate):
                    return candidate

        raise ValueError(f"Could not extract video ID from: {url_or_id}")

    def extract_channel_id(self, url_or_id: str) -> str:
        """Extract a channel ID from common YouTube channel URL formats."""
        url_or_id = url_or_id.strip()

        if re.match(r"^UC[\w-]{22}$", url_or_id):
            return url_or_id

        patterns = [
            r"youtube\.com/channel/(UC[\w-]{22})",
            r"youtube\.com/@([\w.-]+)",
            r"youtube\.com/(?:c|user)/([\w.-]+)",
        ]

        if url_or_id.startswith("@"):
            return self._resolve_channel_metadata(url_or_id)["id"]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if not match:
                continue

            extracted = match.group(1)
            if extracted.startswith("UC"):
                return extracted
            return self._resolve_channel_metadata(f"@{extracted}")["id"]

        raise ValueError(f"Could not extract channel ID from: {url_or_id}")

    def get_channel_info(self, channel_id: str) -> ChannelInfo:
        """Get public information about a YouTube channel."""
        try:
            metadata = self._resolve_channel_metadata(channel_id)
            return ChannelInfo(
                channel_id=metadata.get("id", channel_id),
                channel_name=metadata.get("name") or "Unknown",
                subscriber_count=self._parse_count(metadata.get("subscribers")),
                video_count=self._parse_count(metadata.get("video_count")),
            )
        except Exception as e:
            self._raise_if_rate_limited(e)
            logger.error(f"Failed to get channel info for {channel_id}: {e}")
            return ChannelInfo(channel_id=channel_id, channel_name="Unknown")

    def get_latest_videos(self, channel_id: str, limit: int = 10) -> list[VideoMetadata]:
        """Get the latest uploaded videos from a channel."""
        try:
            channel = opentube.Channel(channel_id)
            videos = channel.videos() or {}
        except Exception as e:
            self._raise_if_rate_limited(e)
            logger.error(f"Failed to get latest videos for channel {channel_id}: {e}")
            return []

        results: list[VideoMetadata] = []
        for raw in list(videos.values())[:limit]:
            try:
                results.append(self._video_metadata_from_basic(raw, channel_id))
            except Exception as e:
                logger.warning(f"Failed to parse opentube video metadata: {e}")

        return results

    def get_top_videos(
        self,
        channel_id: str,
        limit: int = 5,
        sort_by: str = "view_count",
    ) -> list[VideoMetadata]:
        """Backward-compatible wrapper for retrieving videos from a channel."""
        videos = self.get_latest_videos(channel_id, limit=max(limit, 10))

        if sort_by == "view_count":
            videos.sort(key=lambda video: video.view_count, reverse=True)
        else:
            videos.sort(key=lambda video: video.published_at or datetime.min, reverse=True)

        return videos[:limit]

    def get_video_info(self, url_or_id: str) -> VideoMetadata:
        """Get detailed public metadata for a single video."""
        video_id = self.extract_video_id(url_or_id)
        url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            with redirect_stdout(io.StringIO()):
                video = opentube.Video(url)
            return self._video_metadata_from_opentube_video(video, video_id)
        except Exception as e:
            self._raise_if_rate_limited(e)
            logger.error(f"Failed to get video info for {video_id}: {e}")
            raise ValueError(f"Could not fetch video info for: {url_or_id}") from e

    def get_transcript(
        self,
        video_id: str,
        languages: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Get transcript text for a YouTube video."""
        if languages is None:
            languages = settings.transcript_language_list

        return self._get_transcript_from_api(video_id, languages)

    def _resolve_channel_metadata(self, channel_input: str) -> dict[str, Any]:
        """Resolve a channel ID, handle, or URL into opentube channel metadata."""
        return opentube.Channel(channel_input).metadata

    def _video_metadata_from_basic(
        self,
        raw: dict[str, Any],
        channel_id: str,
    ) -> VideoMetadata:
        """Convert opentube channel video metadata into the app model."""
        thumbnails = raw.get("thumbnails") or []
        thumbnail = thumbnails[-1].get("url") if thumbnails else raw.get("thumbnail")

        return VideoMetadata(
            video_id=raw.get("id", ""),
            title=raw.get("title") or "Unknown",
            channel_id=channel_id,
            channel_name="Unknown",
            view_count=self._parse_count(raw.get("views")),
            duration_seconds=self._parse_duration(raw.get("duration")),
            published_at=self._parse_published_at(raw.get("published")),
            thumbnail_url=thumbnail,
            url=raw.get("url") or f"https://www.youtube.com/watch?v={raw.get('id', '')}",
        )

    def _video_metadata_from_full(
        self,
        raw: dict[str, Any],
        video_id: str,
    ) -> VideoMetadata:
        """Convert opentube video metadata into the app model."""
        owner = raw.get("owner") or {}

        return VideoMetadata(
            video_id=raw.get("id") or video_id,
            title=raw.get("title") or "Unknown",
            channel_id=owner.get("id", ""),
            channel_name=owner.get("title") or "Unknown",
            view_count=self._parse_count(raw.get("views")),
            duration_seconds=0,
            published_at=self._parse_published_at(raw.get("published")),
            thumbnail_url=raw.get("thumbnail"),
            url=raw.get("url") or f"https://www.youtube.com/watch?v={video_id}",
        )

    def _video_metadata_from_opentube_video(
        self,
        video: opentube.Video,
        video_id: str,
    ) -> VideoMetadata:
        """Convert opentube's raw video data into the app model."""
        raw_data = getattr(video, "_video_data", {})
        contents = (
            raw_data.get("contents", {})
            .get("twoColumnWatchNextResults", {})
            .get("results", {})
            .get("results", {})
            .get("contents", [])
        )
        primary = self._find_renderer(contents, "videoPrimaryInfoRenderer")
        secondary = self._find_renderer(contents, "videoSecondaryInfoRenderer")

        owner = secondary.get("owner", {}).get("videoOwnerRenderer", {})
        owner_runs = owner.get("title", {}).get("runs", [])
        owner_endpoint = (
            owner_runs[0].get("navigationEndpoint", {}) if owner_runs else {}
        )
        browse_endpoint = owner_endpoint.get("browseEndpoint", {})

        title = self._runs_text(primary.get("title", {}).get("runs")) or "Unknown"
        view_text = (
            primary.get("viewCount", {})
            .get("videoViewCountRenderer", {})
            .get("originalViewCount")
        )
        if view_text in {None, "0"}:
            view_text = (
                primary.get("viewCount", {})
                .get("videoViewCountRenderer", {})
                .get("viewCount", {})
                .get("simpleText")
            )

        return VideoMetadata(
            video_id=video_id,
            title=title,
            channel_id=browse_endpoint.get("browseId", ""),
            channel_name=self._runs_text(owner.get("title", {}).get("runs")) or "Unknown",
            view_count=self._parse_count(view_text),
            duration_seconds=0,
            published_at=self._parse_published_at(
                primary.get("dateText", {}).get("simpleText")
            ),
            thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
            url=f"https://www.youtube.com/watch?v={video_id}",
        )

    def _get_transcript_from_api(
        self,
        video_id: str,
        languages: list[str],
    ) -> Optional[str]:
        """Fetch transcript text using youtube-transcript-api."""
        try:
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                transcript_items = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=languages,
                )
            else:
                transcript_items = YouTubeTranscriptApi().fetch(
                    video_id,
                    languages=languages,
                ).to_raw_data()
            texts = [
                item.get("text", "").strip()
                for item in transcript_items
                if item.get("text", "").strip()
            ]
            transcript = " ".join(texts).strip()
            if transcript:
                logger.info(f"Got transcript from API for {video_id}")
                return self._clean_transcript_text(transcript)
        except Exception as e:
            self._raise_if_rate_limited(e)
            logger.warning(f"Transcript API failed for {video_id}: {e}")

        return None

    def _parse_count(self, value: Any) -> int:
        """Parse YouTube count text into an integer when possible."""
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)

        text = str(value).strip().lower()
        text = text.replace("\u202f", " ").replace("\xa0", " ")
        text = re.sub(
            r"\s*(views?|vues?|subscribers?|abonnés?|videos?|vidéos?|likes?)\s*$",
            "",
            text,
        ).strip()
        if not text or text in {"no", "none"}:
            return 0

        leading_count = re.match(r"^([\d.,\s]+)\s*(md|[kmb])?", text)
        if leading_count:
            compact = "".join(leading_count.groups(default=""))
        else:
            compact = text.replace(" ", "")

        if re.search(r"[kmb]|md", compact) and "," in compact:
            compact = compact.replace(",", ".")
        else:
            compact = compact.replace(",", "")

        multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "md": 1_000_000_000}
        match = re.match(r"^([\d.]+)\s*(md|[kmb])?$", compact)
        if match:
            number = float(match.group(1))
            suffix = match.group(2)
            return int(number * multipliers.get(suffix, 1))

        digits = re.sub(r"\D", "", compact)
        return int(digits) if digits else 0

    def _parse_duration(self, value: Any) -> int:
        """Parse YouTube duration text like 1:02:03 into seconds."""
        if not value:
            return 0
        parts = str(value).split(":")
        if not all(part.isdigit() for part in parts):
            return 0

        seconds = 0
        for part in parts:
            seconds = seconds * 60 + int(part)
        return seconds

    def _parse_published_at(self, value: Any) -> Optional[datetime]:
        """Parse absolute YouTube publish dates; relative dates return None."""
        if not value:
            return None

        text = str(value).replace("Premiered ", "").strip()
        for date_format in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, date_format)
            except ValueError:
                continue

        return None

    def _clean_transcript_text(self, text: str) -> Optional[str]:
        """Normalize transcript text into a plain readable string."""
        cleaned_text = re.sub(r"\s+", " ", text)
        cleaned_text = re.sub(r"\[Music\]", "", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\[Applause\]", "", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = cleaned_text.strip()
        return cleaned_text if cleaned_text else None

    def _find_renderer(self, items: list[dict[str, Any]], renderer_name: str) -> dict[str, Any]:
        """Find a renderer object inside a list of YouTube content blocks."""
        for item in items:
            if renderer_name in item:
                return item[renderer_name]
        return {}

    def _runs_text(self, runs: Any) -> str:
        """Join YouTube text runs into a plain string."""
        if not runs:
            return ""
        return "".join(run.get("text", "") for run in runs).strip()

    def _raise_if_rate_limited(self, error: Exception) -> None:
        """Convert opentube and YouTube blocking failures into an API-level 503."""
        if isinstance(error, opentube.TooManyRequests):
            raise YouTubeAuthenticationError(
                "YouTube is temporarily rate-limiting public metadata requests. "
                "Please retry later."
            ) from error

        message = str(error).lower()
        if any(marker in message for marker in ("too many requests", "429", "captcha", "not a bot")):
            raise YouTubeAuthenticationError(
                "YouTube is temporarily blocking public metadata or transcript requests. "
                "Please retry later."
            ) from error
