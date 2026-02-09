#!/bin/bash
# Add this to pipeline_v4.sh after Phase 2

# Phase 2b: Influencer Monitoring
echo "$(date '+%Y-%m-%d %H:%M') Phase 2b: Influencer monitoring..." >> "$LOG"
python3 scripts/enhanced_sources/influencer_monitor.py >> "$LOG" 2>&1 || true