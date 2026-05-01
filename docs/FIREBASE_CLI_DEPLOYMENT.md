# Firebase CLI Deployment Guide

Firebase CLI provides a unified way to deploy both frontend and backend to Firebase services.

---

## Installation & Setup

### 1. Install Firebase CLI
```bash
# Windows, Mac, or Linux
npm install -g firebase-tools

# Verify installation
firebase --version
```

### 2. Initialize Firebase Project
```bash
# From project root directory
firebase init

# You'll see interactive prompts, select:
# ✓ Functions (for backend API)
# ✓ Hosting (optional, for frontend)
# ✓ Yes, associate with existing Google Cloud project
```

---

## Option A: Deploy Backend to Cloud Run via Firebase CLI

### Step 1: Create firebase.json (Backend Config)

Create `firebase.json` in project root:

```json
{
  "functions": {
    "source": "backend",
    "runtime": "python311",
    "codebase": "default"
  },
  "hosting": {
    "public": "frontend",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**",
      "**/__pycache__"
    ]
  }
}
```

### Step 2: Create .firebaserc

Create `.firebaserc` in project root:

```json
{
  "projects": {
    "default": "your-project-id"
  },
  "targets": {
    "your-project-id": {
      "hosting": {
        "frontend": ["youtube-guide-frontend"]
      }
    }
  }
}
```

Replace `your-project-id` with your actual Google Cloud project ID.

### Step 3: Create functions/main.py

Firebase Functions requires specific structure. Create `functions/main.py`:

```python
"""
Firebase Cloud Function wrapper for FastAPI backend
"""

import functions_framework
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

# Import your FastAPI app
from backend.main import app

# Add CORS for Firebase Hosting frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000",
        "http://localhost:3000",
        f"https://{os.getenv('FIREBASE_PROJECT')}.web.app",
        f"https://{os.getenv('FIREBASE_PROJECT')}.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@functions_framework.http
def api(request):
    """HTTP Cloud Function for FastAPI"""
    with app.router.lifespan_context(app):
        return app(request)
```

### Step 4: Create functions/requirements.txt

```
fastapi>=0.109.0
uvicorn>=0.27.0
functions-framework>=3.3.0
yt-dlp>=2024.1.0
youtube-transcript-api>=0.6.2
groq>=0.4.0
notion-client>=2.2.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
tiktoken>=0.5.0
python-dotenv>=1.0.0
requests>=2.31.0
httpx>=0.26.0
```

### Step 5: Authenticate & Deploy

```bash
# Login to Firebase
firebase login

# Deploy backend as Cloud Function
firebase deploy --only functions

# Or deploy everything (functions + hosting)
firebase deploy
```

---

## Option B: Deploy Backend to Cloud Run via Firebase CLI (Recommended)

### Pros Over Cloud Functions
- ✅ No 15-minute timeout limit (supports 30-120 second processing)
- ✅ Full FastAPI features work
- ✅ Better performance
- ✅ Custom Docker support

### Setup

Create `firebase.json`:

```json
{
  "functions": [
    {
      "source": "backend",
      "codebase": "backend",
      "runtime": "python311"
    }
  ],
  "hosting": {
    "public": "frontend",
    "cleanUrls": true,
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

### Create Cloud Run Config

Create `backend/.gcloudignore`:

```
.git
.gitignore
__pycache__
*.pyc
.env
.env.local
venv/
env/
*.log
```

### Deploy

```bash
# Deploy backend to Cloud Run with Firebase CLI
firebase deploy --only functions:api

# View logs
firebase functions:log
```

---

## Option C: Deploy via Docker + Firebase CLI (Best Practice)

### Create backend/Dockerfile (Already Done)

Your backend/Dockerfile is already set up for Cloud Run.

### Create cloudbuild.yaml (for Firebase)

Create `cloudbuild.yaml` in project root:

```yaml
steps:
  # Deploy backend to Cloud Run
  - name: 'gcr.io/cloud-builders/run'
    args:
      - 'deploy'
      - 'youtube-guide-backend'
      - '--source=.'
      - '--platform=managed'
      - '--region=us-central1'
      - '--allow-unauthenticated'
      - '--dockerfile=./backend/Dockerfile'
      - '--set-env-vars=GROQ_API_KEY=${_GROQ_API_KEY},NOTION_API_KEY=${_NOTION_API_KEY},ENVIRONMENT=production'
    env:
      - 'CLOUDSDK_RUN_REGION=us-central1'

  # Deploy frontend to Firebase Hosting (optional)
  - name: 'gcr.io/cloud-builders/firebase'
    args: ['deploy', '--only', 'hosting']

substitutions:
  _GROQ_API_KEY: 'gsk_YOUR_KEY'
  _NOTION_API_KEY: 'secret_YOUR_KEY'
```

### Deploy via Firebase CLI

```bash
firebase deploy
```

---

## Complete Setup for Firebase CLI (Recommended)

### Step 1: Install Firebase CLI

```bash
npm install -g firebase-tools
firebase login
```

### Step 2: Initialize Firebase

```bash
firebase init
# Select:
# - Functions
# - Hosting
# - Emulators (optional)
```

### Step 3: Create .firebaserc

```json
{
  "projects": {
    "default": "your-gcp-project-id"
  }
}
```

### Step 4: Create firebase.json

```json
{
  "functions": [
    {
      "source": "functions",
      "codebase": "default",
      "runtime": "python311",
      "entryPoint": "api"
    }
  ],
  "hosting": {
    "public": "frontend",
    "cleanUrls": true,
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

### Step 5: Create functions/main.py

```python
import functions_framework
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Your FastAPI app
app = FastAPI(
    title="YouTube-to-Notion Guide Generator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000",
        f"https://{os.getenv('FIREBASE_PROJECT')}.web.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy"}

@functions_framework.http
def api(request):
    """Wraps FastAPI for Cloud Functions"""
    return app(request)
```

### Step 6: Create functions/requirements.txt

```
fastapi>=0.109.0
functions-framework>=3.3.0
# ... rest of dependencies
```

### Step 7: Deploy

```bash
# Deploy everything
firebase deploy

# Or specific
firebase deploy --only functions
firebase deploy --only hosting
```

---

## Complete Example Setup

### Project Structure
```
ytvideoguides/
├── firebase.json                 # Firebase config
├── .firebaserc                   # Firebase project reference
├── cloudbuild.yaml              # Cloud Build config
├── backend/
│   ├── Dockerfile               # ✅ Already created
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── services/
│   └── utils/
├── functions/                    # Firebase Functions wrapper
│   ├── main.py                  # FastAPI wrapper
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── app.py
│   └── ...
└── requirements.txt              # Root level
```

---

## Deployment Commands

### First Time Setup
```bash
# 1. Install dependencies
npm install -g firebase-tools

# 2. Login
firebase login

# 3. Initialize project
firebase init

# 4. Configure .firebaserc and firebase.json
# (See examples above)
```

### Deploy Backend
```bash
# Deploy just backend (Cloud Functions)
firebase deploy --only functions

# Deploy backend with Docker/Cloud Run
firebase deploy --only run
```

### Deploy Frontend
```bash
# Deploy just frontend (Hosting)
firebase deploy --only hosting
```

### Deploy Everything
```bash
firebase deploy
```

### View Logs
```bash
# Cloud Functions logs
firebase functions:log

# Or via gcloud
gcloud functions logs read api --runtime python311 --limit 50
```

### Delete Service
```bash
firebase functions:delete api
```

---

## Environment Variables via Firebase CLI

### Set Variables
```bash
# For Cloud Functions
firebase functions:config:set groq.api_key="gsk_..." notion.api_key="secret_..."

# Or update via Google Cloud Console
gcloud functions deploy api --set-env-vars="GROQ_API_KEY=gsk_...,NOTION_API_KEY=secret_..."
```

### Access in Code
```python
import os

groq_key = os.getenv('GROQ_API_KEY')
notion_key = os.getenv('NOTION_API_KEY')
```

---

## Costs & Limitations

### Cloud Functions Tier (Free Tier)
- ✅ 2M invocations/month free
- ✅ 400,000 GB-seconds compute free
- ❌ 15-minute timeout (BAD for your 30-120s processing)
- ❌ Cold starts slower

### Cloud Run Tier (Recommended)
- ✅ 2M requests/month free
- ✅ No strict timeout (600s default)
- ✅ Better for long-running operations
- ✅ Better cold start performance

### Firebase Hosting Tier
- ✅ Unlimited free tier
- ✅ Perfect for Streamlit frontend
- ✅ CDN included

---

## Quick Start Commands

```bash
# Install
npm install -g firebase-tools

# Login
firebase login

# Check status
firebase projects:list

# Deploy
firebase deploy

# View logs
firebase functions:log

# Delete
firebase projects:delete your-project-id
```

---

## Recommended Architecture with Firebase CLI

```
Your Code (GitHub)
    ↓
firebase deploy (Firebase CLI)
    ├─→ Functions: Backend API (Cloud Functions/Run)
    ├─→ Hosting: Frontend (Firebase Hosting)
    └─→ Database: Firestore (optional)

Live at:
- https://your-project.web.app (Frontend)
- https://region-your-project.cloudfunctions.net/api (Backend)
```

---

## Next Steps

1. **Install Firebase CLI**: `npm install -g firebase-tools`
2. **Login**: `firebase login`
3. **Initialize**: `firebase init`
4. **Configure**: Create firebase.json and .firebaserc (see examples)
5. **Create wrapper**: functions/main.py for FastAPI
6. **Deploy**: `firebase deploy`

Need help with any specific step?
