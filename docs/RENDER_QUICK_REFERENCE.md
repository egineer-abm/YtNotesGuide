# Render Deployment - Quick Reference

## 30-Second Summary

Deploy two services to Render:
1. **Backend** (FastAPI) - processes videos, creates Notion pages
2. **Frontend** (Streamlit) - user interface

---

## Checklist

### Before You Start
- [ ] GitHub repo has all code committed
- [ ] `.env` is in `.gitignore` (NO SECRETS IN GIT)
- [ ] Have GROQ_API_KEY and NOTION_API_KEY ready

### Create Backend Service
- [ ] Go to https://dashboard.render.com
- [ ] New → Web Service
- [ ] Connect GitHub repo
- [ ] Name: `youtube-guide-backend`
- [ ] Build: `pip install -r requirements.txt`
- [ ] Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- [ ] Env vars:
  - `GROQ_API_KEY=gsk_...`
  - `NOTION_API_KEY=secret_...`
  - `RENDER=true`
- [ ] Deploy & wait for "Live" status
- [ ] Copy backend URL (e.g., `https://youtube-guide-backend.onrender.com`)

### Create Frontend Service
- [ ] New → Web Service again
- [ ] Connect same GitHub repo
- [ ] Name: `youtube-guide-frontend`
- [ ] Build: `pip install -r requirements.txt`
- [ ] Start: `streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0`
- [ ] Env vars:
  - `BACKEND_URL=https://youtube-guide-backend.onrender.com` (paste URL from above)
- [ ] Deploy & wait for "Live" status
- [ ] Frontend URL: `https://youtube-guide-frontend.onrender.com`

### Test
- [ ] Backend health: `https://youtube-guide-backend.onrender.com/health`
  - Should return JSON with "status": "healthy" or "degraded"
- [ ] Frontend loads: `https://youtube-guide-frontend.onrender.com`
  - Should show Streamlit UI
  - Sidebar should say "Backend: Connected" ✓
- [ ] Process a video:
  - Enter YouTube channel URL
  - Set to 1-2 videos
  - Click "Process Channel"
  - Wait 30-60 seconds
  - Should show success message

### Notion Setup
- [ ] Go to https://www.notion.so/my-integrations
- [ ] Create "YouTube Guide Generator" integration
- [ ] Copy Internal Integration Token
- [ ] Go to Render backend service
- [ ] Update `NOTION_API_KEY` with token
- [ ] In Notion: Add integration to page (... → Add connections)
- [ ] Test again - pages should create in Notion

---

## Environment Variables

### Backend Service (`youtube-guide-backend`)
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RENDER=true
LOG_LEVEL=INFO
```

### Frontend Service (`youtube-guide-frontend`)
```
BACKEND_URL=https://youtube-guide-backend.onrender.com
```

---

## URLs After Deployment

```
Frontend:  https://youtube-guide-frontend.onrender.com
Backend:   https://youtube-guide-backend.onrender.com
Health:    https://youtube-guide-backend.onrender.com/health
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| "Backend not connected" | Check `BACKEND_URL` env var in frontend service |
| "Notion API error" | Check `NOTION_API_KEY` is correct and integration has page access |
| "Port error" | Make sure start command uses `$PORT` (not hardcoded port) |
| "Build fails" | Check all packages in requirements.txt are available |
| "Streamlit takes 30 seconds" | Normal for first load, caches after |
| "Service sleeps after 15 mins" | Free tier feature, wakes on HTTP request |

---

## File Locations

```
root/
├── RENDER_SETUP.md              ← Full guide (read this)
├── RENDER_QUICK_REFERENCE.md    ← This file
├── render.yaml                  ← Infrastructure config (optional)
├── build.sh                     ← Build script
├── backend/
│   ├── main.py                  ← Modified for Render
│   ├── config.py                ← Modified for Render
│   └── render_start.sh          ← Startup script
└── frontend/
    ├── api_client.py            ← Modified for Render
    ├── .streamlit/config.toml   ← Streamlit config
    └── render_start.sh          ← Startup script
```

---

## Redeploy After Code Changes

```bash
git push origin main
```

Render auto-redeploys if "Auto-Deploy" is enabled.

Manual redeploy:
1. Render Dashboard
2. Click service
3. Deployments tab
4. Click "Redeploy" on latest

---

## Monitor

**View logs:**
1. Render Dashboard → Service name
2. Click "Logs" tab
3. Real-time streaming logs

**Check status:**
1. Render Dashboard → Service name
2. Status badge shows "Live" or "Build failed"

---

## Costs

**Free Tier (included):**
- 750 hours/month per service (2 services = 1,500 total)
- Enough for ~25 hours/day usage

**If you need more:**
- Upgrade to Standard: $7/month per service
- Gets 730 hours/month + always-on

---

## Next Steps

1. Read full `RENDER_SETUP.md` guide for details
2. Follow the checklist above
3. Test everything works
4. Monitor logs for first week
5. Share the frontend URL with users

