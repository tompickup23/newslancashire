# Influencer Monitor - Best Practice Architecture

## Why Separate Module?

**Problem:** 60+ social accounts across 4 platforms with different:
- API rate limits (X: 450/15min, Bluesky: 3000/15min)
- Authentication methods
- Response formats
- Priority levels

**Solution:** Modular enhanced source (following pipeline_v4.sh pattern)

## Architecture

```
newslancashire/
├── config/
│   ├── feeds.json           # RSS feeds (fast, reliable)
│   ├── social.json          # Legacy social config
│   └── lancashire_influencers.json  # NEW: 60+ accounts
├── scripts/
│   ├── crawler_v3.py        # RSS crawler (every 30 min)
│   ├── social_crawler.py    # Existing social
│   └── enhanced_sources/
│       ├── business_monitor.py
│       ├── reddit_monitor.py
│       └── influencer_monitor.py   # NEW: This module
├── db/
│   └── influencer_cache.db  # SQLite: rate limits + content cache
└── data/
    └── influencer_content.json  # Output for Hugo
```

## Key Features

### 1. Rate Limiting
```python
RATE_LIMITS = {
    "x": 450,        # 15 min window
    "bluesky": 3000,
    "instagram": 200,
    "tiktok": 200
}
```
- SQLite tracks API calls
- Auto-skips when limit hit
- Prevents account bans

### 2. Priority Queuing
```python
priorities = ["critical", "high", "medium", "low"]

# Critical: Football clubs (every run)
# High: Major celebs (every run)
# Medium: Others (every 2nd run)
# Low: Niche (daily only)
```

### 3. Caching
- 6-hour content cache
- Avoids duplicate API calls
- SQLite persistence
- Reduces API usage by ~70%

### 4. Async-Friendly
- Non-blocking (other crawlers continue)
- Individual account failures don't crash pipeline
- Retry logic per platform

## Integration

### Option A: Full Integration (Recommended)
Add to `pipeline_v4.sh`:
```bash
# Phase 2b: Influencer monitoring
python3 scripts/enhanced_sources/influencer_monitor.py >> "$LOG" 2>&1 || true
```

Runs every 30 minutes with main pipeline.

### Option B: Separate Schedule
Create `influencer_cron.sh`:
```bash
#!/bin/bash
# Run every 2 hours for medium/low priority
0 */2 * * * /home/ubuntu/newslancashire/scripts/enhanced_sources/influencer_monitor.py
```

### Option C: On-Demand
Manual trigger:
```bash
python3 scripts/enhanced_sources/influencer_monitor.py
```

## API Tokens Required

| Platform | Token Type | Where to Get | Free Tier |
|----------|------------|--------------|-----------|
| X | Bearer Token | developer.twitter.com | 500 posts/month |
| Bluesky | None (public) | public.api.bsky.app | Unlimited |
| Instagram | Basic Display | developers.facebook.com | 200/hour |
| TikTok | Research API | developers.tiktok.com | Limited |

**Recommendation:** Start with Bluesky (free, no auth) + X (bearer token)

## Storage

**Cache DB:** `~/.sqlite3/influencer_cache.db`
- Table: `api_calls` - rate limit tracking
- Table: `content_cache` - 6hr content cache
- Size: ~10MB per year

**Output:** `data/influencer_content.json`
- Latest posts from all accounts
- Consumed by Hugo generator
- Size: ~1MB per run

## Cost Projection

| Platform | Free Tier | Paid Tier | Recommendation |
|----------|-----------|-----------|----------------|
| X | 500 posts/month | $100/month | Use free, cache heavily |
| Bluesky | Unlimited | Free | Full use |
| Instagram | 200/hour | $80/month | Use free tier |
| TikTok | Limited | Enterprise | Skip for now |

**Total monthly cost: £0** (if using free tiers + caching)

## Monitoring

Check logs:
```bash
tail -f ~/newslancashire/logs/pipeline.log | grep -i influencer
```

Cache status:
```bash
sqlite3 ~/newslancashire/db/influencer_cache.db "SELECT platform, COUNT(*) FROM api_calls WHERE timestamp > $(date +%s) - 900;"
```

## Next Steps

1. **Copy script** to VPS-NEWS
2. **Add X Bearer Token** to social.json
3. **Test run:** `python3 influencer_monitor.py`
4. **Add to pipeline** (Option A/B/C above)
5. **Monitor logs** for 24hrs

## Deduplication

Ingested into same SQLite as RSS crawler:
```sql
INSERT INTO articles (url, title, source, ...)
VALUES (?, ?, 'influencer', ...)
ON CONFLICT(url) DO NOTHING;
```

Prevents duplicate stories from multiple sources.