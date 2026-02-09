#!/usr/bin/env python3
"""
NewsAPI Fetcher + Hugging Face Summarizer
Fetches UK news, summarizes with free HF API
Free: NewsAPI (100 req/day) + Hugging Face (no key needed for public models)
"""
import json
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
OUTPUT_DIR = BASE_DIR / "data/newsapi_articles"

# NewsAPI - get free key from newsapi.org
NEWSAPI_KEY = "912ac2e96e294b438c5d076d61de7f3c"  # Replace with real key for production

# Hugging Face - public inference API (free, no key)
HF_SUMMARIZE_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
LANCASHIRE_KEYWORDS = ["Lancashire", "Burnley", "Blackburn", "Preston", "Blackpool"]

def fetch_uk_news(keyword="Lancashire", api_key="demo"):
    """Fetch news from NewsAPI"""
    if api_key == "demo":
        print("  Note: Using demo key (limited). Get free key at newsapi.org")
        return []
    
    url = f"https://newsapi.org/v2/everything?q={keyword}&language=en&sortBy=publishedAt&pageSize=5&apiKey={api_key}"
    
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("articles", [])
        else:
            print(f"NewsAPI error: {resp.status_code} - {resp.text[:100]}")
            return []
    except Exception as e:
        print(f"NewsAPI fetch failed: {e}")
        return []

def summarize_with_hf(text):
    """Summarize text using Hugging Face free API"""
    if not text or len(text) < 100:
        return text
    
    # Truncate to fit model input
    text = text[:1024]
    
    payload = {"inputs": text}
    
    try:
        resp = requests.post(HF_SUMMARIZE_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("summary_text", text[:200])
        # If model is loading or error, return truncated text
        return text[:200] + "..."
    except Exception as e:
        print(f"HF summarization failed: {e}")
        return text[:200] + "..."

def classify_borough(text):
    """Classify which Lancashire borough the article is about"""
    text_lower = text.lower()
    boroughs = {
        "burnley": ["burnley", "padiham", "brierfield"],
        "blackburn": ["blackburn", "darwen"],
        "blackpool": ["blackpool", "fleetwood"],
        "preston": ["preston", "fulwood"],
        "lancaster": ["lancaster", "morecambe"]
    }
    
    for borough, keywords in boroughs.items():
        for kw in keywords:
            if kw in text_lower:
                return borough
    return "lancashire"

def process_article(article):
    """Process single article from NewsAPI"""
    title = article.get("title", "")
    description = article.get("description", "")
    content = article.get("content", "")
    url = article.get("url", "")
    published = article.get("publishedAt", "")
    source = article.get("source", {}).get("name", "NewsAPI")
    
    # Combine text for summarization
    full_text = f"{title}. {description}. {content}"
    
    # Summarize
    summary = summarize_with_hf(full_text)
    
    # Classify borough
    borough = classify_borough(full_text)
    
    return {
        "id": f"newsapi-{hash(url) % 1000000}",
        "title": title,
        "summary": summary,
        "content": content[:500] if content else summary,
        "url": url,
        "date": published[:10] if published else datetime.now().isoformat(),
        "borough": borough,
        "category": "general",
        "source": source,
        "tags": ["newsapi", borough, "uk-news"],
        "original_source": source,
        "ai_summarized": True
    }

def main():
    print("[NewsAPI Fetcher] Starting...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_articles = []
    
    for keyword in LANCASHIRE_KEYWORDS[:2]:  # Limit to save API calls
        print(f"  Fetching news for: {keyword}")
        articles = fetch_uk_news(keyword, NEWSAPI_KEY)
        
        if not articles:
            print("    No articles (demo mode or API limit)")
            continue
        
        for article in articles:
            processed = process_article(article)
            all_articles.append(processed)
            
            # Save individual
            with open(OUTPUT_DIR / f"{processed['id']}.json", 'w') as f:
                json.dump(processed, f, indent=2)
            
            print(f"    Processed: {processed['title'][:60]}...")
            
            # Rate limit HF API
            import time
            time.sleep(2)
    
    # Save index
    with open(OUTPUT_DIR / "index.json", 'w') as f:
        json.dump(all_articles, f, indent=2)
    
    print(f"\n[NewsAPI Fetcher] Complete: {len(all_articles)} articles")
    print("  Note: Get free NewsAPI key at newsapi.org for production use")

if __name__ == "__main__":
    main()