#!/usr/bin/env python3
"""
Idox Public Access Planning Scraper
Many Lancashire councils use Idox for planning applications
"""
import sqlite3
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

# Lancashire councils using Idox Public Access
IDOX_COUNCILS = [
    {
        'name': 'Burnley',
        'borough': 'burnley',
        'base_url': 'https://publicaccess.burnley.gov.uk/online-applications',
        'search_url': '/advancedSearchResults.do?action=firstPage&searchType=Application'
    },
    {
        'name': 'Hyndburn',
        'borough': 'hyndburn', 
        'base_url': 'https://planning.hyndburnbc.gov.uk/Planning/AdvancedSearch',
        'search_url': ''
    },
    {
        'name': 'Pendle',
        'borough': 'pendle',
        'base_url': 'https://www.planning.pendle.gov.uk/online-applications',
        'search_url': '/advancedSearchResults.do?action=firstPage'
    }
]

def fetch_recent_applications(council):
    """Fetch recent planning applications."""
    url = council['base_url'] + council.get('search_url', '/advancedSearchResults.do?action=firstPage')
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {council['name']}: {e}")
        return None

def parse_applications_simple(html, council_name):
    """Simple parsing for Idox HTML - extracts basic application data."""
    import re
    applications = []
    
    # Look for application references and descriptions
    # Idox typically has tables with class 'searchresults'
    
    # Pattern for reference numbers (YYYY/NNNN format)
    ref_pattern = r'(\d{4}/\d{3,4})'
    refs = re.findall(ref_pattern, html)
    
    # Pattern for addresses/locations
    addr_pattern = r'>([^<]{10,100})<[^>]*>\s*(?:\d{4}/\d{3,4})'
    addresses = re.findall(addr_pattern, html)
    
    # Combine refs with descriptions
    for i, ref in enumerate(refs[:15]):  # Limit to 15 recent
        addr = addresses[i] if i < len(addresses) else 'Unknown location'
        applications.append({
            'reference': ref,
            'address': addr.strip(),
            'description': f'Planning application at {addr.strip()}'
        })
    
    return applications

def categorize_by_description(description):
    """Determine interest level based on description."""
    desc_lower = description.lower()
    
    # High interest (major developments)
    if any(x in desc_lower for x in ['10 dwelling', '20 dwelling', '50 dwelling', '100 dwelling',
                                      'housing development', 'residential development', 
                                      'new estate', 'industrial', 'solar farm']):
        return 85
    
    # Medium interest (smaller housing)
    if any(x in desc_lower for x in ['new dwelling', 'new house', 'bungalow', 'conversion']):
        return 70
    
    # Standard interest (extensions, alterations)
    if any(x in desc_lower for x in ['extension', 'conservatory', 'loft']):
        return 55
    
    # Low interest (minor works)
    return 35

def insert_planning_article(conn, article, borough):
    """Insert planning application."""
    borough_flags = {f'is_{c}': 1 if c == borough else 0 for c in 
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
    print('=== Idox Planning Scraper ===')
    conn = get_db()
    total_new = 0
    
    for council in IDOX_COUNCILS:
        print(f"\nChecking {council['name']}...")
        
        html = fetch_recent_applications(council)
        if not html:
            continue
        
        applications = parse_applications_simple(html, council['name'])
        print(f'  Found {len(applications)} applications')
        
        for app in applications:
            interest = categorize_by_description(app['description'])
            
            # Only alert on medium-high interest applications
            if interest < 55:
                continue
            
            article_id = hashlib.md5(f"planning-{council['borough']}-{app['reference']}".encode()).hexdigest()
            
            urgency = 'MAJOR' if interest >= 80 else 'Planning'
            title = f"{urgency}: {app['description'][:70]}... ({app['reference']})"
            
            summary = f"A planning application has been submitted to {council['name']} Borough Council: {app['description']} at {app['address']}. Reference: {app['reference']}."
            
            article = {
                'id': article_id,
                'title': title,
                'link': f"{council['base_url']}/applicationDetails.do?activeTab=summary&keyVal={app['reference']}",
                'source': f"{council['name']} Council Planning",
                'source_type': 'planning',
                'published': datetime.now().isoformat(),
                'summary': summary,
                'ai_rewrite': summary,
                'category': 'politics',
                'interest_score': interest,
                'trending_score': 50,
                'content_tier': 'planning_alert',
                'author': 'Planning Monitor'
            }
            
            try:
                insert_planning_article(conn, article, council['borough'])
                total_new += 1
                print(f"    Added: {app['reference']}")
            except sqlite3.IntegrityError:
                pass
            except Exception as e:
                print(f'    Error: {e}')
    
    print(f'\nTotal new planning alerts: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
