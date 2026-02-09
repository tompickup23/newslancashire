#!/usr/bin/env python3
"""
Postcode Location Tagger - News Lancashire
Improves location tagging using postcodes.io (free UK API)
"""
import json
import re
import requests
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
POSTCODE_CACHE = BASE_DIR / "db/postcode_cache.json"

# Postcodes.io API (free, no key needed)
POSTCODES_API = "https://api.postcodes.io"

LANCASHIRE_AREAS = {
    "BB": "blackburn",      # Blackburn, Burnley, etc.
    "BL": "bolton",         # Bolton, Bury
    "FY": "fylde",          # Blackpool, Fylde
    "LA": "lancaster",      # Lancaster, Morecambe
    "M": "manchester",      # Manchester, Salford
    "OL": "oldham",         # Oldham, Rochdale
    "PR": "preston",        # Preston, South Ribble
    "WN": "wigan",          # Wigan
    "CH": "cheshire",       # Cheshire (edge cases)
    "L": "liverpool",       # Liverpool (edge cases)
}

def load_cache():
    """Load postcode cache"""
    if POSTCODE_CACHE.exists():
        with open(POSTCODE_CACHE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save postcode cache"""
    POSTCODE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(POSTCODE_CACHE, 'w') as f:
        json.dump(cache, f, indent=2)

def extract_postcodes(text):
    """Extract UK postcodes from text"""
    # UK postcode regex
    pattern = r'\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b'
    return re.findall(pattern, text.upper())

def lookup_postcode(postcode, cache):
    """Lookup postcode details from API or cache"""
    normalized = postcode.replace(" ", "").upper()
    
    # Check cache
    if normalized in cache:
        return cache[normalized]
    
    # API lookup
    try:
        url = f"{POSTCODES_API}/postcodes/{normalized}"
        resp = requests.get(url, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            result = {
                "borough": data.get("admin_district", ""),
                "ward": data.get("admin_ward", ""),
                "county": data.get("admin_county", ""),
                "region": data.get("region", ""),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude")
            }
            cache[normalized] = result
            return result
        else:
            cache[normalized] = None
            return None
    except Exception as e:
        print(f"    Postcode lookup failed: {e}")
        return None

def infer_borough_from_postcode(postcode):
    """Infer borough from postcode area"""
    area = postcode[:2] if postcode[1].isdigit() else postcode[:3]
    return LANCASHIRE_AREAS.get(area, "lancashire")

def main():
    print("[Postcode Tagger] Starting...")
    print("  Using postcodes.io (free UK API)")
    
    with open(ARTICLES_FILE) as f:
        articles = json.load(f)
    
    print(f"  Loaded {len(articles)} articles")
    
    cache = load_cache()
    
    updated = 0
    postcode_count = 0
    
    for article in articles:
        # Skip if already has detailed location
        if article.get("location_verified"):
            continue
        
        # Extract text
        text = ""
        for field in ["title", "content", "summary"]:
            value = article.get(field, "")
            if value:
                text += " " + str(value)
        
        # Find postcodes
        postcodes = extract_postcodes(text)
        
        if postcodes:
            postcode_count += len(postcodes)
            print(f"  Found {len(postcodes)} postcode(s) in: {article.get('title', '')[:50]}...")
            
            # Lookup first postcode
            pc = postcodes[0]
            details = lookup_postcode(pc, cache)
            
            if details:
                article["extracted_postcode"] = pc
                article["location"] = {
                    "borough": details.get("borough", ""),
                    "ward": details.get("ward", ""),
                    "latitude": details.get("latitude"),
                    "longitude": details.get("longitude")
                }
                article["location_verified"] = True
                
                # Update borough if empty
                if not article.get("borough"):
                    inferred = infer_borough_from_postcode(pc)
                    article["borough"] = inferred
                
                updated += 1
                print(f"    Tagged: {details.get('borough', 'unknown')}")
            
            # Rate limit
            import time
            time.sleep(0.5)
    
    # Save cache
    save_cache(cache)
    
    # Save articles
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=2)
    
    print(f"\n[Postcode Tagger] Complete:")
    print(f"  Articles updated: {updated}")
    print(f"  Postcodes found: {postcode_count}")
    print(f"  Cache size: {len(cache)} lookups")

if __name__ == "__main__":
    main()