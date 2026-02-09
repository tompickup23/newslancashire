#!/usr/bin/env python3
"""
Burnley Council Planning Application Scraper
Extracts new planning applications from weekly lists
"""
import sqlite3
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

# Burnley Council planning portal
BURNLEY_PLANNING_URL = 'https://www.burnley.gov.uk/planning/planning-application-search'

def fetch_planning_page():
    """Fetch the planning applications page."""
    try:
        req = urllib.request.Request(BURNLEY_PLANNING_URL, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f'Error fetching planning page: {e}')
        return None

def extract_applications(html):
    """Extract planning applications from HTML."""
    applications = []
    
    # Look for application references (format: 2025/0001)
    app_pattern = r'(\d{4}/\d{3,4})\s*-\s*([^<]+)'
    matches = re.findall(app_pattern, html)
    
    for match in matches[:20]:  # Limit to 20
        ref, description = match
        applications.append({
            'reference': ref.strip(),
            'description': description.strip()[:200]
        })
    
    return applications

def categorize_application(description):
    """Categorize application type."""
    desc_lower = description.lower()
    
    if any(word in desc_lower for word in ['house', 'bungalow', 'flat', 'dwelling']):
        if 'new' in desc_lower:
            return 'new_housing', 75
        else:
            return 'housing_alteration', 50
    
    if any(word in desc_lower for word in ['extension', 'conservatory', 'loft']):
        return 'extension', 40
    
    if any(word in desc_lower for word in ['shop', 'retail', 'commercial', 'office']):
        return 'commercial', 60
    
    if any(word in desc_lower for word in ['solar', 'panels', 'renewable']):
        return 'renewable_energy', 55
    
    if any(word in desc_lower for word in ['demolition', 'change of use']):
        return 'major_change', 70
    
    return 'other', 35

def insert_planning_article(conn, article):
    """Insert planning application as article."""
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
        1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  # is_burnley=1, others=0
    ))
    conn.commit()

def main():
    print('=== Burnley Planning Scraper ===')
    
    html = fetch_planning_page()
    if not html:
        print('Failed to fetch planning page')
        return
    
    applications = extract_applications(html)
    print(f'Found {len(applications)} applications')
    
    if not applications:
        return
    
    conn = get_db()
    total_new = 0
    
    for app in applications:
        app_type, interest = categorize_application(app['description'])
        
        # Skip low-interest applications (minor alterations)
        if interest < 50:
            continue
        
        article_id = hashlib.md5(f"burnley-planning-{app['reference']}".encode()).hexdigest()
        
        title = f"Planning: {app['description'][:80]}... (Ref: {app['reference']})"
        summary = f"A planning application has been submitted to Burnley Borough Council: {app['description']}. Reference number: {app['reference']}. View full details on the council planning portal."
        
        article = {
            'id': article_id,
            'title': title,
            'link': f"https://www.burnley.gov.uk/planning/planning-application-search?search={app['reference']}",
            'source': 'Burnley Council Planning Portal',
            'source_type': 'planning',
            'published': datetime.now().isoformat(),
            'summary': summary,
            'ai_rewrite': summary,
            'category': 'politics',
            'interest_score': interest,
            'trending_score': 45,
            'content_tier': 'planning_alert',
            'author': 'Planning Monitor'
        }
        
        try:
            insert_planning_article(conn, article)
            total_new += 1
            print(f'  Added: {app["reference"]} - {app["description"][:50]}...')
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f'  Error: {e}')
    
    print(f'\nTotal new planning applications: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
