#!/usr/bin/env python3
"""AI Rewriter - Batch rewrite article summaries via Kimi K2.5 (free tier).
Sends 10 articles per API call for efficiency. Fallback: DeepSeek V3."""

import sqlite3
import json
import os
import time
import logging
import urllib.request
import urllib.error

BASE = '/home/ubuntu/newslancashire'
DB_PATH = f'{BASE}/db/news.db'
LOG_DIR = f'{BASE}/logs'

# API endpoints and keys (from OpenClaw config)
KIMI_API_URL = 'https://api.moonshot.ai/v1/chat/completions'
KIMI_API_KEY = os.environ.get('MOONSHOT_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

BATCH_SIZE = 5   # Articles per API call (smaller = more reliable)
MAX_BATCHES = 10  # Max batches per run (50 articles)
MAX_RETRIES = 2
API_TIMEOUT = 120  # Seconds per API call

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/ai_rewriter.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('ai_rewriter')


REWRITE_PROMPT = """You are a concise local news editor for Lancashire, England. Rewrite each article's summary into 2-3 original sentences.

Rules:
- Factual, clear, objective
- Original wording (never copy the source text)
- Include the local angle — why this matters to Lancashire residents
- Keep it under 80 words per article
- Present facts without sensationalism
- If the summary is too vague, write what you can from the title

For each article, respond with ONLY the rewritten text. Separate each article's rewrite with "---" on its own line.

Articles to rewrite:
"""


def api_call(url, api_key, model, prompt, timeout=API_TIMEOUT):
    """Make an API call to Kimi or DeepSeek."""
    # Kimi K2.5 only supports temperature=1
    temp = 1.0 if 'kimi' in model else 0.3
    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': temp,
        'max_tokens': 2000,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
        return data['choices'][0]['message']['content'].strip()


def rewrite_batch(articles):
    """Send a batch of articles to be rewritten. Returns list of rewrites."""
    # Build prompt with numbered articles
    prompt = REWRITE_PROMPT
    for i, (aid, title, summary) in enumerate(articles, 1):
        prompt += f"\n{i}. Title: {title}\n   Summary: {summary or '(no summary)'}\n"

    # Try Kimi first
    if KIMI_API_KEY:
        try:
            log.info('Calling Kimi K2.5 for %d articles', len(articles))
            result = api_call(KIMI_API_URL, KIMI_API_KEY, 'kimi-k2.5', prompt)
            rewrites = [r.strip() for r in result.split('---') if r.strip()]
            if len(rewrites) >= len(articles):
                return rewrites[:len(articles)]
            elif rewrites:
                log.warning('Kimi returned %d rewrites for %d articles', len(rewrites), len(articles))
                # Pad with empty strings
                while len(rewrites) < len(articles):
                    rewrites.append('')
                return rewrites
        except Exception as ex:
            log.error('Kimi API error: %s', ex)

    # Fallback to DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            log.info('Falling back to DeepSeek V3 for %d articles', len(articles))
            result = api_call(DEEPSEEK_API_URL, DEEPSEEK_API_KEY, 'deepseek-chat', prompt)
            rewrites = [r.strip() for r in result.split('---') if r.strip()]
            if len(rewrites) >= len(articles):
                return rewrites[:len(articles)]
            elif rewrites:
                while len(rewrites) < len(articles):
                    rewrites.append('')
                return rewrites
        except Exception as ex:
            log.error('DeepSeek API error: %s', ex)

    log.error('No API keys available or all APIs failed')
    return []


def run():
    log.info('=== AI Rewriter started ===')

    if not KIMI_API_KEY and not DEEPSEEK_API_KEY:
        log.error('No API keys set. Set MOONSHOT_API_KEY or DEEPSEEK_API_KEY.')
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')

    # Get unprocessed articles (no ai_rewrite yet)
    c = conn.execute("""
        SELECT id, title, summary FROM articles
        WHERE ai_rewrite IS NULL
          AND content_tier = 'aggregated'
        ORDER BY interest_score DESC, fetched_at DESC
        LIMIT ?
    """, (BATCH_SIZE * MAX_BATCHES,))

    all_articles = c.fetchall()
    if not all_articles:
        log.info('No articles to rewrite')
        conn.close()
        return

    log.info('Found %d articles to rewrite', len(all_articles))
    total_rewritten = 0

    # Process in batches
    for i in range(0, len(all_articles), BATCH_SIZE):
        batch = all_articles[i:i + BATCH_SIZE]
        rewrites = rewrite_batch(batch)

        if not rewrites:
            log.warning('Batch %d failed — skipping', i // BATCH_SIZE + 1)
            continue

        for (aid, title, _), rewrite in zip(batch, rewrites):
            if rewrite:
                conn.execute(
                    'UPDATE articles SET ai_rewrite = ? WHERE id = ?',
                    (rewrite, aid)
                )
                total_rewritten += 1

        conn.commit()
        log.info('Batch %d: rewritten %d/%d', i // BATCH_SIZE + 1, len(rewrites), len(batch))

        # Rate limit between batches
        time.sleep(2)

    log.info('=== AI Rewriter done: %d articles rewritten ===', total_rewritten)
    conn.close()


if __name__ == '__main__':
    run()
