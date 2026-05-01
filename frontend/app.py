"""
Streamlit frontend for YouTube-to-Notion Guide Generator.
"""

import os
import sys
from pathlib import Path

import streamlit as st

# Add project root to path for imports
FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRONTEND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from frontend.api_client import APIClient
from frontend.components.channel_input import render_channel_input, render_saved_channels
from frontend.components.results_display import (
    render_notion_links,
    render_results,
    render_summary_card,
    render_video_selection,
)


st.set_page_config(
    page_title="YouTube to Notion Guide Generator",
    page_icon=":books:",
    layout="wide"
)


def _initialize_state() -> None:
    """Initialize Streamlit session state keys used by the app."""
    st.session_state.setdefault("discovery_response", None)
    st.session_state.setdefault("discovery_source_input", "")
    st.session_state.setdefault("last_results", None)


def _run_processing(
    api_client: APIClient,
    source_input: str,
    selected_video_ids: list[str],
    notion_db_id: str,
    max_videos: int,
    llm_provider: str,
    llm_model: str,
) -> None:
    """Process selected videos and persist the response in session state."""
    with st.spinner("Processing videos... This may take a minute."):
        try:
            response = api_client.process_videos(
                source_input=source_input,
                selected_video_ids=selected_video_ids,
                notion_database_id=notion_db_id if notion_db_id else None,
                max_videos=max_videos,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            st.session_state["last_results"] = response
            render_summary_card(
                response.get("summary", {}),
                response.get("channel_name", "Unknown"),
            )
        except Exception as e:
            st.error(f"Processing failed: {e}")
            st.session_state["last_results"] = None


def main():
    """Main application entry point."""
    _initialize_state()

    st.title("YouTube to Notion Guide Generator")
    st.markdown("""
    Turn YouTube channel uploads or single video links into actionable notes and Notion-ready guides.

    **How it works:**
    1. Enter a YouTube channel handle, channel URL, video URL, or ID
    2. Fetch the latest videos and choose what you want to process
    3. Transcribe the selected videos, generate actionable notes, and create Notion pages
    """)

    api_client = APIClient()

    with st.sidebar:
        st.header("Configuration")

        health = api_client.health_check()
        services = health.get("services", {})
        resolved_base_url = health.get("base_url", api_client.base_url)
        if health.get("status") == "healthy":
            st.success("Backend: Connected")
            st.caption(f"Using backend: `{resolved_base_url}`")
        elif health.get("status") == "degraded":
            st.warning("Backend: Degraded")
            st.caption(f"Using backend: `{resolved_base_url}`")
            for name, status in services.items():
                if name != "active_llm_provider" and status != "ok":
                    st.caption(f"- {name}: {status}")
        else:
            st.error("Backend: Not connected")
            st.caption(
                "Start the backend with: `uvicorn backend.main:app --host 127.0.0.1 --port 8000`"
            )
            candidate_urls = health.get("candidate_urls", [])
            if candidate_urls:
                st.caption(f"Tried: `{', '.join(candidate_urls)}`")
            if health.get("error"):
                st.caption(f"Connection error: `{health['error']}`")
            st.stop()

        st.divider()
        st.subheader("AI Model")

        active_provider = services.get("active_llm_provider", "openrouter")
        provider_options = ["openrouter", "gemini"]
        provider_index = (
            provider_options.index(active_provider)
            if active_provider in provider_options
            else 0
        )
        llm_provider = st.selectbox(
            "Provider",
            provider_options,
            index=provider_index,
            key="llm_provider",
            format_func=lambda value: "OpenRouter" if value == "openrouter" else "Gemini",
            help="Choose which AI provider should synthesize the Notion guide for this run.",
        )

        model_options = {
            "openrouter": [
                "openrouter/free",
                "openai/gpt-4o-mini",
                "google/gemini-2.5-flash",
            ],
            "gemini": [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.5-pro",
            ],
        }
        default_model = model_options[llm_provider][0]
        llm_model = st.selectbox(
            "Model",
            model_options[llm_provider],
            index=0,
            key=f"llm_model_{llm_provider}",
            help="Select the model to use for transcript analysis and guide generation.",
        )

        custom_model = st.text_input(
            "Custom model ID (optional)",
            placeholder=default_model,
            key=f"custom_model_{llm_provider}",
            help="Use this only if your provider supports a model that is not listed above.",
        ).strip()
        if custom_model:
            llm_model = custom_model

        provider_status = services.get(llm_provider, "unknown")
        llm_ready = provider_status == "ok"
        if provider_status == "ok":
            st.success(f"{llm_provider.title()}: Ready")
        else:
            st.warning(f"{llm_provider.title()}: {provider_status}")

        st.caption(f"Current run will use `{llm_model}`.")

        st.divider()
        st.subheader("Notion Setup")

        notion_db_id = st.text_input(
            "Notion Database ID (optional)",
            placeholder="Leave empty to auto-create",
            help="If you already have a database, enter its ID here. Otherwise the backend will create or reuse one."
        )

        if st.button("Setup/Verify Database"):
            with st.spinner("Setting up Notion database..."):
                try:
                    result = api_client.setup_notion()
                    st.success("Database ready")
                    st.markdown(f"[Open Database]({result.get('database_url', '#')})")
                except Exception as e:
                    st.error(f"Setup failed: {e}")

        st.divider()

        try:
            channels_response = api_client.get_channels()
            saved_channels = channels_response.get("channels", [])
        except Exception:
            saved_channels = []

        selected_channel_id = render_saved_channels(saved_channels)

    col1, col2 = st.columns([1, 1])

    with col1:
        source_input, max_videos = render_channel_input()

        if selected_channel_id and not source_input:
            source_input = selected_channel_id
            st.info(f"Using saved channel: {selected_channel_id}")

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            fetch_button = st.button(
                "Fetch Latest Videos",
                type="primary",
                disabled=not source_input,
                use_container_width=True,
            )
        with button_col2:
            quick_process_button = st.button(
                "Process Latest Now",
                disabled=not source_input or not llm_ready,
                use_container_width=True,
            )

    with col2:
        st.subheader("What Happens")
        st.markdown("""
        - Channel input: the app fetches the latest uploads from that handle or channel.
        - Video input: the app processes that one video directly.
        - After discovery, you can choose exactly which videos to turn into notes.
        - Each processed video becomes a structured Notion page with steps, tools, and action items.
        """)

    if fetch_button and source_input:
        with st.spinner("Fetching latest videos..."):
            try:
                discovery_response = api_client.discover_videos(
                    source_input=source_input,
                    max_videos=max_videos,
                )
                st.session_state["discovery_response"] = discovery_response
                st.session_state["discovery_source_input"] = source_input
                st.success(discovery_response.get("message", "Videos fetched successfully."))
            except Exception as e:
                st.error(f"Could not fetch videos: {e}")
                st.session_state["discovery_response"] = None
                st.session_state["discovery_source_input"] = ""

    if quick_process_button and source_input:
        _run_processing(
            api_client=api_client,
            source_input=source_input,
            selected_video_ids=[],
            notion_db_id=notion_db_id,
            max_videos=max_videos,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )

    discovery_response = st.session_state.get("discovery_response")
    discovery_matches_input = (
        discovery_response
        and st.session_state.get("discovery_source_input") == source_input
    )

    if discovery_response and not discovery_matches_input and source_input:
        st.info("The input changed. Fetch the latest videos again to refresh the selection list.")

    if discovery_matches_input:
        st.divider()
        selected_video_ids = render_video_selection(discovery_response)
        process_selected_button = st.button(
            "Process Selected Videos",
            disabled=not selected_video_ids or not llm_ready,
            use_container_width=True,
        )

        if process_selected_button:
            _run_processing(
                api_client=api_client,
                source_input=source_input,
                selected_video_ids=selected_video_ids,
                notion_db_id=notion_db_id,
                max_videos=max_videos,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )

    if st.session_state.get("last_results"):
        st.divider()
        render_results(st.session_state["last_results"])

        st.divider()
        render_notion_links(st.session_state["last_results"].get("results", []))


if __name__ == "__main__":
    main()
