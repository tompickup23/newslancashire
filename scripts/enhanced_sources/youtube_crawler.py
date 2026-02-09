#!/usr/bin/env python3
"""
YouTube Channel Monitor for Lancashire Creators
Fetches videos via RSS, extracts transcripts via Whisper
"""
import sqlite3
import hashlib
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/newslancashire/scripts')
from crawler_v3 import get_db

BASE = '/home/ubuntu/newslancashire'
YOUTUBE_RSS = 'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'

# Lancashire-focused YouTube channels
CHANNELS = [
    {
        'id': 'UCMjh0agT34-9tXg3CbdXhHg',
        'name': 'June Slater UK Politics Uncovered',
        'category': 'commentary',
        'priority': 'high',
        'description': 'Lancashire political commentary, Reform UK, council waste exposés'
    },
    {
        'id': 'UCylFidWvepBWj6HBu1slk3A',
        'name': 'Tom Pickup Burnley',
        'category': 'politics',
        'priority': 'high',
        'description': 'County Councillor Tom Pickup - Lancashire County Council - Reform UK'
    },
    {
        'id': 'UCk7F7MER7Q-gcNV7UKkRusg',
        'name': 'Reform UK Lancashire',
        'category': 'politics',
        'priority': 'high',
        'description': 'Official Reform UK Lancashire channel - local news and campaigning'
    },
    {
        'id': 'UCxQZIoS2Y_o1JOiKMvGPTeg',
        'name': 'Lancs Vlogger',
        'category': 'vlog',
        'priority': 'medium',
        'description': 'Lancashire vlogger - local life and community'
    },
    {
        'id': 'UCQznv0M5U1s9_CnxMfY9V7A',
        'name': 'Lancashire Transport Vlogs',
        'category': 'transport',
        'priority': 'medium',
        'description': 'Bus and transport enthusiast in Lancashire - Transdev and local services'
    },
]

def fetch_channel_feed(channel_id):
    """Fetch RSS feed for a YouTube channel."""
    url = YOUTUBE_RSS.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f'Error fetching {channel_id}: {e}')
        return None

def parse_entry(entry):
    """Parse a single RSS entry."""
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}
    
    video_id = entry.find('atom:id', ns).text.split(':')[-1] if entry.find('atom:id', ns) else None
    title = entry.find('atom:title', ns).text if entry.find('atom:title', ns) else ''
    published = entry.find('atom:published', ns).text if entry.find('atom:published', ns) else ''
    
    description = ''
    media_desc = entry.find('media:group/media:description', ns)
    if media_desc is not None and media_desc.text:
        description = media_desc.text
    
    thumbnail = ''
    thumb = entry.find('media:group/media:thumbnail', ns)
    if thumb is not None:
        thumbnail = thumb.get('url', '')
    
    return {
        'video_id': video_id,
        'title': title,
        'description': description[:500],
        'published': published,
        'thumbnail': thumbnail,
        'url': f'https://youtube.com/watch?v={video_id}'
    }

def insert_youtube_article(conn, article):
    """Insert YouTube video as article."""
    borough_flags = {f'is_{c}': 0 for c in 
                    ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
                     'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
                     'west_lancashire', 'wyre', 'fylde']}
    
    # Detect Lancashire boroughs from text
    text_lower = f"{article['title']} {article['summary']}".lower()
    for b in ['burnley', 'hyndburn', 'pendle', 'blackpool', 'preston', 'lancaster', 
              'rossendale', 'ribble_valley', 'blackburn', 'chorley', 'south_ribble',
              'west_lancashire', 'wyre', 'fylde']:
        if b.replace('_', ' ') in text_lower or b in text_lower:
            borough_flags[f'is_{b}'] = 1
    
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

def process_channel(channel, conn):
    """Process a single channel."""
    print(f'Processing {channel["name"]}...')
    
    feed_xml = fetch_channel_feed(channel['id'])
    if not feed_xml:
        return 0
    
    root = ET.fromstring(feed_xml)
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}
    entries = root.findall('atom:entry', ns)
    
    new_count = 0
    for entry in entries[:10]:  # Last 10 videos
        video = parse_entry(entry)
        if not video['video_id']:
            continue
        
        article_id = hashlib.md5(f'yt-{video["video_id"]}'.encode()).hexdigest()
        
        # Check if exists
        c = conn.execute('SELECT 1 FROM articles WHERE id = ?', (article_id,))
        if c.fetchone():
            continue
        
        # Calculate interest score based on channel priority
        base_interest = 70 if channel.get('priority') == 'high' else 50
        if any(kw in video['title'].lower() for kw in ['lancashire', 'reform', 'council', 'burnley']):
            base_interest += 15
        
        article = {
            'id': article_id,
            'title': video['title'],
            'link': video['url'],
            'source': f"{channel['name']} (YouTube)",
            'source_type': 'youtube',
            'published': video['published'],
            'summary': video['description'][:280],
            'ai_rewrite': None,  # Will be processed by ai_rewriter.py
            'category': 'politics' if 'politics' in channel.get('category', '') else 'general',
            'interest_score': min(100, base_interest),
            'trending_score': 60,
            'content_tier': 'commentary',
            'author': channel['name']
        }
        
        try:
            insert_youtube_article(conn, article)
            new_count += 1
            print(f'  Added: {video["title"][:60]}...')
        except Exception as e:
            print(f'  Error: {e}')
        
        time.sleep(0.5)
    
    return new_count

def main():
    print('=== YouTube Crawler ===')
    print(f'Monitoring {len(CHANNELS)} channel(s)')
    
    if not CHANNELS:
        print('No channels configured.')
        return
    
    conn = get_db()
    total_new = 0
    
    for channel in CHANNELS:
        try:
            total_new += process_channel(channel, conn)
            time.sleep(2)  # Rate limit between channels
        except Exception as e:
            print(f'Error with {channel["name"]}: {e}')
    
    print(f'\nTotal new videos: {total_new}')
    conn.close()

if __name__ == '__main__':
    main()
