#!/usr/bin/env python3
"""
Category Auto-Tagger - News Lancashire
Rule-based categorization from keywords
Zero AI - keyword matching
"""
import json
import re
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
ARTICLES_FILE = BASE_DIR / "export/articles.json"

# Category rules - keywords mapped to categories
CATEGORY_RULES = {
    "crime": {
        "keywords": ["police", "arrest", "crime", "court", "sentence", "prison", "jail", "theft", "burglary", "robbery", "assault", "drug", "knife", "gun", "officer", "detective", "investigation", "charge", "guilty", "verdict", "trial", "witness", "evidence", "criminal", "offence"],
        "weight": 1.0
    },
    "politics": {
        "keywords": ["council", "mp", "election", "vote", "party", "labour", "conservative", "liberal", "democrat", "reform", "green", "tory", "minister", "government", "parliament", "policy", "budget", "tax", "spending", "funding", "cut", "reform uk", "councillor"],
        "weight": 1.0
    },
    "housing": {
        "keywords": ["house", "housing", "home", "property", "rent", "landlord", "tenant", "council house", "social housing", "planning permission", "development", "building", "construction", "apartment", "flat", "estate", "homeless", "accommodation"],
        "weight": 1.0
    },
    "transport": {
        "keywords": ["road", "traffic", "bus", "train", "rail", "station", "m6", "m65", "m55", "motorway", "highway", "pothole", "parking", "travel", "transport", "commute", "delay", "disruption", "accident", "collision", "crash"],
        "weight": 1.0
    },
    "health": {
        "keywords": ["nhs", "hospital", "health", "doctor", "gp", "surgery", "clinic", "ambulance", "patient", "care", "mental health", "covid", "vaccine", "disease", "illness", "injury", "emergency", "a&e"],
        "weight": 1.0
    },
    "education": {
        "keywords": ["school", "college", "university", "student", "teacher", "pupil", "education", "exam", "gcse", "a-level", "qualification", "academy", "primary", "secondary", "nursery", "ofsted"],
        "weight": 1.0
    },
    "environment": {
        "keywords": ["weather", "flood", "climate", "pollution", "recycling", "waste", "green", "sustainable", "energy", "solar", "wind", "nature", "wildlife", "park", "garden", "tree", "conservation"],
        "weight": 1.0
    },
    "business": {
        "keywords": ["business", "company", "shop", "store", "retail", "job", "employment", "unemployment", "economy", "investment", "startup", "entrepreneur", "profit", "loss", "revenue", "market", "industry"],
        "weight": 1.0
    },
    "community": {
        "keywords": ["charity", "fundraising", "volunteer", "community", "event", "festival", "celebration", "church", "mosque", "religious", "faith", "group", "club", "society", "organization", "neighbourhood"],
        "weight": 1.0
    },
    "sport": {
        "keywords": ["football", "cricket", "rugby", "tennis", "golf", "swimming", "running", "match", "game", "team", "player", "coach", "score", "win", "lose", "draw", "league", "tournament", "championship", "fitness", "gym"],
        "weight": 1.0
    }
}

def categorize_article(article):
    """Auto-categorize article based on keywords"""
    # Combine text
    text = ""
    for field in ["title", "content", "summary", "excerpt"]:
        value = article.get(field, "")
        if value:
            text += " " + str(value)
    
    text = text.lower()
    
    # Score each category
    scores = {}
    for category, rules in CATEGORY_RULES.items():
        score = 0
        for keyword in rules["keywords"]:
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
            score += count * rules["weight"]
        if score > 0:
            scores[category] = score
    
    if not scores:
        return "general"
    
    # Return highest scoring category
    return max(scores, key=scores.get)

def main():
    print("[Category Auto-Tagger] Starting...")
    
    with open(ARTICLES_FILE) as f:
        articles = json.load(f)
    
    print(f"Loaded {len(articles)} articles")
    
    # Track changes
    tagged_count = 0
    category_counts = {}
    
    for article in articles:
        # Only categorize if no category or "general"
        current_cat = article.get("category", "").lower()
        
        if not current_cat or current_cat in ["general", "", "news"]:
            detected = categorize_article(article)
            article["category"] = detected
            article["category_detected_by"] = "keyword_analysis"
            tagged_count += 1
        else:
            detected = current_cat
        
        category_counts[detected] = category_counts.get(detected, 0) + 1
    
    # Save
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=2)
    
    print(f"[Category Auto-Tagger] Complete")
    print(f"  Articles categorized: {tagged_count}")
    print(f"  Category distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")

if __name__ == "__main__":
    main()