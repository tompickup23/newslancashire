#!/usr/bin/env python3
"""
Influencer Monitor - Social media monitoring for Lancashire celebrities
Modular enhanced source for News Lancashire pipeline
Rate-limited, cached, priority-based
"""

import json
import sqlite3
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

BASE_DIR = Path("/home/ubuntu/newslancashire")
CONFIG_FILE = BASE_DIR / "config/lancashire_influencers.json"
CACHE_DB = BASE_DIR / "db/influencer_cache.db"
OUTPUT_FILE = BASE_DIR / "data/influencer_content.json"

# Rate limits (requests per 15 min window)
RATE_LIMITS = {
    "x": 450,           # X API v2
    "instagram": 200,   # Instagram Basic Display
    "bluesky": 3000,    # Bluesky is generous
    "tiktok": 200       # TikTok Research API
}

class InfluencerMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.init_db()
        self.results = []
        
    def load_config(self):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    
    def init_db(self):
        CACHE_DB.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(CACHE_DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS api_calls (
            platform TEXT, timestamp INTEGER, count INTEGER DEFAULT 1
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS content_cache (
            id TEXT PRIMARY KEY, handle TEXT, platform TEXT,
            content TEXT, timestamp INTEGER, url TEXT
        )''')
        conn.commit()
        conn.close()
    
    def check_rate_limit(self, platform):
        """Check if we're within rate limits"""
        conn = sqlite3.connect(CACHE_DB)
        c = conn.cursor()
        window_15min = int(time.time()) - (15 * 60)
        c.execute("SELECT SUM(count) FROM api_calls WHERE platform=? AND timestamp>?",
                  (platform, window_15min))
        count = c.fetchone()[0] or 0
        conn.close()
        return count < RATE_LIMITS.get(platform, 100)
    
    def log_api_call(self, platform):
        """Log an API call for rate tracking"""
        conn = sqlite3.connect(CACHE_DB)
        c = conn.cursor()
        c.execute("INSERT INTO api_calls (platform, timestamp) VALUES (?, ?)",
                  (platform, int(time.time())))
        conn.commit()
        conn.close()
    
    def get_cached(self, handle, platform, max_age_hours=6):
        """Get cached content if fresh"""
        conn = sqlite3.connect(CACHE_DB)
        c = conn.cursor()
        cutoff = int(time.time()) - (max_age_hours * 3600)
        c.execute("SELECT content, url FROM content_cache WHERE handle=? AND platform=? AND timestamp>?",
                  (handle, platform, cutoff))
        result = c.fetchone()
        conn.close()
        return result
    
    def cache_content(self, content_id, handle, platform, content, url):
        """Cache fetched content"""
        conn = sqlite3.connect(CACHE_DB)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO content_cache 
                     (id, handle, platform, content, timestamp, url)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (content_id, handle, platform, content, int(time.time()), url))
        conn.commit()
        conn.close()
    
    def fetch_x_posts(self, handle, priority="medium"):
        """Fetch X posts (simulated - needs API token)"""
        if not self.check_rate_limit("x"):
            print(f"  Rate limit hit for X, skipping @{handle}")
            return []
        
        cached = self.get_cached(handle, "x")
        if cached:
            print(f"  Using cached X content for @{handle}")
            return []
        
        # TODO: Implement X API v2 calls with bearer token
        # For now, placeholder
        self.log_api_call("x")
        time.sleep(random.uniform(1, 3))  # Rate limit spacing
        return []
    
    def fetch_bluesky_posts(self, handle, priority="medium"):
        """Fetch Bluesky posts via public API"""
        if not self.check_rate_limit("bluesky"):
            return []
        
        cached = self.get_cached(handle, "bluesky")
        if cached:
            return []
        
        try:
            import requests
            # Bluesky public API - no auth needed for read
            api_url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
            params = {"actor": handle, "limit": 10}
            
            resp = requests.get(api_url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                posts = []
                for post in data.get("feed", []):
                    record = post.get("post", {}).get("record", {})
                    text = record.get("text", "")
                    if text:
                        posts.append({
                            "handle": handle,
                            "platform": "bluesky",
                            "content": text[:280],
                            "url": f"https://bsky.app/profile/{handle}/post/{post['post']['uri'].split('/')[-1]}",
                            "timestamp": int(time.time()),
                            "priority": priority
                        })
                
                self.log_api_call("bluesky")
                return posts
        except Exception as e:
            print(f"  Bluesky error for @{handle}: {e}")
        
        return []
    
    def run(self):
        """Main monitoring loop"""
        print(f"[{datetime.now()}] Influencer Monitor starting...")
        
        all_content = []
        
        # Process by priority
        priorities = ["critical", "high", "medium", "low"]
        
        for priority in priorities:
            print(f"\nProcessing {priority} priority...")
            
            # X/Twitter
            for account in self.config.get("x_lancashire_influencers", []):
                if account.get("priority") == priority or (priority == "medium" and not account.get("priority")):
                    print(f"  Checking X: @{account['handle']}")
                    posts = self.fetch_x_posts(account["handle"], priority)
                    all_content.extend(posts)
                    time.sleep(2)  # Be nice to APIs
            
            # Bluesky
            for account in self.config.get("bluesky_influencers", []):
                if account.get("priority") == priority or (priority == "medium" and not account.get("priority")):
                    print(f"  Checking Bluesky: @{account['handle']}")
                    posts = self.fetch_bluesky_posts(account["handle"], priority)
                    all_content.extend(posts)
                    time.sleep(1)
        
        # Save results
        OUTPUT_FILE.parent.mkdir(exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(all_content, f, indent=2)
        
        print(f"\n[{datetime.now()}] Monitor complete. {len(all_content)} items fetched.")
        print(f"Output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    monitor = InfluencerMonitor()
    monitor.run()