#!/usr/bin/env python3
"""AI Analyzer - Deep analysis for high-interest articles via Kimi K2.5.
Only processes articles with interest_score >= 60. One article per API call."""

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

KIMI_API_URL = 'https://api.moonshot.ai/v1/chat/completions'
KIMI_API_KEY = os.environ.get('MOONSHOT_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

INTEREST_THRESHOLD = 60  # Only analyze articles scoring 60+
MAX_PER_RUN = 30  # Max analyses per pipeline run (credit efficiency)

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/ai_analyzer.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('ai_analyzer')


ANALYSIS_PROMPT = """You are a senior local news analyst for News Lancashire, covering Lancashire, England. Write a 150-250 word analysis of this news article.

Rules:
- Objective, fact-based, concise — quality journalism
- Present all political perspectives fairly and without favour
- When covering public spending: highlight value-for-money, accountability, whether taxpayers are getting a fair deal
- When covering governance: emphasise transparency, democratic scrutiny, whether proper process was followed
- When covering any political party or figure: provide balanced context, note their stated positions, and report factually without editorial slant
- Include context a Lancashire resident needs to understand why this matters locally
- End with a forward-looking sentence about what happens next or what to watch for
- Do NOT repeat the headline — go straight into the analysis
- Write as flowing prose, not bullet points
- Vary your sentence openings — never start consecutive sentences the same way
- Write as a knowledgeable local journalist would, with natural voice and authority

Article title: {title}
Article summary: {summary}
Source: {source}
Category: {category}

Write your analysis:"""


def api_call(url, api_key, model, prompt, timeout=120):
    """Make an API call."""
    # Kimi K2.5 only supports temperature=1
    temp = 0.7 if 'kimi' in model else 0.4
    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': temp,
        'max_tokens': 600,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
        return data['choices'][0]['message']['content'].strip()


def analyze_article(title, summary, source, category):
    """Generate deep analysis for a single article."""
    prompt = ANALYSIS_PROMPT.format(
        title=title,
        summary=summary or '(no detailed summary available)',
        source=source,
        category=category
    )

    # Try Kimi first
    if KIMI_API_KEY:
        try:
            result = api_call(KIMI_API_URL, KIMI_API_KEY, 'kimi-latest', prompt)
            if result and len(result) > 50:
                return result
        except Exception as ex:
            log.error('Kimi API error: %s', ex)

    # Fallback to DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            result = api_call(DEEPSEEK_API_URL, DEEPSEEK_API_KEY, 'deepseek-chat', prompt)
            if result and len(result) > 50:
                return result
        except Exception as ex:
            log.error('DeepSeek API error: %s', ex)

    return None


def run():
    log.info('=== AI Analyzer started ===')

    if not KIMI_API_KEY and not DEEPSEEK_API_KEY:
        log.error('No API keys set. Set MOONSHOT_API_KEY or DEEPSEEK_API_KEY.')
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')

    # Get high-interest articles without analysis
    c = conn.execute("""
        SELECT id, title, summary, source, category, interest_score
        FROM articles
        WHERE ai_analysis IS NULL
          AND interest_score >= ?
          AND ai_rewrite IS NOT NULL
          AND content_tier = 'aggregated'
        ORDER BY interest_score DESC, trending_score DESC
        LIMIT ?
    """, (INTEREST_THRESHOLD, MAX_PER_RUN))

    articles = c.fetchall()
    if not articles:
        log.info('No high-interest articles to analyze')
        conn.close()
        return

    log.info('Found %d high-interest articles for analysis', len(articles))
    analyzed = 0

    for aid, title, summary, source, category, score in articles:
        log.info('Analyzing: [%d] %s', score, title[:60])

        analysis = analyze_article(title, summary, source, category)

        if analysis:
            conn.execute(
                "UPDATE articles SET ai_analysis = ?, content_tier = 'analysis' WHERE id = ?",
                (analysis, aid)
            )
            conn.commit()
            analyzed += 1
            log.info('  → Analysis written (%d words)', len(analysis.split()))
        else:
            log.warning('  → Analysis failed for: %s', title[:40])

        time.sleep(3)  # Rate limit — one at a time

    log.info('=== AI Analyzer done: %d/%d articles analyzed ===', analyzed, len(articles))
    conn.close()


if __name__ == '__main__':
    run()
