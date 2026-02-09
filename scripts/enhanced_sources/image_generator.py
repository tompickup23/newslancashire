#!/usr/bin/env python3
"""
Article Image Generator - News Lancashire
Generates header images using Pollinations.ai (free)
"""
import json
import requests
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
OUTPUT_DIR = BASE_DIR / "site/static/images/generated"
IMAGE_BASE_URL = "https://image.pollinations.ai/prompt"

def load_articles():
    with open(ARTICLES_FILE) as f:
        return json.load(f)

def generate_image_prompt(title, category, borough):
    """Create image generation prompt from article"""
    base_prompt = f"News illustration: {title}"
    
    # Add style based on category
    styles = {
        "crime": "dramatic news photography style",
        "politics": "professional political illustration",
        "sport": "dynamic sports action",
        "weather": "atmospheric weather scene",
        "community": "warm community photography",
        "business": "modern business illustration",
        "health": "medical healthcare illustration",
        "education": "educational school scene",
        "transport": "urban transport scene"
    }
    
    style = styles.get(category.lower(), "professional news illustration")
    
    # Add location context
    location = borough.replace("_", " ").title() if borough else "Lancashire"
    
    full_prompt = f"{base_prompt}, {style}, {location}, UK, editorial news style, high quality"
    
    return full_prompt

def generate_image(prompt, output_path):
    """Generate image using Pollinations.ai (free)"""
    # URL encode prompt
    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    
    url = f"{IMAGE_BASE_URL}/{encoded_prompt}?width=800&height=400&nologo=true"
    
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            return True
        else:
            print(f"    Image generation failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"    Image error: {e}")
        return False

def main():
    print("[Image Generator] Starting...")
    print("  Using Pollinations.ai (free tier)")
    
    articles = load_articles()
    print(f"  Loaded {len(articles)} articles")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get recent articles without images
    recent_articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[:10]
    
    generated = 0
    
    for article in recent_articles:
        title = article.get("title", "")
        category = article.get("category", "general")
        borough = article.get("borough", "lancashire")
        article_id = article.get("id", hash(title) % 1000000)
        
        # Skip if already has image
        if article.get("image_generated"):
            continue
        
        print(f"  Generating image for: {title[:50]}...")
        
        prompt = generate_image_prompt(title, category, borough)
        output_file = OUTPUT_DIR / f"{article_id}.jpg"
        
        if generate_image(prompt, output_file):
            article["image"] = f"/images/generated/{article_id}.jpg"
            article["image_generated"] = True
            article["image_prompt"] = prompt
            generated += 1
            print(f"    Saved: {output_file}")
        
        # Rate limit
        import time
        time.sleep(3)
    
    # Save updated articles
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=2)
    
    print(f"\n[Image Generator] Complete: {generated} images generated")
    print(f"  Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()