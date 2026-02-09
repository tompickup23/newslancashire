#!/usr/bin/env python3
"""
Client-Side Search Generator - News Lancashire
Generates search index and search page
Zero AI - JSON index generation
"""
import json
import re
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
OUTPUT_DIR = BASE_DIR / "site/static"
SITE_URL = "https://newslancashire.co.uk"

def load_articles():
    with open(ARTICLES_FILE) as f:
        return json.load(f)

def create_search_index(articles):
    """Create lightweight search index"""
    index = []
    
    for article in articles:
        title = article.get("title", "")
        summary = article.get("summary", "")[:200]
        
        entry = {
            "id": article.get("id", article.get("url", "")),
            "title": title,
            "url": article.get("url", ""),
            "summary": summary,
            "date": article.get("date", "")[:10],
            "borough": article.get("borough", ""),
            "category": article.get("category", ""),
            "search_text": f"{title} {summary} {article.get('borough', '')} {article.get('category', '')}".lower()
        }
        index.append(entry)
    
    return index

def generate_search_page():
    """Generate HTML search page with client-side JS"""
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search - News Lancashire</title>
    <meta name="description" content="Search News Lancashire articles">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',system-ui,sans-serif;background:#0a0a0a;color:#f5f5f7;line-height:1.6;max-width:900px;margin:0 auto;padding:20px}
        header{padding:20px 0;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:40px}
        .logo{font-size:1.4rem;font-weight:700;color:#f5f5f7;text-decoration:none}
        .logo span{color:#c00}
        .search-box{width:100%;padding:16px 20px;font-size:1.1rem;background:rgba(28,28,30,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;color:#f5f5f7;margin-bottom:30px}
        .search-box:focus{outline:none;border-color:#0a84ff}
        .filters{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
        .filter{padding:8px 16px;background:rgba(28,28,30,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:20px;color:#f5f5f7;cursor:pointer;font-size:0.85rem}
        .filter:hover{border-color:rgba(255,255,255,0.2)}
        .filter.active{background:#c00;border-color:#c00}
        .results{margin-top:20px}
        .result{background:rgba(28,28,30,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:20px;margin-bottom:12px}
        .result h3{font-size:1.1rem;margin-bottom:8px}
        .result h3 a{color:#f5f5f7;text-decoration:none}
        .result h3 a:hover{color:#0a84ff}
        .result-meta{font-size:0.8rem;color:rgba(245,245,247,0.6);margin-bottom:8px}
        .result-summary{font-size:0.9rem;color:rgba(245,245,247,0.8);line-height:1.5}
        .badge{display:inline-block;padding:3px 10px;background:#c00;border-radius:20px;font-size:0.75rem;margin-right:5px}
        .no-results{text-align:center;padding:40px;color:rgba(245,245,247,0.6)}
        .stats{font-size:0.85rem;color:rgba(245,245,247,0.6);margin-bottom:20px}
    </style>
</head>
<body>
    <header>
        <a href="/" class="logo">News <span>Lancashire</span></a>
    </header>
    
    <h1 style="margin-bottom:20px">Search Articles</h1>
    
    <input type="text" class="search-box" id="searchInput" placeholder="Search news, topics, boroughs..." autocomplete="off">
    
    <div class="filters" id="boroughFilters">
        <span class="filter active" data-borough="">All</span>
    </div>
    
    <div class="stats" id="stats"></div>
    
    <div class="results" id="results">
        <div class="no-results">Start typing to search...</div>
    </div>
    
    <script>
        let articles = [];
        let currentBorough = '';
        
        fetch('search_index.json')
            .then(r => r.json())
            .then(data => {
                articles = data;
                setupFilters();
                document.getElementById('stats').textContent = articles.length + ' articles indexed';
            })
            .catch(err => console.error('Failed to load index:', err));
        
        function setupFilters() {
            const boroughs = [...new Set(articles.map(a => a.borough).filter(Boolean))].sort();
            const container = document.getElementById('boroughFilters');
            boroughs.forEach(b => {
                const span = document.createElement('span');
                span.className = 'filter';
                span.textContent = b.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                span.dataset.borough = b;
                span.onclick = () => setBorough(b, span);
                container.appendChild(span);
            });
        }
        
        function setBorough(borough, element) {
            currentBorough = borough;
            document.querySelectorAll('.filter').forEach(f => f.classList.remove('active'));
            element.classList.add('active');
            performSearch();
        }
        
        function performSearch() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const resultsDiv = document.getElementById('results');
            
            if (!query && !currentBorough) {
                resultsDiv.innerHTML = '<div class="no-results">Start typing to search...</div>';
                return;
            }
            
            let filtered = articles;
            
            if (currentBorough) {
                filtered = filtered.filter(a => a.borough === currentBorough);
            }
            
            if (query) {
                filtered = filtered.filter(a => 
                    a.search_text.includes(query) ||
                    a.title.toLowerCase().includes(query)
                );
            }
            
            filtered.sort((a, b) => b.date.localeCompare(a.date));
            filtered = filtered.slice(0, 50);
            
            if (filtered.length === 0) {
                resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
                return;
            }
            
            resultsDiv.innerHTML = filtered.map(function(a) {
                var boroughBadge = a.borough ? '<span class="badge">' + a.borough.replace(/_/g, ' ') + '</span>' : '';
                var catBadge = a.category ? '<span class="badge" style="background:#555">' + a.category + '</span>' : '';
                return '<div class="result">' +
                    '<div class="result-meta">' + boroughBadge + catBadge + '<span>' + a.date + '</span></div>' +
                    '<h3><a href="' + a.url + '" target="_blank">' + a.title + '</a></h3>' +
                    '<p class="result-summary">' + a.summary + '</p>' +
                '</div>';
            }).join('');
        }
        
        let timeout;
        document.getElementById('searchInput').addEventListener('input', function(e) {
            clearTimeout(timeout);
            timeout = setTimeout(performSearch, 200);
        });
    </script>
</body>
</html>'''
    
    return html

def main():
    print("[Search Generator] Starting...")
    
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    
    index = create_search_index(articles)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "search_index.json", 'w') as f:
        json.dump(index, f)
    print(f"  Search index: {OUTPUT_DIR}/search_index.json ({len(index)} entries)")
    
    html = generate_search_page()
    with open(OUTPUT_DIR / "search.html", 'w') as f:
        f.write(html)
    print(f"  Search page: {OUTPUT_DIR}/search.html")
    
    print(f"\n[Search Generator] Complete")
    print(f"  Articles indexed: {len(index)}")
    print(f"  Search URL: {SITE_URL}/search.html")

if __name__ == "__main__":
    main()