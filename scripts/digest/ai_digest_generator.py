#!/usr/bin/env python3
"""
AI Digest Generator - Continues Claude's Work
Generates AI-powered summary digests from the article database
Creates borough-specific and topic-specific digests
"""
import sqlite3
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

# API configuration
KIMI_API_URL = 'https://api.moonshot.ai/v1/chat/completions'
KIMI_API_KEY = os.environ.get('MOONSHOT_API_KEY', '')

def fetch_articles_for_digest(conn, hours=24, min_interest=40):
    """Fetch articles from last N hours for digest."""
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    c = conn.execute('''
        SELECT id, title, summary, category, is_burnley, is_hyndburn, is_pendle,
               is_blackpool, is_preston, is_lancaster, is_rossendale, is_ribble_valley,
               is_blackburn, is_chorley, is_south_ribble, is_west_lancashire, is_wyre, is_fylde
        FROM articles
        WHERE published > ? AND interest_score >= ?
        ORDER BY interest_score DESC, published DESC
        LIMIT 50
    ''', (since, min_interest))
    
    return c.fetchall()

def group_by_borough(articles):
    """Group articles by borough."""
    boroughs = {
        'burnley': [], 'hyndburn': [], 'pendle': [], 'blackpool': [],
        'preston': [], 'lancaster': [], 'rossendale': [], 'ribble_valley': [],
        'blackburn': [], 'chorley': [], 'south_ribble': [], 'west_lancashire': [],
        'wyre': [], 'fylde': []
    }
    
    for article in articles:
        # Article structure from SELECT: id(0), title(1), summary(2), category(3), 
        # then borough flags starting at index 4
        borough_map = {
            'burnley': 4, 'hyndburn': 5, 'pendle': 6, 'blackpool': 7,
            'preston': 8, 'lancaster': 9, 'rossendale': 10, 'ribble_valley': 11,
            'blackburn': 12, 'chorley': 13, 'south_ribble': 14, 'west_lancashire': 15,
            'wyre': 16, 'fylde': 17
        }
        for borough, idx in borough_map.items():
            if idx < len(article) and article[idx] == 1:
                boroughs[borough].append(article)
    
    return {k: v for k, v in boroughs.items() if v}

def group_by_category(articles):
    """Group articles by category."""
    categories = {}
    for article in articles:
        cat = article[3] or 'general'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(article)
    return categories

def generate_digest_with_kimi(articles, digest_type, context):
    """Generate AI digest using Kimi K2.5."""
    if not KIMI_API_KEY:
        print('No Kimi API key - using template digest')
        return generate_template_digest(articles, digest_type, context)
    
    # Build prompt
    article_texts = []
    for article in articles[:10]:
        article_texts.append(f"- {article[1]}: {article[2][:100]}...")
    
    prompt = f"""Write a news digest summary for {context}. Based on these articles:

{chr(10).join(article_texts)}

Write a concise 3-paragraph digest that:
1. Summarizes the main stories
2. Highlights any significant developments
3. Provides context for Lancashire residents

Keep it factual, objective, and engaging."""
    
    try:
        payload = json.dumps({
            'model': 'kimi-k2.5',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
            'max_tokens': 500
        }).encode()
        
        req = urllib.request.Request(KIMI_API_URL, data=payload, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {KIMI_API_KEY}'
        })
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f'Kimi API error: {e}')
        return generate_template_digest(articles, digest_type, context)

def generate_template_digest(articles, digest_type, context):
    """Generate template-based digest when AI unavailable."""
    lines = [f"# {context} News Digest", ""]
    lines.append(f"Key stories from the last 24 hours in {context}:")
    lines.append("")
    
    for article in articles[:8]:
        lines.append(f"• **{article[1]}** - {article[2][:120]}...")
    
    lines.append("")
    lines.append("*This digest is automatically generated from local news sources.*")
    
    return "\n".join(lines)

def create_borough_digest(conn, borough_name, articles):
    """Create a digest for a specific borough."""
    if len(articles) < 3:
        return None
    
    borough_display = borough_name.replace('_', ' ').title()
    
    content = generate_digest_with_kimi(
        articles, 
        'borough', 
        borough_display
    )
    
    article_id = hashlib.md5(f"digest-{borough_name}-{datetime.now().strftime('%Y-%m-%d')}".encode()).hexdigest()
    
    title = f"{borough_display} Daily Digest: {len(articles)} stories you need to know"
    summary = f"A roundup of the latest news from {borough_display}, including {articles[0][1]} and other key stories."
    
    return {
        'id': article_id,
        'title': title,
        'summary': summary,
        'content': content,
        'borough': borough_name,
        'article_count': len(articles)
    }

def create_category_digest(conn, category, articles):
    """Create a digest for a specific category."""
    if len(articles) < 3:
        return None
    
    category_display = category.title()
    
    content = generate_digest_with_kimi(
        articles,
        'category',
        f'{category_display} News'
    )
    
    article_id = hashlib.md5(f"digest-{category}-{datetime.now().strftime('%Y-%m-%d')}".encode()).hexdigest()
    
    title = f"{category_display} Roundup: {len(articles)} key stories"
    summary = f"Latest {category_display.lower()} news from across Lancashire."
    
    return {
        'id': article_id,
        'title': title,
        'summary': summary,
        'content': content,
        'category': category,
        'article_count': len(articles)
    }

def save_digest_to_database(conn, digest, digest_type='borough'):
    """Save digest as article in database."""
    borough_flags = {f'is_{c}': 0 for c in 
                    ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                     'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                     'west_lancashire', 'wyre', 'fylde']}
    
    if digest_type == 'borough' and digest.get('borough'):
        borough_flags[f"is_{digest['borough']}"] = 1
    else:
        borough_flags = {k: 1 for k in borough_flags.keys()}
    
    search_text = f"{digest['title']} {digest['summary']} {digest['content']}".lower()
    
    conn.execute('''
        INSERT OR IGNORE INTO articles 
        (id, title, link, source, source_type, published, summary, ai_rewrite,
         category, content_tier, interest_score, trending_score, author, search_text,
         is_burnley, is_hyndburn, is_pendle, is_rossendale, is_ribble_valley,
         is_blackburn, is_chorley, is_south_ribble, is_preston, is_west_lancashire,
         is_lancaster, is_wyre, is_fylde, is_blackpool)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        digest['id'], digest['title'], 'https://newslancashire.co.uk/',
        f"AI Digest ({digest_type})", 'ai_digest',
        datetime.now().isoformat(), digest['summary'], digest['content'][:500],
        digest.get('category', digest.get('borough', 'general')), 'digest',
        70, 50, 'AI Digest Generator', search_text[:500],
        borough_flags['is_burnley'], borough_flags['is_hyndburn'], borough_flags['is_pendle'], 
        borough_flags['is_rossendale'], borough_flags['is_ribble_valley'], borough_flags['is_blackburn'], 
        borough_flags['is_chorley'], borough_flags['is_south_ribble'], borough_flags['is_preston'], 
        borough_flags['is_west_lancashire'], borough_flags['is_lancaster'], borough_flags['is_wyre'],
        borough_flags['is_fylde'], borough_flags['is_blackpool']
    ))
    conn.commit()

def main():
    print('=== AI Digest Generator ===')
    print('Continuing Claude Code work on /digest/ section')
    
    conn = get_db()
    
    print('\nFetching articles from last 24 hours...')
    articles = fetch_articles_for_digest(conn)
    print(f'Found {len(articles)} articles for digest')
    
    if len(articles) < 5:
        print('Not enough articles for meaningful digest')
        conn.close()
        return
    
    total_digests = 0
    
    print('\nGenerating borough digests...')
    borough_articles = group_by_borough(articles)
    for borough, b_articles in borough_articles.items():
        if len(b_articles) >= 3:
            digest = create_borough_digest(conn, borough, b_articles)
            if digest:
                try:
                    save_digest_to_database(conn, digest, 'borough')
                    total_digests += 1
                    print(f"  Created digest for {borough.replace('_', ' ').title()} ({len(b_articles)} articles)")
                except Exception as e:
                    print(f'  Error saving {borough} digest: {e}')
    
    print('\nGenerating category digests...')
    category_articles = group_by_category(articles)
    for category, c_articles in category_articles.items():
        if len(c_articles) >= 5:
            digest = create_category_digest(conn, category, c_articles)
            if digest:
                try:
                    save_digest_to_database(conn, digest, 'category')
                    total_digests += 1
                    print(f"  Created {category} digest ({len(c_articles)} articles)")
                except Exception as e:
                    print(f'  Error saving {category} digest: {e}')
    
    print(f'\nTotal digests generated: {total_digests}')
    conn.close()

if __name__ == '__main__':
    main()
