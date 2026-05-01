"""
Channel input component for Streamlit UI.
"""

import re
import streamlit as st


def render_channel_input() -> tuple[str, int]:
    """
    Render channel input form.
    
    Returns:
        Tuple of (channel_url, max_videos)
    """
    st.subheader("Enter YouTube Channel or Video")

    # Channel URL input
    channel_url = st.text_input(
        "YouTube URL, Handle, or ID",
        placeholder="https://www.youtube.com/@fireship or https://www.youtube.com/watch?v=... or @fireship",
        help="Enter a channel URL, @handle, channel ID, video URL, or video ID"
    )
    
    # Validate input format
    if channel_url:
        is_valid = validate_channel_input(channel_url)
        if is_valid:
            st.success("Valid YouTube input")
        else:
            st.warning("Please enter a valid YouTube channel or video URL, handle, or ID")

    # Number of videos
    max_videos = st.slider(
        "Number of latest videos to fetch",
        min_value=1,
        max_value=20,
        value=5,
        help="For channels, fetch this many latest videos before choosing what to process"
    )
    
    return channel_url, max_videos


def validate_channel_input(input_str: str) -> bool:
    """
    Validate if the input looks like a valid channel URL or ID.
    
    Args:
        input_str: User input string
        
    Returns:
        True if valid format
    """
    input_str = input_str.strip()
    
    # Channel ID format (UC + 22 chars)
    if re.match(r'^UC[\w-]{22}$', input_str):
        return True

    # Video ID format (11 chars)
    if re.match(r'^[A-Za-z0-9_-]{11}$', input_str):
        return True

    # @handle format
    if input_str.startswith('@') and len(input_str) > 1:
        return True

    # YouTube URL patterns
    youtube_patterns = [
        r'youtube\.com/channel/',
        r'youtube\.com/@',
        r'youtube\.com/c/',
        r'youtube\.com/user/',
        r'youtube\.com/watch\?v=',
        r'youtube\.com/shorts/',
        r'youtube\.com/live/',
        r'youtu\.be/',
    ]
    
    for pattern in youtube_patterns:
        if re.search(pattern, input_str):
            return True
    
    return False


def render_saved_channels(channels: list) -> str:
    """
    Render saved channels selector.
    
    Args:
        channels: List of saved channel dicts
        
    Returns:
        Selected channel ID or empty string
    """
    if not channels:
        st.info("No saved channels yet. Process a channel to save it.")
        return ""
    
    st.subheader("Or Select Saved Channel")
    
    # Create options
    options = ["Select a channel..."]
    for ch in channels:
        name = ch.get('channel_name', 'Unknown')
        ch_id = ch.get('channel_id', '')
        last = ch.get('last_processed', 'Never')
        if last and last != 'Never':
            last = last.split('T')[0]  # Just the date
        options.append(f"{name} (last: {last})")
    
    selected_idx = st.selectbox(
        "Saved Channels",
        range(len(options)),
        format_func=lambda i: options[i]
    )
    
    if selected_idx > 0:
        return channels[selected_idx - 1].get('channel_id', '')
    
    return ""
