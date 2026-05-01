# Firebase CLI - Step-by-Step Execution Guide

Complete walkthrough with exact commands to copy-paste.

---

## Prerequisites Checklist

Before starting, make sure you have:

- [ ] Google Cloud account (free tier OK)
- [ ] Google Cloud project created
- [ ] Node.js installed (v18+)
- [ ] Command line/terminal access
- [ ] Your GROQ API key (gsk_...)
- [ ] Your Notion API key (secret_...)

If you don't have these, go to:
- Google Cloud: https://cloud.google.com
- Node.js: https://nodejs.org/

---

## Step-by-Step Execution

### Step 1: Install Firebase CLI (2 minutes)

Open terminal/command prompt:

```bash
npm install -g firebase-tools
```

Verify installation:
```bash
firebase --version
```

Expected output:
```
12.4.0  (or similar version)
```

### Step 2: Authenticate with Google (1 minute)

```bash
firebase login
```

A browser window will open. Click "Allow" to grant Firebase CLI access.

Back in terminal, you should see:
```
✔ Logged in as your.email@gmail.com
```

### Step 3: Verify Project ID (1 minute)

List your projects:
```bash
firebase projects:list
```

You'll see output like:
```
┌──────────────────────┬──────────────────────┬─────────────────┐
│ Project Display Name │ Project ID           │ Location        │
├──────────────────────┼──────────────────────┼─────────────────┤
│ YouTube Guide        │ youtube-guide-12345  │ us-central1     │
└──────────────────────┴──────────────────────┴─────────────────┘
```

Copy your PROJECT_ID (e.g., `youtube-guide-12345`).

### Step 4: Update .firebaserc (1 minute)

Open `.firebaserc` file in this project.

Replace:
```json
{
  "projects": {
    "default": "YOUR_GOOGLE_PROJECT_ID_HERE"
  }
}
```

With your actual project ID:
```json
{
  "projects": {
    "default": "youtube-guide-12345"
  }
}
```

Save file.

### Step 5: Verify Project Root (30 seconds)

Make sure you're in the correct directory:
```bash
# Navigate to project root
cd d:/100xEngineers-c6/LLM\ Modeule/week5/MVP

# Verify files exist
ls firebase.json .firebaserc backend/Dockerfile functions/main.py
```

You should see all four files listed.

### Step 6: Deploy Backend to Cloud Functions (3 minutes)

Run deployment:
```bash
firebase deploy --only functions
```

You'll see progress:
```
i  deploying functions
i  Loading function code from /path/to/backend
⚙ activating service account
⚙ checking for new packages in requirements.txt
⚙ installing dependencies
...
✔ Deploy complete!

api deployed successfully
```

### Step 7: Get Your Backend URL (30 seconds)

After deployment, find your function URL:
```bash
firebase functions:describe api
```

Output will show:
```
Name: api
Status: ACTIVE
Trigger: HTTPS
URL: https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/api
Available Memory MB: 256
Timeout (seconds): 60
```

**Copy this URL**: `https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/api`

### Step 8: Set Environment Variables (2 minutes)

Set your API keys. Replace with your actual keys:

```bash
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="GROQ_API_KEY=gsk_YOUR_ACTUAL_KEY,NOTION_API_KEY=secret_YOUR_ACTUAL_KEY,ENVIRONMENT=production"
```

Wait for deployment to complete (30-60 seconds).

### Step 9: Test Health Endpoint (1 minute)

Test if backend is working:
```bash
curl https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "groq": "ok",
    "notion": "ok"
  },
  "timestamp": "2024-02-18T10:30:45.123456"
}
```

If you get an error, check Step 8 (environment variables).

### Step 10: Update Frontend (1 minute)

Copy your backend URL from Step 7.

Update frontend environment variable:
```
BACKEND_URL=https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/api
```

In Render dashboard or frontend code.

### Step 11: Test Full Integration (2 minutes)

1. Open frontend (https://youtube-guide-frontend.onrender.com)
2. Check sidebar - should show "Backend: Connected ✓"
3. Try processing a small channel
4. Should work end-to-end

### Step 12: Monitor and Verify (ongoing)

View recent logs:
```bash
firebase functions:log
```

View detailed logs:
```bash
firebase functions:log --limit 100
```

View function metrics:
```bash
firebase functions:describe api
```

View costs:
```bash
gcloud billing accounts list
```

---

## Complete Commands Summary

```bash
# 1. Install
npm install -g firebase-tools

# 2. Login
firebase login

# 3. List projects
firebase projects:list
# Copy PROJECT_ID

# 4. Update .firebaserc with PROJECT_ID
# (Manual edit)

# 5. Deploy
firebase deploy --only functions

# 6. Get URL
firebase functions:describe api
# Copy the URL

# 7. Set environment variables
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="GROQ_API_KEY=gsk_xxx,NOTION_API_KEY=secret_xxx,ENVIRONMENT=production"

# 8. Test
curl https://BACKEND_URL/health

# 9. View logs
firebase functions:log

# 10. View details
firebase functions:describe api
```

---

## Troubleshooting During Deployment

### Error: "Cannot find module 'backend'"

**Cause**: Python path issue in functions/main.py

**Fix**:
```bash
# Make sure you're in project root
cd /path/to/project

# Verify structure
ls -la functions/main.py backend/main.py

# Redeploy
firebase deploy --only functions
```

### Error: "GROQ_API_KEY not set"

**Cause**: Environment variables not deployed

**Fix**:
```bash
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="GROQ_API_KEY=gsk_YOUR_KEY,NOTION_API_KEY=secret_YOUR_KEY"
```

### Error: "Health check failed" or "Port 8080"

**Cause**: Functions wrapper issue

**Fix**: Check functions/main.py is valid:
```bash
# View recent errors
firebase functions:log --limit 50

# Look for error messages
```

### Error: "Timeout exceeded"

**Cause**: Processing took > 15 minutes

**Fix**: Switch to Cloud Run (see FIREBASE_DEPLOYMENT_GUIDE.md)

### "Deployment succeeded but API returns 500"

**Cause**: Missing environment variables

**Fix**:
```bash
# Check current variables
gcloud functions describe api \
  --format="value(environmentVariables)"

# Should show GROQ_API_KEY, NOTION_API_KEY

# If missing, set them
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="GROQ_API_KEY=gsk_xxx,NOTION_API_KEY=secret_xxx"
```

---

## Post-Deployment

### 1. Monitor Costs (Free Tier)
```
Free tier includes:
- 2 million invocations/month
- 400,000 GB-seconds
- Typical project: $0/month

Check usage:
gcloud billing accounts list
```

### 2. Monitor Performance
```bash
# View recent invocations
firebase functions:log --limit 50

# Check if any errors
# Look for HTTP status codes (500 = error)
```

### 3. View Function Dashboard
```
Google Cloud Console:
https://console.cloud.google.com/functions/details/us-central1/api?project=YOUR_PROJECT_ID
```

### 4. Set Up Alerts (Optional)
```bash
# In Google Cloud Console:
# → Monitoring → Policies → Create Policy
# → Metric: Cloud Functions > Execution Times
# → Alert if > 10 seconds
```

---

## What Happens Next?

### Every Request:
1. User makes request to your frontend
2. Frontend calls `BACKEND_URL/api/v1/process-channel`
3. Request hits Firebase Cloud Functions
4. Functions wrapper loads FastAPI app
5. FastAPI processes request
6. Response returned to frontend

### Costs:
- First 2 million requests: FREE
- After: $0.40 per 1 million requests
- Typical monthly: $0-5

### Scaling:
- Auto-scales from 0 to 1000+ instances
- Each instance handles ~80 concurrent requests
- You never manually scale

---

## Maintenance

### Weekly
```bash
# Check logs for errors
firebase functions:log --limit 20
```

### Monthly
```bash
# Review costs
gcloud billing accounts list

# Check function metrics
firebase functions:describe api
```

### When Errors Appear
```bash
# View full logs
firebase functions:log --limit 100

# Search for specific error
firebase functions:log | grep "error"

# Deploy fixes
firebase deploy --only functions
```

---

## Reverting to Previous Version

If something breaks:

```bash
# Delete current function
firebase functions:delete api

# Go back to Render (keep working)
# No changes needed to frontend, just update BACKEND_URL

# Redeploy later when fixed
firebase deploy --only functions
```

---

## Success Indicators

You'll know it's working when:

✅ Backend URL returns 200 status:
```bash
curl -I https://us-central1-PROJECT.cloudfunctions.net/api/health
# Should show "HTTP/1.1 200 OK"
```

✅ Logs show no errors:
```bash
firebase functions:log
# Should show GET/POST requests, no 500 errors
```

✅ Frontend connects:
```
Frontend sidebar shows "Backend: Connected ✓"
```

✅ Processing works:
```
Can submit channel URL and get results
Notion pages are created
```

---

## Need Help?

| Issue | Guide |
|-------|-------|
| Want to understand options? | DEPLOYMENT_COMPARISON.md |
| Cloud Run instead of Functions? | FIREBASE_DEPLOYMENT_GUIDE.md |
| General Firebase info? | FIREBASE_CLI_DEPLOYMENT.md |
| Quick reference? | FIREBASE_CLI_QUICK_START.md |

---

## Time Estimate

| Phase | Time |
|-------|------|
| Install Firebase CLI | 2 min |
| Login to Google | 1 min |
| Get Project ID | 1 min |
| Update .firebaserc | 1 min |
| Deploy backend | 3 min |
| Get Backend URL | 1 min |
| Set env variables | 2 min |
| Test health | 1 min |
| Update frontend | 1 min |
| Test integration | 2 min |
| **TOTAL** | **15-20 min** |

You're ready! Start with Step 1.
