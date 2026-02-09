#!/usr/bin/env python3
"""
Food Hygiene Ratings Crawler (FSA API)
Alerts on poor ratings (0-2 stars) in Lancashire
"""
import sqlite3
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

FSA_API = 'http://api.ratings.food.gov.uk'

# Lancashire local authorities with FSA IDs
LANCASHIRE_AUTHORITIES = [
    {'id': 182, 'name': 'Burnley', 'borough': 'burnley'},
    {'id': 188, 'name': 'Hyndburn', 'borough': 'hyndburn'},
    {'id': 191, 'name': 'Lancaster', 'borough': 'lancaster'},
    {'id': 193, 'name': 'Pendle', 'borough': 'pendle'},
    {'id': 199, 'name': 'Preston', 'borough': 'preston'},
    {'id': 200, 'name': 'Ribble Valley', 'borough': 'ribble_valley'},
    {'id': 201, 'name': 'Rossendale', 'borough': 'rossendale'},
    {'id': 202, 'name': 'South Ribble', 'borough': 'south_ribble'},
    {'id': 204, 'name': 'West Lancashire', 'borough': 'west_lancashire'},
    {'id': 206, 'name': 'Wyre', 'borough': 'wyre'},
    {'id': 153, 'name': 'Blackburn with Darwen', 'borough': 'blackburn'},
    {'id': 154, 'name': 'Blackpool', 'borough': 'blackpool'},
    {'id': 189, 'name': 'Chorley', 'borough': 'chorley'},
    {'id': 197, 'name': 'Fylde', 'borough': 'fylde'},
]

def fetch_establishments(authority_id, page=1):
    """Fetch food hygiene ratings for an authority."""
    url = f'{FSA_API}/Establishments?localAuthorityId={authority_id}&pageNumber={page}&pageSize=100'
    try:
        req = urllib.request.Request(url, headers={
            'x-api-version': '2',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f'FSA API error: {e}')
        return None

def rating_to_stars(rating):
    """Convert FSA rating to stars."""
    try:
        return int(rating)
    except:
        return None

def get_rating_text(rating):
    """Get description for rating."""
    descriptions = {
        5: 'Very Good',
        4: 'Good', 
        3: 'Generally Satisfactory',
        2: 'Improvement Necessary',
        1: 'Major Improvement Necessary',
        0: 'Urgent Improvement Necessary',
        -1: 'Exempt',
        'AwaitingInspection': 'Awaiting Inspection',
        'AwaitingPublication': 'Awaiting Publication'
    }
    return descriptions.get(rating, f'Rating {rating}')

def insert_food_article(conn, article):
    """Insert food hygiene article."""
    borough_flags = {f'is_{c}': article.get(f'is_{c}', 0) for c in 
                    ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                     'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                     'west_lancashire', 'wyre', 'fylde']}
    
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
        article['source_type'], article['published'], article['summary'], article.get('ai_rewrite'),
        article['category'], article['content_tier'], article['interest_score'], article['trending_score'],
        article.get('author'), search_text,
        borough_flags['is_burnley'], borough_flags['is_hyndburn'], borough_flags['is_pendle'], 
        borough_flags['is_rossendale'], borough_flags['is_ribble_valley'], borough_flags['is_blackburn'], 
        borough_flags['is_chorley'], borough_flags['is_south_ribble'], borough_flags['is_preston'], 
        borough_flags['is_west_lancashire'], borough_flags['is_lancaster'], borough_flags['is_wyre'],
        borough_flags['is_fylde'], borough_flags['is_blackpool']
    ))
    conn.commit()

def process_authority(auth, conn):
    """Process a single local authority."""
    print(f'Checking {auth["name"]}...')
    
    data = fetch_establishments(auth['id'])
    if not data or 'establishments' not in data:
        return 0
    
    new_count = 0
    
    # Check first 50 establishments for poor ratings
    for est in data['establishments'][:50]:
        rating_val = est.get('RatingValue')
        rating = rating_to_stars(rating_val)
        
        # Only alert on 0-2 ratings (poor hygiene)
        if rating is None or rating > 2:
            continue
        
        fhrs_id = est.get('FHRSID')
        business_name = est.get('BusinessName', 'Unknown')
        address = est.get('AddressLine1', '')
        post_code = est.get('PostCode', '')
        
        # Skip if no ID
        if not fhrs_id:
            continue
        
        article_id = hashlib.md5(f'fsa-{fhrs_id}'.encode()).hexdigest()
        
        # Check if already exists
        c = conn.execute('SELECT 1 FROM articles WHERE id = ?', (article_id,))
        if c.fetchone():
            continue
        
        rating_text = get_rating_text(rating)
        
        urgency = 'URGENT' if rating <= 1 else 'WARNING'
        title = f"{urgency}: {business_name} in {auth['name']} rated {rating}/5 for food hygiene"
        
        summary = f"{business_name} at {address} {post_code} received a food hygiene rating of {rating} out of 5 ({rating_text}) following an inspection by {auth['name']} Council environmental health officers. Establishments rated 0-2 require improvement. Check the Food Standards Agency website for full inspection details."
        
        article = {
            'id': article_id,
            'title': title,
            'link': f'https://ratings.food.gov.uk/enhanced-search/en-GB/{fhrs_id}',
            'source': 'Food Standards Agency',
            'source_type': 'regulatory',
            'published': datetime.now().isoformat(),
            'summary': summary,
            'ai_rewrite': summary,
            'category': 'health',
            'interest_score': 80 if rating <= 1 else 65,
            'trending_score': 75,
            'content_tier': 'regulatory_alert',
            'author': 'FSA Inspection Data',
            f"is_{auth['borough']}": 1
        }
        
        # Set other boroughs to 0
        for other_auth in LANCASHIRE_AUTHORITIES:
            if other_auth['borough'] != auth['borough']:
                article[f"is_{other_auth['borough']}"] = 0
        
        try:
            insert_food_article(conn, article)
            new_count += 1
            print(f'  ALERT: {business_name} rated {rating}/5')
        except Exception as e:
            print(f'  Error: {e}')
    
    return new_count

def main():
    print('=== Food Hygiene Crawler ===')
    print(f'Monitoring {len(LANCASHIRE_AUTHORITIES)} Lancashire authorities')
    
    conn = get_db()
    total_new = 0
    
    # Limit to 5 authorities per run to avoid rate limits
    for auth in LANCASHIRE_AUTHORITIES[:5]:
        try:
            total_new += process_authority(auth, conn)
            time.sleep(1)  # Rate limit
        except Exception as e:
            print(f'Error with {auth["name"]}: {e}')
    
    print(f'\nTotal new food hygiene alerts: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
