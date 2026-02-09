#!/bin/bash
# News Lancashire Pipeline v2 - runs hourly
# 1. Crawl RSS feeds → SQLite
# 2. Generate Hugo content from DB
# 3. Rebuild Hugo site
# 4. Deploy to GitHub Pages (News Lancashire)
# 5. Deploy to GitHub Pages (News Burnley)
set -e

cd /home/ubuntu/newslancashire
LOG=/home/ubuntu/newslancashire/logs/pipeline.log

echo "$(date '+%Y-%m-%d %H:%M') Pipeline start" >> $LOG

# Step 1: Crawl
python3 scripts/crawler.py >> $LOG 2>&1

# Step 2: Generate content
python3 scripts/generate_hugo_content.py >> $LOG 2>&1

# Step 3: Rebuild Hugo
cd site
hugo --gc --minify >> $LOG 2>&1
cd ..

# Step 4: Deploy News Lancashire to GitHub Pages
LANCASHIRE_REPO="/home/ubuntu/github-newslancashire"
if [ -d "$LANCASHIRE_REPO/.git" ]; then
    rsync -a --delete --exclude='.git' site/public/ "$LANCASHIRE_REPO/"
    cd "$LANCASHIRE_REPO"
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "Pipeline update $(date '+%Y-%m-%d %H:%M')" >> $LOG 2>&1
        GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes" git push origin main >> $LOG 2>&1
        echo "$(date '+%Y-%m-%d %H:%M') News Lancashire deployed to GitHub" >> $LOG
    else
        echo "$(date '+%Y-%m-%d %H:%M') News Lancashire: no changes" >> $LOG
    fi
    cd /home/ubuntu/newslancashire
fi

# Step 5: Deploy News Burnley to GitHub Pages
BURNLEY_REPO="/home/ubuntu/github-newsburnley"
BURNLEY_JSON="data/burnley-news.json"
if [ -d "$BURNLEY_REPO/.git" ] && [ -f "$BURNLEY_JSON" ]; then
    cp "$BURNLEY_JSON" "$BURNLEY_REPO/burnley-news.json"
    cd "$BURNLEY_REPO"
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "News update $(date '+%Y-%m-%d %H:%M')" >> $LOG 2>&1
        GIT_SSH_COMMAND="ssh -i ~/.ssh/id_newsburnley -o IdentitiesOnly=yes" git push origin main >> $LOG 2>&1
        echo "$(date '+%Y-%m-%d %H:%M') News Burnley deployed to GitHub" >> $LOG
    else
        echo "$(date '+%Y-%m-%d %H:%M') News Burnley: no changes" >> $LOG
    fi
    cd /home/ubuntu/newslancashire
fi

echo "$(date '+%Y-%m-%d %H:%M') Pipeline done" >> $LOG
