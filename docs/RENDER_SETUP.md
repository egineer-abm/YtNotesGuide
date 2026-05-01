# Render Deployment Guide

## Prerequisites

1. **GitHub Repository**
   - Push your code to: https://github.com/abm1119/ytvideoguides
   - Ensure `.env` is in `.gitignore` (do NOT commit secrets)

2. **Render Account**
   - Create free account at https://render.com
   - Sign in with GitHub

3. **API Keys Ready**
   - GROQ_API_KEY from https://console.groq.com/keys
   - NOTION_API_KEY from https://www.notion.so/my-integrations

---

## Step 1: Prepare Code

All preparation files are already created:
- ✅ `build.sh` - Build script
- ✅ `backend/render_start.sh` - Backend startup script
- ✅ `frontend/.streamlit/config.toml` - Streamlit configuration
- ✅ `frontend/render_start.sh` - Frontend startup script
- ✅ `render.yaml` - Infrastructure configuration (optional)

Verify files are pushed to GitHub:
```bash
cd MVP
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

---

## Step 2: Create Backend Service

### 2.1 Go to Render Dashboard
https://dashboard.render.com

### 2.2 Create New Web Service

1. Click **"New +"** → **"Web Service"**
2. Select your GitHub repo `ytvideoguides`
3. Fill in the form:
   - **Name**: `youtube-guide-backend`
   - **Environment**: `Python 3`
   - **Region**: Select closest to you (or `Oregon`)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### 2.3 Add Environment Variables

Click **"Advanced"** and add:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_...` (your Groq API key) |
| `NOTION_API_KEY` | `secret_...` (your Notion integration token) |
| `RENDER` | `true` |
| `LOG_LEVEL` | `INFO` |

### 2.4 Deploy

Click **"Create Web Service"**

Wait for deployment (1-2 minutes). You'll see:
```
✓ Build successful
✓ Deploying...
```

Note your backend URL: `https://youtube-guide-backend.onrender.com` (it will be different)

---

## Step 3: Create Frontend Service

### 3.1 Go Back to Dashboard

Click **"New +"** → **"Web Service"** again

### 3.2 Create Frontend Service

1. Select your GitHub repo again
2. Fill in the form:
   - **Name**: `youtube-guide-frontend`
   - **Environment**: `Python 3`
   - **Region**: Same as backend
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0`

### 3.3 Add Environment Variables

Click **"Advanced"** and add:

| Key | Value |
|-----|-------|
| `BACKEND_URL` | `https://youtube-guide-backend.onrender.com` (from Step 2) |

### 3.4 Deploy

Click **"Create Web Service"**

Wait for deployment. Frontend URL: `https://youtube-guide-frontend.onrender.com`

---

## Step 4: Test Deployment

### 4.1 Check Backend Health

Open in browser:
```
https://youtube-guide-backend.onrender.com/health
```

Should see:
```json
{
  "status": "healthy" or "degraded",
  "services": {
    "groq": "ok",
    "notion": "ok"
  }
}
```

### 4.2 Open Frontend

Open in browser:
```
https://youtube-guide-frontend.onrender.com
```

Should see:
- Streamlit interface loads
- Sidebar shows "Backend: Connected" ✓

### 4.3 Test Full Workflow

1. Enter YouTube channel URL (e.g., `https://www.youtube.com/@fireship`)
2. Set "Number of Videos" to 1-2
3. Click "Process Channel"
4. Wait for processing

Should complete successfully and show Notion links.

---

## Step 5: Set Up Notion Integration

### 5.1 Create Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **"New integration"**
3. Name: `YouTube Guide Generator`
4. Select your workspace
5. Click **"Submit"**
6. Copy the **"Internal Integration Token"**

### 5.2 Add to Backend Environment

1. Go to Render Dashboard
2. Select `youtube-guide-backend` service
3. Click **"Environment"**
4. Update `NOTION_API_KEY` with the token
5. Service auto-redeployss

### 5.3 Grant Integration Access to Pages

In Notion:
1. Go to the page where you want guides created
2. Click **"..."** menu → **"Add connections"**
3. Select **"YouTube Guide Generator"** integration
4. Save

---

## Step 6: Ongoing Management

### View Logs

**Backend logs:**
1. Render Dashboard → `youtube-guide-backend`
2. Click **"Logs"** tab
3. Watch real-time output

**Frontend logs:**
1. Render Dashboard → `youtube-guide-frontend`
2. Click **"Logs"** tab

### Redeploy

Push new code to GitHub:
```bash
git push origin main
```

Render auto-redeploys (check **"Auto-Deploy"** is enabled)

Manual redeploy:
1. Click service
2. Click **"Deployments"**
3. Click **"Redeploy"** on latest deployment

### Monitor Usage

**Free Tier Limits:**
- 750 free hours/month per service
- Automatic sleep after 15 mins inactivity
- Wake on HTTP request

**Upgrade if:**
- You need always-on availability
- You're hitting the 750-hour limit

---

## Troubleshooting

### "Backend not connected" in Frontend

**Check:**
1. Backend service status in Render Dashboard (should be "Live")
2. Backend logs for errors
3. `BACKEND_URL` env var in frontend service matches your backend URL

**Fix:**
```bash
# 1. Go to frontend service Environment
# 2. Verify BACKEND_URL exactly matches backend URL
# 3. Redeploy frontend
```

### "Notion API Error"

**Check:**
1. `NOTION_API_KEY` is set and correct (copy from integration again)
2. Integration has access to the page (check Notion connections)
3. Check backend logs for specific error

**Fix:**
```bash
# 1. Update NOTION_API_KEY in backend service
# 2. Redeploy backend
# 3. Test via /health endpoint
```

### "No transcript available"

This is normal - not all YouTube videos have transcripts. Try different channel.

### "Service takes too long to start"

Streamlit takes 30-60 seconds on first load. This is normal. On subsequent requests it's instant.

### "Port already in use" error

Render handles port assignment via `$PORT` env var. If error persists:
1. Check Build Command doesn't hardcode port
2. Check Start Command uses `$PORT`
3. Redeploy

---

## File Reference

### Created for Render Deployment

```
build.sh                        # Build script
backend/render_start.sh         # Backend startup
frontend/.streamlit/config.toml # Streamlit production config
frontend/render_start.sh        # Frontend startup
render.yaml                     # Infrastructure-as-code (optional)
```

### Modified for Render

```
backend/config.py               # Port handling, $PORT env var
backend/main.py                 # CORS configuration
frontend/api_client.py          # Dynamic backend URL
```

---

## Success Checklist

- [ ] Code pushed to GitHub
- [ ] Backend service created and deployed
- [ ] Frontend service created and deployed
- [ ] Both services show "Live" status
- [ ] Backend `/health` endpoint returns 200
- [ ] Frontend loads Streamlit UI
- [ ] Frontend shows "Backend: Connected"
- [ ] Full workflow tested (YouTube → Notion)
- [ ] Notion integration created and connected
- [ ] Notion pages are being created successfully

---

## Next Steps

1. **Monitor**: Check logs daily for first week
2. **Optimize**: If using >500 hours/month, upgrade to Standard tier
3. **Backup**: Export important data from Notion regularly
4. **Updates**: Push new features to GitHub for auto-deployment

---

## Support

**Render Docs:** https://render.com/docs
**Streamlit Deployment:** https://docs.streamlit.io/deploy/streamlit-community-cloud
**FastAPI:** https://fastapi.tiangolo.com/deployment/

