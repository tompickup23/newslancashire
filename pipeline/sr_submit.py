#!/usr/bin/env python3
"""
sr_submit.py — Submit top News Lancashire articles to Situation Room editorial queue.

Marks high-interest articles as pending_review in the SR article_reviews table.
Only submits articles that haven't been reviewed yet.

Usage:
    python3 sr_submit.py                     # Submit top 10 unreviewed
    python3 sr_submit.py --max 20            # Submit top 20
    python3 sr_submit.py --min-score 70      # Only high-interest
    python3 sr_submit.py --dry-run           # Show what would be submitted
"""

import argparse
import json
import logging
import os
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
DB_PATH = NL_PIPELINE_DIR / 'db' / 'news.db'
SR_DB_PATH = Path('/opt/dashboard/data/situationroom.db')
LOG_DIR = NL_PIPELINE_DIR / 'logs'

# SR API (local on vps-main, or remote)
SR_API_URL = os.environ.get('SR_API_URL', 'http://127.0.0.1:8440')
SR_PASSWORD = os.environ.get('AUTH_PASSWORD', '')

# Load .env
_env_file = NL_PIPELINE_DIR / '.env'
if _env_file.is_file():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# Also try SR .env for AUTH_PASSWORD
_sr_env = Path('/opt/dashboard/.env')
if _sr_env.is_file():
    with open(_sr_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k.strip() == 'AUTH_PASSWORD':
                    SR_PASSWORD = v.strip()

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'sr_submit.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('sr_submit')

BOROUGH_MAP = {
    'is_burnley': 'burnley', 'is_pendle': 'pendle', 'is_hyndburn': 'hyndburn',
    'is_rossendale': 'rossendale', 'is_ribble_valley': 'ribble_valley',
    'is_blackburn': 'blackburn', 'is_blackpool': 'blackpool',
    'is_chorley': 'chorley', 'is_south_ribble': 'south_ribble',
    'is_preston': 'preston', 'is_west_lancashire': 'west_lancashire',
    'is_lancaster': 'lancaster', 'is_wyre': 'wyre', 'is_fylde': 'fylde',
    'is_lancashire_cc': 'lancashire',
}


def get_top_articles(max_articles=10, min_score=60):
    """Get top unreviewed articles from NL DB."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get already-reviewed article IDs from SR DB
    reviewed_ids = set()
    if SR_DB_PATH.exists():
        try:
            sr_conn = sqlite3.connect(str(SR_DB_PATH))
            rows = sr_conn.execute(
                "SELECT article_id FROM article_reviews WHERE project = 'news_lancashire'"
            ).fetchall()
            reviewed_ids = {r[0] for r in rows}
            sr_conn.close()
        except Exception as e:
            log.warning('Could not read SR DB: %s', e)

    rows = conn.execute("""
        SELECT id, title, source, published, category, interest_score, content_tier,
               COALESCE(two_pass_rewrite, ai_rewrite, summary) as content,
               is_burnley, is_pendle, is_hyndburn, is_rossendale, is_blackburn,
               is_blackpool, is_preston, is_lancaster, is_chorley, is_south_ribble,
               is_west_lancashire, is_wyre, is_fylde, is_lancashire_cc
        FROM articles
        WHERE interest_score >= ?
          AND (ai_rewrite IS NOT NULL AND ai_rewrite != '')
        ORDER BY interest_score DESC, published DESC
        LIMIT ?
    """, (min_score, max_articles * 3)).fetchall()  # Get extra to filter reviewed

    articles = []
    for row in rows:
        r = dict(row)
        short_id = r['id'][:12]
        if short_id in reviewed_ids:
            continue

        borough = 'lancashire'
        for col, name in BOROUGH_MAP.items():
            if r.get(col, 0) == 1:
                borough = name
                break

        articles.append({
            'article_id': short_id,
            'title': r.get('title', '')[:120],
            'date': (r.get('published') or '')[:10],
            'category': r.get('category', 'local'),
            'council': borough,
            'interest_score': r.get('interest_score', 0),
            'content_tier': r.get('content_tier', 'summary'),
            'content': r.get('content', ''),
        })
        if len(articles) >= max_articles:
            break

    conn.close()
    return articles


def submit_to_sr_db(articles):
    """Submit articles directly to SR SQLite DB (same machine)."""
    if not SR_DB_PATH.exists():
        log.error('SR DB not found at %s', SR_DB_PATH)
        return 0

    conn = sqlite3.connect(str(SR_DB_PATH))
    now = datetime.now(timezone.utc).isoformat()
    submitted = 0

    for art in articles:
        review_id = f"news_lancashire-{art['council']}-{art['article_id']}"
        try:
            conn.execute("""
                INSERT INTO article_reviews (id, project, article_id, council, title, status, notes, reviewed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project, article_id, council) DO NOTHING
            """, (
                review_id, 'news_lancashire', art['article_id'], art['council'],
                art['title'], 'pending_review',
                f"Auto-submitted. Score: {art['interest_score']}, Tier: {art['content_tier']}",
                now, now
            ))
            submitted += 1
        except Exception as e:
            log.warning('Failed to submit %s: %s', art['article_id'], e)

    conn.commit()
    conn.close()
    return submitted


def main():
    parser = argparse.ArgumentParser(description='Submit NL articles to SR editorial')
    parser.add_argument('--max', type=int, default=50, help='Max articles to submit')
    parser.add_argument('--min-score', type=int, default=40, help='Min interest score')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    articles = get_top_articles(args.max, args.min_score)
    log.info('Found %d articles to submit (min_score=%d)', len(articles), args.min_score)

    if args.dry_run:
        for art in articles:
            log.info('  [%s] score=%d %s/%s: %s',
                     art['article_id'], art['interest_score'],
                     art['council'], art['category'], art['title'][:60])
        return

    submitted = submit_to_sr_db(articles)
    log.info('Submitted %d/%d articles to SR editorial queue', submitted, len(articles))


if __name__ == '__main__':
    main()
