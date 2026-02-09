#!/bin/bash
# News Lancashire Pipeline v4.1 — Per-phase error handling, broken scrapers disabled
# Runs every 30 minutes via cron
# Changes from v4: removed set -e (cascade failures), disabled broken scrapers,
# added per-phase error counting, health summary at end

cd /home/ubuntu/newslancashire
LOG=logs/pipeline.log
ERRORS=0

# Load API keys
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

log_phase() {
    echo "$(date '+%Y-%m-%d %H:%M') $1" >> "$LOG"
}

run_script() {
    # Run a script, log errors but don't stop pipeline
    local script="$1"
    local label="$2"
    if python3 "$script" >> "$LOG" 2>&1; then
        return 0
    else
        log_phase "  ERROR: $label failed (exit $?)"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

log_phase "Pipeline v4.1 start"

# Phase 1: Core Crawling (critical — but don't kill pipeline on failure)
log_phase "Phase 1: Core crawling..."
run_script scripts/crawler_v3.py "crawler_v3"
run_script scripts/social_crawler.py "social_crawler"

# Phase 2: Enhanced Sources (all non-critical)
log_phase "Phase 2: Enhanced sources..."
run_script scripts/enhanced_sources/data_journalist.py "data_journalist"
run_script scripts/enhanced_sources/youtube_crawler.py "youtube"
run_script scripts/enhanced_sources/food_hygiene_crawler.py "food_hygiene"
run_script scripts/enhanced_sources/traffic_monitor.py "traffic"
run_script scripts/enhanced_sources/reddit_monitor.py "reddit"
run_script scripts/enhanced_sources/community_fundraising.py "fundraising"
run_script scripts/enhanced_sources/business_monitor.py "business"
run_script scripts/enhanced_sources/influencer_monitor.py "influencer"

# Phase 2c: Content Analysis & Social
run_script scripts/enhanced_sources/content_gap_analysis.py "content_gap"
run_script scripts/enhanced_sources/trending_dashboard.py "trending"
run_script scripts/enhanced_sources/auto_social_poster.py "social_poster"

# Phase 2d: Borough Detection & SEO
run_script scripts/enhanced_sources/borough_detection_fix.py "borough_fix"
run_script scripts/enhanced_sources/seo_generator.py "seo"

# Phase 2e: Categorization, RSS, Search
run_script scripts/enhanced_sources/category_tagger.py "category"
run_script scripts/enhanced_sources/rss_generator.py "rss_gen"
run_script scripts/enhanced_sources/search_generator.py "search_gen"
run_script scripts/enhanced_sources/share_buttons_generator.py "share_buttons"

# Phase 2f: Free API Integrations
run_script scripts/enhanced_sources/weather_generator.py "weather"
run_script scripts/enhanced_sources/newsapi_fetcher.py "newsapi"
run_script scripts/enhanced_sources/image_generator.py "image_gen"
run_script scripts/enhanced_sources/postcode_tagger.py "postcode"

# Phase 3: AI Digests
log_phase "Phase 3: AI digest generation..."
run_script scripts/digest/ai_digest_generator.py "ai_digest"

# Phase 4: Planning Applications — DISABLED (endpoints broken: 500/404/SSL errors)
# Uncomment when Burnley/Hyndburn/Pendle IDOX endpoints are working again
# hour=$(date +%H)
# if [ $((hour % 2)) -eq 0 ]; then
#     log_phase "Phase 4: Planning applications..."
#     run_script scripts/planning/idox_scraper.py "planning"
# fi

# Phase 5: Council Minutes — DISABLED (DNS lookup failures)
# Uncomment when council minutes endpoint is reachable
# if [ $((hour % 4)) -eq 0 ]; then
#     log_phase "Phase 5: Council minutes..."
#     run_script scripts/council_minutes/burnley_minutes.py "minutes"
# fi

# Phase 6: Weekly Digest (Mondays only — handled internally by the script)
run_script scripts/enhanced_sources/weekly_digest.py "weekly_digest"

# Phase 7: AI Processing (needs MOONSHOT_API_KEY or DEEPSEEK_API_KEY)
log_phase "Phase 7: AI processing..."
run_script scripts/ai_rewriter.py "ai_rewriter"
run_script scripts/ai_analyzer.py "ai_analyzer"

# Phase 8: Export
log_phase "Phase 8: Export..."
run_script scripts/export_json.py "export"

# Phase 9: News Burnley Sync + Deploy
log_phase "Phase 9: News Burnley sync..."
run_script scripts/enhanced_sources/news_burnley_sync.py "news_burnley"

# Health summary
if [ $ERRORS -eq 0 ]; then
    log_phase "Pipeline v4.1 complete (no errors)"
else
    log_phase "Pipeline v4.1 complete ($ERRORS errors — check log)"
fi
