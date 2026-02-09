#!/usr/bin/env python3
"""News Lancashire RSS Crawler v2
Fetches RSS feeds, detects 14 borough locations, exports Burnley JSON."""

import feedparser
import sqlite3
import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta
import time
import logging

DB_PATH = '/home/ubuntu/newslancashire/db/news.db'
LOG_DIR = '/home/ubuntu/newslancashire/logs'
BURNLEY_EXPORT = '/home/ubuntu/newslancashire/export/burnley-news.json'
OCTAVIANUS_IP = '51.20.51.127'
RATE_LIMIT = 2

FEEDS = [
    ('http://feeds.bbci.co.uk/news/england/lancashire/rss.xml', 'BBC Lancashire'),
    ('https://www.lancashiretelegraph.co.uk/rss/', 'Lancashire Telegraph'),
    ('https://www.burnleyexpress.net/rss/', 'Burnley Express'),
    ('https://www.blackpoolgazette.co.uk/rss/', 'Blackpool Gazette'),
    ('https://www.lancasterguardian.co.uk/rss/', 'Lancaster Guardian'),
    ('https://www.lep.co.uk/rss/', 'LEP Preston'),
]

BOROUGHS = {
    'burnley': ['burnley', 'padiham', 'brierfield', 'hapton', 'worsthorne'],
    'pendle': ['pendle', 'nelson', 'colne', 'barnoldswick', 'barrowford', 'earby', 'trawden'],
    'rossendale': ['rossendale', 'rawtenstall', 'bacup', 'haslingden', 'whitworth', 'helmshore'],
    'hyndburn': ['hyndburn', 'accrington', 'oswaldtwistle', 'great harwood', 'rishton', 'clayton-le-moors'],
    'ribble_valley': ['ribble valley', 'clitheroe', 'longridge', 'whalley', 'read', 'sabden'],
    'blackburn': ['blackburn', 'darwen', 'blackburn with darwen'],
    'chorley': ['chorley', 'adlington', 'euxton', 'coppull', 'whittle-le-woods'],
    'south_ribble': ['south ribble', 'leyland', 'penwortham', 'bamber bridge', 'lostock hall'],
    'preston': ['preston', 'fulwood', 'ashton-on-ribble', 'ribbleton'],
    'west_lancashire': ['west lancashire', 'ormskirk', 'skelmersdale', 'burscough', 'tarleton'],
    'lancaster': ['lancaster', 'morecambe', 'heysham', 'carnforth', 'silverdale'],
    'wyre': ['wyre', 'fleetwood', 'thornton-cleveleys', 'garstang', 'poulton-le-fylde'],
    'fylde': ['fylde', 'lytham', 'st annes', 'kirkham', 'freckleton', 'warton'],
    'blackpool': ['blackpool', 'bispham', 'south shore', 'north shore'],
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/crawler.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('crawler')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        source TEXT NOT NULL,
        published TEXT,
        summary TEXT,
        is_processed INTEGER DEFAULT 0,
        is_burnley INTEGER DEFAULT 0,
        is_blackpool INTEGER DEFAULT 0,
        is_preston INTEGER DEFAULT 0,
        is_lancaster INTEGER DEFAULT 0,
        is_pendle INTEGER DEFAULT 0,
        is_rossendale INTEGER DEFAULT 0,
        is_hyndburn INTEGER DEFAULT 0,
        is_ribble_valley INTEGER DEFAULT 0,
        is_blackburn INTEGER DEFAULT 0,
        is_chorley INTEGER DEFAULT 0,
        is_south_ribble INTEGER DEFAULT 0,
        is_west_lancashire INTEGER DEFAULT 0,
        is_wyre INTEGER DEFAULT 0,
        is_fylde INTEGER DEFAULT 0,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute('CREATE INDEX IF NOT EXISTS idx_link ON articles(link)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fetched ON articles(fetched_at)')
    conn.commit()
    return conn


def detect_boroughs(title, summary):
    text = (title + ' ' + summary).lower()
    result = {}
    for borough, keywords in BOROUGHS.items():
        result['is_' + borough] = 1 if any(kw in text for kw in keywords) else 0
    return result


def fetch_feed(url, name):
    try:
        log.info('Fetching: %s', name)
        feed = feedparser.parse(url)
        entries = []
        for e in feed.entries[:15]:
            entries.append({
                'title': e.get('title', ''),
                'link': e.get('link', ''),
                'summary': e.get('summary', '')[:800],
                'published': e.get('published', datetime.now().isoformat()),
            })
        return entries
    except Exception as ex:
        log.error('Error fetching %s: %s', name, ex)
        return []


def export_burnley_json(conn):
    """Export latest Burnley articles as JSON for newsburnley.co.uk"""
    os.makedirs(os.path.dirname(BURNLEY_EXPORT), exist_ok=True)
    c = conn.cursor()
    c.execute("""
        SELECT title, link, source, published, summary
        FROM articles WHERE is_burnley = 1
        ORDER BY fetched_at DESC LIMIT 50
    """)
    articles = []
    for r in c.fetchall():
        articles.append({
            'title': r[0], 'link': r[1], 'source': r[2],
            'published': r[3], 'summary': r[4]
        })
    with open(BURNLEY_EXPORT, 'w') as f:
        json.dump(articles, f, indent=2)
    log.info('Exported %d Burnley articles to JSON', len(articles))
    return articles


def sync_to_octavianus():
    """SCP the Burnley JSON to Octavianus"""
    try:
        key = '/home/ubuntu/.ssh/octavianus_key'
        if not os.path.exists(key):
            log.warning('No Octavianus SSH key - skipping sync')
            return
        cmd = (
            'scp -i ' + key + ' -o StrictHostKeyChecking=no '
            + BURNLEY_EXPORT + ' ubuntu@' + OCTAVIANUS_IP
            + ':/home/ubuntu/newsburnley/public/burnley-news.json'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log.info('Synced Burnley JSON to Octavianus')
        else:
            log.warning('Sync failed: %s', result.stderr)
    except Exception as ex:
        log.warning('Sync error: %s', ex)


def run():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    log.info('=== Crawler started: %s ===', now)
    conn = init_db()
    c = conn.cursor()
    total_new = 0

    for url, name in FEEDS:
        entries = fetch_feed(url, name)
        new_count = 0
        for entry in entries:
            article_id = hashlib.md5(entry['link'].encode()).hexdigest()
            c.execute('SELECT 1 FROM articles WHERE link = ? LIMIT 1', (entry['link'],))
            if c.fetchone():
                continue
            boroughs = detect_boroughs(entry['title'], entry['summary'])
            c.execute(
                'INSERT OR IGNORE INTO articles (id, title, link, source, published, summary, '
                'is_burnley, is_blackpool, is_preston, is_lancaster, is_pendle, is_rossendale, '
                'is_hyndburn, is_ribble_valley, is_blackburn, is_chorley, is_south_ribble, '
                'is_west_lancashire, is_wyre, is_fylde) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (article_id, entry['title'], entry['link'], name,
                 entry['published'], entry['summary'],
                 boroughs['is_burnley'], boroughs['is_blackpool'],
                 boroughs['is_preston'], boroughs['is_lancaster'],
                 boroughs['is_pendle'], boroughs['is_rossendale'],
                 boroughs['is_hyndburn'], boroughs['is_ribble_valley'],
                 boroughs['is_blackburn'], boroughs['is_chorley'],
                 boroughs['is_south_ribble'], boroughs['is_west_lancashire'],
                 boroughs['is_wyre'], boroughs['is_fylde']))
            new_count += 1
        conn.commit()
        total_new += new_count
        log.info('%s: %d new', name, new_count)
        time.sleep(RATE_LIMIT)

    # Cleanup old articles (30 days)
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    c.execute('DELETE FROM articles WHERE fetched_at < ?', (cutoff,))
    conn.commit()

    # Export and sync Burnley content
    export_burnley_json(conn)
    sync_to_octavianus()

    c.execute('SELECT COUNT(*) FROM articles')
    total = c.fetchone()[0]
    log.info('=== Done: %d new | %d total ===', total_new, total)
    conn.close()


if __name__ == '__main__':
    run()
