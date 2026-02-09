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
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_rate_limiter import can_use, record_usage, get_daily_summary

BASE = '/home/ubuntu/newslancashire'
DB_PATH = f'{BASE}/db/news.db'
LOG_DIR = f'{BASE}/logs'

# API endpoints and keys (from OpenClaw config)
KIMI_API_URL = 'https://api.moonshot.ai/v1/chat/completions'
KIMI_API_KEY = os.environ.get('MOONSHOT_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# Free tier providers (primary)
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

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
        content = data['choices'][0]['message']['content'].strip()
        # Estimate tokens used (prompt + completion)
        tokens = data.get('usage', {}).get('total_tokens', 0)
        if not tokens:
            tokens = len(prompt) // 4 + len(content) // 4  # rough estimate
        return content, tokens


def rewrite_batch(articles):
    """Send a batch of articles to be rewritten. Returns list of rewrites."""
    # Build prompt with numbered articles
    prompt = REWRITE_PROMPT
    for i, (aid, title, summary) in enumerate(articles, 1):
        prompt += f"\n{i}. Title: {title}\n   Summary: {summary or '(no summary)'}\n"

    # Fallback chain: Gemini → Groq → Kimi → DeepSeek (with rate limiting)
    providers = []
    if GEMINI_API_KEY and can_use('gemini'):
        providers.append(('gemini', 'Gemini 2.5 Flash', GEMINI_API_URL, GEMINI_API_KEY, 'gemini-2.5-flash'))
    if GROQ_API_KEY and can_use('groq'):
        providers.append(('groq', 'Groq Llama 3.3 70B', GROQ_API_URL, GROQ_API_KEY, 'llama-3.3-70b-versatile'))
    if KIMI_API_KEY and can_use('kimi'):
        providers.append(('kimi', 'Kimi K2.5', KIMI_API_URL, KIMI_API_KEY, 'kimi-k2.5'))
    if DEEPSEEK_API_KEY and can_use('deepseek'):
        providers.append(('deepseek', 'DeepSeek V3', DEEPSEEK_API_URL, DEEPSEEK_API_KEY, 'deepseek-chat'))

    for prov_id, name, url, key, model in providers:
        try:
            log.info('Calling %s for %d articles', name, len(articles))
            result, tokens = api_call(url, key, model, prompt)
            record_usage(prov_id, tokens)
            rewrites = [r.strip() for r in result.split('---') if r.strip()]
            if len(rewrites) >= len(articles):
                return rewrites[:len(articles)]
            elif rewrites:
                log.warning('%s returned %d rewrites for %d articles', name, len(rewrites), len(articles))
                while len(rewrites) < len(articles):
                    rewrites.append('')
                return rewrites
        except urllib.error.HTTPError as ex:
            if ex.code == 400:
                try:
                    body = ex.read().decode()
                except Exception:
                    body = ''
                if 'content_filter' in body or 'high risk' in body:
                    log.warning('%s content filter — trying articles individually', name)
                    individual_rewrites = []
                    for (aid, title, summary) in articles:
                        single_prompt = REWRITE_PROMPT
                        single_prompt += '\n1. Title: ' + title
                        single_prompt += '\n   Summary: ' + (summary or '(no summary)') + '\n'
                        try:
                            r, t = api_call(url, key, model, single_prompt)
                            record_usage(prov_id, t)
                            individual_rewrites.append(r.strip().replace('---', '').strip())
                        except Exception:
                            log.warning('Content filter: skipping %s (%s)', aid[:12], title[:40])
                            individual_rewrites.append('')
                    if any(r for r in individual_rewrites):
                        return individual_rewrites
                else:
                    log.error('%s API 400 error: %s', name, body[:200])
            elif ex.code == 402:
                log.warning('%s credits exhausted (402) — trying next provider', name)
            elif ex.code == 429:
                log.warning('%s rate limited (429) — trying next provider', name)
            else:
                log.error('%s API error: HTTP %d %s', name, ex.code, ex.reason)
        except Exception as ex:
            log.error('%s API error: %s', name, ex)

    log.error('All LLM providers failed or rate-limited')
    return []


def run():
    log.info('=== AI Rewriter started ===')

    if not any([GEMINI_API_KEY, GROQ_API_KEY, KIMI_API_KEY, DEEPSEEK_API_KEY]):
        log.error('No API keys set. Set GEMINI_API_KEY, GROQ_API_KEY, MOONSHOT_API_KEY, or DEEPSEEK_API_KEY.')
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
    log.info(get_daily_summary())


if __name__ == '__main__':
    run()
