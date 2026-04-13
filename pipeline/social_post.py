#!/usr/bin/env python3
"""
social_post.py — Post top News Lancashire articles to Bluesky.

Selects unposted high-interest articles, generates a social card via SR brand_system,
and posts to Bluesky with the AT Protocol.

Usage:
    python3 social_post.py                      # Post top unposted article
    python3 social_post.py --max 3              # Post up to 3 articles
    python3 social_post.py --dry-run            # Show what would be posted
"""

import argparse
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

# Load .env
_env_file = NL_PIPELINE_DIR / '.env'
if _env_file.is_file():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

BLUESKY_HANDLE = os.environ.get('BLUESKY_HANDLE', '')
BLUESKY_APP_PASSWORD = os.environ.get('BLUESKY_APP_PASSWORD', '')

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'social_post.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('social_post')

BOROUGH_MAP = {
    'is_burnley': 'Burnley', 'is_pendle': 'Pendle', 'is_hyndburn': 'Hyndburn',
    'is_rossendale': 'Rossendale', 'is_ribble_valley': 'Ribble Valley',
    'is_blackburn': 'Blackburn', 'is_blackpool': 'Blackpool',
    'is_chorley': 'Chorley', 'is_south_ribble': 'South Ribble',
    'is_preston': 'Preston', 'is_west_lancashire': 'West Lancashire',
    'is_lancaster': 'Lancaster', 'is_wyre': 'Wyre', 'is_fylde': 'Fylde',
}


def ensure_columns(conn):
    """Add social posting columns."""
    for col, typedef in [
        ('posted_to_bluesky', 'INTEGER DEFAULT 0'),
        ('bluesky_uri', 'TEXT'),
    ]:
        try:
            conn.execute(f'ALTER TABLE articles ADD COLUMN {col} {typedef}')
        except sqlite3.OperationalError:
            pass


def get_unposted_articles(conn, max_articles=3):
    """Get high-interest articles not yet posted to Bluesky."""
    col_names = [r[1] for r in conn.execute('PRAGMA table_info(articles)').fetchall()]
    has_bluesky = 'posted_to_bluesky' in col_names

    query = """
        SELECT id, title, link, source, published, category, interest_score,
               COALESCE(two_pass_rewrite, ai_rewrite, summary) as content,
               is_burnley, is_pendle, is_hyndburn, is_rossendale, is_blackburn,
               is_blackpool, is_preston, is_lancaster, is_chorley, is_south_ribble,
               is_west_lancashire, is_wyre, is_fylde
        FROM articles
        WHERE interest_score >= 70
          AND (ai_rewrite IS NOT NULL AND ai_rewrite != '')
    """
    if has_bluesky:
        query += ' AND (posted_to_bluesky IS NULL OR posted_to_bluesky = 0)'
    query += ' ORDER BY interest_score DESC, published DESC LIMIT ?'

    conn.row_factory = sqlite3.Row
    return conn.execute(query, (max_articles,)).fetchall()


def make_post_text(title, borough, summary, link):
    """Create Bluesky post text (max 300 chars)."""
    tag = f'#{borough.replace(" ", "")}' if borough else '#Lancashire'
    text = f'{title[:200]}\n\n{tag} #Lancashire #LocalNews'
    if link:
        text += f'\n\n{link}'
    if len(text) > 300:
        text = text[:297] + '...'
    return text


def bluesky_auth():
    """Authenticate with Bluesky AT Protocol."""
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        return None
    payload = json.dumps({
        'identifier': BLUESKY_HANDLE,
        'password': BLUESKY_APP_PASSWORD,
    }).encode()
    req = urllib.request.Request(
        'https://bsky.social/xrpc/com.atproto.server.createSession',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.error('Bluesky auth failed: %s', e)
        return None


def bluesky_post(session, text):
    """Create a Bluesky post. Returns post URI or None."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    record = {
        'repo': session['did'],
        'collection': 'app.bsky.feed.post',
        'record': {
            '$type': 'app.bsky.feed.post',
            'text': text,
            'createdAt': now,
            'langs': ['en'],
        },
    }

    # Detect URLs and add facets
    url_match = re.search(r'https?://\S+', text)
    if url_match:
        record['record']['facets'] = [{
            'index': {
                'byteStart': text.encode('utf-8').index(url_match.group().encode('utf-8')),
                'byteEnd': text.encode('utf-8').index(url_match.group().encode('utf-8')) + len(url_match.group().encode('utf-8')),
            },
            'features': [{'$type': 'app.bsky.richtext.facet#link', 'uri': url_match.group()}],
        }]

    payload = json.dumps(record).encode()
    req = urllib.request.Request(
        'https://bsky.social/xrpc/com.atproto.repo.createRecord',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {session["accessJwt"]}',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get('uri')
    except Exception as e:
        log.error('Bluesky post failed: %s', e)
        return None


def main():
    parser = argparse.ArgumentParser(description='Post NL articles to Bluesky')
    parser.add_argument('--max', type=int, default=1, help='Max articles to post')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    ensure_columns(conn)
    conn.commit()

    articles = get_unposted_articles(conn, args.max)
    log.info('Found %d unposted articles', len(articles))

    if not articles:
        conn.close()
        return

    if args.dry_run:
        for row in articles:
            r = dict(row)
            borough = 'Lancashire'
            for col, name in BOROUGH_MAP.items():
                if r.get(col, 0) == 1:
                    borough = name
                    break
            text = make_post_text(r['title'], borough, '', r.get('link', ''))
            log.info('Would post [%d]: %s', r['interest_score'], text[:100])
        conn.close()
        return

    session = bluesky_auth()
    if not session:
        log.error('Bluesky authentication failed. Set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD in .env')
        conn.close()
        return

    posted = 0
    for row in articles:
        r = dict(row)
        borough = 'Lancashire'
        for col, name in BOROUGH_MAP.items():
            if r.get(col, 0) == 1:
                borough = name
                break

        summary = (r.get('content') or '')[:150]
        text = make_post_text(r['title'], borough, summary, r.get('link', ''))
        uri = bluesky_post(session, text)
        if uri:
            conn.execute('UPDATE articles SET posted_to_bluesky = 1, bluesky_uri = ? WHERE id = ?', (uri, r['id']))
            conn.commit()
            posted += 1
            log.info('Posted [%d]: %s', r['interest_score'], r['title'][:60])
            time.sleep(5)  # Rate limit
        else:
            log.warning('Failed to post: %s', r['title'][:60])

    conn.close()
    log.info('Posted %d/%d articles to Bluesky', posted, len(articles))


if __name__ == '__main__':
    main()
