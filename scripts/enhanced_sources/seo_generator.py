#!/usr/bin/env python3
"""
SEO Meta & Sitemap Generator - News Lancashire
Generates sitemap.xml and meta descriptions
Zero AI - template-based
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
SITE_URL = "https://newslancashire.co.uk"

def load_articles():
    with open(ARTICLES_FILE) as f:
        return json.load(f)

def generate_meta_description(article):
    """Generate meta description from content"""
    title = article.get("title", "")
    summary = article.get("summary", article.get("excerpt", ""))
    borough = article.get("borough", "Lancashire")
    
    # Use summary if available
    if summary and len(summary) > 50:
        desc = summary[:155]
        if len(summary) > 155:
            desc += "..."
        return desc
    
    # Generate from title
    desc = f"Latest {borough.title()} news: {title}"[:160]
    return desc

def generate_sitemap(articles):
    """Generate sitemap.xml"""
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    # Homepage
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = SITE_URL
    ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(url, "changefreq").text = "daily"
    ET.SubElement(url, "priority").text = "1.0"
    
    # Borough pages
    boroughs = set(a.get("borough", "") for a in articles if a.get("borough"))
    for borough in boroughs:
        if borough:
            url = ET.SubElement(urlset, "url")
            ET.SubElement(url, "loc").text = f"{SITE_URL}/{borough}/"
            ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
            ET.SubElement(url, "changefreq").text = "daily"
            ET.SubElement(url, "priority").text = "0.8"
    
    # Individual articles
    for article in articles:
        article_url = article.get("url", "")
        if article_url and article_url.startswith("http"):
            url = ET.SubElement(urlset, "url")
            ET.SubElement(url, "loc").text = article_url
            
            # Last modified date
            date = article.get("date", "")
            if date:
                ET.SubElement(url, "lastmod").text = date[:10]
            
            ET.SubElement(url, "changefreq").text = "weekly"
            ET.SubElement(url, "priority").text = "0.6"
    
    # Pretty print
    ET.indent(urlset, space="  ")
    return ET.tostring(urlset, encoding="unicode")

def generate_robots_txt():
    """Generate robots.txt"""
    return f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""

def enhance_articles_with_meta(articles):
    """Add SEO meta to each article"""
    enhanced = []
    
    for article in articles:
        # Generate meta description
        article["meta_description"] = generate_meta_description(article)
        
        # Generate keywords from tags + borough
        tags = article.get("tags", [])
        borough = article.get("borough", "")
        category = article.get("category", "")
        
        keywords = ["Lancashire news"]
        if borough:
            keywords.append(f"{borough} news")
        if category:
            keywords.append(f"{category} news")
        keywords.extend(tags[:5])  # First 5 tags
        
        article["meta_keywords"] = ", ".join(keywords)
        
        # Canonical URL
        article["canonical_url"] = article.get("url", "")
        
        enhanced.append(article)
    
    return enhanced

def generate_html_sitemap(articles):
    """Generate HTML sitemap page"""
    
    # Group by borough
    by_borough = {}
    for article in articles:
        borough = article.get("borough", "Uncategorized")
        if borough not in by_borough:
            by_borough[borough] = []
        by_borough[borough].append(article)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sitemap - News Lancashire</title>
    <meta name="description" content="Complete sitemap of News Lancashire articles by borough.">
</head>
<body style="font-family:system-ui;max-width:800px;margin:40px auto;padding:20px">
    <h1>News Lancashire - Sitemap</h1>
    <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <h2>Categories by Borough</h2>
'''
    
    for borough in sorted(by_borough.keys()):
        articles_list = sorted(by_borough[borough], key=lambda x: x.get("date", ""), reverse=True)[:10]
        html += f'    <h3>{borough.replace("_", " ").title()}</h3>\n    <ul>\n'
        for article in articles_list:
            title = article.get("title", "Untitled")
            url = article.get("url", "#")
            date = article.get("date", "")[:10]
            html += f'        <li><a href="{url}">{title}</a> <small>({date})</small></li>\n'
        html += '    </ul>\n'
    
    html += '''</body>
</html>'''
    
    return html

def main():
    print("[SEO Generator] Starting...")
    
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    
    # Enhance articles with meta
    enhanced = enhance_articles_with_meta(articles)
    
    # Save enhanced articles
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(enhanced, f, indent=2)
    
    print(f"  Added meta to {len(enhanced)} articles")
    
    # Generate sitemap.xml
    sitemap = generate_sitemap(enhanced)
    sitemap_path = BASE_DIR / "site/static/sitemap.xml"
    sitemap_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sitemap_path, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(sitemap)
    
    print(f"  Sitemap: {sitemap_path}")
    
    # Generate robots.txt
    robots = generate_robots_txt()
    robots_path = BASE_DIR / "site/static/robots.txt"
    with open(robots_path, 'w') as f:
        f.write(robots)
    
    print(f"  Robots: {robots_path}")
    
    # Generate HTML sitemap
    html_sitemap = generate_html_sitemap(enhanced)
    html_path = BASE_DIR / "site/static/sitemap.html"
    with open(html_path, 'w') as f:
        f.write(html_sitemap)
    
    print(f"  HTML Sitemap: {html_path}")
    
    # Stats
    total_urls = len(enhanced) + len(set(a.get("borough", "") for a in enhanced)) + 1
    print(f"\n[SEO Generator] Complete")
    print(f"  Total URLs in sitemap: {total_urls}")
    print(f"  Articles with meta: {len(enhanced)}")

if __name__ == "__main__":
    main()