#!/usr/bin/env python3
"""
Weekly Digest Generator - Automated newsletter-style summaries
Generates weekly roundups of crime, spending, and council activity
"""
import sqlite3
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

AIDOGE_DATA = '/home/ubuntu/aidoge/data'

def generate_weekly_crime_digest():
    """Generate weekly crime summary across all councils."""
    councils_data = []
    total_crimes = 0
    
    for council in ['burnley', 'hyndburn', 'pendle']:
        crime_file = f'{AIDOGE_DATA}/{council}/crime_stats.json'
        if not os.path.exists(crime_file):
            continue
        
        with open(crime_file) as f:
            data = json.load(f)
        
        councils_data.append({
            'name': data.get('borough_name', council.title()),
            'crimes': data.get('total_crimes', 0),
            'top_crime': max(data.get('by_category', {}).items(), key=lambda x: x[1]) if data.get('by_category') else ('Unknown', 0)
        })
        total_crimes += data.get('total_crimes', 0)
    
    if not councils_data:
        return None
    
    title = f"Weekly Crime Digest: {total_crimes} offences across Lancashire councils"
    
    summary_parts = []
    for c in councils_data:
        summary_parts.append(f"{c['name']}: {c['crimes']} crimes ({c['top_crime'][1]} {c['top_crime'][0].replace('-', ' ')})")
    
    summary = f"Latest police data shows {total_crimes} crimes reported across monitored Lancashire boroughs. " + " | ".join(summary_parts) + ". Full ward-by-ward breakdowns available via AI DOGE."
    
    article_id = hashlib.md5(f'weekly-crime-{datetime.now().strftime("%Y-%W")}'.encode()).hexdigest()
    
    return {
        'id': article_id,
        'title': title,
        'link': 'https://aidoge.co.uk/',
        'source': 'AI DOGE Weekly Crime Digest',
        'source_type': 'weekly_digest',
        'published': datetime.now().isoformat(),
        'summary': summary,
        'ai_rewrite': summary,
        'category': 'crime',
        'interest_score': 80,
        'trending_score': 55,
        'content_tier': 'digest',
        'author': 'Weekly Digest',
        'is_burnley': 1, 'is_hyndburn': 1, 'is_pendle': 1,
        'is_rossendale': 0, 'is_ribble_valley': 0, 'is_blackburn': 0, 'is_chorley': 0,
        'is_south_ribble': 0, 'is_preston': 0, 'is_west_lancashire': 0, 'is_lancaster': 0,
        'is_wyre': 0, 'is_fylde': 0, 'is_blackpool': 0
    }

def generate_weekly_spending_digest():
    """Generate weekly spending highlights."""
    council_totals = []
    grand_total = 0
    
    for council in ['burnley', 'hyndburn', 'pendle']:
        spending_file = f'{AIDOGE_DATA}/{council}/spending.json'
        if not os.path.exists(spending_file):
            continue
        
        try:
            with open(spending_file) as f:
                data = json.load(f)
        except:
            continue
        
        transactions = data.get('data', [])
        if not transactions:
            continue
        
        # Get top payment
        top = max(transactions, key=lambda x: float(x.get('amount', 0)))
        total = sum(float(t.get('amount', 0)) for t in transactions[:100])
        
        council_totals.append({
            'name': council.title(),
            'total': total,
            'top_payment': top
        })
        grand_total += total
    
    if not council_totals:
        return None
    
    title = f"Weekly Council Spending: £{grand_total/1e6:.1f}M across 3 Lancashire boroughs"
    
    parts = []
    for c in council_totals:
        parts.append(f"{c['name']}: £{c['total']/1e6:.2f}M")
    
    summary = f"Council spending data shows £{grand_total/1e6:.2f}million in recent transactions. " + " | ".join(parts) + ". Full transaction details available on AI DOGE."
    
    article_id = hashlib.md5(f'weekly-spending-{datetime.now().strftime("%Y-%W")}'.encode()).hexdigest()
    
    return {
        'id': article_id,
        'title': title,
        'link': 'https://aidoge.co.uk/',
        'source': 'AI DOGE Weekly Spending Digest',
        'source_type': 'weekly_digest',
        'published': datetime.now().isoformat(),
        'summary': summary,
        'ai_rewrite': summary,
        'category': 'politics',
        'interest_score': 75,
        'trending_score': 50,
        'content_tier': 'digest',
        'author': 'Weekly Digest',
        'is_burnley': 1, 'is_hyndburn': 1, 'is_pendle': 1,
        'is_rossendale': 0, 'is_ribble_valley': 0, 'is_blackburn': 0, 'is_chorley': 0,
        'is_south_ribble': 0, 'is_preston': 0, 'is_west_lancashire': 0, 'is_lancaster': 0,
        'is_wyre': 0, 'is_fylde': 0, 'is_blackpool': 0
    }

def insert_digest(conn, article):
    """Insert weekly digest article."""
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
        article['is_burnley'], article['is_hyndburn'], article['is_pendle'], article['is_rossendale'],
        article['is_ribble_valley'], article['is_blackburn'], article['is_chorley'], article['is_south_ribble'],
        article['is_preston'], article['is_west_lancashire'], article['is_lancaster'], article['is_wyre'],
        article['is_fylde'], article['is_blackpool']
    ))
    conn.commit()

def main():
    print('=== Weekly Digest Generator ===')
    conn = get_db()
    total_new = 0
    
    # Only run on Mondays (weekly digest)
    if datetime.now().weekday() != 0:
        print('Not Monday - skipping weekly digest (runs Mondays only)')
        conn.close()
        return
    
    print('\nGenerating weekly crime digest...')
    article = generate_weekly_crime_digest()
    if article:
        try:
            insert_digest(conn, article)
            total_new += 1
            print(f'  Added: {article["title"][:60]}...')
        except sqlite3.IntegrityError:
            print(f'  Exists: Weekly crime digest already generated this week')
        except Exception as e:
            print(f'  Error: {e}')
    
    print('\nGenerating weekly spending digest...')
    article = generate_weekly_spending_digest()
    if article:
        try:
            insert_digest(conn, article)
            total_new += 1
            print(f'  Added: {article["title"][:60]}...')
        except sqlite3.IntegrityError:
            print(f'  Exists: Weekly spending digest already generated this week')
        except Exception as e:
            print(f'  Error: {e}')
    
    print(f'\nTotal new weekly digests: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
