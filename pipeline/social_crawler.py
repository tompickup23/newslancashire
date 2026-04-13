#!/usr/bin/env python3
"""
social_crawler.py — Social media crawler for Lancashire news.

Two modes:
1. mbasic.facebook.com scraping (lightweight, no browser needed)
2. Playwright headless for X/Twitter (needs JS rendering)

Anti-detection: rotating user agents, random delays, session cookies.

Usage:
    python3 social_crawler.py                       # Crawl all
    python3 social_crawler.py --platform facebook   # Facebook only
    python3 social_crawler.py --platform x          # X only
    python3 social_crawler.py --dry-run
    python3 social_crawler.py --page "Lancashire Police"
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from http.cookiejar import CookieJar

NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
DB_PATH = NL_PIPELINE_DIR / 'db' / 'news.db'
LOG_DIR = NL_PIPELINE_DIR / 'logs'
CONFIG_PATH = NL_PIPELINE_DIR / 'config' / 'feeds.json'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'social_crawler.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('social_crawler')

# Rotating user agents for anti-detection
USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; Nokia G50) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Mobile Safari/537.36',
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
    score = 35
    for kw in HIGH_INTEREST:
        if kw in text.lower():
            score += 12
    return min(100, score)


def random_delay(min_s=2, max_s=6):
    time.sleep(random.uniform(min_s, max_s))


# ── Facebook mbasic scraper ──────────────────────────────────

def _create_fb_opener():
    """Create urllib opener with cookie support for mbasic."""
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return opener


def crawl_facebook_mbasic(page_config, opener=None):
    """Scrape public Facebook page via mbasic.facebook.com."""
    name = page_config.get('name', '?')
    url = page_config.get('url', '')
    if not url:
        return []

    slug = url.rstrip('/').split('/')[-1]
    target = f'https://mbasic.facebook.com/{slug}'

    if opener is None:
        opener = _create_fb_opener()

    ua = random.choice(USER_AGENTS)
    log.info('Facebook: %s → %s', name, slug)

    try:
        req = urllib.request.Request(target, headers={
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
        })
        resp = opener.open(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log.warning('Facebook fetch failed %s: %s', name, str(e)[:60])
        return []

    # Check for login wall
    if 'login' in html[:2000].lower() and 'password' in html[:5000].lower():
        log.info('  %s: login wall detected, trying to extract visible posts...', name)

    posts = []

    # mbasic wraps posts in <div> with specific structure
    # Each post's text is inside story_body_container or userContent
    # Try multiple extraction strategies

    # Strategy 1: Extract from article/story blocks
    story_blocks = re.findall(
        r'<(?:article|div)[^>]*(?:story_body_container|userContent|_5rgt|_55wo)[^>]*>(.*?)</(?:article|div)>',
        html, re.DOTALL | re.IGNORECASE
    )

    # Strategy 2: Extract from paragraphs with substantial text
    if not story_blocks:
        story_blocks = re.findall(r'<div[^>]*>((?:[^<]|<(?!/div>))*?)</div>', html, re.DOTALL)

    for block in story_blocks:
        text = re.sub(r'<[^>]+>', ' ', block)
        text = re.sub(r'\s+', ' ', text).strip()

        # Filter: must be substantial, not UI text
        if len(text) < 60:
            continue
        lower = text.lower()
        if any(skip in lower for skip in ['log in', 'sign up', 'create account', 'forgot password',
                                           'see more', 'like · comment', 'share', 'privacy · terms']):
            continue
        # Skip if it's mostly numbers/punctuation
        alpha_ratio = sum(1 for c in text if c.isalpha()) / max(len(text), 1)
        if alpha_ratio < 0.5:
            continue

        posts.append({
            'text': text[:1000],
            'source': name + ' (Facebook)',
            'url': f'https://www.facebook.com/{slug}',
        })

    log.info('  %s: %d posts extracted', name, len(posts))
    return posts[:10]


# ── X/Twitter scraper (Playwright) ───────────────────────────

def crawl_x_playwright(accounts, max_accounts=10):
    """Crawl X/Twitter profiles using Playwright headless browser."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning('Playwright not installed, skipping X crawl')
        return []

    all_posts = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=random.choice(USER_AGENTS).replace('Mobile', 'Desktop'),
        )

        for account in accounts[:max_accounts]:
            handle = account.get('handle', '')
            name = account.get('name', '?')
            if not handle:
                continue

            target = f'https://x.com/{handle}'
            log.info('X: %s → %s', name, handle)

            try:
                page = context.new_page()
                page.set_default_timeout(12000)
                page.goto(target, wait_until='domcontentloaded')
                time.sleep(3 + random.uniform(0, 2))

                page.evaluate('window.scrollBy(0, 1500)')
                time.sleep(2)

                tweets = page.evaluate('''
                    () => {
                        const texts = [];
                        document.querySelectorAll('[data-testid="tweetText"]').forEach(el => {
                            const t = el.innerText.trim();
                            if (t.length > 30) texts.push(t);
                        });
                        return texts.slice(0, 8);
                    }
                ''')

                for text in tweets:
                    all_posts.append({
                        'text': text[:1000],
                        'source': name + ' (X)',
                        'url': target,
                    })

                log.info('  %s: %d tweets', name, len(tweets))
                page.close()
            except Exception as e:
                log.warning('  %s failed: %s', name, str(e)[:60])
                try:
                    page.close()
                except Exception:
                    pass

            random_delay(3, 7)

        browser.close()

    return all_posts


# ── Database ─────────────────────────────────────────────────

def save_posts(conn, posts, borough_default=''):
    new_count = 0
    for post in posts:
        text = post['text']
        title = text[:120]
        if len(text) > 120:
            title = text[:117].rsplit(' ', 1)[0] + '...'

        aid = hashlib.md5((post['url'] + title).encode()).hexdigest()
        if conn.execute('SELECT 1 FROM articles WHERE id = ?', (aid,)).fetchone():
            continue

        borough = detect_borough(text, borough_default)
        score = score_interest(text)

        borough_col = ''
        borough_val = ''
        if borough:
            borough_col = ', is_' + borough
            borough_val = ', 1'

        conn.execute(
            'INSERT OR IGNORE INTO articles '
            '(id, title, link, source, published, summary, interest_score, category, source_type' + borough_col + ') '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?' + borough_val + ')',
            (aid, title, post['url'], post['source'],
             datetime.now(timezone.utc).strftime('%Y-%m-%d'), text[:500],
             score, 'politics', 'social_crawler')
        )
        new_count += 1
        log.info('  NEW [%d] %s: %s', score, borough or 'lancs', title[:60])

    return new_count


def main():
    parser = argparse.ArgumentParser(description='Social media crawler')
    parser.add_argument('--platform', choices=['facebook', 'x', 'all'], default='all')
    parser.add_argument('--page', type=str, help='Filter by name')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max', type=int, default=15)
    args = parser.parse_args()

    config = json.load(open(CONFIG_PATH))
    conn = sqlite3.connect(str(DB_PATH))
    total_new = 0

    # Facebook (mbasic, no browser)
    if args.platform in ('facebook', 'all'):
        pages = config.get('facebook_pages', [])
        if args.page:
            pages = [p for p in pages if args.page.lower() in p.get('name', '').lower()]

        opener = _create_fb_opener()
        for page_cfg in pages[:args.max]:
            posts = crawl_facebook_mbasic(page_cfg, opener)
            if not args.dry_run:
                new = save_posts(conn, posts, page_cfg.get('borough_focus', ''))
                total_new += new
            else:
                for p in posts:
                    log.info('  DRY [%d]: %s', score_interest(p['text']), p['text'][:70])
            random_delay(2, 5)

    # X/Twitter (Playwright)
    if args.platform in ('x', 'all'):
        accounts = config.get('x_accounts', [])
        if args.page:
            accounts = [a for a in accounts if args.page.lower() in a.get('name', '').lower()]
        x_posts = crawl_x_playwright(accounts[:args.max])
        if not args.dry_run:
            total_new += save_posts(conn, x_posts)
        else:
            for p in x_posts:
                log.info('  DRY [%d]: %s', score_interest(p['text']), p['text'][:70])

    if not args.dry_run:
        conn.commit()
    conn.close()
    log.info('Total new: %d', total_new)


if __name__ == '__main__':
    main()
