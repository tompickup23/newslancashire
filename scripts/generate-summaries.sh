#!/bin/bash
# This script is called by Dominus (master clawdbot) to trigger AI summary generation
# It exports unprocessed articles for AI summarization

DB_PATH=~/newslancashire/db/news.db
EXPORT_PATH=~/newslancashire/data/articles-for-summary.json

echo "Exporting unprocessed articles..."

sqlite3 $DB_PATH << SQL
.headers off
.mode json
SELECT id, title, link, source, summary, is_burnley 
FROM articles 
WHERE is_processed = 0 
ORDER BY published DESC 
LIMIT 20;
SQL > $EXPORT_PATH

echo "Exported articles to $EXPORT_PATH"
echo "Articles ready for AI summarization by Dominus"
cat $EXPORT_PATH
