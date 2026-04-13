#!/usr/bin/env python3
"""
facebook_crawler.py — Crawl public Facebook pages for Lancashire news.

Scrapes public Facebook pages (mobile site) for posts by Lancashire MPs,
councillors, councils, and local organisations. No API auth needed.

Posts are stored in the NL pipeline DB and fed through the normal
borough detection + interest scoring + editorial pipeline.

Usage:
    python3 facebook_crawler.py                 # Crawl all configured pages
    python3 facebook_crawler.py --dry-run       # Show what would be crawled
    python3 facebook_crawler.py --page burnley  # Crawl single page
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
DB_PATH = NL_PIPELINE_DIR / 'db' / 'news.db'
LOG_DIR = NL_PIPELINE_DIR / 'logs'
CONFIG_PATH = NL_PIPELINE_DIR / 'config' / 'feeds.json'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'facebook_crawler.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('fb_crawler')

# Borough keywords for detection
BOROUGH_KEYWORDS = {
    'burnley': ['burnley', 'padiham', 'brierfield'],
    'pendle': ['pendle', 'nelson', 'colne', 'barnoldswick'],
    'hyndburn': ['hyndburn', 'accrington', 'oswaldtwistle'],
    'rossendale': ['rossendale', 'rawtenstall', 'bacup'],
    'ribble_valley': ['ribble valley', 'clitheroe', 'longridge'],
    'blackburn': ['blackburn', 'darwen'],
    'blackpool': ['blackpool'],
    'chorley': ['chorley'],
    'south_ribble': ['south ribble', 'leyland', 'penwortham'],
    'preston': ['preston', 'fulwood'],
    'west_lancashire': ['west lancashire', 'ormskirk', 'skelmersdale'],
    'lancaster': ['lancaster', 'morecambe'],
    'wyre': ['wyre', 'fleetwood', 'garstang', 'poulton'],
    'fylde': ['fylde', 'lytham', 'st annes'],
}

# Interest scoring
HIGH_INTEREST = ['reform', 'election', 'council tax', 'budget', 'crime', 'police',
                 'planning', 'housing', 'nhs', 'hospital', 'school', 'closure']


def detect_borough(text, page_borough=''):
    if page_borough:
        return page_borough
    text_lower = text.lower()
    for borough, keywords in BOROUGH_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return borough
    return ''


def score_interest(text):
    score = 35
    text_lower = text.lower()
    for kw in HIGH_INTEREST:
        if kw in text_lower:
            score += 15
    return min(100, score)


def fetch_facebook_page(page_url, timeout=20):
    """Fetch public Facebook page posts via mobile site.
    Returns list of post dicts with text content."""
    posts = []

    # Use mbasic.facebook.com for simpler HTML
    # Extract page slug from any facebook URL format
    slug = page_url.rstrip('/').split('/')[-1]
    url = 'https://mbasic.facebook.com/' + slug

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/91.0',
            'Accept-Language': 'en-GB,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log.warning('Failed to fetch %s: %s', url, str(e)[:60])
        return posts

    # Extract post blocks from mbasic HTML
    # Posts are in <div> blocks with data-ft or specific class patterns
    # Simple regex extraction of visible text blocks
    post_blocks = re.findall(
        r'<div[^>]*class="[^"]*(?:userContent|story_body_container|_5rgt)[^"]*"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )

    if not post_blocks:
        # Fallback: try extracting from article tags
        post_blocks = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)

    if not post_blocks:
        # Last resort: extract paragraphs with substantial text
        post_blocks = re.findall(r'<p>(.*?)</p>', html, re.DOTALL)

    for block in post_blocks:
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', block)
        text = re.sub(r'\s+', ' ', text).strip()

        # Skip very short posts or navigation text
        if len(text) < 50:
            continue
        if any(skip in text.lower() for skip in ['log in', 'sign up', 'create account', 'forgot password']):
            continue

        posts.append({
            'text': text[:1000],
            'source_url': url,
        })

    return posts[:10]  # Max 10 posts per page


def crawl_all(conn, dry_run=False, page_filter=None):
    """Crawl all configured Facebook pages."""
    config = json.load(open(CONFIG_PATH))
    pages = config.get('facebook_pages', [])

    if page_filter:
        pages = [p for p in pages if page_filter.lower() in p.get('name', '').lower()]

    if not pages:
        log.info('No Facebook pages configured')
        return 0

    new_count = 0
    for page in pages:
        name = page.get('name', '?')
        url = page.get('url', '')
        borough = page.get('borough_focus', '')

        if not url:
            # Try constructing from name
            slug = name.lower().replace(' ', '').replace("'", '')
            url = 'https://www.facebook.com/' + slug

        log.info('Crawling: %s (%s)', name, url[:50])
        posts = fetch_facebook_page(url)

        for post in posts:
            text = post['text']
            title = text[:120]
            if len(text) > 120:
                title = text[:117].rsplit(' ', 1)[0] + '...'

            aid = hashlib.md5((url + title).encode()).hexdigest()
            existing = conn.execute('SELECT 1 FROM articles WHERE id = ?', (aid,)).fetchone()
            if existing:
                continue

            detected_borough = detect_borough(text, borough)
            score = score_interest(text)

            if dry_run:
                log.info('  [%d] %s: %s', score, detected_borough or 'lancs', title[:70])
                new_count += 1
                continue

            # Insert
            borough_cols = ''
            borough_vals = ''
            if detected_borough:
                col = 'is_' + detected_borough
                borough_cols = ', ' + col
                borough_vals = ', 1'

            conn.execute(
                'INSERT OR IGNORE INTO articles '
                '(id, title, link, source, published, summary, interest_score, category, source_type' + borough_cols + ') '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?' + borough_vals + ')',
                (aid, title, post['source_url'], name + ' (Facebook)',
                 datetime.now(timezone.utc).strftime('%Y-%m-%d'), text[:500],
                 score, 'politics', 'facebook')
            )
            new_count += 1
            log.info('  NEW [%d] %s: %s', score, detected_borough or 'lancs', title[:60])

        time.sleep(2)  # Rate limit between pages

    if not dry_run:
        conn.commit()

    return new_count


def main():
    parser = argparse.ArgumentParser(description='Facebook page crawler for NL')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--page', type=str, help='Filter by page name')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    new = crawl_all(conn, args.dry_run, args.page)
    log.info('Crawled %d new posts from Facebook', new)
    conn.close()


if __name__ == '__main__':
    main()
