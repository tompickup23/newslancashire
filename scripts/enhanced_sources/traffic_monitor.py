#!/usr/bin/env python3
"""
Traffic & Roadworks Monitor for Lancashire
Monitors Traffic England API and roadworks.org for disruptions
"""
import sqlite3
import hashlib
import json
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

# Lancashire major roads to monitor
LANCASHIRE_ROADS = ['M6', 'M65', 'M55', 'A56', 'A59', 'A6', 'A583', 'A677']

def fetch_traffic_england_incidents():
    """Fetch current incidents from Traffic England."""
    # Traffic England API - incidents endpoint
    url = 'https://api.trafficengland.com/api/incidents'
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f'Traffic England API error: {e}')
        return []

def filter_lancashire_incidents(incidents):
    """Filter incidents to Lancashire roads."""
    lancs_incidents = []
    
    for incident in incidents:
        road = incident.get('road', '')
        if any(r in road.upper() for r in LANCASHIRE_ROADS):
            lancs_incidents.append(incident)
    
    return lancs_incidents

def categorize_incident(incident):
    """Determine severity and interest."""
    severity = incident.get('severity', 'Unknown')
    
    severity_scores = {
        'Severe': 90,
        'High': 75,
        'Medium': 55,
        'Low': 35
    }
    
    return severity_scores.get(severity, 50)

def insert_traffic_article(conn, article):
    """Insert traffic alert."""
    # Detect affected borough from description
    text_lower = f"{article['title']} {article['summary']}".lower()
    
    borough_flags = {}
    for b in ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
              'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
              'west_lancashire', 'wyre', 'fylde']:
        borough_flags[f'is_{b}'] = 1 if b.replace('_', ' ') in text_lower else 0
    
    # Default to all if no specific borough detected
    if not any(borough_flags.values()):
        borough_flags = {f'is_{b}': 1 for b in borough_flags.keys()}
    
    search_text = text_lower
    
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
    print('=== Traffic Monitor ===')
    
    incidents = fetch_traffic_england_incidents()
    if not incidents:
        print('No traffic data available')
        return
    
    lancs_incidents = filter_lancashire_incidents(incidents)
    print(f'Found {len(lancs_incidents)} Lancashire incidents')
    
    if not lancs_incidents:
        return
    
    conn = get_db()
    total_new = 0
    
    for incident in lancs_incidents[:10]:  # Limit to 10 most severe
        interest = categorize_incident(incident)
        
        # Only alert on medium+ severity
        if interest < 55:
            continue
        
        road = incident.get('road', 'Unknown road')
        incident_type = incident.get('type', 'Incident')
        description = incident.get('description', 'No details')
        
        article_id = hashlib.md5(f"traffic-{incident.get('id', road)}".encode()).hexdigest()
        
        severity_label = 'SEVERE' if interest >= 75 else 'Traffic'
        title = f"{severity_label}: {incident_type} on {road}"
        
        summary = f"{incident_type} causing delays on {road}. {description}. Check Traffic England for current status and alternative routes."
        
        article = {
            'id': article_id,
            'title': title,
            'link': 'https://trafficengland.com/',
            'source': 'Traffic England',
            'source_type': 'traffic_alert',
            'published': datetime.now().isoformat(),
            'summary': summary,
            'ai_rewrite': summary,
            'category': 'transport',
            'interest_score': interest,
            'trending_score': 80 if interest >= 75 else 60,
            'content_tier': 'alert',
            'author': 'Traffic Monitor'
        }
        
        try:
            insert_traffic_article(conn, article)
            total_new += 1
            print(f'  Alert: {title[:60]}...')
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f'  Error: {e}')
    
    print(f'\nTotal new traffic alerts: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
