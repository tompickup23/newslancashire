#!/usr/bin/env python3
"""
Borough Detection Fix - News Lancashire
Retrospectively tags articles with borough based on content analysis
Zero AI - keyword matching only
"""
import json
import re
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"
OUTPUT_FILE = BASE_DIR / "export/articles_borough_fixed.json"

# Borough keywords mapping
BOROUGH_KEYWORDS = {
    "burnley": ["burnley", "padiham", "brierfield", "nelson", "colne", "barnoldswick", "earby"],
    "blackburn": ["blackburn", "darwen", "rishton", "great harwood", "accrington"],
    "blackpool": ["blackpool", "bispham", "layton", "south shore"],
    "preston": ["preston", "fulwood", "ashton", "penwortham", "bamber bridge"],
    "lancaster": ["lancaster", "morecambe", "heysham", "carnforth"],
    "chorley": ["chorley", "leyland", "eccleston", "euxton"],
    "south_ribble": ["south ribble", "penwortham", "bamber bridge", "leyland"],
    "rossendale": ["rossendale", "rawtenstall", "bacup", "haslingden"],
    "hyndburn": ["hyndburn", "accrington", "church", "clayton-le-moors"],
    "pendle": ["pendle", "colne", "nelson", "barnoldswick", "earby"],
    "ribble_valley": ["ribble valley", "clitheroe", "whalley", "longridge"],
    "wyre": ["wyre", "garstang", "poulton", "fleetwood", "thorne"],
    "fylde": ["fylde", "lytham", "st annes", "kirkham"],
    "west_lancashire": ["west lancashire", "skelmersdale", "ormskirk"],
    "bolton": ["bolton", "horwich", "farnworth", "westhoughton"],
    "bury": ["bury", "ramsbottom", "tottington", "prestwich"],
    "wigan": ["wigan", "leigh", "ashton", "atherton"],
    "salford": ["salford", "swinton", "eccles", "walkden"],
    "rochdale": ["rochdale", "middleton", "heywood"],
    "oldham": ["oldham", "saddleworth", "chadderton", "sholver"]
}

def detect_borough(article):
    """Detect borough from article content"""
    text = ""
    
    # Combine all text fields
    for field in ["title", "content", "summary", "excerpt", "tags"]:
        value = article.get(field, "")
        if isinstance(value, list):
            text += " " + " ".join(str(v) for v in value)
        else:
            text += " " + str(value)
    
    text = text.lower()
    
    # Check each borough
    scores = {}
    for borough, keywords in BOROUGH_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
            score += count
        if score > 0:
            scores[borough] = score
    
    # Return borough with highest score
    if scores:
        return max(scores, key=scores.get)
    
    # Check source field
    source = article.get("source", "").lower()
    if "burnley" in source:
        return "burnley"
    elif "blackburn" in source:
        return "blackburn"
    elif "preston" in source:
        return "preston"
    
    return "lancashire"  # Default

def main():
    print("[Borough Detection Fix] Starting...")
    
    with open(ARTICLES_FILE) as f:
        articles = json.load(f)
    
    print(f"Loaded {len(articles)} articles")
    
    # Track changes
    fixed_count = 0
    borough_counts = {}
    
    for article in articles:
        # Only fix if no borough or "unknown"
        current_borough = article.get("borough", "").lower()
        
        if not current_borough or current_borough in ["unknown", "", "all", "lancashire"]:
            detected = detect_borough(article)
            article["borough"] = detected
            article["borough_detected_by"] = "keyword_analysis"
            fixed_count += 1
        else:
            detected = current_borough
        
        borough_counts[detected] = borough_counts.get(detected, 0) + 1
    
    # Save fixed articles
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(articles, f, indent=2)
    
    # Also update original
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=2)
    
    print(f"[Borough Detection Fix] Complete")
    print(f"  Articles fixed: {fixed_count}")
    print(f"  Borough distribution:")
    for borough, count in sorted(borough_counts.items(), key=lambda x: -x[1]):
        print(f"    {borough}: {count}")

if __name__ == "__main__":
    main()