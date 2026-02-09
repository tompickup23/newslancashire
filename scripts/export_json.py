#!/usr/bin/env python3
"""Export articles from SQLite to JSON for Astro build."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from crawler_v3 import get_db, export_articles_json, export_burnley_json

conn = get_db()
export_articles_json(conn)
export_burnley_json(conn)
conn.close()
print('Export complete')
