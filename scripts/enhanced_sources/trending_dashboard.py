#!/usr/bin/env python3
"""
Trending Topics Dashboard - News Lancashire
Analyzes word frequency and topic trends
Zero AI - pure text analysis
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
OUTPUT_FILE = BASE_DIR / "data/trending_dashboard.json"
HTML_OUTPUT = BASE_DIR / "site/static/trending.html"

# Common words to exclude
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "shall", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "and", "but", "or", "yet", "so", "if", "because", "although",
    "this", "that", "these", "those", "i", "you", "he", "she", "it",
    "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "her", "its", "our", "their", "said", "says", "new", "news"
}

def load_articles():
    with open(ARTICLES_FILE) as f:
        return json.load(f)

def extract_words(text):
    """Extract meaningful words from text"""
    if not text:
        return []
    
    # Lowercase and extract words
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    
    # Filter stop words and numbers
    words = [w for w in words if w not in STOP_WORDS and not w.isdigit()]
    
    return words

def analyze_trends(articles):
    """Analyze trending topics over time"""
    # Group by week
    weekly_words = defaultdict(list)
    all_words = []
    
    for article in articles:
        date_str = article.get("date", "")
        if not date_str:
            continue
        
        try:
            date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            week_key = date.strftime("%Y-W%U")
        except:
            continue
        
        # Extract from title + content
        text = article.get("title", "") + " " + str(article.get("content", ""))
        words = extract_words(text)
        
        weekly_words[week_key].extend(words)
        all_words.extend(words)
    
    return weekly_words, all_words

def calculate_trending(weekly_words):
    """Calculate what's trending up vs down"""
    if len(weekly_words) < 2:
        return []
    
    weeks = sorted(weekly_words.keys())
    
    # Get last 2 weeks
    current_week = weeks[-1]
    prev_week = weeks[-2] if len(weeks) >= 2 else weeks[-1]
    
    current_counts = Counter(weekly_words[current_week])
    prev_counts = Counter(weekly_words[prev_week])
    
    trending = []
    
    for word, count in current_counts.most_common(100):
        if count < 2:  # Ignore rare words
            continue
        
        prev_count = prev_counts.get(word, 0)
        
        if prev_count == 0:
            trend = "new"
            change = "+∞"
        else:
            pct_change = ((count - prev_count) / prev_count) * 100
            if pct_change > 50:
                trend = "rising"
                change = f"+{pct_change:.0f}%"
            elif pct_change < -30:
                trend = "falling"
                change = f"{pct_change:.0f}%"
            else:
                trend = "stable"
                change = f"{pct_change:+.0f}%"
        
        trending.append({
            "word": word,
            "count": count,
            "trend": trend,
            "change": change,
            "previous_count": prev_count
        })
    
    return sorted(trending, key=lambda x: (x["trend"] != "new", x["trend"] != "rising", -x["count"]))

def analyze_borough_trends(articles):
    """Analyze trending topics by borough"""
    borough_topics = defaultdict(Counter)
    
    for article in articles:
        borough = article.get("borough", "unknown")
        text = article.get("title", "") + " " + str(article.get("content", ""))
        words = extract_words(text)
        borough_topics[borough].update(words)
    
    return {b: c.most_common(10) for b, c in borough_topics.items()}

def generate_html(dashboard_data):
    """Generate HTML dashboard"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>News Lancashire - Trending Topics</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 3px solid #c00; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metric {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .trend-new {{ color: #c00; font-weight: bold; }}
        .trend-rising {{ color: #080; font-weight: bold; }}
        .trend-falling {{ color: #888; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #ddd; }}
        th {{ background: #f0f0f0; }}
        .updated {{ color: #666; font-size: 14px; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>📈 News Lancashire - Trending Topics</h1>
    
    <div class="metric">
        <strong>Total Articles Analyzed:</strong> {dashboard_data['total_articles']}<br>
        <strong>Analysis Period:</strong> {dashboard_data.get('weeks_analyzed', 0)} weeks<br>
        <strong>Generated:</strong> {dashboard_data['generated'][:10]}
    </div>
    
    <h2>🔥 Trending Now</h2>
    <table>
        <tr><th>Topic</th><th>Mentions</th><th>Trend</th><th>Change</th></tr>
"""
    
    for item in dashboard_data.get('trending', [])[:20]:
        trend_class = f"trend-{item['trend']}"
        html += f"        <tr><td>{item['word'].title()}</td><td>{item['count']}</td><td class='{trend_class}'>{item['trend'].upper()}</td><td>{item['change']}</td></tr>\n"
    
    html += """    </table>
    
    <h2>📍 Top Topics by Borough</h2>
"""
    
    for borough, topics in list(dashboard_data.get('borough_trends', {}).items())[:10]:
        html += f"    <h3>{borough.replace('_', ' ').title()}</h3>\n    <p>"
        html += ", ".join([f"{word} ({count})" for word, count in topics[:5]])
        html += "</p>\n"
    
    html += f"""
    <p class="updated">Dashboard auto-generated: {dashboard_data['generated']}</p>
</body>
</html>"""
    
    return html

def main():
    print("[Trending Dashboard] Starting analysis...")
    
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    
    # Analyze
    weekly_words, all_words = analyze_trends(articles)
    trending = calculate_trending(weekly_words)
    borough_trends = analyze_borough_trends(articles)
    
    # Top overall words
    top_words = Counter(all_words).most_common(50)
    
    # Build dashboard
    dashboard = {
        "generated": datetime.now().isoformat(),
        "total_articles": len(articles),
        "weeks_analyzed": len(weekly_words),
        "trending": trending[:50],
        "top_words": top_words,
        "borough_trends": borough_trends,
        "weekly_summary": {w: len(words) for w, words in weekly_words.items()}
    }
    
    # Save JSON
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(dashboard, f, indent=2)
    
    # Generate HTML
    html = generate_html(dashboard)
    HTML_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(HTML_OUTPUT, 'w') as f:
        f.write(html)
    
    print(f"[Trending Dashboard] Complete")
    print(f"  JSON: {OUTPUT_FILE}")
    print(f"  HTML: {HTML_OUTPUT}")
    print(f"  Trending topics: {len(trending)}")
    print(f"  Boroughs tracked: {len(borough_trends)}")
    
    # Print summary
    print("\n=== TOP TRENDING ===")
    for item in trending[:10]:
        print(f"  {item['word'].title()}: {item['count']} ({item['trend']})")

if __name__ == "__main__":
    main()