#!/usr/bin/env python3
"""
RSS Feed Generator - News Lancashire
Generates RSS 2.0 and Atom feeds for syndication
Zero AI - template-based XML generation
"""
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
OUTPUT_DIR = BASE_DIR / "site/static"
SITE_URL = "https://newslancashire.co.uk"
SITE_TITLE = "News Lancashire"
SITE_DESCRIPTION = "Latest news from across Lancashire"

def load_articles():
    with open(ARTICLES_FILE) as f:
        return json.load(f)

def generate_rss(articles, filename="feed.xml", borough_filter=None):
    """Generate RSS 2.0 feed"""
    
    # Filter if needed
    if borough_filter:
        articles = [a for a in articles if a.get("borough") == borough_filter]
        title = f"{SITE_TITLE} - {borough_filter.replace('_', ' ').title()}"
        link = f"{SITE_URL}/{borough_filter}/"
    else:
        title = SITE_TITLE
        link = SITE_URL
    
    # Sort by date
    articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[:50]
    
    # Build RSS
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
    <title>{title}</title>
    <link>{link}</link>
    <description>{SITE_DESCRIPTION}</description>
    <language>en-gb</language>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
    <atom:link href="{link}{filename}" rel="self" type="application/rss+xml" />
    <generator>News Lancashire RSS Generator</generator>
'''
    
    for article in articles:
        title = article.get("title", "Untitled").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        url = article.get("url", "")
        desc = article.get("summary", article.get("excerpt", title))[:300]
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        date = article.get("date", "")
        category = article.get("category", "")
        borough = article.get("borough", "")
        
        # Parse date to RSS format
        try:
            pub_date = datetime.strptime(date[:10], "%Y-%m-%d").strftime('%a, %d %b %Y %H:%M:%S +0000')
        except:
            pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        rss += f'''    <item>
        <title>{title}</title>
        <link>{url}</link>
        <guid isPermaLink="true">{url}</guid>
        <description>{desc}</description>
        <pubDate>{pub_date}</pubDate>
'''
        if category:
            rss += f'        <category>{category}</category>\n'
        if borough:
            rss += f'        <category domain="borough">{borough}</category>\n'
        
        rss += '    </item>\n'
    
    rss += '</channel>\n</rss>'
    
    return rss

def generate_atom(articles, filename="atom.xml", borough_filter=None):
    """Generate Atom feed"""
    
    if borough_filter:
        articles = [a for a in articles if a.get("borough") == borough_filter]
        title = f"{SITE_TITLE} - {borough_filter.replace('_', ' ').title()}"
    else:
        title = SITE_TITLE
    
    articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[:50]
    
    atom = f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>{title}</title>
    <link href="{SITE_URL}/{filename}" rel="self" />
    <link href="{SITE_URL}" />
    <id>{SITE_URL}/</id>
    <updated>{datetime.now().isoformat()}Z</updated>
    <generator>News Lancashire</generator>
'''
    
    for article in articles:
        title = article.get("title", "Untitled").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        url = article.get("url", "")
        desc = article.get("summary", title).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        date = article.get("date", "")
        
        try:
            updated = datetime.strptime(date[:10], "%Y-%m-%d").isoformat() + "Z"
        except:
            updated = datetime.now().isoformat() + "Z"
        
        atom += f'''    <entry>
        <title>{title}</title>
        <link href="{url}" />
        <id>{url}</id>
        <updated>{updated}</updated>
        <summary>{desc}</summary>
    </entry>
'''
    
    atom += '</feed>'
    
    return atom

def generate_json_feed(articles, filename="feed.json"):
    """Generate JSON Feed 1.0"""
    
    articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[:50]
    
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": SITE_TITLE,
        "home_page_url": SITE_URL,
        "feed_url": f"{SITE_URL}/{filename}",
        "description": SITE_DESCRIPTION,
        "items": []
    }
    
    for article in articles:
        item = {
            "id": article.get("url", ""),
            "url": article.get("url", ""),
            "title": article.get("title", "Untitled"),
            "content_text": article.get("summary", ""),
            "date_published": article.get("date", ""),
            "tags": [article.get("category", ""), article.get("borough", "")]
        }
        feed["items"].append(item)
    
    return json.dumps(feed, indent=2)

def main():
    print("[RSS Generator] Starting...")
    
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Main feeds
    rss = generate_rss(articles)
    with open(OUTPUT_DIR / "feed.xml", 'w') as f:
        f.write(rss)
    print(f"  RSS feed: {OUTPUT_DIR}/feed.xml")
    
    atom = generate_atom(articles)
    with open(OUTPUT_DIR / "atom.xml", 'w') as f:
        f.write(atom)
    print(f"  Atom feed: {OUTPUT_DIR}/atom.xml")
    
    json_feed = generate_json_feed(articles)
    with open(OUTPUT_DIR / "feed.json", 'w') as f:
        f.write(json_feed)
    print(f"  JSON feed: {OUTPUT_DIR}/feed.json")
    
    # Borough-specific feeds
    boroughs = set(a.get("borough", "") for a in articles if a.get("borough"))
    
    for borough in list(boroughs)[:10]:  # Top 10 boroughs
        rss = generate_rss(articles, f"{borough}_feed.xml", borough)
        with open(OUTPUT_DIR / f"{borough}_feed.xml", 'w') as f:
            f.write(rss)
        print(f"  {borough} feed: {OUTPUT_DIR}/{borough}_feed.xml")
    
    print(f"\n[RSS Generator] Complete")
    print(f"  Total feeds: {3 + min(len(boroughs), 10)}")

if __name__ == "__main__":
    main()