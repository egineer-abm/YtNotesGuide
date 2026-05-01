# Firebase CLI - Cheat Sheet

One-page reference for common commands and troubleshooting.

---

## Installation (First Time Only)

```bash
npm install -g firebase-tools
firebase --version                    # Should show version
firebase login                        # Opens browser, click Allow
firebase projects:list                # Shows your projects
```

---

## Deployment

```bash
# From project root directory

# Deploy backend to Cloud Functions
firebase deploy --only functions

# Deploy both backend and frontend
firebase deploy

# Deploy with specific function
firebase deploy --only functions:api
```

---

## Configuration

### Update .firebaserc
```json
{
  "projects": {
    "default": "your-project-id-12345"
  }
}
```

### Set Environment Variables (After Deploy)
```bash
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="\
GROQ_API_KEY=gsk_YOUR_KEY,\
NOTION_API_KEY=secret_YOUR_KEY,\
ENVIRONMENT=production"
```

---

## Monitoring & Debugging

### View Logs
```bash
firebase functions:log                # Last 50 logs
firebase functions:log --limit 100    # More logs
firebase functions:log --limit 1000   # All logs
```

### View Function Details
```bash
firebase functions:describe api       # Full details
firebase functions:describe api --format json  # JSON format
```

### View All Functions
```bash
firebase functions:list
```

### Real-time Logs (Windows)
```bash
gcloud functions logs read api --limit 50 --follow
```

---

## Testing

### Test Health Endpoint
```bash
curl https://us-central1-PROJECT_ID.cloudfunctions.net/api/health
```

### Test with Verbose Output
```bash
curl -v https://us-central1-PROJECT_ID.cloudfunctions.net/api/health
```

### Test POST Request
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"channel_url":"https://www.youtube.com/@channel"}' \
  https://us-central1-PROJECT_ID.cloudfunctions.net/api/v1/process-channel
```

---

## Environment Variables

### View Current Variables
```bash
gcloud functions describe api --format="value(environmentVariables)"
```

### Update Variables
```bash
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="KEY1=value1,KEY2=value2"
```

### Add Single Variable
```bash
gcloud functions deploy api \
  --runtime python311 \
  --update-env-vars="NEW_KEY=new_value"
```

---

## Troubleshooting

### Can't Find firebase Command
```bash
# Reinstall
npm uninstall -g firebase-tools
npm install -g firebase-tools

# Verify
firebase --version
```

### Authentication Issues
```bash
firebase logout
firebase login
firebase projects:list
```

### Deployment Stuck
```bash
# Cancel (Ctrl+C), then retry
firebase deploy --only functions --debug
```

### Function Not Found
```bash
firebase functions:list             # Check if exists
firebase functions:describe api     # Check details
```

### Timeout Errors (> 15 min processing)
```bash
# Increase timeout to 9 minutes (max for Cloud Functions)
gcloud functions deploy api \
  --timeout=540 \
  --runtime python311

# Or switch to Cloud Run
# See FIREBASE_DEPLOYMENT_GUIDE.md
```

### Environment Variables Not Working
```bash
# Redeploy with variables
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="GROQ_API_KEY=gsk_xxx,NOTION_API_KEY=secret_xxx"

# Verify they're set
gcloud functions describe api --format="value(environmentVariables)"
```

### Health Check Returns 500
```bash
# View detailed logs
firebase functions:log --limit 100

# Look for error messages starting with "E"

# Usually: Missing environment variables
# Fix: See "Environment Variables Not Working" above
```

### CORS Errors
```bash
# CORS should be handled in functions/main.py
# If still issues, check:

# 1. Function is accessible
curl https://us-central1-PROJECT.cloudfunctions.net/api/health

# 2. Headers are correct
curl -i https://us-central1-PROJECT.cloudfunctions.net/api/health
# Look for: Access-Control-Allow-Origin: *
```

### ImportError: Cannot find module 'backend'
```bash
# Fix Python path in functions/main.py

# Check file structure
ls -la functions/main.py             # Should exist
ls -la backend/main.py              # Should exist

# Redeploy
firebase deploy --only functions --debug
```

---

## Cleanup & Deletion

### Delete Single Function
```bash
firebase functions:delete api
```

### Delete All Functions
```bash
firebase functions:delete --force
```

### Delete Entire Project (Careful!)
```bash
gcloud projects delete YOUR_PROJECT_ID
```

---

## Performance & Costs

### Check Usage & Costs
```bash
gcloud billing accounts list
gcloud billing projects list
```

### View Function Metrics
```bash
# In Google Cloud Console:
# https://console.cloud.google.com/functions
```

### Monitor Invocations
```bash
gcloud monitoring time-series list \
  --filter='resource.type="cloud_function"'
```

---

## Quick Status Check

```bash
# Complete health check
echo "1. Firebase CLI:"
firebase --version

echo "2. Google Cloud:"
gcloud --version

echo "3. Logged in as:"
gcloud config get-value account

echo "4. Projects:"
firebase projects:list

echo "5. Functions:"
firebase functions:list

echo "6. Function details:"
firebase functions:describe api
```

---

## Common Workflow

### Initial Setup
```bash
npm install -g firebase-tools       # Once
firebase login                       # Once
# Edit .firebaserc with PROJECT_ID  # Once
```

### Deploy Changes
```bash
# Edit your code (backend/main.py)
firebase deploy --only functions    # Deploy
firebase functions:log              # View logs
```

### Debug Issues
```bash
firebase functions:log --limit 100  # View all logs
firebase functions:describe api     # View details
gcloud functions describe api \
  --format="value(environmentVariables)"  # View env vars
```

### Rollback (if needed)
```bash
# Update BACKEND_URL in frontend back to Render
# Then fix and redeploy
firebase deploy --only functions
```

---

## Environment Variables Format

### Correct Format (Commas, No Spaces)
```bash
--set-env-vars="KEY1=value1,KEY2=value2,KEY3=value3"
```

### Incorrect (Spaces Around Equals)
```bash
--set-env-vars="KEY1 = value1"  # ❌ Wrong
```

### With Special Characters
```bash
--set-env-vars="URL=https://example.com,KEY=gsk_abc123"
```

### Long Values
```bash
# Break across lines with backslash
gcloud functions deploy api \
  --runtime python311 \
  --set-env-vars="\
GROQ_API_KEY=gsk_very_long_key_here,\
NOTION_API_KEY=secret_very_long_key_here"
```

---

## Project ID vs Project Name

```bash
firebase projects:list

# Output:
# Project Display Name     Project ID              Location
# YouTube Guides          youtube-guides-12345    us-central1

# Use PROJECT_ID (right column) for:
# - .firebaserc
# - Backend URL: https://us-central1-PROJECT_ID.cloudfunctions.net/api
```

---

## Regional Endpoints

Default region: `us-central1`

Other regions:
```
us-central1          (Default)
us-east1
us-west1
us-west2
europe-west1
asia-northeast1
```

Your endpoint format:
```
https://REGION-PROJECT_ID.cloudfunctions.net/api
```

---

## Time Estimates

| Task | Time |
|------|------|
| Install Firebase CLI | 2 min |
| Login | 1 min |
| Get Project ID | 1 min |
| Update .firebaserc | 1 min |
| Deploy backend | 3-5 min |
| Set env variables | 2 min |
| Test endpoint | 1 min |
| **Total** | **11-15 min** |

---

## Links

```
Google Cloud Console:
https://console.cloud.google.com/functions

Firebase Dashboard:
https://console.firebase.google.com/

Cloud Functions Logs:
https://console.cloud.google.com/functions/details/REGION/api?project=PROJECT_ID

Billing:
https://console.cloud.google.com/billing
```

---

## One-Liner Commands

```bash
# Deploy and show URL
firebase deploy --only functions && firebase functions:describe api --format="value(httpsTrigger.url)"

# Deploy and test
firebase deploy --only functions && curl https://us-central1-PROJECT_ID.cloudfunctions.net/api/health

# View recent logs and filter errors
firebase functions:log | grep -i error

# Get function URL
firebase functions:describe api --format="value(httpsTrigger.url)"

# Count invocations (last hour)
gcloud monitoring time-series list --filter='resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/execution_count"' --format="value(points[0].value.number_value)"
```

---

## When to Check These Docs

| Situation | Check |
|-----------|-------|
| "How do I deploy?" | Deployment section |
| "It's broken" | Troubleshooting section |
| "What's my URL?" | View Function Details section |
| "Set API keys" | Set Environment Variables section |
| "See what happened?" | Monitoring & Debugging section |
| "Delete everything" | Cleanup & Deletion section |
| "Forgot a command?" | Common Workflow section |

---

**Print this page for quick reference!**
