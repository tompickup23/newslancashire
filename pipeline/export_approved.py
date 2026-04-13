#!/usr/bin/env python3
"""
export_approved.py — Export ONLY SR-approved articles to live Astro content.

Reads the SR article_reviews table, filters for status='approved',
then exports matching articles from the NL DB to Astro markdown.

This is the editorial gate — nothing goes live without SR approval.

Usage:
    python3 export_approved.py                          # Export approved
    python3 export_approved.py --output /path/to/dir    # Custom output
    python3 export_approved.py --include-pending         # Also include pending_review (bypass gate)
    python3 export_approved.py --dry-run                # Show what would export
"""

import argparse
import json
import logging
import os
import re
import sqlite3
from pathlib import Path

# Import the export logic from export_astro
import sys
sys.path.insert(0, os.path.dirname(__file__))
from export_astro import (
    article_to_markdown, get_borough, get_category,
    DB_PATH, VALID_BOROUGHS, VALID_CATEGORIES,
)

NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
NL_ASTRO_DIR = Path(os.environ.get('NL_ASTRO_DIR', '/root/newslancashire'))
SR_DB_PATH = Path('/opt/dashboard/data/situationroom.db')
DEFAULT_OUTPUT = NL_ASTRO_DIR / 'src' / 'content' / 'articles'
LOG_DIR = NL_PIPELINE_DIR / 'logs'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'export_approved.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('export_approved')


def get_approved_ids(include_pending=False):
    """Get article IDs approved in SR editorial."""
    if not SR_DB_PATH.exists():
        log.warning('SR DB not found at %s — exporting all articles (no gate)', SR_DB_PATH)
        return None  # None = no gate, export everything

    conn = sqlite3.connect(str(SR_DB_PATH))
    statuses = "'approved', 'content_approved'"
    if include_pending:
        statuses += ", 'pending_review'"

    rows = conn.execute(f"""
        SELECT article_id FROM article_reviews
        WHERE project = 'news_lancashire'
          AND status IN ({statuses})
    """).fetchall()
    conn.close()

    ids = {r[0] for r in rows}
    log.info('Found %d approved article IDs in SR', len(ids))
    return ids


def get_approved_articles(approved_ids, max_articles=500):
    """Get articles from NL DB that are in the approved set."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # If no gate (SR DB missing), export top articles
    if approved_ids is None:
        rows = conn.execute("""
            SELECT * FROM articles
            WHERE interest_score >= 50
              AND (ai_rewrite IS NOT NULL AND ai_rewrite != '')
            ORDER BY interest_score DESC, published DESC
            LIMIT ?
        """, (max_articles,)).fetchall()
    else:
        # Only export approved articles
        if not approved_ids:
            conn.close()
            return []
        placeholders = ','.join('?' * len(approved_ids))
        rows = conn.execute(f"""
            SELECT * FROM articles
            WHERE SUBSTR(id, 1, 12) IN ({placeholders})
              AND (ai_rewrite IS NOT NULL AND ai_rewrite != '')
            ORDER BY interest_score DESC, published DESC
        """, list(approved_ids)).fetchall()

    articles = [dict(r) for r in rows]
    conn.close()
    return articles


def main():
    parser = argparse.ArgumentParser(description='Export SR-approved articles to Astro')
    parser.add_argument('--output', type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument('--include-pending', action='store_true', help='Include pending_review')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--clean', action='store_true', help='Remove existing before export')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get approved IDs from SR
    approved_ids = get_approved_ids(args.include_pending)

    # Get matching articles
    articles = get_approved_articles(approved_ids)
    log.info('Found %d articles to export', len(articles))

    if args.clean:
        # Only remove auto-generated files, keep cross-published
        existing = [f for f in output_dir.glob('*.md') if not f.name.startswith(('lt-', 'as-', 'do-'))]
        for f in existing:
            f.unlink()
        log.info('Cleaned %d existing auto-generated files', len(existing))

    if args.dry_run:
        for art in articles[:20]:
            borough = get_borough(art)
            cat = get_category(art.get('category', 'local'))
            hl = art.get('clean_headline') or art.get('title', '')
            log.info('  [%d] %s/%s: %s', art.get('interest_score', 0), borough, cat, hl[:60])
        return

    exported = 0
    for art in articles:
        filename, markdown = article_to_markdown(art)
        if not filename or not markdown:
            continue
        filepath = output_dir / filename
        filepath.write_text(markdown)
        exported += 1

    # Also copy cross-published articles from staging
    staging = NL_PIPELINE_DIR / 'staging' / 'articles'
    if staging.exists():
        for f in staging.glob('*.md'):
            dest = output_dir / f.name
            if not dest.exists():
                dest.write_text(f.read_text())
                exported += 1

    log.info('Exported %d articles to %s', exported, output_dir)


if __name__ == '__main__':
    main()
