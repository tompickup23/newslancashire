#!/usr/bin/env python3
"""
Unconventional Sources Crawler
Food hygiene, Companies House, traffic, weather, infrastructure
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
from crawler_v3 import get_db, insert_article

# === FOOD HYGIENE RATINGS (FSA API) ===
FSA_API = 'http://api.ratings.food.gov.uk'

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
    {'id': 153, 'name': 'Blackburn', 'borough': 'blackburn'},
    {'id': 154, 'name': 'Blackpool', 'borough': 'blackpool'},
]

def fetch_fsa_establishments(authority_id, page=1):
    """Fetch food hygiene ratings for an authority."""
    url = f'{FSA_API}/Establishments?localAuthorityId={authority_id}&pageNumber={page}&pageSize=100'
    try:
        req = urllib.request.Request(url, headers={'x-api-version': '2'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f'FSA error: {e}')
        return None

def process_food_hygiene(conn):
    """Process food hygiene ratings - flag new 0-2 ratings."""
    new_articles = []
    
    for auth in LANCASHIRE_AUTHORITIES[:3]:  # Limit for testing
        print(f'Checking food hygiene for {auth["name"]}...')
        data = fetch_fsa_establishments(auth['id'])
        if not data or 'establishments' not in data:
            continue
        
        for est in data['establishments'][:20]:  # Check recent 20
            rating = est.get('RatingValue', 'N/A')
            if rating in ['0', '1', '2']:  # Poor hygiene
                name = est.get('BusinessName', 'Unknown')
                address = est.get('AddressLine1', '')
                
                title = f"URGENT: {name} in {auth['name']} rated {rating}/5 for food hygiene"
                summary = f"{name} at {address} received a food hygiene rating of {rating} out of 5 following an inspection by {auth['name']} Borough Council. Establishments rated 0-2 require urgent improvement."
                
                article_id = hashlib.md5(f"fsa-{est.get('FHRSID', '0')}".encode()).hexdigest()
                
                article = {
                    'id': article_id,
                    'title': title,
                    'link': f"https://ratings.food.gov.uk/enhanced-search/en-GB/{est.get('FHRSID', '')}",
                    'source': 'Food Standards Agency',
                    'source_type': 'regulatory',
                    'published': datetime.now().isoformat(),
                    'summary': summary,
                    'ai_rewrite': summary,
                    'category': 'health',
                    'interest_score': 65,
                    'trending_score': 70,
                    'content_tier': 'regulatory_alert',
                    f"is_{auth['borough']}": 1,
                }
                
                try:
                    insert_article(conn, article)
                    new_articles.append(article)
                    print(f'  Alert: {name} rated {rating}/5')
                except sqlite3.IntegrityError:
                    pass
        
        time.sleep(1)
    
    return new_articles

# === TRAFFIC ENGLAND API ===
def fetch_traffic_incidents():
    """Fetch traffic incidents on M65, A56, M6 around Lancashire."""
    # Traffic England API - incidents within Lancashire bounding box
    bbox = '-2.9,53.7,-2.0,54.3'  # Rough Lancashire area
    url = f'https://api.trafficengland.com/api/incidents?bbox={bbox}'
    
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f'Traffic API error: {e}')
        return []

def process_traffic(conn):
    """Process traffic incidents."""
    incidents = fetch_traffic_incidents()
    new_articles = []
    
    for incident in incidents:
        road = incident.get('road', '')
        if not any(r in road.upper() for r in ['M65', 'M6', 'A56', 'A59', 'A6', 'A583']):
            continue
        
        title = f"Traffic Alert: {incident.get('eventType', 'Incident')} on {road}"
        summary = f"{incident.get('eventType', 'Incident')}: {incident.get('description', 'No details')} on {road}. "                   f"Severity: {incident.get('severity', 'Unknown')}. Check before travelling."
        
        article_id = hashlib.md5(f"traffic-{incident.get('id', '0')}".encode()).hexdigest()
        
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
            'interest_score': 55,
            'trending_score': 80 if incident.get('severity') == 'High' else 60,
            'content_tier': 'alert',
        }
        
        # Try to detect borough from coordinates
        # (simplified - would need proper geo lookup)
        
        try:
            insert_article(conn, article)
            new_articles.append(article)
            print(f'  Traffic: {title[:60]}...')
        except sqlite3.IntegrityError:
            pass
    
    return new_articles

# === MET OFFICE ALERTS ===
def fetch_weather_warnings():
    """Fetch Met Office weather warnings for North West England."""
    # Met Office DataPoint API (requires key)
    # For now, use RSS feed
    url = 'https://www.metoffice.gov.uk/public/data/CoreProductCache.json'
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except:
        return None

# === COMPANIES HOUSE STREAMING ===
CH_API = 'https://api.company-information.service.gov.uk'

def fetch_new_companies(postcode_prefix='BB'):
    """Fetch recently incorporated companies in Lancashire area."""
    # This requires API key - placeholder for now
    return []

def main():
    print('=== Unconventional Sources Crawler ===')
    
    conn = get_db()
    total_new = 0
    
    # Food hygiene alerts
    print('\nChecking food hygiene ratings...')
    total_new += len(process_food_hygiene(conn))
    
    # Traffic incidents
    print('\nChecking traffic incidents...')
    total_new += len(process_traffic(conn))
    
    print(f'\nTotal new unconventional articles: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
