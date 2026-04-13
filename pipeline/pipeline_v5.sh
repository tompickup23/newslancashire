#!/bin/bash
# News Lancashire Pipeline v5.0 — Astro-native pipeline
# Runs every 30 minutes via cron on vps-news
# Flow: crawl → score → two-pass rewrite → borough detect → fact check → export Astro → deploy
cd /home/ubuntu/newslancashire
LOG=/home/ubuntu/newslancashire/logs/pipeline.log
ERRORS=0
PIPELINE_DIR="$(dirname "$0")"

# Use pipeline dir for new scripts, scripts/ for legacy
PIPELINE="${PIPELINE_DIR}"
SCRIPTS="/home/ubuntu/newslancashire/scripts"

log_phase() {
  echo "$(date '+%Y-%m-%d %H:%M') $1" >> "$LOG"
}

run_script() {
  local script="$1"
  local label="$2"
  local timeout="${3:-120}"
  log_phase "Phase: $label..."
  if timeout "$timeout" python3 "$script" >> "$LOG" 2>&1; then
    return 0
  else
    log_phase "ERROR: $label failed (exit $?)"
    ERRORS=$((ERRORS + 1))
    return 1
  fi
}

log_phase "Pipeline v5.0 start"

# ── Phase 1: Crawl RSS + council feeds ──
run_script "$SCRIPTS/crawler_v3.py" "Crawler" 90

# ── Phase 2: AI rewrite (legacy single-pass for all articles) ──
run_script "$SCRIPTS/ai_rewriter.py" "AI Rewriter" 180

# ── Phase 3: Borough detection (enhanced) ──
run_script "$PIPELINE/borough_detector.py" "Borough Detector" 60

# ── Phase 4: Two-pass article engine (high-interest articles only) ──
# Only runs on articles with interest_score >= 40 that haven't been two-pass processed
run_script "$PIPELINE/article_engine.py" "Article Engine" 300

# ── Phase 5: Export to Astro markdown ──
ASTRO_CONTENT="/home/ubuntu/newslancashire/astro-content/articles"
mkdir -p "$ASTRO_CONTENT"
python3 "$PIPELINE/export_astro.py" --output "$ASTRO_CONTENT" --clean >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  log_phase "ERROR: Astro export failed"
  ERRORS=$((ERRORS + 1))
fi

# ── Phase 6: Digests (every 2 hours) ──
HOUR=$(date +%-H)
if [ $((HOUR % 2)) -eq 0 ]; then
  if [ -f "$SCRIPTS/digest/ai_digest_generator.py" ]; then
    run_script "$SCRIPTS/digest/ai_digest_generator.py" "Digests" 120
  fi
fi

# ── Phase 7: News Burnley sync ──
if [ -f "$SCRIPTS/enhanced_sources/news_burnley_sync.py" ]; then
  run_script "$SCRIPTS/enhanced_sources/news_burnley_sync.py" "News Burnley Sync" 30
elif [ -f "$SCRIPTS/news_burnley_sync.py" ]; then
  run_script "$SCRIPTS/news_burnley_sync.py" "News Burnley Sync" 30
fi

# ── Phase 8: Deploy Astro site (via vps-main, every 6 hours) ──
if [ $ERRORS -eq 0 ] && [ $((HOUR % 6)) -eq 0 ]; then
  log_phase "Phase: Rsync Astro content to vps-main..."
  # Sync exported articles to vps-main for Astro build
  if rsync -az --delete "$ASTRO_CONTENT/" vps-main:/root/newslancashire/src/content/articles/ >> "$LOG" 2>&1; then
    log_phase "Rsync OK"
    # Trigger build on vps-main
    if ssh -o ConnectTimeout=10 vps-main "cd /root/newslancashire && npm run build && wrangler pages deploy dist --project-name=newslancashire" >> "$LOG" 2>&1; then
      log_phase "Astro deploy OK"
    else
      log_phase "WARN: Astro deploy failed"
    fi
  else
    log_phase "WARN: Rsync to vps-main failed"
  fi
fi

# ── Phase 9: News Burnley deploy (via vps-main) ──
if [ $ERRORS -eq 0 ]; then
  if ssh -o ConnectTimeout=10 vps-main "bash /root/aidoge/deploy_newsburnley.sh" >> "$LOG" 2>&1; then
    log_phase "News Burnley deploy OK"
  else
    log_phase "WARN: News Burnley deploy failed"
  fi
fi

log_phase "Pipeline v5.0 complete (errors: $ERRORS)"
