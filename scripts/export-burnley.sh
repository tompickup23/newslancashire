#!/bin/bash
# Export Burnley articles to JSON for Octavianus

DB_PATH=~/newslancashire/db/news.db
EXPORT_DIR=~/newslancashire/data

mkdir -p $EXPORT_DIR

# Export Burnley articles as JSON
sqlite3 $DB_PATH << SQL > $EXPORT_DIR/burnley-news.json
.headers off
.mode json
SELECT json_object(
    'id', id,
    'title', title,
    'link', link,
    'source', source,
    'published', published,
    'summary', summary
) FROM articles 
WHERE is_burnley = 1 
ORDER BY published DESC 
LIMIT 50;
SQL

echo "Exported Burnley articles to $EXPORT_DIR/burnley-news.json"
wc -l $EXPORT_DIR/burnley-news.json
