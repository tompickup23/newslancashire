#!/usr/bin/env python3
"""
article_engine.py — Two-pass article rewriter for News Lancashire.

Pass 1 (Gemini Flash): Extract facts, structure, attribution from raw summary
Pass 2 (Gemini Pro / Mistral): Apply local news voice, add Lancashire context

Quality gate:
  - interest_score >= 70: full two-pass rewrite (content_tier = "analysis")
  - interest_score 40-69: single-pass clean summary (content_tier = "summary")
  - interest_score < 40: skip entirely

Usage:
    python3 article_engine.py                   # Process all pending
    python3 article_engine.py --max 10          # Limit articles
    python3 article_engine.py --dry-run         # Show what would be processed
    python3 article_engine.py --reprocess       # Re-run on already processed articles
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path('/home/ubuntu/newslancashire')
DB_PATH = BASE / 'db' / 'news.db'
LOG_DIR = BASE / 'logs'
STYLE_GUIDE_PATH = Path(__file__).parent / 'nl_style_guide.json'

# Load .env
_env_file = BASE / '.env'
if _env_file.is_file():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'article_engine.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('article_engine')

# Rate limiting
sys.path.insert(0, str(BASE / 'scripts'))
try:
    from llm_rate_limiter import can_use, record_usage
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False
    def can_use(p): return True
    def record_usage(p, t): pass


def load_style_guide():
    try:
        with open(STYLE_GUIDE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def llm_call(model, prompt, temperature=0.3, timeout=120):
    """Call OpenAI-compatible API. Returns (text, tokens_used)."""
    if 'gemini' in model:
        url = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
        api_key = GEMINI_API_KEY
    else:
        url = 'https://api.mistral.ai/v1/chat/completions'
        api_key = MISTRAL_API_KEY

    if not api_key:
        raise ValueError(f'No API key for {model}')

    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': temperature,
        'max_tokens': 2000,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
        content = data['choices'][0]['message']['content'].strip()
        tokens = data.get('usage', {}).get('total_tokens', 0)
        if not tokens:
            tokens = len(prompt) // 4 + len(content) // 4
        return content, tokens


def pass1_extract(title, summary, source):
    """Pass 1: Extract structured facts from raw article."""
    prompt = f"""You are a news analyst for Lancashire, England. Extract the key facts from this article.

Title: {title}
Source: {source}
Summary: {summary or '(no summary available)'}

Return a JSON object with:
- "who": main people/organisations involved
- "what": what happened (one sentence)
- "where": location in Lancashire (be specific: town, borough)
- "when": when it happened (date or timeframe)
- "why": why it matters to local residents
- "figures": any numbers, amounts, percentages mentioned
- "category": one of: local, crime, politics, health, education, transport, planning, environment, business, sport, council
- "interest_score": 0-100 how interesting/important this is to Lancashire readers

Return ONLY valid JSON, no markdown formatting."""

    providers = []
    if GEMINI_API_KEY and can_use('gemini'):
        providers.append(('gemini', 'gemini-2.5-flash'))
    if MISTRAL_API_KEY and can_use('mistral'):
        providers.append(('mistral', 'mistral-small-latest'))

    for prov_id, model in providers:
        try:
            result, tokens = llm_call(model, prompt, temperature=0.1)
            record_usage(prov_id, tokens)
            # Strip markdown code fences if present
            result = result.strip()
            if result.startswith('```'):
                result = result.split('\n', 1)[1] if '\n' in result else result[3:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
            if result.startswith('json'):
                result = result[4:].strip()
            return json.loads(result)
        except Exception as e:
            log.warning('Pass 1 failed with %s: %s', model, e)
            continue

    return None


def pass2_rewrite(title, summary, facts, style_guide, tier='analysis'):
    """Pass 2: Rewrite article in local news voice."""
    guide = style_guide or {}
    rules = '\n'.join(f'- {r}' for r in guide.get('rules', []))
    banned = ', '.join(guide.get('banned_patterns', [])[:15])

    tier_config = guide.get('content_tiers', {}).get(tier, {})
    word_min = tier_config.get('word_range', [60, 120])[0]
    word_max = tier_config.get('word_range', [60, 120])[1]

    facts_str = json.dumps(facts, indent=2) if facts else '(no structured facts available)'

    prompt = f"""You are a local news writer for News Lancashire (newslancashire.co.uk).
Rewrite this article for Lancashire readers.

Title: {title}
Original summary: {summary or '(no summary)'}
Extracted facts: {facts_str}

Writing rules:
{rules}

NEVER use these phrases: {banned}

Target length: {word_min}-{word_max} words.
Write in plain text (no HTML, no markdown headers).
Start with the news — no preamble.
End with practical information if relevant (dates, contact details, locations).
"""

    # Prefer Gemini Pro for analysis tier, Flash for summaries
    providers = []
    if tier == 'analysis':
        if GEMINI_API_KEY and can_use('gemini'):
            providers.append(('gemini', 'gemini-2.5-flash'))
        if MISTRAL_API_KEY and can_use('mistral'):
            providers.append(('mistral', 'mistral-small-latest'))
    else:
        if GEMINI_API_KEY and can_use('gemini'):
            providers.append(('gemini', 'gemini-2.5-flash'))
        if MISTRAL_API_KEY and can_use('mistral'):
            providers.append(('mistral', 'mistral-small-latest'))

    for prov_id, model in providers:
        try:
            result, tokens = llm_call(model, prompt, temperature=0.4)
            record_usage(prov_id, tokens)
            return result
        except Exception as e:
            log.warning('Pass 2 failed with %s: %s', model, e)
            continue

    return None


def ensure_columns(conn):
    """Add columns if they don't exist."""
    for col, typedef in [
        ('two_pass_rewrite', 'TEXT'),
        ('fact_check_score', 'INTEGER DEFAULT 0'),
        ('extracted_facts', 'TEXT'),
        ('engine_version', 'TEXT'),
    ]:
        try:
            conn.execute(f'ALTER TABLE articles ADD COLUMN {col} {typedef}')
            log.info('Added column: %s', col)
        except sqlite3.OperationalError:
            pass  # Column already exists


def get_pending_articles(conn, max_articles=50, reprocess=False):
    """Get articles needing two-pass processing."""
    if reprocess:
        query = """
            SELECT id, title, summary, source, interest_score, category
            FROM articles
            WHERE interest_score >= 40
            ORDER BY interest_score DESC, published DESC
            LIMIT ?
        """
    else:
        query = """
            SELECT id, title, summary, source, interest_score, category
            FROM articles
            WHERE interest_score >= 40
              AND (two_pass_rewrite IS NULL OR two_pass_rewrite = '')
            ORDER BY interest_score DESC, published DESC
            LIMIT ?
        """
    return conn.execute(query, (max_articles,)).fetchall()


def process_article(conn, article, style_guide):
    """Process a single article through the two-pass engine."""
    aid, title, summary, source, score, category = article

    if score >= 70:
        tier = 'analysis'
    else:
        tier = 'summary'

    log.info('Processing [%s] score=%d tier=%s: %s', aid[:8], score, tier, title[:60])

    # Pass 1: Extract facts
    facts = pass1_extract(title, summary, source)
    if not facts:
        log.warning('Pass 1 failed for %s, falling back to single-pass', aid[:8])
        facts = {}

    # Update interest score from LLM if available
    llm_score = facts.get('interest_score')
    if llm_score and isinstance(llm_score, (int, float)):
        # Average with existing score
        new_score = int((score + llm_score) / 2)
        if new_score < 40:
            log.info('LLM scored %s at %d (below threshold), skipping', aid[:8], new_score)
            conn.execute(
                'UPDATE articles SET interest_score = ?, extracted_facts = ? WHERE id = ?',
                (new_score, json.dumps(facts), aid)
            )
            return False

    # Update category from LLM if we have a mapping
    llm_category = facts.get('category', '')
    cat_map = style_guide.get('category_map', {})
    if llm_category and llm_category in cat_map.values():
        category = llm_category
    elif llm_category and llm_category in cat_map:
        category = cat_map[llm_category]

    time.sleep(2)  # Rate limit between API calls

    # Pass 2: Rewrite in local news voice
    rewrite = pass2_rewrite(title, summary, facts, style_guide, tier)
    if not rewrite:
        log.warning('Pass 2 failed for %s', aid[:8])
        return False

    # Update DB
    conn.execute(
        '''UPDATE articles SET
            two_pass_rewrite = ?,
            extracted_facts = ?,
            category = ?,
            content_tier = ?,
            engine_version = ?
        WHERE id = ?''',
        (rewrite, json.dumps(facts), category, tier, 'engine-v1.0', aid)
    )

    log.info('OK [%s] %s -> %d words', aid[:8], tier, len(rewrite.split()))
    return True


def main():
    parser = argparse.ArgumentParser(description='News Lancashire two-pass article engine')
    parser.add_argument('--max', type=int, default=20, help='Max articles to process')
    parser.add_argument('--dry-run', action='store_true', help='Show pending without processing')
    parser.add_argument('--reprocess', action='store_true', help='Re-run on already processed')
    args = parser.parse_args()

    style_guide = load_style_guide()
    conn = sqlite3.connect(str(DB_PATH))
    ensure_columns(conn)
    conn.commit()

    articles = get_pending_articles(conn, args.max, args.reprocess)
    log.info('Found %d articles to process (max=%d)', len(articles), args.max)

    if args.dry_run:
        for a in articles:
            log.info('  [%s] score=%d cat=%s: %s', a[0][:8], a[4], a[5], a[1][:60])
        conn.close()
        return

    processed = 0
    for article in articles:
        try:
            if process_article(conn, article, style_guide):
                processed += 1
                conn.commit()
            time.sleep(3)  # Rate limit between articles
        except Exception as e:
            log.error('Error processing %s: %s', article[0][:8], e)
            continue

    conn.commit()
    conn.close()
    log.info('Done. Processed %d/%d articles', processed, len(articles))


if __name__ == '__main__':
    main()
