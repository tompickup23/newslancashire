#!/usr/bin/env python3
"""
Burnley Council Meeting Minutes Scraper
Monitors council meeting agendas and minutes for key decisions
"""
import sqlite3
import hashlib
import re
import sys
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

# Burnley Council meetings page
BURNLEY_MEETINGS_URL = 'https://burnleycouncil.co.uk/council-meetings/'

# Keywords that indicate important decisions
IMPORTANT_KEYWORDS = [
    'budget', 'spending', 'cuts', 'closure', 'sell', 'privatisation',
    'planning permission', 'granted', 'refused', 'appeal',
    'appointment', 'chief executive', 'director', 'salary',
    'consultation', 'review', 'restructure', 'redundancy',
    'contract', 'procurement', 'tender', 'award',
    'increase', 'decrease', 'council tax', 'fees', 'charges',
    'development', 'housing', 'school', 'care home', 'library'
]

def fetch_meetings_page():
    """Fetch council meetings page."""
    try:
        req = urllib.request.Request(BURNLEY_MEETINGS_URL, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f'Error fetching meetings page: {e}')
        return None

def extract_meeting_info(html):
    """Extract meeting info from HTML."""
    meetings = []
    
    # Look for meeting titles and dates
    # Pattern: meeting name + date
    meeting_pattern = r'(Cabinet|Council|Planning Committee|Audit Committee)[^<]*?(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})'
    
    matches = re.findall(meeting_pattern, html, re.IGNORECASE)
    
    for match in matches[:10]:
        meeting_type = match[0]
        date_str = match[1]
        
        meetings.append({
            'type': meeting_type,
            'date': date_str,
            'description': f'{meeting_type} meeting scheduled for {date_str}'
        })
    
    return meetings

def score_importance(text):
    """Score how important a meeting item is."""
    text_lower = text.lower()
    score = 0
    
    for keyword in IMPORTANT_KEYWORDS:
        if keyword in text_lower:
            score += 10
    
    # Boost for financial decisions
    if any(x in text_lower for x in ['£', 'million', 'thousand', 'budget', 'cost']):
        score += 15
    
    # Boost for planning decisions
    if 'planning permission' in text_lower or 'application' in text_lower:
        score += 10
    
    return min(100, score)

def insert_minutes_article(conn, article):
    """Insert council minutes alert."""
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
        1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    ))
    conn.commit()

def main():
    print('=== Burnley Council Minutes Monitor ===')
    
    html = fetch_meetings_page()
    if not html:
        print('Failed to fetch meetings page')
        return
    
    meetings = extract_meeting_info(html)
    print(f'Found {len(meetings)} upcoming meetings')
    
    if not meetings:
        return
    
    conn = get_db()
    total_new = 0
    
    for meeting in meetings:
        # Score importance
        importance = score_importance(meeting['description'])
        
        # Only alert on significant meetings
        if importance < 30:
            continue
        
        article_id = hashlib.md5(f"burnley-meeting-{meeting['type']}-{meeting['date']}".encode()).hexdigest()
        
        title = f"Burnley {meeting['type']}: Meeting scheduled for {meeting['date']}"
        
        summary = f"{meeting['type']} meeting at Burnley Borough Council scheduled for {meeting['date']}. Agenda items may include planning decisions, budget matters, and policy changes. Full agenda available on the council website."
        
        article = {
            'id': article_id,
            'title': title,
            'link': BURNLEY_MEETINGS_URL,
            'source': 'Burnley Council Meetings',
            'source_type': 'council_minutes',
            'published': datetime.now().isoformat(),
            'summary': summary,
            'ai_rewrite': summary,
            'category': 'politics',
            'interest_score': importance,
            'trending_score': 40,
            'content_tier': 'council_alert',
            'author': 'Council Monitor'
        }
        
        try:
            insert_minutes_article(conn, article)
            total_new += 1
            print(f"  Added: {meeting['type']} - {meeting['date']}")
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f'  Error: {e}')
    
    print(f'\nTotal new meeting alerts: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
