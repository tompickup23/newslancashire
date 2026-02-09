#!/bin/bash
# EASY UPDATE SCRIPT for News Lancashire
# Run this after SSHing into Thurinus

echo "=== News Lancashire Updater ==="
echo "1) Add original article"
echo "2) Build and deploy site"  
echo "3) Export articles for AI summary"
echo "4) Run crawler now"
echo ""
read -p "Choice: " choice

case $choice in
  1)
    read -p "Article title: " title
    slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
    file="~/newslancashire/site/content/original/$slug.md"
    echo "---" > "$file"
    echo "title: \"$title\"" >> "$file"
    echo "date: $(date -Iseconds)" >> "$file"
    echo "draft: false" >> "$file"
    echo "source: \"Tom Pickup\"" >> "$file"
    echo "---" >> "$file"
    echo "" >> "$file"
    echo "Write your article here..." >> "$file"
    echo "✅ Created: $file"
    echo "   Edit with: nano $file"
    ;;
  2)
    cd ~/newslancashire/site && hugo --minify && sudo chown -R www-data:www-data public
    echo "✅ Site deployed!"
    ;;
  3)
    ~/newslancashire/scripts/generate-summaries.sh
    ;;
  4)
    python3 ~/newslancashire/scripts/crawler.py
    ;;
esac
