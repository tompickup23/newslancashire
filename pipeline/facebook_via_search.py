#!/usr/bin/env python3
"""
facebook_via_search.py — Crawl Facebook pages via DuckDuckGo site: search.

Uses DuckDuckGo HTML search (no API key needed, no CAPTCHA from datacenter IPs)
to find recent public Facebook posts. Extracts titles and post URLs.

Usage:
    python3 facebook_via_search.py                      # Crawl all pages
    python3 facebook_via_search.py --page "Oliver Ryan"  # Single page
    python3 facebook_via_search.py --dry-run
"""

import argparse
import hashlib
import html as html_mod
import json
import logging
import os
import random
import re
import sqlite3
import time
import urllib.request
import urllib.parse
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
        logging.FileHandler(LOG_DIR / 'facebook_search.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('fb_search')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36',
]

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

HIGH_INTEREST = ['reform', 'election', 'council tax', 'budget', 'crime', 'police',
                 'planning', 'housing', 'nhs', 'hospital', 'school', 'closure',
                 'investigation', 'spending', 'million', 'arrested']


def detect_borough(text, default=''):
    text_lower = text.lower()
    for borough, kws in BOROUGH_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            return borough
    return default


def score_interest(text):
    score = 40
    for kw in HIGH_INTEREST:
        if kw in text.lower():
            score += 12
    return min(100, score)


def search_ddg(query, num_results=10, time_filter='m'):
    """Search DuckDuckGo HTML and extract results.
    time_filter: 'd' (day), 'w' (week), 'm' (month), '' (all time)"""
    params = 'q=' + urllib.parse.quote(query)
    if time_filter:
        params += '&df=' + time_filter
    url = 'https://html.duckduckgo.com/html/?' + params
    req = urllib.request.Request(url, headers={
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-GB,en;q=0.9',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log.warning('DuckDuckGo search failed: %s', str(e)[:60])
        return []

    # Extract results
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|span)', html, re.DOTALL)

    results = []
    for i in range(min(len(titles), len(urls), num_results)):
        title = html_mod.unescape(re.sub(r'<[^>]+>', '', titles[i]).strip())
        result_url = re.sub(r'<[^>]+>', '', urls[i]).strip()
        snippet = html_mod.unescape(re.sub(r'<[^>]+>', '', snippets[i]).strip()) if i < len(snippets) else ''

        # Only keep actual post URLs (not profile/about pages)
        if '/posts/' in result_url or '/photos/' in result_url:
            results.append({
                'title': title,
                'url': 'https://' + result_url if not result_url.startswith('http') else result_url,
                'snippet': snippet,
            })

    return results


def crawl_facebook_pages(config, page_filter=None, dry_run=False):
    """Crawl all configured Facebook pages via DuckDuckGo."""
    pages = config.get('facebook_pages', [])
    if page_filter:
        pages = [p for p in pages if page_filter.lower() in p.get('name', '').lower()]

    conn = sqlite3.connect(str(DB_PATH))
    total_new = 0

    for page_cfg in pages:
        name = page_cfg.get('name', '?')
        url = page_cfg.get('url', '')
        borough = page_cfg.get('borough_focus', '')

        if not url:
            continue

        slug = page_cfg.get('slug', url.rstrip('/').split('/')[-1])
        query = f'site:facebook.com/{slug}'

        log.info('Searching: %s (%s)', name, slug)
        results = search_ddg(query, num_results=8)
        log.info('  Found %d post results', len(results))

        for r in results:
            title = r['title']
            # Clean up title — remove "Name - " prefix and " | Facebook" suffix
            title = re.sub(r'^[^-]+-\s*', '', title)
            title = re.sub(r'\s*[|·]\s*Facebook\s*$', '', title)
            title = title.strip()

            if len(title) < 20:
                continue

            # Use snippet as summary if available
            text = title + ' ' + r.get('snippet', '')
            aid = hashlib.md5((slug + title).encode()).hexdigest()

            if conn.execute('SELECT 1 FROM articles WHERE id = ?', (aid,)).fetchone():
                continue

            detected_borough = detect_borough(text, borough)
            score = score_interest(text)

            if dry_run:
                log.info('  [%d] %s: %s', score, detected_borough or 'lancs', title[:80])
                total_new += 1
                continue

            borough_col = ', is_' + detected_borough if detected_borough else ''
            borough_val = ', 1' if detected_borough else ''

            conn.execute(
                'INSERT OR IGNORE INTO articles '
                '(id, title, link, source, published, summary, interest_score, category, source_type' + borough_col + ') '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?' + borough_val + ')',
                (aid, title[:200], r['url'], name + ' (Facebook)',
                 datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                 r.get('snippet', text)[:500],
                 score, 'politics', 'facebook_search')
            )
            total_new += 1
            log.info('  NEW [%d] %s: %s', score, detected_borough or 'lancs', title[:60])

        time.sleep(random.uniform(3, 6))  # Rate limit DDG

    if not dry_run:
        conn.commit()
    conn.close()
    return total_new


def main():
    parser = argparse.ArgumentParser(description='Facebook crawler via DuckDuckGo')
    parser.add_argument('--page', type=str, help='Filter by page name')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    config = json.load(open(CONFIG_PATH))
    new = crawl_facebook_pages(config, args.page, args.dry_run)
    log.info('Total new: %d', new)


if __name__ == '__main__':
    main()
