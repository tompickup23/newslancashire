#!/usr/bin/env python3
"""
Social Media Automation for News Lancashire
Posts to Facebook and X (Twitter) when new articles are published
"""

import sqlite3
import json
import os
from datetime import datetime
import requests

DB_PATH = '/home/ubuntu/newslancashire/db/news.db'
CONFIG_PATH = '/home/ubuntu/newslancashire/config/social.json'

def load_config():
    """Load social media API credentials"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def post_to_x(title, link, summary, config):
    """Post to X (Twitter) via API v2"""
    if not config.get('x_bearer_token'):
        print("X not configured - missing bearer token")
        return False
    
    # Truncate summary for tweet
    tweet_text = f"{title}\n\n{summary[:150]}...\n\nRead more: {link}"
    if len(tweet_text) > 280:
        tweet_text = f"{title[:200]}...\n\n{link}"
    
    print(f"[X] Would post: {tweet_text[:100]}...")
    # Actual API call would go here once credentials provided
    return True

def post_to_facebook(title, link, summary, config):
    """Post to Facebook Page via Graph API"""
    if not config.get('fb_access_token') or not config.get('fb_page_id'):
        print("Facebook not configured - missing token or page ID")
        return False
    
    message = f"{title}\n\n{summary}\n\nRead more: {link}"
    
    print(f"[Facebook] Would post to page {config.get('fb_page_id')}")
    # Actual API call would go here once credentials provided
    return True

def get_unposted_articles():
    """Get articles that haven't been posted to social media yet"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Add posted_to_social column if not exists
    try:
        c.execute("ALTER TABLE articles ADD COLUMN posted_to_social INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass  # Column already exists
    
    c.execute("""
        SELECT id, title, link, summary, source, is_burnley 
        FROM articles 
        WHERE posted_to_social = 0 
        ORDER BY published DESC 
        LIMIT 5
    """)
    
    articles = c.fetchall()
    conn.close()
    return articles

def mark_as_posted(article_id):
    """Mark article as posted to social media"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE articles SET posted_to_social = 1 WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()

def main():
    print(f"=== Social Media Automation - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    
    config = load_config()
    
    if not config:
        print("No social media config found.")
        print(f"Create: {CONFIG_PATH}")
        print("\nFormat:")
        print(json.dumps({
            "x_bearer_token": "your_x_token_here",
            "fb_access_token": "your_fb_token_here",
            "fb_page_id": "your_page_id_here"
        }, indent=2))
        return
    
    articles = get_unposted_articles()
    
    if not articles:
        print("No new articles to post.")
        return
    
    print(f"Found {len(articles)} articles to post\n")
    
    for article in articles:
        article_id, title, link, summary, source, is_burnley = article
        
        # Skip AI digest articles, only post originals
        if source == "AI Digest":
            print(f"Skipping AI digest: {title[:50]}...")
            mark_as_posted(article_id)
            continue
        
        print(f"Posting: {title[:60]}...")
        
        # Post to X
        if config.get('x_bearer_token'):
            post_to_x(title, link, summary, config)
        
        # Post to Facebook
        if config.get('fb_access_token'):
            post_to_facebook(title, link, summary, config)
        
        mark_as_posted(article_id)
        print()

if __name__ == '__main__':
    main()
