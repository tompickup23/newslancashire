#!/bin/bash
# Run all enhanced news sources
set -e

cd /home/ubuntu/newslancashire
LOG=logs/enhanced_sources.log

echo 2026-02-07 14:39 Running enhanced sources... >> 

# YouTube crawler (Lancashire creators)
python3 scripts/enhanced_sources/youtube_crawler.py >>  2>&1 || true

# Data journalist (crime, spending, budgets)
python3 scripts/enhanced_sources/data_journalist.py >>  2>&1 || true

# Unconventional sources (food hygiene, traffic, etc.)
python3 scripts/enhanced_sources/unconventional_crawler.py >>  2>&1 || true

echo 2026-02-07 14:39 Enhanced sources complete >> 
