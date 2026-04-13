#!/usr/bin/env python3
"""
article_enricher.py — Fetch full article text from source URLs.

Takes articles that only have RSS summaries (1-2 sentences) and
fetches the actual article page to extract the full text.

Uses readability-style extraction: finds the main content block,
strips ads/navigation/sidebars, returns clean text.

This does NOT rewrite or generate content — it copies the original
article text verbatim, then attributes the source.

Usage:
    python3 article_enricher.py                 # Enrich all pending
    python3 article_enricher.py --max 20        # Limit
    python3 article_enricher.py --dry-run       # Show what would be enriched
"""

import argparse
import logging
import os
import re
import sqlite3
import time
import urllib.request
import urllib.error
from pathlib import Path

NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
DB_PATH = NL_PIPELINE_DIR / 'db' / 'news.db'
LOG_DIR = NL_PIPELINE_DIR / 'logs'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'enricher.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('enricher')

# Skip these domains (paywalled, login-required, or Google redirects)
SKIP_DOMAINS = [
    'bsky.app',             # Bluesky (already have full post text)
    'facebook.com',         # Login wall
    'twitter.com', 'x.com', # Login wall
    'instagram.com',        # Login wall
]


def should_skip(url):
    """Check if URL should be skipped."""
    for domain in SKIP_DOMAINS:
        if domain in url:
            return True
    return False


def resolve_google_news_url(url):
    """Resolve a Google News redirect URL to the actual article URL.
    Google News RSS URLs are Base64-encoded. We fetch the page and
    extract the canonical/redirect URL from the HTML."""
    if 'news.google.com' not in url:
        return url
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(50000).decode('utf-8', errors='replace')
            # Look for the actual article URL in the page
            # Google News embeds it in a data-redirect attribute or a JS redirect
            match = re.search(r'data-n-au="([^"]+)"', html)
            if match:
                return match.group(1)
            # Try canonical link
            match = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html)
            if match and 'news.google.com' not in match.group(1):
                return match.group(1)
            # Try og:url
            match = re.search(r'property="og:url"[^>]+content="([^"]+)"', html)
            if match and 'news.google.com' not in match.group(1):
                return match.group(1)
            # Try any non-Google URL in the page
            urls = re.findall(r'https?://(?:www\.)?(?:lancashiretelegraph|burnleyexpress|blackpoolgazette|lep|beyondradio|blogpreston|bbc\.co\.uk/news)[^\s"<>]+', html)
            if urls:
                return urls[0]
    except Exception as e:
        log.debug('Google News resolve failed: %s', str(e)[:40])
    return url  # Return original if resolution fails


def extract_article_text(html):
    """Extract main article text from HTML page.
    Simple readability-style extraction without dependencies."""
    # Remove script, style, nav, header, footer, aside, form elements
    for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript', 'iframe']:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Try to find article body
    # Look for common article content containers
    content = None
    for pattern in [
        r'<article[^>]*>(.*?)</article>',
        r'class="[^"]*(?:article-body|article__body|story-body|entry-content|post-content|content-body)[^"]*"[^>]*>(.*?)</div>',
        r'itemprop="articleBody"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*(?:article|story|content|post)[^"]*"[^>]*>(.*?)</div>',
    ]:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1) if match.lastindex else match.group(0)
            break

    if not content:
        # Fallback: extract all paragraphs
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        if paragraphs:
            # Filter out short/nav paragraphs
            good_paras = [p for p in paragraphs if len(re.sub(r'<[^>]+>', '', p).strip()) > 40]
            content = '\n\n'.join(good_paras)

    if not content:
        return None

    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', content)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()

    # Must be substantial
    if len(text) < 100:
        return None

    return text[:3000]  # Cap at 3000 chars


def fetch_full_text(url, timeout=15):
    """Fetch a URL and extract article text."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0',
            'Accept': 'text/html',
            'Accept-Language': 'en-GB,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Check content type
            ct = resp.headers.get('Content-Type', '')
            if 'text/html' not in ct:
                return None
            html = resp.read(500000).decode('utf-8', errors='replace')  # Max 500KB
        return extract_article_text(html)
    except Exception as e:
        log.debug('Fetch failed %s: %s', url[:50], str(e)[:40])
        return None


def ensure_columns(conn):
    for col, typedef in [
        ('full_text', 'TEXT'),
        ('enriched_at', 'TEXT'),
    ]:
        try:
            conn.execute(f'ALTER TABLE articles ADD COLUMN {col} {typedef}')
        except sqlite3.OperationalError:
            pass


def get_pending(conn, max_articles=50):
    """Get articles needing enrichment."""
    col_names = [r[1] for r in conn.execute('PRAGMA table_info(articles)').fetchall()]
    has_full = 'full_text' in col_names

    if has_full:
        query = """
            SELECT id, title, link, source, interest_score
            FROM articles
            WHERE interest_score >= 40
              AND (full_text IS NULL OR full_text = '')
              AND link IS NOT NULL AND link != ''
            ORDER BY interest_score DESC
            LIMIT ?
        """
    else:
        query = """
            SELECT id, title, link, source, interest_score
            FROM articles
            WHERE interest_score >= 40
              AND link IS NOT NULL AND link != ''
            ORDER BY interest_score DESC
            LIMIT ?
        """
    return conn.execute(query, (max_articles,)).fetchall()


def main():
    parser = argparse.ArgumentParser(description='Enrich articles with full text')
    parser.add_argument('--max', type=int, default=30, help='Max articles')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    ensure_columns(conn)
    conn.commit()

    articles = get_pending(conn, args.max)
    log.info('Found %d articles to enrich', len(articles))

    enriched = 0
    skipped = 0
    for aid, title, link, source, score in articles:
        if should_skip(link):
            skipped += 1
            continue

        # Resolve Google News URLs to actual article URLs
        actual_url = resolve_google_news_url(link)
        if actual_url != link:
            log.info('  Resolved: %s → %s', link[:40], actual_url[:60])
            # Update the link in the DB
            conn.execute('UPDATE articles SET link = ? WHERE id = ?', (actual_url, aid))

        if should_skip(actual_url):
            skipped += 1
            continue

        if args.dry_run:
            log.info('  [%d] %s: %s → %s', score, source, title[:40], actual_url[:50])
            continue

        full_text = fetch_full_text(actual_url)
        if full_text and len(full_text) > 100:
            conn.execute(
                'UPDATE articles SET full_text = ?, enriched_at = datetime(\"now\") WHERE id = ?',
                (full_text, aid)
            )
            enriched += 1
            log.info('OK [%d] %s (%d chars)', score, title[:50], len(full_text))
        else:
            log.debug('SKIP: %s (no extractable text)', title[:50])
            skipped += 1

        time.sleep(1)  # Rate limit

    if not args.dry_run:
        conn.commit()

    conn.close()
    log.info('Enriched: %d, Skipped: %d', enriched, skipped)


if __name__ == '__main__':
    main()
