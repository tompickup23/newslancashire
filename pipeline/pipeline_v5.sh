#!/bin/bash
# News Lancashire Pipeline v5.0 — Unified pipeline on vps-main
# Runs every 30 minutes via cron
# Flow: crawl → rewrite → borough detect → two-pass engine → export Astro → build → deploy
set -o pipefail

NL_PIPELINE="/root/newslancashire-pipeline"
NL_ASTRO="/root/newslancashire"
LOG="$NL_PIPELINE/logs/pipeline.log"
ERRORS=0

cd "$NL_PIPELINE"
mkdir -p logs

# Source environment variables (API keys, CF tokens)
if [ -f "$NL_PIPELINE/.env" ]; then
  set -a
  source "$NL_PIPELINE/.env"
  set +a
fi

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
run_script scripts/crawler_v3.py "Crawler" 90

# ── Phase 2: AI rewrite (single-pass for all articles) ──
run_script scripts/ai_rewriter.py "AI Rewriter" 180

# ── Phase 3: Borough detection (enhanced) ──
run_script pipeline/borough_detector.py "Borough Detector" 60

# ── Phase 4: Two-pass article engine (high-interest only) ──
run_script pipeline/article_engine.py "Article Engine" 300

# ── Phase 5: Export to Astro markdown ──
ASTRO_CONTENT="$NL_ASTRO/src/content/articles"
mkdir -p "$ASTRO_CONTENT"
python3 pipeline/export_astro.py --output "$ASTRO_CONTENT" --clean >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  log_phase "ERROR: Astro export failed"
  ERRORS=$((ERRORS + 1))
fi

# ── Phase 6: Cross-publish (LT, Asylum Stats, DOGE → NL staging) ──
STAGING_DIR="$NL_PIPELINE/staging/articles"
mkdir -p "$STAGING_DIR"
python3 pipeline/cross_publish.py --output "$STAGING_DIR" >> "$LOG" 2>&1

# ── Phase 7: Submit ALL articles to SR editorial for review ──
# Articles only go live after SR approval
run_script pipeline/sr_submit.py "SR Submit" 30

# ── Phase 8: Export ONLY SR-approved articles to live Astro ──
python3 pipeline/export_approved.py --output "$ASTRO_CONTENT" >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  log_phase "WARN: Approved export had errors"
fi

# ── Phase 10: Digests (every 2 hours) ──
HOUR=$(date +%-H)
if [ $((HOUR % 2)) -eq 0 ]; then
  if [ -f scripts/digest/ai_digest_generator.py ]; then
    run_script scripts/digest/ai_digest_generator.py "Digests" 120
  fi
fi

# ── Phase 11: Build + Deploy Astro (every 6 hours) ──
if [ $ERRORS -eq 0 ] && [ $((HOUR % 6)) -eq 0 ]; then
  log_phase "Phase: Astro build + deploy..."
  cd "$NL_ASTRO"
  git pull --ff-only origin main >> "$LOG" 2>&1 || true
  if npx astro build >> "$LOG" 2>&1; then
    log_phase "Astro build OK"
    if npx wrangler pages deploy dist --project-name=newslancashire --commit-dirty=true >> "$LOG" 2>&1; then
      log_phase "CF Pages deploy OK"
    else
      log_phase "WARN: CF Pages deploy failed"
    fi
  else
    log_phase "ERROR: Astro build failed"
    ERRORS=$((ERRORS + 1))
  fi
  cd "$NL_PIPELINE"
fi

log_phase "Pipeline v5.0 complete (errors: $ERRORS)"
