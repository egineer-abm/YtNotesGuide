# Firebase Cloud Run - Quick Start

## 5-Minute Setup

### 1. Create Google Cloud Project
```bash
# Go to https://cloud.google.com → Sign up (free)
# Create new project: "youtube-guide-backend"
```

### 2. Install Google Cloud CLI
```bash
# Windows: https://cloud.google.com/sdk/docs/install
# After installation, verify:
gcloud --version
```

### 3. Authenticate
```bash
gcloud auth login
# Opens browser, click "Allow"
```

### 4. Deploy Backend
```bash
# Replace with your actual keys
./deploy-firebase.sh my-youtube-project gsk_YOUR_GROQ_KEY secret_YOUR_NOTION_KEY
```

### 5. Get Backend URL
The script will output your Cloud Run URL:
```
Backend URL: https://youtube-guide-backend-abc123-uc.a.run.app
```

### 6. Update Frontend
Update `BACKEND_URL` environment variable in frontend deployment:
```
BACKEND_URL=https://youtube-guide-backend-abc123-uc.a.run.app
```

### 7. Test
```bash
curl https://youtube-guide-backend-abc123-uc.a.run.app/health
```

---

## Common Commands

### View Logs
```bash
gcloud run logs read youtube-guide-backend --region us-central1 --limit 50
```

### View Service Details
```bash
gcloud run services describe youtube-guide-backend --region us-central1
```

### Update Environment Variables
```bash
gcloud run services update youtube-guide-backend \
  --region us-central1 \
  --update-env-vars="GROQ_API_KEY=new_key,NOTION_API_KEY=new_key"
```

### Delete Service
```bash
gcloud run services delete youtube-guide-backend --region us-central1
```

### Monitor Costs
```bash
# Dashboard: https://console.cloud.google.com/billing
# Cloud Run: https://console.cloud.google.com/run
```

---

## Costs

- **First 2 million requests/month**: FREE
- **Next requests**: $0.24 per 1M requests
- **Compute**: ~$0.024 per vCPU-hour (for 512Mi/0.5 vCPU)
- **Typical monthly**: $0-5 (development), $5-50 (production)

---

## Migration Checklist

- [ ] Create Google Cloud Account
- [ ] Install gcloud CLI
- [ ] Authenticate gcloud
- [ ] Run deploy-firebase.sh
- [ ] Test health endpoint
- [ ] Update BACKEND_URL in frontend
- [ ] Test API from frontend
- [ ] Monitor costs on Google Cloud Console

---

## Troubleshooting

### Can't find gcloud command
```bash
# Add to PATH or reinstall gcloud CLI
# Restart terminal after installation
which gcloud
```

### Authentication fails
```bash
gcloud auth login --no-launch-browser
# Follow the URL
```

### Deployment times out
```bash
# Check if you have billing enabled:
gcloud billing accounts list
gcloud billing projects link my-youtube-project \
  --billing-account=ACCOUNT_ID
```

### Health check fails (port 8080)
- Make sure Dockerfile exposes port 8080
- Verify BACKEND_PORT=8080 in config.py
- Check logs: `gcloud run logs read youtube-guide-backend --limit 50`

---

## Need Help?

- Full guide: See `FIREBASE_DEPLOYMENT_GUIDE.md`
- Google Cloud docs: https://cloud.google.com/run/docs
- This project's architecture: See `DEPLOYMENT_ARCHITECTURE.md`
