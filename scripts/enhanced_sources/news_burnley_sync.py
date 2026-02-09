#!/usr/bin/env python3
"""
News Burnley Auto-Sync
Pulls Burnley-filtered articles from News Lancashire
Deploys to Cloudflare Pages (newsburnley.co.uk)
Zero AI - data filtering only
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

NEWS_LANCS_DIR = Path("/home/ubuntu/newslancashire")
NEWS_BURNLEY_DIR = Path("/home/ubuntu/newsburnley/public")
ARTICLES_SOURCE = NEWS_LANCS_DIR / "export/articles.json"
ARTICLES_DEST = NEWS_BURNLEY_DIR / "burnley-news.json"
INDEX_DEST = NEWS_BURNLEY_DIR / "index.html"

BURNLEY_KEYWORDS = ["burnley", "padiham", "brierfield"]
MAX_ARTICLES = 50

def load_lancashire_articles():
    with open(ARTICLES_SOURCE) as f:
        return json.load(f)

def filter_burnley_articles(articles):
    """Filter for Burnley-related articles"""
    burnley_articles = []
    
    for article in articles:
        borough = article.get("borough", "").lower()
        if borough == "burnley":
            burnley_articles.append(article)
            continue
        
        text = f"{article.get('title', '')} {article.get('content', '')} {article.get('summary', '')}".lower()
        
        for keyword in BURNLEY_KEYWORDS:
            if keyword in text:
                article["borough"] = "burnley"
                burnley_articles.append(article)
                break
    
    burnley_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
    return burnley_articles[:MAX_ARTICLES]

def generate_html(articles):
    """Generate HTML for News Burnley"""
    article_html = ""
    for article in articles:
        title = article.get("title", "Untitled")
        url = article.get("url", "#")
        summary = article.get("summary", article.get("excerpt", "")[:200])
        date = article.get("date", "")[:10]
        source = article.get("source", "News Lancashire")
        category = article.get("category", "News")
        
        article_html += f'''
        <article class="article-card">
            <div class="article-meta">
                <span class="badge">{category}</span>
                <span class="date">{date}</span>
                <span class="source">{source}</span>
            </div>
            <h2><a href="{url}" target="_blank">{title}</a></h2>
            <p class="article-summary">{summary}</p>
        </article>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="en-gb">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News Burnley - Local News, Sport & Community Updates</title>
    <meta name="description" content="Latest Burnley news, sport and community updates. Aggregated from trusted Lancashire sources.">
    <link rel="canonical" href="https://newsburnley.co.uk/">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        :root{{--bg:#0a0a0a;--surface:rgba(28,28,30,0.7);--text:#f5f5f7;--text-secondary:rgba(245,245,247,0.6);--accent:#0a84ff;--border:rgba(255,255,255,0.08);--claret:#8B2635}}
        body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}}
        .container{{max-width:900px;margin:0 auto;padding:0 20px}}
        header{{padding:20px 0;border-bottom:1px solid var(--border);position:sticky;top:0;background:rgba(10,10,10,0.85);backdrop-filter:blur(20px);z-index:100}}
        .header-inner{{display:flex;align-items:center;justify-content:space-between}}
        .logo{{font-size:1.4rem;font-weight:700;color:var(--text);text-decoration:none}}
        .logo span{{color:var(--claret)}}
        .hero{{padding:60px 0 40px;text-align:center}}
        .hero h1{{font-size:clamp(2rem,5vw,3rem);font-weight:700;background:linear-gradient(135deg,var(--text) 0%,var(--claret) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
        .hero p{{color:var(--text-secondary);margin-top:12px}}
        .articles{{padding-bottom:60px}}
        .article-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:16px}}
        .article-card:hover{{border-color:rgba(255,255,255,0.12)}}
        .article-card h2{{font-size:1.15rem;font-weight:600;margin-bottom:8px}}
        .article-card h2 a{{color:var(--text);text-decoration:none}}
        .article-card h2 a:hover{{color:var(--accent)}}
        .article-meta{{display:flex;align-items:center;gap:12px;margin-bottom:10px;font-size:0.8rem}}
        .badge{{background:var(--claret);color:#fff;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:600}}
        .date, .source{{color:var(--text-secondary)}}
        .article-summary{{color:var(--text-secondary);font-size:0.9rem}}
        footer{{padding:40px 0;text-align:center;color:var(--text-secondary);font-size:0.85rem;border-top:1px solid var(--border)}}
        .updated{{margin-top:10px;font-size:0.75rem}}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-inner">
                <a href="/" class="logo">News <span>Burnley</span></a>
                <span style="color:var(--text-secondary);font-size:0.85rem">Auto-synced from News Lancashire</span>
            </div>
        </div>
    </header>
    <main class="container">
        <section class="hero">
            <h1>Burnley News</h1>
            <p>Latest news from Burnley, Padiham & Brierfield</p>
        </section>
        <section class="articles">
            {article_html}
        </section>
    </main>
    <footer>
        <div class="container">
            <p>News Burnley - Aggregated local news</p>
            <p class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </footer>
</body>
</html>'''
    return html

def deploy_cloudflare():
    """Deploy to Cloudflare Pages."""
    env = os.environ.copy()
    env['CLOUDFLARE_API_TOKEN'] = env.get('CLOUDFLARE_API_TOKEN', 'BmINWd_dv9Qiw6Pu3WRu3Wy2V2STEccjZ5AMhXfx')
    env['CLOUDFLARE_ACCOUNT_ID'] = env.get('CLOUDFLARE_ACCOUNT_ID', '35e8f9e8edb5487b97309d107331f7f5')
    
    try:
        result = subprocess.run(
            ['npx', 'wrangler', 'pages', 'deploy', str(NEWS_BURNLEY_DIR),
             '--project-name=newsburnley', '--branch=main'],
            capture_output=True, text=True, timeout=120, env=env
        )
        if result.returncode == 0:
            print(f"[News Burnley Sync] Deployed to Cloudflare Pages")
        else:
            print(f"[News Burnley Sync] Deploy failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"[News Burnley Sync] Deploy error: {e}")

def main():
    print("[News Burnley Sync] Starting...")
    
    all_articles = load_lancashire_articles()
    burnley_articles = filter_burnley_articles(all_articles)
    print(f"Found {len(burnley_articles)} Burnley articles")
    
    NEWS_BURNLEY_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_DEST, 'w') as f:
        json.dump(burnley_articles, f, indent=2)
    
    html = generate_html(burnley_articles)
    with open(INDEX_DEST, 'w') as f:
        f.write(html)
    
    # deploy_cloudflare()  # DISABLED — wrangler OOMs on 1GB vps-news. Deploy via vps-main instead.
    
    print(f"[News Burnley Sync] Complete — {len(burnley_articles)} articles")

if __name__ == "__main__":
    main()
