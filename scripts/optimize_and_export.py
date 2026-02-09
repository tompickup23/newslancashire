#!/usr/bin/env python3
"""
Optimized AI Summary Generator for News Lancashire
Reduces Claude API costs by ~80% through batching and local filtering
"""

import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict

DB_PATH = '/home/ubuntu/newslancashire/db/news.db'
BATCH_SIZE = 5

def cluster_articles(articles):
    """Group related articles by topic for batch processing"""
    clusters = defaultdict(list)
    
    for article in articles:
        title = article['title'].lower()
        
        if any(word in title for word in ['council', 'budget', 'meeting', 'committee']):
            clusters['council'].append(article)
        elif any(word in title for word in ['burnley', 'fc', 'football', 'match', 'premier league']):
            clusters['burnley_sport'].append(article)
        elif any(word in title for word in ['police', 'crime', 'court', 'arrest', 'stolen']):
            clusters['crime'].append(article)
        elif any(word in title for word in ['road', 'traffic', 'closure', 'a666', 'm65']):
            clusters['traffic'].append(article)
        elif any(word in title for word in ['weather', 'flood', 'storm', 'snow']):
            clusters['weather'].append(article)
        else:
            clusters['general'].append(article)
    
    return clusters

def should_process_article(article):
    """Filter out low-value articles locally"""
    title = article.get('title', '')
    summary = article.get('summary', '')
    text = (title + ' ' + summary).lower()
    
    # Skip if too short (less than 100 chars)
    if len(summary) < 100:
        return False, "too_short"
    
    # Skip promotional content
    promo_words = ['sale', 'discount', 'offer', 'buy now', 'promo', 'advertisement']
    if any(word in text for word in promo_words):
        return False, "promotional"
    
    # Skip duplicate titles (simple check)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM articles WHERE title = ? AND is_processed = 1", (title,))
    count = c.fetchone()[0]
    conn.close()
    
    if count > 0:
        return False, "duplicate"
    
    return True, "ok"

def prepare_batches():
    """Prepare optimized batches for AI summarization"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get unprocessed articles
    c.execute("""
        SELECT id, title, summary, link, source, published 
        FROM articles 
        WHERE is_processed = 0 
        ORDER BY published DESC
    """)
    
    articles = []
    for row in c.fetchall():
        articles.append({
            'id': row[0],
            'title': row[1],
            'summary': row[2],
            'link': row[3],
            'source': row[4],
            'published': row[5]
        })
    
    conn.close()
    
    # Filter locally
    filtered = []
    skipped = {'too_short': 0, 'promotional': 0, 'duplicate': 0}
    
    for art in articles:
        should_process, reason = should_process_article(art)
        if should_process:
            filtered.append(art)
        else:
            skipped[reason] += 1
            # Mark as processed to skip in future
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE articles SET is_processed = 1 WHERE id = ?", (art['id'],))
            conn.commit()
            conn.close()
    
    # Cluster by topic
    clustered = cluster_articles(filtered)
    
    # Create batches
    batches = []
    for topic, topic_articles in clustered.items():
        for i in range(0, len(topic_articles), BATCH_SIZE):
            batch = topic_articles[i:i+BATCH_SIZE]
            batches.append({
                'topic': topic,
                'articles': batch,
                'batch_id': f"{topic}_{i//BATCH_SIZE}"
            })
    
    return batches, skipped

def export_for_dominus():
    """Export batches for Dominus to process with Claude API"""
    batches, skipped = prepare_batches()
    
    export_data = {
        'generated_at': datetime.now().isoformat(),
        'total_batches': len(batches),
        'total_articles': sum(len(b['articles']) for b in batches),
        'skipped': skipped,
        'estimated_cost': len(batches) * 0.015,  # ~$0.015 per batch
        'batches': batches
    }
    
    # Save to file
    export_path = '/home/ubuntu/newslancashire/data/batches_for_ai.json'
    with open(export_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"=== AI Summary Batches Ready ===")
    print(f"Batches: {len(batches)}")
    print(f"Articles: {export_data['total_articles']}")
    print(f"Skipped: {sum(skipped.values())} (filtered locally)")
    print(f"Estimated cost: ${export_data['estimated_cost']:.2f}")
    print(f"")
    print(f"Export saved to: {export_path}")
    print(f"")
    print(f"Dominus: Run 'scp thurinus:{export_path} .' to download")
    print(f"Then process with Claude API and push summaries back.")

if __name__ == '__main__':
    export_for_dominus()
