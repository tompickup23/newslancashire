#!/bin/bash
# News Lancashire Pipeline v3 - runs every 30 minutes
set -e

cd /home/ubuntu/newslancashire
LOG=logs/pipeline.log

export MOONSHOT_API_KEY="sk-A9tqAkurjbh2RIXRVu3YdFZs5Hj19QmkdlEFXOM0cAyxdduH"
export DEEPSEEK_API_KEY="sk-5b7f5f8a164b4853a80b0fa69ed04c8c"
export CLOUDFLARE_API_TOKEN="BmINWd_dv9Qiw6Pu3WRu3Wy2V2STEccjZ5AMhXfx"
export CLOUDFLARE_ACCOUNT_ID="35e8f9e8edb5487b97309d107331f7f5"

echo "$(date '+%Y-%m-%d %H:%M') Pipeline v3 start" >> $LOG

# Step 1: Crawl RSS + Bluesky → SQLite
python3 scripts/crawler_v3.py >> $LOG 2>&1

# Step 1b: Crawl Google News + Parliament + Police APIs
python3 scripts/social_crawler.py >> $LOG 2>&1

# Step 2: AI Rewrite (Kimi K2.5)
if [ -f scripts/ai_rewriter.py ]; then
    python3 scripts/ai_rewriter.py >> $LOG 2>&1
fi

# Step 3: AI Analysis (high-interest)
if [ -f scripts/ai_analyzer.py ]; then
    python3 scripts/ai_analyzer.py >> $LOG 2>&1
fi

# Step 3b: Export DB to JSON for Astro
python3 scripts/export_json.py >> $LOG 2>&1

# Step 4: Build Astro
cd /home/ubuntu/newslancashire-astro
npx astro build >> $LOG 2>&1
echo "$(date '+%Y-%m-%d %H:%M') Astro build complete" >> $LOG
cd /home/ubuntu/newslancashire

# Step 5: Deploy to Cloudflare Pages (direct from dist/)
cd /home/ubuntu/newslancashire-astro/dist
npx wrangler pages deploy . --project-name=newslancashire --branch=main >> $LOG 2>&1
echo "$(date '+%Y-%m-%d %H:%M') Deployed to Cloudflare Pages" >> $LOG
cd /home/ubuntu/newslancashire

# Step 6: Backup to GitHub (non-critical, don't fail pipeline)
LANCASHIRE_REPO="/home/ubuntu/github-newslancashire"
if [ -d "$LANCASHIRE_REPO/.git" ]; then
    rsync -a --delete --exclude='.git' --exclude='CNAME' /home/ubuntu/newslancashire-astro/dist/ "$LANCASHIRE_REPO/"
    cd "$LANCASHIRE_REPO"
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "Update $(date '+%Y-%m-%d %H:%M')" >> $LOG 2>&1
        GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes" git push origin main >> $LOG 2>&1 || true
        echo "$(date '+%Y-%m-%d %H:%M') Backed up to GitHub" >> $LOG
    fi
    cd /home/ubuntu/newslancashire
fi

# Step 7: Deploy News Burnley
BURNLEY_REPO="/home/ubuntu/github-newsburnley"
BURNLEY_JSON="export/burnley-news.json"
if [ -d "$BURNLEY_REPO/.git" ] && [ -f "$BURNLEY_JSON" ]; then
    cp "$BURNLEY_JSON" "$BURNLEY_REPO/burnley-news.json"
    cd "$BURNLEY_REPO"
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "News update $(date '+%Y-%m-%d %H:%M')" >> $LOG 2>&1
        GIT_SSH_COMMAND="ssh -i ~/.ssh/id_newsburnley -o IdentitiesOnly=yes" git push origin main >> $LOG 2>&1
        echo "$(date '+%Y-%m-%d %H:%M') News Burnley deployed" >> $LOG
    fi
    cd /home/ubuntu/newslancashire
fi

echo "$(date '+%Y-%m-%d %H:%M') Pipeline v3 done" >> $LOG
