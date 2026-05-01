"""
API client for communicating with the FastAPI backend.
"""

import os
from urllib.parse import urlparse
from typing import Optional

import requests


class APIClient:
    """Client for interacting with the backend API."""

    def __init__(self, base_url: str = None):
        """
        Initialize API client.

        Args:
            base_url: Backend API base URL. Defaults to BACKEND_URL env var or local dev URLs.
        """
        configured_base_url = base_url or os.getenv("BACKEND_URL", "")
        self.candidate_urls = self._build_candidate_urls(configured_base_url)
        self.base_url = self.candidate_urls[0]
        self.session = requests.Session()
        self.timeout = 300  # 5 minutes for long operations

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize a base URL and strip any trailing slash."""
        normalized = url.strip().rstrip("/")
        if "://" not in normalized:
            normalized = f"http://{normalized}"
        return normalized

    def _build_candidate_urls(self, configured_base_url: str) -> list[str]:
        """Build the ordered list of backend URLs to try."""
        candidates: list[str] = []

        if configured_base_url.strip():
            normalized = self._normalize_url(configured_base_url)
            candidates.append(normalized)

            parsed = urlparse(normalized)
            if parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port is None:
                candidates.append(f"{parsed.scheme}://{parsed.hostname}:8000")
        else:
            candidates.extend(
                [
                    "http://127.0.0.1:8000",
                    "http://localhost:8000",
                    "http://127.0.0.1",
                    "http://localhost",
                ]
            )

        deduplicated: list[str] = []
        for candidate in candidates:
            if candidate not in deduplicated:
                deduplicated.append(candidate)

        return deduplicated

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        Send a request to the backend, trying local fallback URLs on connection failures.
        """
        errors: list[str] = []

        for base_url in self.candidate_urls:
            try:
                response = self.session.request(
                    method=method,
                    url=f"{base_url}{path}",
                    **kwargs,
                )
                response.raise_for_status()
                self.base_url = base_url
                return response
            except requests.exceptions.ConnectionError as exc:
                errors.append(f"{base_url}: {exc}")
                continue
            except requests.exceptions.Timeout as exc:
                errors.append(f"{base_url}: {exc}")
                continue
            except requests.exceptions.HTTPError as exc:
                detail = self._extract_error_detail(exc.response)
                if detail:
                    raise requests.exceptions.HTTPError(detail, response=exc.response) from exc
                raise

        raise requests.exceptions.ConnectionError(
            "Unable to reach backend. Tried: " + " | ".join(errors or self.candidate_urls)
        )

    def _extract_error_detail(self, response: requests.Response | None) -> str:
        """Extract a useful API error message from an HTTP response."""
        if response is None:
            return ""

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("error")
            if isinstance(detail, list):
                messages = []
                for item in detail:
                    if isinstance(item, dict):
                        location = ".".join(str(part) for part in item.get("loc", []))
                        message = item.get("msg", item)
                        messages.append(f"{location}: {message}" if location else str(message))
                    else:
                        messages.append(str(item))
                detail = "; ".join(messages)
            return str(detail) if detail else response.text

        return str(payload)

    def health_check(self) -> dict:
        """
        Check backend health status.

        Returns:
            Health status response
        """
        try:
            response = self._request(
                "GET",
                "/health",
                timeout=10
            )
            payload = response.json()
            payload["base_url"] = self.base_url
            payload["candidate_urls"] = self.candidate_urls
            return payload
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "services": {},
                "error": str(e),
                "base_url": self.base_url,
                "candidate_urls": self.candidate_urls,
            }

    def process_channel(
        self,
        channel_url: str,
        notion_database_id: Optional[str] = None,
        max_videos: int = 5,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> dict:
        """
        Process a YouTube channel.
        
        Args:
            channel_url: YouTube channel URL or ID
            notion_database_id: Optional Notion database ID
            max_videos: Maximum number of videos to process
            
        Returns:
            Processing result response
        """
        payload = {
            "channel_url": channel_url,
            "max_videos": max_videos
        }
        
        if notion_database_id:
            payload["notion_database_id"] = notion_database_id
        if llm_provider:
            payload["llm_provider"] = llm_provider
        if llm_model:
            payload["llm_model"] = llm_model
        
        response = self._request(
            "POST",
            "/api/v1/process-channel",
            json=payload,
            timeout=self.timeout
        )
        return response.json()

    def discover_videos(self, source_input: str, max_videos: int = 10) -> dict:
        """
        Discover latest videos for a channel or inspect a single video input.

        Args:
            source_input: YouTube channel/video URL, handle, or ID
            max_videos: Maximum number of latest channel videos to fetch

        Returns:
            Discovery response with source type and video list
        """
        response = self._request(
            "POST",
            "/api/v1/discover-videos",
            json={
                "source_input": source_input,
                "max_videos": max_videos,
            },
            timeout=60,
        )
        return response.json()

    def process_videos(
        self,
        source_input: str,
        selected_video_ids: list[str],
        notion_database_id: Optional[str] = None,
        max_videos: int = 5,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> dict:
        """
        Process selected videos from a channel or a single video input.

        Args:
            source_input: YouTube channel/video URL, handle, or ID
            selected_video_ids: Video IDs chosen by the user
            notion_database_id: Optional Notion database ID
            max_videos: Fallback number of latest videos to process

        Returns:
            Processing result response
        """
        payload = {
            "source_input": source_input,
            "selected_video_ids": selected_video_ids,
            "max_videos": max_videos,
        }

        if notion_database_id:
            payload["notion_database_id"] = notion_database_id
        if llm_provider:
            payload["llm_provider"] = llm_provider
        if llm_model:
            payload["llm_model"] = llm_model

        response = self._request(
            "POST",
            "/api/v1/process-videos",
            json=payload,
            timeout=self.timeout,
        )
        return response.json()

    def get_channels(self) -> dict:
        """
        Get list of saved channels.

        Returns:
            List of channels response
        """
        response = self._request(
            "GET",
            "/api/v1/channels",
            timeout=10
        )
        return response.json()

    def setup_notion(
        self,
        database_name: str = "Application Guides",
        parent_page_id: Optional[str] = None
    ) -> dict:
        """
        Set up Notion database.
        
        Args:
            database_name: Name for the database
            parent_page_id: Optional parent page ID
            
        Returns:
            Setup response with database ID and URL
        """
        payload = {"database_name": database_name}
        
        if parent_page_id:
            payload["parent_page_id"] = parent_page_id
        
        response = self._request(
            "POST",
            "/api/v1/notion/setup",
            json=payload,
            timeout=30
        )
        return response.json()

    def test_youtube(self, source_input: str) -> dict:
        """
        Test YouTube service.

        Args:
            source_input: YouTube channel or video input

        Returns:
            Test result with videos
        """
        response = self._request(
            "POST",
            "/api/v1/test-youtube",
            params={"source_input": source_input},
            timeout=60
        )
        return response.json()
