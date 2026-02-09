#!/bin/bash
# News Lancashire Pipeline v4 - Enhanced with Alternative Sources
# Runs every 30 minutes via cron
set -e

cd /home/ubuntu/newslancashire
LOG=logs/pipeline.log

# Load API keys
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "$(date '+%Y-%m-%d %H:%M') Pipeline v4 start" >> "$LOG"

# Phase 1: Core Crawling
echo "$(date '+%Y-%m-%d %H:%M') Phase 1: Core crawling..." >> "$LOG"
python3 scripts/crawler_v3.py >> "$LOG" 2>&1
python3 scripts/social_crawler.py >> "$LOG" 2>&1

# Phase 2: Enhanced Sources
echo "$(date '+%Y-%m-%d %H:%M') Phase 2: Enhanced sources..." >> "$LOG"
python3 scripts/enhanced_sources/data_journalist.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/youtube_crawler.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/food_hygiene_crawler.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/traffic_monitor.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/reddit_monitor.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/community_fundraising.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/business_monitor.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/influencer_monitor.py >> "$LOG" 2>&1 || true

# Phase 2c: Content Analysis & Social
python3 scripts/enhanced_sources/content_gap_analysis.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/trending_dashboard.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/auto_social_poster.py >> "$LOG" 2>&1 || true

# Phase 2d: Borough Detection & SEO
python3 scripts/enhanced_sources/borough_detection_fix.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/seo_generator.py >> "$LOG" 2>&1 || true

# Phase 2e: Categorization, RSS, Search
python3 scripts/enhanced_sources/category_tagger.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/rss_generator.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/search_generator.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/share_buttons_generator.py >> "$LOG" 2>&1 || true

# Phase 2f: Free API Integrations
python3 scripts/enhanced_sources/weather_generator.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/newsapi_fetcher.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/image_generator.py >> "$LOG" 2>&1 || true
python3 scripts/enhanced_sources/postcode_tagger.py >> "$LOG" 2>&1 || true

# Phase 3: AI Digests
echo "$(date '+%Y-%m-%d %H:%M') Phase 3: AI digest generation..." >> "$LOG"
python3 scripts/digest/ai_digest_generator.py >> "$LOG" 2>&1 || true

# Phase 4: Planning Applications (Every 2 hours)
hour=$(date +%H)
if [ $((hour % 2)) -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M') Phase 4: Planning applications..." >> "$LOG"
    python3 scripts/planning/idox_scraper.py >> "$LOG" 2>&1 || true
fi

# Phase 5: Council Minutes (Every 4 hours)
if [ $((hour % 4)) -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M') Phase 5: Council minutes..." >> "$LOG"
    python3 scripts/council_minutes/burnley_minutes.py >> "$LOG" 2>&1 || true
fi

# Phase 6: Weekly Digest (Mondays only)
python3 scripts/enhanced_sources/weekly_digest.py >> "$LOG" 2>&1 || true

# Phase 7: AI Processing (needs MOONSHOT_API_KEY or DEEPSEEK_API_KEY)
echo "$(date '+%Y-%m-%d %H:%M') Phase 7: AI processing..." >> "$LOG"
python3 scripts/ai_rewriter.py >> "$LOG" 2>&1 || true
python3 scripts/ai_analyzer.py >> "$LOG" 2>&1 || true

# Phase 8: Export
echo "$(date '+%Y-%m-%d %H:%M') Phase 8: Export..." >> "$LOG"
python3 scripts/export_json.py >> "$LOG" 2>&1

# Phase 9: News Burnley Sync + Deploy
echo "$(date '+%Y-%m-%d %H:%M') Phase 9: News Burnley sync..." >> "$LOG"
python3 scripts/enhanced_sources/news_burnley_sync.py >> "$LOG" 2>&1 || true

# Note: newslancashire.co.uk Astro build/deploy is currently broken.
# The Astro project needs rebuilding. For now, the last CF Pages deploy is live.
# TODO: Rebuild newslancashire Astro site or switch to simple static deploy

echo "$(date '+%Y-%m-%d %H:%M') Pipeline v4 complete" >> "$LOG"
