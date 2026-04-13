#!/usr/bin/env python3
"""
borough_detector.py — Enhanced borough detection for News Lancashire.

Two detection methods:
1. Source-based: RSS feed URL/source name maps to known boroughs
2. Entity-based: Keyword matching on title + summary + rewrite text

Fixes the 25% no-borough problem by using source URL patterns.

Usage:
    python3 borough_detector.py              # Re-detect all articles
    python3 borough_detector.py --untagged   # Only articles with no borough
"""

import argparse
import logging
import os
import re
import sqlite3
from pathlib import Path

BASE = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
DB_PATH = BASE / 'db' / 'news.db'
LOG_DIR = BASE / 'logs'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'borough_detector.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('borough_detector')

# Borough keywords — extended from redetect_boroughs.py
BOROUGH_KEYWORDS = {
    'burnley': [
        'burnley', 'padiham', 'brierfield', 'hapton', 'worsthorne',
        'cliviger', 'brunshaw', 'pike hill', 'rosehill', 'queensgate',
        'burnley fc', 'turf moor', 'burnley express',
    ],
    'pendle': [
        'pendle', 'nelson', 'colne', 'barnoldswick', 'barrowford',
        'earby', 'trawden', 'briercliffe', 'foulridge', 'roughlee',
        'pendleside', 'pendle hill',
    ],
    'hyndburn': [
        'hyndburn', 'accrington', 'oswaldtwistle', 'great harwood',
        'rishton', 'clayton-le-moors', 'altham', 'huncoat',
        'accrington stanley',
    ],
    'rossendale': [
        'rossendale', 'rawtenstall', 'bacup', 'haslingden',
        'whitworth', 'helmshore', 'waterfoot', 'stacksteads',
        'edenfield', 'ramsbottom',  # border area
    ],
    'ribble_valley': [
        'ribble valley', 'clitheroe', 'longridge', 'whalley',
        'read', 'sabden', 'chatburn', 'grindleton', 'slaidburn',
        'ribble valley borough',
    ],
    'blackburn': [
        'blackburn', 'darwen', 'blackburn with darwen', 'bwd',
        'blackburn rovers', 'ewood park', 'blackburn cathedral',
    ],
    'blackpool': [
        'blackpool', 'bispham', 'south shore', 'north shore',
        'blackpool tower', 'pleasure beach', 'blackpool fc',
        'blackpool victoria', 'layton',
    ],
    'chorley': [
        'chorley', 'adlington', 'euxton', 'coppull',
        'whittle-le-woods', 'astley village', 'clayton-le-woods',
        'buckshaw village',
    ],
    'south_ribble': [
        'south ribble', 'leyland', 'penwortham', 'bamber bridge',
        'lostock hall', 'walton-le-dale', 'farington',
    ],
    'preston': [
        'preston', 'fulwood', 'ashton-on-ribble', 'ribbleton',
        'ingol', 'brookfield', 'uclan', 'preston north end',
        'deepdale', 'avenham',
    ],
    'west_lancashire': [
        'west lancashire', 'ormskirk', 'skelmersdale', 'burscough',
        'tarleton', 'rufford', 'parbold', 'aughton',
        'edge hill university',
    ],
    'lancaster': [
        'lancaster', 'morecambe', 'heysham', 'carnforth',
        'silverdale', 'galgate', 'bolton-le-sands', 'hest bank',
        'lancaster university', 'lancaster castle',
    ],
    'wyre': [
        'wyre', 'fleetwood', 'thornton-cleveleys', 'garstang',
        'poulton-le-fylde', 'cleveleys', 'preesall', 'knott end',
        'over wyre',
    ],
    'fylde': [
        'fylde', 'lytham', 'st annes', 'kirkham', 'freckleton',
        'warton', 'lytham st annes', 'wesham', 'wrea green',
        'bae warton', 'fylde coast',
    ],
    'lancashire_cc': [
        'lancashire county council', 'lancashire cc', 'county hall',
        'lcc ', 'lancashire-wide', 'across lancashire',
    ],
}

# Source URL → borough mapping
SOURCE_BOROUGH_MAP = {
    'burnleyexpress.net': ['burnley'],
    'lancashiretelegraph.co.uk': ['blackburn', 'burnley', 'pendle', 'hyndburn', 'rossendale'],
    'blackpoolgazette.co.uk': ['blackpool', 'fylde', 'wyre'],
    'lep.co.uk': ['preston', 'south_ribble', 'chorley', 'west_lancashire'],
    'lancastergua': ['lancaster'],
    'beyondradio.co.uk': ['lancaster', 'wyre'],
    'thevisitor.co.uk': ['lancaster'],
    'chorleycitizen.co.uk': ['chorley'],
    'skelmersdalead': ['west_lancashire'],
    'rossendalefreepress.co.uk': ['rossendale'],
    'pendle.gov.uk': ['pendle'],
    'burnley.gov.uk': ['burnley'],
    'hyndburn.gov.uk': ['hyndburn'],
    'blackburn.gov.uk': ['blackburn'],
    'blackpool.gov.uk': ['blackpool'],
    'preston.gov.uk': ['preston'],
    'chorley.gov.uk': ['chorley'],
    'southribble.gov.uk': ['south_ribble'],
    'westlancs.gov.uk': ['west_lancashire'],
    'lancaster.gov.uk': ['lancaster'],
    'wyre.gov.uk': ['wyre'],
    'fylde.gov.uk': ['fylde'],
    'lancashire.gov.uk': ['lancashire_cc'],
    'lancashire.police.uk': [],  # Multi-borough, use keyword detection
    'bbc.co.uk/news/articles': [],  # Use keyword detection
}

# Astro uses hyphens, DB uses underscores
DB_TO_ASTRO = {
    'burnley': 'burnley',
    'pendle': 'pendle',
    'hyndburn': 'hyndburn',
    'rossendale': 'rossendale',
    'ribble_valley': 'ribble-valley',
    'blackburn': 'blackburn',
    'blackpool': 'blackpool',
    'chorley': 'chorley',
    'south_ribble': 'south-ribble',
    'preston': 'preston',
    'west_lancashire': 'west-lancashire',
    'lancaster': 'lancaster',
    'wyre': 'wyre',
    'fylde': 'fylde',
    'lancashire_cc': 'lancashire-wide',
}


def detect_from_source(source_url):
    """Detect boroughs from the source URL/name."""
    if not source_url:
        return []
    source_lower = source_url.lower()
    for domain, boroughs in SOURCE_BOROUGH_MAP.items():
        if domain in source_lower:
            return boroughs
    return []


def detect_from_keywords(text):
    """Detect boroughs from keyword matching on text."""
    if not text:
        return []
    text_lower = text.lower()
    matches = {}
    for borough, keywords in BOROUGH_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            matches[borough] = score
    # Sort by score descending
    return sorted(matches.keys(), key=lambda b: matches[b], reverse=True)


def detect_borough(title, summary, source_url, rewrite=None):
    """Detect borough(s) for an article. Returns list of borough IDs (DB format)."""
    # Method 1: Source URL
    source_boroughs = detect_from_source(source_url)

    # Method 2: Keyword matching on all text
    text = ' '.join(filter(None, [title, summary, rewrite]))
    keyword_boroughs = detect_from_keywords(text)

    # Combine: if source gives specific boroughs, intersect with keywords
    if source_boroughs and keyword_boroughs:
        # Prefer intersection
        intersection = [b for b in keyword_boroughs if b in source_boroughs]
        if intersection:
            return intersection
        # If no intersection, prefer keyword (more specific)
        return keyword_boroughs[:2]
    elif keyword_boroughs:
        return keyword_boroughs[:2]
    elif source_boroughs:
        return source_boroughs[:1]

    return []


def update_all(conn, untagged_only=False):
    """Re-detect boroughs for all articles."""
    borough_cols = [f'is_{b}' for b in BOROUGH_KEYWORDS.keys()]

    # Check which columns exist
    col_names = [r[1] for r in conn.execute('PRAGMA table_info(articles)').fetchall()]
    has_two_pass = 'two_pass_rewrite' in col_names
    extra_cols = ', ai_rewrite'
    if has_two_pass:
        extra_cols += ', two_pass_rewrite'

    if untagged_only:
        where = ' AND '.join(f'{col} = 0' for col in borough_cols)
        query = f'SELECT id, title, summary, link{extra_cols} FROM articles WHERE {where}'
    else:
        query = f'SELECT id, title, summary, link{extra_cols} FROM articles'

    rows = conn.execute(query).fetchall()
    log.info('Processing %d articles', len(rows))

    updated = 0
    for row in rows:
        aid, title, summary, link = row[0], row[1], row[2], row[3]
        rewrite = row[4] if len(row) > 4 else None
        two_pass = row[5] if len(row) > 5 else None
        text = two_pass or rewrite  # Prefer two-pass rewrite
        boroughs = detect_borough(title, summary, link, text)

        if boroughs:
            # Set borough flags
            updates = {f'is_{b}': 0 for b in BOROUGH_KEYWORDS.keys()}
            for b in boroughs:
                updates[f'is_{b}'] = 1

            set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
            values = list(updates.values()) + [aid]
            conn.execute(f'UPDATE articles SET {set_clause} WHERE id = ?', values)
            updated += 1

    conn.commit()

    # Print stats
    for borough in sorted(BOROUGH_KEYWORDS.keys()):
        col = f'is_{borough}'
        count = conn.execute(f'SELECT COUNT(*) FROM articles WHERE {col} = 1').fetchone()[0]
        if count > 0:
            log.info('%s: %d articles', borough, count)

    # Count untagged
    where = ' AND '.join(f'{col} = 0' for col in borough_cols)
    untagged = conn.execute(f'SELECT COUNT(*) FROM articles WHERE {where}').fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
    log.info('Total: %d, Updated: %d, Still untagged: %d', total, updated, untagged)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--untagged', action='store_true', help='Only process untagged articles')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    update_all(conn, untagged_only=args.untagged)
    conn.close()


if __name__ == '__main__':
    main()
