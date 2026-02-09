#!/usr/bin/env python3
"""
Auto-Social Poster - News Lancashire
Posts new articles to X (Twitter) and Bluesky automatically
OAuth 1.0a for X posting
"""
import json
import sqlite3
import requests
import base64
import hashlib
import hmac
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
CONFIG_FILE = BASE_DIR / "config/social.json"
CACHE_DB = BASE_DIR / "db/social_posts.db"
LOG_FILE = BASE_DIR / "logs/social_poster.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {msg}\n")

def init_db():
    CACHE_DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posted (
        article_id TEXT PRIMARY KEY,
        platform TEXT,
        posted_at INTEGER,
        post_url TEXT
    )''')
    conn.commit()
    conn.close()

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except:
        return {}

def load_articles():
    try:
        with open(ARTICLES_FILE) as f:
            return json.load(f)
    except:
        return []

def is_posted(article_id, platform):
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM posted WHERE article_id=? AND platform=?", (article_id, platform))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_posted(article_id, platform, post_url=None):
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute("INSERT INTO posted VALUES (?, ?, ?, ?)",
              (article_id, platform, int(time.time()), post_url))
    conn.commit()
    conn.close()

def format_post(article):
    """Create social post from article"""
    title = article.get("title", "")
    borough = article.get("borough", "")
    category = article.get("category", "")
    url = article.get("url", "")
    
    # Truncate title if too long
    max_title = 200 if url else 250
    if len(title) > max_title:
        title = title[:max_title-3] + "..."
    
    # Build hashtags
    hashtags = ["#NewsLancashire"]
    if borough:
        hashtags.append(f"#{borough.replace('_', '').title()}")
    if category:
        hashtags.append(f"#{category.title()}")
    
    hashtag_str = " ".join(hashtags)
    
    # Assemble post
    post = f"{title}\n\n{hashtag_str}"
    if url:
        post += f"\n\n{url}"
    
    return post[:280]  # X limit

def oauth1_sign(method, url, params, consumer_secret, token_secret):
    """Create OAuth 1.0a signature"""
    param_string = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}" 
                           for k, v in sorted(params.items()))
    base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    signing_key = f"{urllib.parse.quote(consumer_secret)}&{urllib.parse.quote(token_secret)}"
    signature = base64.b64encode(hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()).decode()
    return signature

def post_to_x_v2(text, config):
    """Post to X (Twitter) API v2 with OAuth 1.0a"""
    api_key = config.get("x_api_key", "")
    api_secret = config.get("x_api_secret", "")
    access_token = config.get("x_access_token", "")
    access_token_secret = config.get("x_access_token_secret", "")
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        log("Missing X OAuth credentials")
        return None
    
    url = "https://api.twitter.com/2/tweets"
    
    # OAuth 1.0a parameters
    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": hashlib.md5(str(time.time()).encode()).hexdigest()[:32],
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0"
    }
    
    # Create signature
    oauth_params["oauth_signature"] = oauth1_sign("POST", url, oauth_params, api_secret, access_token_secret)
    
    # Build Authorization header
    auth_header = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(v)}"' for k, v in oauth_params.items())
    
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    
    payload = {"text": text}
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 201:
            data = resp.json()
            tweet_id = data.get("data", {}).get("id")
            log(f"Posted to X: {tweet_id}")
            return f"https://twitter.com/i/web/status/{tweet_id}"
        else:
            log(f"X API error: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        log(f"X post failed: {e}")
    
    return None

def post_to_bluesky(text, config):
    """Post to Bluesky (requires auth setup)"""
    # Placeholder - needs session/auth
    log(f"[Bluesky] Would post: {text[:50]}...")
    return None

def main():
    log("[Auto-Social Poster] Starting...")
    
    init_db()
    config = load_config()
    articles = load_articles()
    
    if not articles:
        log("No articles found")
        return
    
    # Sort by date, newest first
    articles.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # Only check last 10 articles (recent)
    recent_articles = articles[:10]
    
    posted_count = 0
    skipped_count = 0
    
    for article in recent_articles:
        article_id = article.get("id", article.get("url", ""))
        
        if not article_id:
            continue
        
        # Skip if already posted to X
        if is_posted(article_id, "x"):
            skipped_count += 1
            continue
        
        # Format post
        post_text = format_post(article)
        
        # Post to X
        post_url = post_to_x_v2(post_text, config)
        if post_url:
            mark_posted(article_id, "x", post_url)
            posted_count += 1
            time.sleep(2)  # Rate limit spacing
        
        # Post to Bluesky
        if not is_posted(article_id, "bluesky"):
            post_to_bluesky(post_text, config)
            mark_posted(article_id, "bluesky")
    
    log(f"[Auto-Social Poster] Complete. Posted: {posted_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    main()