# Deployment Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                       │
│              (Internet Connection)                      │
└────────────────────────────┬────────────────────────────┘
                             │
                    HTTPS Request/Response
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────────┐            ┌──────────────────────┐
│   STREAMLIT FRONTEND │            │   FASTAPI BACKEND    │
│  (Render Service)    │            │  (Render Service)    │
│ youtube-guide-       │            │ youtube-guide-       │
│    frontend          │            │    backend           │
│                      │            │                      │
│  Port: 8501 ($PORT)  │            │  Port: 8000 ($PORT)  │
│  Python 3            │            │  Python 3            │
│  streamlit run ...   │            │  uvicorn ...         │
└──────────────────────┘            └──────────────────────┘
        │                                     │
        └─────────┬──────────────────────────┘
                  │
        HTTP (internal Render network)
                  │
    Environment: BACKEND_URL env var
                  │
    https://youtube-guide-backend.onrender.com
```

---

## Data Flow - Processing a YouTube Channel

```
┌─────────────────────────────────────────────────────────┐
│ 1. USER SUBMITS                                         │
│    Channel URL: https://www.youtube.com/@fireship       │
│    Max Videos: 5                                        │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 2. FRONTEND (Streamlit)                                 │
│    - Displays loading spinner                           │
│    - Sends HTTP POST to backend                         │
│    - Payload: {channel_url, max_videos}                │
└─────────────┬───────────────────────────────────────────┘
              │
    POST /api/v1/process-channel
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 3. BACKEND (FastAPI)                                    │
│    ├─ Receive request                                   │
│    ├─ Validate inputs                                   │
│    └─ Start processing                                  │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 4. YOUTUBE SERVICE                                      │
│    ├─ Extract channel ID from URL                       │
│    ├─ Fetch channel info                                │
│    ├─ Get top 5 videos (by view count)                 │
│    ├─ For each video:                                   │
│    │  ├─ Get video metadata                             │
│    │  └─ Extract transcript (youtube-transcript-api)   │
│    └─ Return videos with transcripts                    │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 5. GROQ LLM SERVICE                                     │
│    For each video:                                      │
│    ├─ Chunk transcript (max 30K tokens)                │
│    ├─ Send to Groq API (mixtral-8x7b)                 │
│    ├─ LLM generates:                                    │
│    │  ├─ Big Idea summary                               │
│    │  ├─ Key Terms                                      │
│    │  ├─ 5-Minute Actions                               │
│    │  ├─ Implementation Steps                           │
│    │  └─ Code Snippets                                  │
│    └─ Return structured guide                           │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 6. NOTION SERVICE                                       │
│    For each guide:                                      │
│    ├─ Format guide as Notion blocks                     │
│    ├─ Create new Notion page via API                    │
│    ├─ Set properties (title, date, etc.)               │
│    ├─ Add formatted content                             │
│    └─ Return page URL                                   │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 7. STORAGE SERVICE                                      │
│    ├─ Save channel info to channels.json                │
│    └─ Keep processing history                           │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 8. BACKEND RESPONSE                                     │
│    Return JSON:                                         │
│    {                                                    │
│      "channel_id": "UCrF...",                          │
│      "channel_name": "Fireship",                        │
│      "results": [{                                      │
│        "video_id": "xyz123",                            │
│        "video_title": "...",                            │
│        "status": "success",                             │
│        "notion_page_url": "https://notion.so/page",    │
│        "processing_time_seconds": 45.2                  │
│      }, ...],                                           │
│      "summary": {                                       │
│        "total": 5,                                      │
│        "successful": 5,                                 │
│        "failed": 0                                      │
│      }                                                  │
│    }                                                    │
└─────────────┬───────────────────────────────────────────┘
              │
    HTTP 200 OK with response body
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 9. FRONTEND                                             │
│    ├─ Display summary card                              │
│    │  - Total: 5 videos processed                       │
│    │  - Successful: 5 ✓                                 │
│    │  - Failed: 0                                       │
│    ├─ Show each video result                            │
│    ├─ Display Notion page links (clickable)             │
│    └─ Store results in session state                    │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ 10. USER CLICKS NOTION LINKS                            │
│     → Opens Notion database with generated pages        │
│     → Views structured Application Guides               │
│     → Can organize, share, and modify in Notion         │
└─────────────────────────────────────────────────────────┘
```

---

## Render Service Architecture

### Local Development Setup
```
Your Computer
│
├─ Backend (Terminal 1)
│  └─ uvicorn backend.main:app --host localhost --port 8000
│
├─ Frontend (Terminal 2)
│  └─ streamlit run frontend/app.py
│
└─ Browser
   └─ http://localhost:8501
```

### Production on Render
```
Render.com (Cloud)
│
├─ Web Service 1: youtube-guide-backend
│  ├─ Repository: abm1119/ytvideoguides
│  ├─ Branch: main
│  ├─ Build: pip install -r requirements.txt
│  ├─ Start: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
│  ├─ Environment:
│  │  ├─ GROQ_API_KEY = gsk_...
│  │  ├─ NOTION_API_KEY = secret_...
│  │  └─ RENDER = true
│  └─ URL: https://youtube-guide-backend.onrender.com
│
├─ Web Service 2: youtube-guide-frontend
│  ├─ Repository: abm1119/ytvideoguides
│  ├─ Branch: main
│  ├─ Build: pip install -r requirements.txt
│  ├─ Start: streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
│  ├─ Environment:
│  │  └─ BACKEND_URL = https://youtube-guide-backend.onrender.com
│  └─ URL: https://youtube-guide-frontend.onrender.com
│
└─ User's Browser
   └─ https://youtube-guide-frontend.onrender.com
```

---

## External API Integration

```
┌─────────────────────────────────────────────────────────┐
│                   YOUR APPLICATION                      │
├─────────────────────────────────────────────────────────┤
│ Backend                   Frontend                      │
│ (FastAPI)                (Streamlit)                   │
└─────────────────────────────────────────────────────────┘
         │                         │
    ┌────┴────────┬────────┬───────┴─────┐
    ▼             ▼        ▼              ▼
┌───────┐   ┌───────┐  ┌───────┐   ┌─────────┐
│YouTube│   │ Groq  │  │Notion │   │Analytics│
│  API  │   │  API  │  │  API  │   │(future) │
└───────┘   └───────┘  └───────┘   └─────────┘
     │           │          │
     │           │          │
HTTP GET/POST    │      HTTP POST
Transcripts      │      Create Pages
Metadata         │      Set Properties
              HTTP POST
              LLM Requests
              Streaming
```

---

## Environment Variable Flow

```
Local Development (.env file)
├─ GROQ_API_KEY = gsk_...
├─ NOTION_API_KEY = secret_...
├─ BACKEND_HOST = localhost
├─ BACKEND_PORT = 8000
└─ STREAMLIT_PORT = 8501

                    ↓↓↓ Deployed to Render ↓↓↓

Backend Service Environment (Render Dashboard)
├─ GROQ_API_KEY = gsk_...         [Required]
├─ NOTION_API_KEY = secret_...    [Required]
├─ RENDER = true                  [Optional, enables prod CORS]
├─ BACKEND_HOST = 0.0.0.0         [Set by code]
├─ BACKEND_PORT = $PORT           [Set by Render]
└─ LOG_LEVEL = INFO               [Optional]

Frontend Service Environment (Render Dashboard)
├─ BACKEND_URL = https://youtube-guide-backend.onrender.com
└─ Other env vars inherited from code defaults
```

---

## Port Routing

### Local Development
```
Browser (localhost:8501)
    ↓
Streamlit (8501)
    ↓
APIClient calls → http://localhost:8000
    ↓
FastAPI Backend (8000)
```

### Production on Render
```
Browser (https://youtube-guide-frontend.onrender.com)
    ↓ HTTPS
Internet
    ↓
Render Load Balancer → Port $PORT → Container Port 8501
    ↓
Streamlit Frontend (8501)
    ↓
APIClient calls → $BACKEND_URL env var
    ↓
https://youtube-guide-backend.onrender.com
    ↓
Render Load Balancer → Port $PORT → Container Port 8000
    ↓
FastAPI Backend (8000)
```

---

## CORS Configuration

### Local Development
- Frontend: `http://localhost:8501`
- Backend allows: `localhost:8501`, `127.0.0.1:8501`

### Production
- Frontend: `https://youtube-guide-frontend.onrender.com`
- Backend allows: `https://*.onrender.com` (wildcard for flexibility)
- Plus: Custom `FRONTEND_URL` env var if needed

---

## Data Storage

### Ephemeral Storage (Render Free Tier)
```
Backend Service
├─ Filesystem (lost on restart)
│  └─ data/channels.json
│  └─ data/logs/
└─ Session/Memory

Lost when service:
- Restarts (every 24-48 hours)
- Gets redeployed
- Scales up/down
```

### Persistent Storage (Future Enhancement)
Options for upgrades:
- PostgreSQL (Render database)
- MongoDB (external)
- AWS S3 (file storage)
- Notion itself (primary storage)

---

## Health Check & Monitoring

```
Frontend                  Backend
   │                        │
   └─→ GET /health  ───→   │
       (every 30s)          │
                            ├─ Check Groq: Connected?
                            ├─ Check Notion: Connected?
                            └─ Return Status
                            
                      ←─── 200 OK
                      {
                        "status": "healthy",
                        "services": {
                          "groq": "ok",
                          "notion": "ok"
                        }
                      }
   │
   └─ Display "Backend: Connected" ✓
```

---

## Deployment Flow

```
Local Development
    ↓ (when ready)
    
git push origin main
    ↓ (GitHub webhook)
    
Render Detects Change
    ├─ Backend Service
    │  ├─ Git clone latest
    │  ├─ pip install -r requirements.txt (build.sh)
    │  └─ uvicorn backend.main:app ... (start)
    │
    └─ Frontend Service
       ├─ Git clone latest
       ├─ pip install -r requirements.txt (build.sh)
       └─ streamlit run frontend/app.py ... (start)

    Both services deploy in parallel
    
    ↓ (1-2 minutes)
    
Both services show "Live" ✓
    
    ↓ (user accesses)
    
Application Ready to Use
```

---

## Session Lifecycle

```
User → Opens https://youtube-guide-frontend.onrender.com
        ↓
   Streamlit initializes
        ↓
   APIClient created
        ↓
   Reads BACKEND_URL from environment
        ↓
   Makes GET /health to backend
        ↓
   Sidebar shows status
        ↓
   Ready to accept input

User → Enters channel URL, clicks "Process"
        ↓
   Frontend disables button, shows spinner
        ↓
   POST request to backend (5 min timeout)
        ↓
   Backend processes (30-120 seconds)
        ↓
   Backend returns results
        ↓
   Frontend displays:
        - Summary card
        - Result list
        - Notion links (clickable)
        ↓
   User → Clicks Notion link
           Opens Notion with generated page
```

