"""
YouTube service for video discovery and transcript extraction.
Uses yt-dlp for metadata and youtube-transcript-api as a transcript fallback.
"""

import json
import os
import re
import tempfile
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from backend.config import get_settings
from backend.models import ChannelInfo, InputSourceType, VideoMetadata
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class YouTubeService:
    """Service for interacting with YouTube content."""

    VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
    
    def __init__(self):
        """Initialize YouTube service with yt-dlp options."""
        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreerrors": True,
        }
    
    def extract_channel_id(self, url_or_id: str) -> str:
        """
        Extract channel ID from various YouTube URL formats or return ID directly.
        
        Args:
            url_or_id: YouTube channel URL or channel ID
            
        Returns:
            Channel ID string
            
        Raises:
            ValueError: If unable to extract channel ID
        """
        url_or_id = url_or_id.strip()
        
        # Already a channel ID (starts with UC)
        if re.match(r'^UC[\w-]{22}$', url_or_id):
            return url_or_id
        
        # Handle @username format
        if url_or_id.startswith('@'):
            return self._resolve_handle_to_channel_id(url_or_id)
        
        # URL patterns
        patterns = [
            # /channel/CHANNEL_ID
            r'youtube\.com/channel/(UC[\w-]{22})',
            # /@handle
            r'youtube\.com/@([\w.-]+)',
            # /c/customname or /user/username
            r'youtube\.com/(?:c|user)/([\w.-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                extracted = match.group(1)
                # If it's a channel ID, return it
                if extracted.startswith('UC'):
                    return extracted
                # Otherwise it's a handle/username, resolve it
                return self._resolve_handle_to_channel_id(f"@{extracted}")
        
        raise ValueError(f"Could not extract channel ID from: {url_or_id}")

    def detect_source_type(self, source_input: str) -> InputSourceType:
        """
        Detect whether the user provided a channel-like input or a single video.

        Args:
            source_input: YouTube channel/video URL, handle, or ID

        Returns:
            InputSourceType enum
        """
        source_input = source_input.strip()

        if self.is_video_input(source_input):
            return InputSourceType.VIDEO

        return InputSourceType.CHANNEL

    def is_video_input(self, source_input: str) -> bool:
        """
        Check whether the input refers to a single YouTube video.

        Args:
            source_input: User-provided YouTube input

        Returns:
            True if the input appears to be a video URL or video ID
        """
        source_input = source_input.strip()

        if self.VIDEO_ID_PATTERN.fullmatch(source_input):
            return True

        if "youtu.be/" in source_input:
            return True

        if (
            "watch?v=" in source_input
            or "youtube.com/shorts/" in source_input
            or "youtube.com/live/" in source_input
        ):
            return True

        return False

    def extract_video_id(self, url_or_id: str) -> str:
        """
        Extract a YouTube video ID from a URL or return it directly.

        Args:
            url_or_id: YouTube video URL or video ID

        Returns:
            Video ID string

        Raises:
            ValueError: If unable to extract a valid video ID
        """
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
    
    def _resolve_handle_to_channel_id(self, handle: str) -> str:
        """
        Resolve a YouTube handle to a channel ID.
        
        Args:
            handle: YouTube handle (e.g., @fireship)
            
        Returns:
            Channel ID
        """
        # Clean up handle
        handle = handle.lstrip('@')
        url = f"https://www.youtube.com/@{handle}"
        
        opts = {
            **self.ydl_opts,
            "extract_flat": False,
            "playlist_items": "0",  # Don't fetch any videos
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and 'channel_id' in info:
                    return info['channel_id']
                # Try uploader_id as fallback
                if info and 'uploader_id' in info:
                    uploader_id = info['uploader_id']
                    if uploader_id.startswith('UC'):
                        return uploader_id
        except Exception as e:
            logger.error(f"Failed to resolve handle {handle}: {e}")
        
        raise ValueError(f"Could not resolve channel ID for handle: @{handle}")
    
    def get_channel_info(self, channel_id: str) -> ChannelInfo:
        """
        Get information about a YouTube channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            ChannelInfo object
        """
        url = f"https://www.youtube.com/channel/{channel_id}"
        
        opts = {
            **self.ydl_opts,
            "extract_flat": False,
            "playlist_items": "0",
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return ChannelInfo(
                    channel_id=channel_id,
                    channel_name=info.get('uploader', info.get('channel', 'Unknown')),
                    subscriber_count=info.get('channel_follower_count'),
                    video_count=info.get('playlist_count'),
                )
        except Exception as e:
            logger.error(f"Failed to get channel info for {channel_id}: {e}")
            # Return basic info
            return ChannelInfo(
                channel_id=channel_id,
                channel_name="Unknown",
            )

    def get_latest_videos(
        self,
        channel_id: str,
        limit: int = 10,
    ) -> list[VideoMetadata]:
        """
        Get the latest uploaded videos from a channel.

        Args:
            channel_id: YouTube channel ID
            limit: Maximum number of videos to return

        Returns:
            List of VideoMetadata objects
        """
        uploads_playlist_id = f"UU{channel_id[2:]}"
        url = f"https://www.youtube.com/playlist?list={uploads_playlist_id}"

        opts = {
            **self.ydl_opts,
            "extract_flat": "in_playlist",
            "playlistend": limit,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info or 'entries' not in info:
                    logger.warning(f"No videos found for channel {channel_id}")
                    return []
                
                videos = []
                for entry in info['entries']:
                    if entry is None:
                        continue

                    try:
                        # Get full video info for view count
                        video_info = self._get_video_info(entry['id'])
                        if video_info:
                            videos.append(video_info)
                    except Exception as e:
                        logger.warning(f"Failed to get info for video {entry.get('id')}: {e}")

                return videos[:limit]

        except Exception as e:
            logger.error(f"Failed to get latest videos for channel {channel_id}: {e}")
            return []

    def get_top_videos(
        self,
        channel_id: str,
        limit: int = 5,
        sort_by: str = "view_count"
    ) -> list[VideoMetadata]:
        """
        Backward-compatible wrapper for retrieving videos from a channel.

        Args:
            channel_id: YouTube channel ID
            limit: Maximum number of videos to return
            sort_by: Sort criteria ('view_count' or 'date')

        Returns:
            List of VideoMetadata objects
        """
        videos = self.get_latest_videos(channel_id, limit=max(limit, 10))

        if sort_by == "view_count":
            videos.sort(key=lambda video: video.view_count, reverse=True)
        else:
            videos.sort(
                key=lambda video: video.published_at or datetime.min,
                reverse=True,
            )

        return videos[:limit]
    
    def _get_video_info(self, video_id: str) -> Optional[VideoMetadata]:
        """
        Get detailed information about a single video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            VideoMetadata object or None
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        opts = {
            **self.ydl_opts,
            "extract_flat": False,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                # Parse upload date
                published_at = None
                if info.get('upload_date'):
                    try:
                        published_at = datetime.strptime(info['upload_date'], '%Y%m%d')
                    except ValueError:
                        pass
                
                return VideoMetadata(
                    video_id=video_id,
                    title=info.get('title', 'Unknown'),
                    channel_id=info.get('channel_id', ''),
                    channel_name=info.get('uploader', info.get('channel', 'Unknown')),
                    view_count=info.get('view_count', 0) or 0,
                    duration_seconds=info.get('duration', 0) or 0,
                    published_at=published_at,
                    thumbnail_url=info.get('thumbnail'),
                    url=url,
                )
        except Exception as e:
            logger.error(f"Failed to get video info for {video_id}: {e}")
            return None

    def get_video_info(self, url_or_id: str) -> VideoMetadata:
        """
        Get detailed metadata for a single video.

        Args:
            url_or_id: YouTube video URL or ID

        Returns:
            VideoMetadata object
        """
        video_id = self.extract_video_id(url_or_id)
        video_info = self._get_video_info(video_id)
        if not video_info:
            raise ValueError(f"Could not fetch video info for: {url_or_id}")

        return video_info
    
    def get_transcript(
        self,
        video_id: str,
        languages: Optional[list[str]] = None
    ) -> Optional[str]:
        """
        Get transcript for a YouTube video using yt-dlp.
        
        Args:
            video_id: YouTube video ID
            languages: List of language codes to try (default from settings)
            
        Returns:
            Transcript text or None if unavailable
        """
        if languages is None:
            languages = settings.transcript_language_list
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create temp directory for subtitles
        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = os.path.join(tmp_dir, "subtitle")
            
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": languages,
                "subtitlesformat": "json3",
                "outtmpl": subtitle_file,
            }
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                
                # Find the subtitle file
                transcript_text = None
                for lang in languages + ['en']:
                    json_file = f"{subtitle_file}.{lang}.json3"
                    if os.path.exists(json_file):
                        transcript_text = self._parse_json3_subtitle(json_file)
                        if transcript_text:
                            break
                
                # Try any subtitle file if specific language not found
                if not transcript_text:
                    for file in os.listdir(tmp_dir):
                        if file.endswith('.json3'):
                            json_file = os.path.join(tmp_dir, file)
                            transcript_text = self._parse_json3_subtitle(json_file)
                            if transcript_text:
                                break
                
                if transcript_text:
                    logger.info(f"Got transcript for {video_id}: {len(transcript_text)} chars")
                    return transcript_text
                
                logger.warning(f"No transcript found for video {video_id}")
                return self._get_transcript_from_api(video_id, languages)
                
            except Exception as e:
                logger.error(f"Failed to get transcript for {video_id}: {e}")
                fallback_transcript = self._get_transcript_from_api(video_id, languages)
                if fallback_transcript:
                    return fallback_transcript
                return None

    def _get_transcript_from_api(
        self,
        video_id: str,
        languages: list[str]
    ) -> Optional[str]:
        """
        Fallback transcript fetch using youtube-transcript-api.

        Args:
            video_id: YouTube video ID
            languages: Language codes to try

        Returns:
            Transcript text or None
        """
        try:
            transcript_items = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=languages,
            )
            texts = [
                item.get("text", "").strip()
                for item in transcript_items
                if item.get("text", "").strip()
            ]
            transcript = " ".join(texts).strip()
            if transcript:
                logger.info(f"Got transcript from API fallback for {video_id}")
                return self._clean_transcript_text(transcript)
        except Exception as e:
            logger.warning(f"Transcript API fallback failed for {video_id}: {e}")

        return None
    
    def _parse_json3_subtitle(self, file_path: str) -> Optional[str]:
        """
        Parse JSON3 subtitle file into plain text.
        
        Args:
            file_path: Path to JSON3 subtitle file
            
        Returns:
            Transcript text or None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            texts = []
            events = data.get('events', [])
            
            for event in events:
                segs = event.get('segs', [])
                for seg in segs:
                    text = seg.get('utf8', '').strip()
                    if text and text != '\n':
                        texts.append(text)
            
            if not texts:
                return None
            
            # Join and clean
            text = ' '.join(texts)
            return self._clean_transcript_text(text)

        except Exception as e:
            logger.error(f"Failed to parse subtitle file {file_path}: {e}")
            return None

    def _clean_transcript_text(self, text: str) -> Optional[str]:
        """
        Normalize transcript text into a plain readable string.

        Args:
            text: Raw transcript text

        Returns:
            Cleaned transcript or None if empty
        """
        cleaned_text = re.sub(r'\s+', ' ', text)
        cleaned_text = re.sub(r'\[Music\]', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\[Applause\]', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = cleaned_text.strip()
        return cleaned_text if cleaned_text else None
