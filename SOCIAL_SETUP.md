# Social Media Setup Guide - News Lancashire

## Platforms: Facebook & X (Twitter)

---

## X (Twitter) API Setup

### Step 1: Create X Developer Account
1. Go to https://developer.twitter.com/
2. Sign in with your X account
3. Apply for developer access (free tier available)

### Step 2: Create Project & App
1. Create a new Project (e.g., "News Lancashire")
2. Create an App within the project
3. Go to "Keys and Tokens" tab

### Step 3: Get Your Credentials
You need these 4 values:
- **API Key** (Consumer Key)
- **API Secret** (Consumer Secret)
- **Access Token**
- **Access Token Secret**

Generate "User Authentication Tokens" with Read + Write permissions.

### Step 4: Edit Config File
On Thurinus, edit:
```bash
nano ~/newslancashire/config/social.json
```

Add your X credentials:
```json
{
  "x_api_key": "your_api_key_here",
  "x_api_secret": "your_api_secret_here",
  "x_access_token": "your_access_token_here",
  "x_access_token_secret": "your_access_token_secret_here"
}
```

---

## Facebook API Setup

### Step 1: Create Facebook App
1. Go to https://developers.facebook.com/
2. Create New App → "Business" type
3. Add "Facebook Login" and "Pages" products

### Step 2: Get Page Access Token
1. Go to Graph API Explorer: https://developers.facebook.com/tools/explorer/
2. Select your app
3. Select "Get Page Access Token"
4. Choose your Facebook Page
5. Copy the token

### Step 3: Get Your Page ID
1. Go to your Facebook Page
2. Click "About" → "Page Transparency"
3. Copy the Page ID number

### Step 4: Edit Config File
Add to `~/newslancashire/config/social.json`:
```json
{
  "fb_access_token": "your_page_access_token_here",
  "fb_page_id": "your_page_id_here"
}
```

---

## Testing

Once configured, test posting:
```bash
cd ~/newslancashire
python3 scripts/social_poster.py
```

## Automation

Social media posting is set to run automatically when new original articles are published.

Cron job runs every 2 hours:
```
0 */2 * * * cd ~/newslancashire && python3 scripts/social_poster.py >> logs/social.log 2>&1
```

## What Gets Posted?

- **Original articles**: Posted to both Facebook and X
- **AI Digests**: Skipped (marked separately)
- **Guest posts**: Posted with attribution

## Rate Limits

- **X (Twitter)**: 50 tweets per day (free tier)
- **Facebook**: Higher limits, but post sparingly

## Security

Keep your API tokens secret! The config file is not tracked in git and has restricted permissions.

---

Need help? Ask Dominus (Clawdbot) for assistance with API setup.
