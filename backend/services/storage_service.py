"""
Storage service for local data persistence.
Handles channel storage using JSON files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.models import ChannelInfo
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for local data storage using JSON files."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize storage service.
        
        Args:
            data_dir: Directory for data files (default: project/data)
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        
        self.data_dir = data_dir
        self.channels_file = self.data_dir / "channels.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize channels file if needed
        if not self.channels_file.exists():
            self._write_channels([])
    
    def save_channel(self, channel_data: dict) -> None:
        """
        Save or update a channel in storage.
        
        Args:
            channel_data: Channel information dictionary
        """
        channels = self._read_channels()
        
        # Update last_processed timestamp
        channel_data['last_processed'] = datetime.utcnow().isoformat()
        
        # Check if channel exists
        channel_id = channel_data.get('channel_id')
        existing_idx = None
        for i, ch in enumerate(channels):
            if ch.get('channel_id') == channel_id:
                existing_idx = i
                break
        
        if existing_idx is not None:
            channels[existing_idx] = channel_data
        else:
            channels.append(channel_data)
        
        self._write_channels(channels)
        logger.info(f"Saved channel: {channel_data.get('channel_name', channel_id)}")
    
    def get_all_channels(self) -> list[ChannelInfo]:
        """
        Get all saved channels.
        
        Returns:
            List of ChannelInfo objects
        """
        channels = self._read_channels()
        
        result = []
        for ch in channels:
            try:
                # Parse last_processed if present
                last_processed = None
                if ch.get('last_processed'):
                    try:
                        last_processed = datetime.fromisoformat(ch['last_processed'])
                    except (ValueError, TypeError):
                        pass
                
                result.append(ChannelInfo(
                    channel_id=ch.get('channel_id', ''),
                    channel_name=ch.get('channel_name', 'Unknown'),
                    subscriber_count=ch.get('subscriber_count'),
                    video_count=ch.get('video_count'),
                    last_processed=last_processed
                ))
            except Exception as e:
                logger.warning(f"Failed to parse channel data: {e}")
        
        return result
    
    def get_channel(self, channel_id: str) -> Optional[ChannelInfo]:
        """
        Get a specific channel by ID.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            ChannelInfo or None if not found
        """
        channels = self.get_all_channels()
        
        for ch in channels:
            if ch.channel_id == channel_id:
                return ch
        
        return None
    
    def delete_channel(self, channel_id: str) -> bool:
        """
        Delete a channel from storage.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            True if deleted, False if not found
        """
        channels = self._read_channels()
        
        initial_len = len(channels)
        channels = [ch for ch in channels if ch.get('channel_id') != channel_id]
        
        if len(channels) < initial_len:
            self._write_channels(channels)
            logger.info(f"Deleted channel: {channel_id}")
            return True
        
        return False
    
    def _read_channels(self) -> list[dict]:
        """
        Read channels from JSON file.
        
        Returns:
            List of channel dictionaries
        """
        try:
            with open(self.channels_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_channels(self, channels: list[dict]) -> None:
        """
        Write channels to JSON file.
        
        Args:
            channels: List of channel dictionaries
        """
        with open(self.channels_file, 'w', encoding='utf-8') as f:
            json.dump(channels, f, indent=2, ensure_ascii=False)
