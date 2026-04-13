#!/usr/bin/env python3
"""
weekly_newsletter.py — Generate a weekly digest email for News Lancashire.

Selects the top articles from the past 7 days, formats them into an HTML email,
and sends via Cloudflare Email Workers (or SMTP fallback).

Usage:
    python3 weekly_newsletter.py                    # Generate + send
    python3 weekly_newsletter.py --preview          # Generate HTML preview only
    python3 weekly_newsletter.py --dry-run          # Show what would be included
"""

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

NL_PIPELINE_DIR = Path(os.environ.get('NL_PIPELINE_DIR', '/root/newslancashire-pipeline'))
DB_PATH = NL_PIPELINE_DIR / 'db' / 'news.db'
LOG_DIR = NL_PIPELINE_DIR / 'logs'
OUTPUT_DIR = NL_PIPELINE_DIR / 'newsletters'

LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'newsletter.log'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('newsletter')

BOROUGH_MAP = {
    'is_burnley': 'Burnley', 'is_pendle': 'Pendle', 'is_hyndburn': 'Hyndburn',
    'is_rossendale': 'Rossendale', 'is_ribble_valley': 'Ribble Valley',
    'is_blackburn': 'Blackburn', 'is_blackpool': 'Blackpool',
    'is_chorley': 'Chorley', 'is_south_ribble': 'South Ribble',
    'is_preston': 'Preston', 'is_west_lancashire': 'West Lancashire',
    'is_lancaster': 'Lancaster', 'is_wyre': 'Wyre', 'is_fylde': 'Fylde',
    'is_lancashire_cc': 'Lancashire',
}


def get_week_articles(max_articles=15):
    """Get top articles from the past 7 days."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    rows = conn.execute("""
        SELECT id, title, source, published, category, interest_score,
               COALESCE(two_pass_rewrite, ai_rewrite, summary) as content,
               is_burnley, is_pendle, is_hyndburn, is_rossendale, is_blackburn,
               is_blackpool, is_preston, is_lancaster, is_chorley, is_south_ribble,
               is_west_lancashire, is_wyre, is_fylde, is_lancashire_cc
        FROM articles
        WHERE published >= ?
          AND interest_score >= 50
          AND (ai_rewrite IS NOT NULL AND ai_rewrite != '')
        ORDER BY interest_score DESC, published DESC
        LIMIT ?
    """, (since, max_articles)).fetchall()

    articles = []
    for row in rows:
        r = dict(row)
        borough = 'Lancashire'
        for col, name in BOROUGH_MAP.items():
            if r.get(col, 0) == 1:
                borough = name
                break
        summary = (r.get('content') or '')[:200]
        if len(summary) >= 200:
            summary = summary.rsplit(' ', 1)[0] + '...'
        articles.append({
            'title': r.get('title', '')[:120],
            'borough': borough,
            'category': r.get('category', 'local'),
            'score': r.get('interest_score', 0),
            'summary': summary,
            'date': (r.get('published') or '')[:10],
        })
    conn.close()
    return articles


def generate_html(articles, week_start, week_end):
    """Generate newsletter HTML."""
    article_blocks = []
    for i, a in enumerate(articles):
        bg = '#1a1a2e' if i % 2 == 0 else '#16213e'
        article_blocks.append(f'''
        <tr><td style="padding:16px 24px;background:{bg};border-radius:8px;margin-bottom:8px">
          <div style="font-size:11px;color:#3b82f6;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">{a["borough"]} | {a["category"]}</div>
          <div style="font-size:16px;font-weight:700;color:#e2e8f0;line-height:1.3;margin-bottom:6px">{a["title"]}</div>
          <div style="font-size:13px;color:#94a3b8;line-height:1.5">{a["summary"]}</div>
        </td></tr>
        <tr><td style="height:8px"></td></tr>''')

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#0f172a">
  <tr><td style="padding:32px 24px;text-align:center;border-bottom:2px solid #3b82f6">
    <div style="font-size:24px;font-weight:800;color:#f8fafc;letter-spacing:-0.5px">NEWS LANCASHIRE</div>
    <div style="font-size:12px;color:#64748b;margin-top:4px">Weekly Digest | {week_start} - {week_end}</div>
  </td></tr>
  <tr><td style="padding:24px 24px 8px">
    <div style="font-size:14px;color:#cbd5e1;margin-bottom:16px">This week's top {len(articles)} stories from across Lancashire.</div>
  </td></tr>
  {''.join(article_blocks)}
  <tr><td style="padding:24px;text-align:center;border-top:1px solid #1e293b">
    <div style="font-size:11px;color:#475569">
      <a href="https://newslancashire.co.uk" style="color:#3b82f6;text-decoration:none">newslancashire.co.uk</a> | Independent Local News<br>
      <a href="https://newslancashire.co.uk/newsletter/unsubscribe" style="color:#475569;text-decoration:underline;font-size:10px">Unsubscribe</a>
    </div>
  </td></tr>
</table>
</body></html>'''


def main():
    parser = argparse.ArgumentParser(description='News Lancashire weekly newsletter')
    parser.add_argument('--preview', action='store_true', help='Save HTML preview')
    parser.add_argument('--dry-run', action='store_true', help='Show articles only')
    parser.add_argument('--max', type=int, default=15, help='Max articles')
    args = parser.parse_args()

    articles = get_week_articles(args.max)
    log.info('Found %d articles for newsletter', len(articles))

    if args.dry_run:
        for a in articles:
            log.info('  [%d] %s | %s: %s', a['score'], a['borough'], a['category'], a['title'][:60])
        return

    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime('%d %b')
    week_end = now.strftime('%d %b %Y')
    html = generate_html(articles, week_start, week_end)

    if args.preview:
        preview_path = OUTPUT_DIR / f'newsletter-{now.strftime("%Y-%m-%d")}.html'
        preview_path.write_text(html)
        log.info('Preview saved to %s', preview_path)
        return

    # Save the newsletter
    newsletter_path = OUTPUT_DIR / f'newsletter-{now.strftime("%Y-%m-%d")}.html'
    newsletter_path.write_text(html)
    log.info('Newsletter saved to %s (%d articles)', newsletter_path, len(articles))
    log.info('Email sending not yet configured — use CF Email Workers or SMTP')


if __name__ == '__main__':
    main()
