#!/usr/bin/env python3
"""
Reddit Community Intelligence Monitor
Tracks r/Lancashire, r/Burnley for trending topics and community concerns
"""
import sqlite3
import hashlib
import json
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

# Lancashire subreddits to monitor
SUBREDDITS = [
    {'name': 'Lancashire', 'borough': None},  # General Lancashire
    {'name': 'Burnley', 'borough': 'burnley'},
    {'name': 'preston', 'borough': 'preston'},
    {'name': 'Blackpool', 'borough': 'blackpool'},
]

def fetch_subreddit_posts(subreddit, limit=10):
    """Fetch hot posts from a subreddit via Reddit JSON API."""
    url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}'
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'NewsLancashireBot/1.0 (by /u/newslancashire)',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f'Reddit API error for r/{subreddit}: {e}')
        return None

def calculate_interest_score(post):
    """Calculate interest based on engagement."""
    score = post.get('score', 0)
    comments = post.get('num_comments', 0)
    
    # Base score from upvotes
    base = min(100, score / 10)
    
    # Boost for high engagement
    comment_boost = min(30, comments / 5)
    
    return min(100, int(base + comment_boost))

def categorize_post(title):
    """Categorize post by content."""
    title_lower = title.lower()
    
    if any(x in title_lower for x in ['crime', 'police', 'stolen', 'robbery', 'arrest']):
        return 'crime', 75
    
    if any(x in title_lower for x in ['council', 'planning', 'development', 'budget']):
        return 'politics', 70
    
    if any(x in title_lower for x in ['traffic', 'road', 'm65', 'm6', 'closed']):
        return 'transport', 65
    
    if any(x in title_lower for x in ['job', 'hiring', 'work', 'employment']):
        return 'business', 55
    
    if any(x in title_lower for x in ['event', 'festival', 'market']):
        return 'community', 50
    
    return 'general', 40

def insert_reddit_article(conn, article, borough):
    """Insert Reddit post as article."""
    borough_flags = {f'is_{c}': 0 for c in 
                    ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                     'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                     'west_lancashire', 'wyre', 'fylde']}
    
    if borough:
        borough_flags[f'is_{borough}'] = 1
    else:
        # If no specific borough, mark as general Lancashire
        pass
    
    search_text = f"{article['title']} {article['summary']}".lower()
    
    conn.execute('''
        INSERT OR IGNORE INTO articles 
        (id, title, link, source, source_type, published, summary, ai_rewrite,
         category, content_tier, interest_score, trending_score, author, search_text,
         is_burnley, is_hyndburn, is_pendle, is_rossendale, is_ribble_valley,
         is_blackburn, is_chorley, is_south_ribble, is_preston, is_west_lancashire,
         is_lancaster, is_wyre, is_fylde, is_blackpool)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        article['id'], article['title'], article['link'], article['source'],
        article['source_type'], article['published'], article['summary'], article['ai_rewrite'],
        article['category'], article['content_tier'], article['interest_score'], article['trending_score'],
        article['author'], search_text,
        borough_flags['is_burnley'], borough_flags['is_hyndburn'], borough_flags['is_pendle'], 
        borough_flags['is_rossendale'], borough_flags['is_ribble_valley'], borough_flags['is_blackburn'], 
        borough_flags['is_chorley'], borough_flags['is_south_ribble'], borough_flags['is_preston'], 
        borough_flags['is_west_lancashire'], borough_flags['is_lancaster'], borough_flags['is_wyre'],
        borough_flags['is_fylde'], borough_flags['is_blackpool']
    ))
    conn.commit()

def main():
    print('=== Reddit Community Monitor ===')
    print(f'Monitoring {len(SUBREDDITS)} subreddits')
    
    conn = get_db()
    total_new = 0
    
    for sub in SUBREDDITS:
        print(f"\nChecking r/{sub['name']}...")
        
        data = fetch_subreddit_posts(sub['name'])
        if not data or 'data' not in data:
            continue
        
        posts = data['data'].get('children', [])
        
        for post_data in posts[:5]:  # Top 5 posts
            post = post_data.get('data', {})
            
            # Skip stickied/announcement posts
            if post.get('stickied'):
                continue
            
            title = post.get('title', '')
            url = post.get('url', '')
            permalink = f"https://reddit.com{post.get('permalink', '')}"
            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            author = post.get('author', 'unknown')
            
            # Skip low-engagement posts
            if score < 10 and comments < 5:
                continue
            
            interest = calculate_interest_score(post)
            category, base_interest = categorize_post(title)
            interest = max(interest, base_interest)
            
            # Only track posts with decent engagement
            if interest < 45:
                continue
            
            article_id = hashlib.md5(f"reddit-{post.get('id')}".encode()).hexdigest()
            
            title_prefix = 'Trending' if score > 50 else 'Community'
            article_title = f"{title_prefix} on r/{sub['name']}: {title[:80]}"
            
            summary = f"{title}. Discussion on r/{sub['name']} with {score} upvotes and {comments} comments. Original post by u/{author}."
            
            article = {
                'id': article_id,
                'title': article_title,
                'link': permalink,
                'source': f"r/{sub['name']} (Reddit)",
                'source_type': 'reddit',
                'published': datetime.now().isoformat(),
                'summary': summary,
                'ai_rewrite': None,  # Let AI rewriter handle this
                'category': category,
                'interest_score': interest,
                'trending_score': min(100, int(score / 5)),
                'content_tier': 'community_intelligence',
                'author': f'u/{author}'
            }
            
            try:
                insert_reddit_article(conn, article, sub.get('borough'))
                total_new += 1
                print(f"  Added: {title[:60]}... ({score} upvotes)")
            except sqlite3.IntegrityError:
                pass
            except Exception as e:
                print(f'  Error: {e}')
    
    print(f'\nTotal new Reddit posts: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
