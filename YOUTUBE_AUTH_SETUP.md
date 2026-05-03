# YouTube Authentication Setup Guide

This guide explains how to configure YouTube authentication to fix the "Sign in to confirm you're not a bot" error when processing YouTube videos.

## Problem Description

When processing YouTube videos, you might encounter this error:
```
ERROR: [youtube] VIDEO_ID: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.
```

This happens because YouTube sometimes requires authentication to verify that requests are not coming from bots.

## Solution Overview

The backend supports several methods for YouTube authentication:

1. **Browser Cookies** (Recommended for development)
2. **Cookie File** (Recommended for production)
3. **Cookie Environment Secret** (Recommended for hosted production)

## Method 1: Using Browser Cookies (Development)

This method automatically extracts cookies from your browser.

### Setup Instructions

1. **Configure the environment variable** in your `.env` file:
   ```bash
   # For Chrome
   YOUTUBE_COOKIES_FROM_BROWSER=chrome
   
   # For Firefox
   # YOUTUBE_COOKIES_FROM_BROWSER=firefox
   
   # For Brave
   # YOUTUBE_COOKIES_FROM_BROWSER=brave
   ```

2. **Sign in to YouTube** in your chosen browser before running the application.

3. **Start the application** - it will automatically use your browser cookies.

### Browser Support

The following browsers are supported:
- `chrome` - Google Chrome
- `firefox` - Mozilla Firefox
- `brave` - Brave Browser
- `edge` - Microsoft Edge
- `opera` - Opera Browser
- `safari` - Safari (macOS only)

You can also specify a profile for browsers that support multiple profiles:
```bash
YOUTUBE_COOKIES_FROM_BROWSER=chrome:Profile 1
```

## Method 2: Using Cookie File (Production)

This method uses a cookie file exported from your browser.

### Setup Instructions

1. **Export cookies from your browser** using a browser extension that produces Netscape-format cookies.
   
   Current yt-dlp YouTube docs recommend a stable export flow:
   - Open a private/incognito window and log into YouTube.
   - In the same private window tab, navigate to `https://www.youtube.com/robots.txt`.
   - Export only `youtube.com` cookies from that private session.
   - Close the private window and do not reopen that session.

2. **Configure the environment variable** in your `.env` file:
   ```bash
   YOUTUBE_COOKIES_FILE=./cookies.txt
   ```

3. **Start the application** - it will use the cookie file for authentication.

## Method 3: Using Cookie Environment Secret (Hosted Production)

Hosted services such as Render usually cannot read cookies from your browser. Use one of these instead:

```bash
# Preferred for secret managers because it preserves newlines safely.
YOUTUBE_COOKIES_B64=<base64 encoded cookies.txt>

# Also supported if your platform preserves multiline secrets.
YOUTUBE_COOKIES=<raw Netscape cookies.txt content>
```

On PowerShell, create a base64 value from a local cookie file:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))
```

## Configuration Priority

The authentication methods are checked in this order:
1. `YOUTUBE_COOKIES_FILE` - Cookie file has priority
2. `YOUTUBE_COOKIES_B64` - Base64 cookie file content
3. `YOUTUBE_COOKIES` - Raw cookie file content
4. `YOUTUBE_COOKIES_FROM_BROWSER` - Browser cookies as fallback
5. No authentication - Default behavior (may fail for some videos)

## Rate Limiting

The backend waits between YouTube requests by default:

```bash
YOUTUBE_SLEEP_INTERVAL=6
YOUTUBE_MAX_SLEEP_INTERVAL=12
```

yt-dlp's YouTube docs recommend delays around 5-10 seconds when YouTube rate-limits a session. Increase these values if hosted processing triggers repeated bot checks.

## Testing the Configuration

You can test if your YouTube authentication is working by:

1. **Using the test endpoint**:
   ```bash
   curl -X POST "http://localhost:7860/api/v1/test-youtube?source_input=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DDddUhB1k_80"
   ```

2. **Using the app**: paste the same video URL and click `Fetch Latest Videos`.

## Troubleshooting

### Common Issues

1. **"Cookie file not found"**
   - Ensure the cookie file path is correct
   - Check file permissions

2. **"Browser not found"**
   - Ensure the specified browser is installed
   - Check that the browser name is spelled correctly

3. **Still getting authentication errors**
   - Try refreshing your cookies by signing out and back in to YouTube
   - Update your cookie file or restart your browser

### Updating Cookies

Cookies expire over time, so you may need to:

1. **For browser cookies**: Simply restart your browser and sign in to YouTube again
2. **For cookie files**: Re-export the cookies using the same method as initial setup

## Security Considerations

- **Cookie files contain sensitive information** - keep them secure and don't commit them to version control
- **Browser cookies are tied to your personal account** - be careful when sharing your environment
- The application only uses cookies for YouTube authentication and doesn't store or transmit them elsewhere

## Example .env Configuration

Here's a complete example of YouTube authentication configuration in your `.env` file:

```bash
# YouTube Authentication (choose one method)

# Method 1: Browser cookies (for development)
YOUTUBE_COOKIES_FROM_BROWSER=chrome

# Method 2: Cookie file (for production)  
# YOUTUBE_COOKIES_FILE=./cookies.txt

# Method 3: Hosted production secret
# YOUTUBE_COOKIES_B64=base64_cookie_file_here

YOUTUBE_SLEEP_INTERVAL=6
YOUTUBE_MAX_SLEEP_INTERVAL=12
YOUTUBE_PLAYER_CLIENTS=default
```

After configuration, restart your application to apply the changes.
