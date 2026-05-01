# Firebase CLI - Quick Start (Copy-Paste Steps)

## Prerequisites
- Node.js installed (https://nodejs.org/)
- Google Cloud account (https://cloud.google.com)
- Google Cloud Project created

---

## 10-Minute Setup

### Step 1: Install Firebase CLI
```bash
npm install -g firebase-tools
firebase --version
```

### Step 2: Login to Firebase
```bash
firebase login
# Opens browser, click "Allow"
```

### Step 3: Get Your Project ID
```bash
# List your projects
firebase projects:list

# Copy the PROJECT_ID from output
```

### Step 4: Update .firebaserc
Open `.firebaserc` and replace:
```json
{
  "projects": {
    "default": "YOUR_PROJECT_ID_HERE"
  }
}
```

With:
```json
{
  "projects": {
    "default": "my-youtube-project"
  }
}
```

### Step 5: Deploy Backend to Cloud Functions
```bash
# From project root
firebase deploy --only functions

# Wait for deployment to complete...
# You'll see output like:
# Function 'api' available at https://region-project-id.cloudfunctions.net/api
```

### Step 6: Get Your Backend URL
From the output above, copy the function URL:
```
https://us-central1-my-youtube-project.cloudfunctions.net/api
```

### Step 7: Set Environment Variables
```bash
# Open Google Cloud Console → Cloud Functions → api → Runtime Settings
# Or use gcloud CLI:

gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="GROQ_API_KEY=gsk_YOUR_KEY,NOTION_API_KEY=secret_YOUR_KEY,ENVIRONMENT=production"
```

### Step 8: Test Backend Health
```bash
curl https://us-central1-my-youtube-project.cloudfunctions.net/api/health
```

Should return:
```json
{
  "status": "healthy",
  "services": {"groq": "ok", "notion": "ok"},
  "timestamp": "2024-02-18T..."
}
```

### Step 9: Update Frontend
Set environment variable:
```
BACKEND_URL=https://us-central1-my-youtube-project.cloudfunctions.net/api
```

### Step 10: Done! 🎉
Your backend is now live on Firebase Cloud Functions.

---

## Common Commands

### Deploy
```bash
firebase deploy                    # Deploy everything
firebase deploy --only functions   # Deploy just backend
firebase deploy --only hosting     # Deploy just frontend
```

### View Logs
```bash
firebase functions:log              # Last 50 logs
firebase functions:log --limit 100  # More logs
```

### View Function Details
```bash
firebase functions:describe api
```

### Update Environment Variables
```bash
# Via gcloud
gcloud functions deploy api \
  --set-env-vars="GROQ_API_KEY=new_key,NOTION_API_KEY=new_key" \
  --runtime python311
```

### Delete Function
```bash
firebase functions:delete api
```

### View All Functions
```bash
firebase functions:list
```

---

## Troubleshooting

### "Cannot find module 'backend'"
The wrapper can't import your backend. Make sure:
- Your backend directory has `__init__.py` files
- Python path is correct in functions/main.py
- Run from project root

### "Timeout exceeded" (15 minutes)
Cloud Functions has a 15-minute timeout. If your processing takes longer:
- Switch to Cloud Run (follow FIREBASE_DEPLOYMENT_GUIDE.md)
- Increase timeout: see next section

### Timeout Configuration
If processing is 30-120 seconds, you need to increase timeout:
```bash
gcloud functions deploy api \
  --timeout=540 \
  --runtime python311
```
Max is 540 seconds (9 minutes).

**Better**: Use Cloud Run which supports up to 3600 seconds (1 hour).

### "CORS error" in frontend
Make sure headers in functions/main.py include CORS headers:
```python
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
}
```

### Environment variables not loading
```bash
# Check if variables are set
gcloud functions describe api --format="value(environmentVariables)"

# Redeploy with variables
gcloud functions deploy api \
  --set-env-vars="KEY1=value1,KEY2=value2" \
  --runtime python311
```

---

## When to Switch to Cloud Run

Use Cloud Run instead if:
- Processing takes > 15 minutes
- You need more memory (Cloud Functions: 8GB max, Cloud Run: 8GB default)
- You want better cold start performance
- You need Docker support

To switch: Follow FIREBASE_DEPLOYMENT_GUIDE.md Option A

---

## Architecture Summary

```
Frontend (Render/Firebase Hosting)
    ↓
    ├─→ BACKEND_URL=https://us-central1-PROJECT.cloudfunctions.net/api
    ↓
Backend (Firebase Cloud Functions)
    ├─→ YouTube API
    ├─→ Groq API (LLM)
    └─→ Notion API (Database)
```

---

## Cost Estimation

- **First 2 million invocations/month**: FREE
- **After**: $0.40 per 1M invocations
- **Compute**: Included in free tier
- **Typical**: $0 (free tier covers most projects)

---

## Next Steps

1. ✅ Install Firebase CLI
2. ✅ Login and get project ID
3. ✅ Update .firebaserc
4. ✅ Deploy with `firebase deploy --only functions`
5. ✅ Set environment variables
6. ✅ Test health endpoint
7. ✅ Update frontend BACKEND_URL
8. ✅ Monitor with `firebase functions:log`

Need help? Check FIREBASE_CLI_DEPLOYMENT.md for detailed guide.
