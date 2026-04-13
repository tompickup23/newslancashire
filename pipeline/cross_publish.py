#!/usr/bin/env python3
"""
cross_publish.py — Pull articles from Labour Tracker, Asylum Stats, and AI DOGE
into News Lancashire as cross-published content.

Sources:
  1. Labour Tracker investigations (Astro markdown in ~/labour-tracker/src/content/investigations/)
  2. Asylum Stats findings (Astro markdown in ~/asylumstats/src/content/findings/)
  3. AI DOGE articles (JSON in burnley-council/data/{council}/articles-index.json)

Only articles with Lancashire relevance are cross-published.

Usage:
    python3 cross_publish.py                    # Process all sources
    python3 cross_publish.py --source lt        # Labour Tracker only
    python3 cross_publish.py --source asylum    # Asylum Stats only
    python3 cross_publish.py --source doge      # AI DOGE only
    python3 cross_publish.py --dry-run          # Show what would be published
"""

import argparse
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

# Configurable paths (vps-main defaults)
NL_ASTRO_DIR = Path(os.environ.get('NL_ASTRO_DIR', '/root/newslancashire'))
NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))

LT_DIR = Path(os.environ.get('LT_DIR', '/root/labour-tracker'))
ASYLUM_DIR = Path(os.environ.get('ASYLUM_DIR', '/root/asylumstats'))
DOGE_DATA_DIR = Path(os.environ.get('DOGE_DATA_DIR', '/root/aidoge/burnley-council/data'))

# Fallback paths
for alt in [Path('/root/labour-tracker'), Path('/opt/labour-tracker'), Path.home() / 'clawd' / 'labour-tracker']:
    if alt.exists():
        LT_DIR = alt
        break
for alt in [Path('/root/asylumstats'), Path.home() / 'asylumstats']:
    if alt.exists():
        ASYLUM_DIR = alt
        break
for alt in [Path('/root/aidoge/burnley-council/data'), Path('/root/clawd-worker/aidoge/data'), Path.home() / 'clawd' / 'burnley-council' / 'data']:
    if alt.exists():
        DOGE_DATA_DIR = alt
        break

OUTPUT_DIR = NL_ASTRO_DIR / 'src' / 'content' / 'articles'
LOG_DIR = NL_PIPELINE_DIR / 'logs'

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'cross_publish.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('cross_publish')

# Lancashire councils (for DOGE filtering)
LANCASHIRE_COUNCILS = {
    'burnley', 'pendle', 'hyndburn', 'rossendale', 'ribble_valley',
    'blackburn', 'blackpool', 'chorley', 'south_ribble', 'preston',
    'west_lancashire', 'lancaster', 'wyre', 'fylde', 'lancashire_cc',
}

COUNCIL_TO_BOROUGH = {
    'burnley': 'burnley', 'pendle': 'pendle', 'hyndburn': 'hyndburn',
    'rossendale': 'rossendale', 'ribble_valley': 'ribble-valley',
    'blackburn': 'blackburn', 'blackpool': 'blackpool', 'chorley': 'chorley',
    'south_ribble': 'south-ribble', 'preston': 'preston',
    'west_lancashire': 'west-lancashire', 'lancaster': 'lancaster',
    'wyre': 'wyre', 'fylde': 'fylde', 'lancashire_cc': 'lancashire-wide',
}


def slugify(text, max_len=60):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:max_len].rsplit('-', 1)[0] if len(text) > max_len else text


def parse_astro_frontmatter(filepath):
    """Parse YAML frontmatter from Astro markdown file."""
    text = filepath.read_text()
    if not text.startswith('---'):
        return None, text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return None, text
    fm_text = parts[1].strip()
    body = parts[2].strip()
    # Simple YAML parser (avoid dependency)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            fm[key] = val
    return fm, body


def _make_article(headline, date, category, borough, source, source_url, score, tier, cross_project, summary, body):
    """Build an Astro markdown article string."""
    safe_hl = headline.replace('"', '\\"')
    safe_sum = summary[:200].replace('"', '\\"')
    slug = slugify(headline)
    slug_hash = hashlib.md5(headline.encode()).hexdigest()[:6]
    prefix = cross_project[:2] if cross_project else 'xp'
    filename = f"{date}-{prefix}-{slug}-{slug_hash}.md"
    md = f'---\nheadline: "{safe_hl}"\ndate: "{date}"\ncategory: "{category}"\nborough: "{borough}"\nsource: "{source}"\nsource_url: "{source_url}"\ninterest_score: {score}\ncontent_tier: "{tier}"\ncross_project: "{cross_project}"\nsummary: "{safe_sum}"\n---\n\n{body}\n'
    return filename, md


def cross_publish_lt():
    """Pull Labour Tracker investigations as NL cross-published articles."""
    articles = []

    # Try Astro markdown source
    inv_dir = LT_DIR / 'src' / 'content' / 'investigations'
    if inv_dir.exists():
        for md_file in sorted(inv_dir.glob('*.md')):
            fm, body = parse_astro_frontmatter(md_file)
            if not fm:
                continue
            headline = fm.get('headline', fm.get('title', md_file.stem))
            date = fm.get('date', datetime.now().strftime('%Y-%m-%d'))
            summary = fm.get('summary', body[:200])
            source_url = fm.get('source_url', 'https://labourtracker.co.uk')
            body_with_angle = f"*Originally published on [Labour Tracker](https://labourtracker.co.uk). Affects Lancashire residents through national policy.*\n\n{body}"
            filename, content = _make_article(headline, date, 'politics', 'lancashire-wide', 'Labour Tracker', source_url, 85, 'cross-publish', 'labour_tracker', summary, body_with_angle)
            articles.append((filename, content))
            log.info('LT [md]: %s', headline[:60])
        return articles

    # Fallback: JSON articles from data directory
    for subdir in ['articles', 'drafts']:
        json_dir = LT_DIR / subdir
        if not json_dir.exists():
            continue
        for jf in sorted(json_dir.glob('*.json')):
            if jf.name.endswith('-factcheck.json') or jf.name == 'articles-index.json':
                continue
            try:
                art = json.loads(jf.read_text())
            except (json.JSONDecodeError, IOError):
                continue
            if not isinstance(art, dict) or 'content' not in art:
                continue
            headline = art.get('title', jf.stem)
            date = art.get('date', datetime.now().strftime('%Y-%m-%d'))[:10]
            body = re.sub(r'<[^>]+>', '', art.get('content', ''))
            summary = body[:200]
            body_with_angle = f"*Originally published on [Labour Tracker](https://labourtracker.co.uk). Affects Lancashire residents through national policy.*\n\n{body}"
            filename, content = _make_article(headline, date, 'politics', 'lancashire-wide', 'Labour Tracker', 'https://labourtracker.co.uk', 85, 'cross-publish', 'labour_tracker', summary, body_with_angle)
            articles.append((filename, content))
            log.info('LT [json]: %s', headline[:60])

    # Also check article_opportunities.json for high-scoring leads
    opps_path = LT_DIR / 'article_opportunities.json'
    if opps_path.exists():
        try:
            data = json.loads(opps_path.read_text())
            opps = data.get('opportunities', []) if isinstance(data, dict) else data
            for o in opps:
                score = o.get('score', 0)
                if score < 70:
                    continue
                headline = o.get('headline_hook', 'Untitled')
                angle = o.get('angle', headline)
                body = f"*Planned investigation from [Labour Tracker](https://labourtracker.co.uk).*\n\n{angle}"
                filename, content = _make_article(headline, '2026-04-01', 'politics', 'lancashire-wide', 'Labour Tracker', 'https://labourtracker.co.uk', score, 'cross-publish', 'labour_tracker', angle[:200], body)
                articles.append((filename, content))
                log.info('LT [opp]: %s (score=%d)', headline[:50], score)
        except (json.JSONDecodeError, IOError):
            pass

    if not articles:
        log.info('No Labour Tracker articles found at %s', LT_DIR)

    return articles


def cross_publish_asylum():
    """Pull Asylum Stats findings as NL cross-published articles."""
    articles = []
    findings_dir = ASYLUM_DIR / 'src' / 'content' / 'findings'
    if not findings_dir.exists():
        log.warning('Asylum Stats not found at %s', findings_dir)
        return articles

    for md_file in sorted(findings_dir.glob('*.md')):
        fm, body = parse_astro_frontmatter(md_file)
        if not fm:
            continue

        headline = fm.get('headline', fm.get('title', md_file.stem.replace('-', ' ').title()))
        date = fm.get('date', datetime.now().strftime('%Y-%m-%d'))
        summary = fm.get('summary', body[:200])
        source_url = fm.get('source_url', 'https://asylumstats.co.uk')
        body_with_angle = f"*Originally published on [Asylum Stats](https://asylumstats.co.uk). Data includes Lancashire councils.*\n\n{body}"
        filename, content = _make_article(headline, date, 'data-driven', 'lancashire-wide', 'Asylum Stats', source_url, 80, 'cross-publish', 'asylum_stats', summary, body_with_angle)
        articles.append((filename, content))
        log.info('AS: %s', headline[:60])

    return articles


def cross_publish_doge():
    """Pull AI DOGE articles for Lancashire councils as NL cross-published."""
    articles = []
    if not DOGE_DATA_DIR.exists():
        log.warning('DOGE data not found at %s', DOGE_DATA_DIR)
        return articles

    for council in LANCASHIRE_COUNCILS:
        index_path = DOGE_DATA_DIR / council / 'articles-index.json'
        if not index_path.exists():
            continue
        try:
            data = json.loads(index_path.read_text())
            if not isinstance(data, list):
                continue
        except (json.JSONDecodeError, IOError):
            continue

        borough = COUNCIL_TO_BOROUGH.get(council, 'lancashire-wide')
        for art in data:
            title = art.get('title', '')
            if not title:
                continue
            article_id = art.get('id', slugify(title))

            # Content may be in index or in separate article file
            content_text = art.get('content', '')
            if not content_text or len(content_text) < 100:
                # Try loading full article file
                art_file = DOGE_DATA_DIR / council / 'articles' / f'{article_id}.json'
                if art_file.exists():
                    try:
                        full_art = json.loads(art_file.read_text())
                        content_text = full_art.get('content', '')
                    except (json.JSONDecodeError, IOError):
                        pass
            if not content_text or len(content_text) < 100:
                continue

            date = art.get('date', datetime.now().strftime('%Y-%m-%d'))
            plain_text = re.sub(r'<[^>]+>', '', content_text)
            summary = plain_text[:200]
            source_url = f"https://aidoge.co.uk/{council.replace('_', '')}council/"
            body = f"*Originally published on [AI DOGE](https://aidoge.co.uk). Covers {council.replace('_', ' ').title()} council spending.*\n\n{plain_text}"
            filename, md_content = _make_article(title, date, 'council', borough, 'AI DOGE', source_url, 75, 'cross-publish', 'aidoge', summary, body)
            articles.append((filename, md_content))
            log.info('DOGE [%s]: %s', council, title[:50])

    return articles


def main():
    parser = argparse.ArgumentParser(description='Cross-publish articles to News Lancashire')
    parser.add_argument('--source', choices=['lt', 'asylum', 'doge', 'all'], default='all')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--output', type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    all_articles = []
    if args.source in ('all', 'lt'):
        all_articles.extend(cross_publish_lt())
    if args.source in ('all', 'asylum'):
        all_articles.extend(cross_publish_asylum())
    if args.source in ('all', 'doge'):
        all_articles.extend(cross_publish_doge())

    log.info('Total cross-publish articles: %d', len(all_articles))

    if args.dry_run:
        for filename, _ in all_articles:
            log.info('  Would write: %s', filename)
        return

    written = 0
    for filename, content in all_articles:
        filepath = output / filename
        filepath.write_text(content)
        written += 1

    log.info('Written %d cross-published articles to %s', written, output)


if __name__ == '__main__':
    main()
