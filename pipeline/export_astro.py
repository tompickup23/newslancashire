#!/usr/bin/env python3
"""
export_astro.py — Export SQLite articles to Astro content collection markdown.

Generates files in src/content/articles/ with Zod-validated frontmatter matching
the Astro content schema defined in content.config.ts.

Quality gate:
  - Only exports articles with interest_score >= 40
  - Prefers two_pass_rewrite over ai_rewrite
  - Validates borough and category against Astro enums

Usage:
    python3 export_astro.py                          # Export all eligible
    python3 export_astro.py --output ~/newslancashire/src/content/articles/
    python3 export_astro.py --max 50                 # Limit output
    python3 export_astro.py --since 2026-04-01       # Only recent articles
    python3 export_astro.py --dry-run                # Show what would be exported
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path('/home/ubuntu/newslancashire')
DB_PATH = BASE / 'db' / 'news.db'
DEFAULT_OUTPUT = Path('/home/ubuntu/newslancashire/astro-content/articles')
LOG_DIR = BASE / 'logs'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'export_astro.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('export_astro')

# Must match content.config.ts enums exactly
VALID_BOROUGHS = [
    'burnley', 'pendle', 'hyndburn', 'rossendale', 'ribble-valley',
    'lancaster', 'wyre', 'fylde', 'chorley', 'south-ribble',
    'preston', 'west-lancashire', 'blackpool', 'blackburn', 'lancashire-wide',
]

VALID_CATEGORIES = [
    'local', 'crime', 'politics', 'health', 'education',
    'transport', 'planning', 'environment', 'business', 'sport',
    'council', 'investigation', 'data-driven',
]

VALID_TIERS = ['summary', 'analysis', 'investigation', 'cross-publish', 'data-driven']

# DB borough columns → Astro borough slug
DB_BOROUGH_MAP = {
    'is_burnley': 'burnley',
    'is_pendle': 'pendle',
    'is_hyndburn': 'hyndburn',
    'is_rossendale': 'rossendale',
    'is_ribble_valley': 'ribble-valley',
    'is_lancaster': 'lancaster',
    'is_wyre': 'wyre',
    'is_fylde': 'fylde',
    'is_chorley': 'chorley',
    'is_south_ribble': 'south-ribble',
    'is_preston': 'preston',
    'is_west_lancashire': 'west-lancashire',
    'is_blackpool': 'blackpool',
    'is_blackburn': 'blackburn',
    'is_lancashire_cc': 'lancashire-wide',
}

# DB category → Astro category
CATEGORY_MAP = {
    'general': 'local',
    'politics': 'politics',
    'crime': 'crime',
    'sport': 'sport',
    'business': 'business',
    'health': 'health',
    'education': 'education',
    'transport': 'transport',
    'community': 'local',
    'weather': 'environment',
    'planning': 'planning',
    'environment': 'environment',
    'council': 'council',
    'investigation': 'investigation',
    'local': 'local',
    'data-driven': 'data-driven',
}


def slugify(text, max_len=80):
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    if len(text) > max_len:
        text = text[:max_len].rsplit('-', 1)[0]
    return text


def get_borough(row_dict):
    """Get primary Astro borough from DB row."""
    for db_col, astro_slug in DB_BOROUGH_MAP.items():
        if row_dict.get(db_col, 0) == 1:
            return astro_slug
    return 'lancashire-wide'


def get_category(db_category):
    """Map DB category to Astro category."""
    mapped = CATEGORY_MAP.get(db_category, db_category)
    if mapped in VALID_CATEGORIES:
        return mapped
    return 'local'


def get_content_tier(db_tier, interest_score):
    """Map DB tier to Astro tier."""
    if db_tier in VALID_TIERS:
        return db_tier
    if interest_score >= 70:
        return 'analysis'
    return 'summary'


def format_date(date_str):
    """Parse and format date to YYYY-MM-DD."""
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d',
                '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    # Last resort: try ISO parse
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def make_summary(content, max_len=200):
    """Extract first paragraph as summary."""
    if not content:
        return ''
    # Take first paragraph
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    if paragraphs:
        summary = paragraphs[0]
    else:
        summary = content
    # Truncate
    if len(summary) > max_len:
        summary = summary[:max_len].rsplit(' ', 1)[0] + '...'
    return summary


def article_to_markdown(row_dict):
    """Convert a DB article row to Astro markdown with frontmatter."""
    title = (row_dict.get('title') or 'Untitled').strip()
    # Use best available content
    content = (
        row_dict.get('two_pass_rewrite')
        or row_dict.get('ai_rewrite')
        or row_dict.get('summary')
        or ''
    ).strip()

    if not content:
        return None, None

    borough = get_borough(row_dict)
    category = get_category(row_dict.get('category', 'general'))
    date = format_date(row_dict.get('published'))
    interest_score = row_dict.get('interest_score', 50) or 50
    content_tier = get_content_tier(row_dict.get('content_tier', 'summary'), interest_score)
    source = row_dict.get('source', 'News Lancashire')
    source_url = row_dict.get('link', 'https://newslancashire.co.uk')
    fact_check_score = row_dict.get('fact_check_score', 0) or 0

    # Generate slug from title + date for uniqueness
    slug = slugify(title)
    slug_hash = hashlib.md5(row_dict.get('id', title).encode()).hexdigest()[:6]
    filename = f"{date}-{slug}-{slug_hash}.md"

    # Clean content for markdown
    # Replace single newlines with double (paragraph breaks)
    content_clean = re.sub(r'(?<!\n)\n(?!\n)', '\n\n', content)

    # Escape YAML special chars in title
    safe_title = title.replace('"', '\\"')

    # Validate source_url
    if not source_url.startswith('http'):
        source_url = f'https://newslancashire.co.uk'

    summary = make_summary(content, 200)
    safe_summary = summary.replace('"', '\\"')

    frontmatter = f'''---
headline: "{safe_title}"
date: "{date}"
category: "{category}"
borough: "{borough}"
source: "{source}"
source_url: "{source_url}"
interest_score: {interest_score}
content_tier: "{content_tier}"
summary: "{safe_summary}"
fact_check_score: {fact_check_score}
---'''

    markdown = f"{frontmatter}\n\n{content_clean}\n"
    return filename, markdown


def get_eligible_articles(conn, max_articles=500, since=None):
    """Get articles eligible for Astro export."""
    query = """
        SELECT *
        FROM articles
        WHERE interest_score >= 40
          AND (ai_rewrite IS NOT NULL AND ai_rewrite != '')
    """
    params = []
    if since:
        query += ' AND published >= ?'
        params.append(since)
    query += ' ORDER BY published DESC LIMIT ?'
    params.append(max_articles)

    conn.row_factory = sqlite3.Row
    return conn.execute(query, params).fetchall()


def main():
    parser = argparse.ArgumentParser(description='Export articles to Astro markdown')
    parser.add_argument('--output', type=str, default=str(DEFAULT_OUTPUT),
                        help='Output directory for markdown files')
    parser.add_argument('--max', type=int, default=500, help='Max articles to export')
    parser.add_argument('--since', type=str, help='Only export articles since date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be exported')
    parser.add_argument('--clean', action='store_true', help='Remove existing files before export')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        existing = list(output_dir.glob('*.md'))
        for f in existing:
            f.unlink()
        log.info('Cleaned %d existing files', len(existing))

    conn = sqlite3.connect(str(DB_PATH))
    articles = get_eligible_articles(conn, args.max, args.since)
    log.info('Found %d eligible articles', len(articles))

    exported = 0
    skipped = 0
    by_borough = {}
    by_category = {}

    for row in articles:
        row_dict = dict(row)
        filename, markdown = article_to_markdown(row_dict)

        if not filename or not markdown:
            skipped += 1
            continue

        if args.dry_run:
            borough = get_borough(row_dict)
            cat = get_category(row_dict.get('category', 'general'))
            log.info('  %s [%s/%s] score=%d', filename[:60], borough, cat,
                     row_dict.get('interest_score', 0))
        else:
            filepath = output_dir / filename
            with open(filepath, 'w') as f:
                f.write(markdown)

        # Stats
        borough = get_borough(row_dict)
        cat = get_category(row_dict.get('category', 'general'))
        by_borough[borough] = by_borough.get(borough, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        exported += 1

    conn.close()

    log.info('Exported: %d, Skipped: %d', exported, skipped)
    log.info('By borough: %s', json.dumps(by_borough, indent=2))
    log.info('By category: %s', json.dumps(by_category, indent=2))


if __name__ == '__main__':
    main()
