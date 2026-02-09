#!/usr/bin/env python3
"""Generate Hugo markdown files from SQLite articles database.
Reads crawled articles and creates .md files in appropriate borough directories."""

import sqlite3
import os
import re
import hashlib
from datetime import datetime

DB_PATH = '/home/ubuntu/newslancashire/db/news.db'
CONTENT_DIR = '/home/ubuntu/newslancashire/site/content'

BOROUGH_COLS = [
    'is_burnley', 'is_blackpool', 'is_preston', 'is_lancaster',
    'is_pendle', 'is_rossendale', 'is_hyndburn', 'is_ribble_valley',
    'is_blackburn', 'is_chorley', 'is_south_ribble', 'is_west_lancashire',
    'is_wyre', 'is_fylde'
]

BOROUGH_DIRS = {
    'is_burnley': 'burnley',
    'is_blackpool': 'blackpool',
    'is_preston': 'preston',
    'is_lancaster': 'lancaster',
    'is_pendle': 'pendle',
    'is_rossendale': 'rossendale',
    'is_hyndburn': 'hyndburn',
    'is_ribble_valley': 'ribble-valley',
    'is_blackburn': 'blackburn',
    'is_chorley': 'chorley',
    'is_south_ribble': 'south-ribble',
    'is_west_lancashire': 'west-lancashire',
    'is_wyre': 'wyre',
    'is_fylde': 'fylde',
}


def slugify(text):
    """Create URL-safe slug from title."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


def parse_date(date_str):
    """Parse various date formats into ISO format."""
    if not date_str:
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')

    formats = [
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d %b %Y %H:%M:%S %z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        except ValueError:
            continue

    # Fallback
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')


def clean_summary(summary):
    """Remove HTML tags and clean up summary text."""
    if not summary:
        return ''
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', summary)
    # Fix double spaces
    text = re.sub(r'\s+', ' ', text).strip()
    # Escape Hugo template chars
    text = text.replace('{{', '{ {').replace('}}', '} }')
    return text


def get_borough_tags(row, col_map):
    """Get list of borough names this article belongs to."""
    tags = []
    for col in BOROUGH_COLS:
        if col in col_map and row[col_map[col]] == 1:
            borough_name = col.replace('is_', '').replace('_', ' ').title()
            tags.append(borough_name)
    return tags


def get_primary_borough(row, col_map):
    """Get the first matching borough directory for this article."""
    for col in BOROUGH_COLS:
        if col in col_map and row[col_map[col]] == 1:
            return BOROUGH_DIRS[col]
    return None


def generate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get column names
    c.execute('PRAGMA table_info(articles)')
    columns = [col[1] for col in c.fetchall()]
    col_map = {name: idx for idx, name in enumerate(columns)}

    # Fetch all articles
    c.execute('SELECT * FROM articles ORDER BY fetched_at DESC')
    rows = c.fetchall()

    created = 0
    skipped = 0

    # Track files we create to avoid duplicates
    created_slugs = set()

    for row in rows:
        title = row[col_map['title']]
        link = row[col_map['link']]
        source = row[col_map['source']]
        published = row[col_map.get('published', col_map.get('fetched_at'))]
        summary = row[col_map['summary']]

        if not title or not link:
            skipped += 1
            continue

        slug = slugify(title)
        if not slug or slug in created_slugs:
            skipped += 1
            continue
        created_slugs.add(slug)

        date_str = parse_date(published)
        clean_sum = clean_summary(summary)
        borough_tags = get_borough_tags(row, col_map)
        primary_borough = get_primary_borough(row, col_map)

        # Determine which directory to put it in
        if primary_borough:
            target_dir = os.path.join(CONTENT_DIR, primary_borough)
            location = primary_borough
        else:
            # General Lancashire news - put in a posts directory
            target_dir = os.path.join(CONTENT_DIR, 'posts')
            location = 'lancashire'

        os.makedirs(target_dir, exist_ok=True)

        # Determine article type tag
        if 'BBC' in source:
            source_tag = 'bbc'
        elif 'Telegraph' in source:
            source_tag = 'telegraph'
        elif 'Express' in source:
            source_tag = 'express'
        elif 'Gazette' in source:
            source_tag = 'gazette'
        elif 'Guardian' in source:
            source_tag = 'guardian'
        elif 'LEP' in source:
            source_tag = 'lep'
        else:
            source_tag = 'local'

        # Build tags list
        tags = borough_tags.copy()
        tags.append(source)
        if 'lancashire' not in [t.lower() for t in tags]:
            tags.append('Lancashire')

        tags_yaml = '\n'.join(['  - "' + t + '"' for t in tags])

        # Build Hugo front matter
        front_matter = '---\n'
        front_matter += 'title: "' + title.replace('"', '\\"') + '"\n'
        front_matter += 'date: ' + date_str + '\n'
        front_matter += 'source: "' + source + '"\n'
        front_matter += 'source_url: "' + link + '"\n'
        front_matter += 'location: "' + location + '"\n'
        front_matter += 'type: "news"\n'
        front_matter += 'tags:\n' + tags_yaml + '\n'
        front_matter += 'draft: false\n'
        front_matter += '---\n\n'

        # Build content
        content = front_matter
        if clean_sum:
            content += clean_sum + '\n\n'
        content += '**Source:** [' + source + '](' + link + ')\n'

        # Write file
        filepath = os.path.join(target_dir, slug + '.md')
        with open(filepath, 'w') as f:
            f.write(content)
        created += 1

    conn.close()
    print('Generated ' + str(created) + ' Hugo content files')
    print('Skipped ' + str(skipped) + ' (no title/link or duplicate)')

    # Count per directory
    for dirname in sorted(os.listdir(CONTENT_DIR)):
        dirpath = os.path.join(CONTENT_DIR, dirname)
        if os.path.isdir(dirpath):
            count = len([f for f in os.listdir(dirpath) if f.endswith('.md') and f != '_index.md'])
            if count > 0:
                print('  ' + dirname + ': ' + str(count) + ' articles')


if __name__ == '__main__':
    generate()
