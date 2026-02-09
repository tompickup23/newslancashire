# News Lancashire — Claude Code Project Guide

## What This Is

Automated local news pipeline for Lancashire, England. Crawls RSS, Bluesky, Google News every 30 minutes. AI rewrites and analyses articles. Deploys to Cloudflare Pages.

**Live sites:**
- newsburnley.co.uk — Burnley news (LIVE, Cloudflare Pages)
- newslancashire.co.uk — All boroughs (DEPLOY BROKEN — serves stale cache)

**Server:** vps-news (Oracle, 1GB RAM, free tier)
**Database:** SQLite, 787 articles, 655 exported
**AI:** Kimi K2.5 → DeepSeek fallback (keys in .env)

## File Structure

```
~/newslancashire/
├── pipeline_v4.sh          # Main pipeline (cron */30)
├── .env                    # API keys (gitignored)
├── CLAUDE.md               # This file
├── db/news.db              # SQLite database
├── export/                 # Generated JSON
├── scripts/
│   ├── crawler_v3.py       # Core crawler (RSS + Bluesky)
│   ├── ai_rewriter.py      # Batch AI rewrites
│   ├── ai_analyzer.py      # Deep analysis (interest >= 60)
│   ├── export_json.py      # DB → JSON export
│   ├── enhanced_sources/   # 16+ extra scrapers
│   ├── planning/           # DISABLED
│   └── council_minutes/    # DISABLED
├── config/
│   ├── feeds.json          # RSS feeds + Bluesky accounts
│   └── categories.json     # Category detection keywords
├── site/                   # Hugo site (disconnected)
└── logs/                   # All logs
```

## Critical Rules

1. **Never edit news.db directly** — use scripts or sqlite3 CLI
2. **Never commit .env** — contains API keys
3. **.env must be sourced** before running AI scripts manually
4. **Pipeline runs every 30 min** — don't run long-running processes that compete for RAM
5. **1GB RAM limit** — vps-news is memory-constrained, don't install heavy services
6. **export/articles.json is generated** — don't edit, run export_json.py instead

## Key Commands

```bash
# Check pipeline status
tail -20 logs/pipeline.log

# Run full pipeline manually
bash pipeline_v4.sh

# Run just the crawler
python3 scripts/crawler_v3.py

# Run AI rewriter (needs .env sourced)
source .env && python3 scripts/ai_rewriter.py

# Run AI analyzer
source .env && python3 scripts/ai_analyzer.py

# Export articles to JSON
python3 scripts/export_json.py

# Quick DB stats
sqlite3 db/news.db "SELECT COUNT(*), COUNT(ai_rewrite), COUNT(ai_analysis) FROM articles"

# Recent articles
sqlite3 db/news.db "SELECT title, source, interest_score FROM articles ORDER BY fetched_at DESC LIMIT 10"

# Check for truncated rewrites
sqlite3 db/news.db "SELECT COUNT(*) FROM articles WHERE LENGTH(ai_rewrite) = 500"
```

## Pipeline Phases

| Phase | Script | Notes |
|-------|--------|-------|
| 1 | crawler_v3.py | RSS + Bluesky |
| 2 | 16 enhanced sources | All non-critical (|| true equivalent) |
| 3 | ai_digest_generator.py | AI roundups |
| 4 | DISABLED | Planning scraper (broken) |
| 5 | DISABLED | Council minutes (broken) |
| 6 | weekly_digest.py | Mondays only |
| 7 | ai_rewriter.py + ai_analyzer.py | AI processing |
| 8 | export_json.py | DB → JSON |
| 9 | news_burnley_sync.py | → Cloudflare Pages |

## Database Schema

```sql
articles: id, title, link, source, source_type, published, summary,
  ai_rewrite, ai_analysis, content_tier, category,
  interest_score, trending_score,
  is_burnley, is_pendle, is_rossendale, is_hyndburn,
  is_ribble_valley, is_blackburn, is_chorley, is_south_ribble,
  is_preston, is_west_lancashire, is_lancaster, is_wyre,
  is_fylde, is_blackpool, fetched_at
```

## Known Issues

- newslancashire.co.uk deploy is broken (Astro dir deleted, need new frontend)
- 25% of articles have no borough assigned (keyword detection too narrow)
- 39% of articles have zero interest score (need baseline scoring)
- 43 AI rewrites truncated at 500 chars (need higher max_tokens)
- Rewriter batches 5 articles per call (should be 1 for quality)
- Planning + council minutes scrapers disabled (endpoints broken)

## AI Writing Config

**Rewriter:** 5 articles per API call, max 50/run, max_tokens ~167 per article
**Analyzer:** 1 article per call, max 30/run, max_tokens 600, interest >= 60 only

## Costs

Zero. Oracle free tier server. Kimi K2.5 free API. DeepSeek cheap fallback.
