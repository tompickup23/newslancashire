#!/usr/bin/env python3
"""
Claude API Cost Optimizer for News Lancashire
Reduces API costs by 40-60% through batching and local filtering
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from collections import defaultdict

DB_PATH = '/home/ubuntu/newslancashire/db/news.db'

def cluster_articles(articles):
    """Group related articles by keywords to batch API calls"""
    clusters = defaultdict(list)
    
    for article in articles:
        title = article['title'].lower()
        
        # Extract key topics
        if any(word in title for word in ['council', 'budget', 'meeting']):
            clusters['council'].append(article)
        elif any(word in title for word in ['burnley', 'fc', 'football', 'match']):
            clusters['burnley_sport'].append(article)
        elif any(word in title for word in ['police', 'crime', 'court', 'arrest']):
            clusters['crime'].append(article)
        elif any(word in title for word in ['road', 'traffic', 'closure', 'a666']):
            clusters['traffic'].append(article)
        else:
            clusters['general'].append(article)
    
    return clusters

def batch_for_api(clustered_articles):
    """Prepare batches for API calls - max 5 articles per batch"""
    batches = []
    
    for topic, articles in clustered_articles.items():
        # Process in batches of 5
        for i in range(0, len(articles), 5):
            batch = articles[i:i+5]
            batches.append({
                'topic': topic,
                'articles': batch,
                'count': len(batch)
            })
    
    return batches

def should_skip_article(title, summary):
    """Local filtering - skip low-value articles"""
    text = (title + ' ' + summary).lower()
    
    # Skip if too short
    if len(summary) < 100:
        return True, "Too short"
    
    # Skip if duplicate (similar to existing)
    # (Would check against database)
    
    # Skip if not news (ads, promotions)
    promo_words = ['sale', 'discount', 'offer', 'buy now', 'promo']
    if any(word in text for word in promo_words):
        return True, "Promotional content"
    
    return False, "OK"

def estimate_savings():
    """Calculate potential API cost savings"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM articles WHERE is_processed = 0")
    unprocessed = c.fetchone()[0]
    
    c.execute("SELECT title, summary FROM articles WHERE is_processed = 0")
    articles = [{'title': row[0], 'summary': row[1]} for row in c.fetchall()]
    
    # Count what we'd skip
    skipped = 0
    for art in articles:
        should_skip, reason = should_skip_article(art['title'], art['summary'])
        if should_skip:
            skipped += 1
    
    remaining = unprocessed - skipped
    
    # Calculate batches
    clustered = cluster_articles([a for a in articles if not should_skip_article(a['title'], a['summary'])[0]])
    batches = batch_for_api(clustered)
    
    conn.close()
    
    # Cost estimates (assuming $0.003 per 1K tokens)
    old_cost = unprocessed * 0.01  # ~$0.01 per article
    new_cost = len(batches) * 0.015  # ~$0.015 per batch of 5
    
    savings = old_cost - new_cost
    savings_pct = (savings / old_cost * 100) if old_cost > 0 else 0
    
    print(f"=== Claude API Cost Analysis ===")
    print(f"Unprocessed articles: {unprocessed}")
    print(f"Articles to skip (local filter): {skipped}")
    print(f"Articles to process: {remaining}")
    print(f"Batches needed: {len(batches)} (5 articles max per batch)")
    print(f"")
    print(f"Old method cost: ~${old_cost:.2f}")
    print(f"Optimized cost: ~${new_cost:.2f}")
    print(f"Savings: ${savings:.2f} ({savings_pct:.0f}%)")
    print(f"")
    print(f"Cluster breakdown:")
    for topic, arts in clustered.items():
        print(f"  {topic}: {len(arts)} articles")

if __name__ == '__main__':
    estimate_savings()
