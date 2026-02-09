#!/usr/bin/env python3
"""Re-categorize all existing articles with improved keywords."""
import sqlite3
import json

DB_PATH = "/home/ubuntu/newslancashire/db/news.db"
CONFIG = "/home/ubuntu/newslancashire/config"

# Load categories
with open(CONFIG + "/categories.json", "r") as f:
    data = json.load(f)
categories = data["categories"]
boosters = data.get("interest_boosters", {})

CATEGORY_INTEREST = {
    "politics": {
        "reform": 50, "reform uk": 50, "tom pickup": 50, "cllr pickup": 50,
        "council": 40, "election": 40, "budget": 35, "tax": 35, "council tax": 40,
        "mp": 30, "vote": 30, "labour": 25, "conservative": 25, "lib dem": 20,
        "planning committee": 30, "devolution": 25, "unitary": 25
    },
    "sport": {
        "burnley fc": 45, "turf moor": 40, "premier league": 40, "championship": 35,
        "preston north end": 30, "pne": 30, "blackpool fc": 30, "fleetwood": 25,
        "morecambe": 25, "accrington stanley": 25, "cricket": 20, "cup": 25,
        "transfer": 30, "goal": 20, "manager": 25
    },
    "crime": {
        "murder": 50, "stabbing": 45, "shooting": 45, "court": 40, "crown court": 40,
        "arrest": 35, "drug": 35, "drugs": 35, "robbery": 30, "assault": 30,
        "fraud": 35, "sentence": 30, "jail": 30, "missing": 25, "killed": 40,
        "death": 30, "guilty": 30, "victim": 25
    },
    "business": {
        "jobs": 35, "closure": 30, "regeneration": 30, "investment": 30,
        "opening": 25, "redundancy": 30, "unemployment": 30, "strike": 30, "staff": 20
    },
    "community": {
        "festival": 25, "charity": 25, "volunteer": 20, "fundraiser": 20,
        "award": 20, "memorial": 15, "exhibition": 15
    },
    "transport": {
        "crash": 35, "accident": 35, "m65": 30, "m6": 30, "closure": 30,
        "roadworks": 20, "train": 25, "bus": 20, "pothole": 20
    },
    "health": {
        "nhs": 35, "hospital": 30, "waiting list": 35, "a&e": 30,
        "cancer": 30, "mental health": 25, "gp": 25, "ambulance": 25,
        "beds": 25, "patient": 20, "exercise": 15
    },
    "education": {
        "ofsted": 30, "school": 20, "university": 25, "uclan": 25,
        "gcse": 20, "a-level": 20, "teacher": 20, "headteacher": 25
    },
    "weather": {
        "flood": 40, "flooding": 40, "storm": 35, "warning": 30,
        "snow": 25, "ice": 20, "heatwave": 25
    }
}


def detect_category(text):
    text_lower = text.lower()
    best_cat = "general"
    best_score = 0
    for cat_name, cat_info in categories.items():
        score = 0
        for kw in cat_info["keywords"]:
            if kw in text_lower:
                score += len(kw.split())
        if score > best_score:
            best_score = score
            best_cat = cat_name
    return best_cat


def calc_interest(text, category):
    text_lower = text.lower()
    score = 0
    cat_weights = CATEGORY_INTEREST.get(category, {})
    for kw, weight in cat_weights.items():
        if kw in text_lower:
            score += weight
    for kw, weight in boosters.items():
        if kw in text_lower:
            score += weight
    return min(score, 100)


conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, title, summary, source_type FROM articles").fetchall()
updated = 0
for aid, title, summary, stype in rows:
    summary_text = summary if summary else ""
    full_text = title + " " + summary_text
    new_cat = detect_category(full_text)
    new_interest = calc_interest(full_text, new_cat)
    conn.execute(
        "UPDATE articles SET category = ?, interest_score = ? WHERE id = ?",
        (new_cat, new_interest, aid)
    )
    updated += 1
conn.commit()

# Show distribution
cats = conn.execute(
    "SELECT category, COUNT(*) FROM articles GROUP BY category ORDER BY COUNT(*) DESC"
).fetchall()
print("Re-categorized %d articles:" % updated)
for cat, cnt in cats:
    print("  %s: %d" % (cat, cnt))

# Show top interest
top = conn.execute(
    "SELECT title, category, interest_score, source FROM articles ORDER BY interest_score DESC LIMIT 8"
).fetchall()
print("\nTop 8 by interest:")
for t, c, s, src in top:
    print("  [%3d] %-10s | %.60s (%s)" % (s, c, t, src))

# Show sample from each category
print("\nSample articles per category:")
for cat, _ in cats:
    samples = conn.execute(
        "SELECT title, source FROM articles WHERE category = ? LIMIT 3", (cat,)
    ).fetchall()
    print("  --- %s ---" % cat)
    for t, src in samples:
        print("    %.70s (%s)" % (t, src))

conn.close()
