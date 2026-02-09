#!/usr/bin/env python3
"""
Content Gap Analysis - News Lancashire
Identifies underserved topics, boroughs, and categories
Zero AI - SQLite analysis only
"""
import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
OUTPUT_FILE = BASE_DIR / "data/content_gap_analysis.json"

# Target coverage areas
LANCASHIRE_BOROUGHS = [
    "burnley", "blackburn", "blackpool", "preston", "lancaster",
    "chorley", "south_ribble", "rossendale", "hyndburn", "pendle",
    "ribble_valley", "wyre", "fylde", "west_lancashire", "bolton",
    "bury", "wigan", "salford", "rochdale", "oldham"
]

TARGET_CATEGORIES = [
    "crime", "politics", "council", "housing", "transport",
    "health", "education", "environment", "business", "community"
]

def load_articles():
    with open(ARTICLES_FILE) as f:
        return json.load(f)

def analyze_borough_coverage(articles):
    """Count articles per borough"""
    borough_counts = Counter()
    for article in articles:
        borough = article.get("borough", "unknown")
        if borough:
            borough_counts[borough.lower()] += 1
    return borough_counts

def analyze_categories(articles):
    """Count articles per category"""
    cat_counts = Counter()
    for article in articles:
        cat = article.get("category", "general")
        if cat:
            cat_counts[cat.lower()] += 1
    return cat_counts

def analyze_keywords(articles, top_n=50):
    """Extract most common keywords/tags"""
    keywords = Counter()
    for article in articles:
        tags = article.get("tags", []) or article.get("keywords", [])
        for tag in tags:
            keywords[tag.lower()] += 1
    return keywords.most_common(top_n)

def analyze_publication_dates(articles):
    """Check date distribution"""
    dates = []
    for article in articles:
        date_str = article.get("date", "")
        if date_str:
            try:
                dates.append(datetime.strptime(date_str[:10], "%Y-%m-%d"))
            except:
                pass
    
    if not dates:
        return {}
    
    dates.sort()
    date_range = (dates[-1] - dates[0]).days if len(dates) > 1 else 0
    recent_30d = sum(1 for d in dates if d > datetime.now() - timedelta(days=30))
    
    return {
        "total_days_covered": date_range,
        "articles_last_30d": recent_30d,
        "avg_per_day": len(dates) / max(date_range, 1),
        "oldest_article": dates[0].isoformat() if dates else None,
        "newest_article": dates[-1].isoformat() if dates else None
    }

def identify_gaps(borough_counts, cat_counts):
    """Identify underserved areas"""
    gaps = {
        "underserved_boroughs": [],
        "missing_categories": [],
        "recommendations": []
    }
    
    # Boroughs with < 5 articles
    for borough in LANCASHIRE_BOROUGHS:
        count = borough_counts.get(borough, 0)
        if count < 5:
            gaps["underserved_boroughs"].append({
                "borough": borough,
                "article_count": count,
                "priority": "high" if count == 0 else "medium"
            })
    
    # Categories with < 10 articles
    for cat in TARGET_CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count < 10:
            gaps["missing_categories"].append({
                "category": cat,
                "article_count": count,
                "priority": "high" if count == 0 else "medium"
            })
    
    # Generate recommendations
    if gaps["underserved_boroughs"]:
        top_borough = gaps["underserved_boroughs"][0]["borough"]
        gaps["recommendations"].append(f"Increase coverage in {top_borough.title()}")
    
    if gaps["missing_categories"]:
        top_cat = gaps["missing_categories"][0]["category"]
        gaps["recommendations"].append(f"Add more {top_cat} content")
    
    return gaps

def main():
    print("[Content Gap Analysis] Starting...")
    
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    
    # Analysis
    borough_counts = analyze_borough_coverage(articles)
    cat_counts = analyze_categories(articles)
    top_keywords = analyze_keywords(articles, 30)
    date_stats = analyze_publication_dates(articles)
    gaps = identify_gaps(borough_counts, cat_counts)
    
    # Output
    analysis = {
        "generated": datetime.now().isoformat(),
        "total_articles": len(articles),
        "borough_coverage": dict(borough_counts.most_common(20)),
        "category_distribution": dict(cat_counts.most_common(15)),
        "top_keywords": top_keywords,
        "date_statistics": date_stats,
        "content_gaps": gaps
    }
    
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"[Content Gap Analysis] Complete. Output: {OUTPUT_FILE}")
    print(f"  Boroughs covered: {len(borough_counts)}")
    print(f"  Categories: {len(cat_counts)}")
    print(f"  Underserved boroughs: {len(gaps['underserved_boroughs'])}")
    
    # Print summary
    print("\n=== TOP GAPS ===")
    for b in gaps["underserved_boroughs"][:5]:
        print(f"  {b['borough']}: {b['article_count']} articles ({b['priority']} priority)")

if __name__ == "__main__":
    main()