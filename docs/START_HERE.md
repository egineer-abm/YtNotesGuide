# Start Here

Welcome to the YouTube to Notion Guide Generator documentation.

This app is an assistant for turning YouTube videos into organized Notion notes. Paste a YouTube channel or a single video, choose which videos to process, select an AI engine such as OpenRouter or Gemini, and get structured Notion pages with summaries, terms, tools, steps, code snippets, links, and timestamps.

## The Short Version

The app does four jobs:

1. Finds videos from a YouTube channel or direct video link.
2. Reads the available transcript.
3. Uses OpenRouter or Gemini to write a structured guide.
4. Saves the guide into Notion and returns the created page links.

The best starting point is the root [README.md](../README.md). It includes the product overview, local setup, environment variables, API reference, troubleshooting, and deployment notes.

## What You Need

- Python 3.10 or newer
- A Notion integration token
- One or both AI provider keys:
  - OpenRouter API key
  - Gemini API key
- A Notion page or database shared with your integration

## First Local Run

Install dependencies from the project root:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```bash
NOTION_API_KEY=secret_your_notion_integration_token
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1_your_openrouter_key
OPENROUTER_MODEL=openai/gpt-4o-mini

# Optional Gemini support
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
```

Run the backend:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend in another terminal:

```bash
streamlit run frontend/app.py
```

Open:

```text
http://localhost:8501
```

## User Workflow

1. Open the Streamlit app.
2. Check that the sidebar says the backend is connected.
3. Choose `OpenRouter` or `Gemini`.
4. Choose a listed model or enter a custom model ID.
5. Paste a YouTube channel or video link.
6. Fetch videos, then select the ones you want.
7. Process selected videos.
8. Open the Notion links returned by the app.

## Documentation Map

| Document | Start Here When You Need |
| --- | --- |
| [README.md](../README.md) | Complete product, setup, usage, API, and troubleshooting documentation |
| [RENDER_SETUP.md](RENDER_SETUP.md) | A Render deployment walkthrough |
| [RENDER_QUICK_REFERENCE.md](RENDER_QUICK_REFERENCE.md) | Quick deployment commands and settings |
| [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) | A deeper deployment architecture explanation |
| [DEPLOYMENT_CHECKLIST.txt](DEPLOYMENT_CHECKLIST.txt) | A step-by-step deployment checklist |
| [DEPLOYMENT_INDEX.md](DEPLOYMENT_INDEX.md) | Navigation for the older deployment document set |

## Important Note About Older Docs

Some legacy deployment notes in this folder were written before the app moved to OpenRouter and Gemini. If a document mentions `GROQ_API_KEY`, use the current provider variables instead:

```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1_your_openrouter_key
OPENROUTER_MODEL=openai/gpt-4o-mini
```

or:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
```

Notion configuration remains the same:

```bash
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=optional_existing_database_id
```

## Success Looks Like

- Backend `/health` returns `healthy` or clearly shows which provider is missing.
- Streamlit loads at `http://localhost:8501`.
- You can fetch videos from a channel or direct video input.
- Selected videos process without transcript or provider errors.
- Results show Notion page links.
- The Notion pages contain structured guide sections instead of raw transcript dumps.

## Recommended Next Step

Read [README.md](../README.md), then run the app locally before deploying it.
