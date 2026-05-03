"""
Results display component for Streamlit UI.
"""

from datetime import datetime

import streamlit as st


def _format_date(value: str | None) -> str:
    """Format ISO timestamp strings for display."""
    if not value:
        return "Unknown date"

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return value


def _format_duration(duration_seconds: int | None) -> str:
    """Format video duration in a compact human-readable form."""
    if not duration_seconds:
        return "Unknown duration"

    hours, remainder = divmod(int(duration_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:d}:{seconds:02d}"


def render_results(response: dict):
    """
    Render processing results.
    
    Args:
        response: API response from process-channel endpoint
    """
    if not response:
        return
    
    channel_name = response.get('channel_name', 'Unknown')
    results = response.get('results', [])
    summary = response.get('summary', {})
    total_time = response.get('total_processing_time_seconds', 0)
    total_tokens = summary.get('total_tokens', 0)
    
    # Summary header
    st.subheader(f"Results for {channel_name}")
    
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Videos", summary.get('total', 0))
    
    with col2:
        st.metric("Successful", summary.get('successful', 0))
    
    with col3:
        st.metric("Failed", summary.get('failed', 0))
    
    with col4:
        st.metric("Time (s)", f"{total_time:.1f}")

    with col5:
        st.metric("Tokens", f"{total_tokens:,}")
    
    st.divider()
    
    # Individual results
    for result in results:
        render_video_result(result)


def render_video_result(result: dict):
    """
    Render individual video result.
    
    Args:
        result: Single video processing result
    """
    status = result.get('status', 'unknown')
    title = result.get('video_title', 'Unknown Video')
    views = result.get('views', 0)
    video_url = result.get('video_url')
    published_at = result.get('published_at')
    duration_seconds = result.get('duration_seconds')
    notion_url = result.get('notion_page_url')
    total_tokens = result.get('total_tokens', 0)
    prompt_tokens = result.get('prompt_tokens', 0)
    completion_tokens = result.get('completion_tokens', 0)
    error = result.get('error')
    proc_time = result.get('processing_time_seconds', 0)
    
    # Status indicator
    if status == 'success':
        icon = "Success:"
        color = "green"
    elif status == 'failed':
        icon = "Failed:"
        color = "red"
    else:  # skipped
        icon = "Skipped:"
        color = "orange"
    
    # Result card
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{icon} {title}**")
            st.caption(
                f"Views: {views:,} | Published: {_format_date(published_at)} | Duration: {_format_duration(duration_seconds)}"
            )

            if video_url:
                st.markdown(f"[Open Video]({video_url})")
            
            if notion_url:
                st.markdown(f"[Open in Notion]({notion_url})")

            if error:
                st.error(f"Error: {error}")
        
        with col2:
            if proc_time:
                st.caption(f"{proc_time:.1f}s")
            if total_tokens:
                st.caption(f"{total_tokens:,} tokens")
                st.caption(f"In {prompt_tokens:,} / Out {completion_tokens:,}")
        
        st.divider()


def render_summary_card(summary: dict, channel_name: str):
    """
    Render summary card.
    
    Args:
        summary: Summary statistics
        channel_name: Channel name
    """
    successful = summary.get('successful', 0)
    total = summary.get('total', 0)
    
    if successful == total and total > 0:
        st.success(f"Successfully processed all {total} videos from {channel_name}!")
    elif successful > 0:
        st.warning(f"Processed {successful}/{total} videos from {channel_name}")
    else:
        st.error(f"Failed to process any videos from {channel_name}")


def render_video_selection(discovery_response: dict) -> list[str]:
    """
    Render a selectable list of discovered videos.

    Args:
        discovery_response: API response from discover-videos endpoint

    Returns:
        Selected video IDs
    """
    videos = discovery_response.get("videos", [])
    source_type = discovery_response.get("source_type", "channel")
    channel_name = discovery_response.get("channel_name", "Unknown")

    if not videos:
        st.warning("No videos were found for this input.")
        return []

    if source_type == "video":
        st.info("Single video detected. It is ready to process.")
    else:
        st.subheader(f"Latest Videos for {channel_name}")

    label_to_id: dict[str, str] = {}
    default_labels: list[str] = []

    for video in videos:
        base_label = (
            f"{video.get('title', 'Untitled')} | "
            f"{_format_date(video.get('published_at'))} | "
            f"{video.get('view_count', 0):,} views | "
            f"{_format_duration(video.get('duration_seconds'))}"
        )
        video_id = video.get("video_id", "")
        label = f"{base_label} | ID: {video_id}" if video_id else base_label
        label_to_id[label] = video.get("video_id", "")
        default_labels.append(label)

    selected_labels = st.multiselect(
        "Choose videos to process",
        options=default_labels,
        default=default_labels,
        help="You can process all discovered videos or narrow the list before generating notes and Notion pages."
    )

    return [label_to_id[label] for label in selected_labels if label_to_id.get(label)]


def render_notion_links(results: list):
    """
    Render list of Notion page links.
    
    Args:
        results: List of video results
    """
    successful = [r for r in results if r.get('status') == 'success' and r.get('notion_page_url')]
    
    if not successful:
        return
    
    st.subheader("Notion Pages Created")
    
    for result in successful:
        title = result.get('video_title', 'Unknown')
        url = result.get('notion_page_url')
        st.markdown(f"- [{title}]({url})")
