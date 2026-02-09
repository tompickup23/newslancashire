#!/usr/bin/env python3
"""News Lancashire Unified Crawler v3
Fetches RSS + council + Bluesky feeds, auto-detects categories and boroughs,
calculates interest + trending scores. Single source of truth: SQLite."""

import feedparser
import sqlite3
import hashlib
import json
import os
import re
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE      = '/home/ubuntu/newslancashire'
DB_PATH   = f'{BASE}/db/news.db'
LOG_DIR   = f'{BASE}/logs'
CONFIG    = f'{BASE}/config'
EXPORT    = f'{BASE}/export'

RATE_LIMIT = 1.5  # seconds between requests


def normalise_date_iso(date_str):
    """Normalise any date string to ISO 8601 format (YYYY-MM-DDTHH:MM:SS+00:00).
    Handles RFC 2822 (from RSS), ISO 8601 variants, and fallback."""
    if not date_str:
        return datetime.now().isoformat()
    try:
        # Try RFC 2822 first (RSS format: "Sun, 08 Feb 2026 13:14:25 GMT")
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        pass
    try:
        # Try ISO 8601 variants
        cleaned = date_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(cleaned)
        return dt.isoformat()
    except Exception:
        pass
    # Return as-is if we can't parse (better than losing it)
    return date_str

# ─── Logging ─────────────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/crawler_v3.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('crawler_v3')

# ─── Borough Detection ───────────────────────────────────────────────────────
BOROUGHS = {
    'burnley':        ['burnley', 'padiham', 'brierfield', 'hapton', 'worsthorne', 'cliviger', 'pike hill'],
    'pendle':         ['pendle', 'nelson', 'colne', 'barnoldswick', 'barrowford', 'earby', 'trawden', 'foulridge'],
    'rossendale':     ['rossendale', 'rawtenstall', 'bacup', 'haslingden', 'whitworth', 'helmshore', 'waterfoot'],
    'hyndburn':       ['hyndburn', 'accrington', 'oswaldtwistle', 'great harwood', 'rishton', 'clayton-le-moors'],
    'ribble_valley':  ['ribble valley', 'clitheroe', 'longridge', 'whalley', 'read', 'sabden', 'chatburn'],
    'blackburn':      ['blackburn', 'darwen', 'blackburn with darwen'],
    'chorley':        ['chorley', 'adlington', 'euxton', 'coppull', 'whittle-le-woods', 'buckshaw'],
    'south_ribble':   ['south ribble', 'leyland', 'penwortham', 'bamber bridge', 'lostock hall', 'walton-le-dale'],
    'preston':        ['preston', 'fulwood', 'ashton-on-ribble', 'ribbleton', 'deepdale', 'ingol'],
    'west_lancashire': ['west lancashire', 'ormskirk', 'skelmersdale', 'burscough', 'tarleton', 'rufford'],
    'lancaster':      ['lancaster', 'morecambe', 'heysham', 'carnforth', 'silverdale', 'halton'],
    'wyre':           ['wyre', 'fleetwood', 'thornton-cleveleys', 'garstang', 'poulton-le-fylde', 'preesall'],
    'fylde':          ['fylde', 'lytham', 'st annes', 'kirkham', 'freckleton', 'warton'],
    'blackpool':      ['blackpool', 'bispham', 'south shore', 'north shore', 'pleasure beach'],
}


def detect_boroughs(text):
    """Returns dict of is_borough flags."""
    text_lower = text.lower()
    return {f'is_{b}': 1 if any(kw in text_lower for kw in kws) else 0
            for b, kws in BOROUGHS.items()}


def borough_names_for_article(boroughs_dict):
    """Return list of borough names where flag is 1."""
    return [b.replace('is_', '') for b, v in boroughs_dict.items() if v == 1]


# ─── Category Detection ─────────────────────────────────────────────────────
def load_categories():
    """Load categories from config/categories.json."""
    path = f'{CONFIG}/categories.json'
    with open(path, 'r') as f:
        data = json.load(f)
    return data['categories'], data.get('interest_boosters', {})


def detect_category(text, categories):
    """Auto-detect the best category for an article based on keyword matching.
    Returns (category_name, match_score)."""
    text_lower = text.lower()
    best_cat = 'general'
    best_score = 0

    for cat_name, cat_info in categories.items():
        score = 0
        for kw in cat_info['keywords']:
            if kw in text_lower:
                # Longer keywords are more specific → higher weight
                score += len(kw.split())
        if score > best_score:
            best_score = score
            best_cat = cat_name

    return best_cat, best_score


# ─── Interest Scoring ────────────────────────────────────────────────────────
CATEGORY_INTEREST = {
    'politics': {
        'reform': 50, 'reform uk': 50, 'tom pickup': 50, 'cllr pickup': 50,
        'council': 40, 'election': 40, 'budget': 35, 'tax': 35, 'council tax': 40,
        'mp': 30, 'vote': 30, 'labour': 25, 'conservative': 25, 'lib dem': 20,
        'planning committee': 30, 'devolution': 25, 'unitary': 25
    },
    'sport': {
        'burnley fc': 45, 'turf moor': 40, 'premier league': 40, 'championship': 35,
        'preston north end': 30, 'pne': 30, 'blackpool fc': 30, 'fleetwood': 25,
        'morecambe': 25, 'accrington stanley': 25, 'cricket': 20, 'cup': 25,
        'transfer': 30, 'goal': 20, 'manager': 25
    },
    'crime': {
        'murder': 50, 'stabbing': 45, 'shooting': 45, 'court': 40, 'crown court': 40,
        'arrest': 35, 'drug': 35, 'drugs': 35, 'robbery': 30, 'assault': 30,
        'fraud': 35, 'sentence': 30, 'jail': 30, 'missing': 25
    },
    'business': {
        'jobs': 35, 'closure': 30, 'regeneration': 30, 'investment': 30,
        'opening': 25, 'redundancy': 30, 'unemployment': 30, 'startup': 20
    },
    'community': {
        'festival': 25, 'charity': 25, 'volunteer': 20, 'fundraiser': 20,
        'award': 20, 'memorial': 15
    },
    'transport': {
        'crash': 35, 'accident': 35, 'm65': 30, 'm6': 30, 'closure': 30,
        'roadworks': 20, 'train': 25, 'bus': 20, 'pothole': 20
    },
    'health': {
        'nhs': 35, 'hospital': 30, 'waiting list': 35, 'a&e': 30,
        'cancer': 30, 'mental health': 25, 'gp': 25, 'ambulance': 25
    },
    'education': {
        'ofsted': 30, 'school': 20, 'university': 25, 'uclan': 25,
        'gcse': 20, 'a-level': 20, 'teacher': 20
    },
    'weather': {
        'flood': 40, 'flooding': 40, 'storm': 35, 'warning': 30,
        'snow': 25, 'ice': 20, 'heatwave': 25
    }
}


def calc_interest_score(text, category, boosters):
    """Calculate interest score (0-100) from keywords."""
    text_lower = text.lower()
    score = 0

    # Category-specific interest
    cat_weights = CATEGORY_INTEREST.get(category, {})
    for kw, weight in cat_weights.items():
        if kw in text_lower:
            score += weight

    # Global boosters from config
    for kw, weight in boosters.items():
        if kw in text_lower:
            score += weight

    return min(score, 100)


# ─── Trending Score ──────────────────────────────────────────────────────────
SOURCE_WEIGHTS = {
    'BBC Lancashire': 30,
    'Lancashire Telegraph': 25,
    'Burnley Express': 25,
    'Blackpool Gazette': 20,
    'Lancaster Guardian': 20,
    'Lancashire Evening Post': 25,
    'Lancashire County Council': 20,
    'Burnley Council Watch': 30,
    'Reform UK': 35,
}


def calc_trending_score(published_str, source, interest_score, engagement=0):
    """Calculate trending score (0-100)."""
    score = 0

    # Recency (exponential decay)
    try:
        if published_str:
            try:
                pub = parsedate_to_datetime(published_str)
            except Exception:
                pub = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            hours_old = (datetime.now(pub.tzinfo) - pub).total_seconds() / 3600
        else:
            hours_old = 1  # assume recent if no date
    except Exception:
        hours_old = 6  # default moderate recency

    if hours_old < 1:
        score += 50
    elif hours_old < 6:
        score += 40
    elif hours_old < 24:
        score += 25
    elif hours_old < 72:
        score += 10

    # Source importance
    score += SOURCE_WEIGHTS.get(source, 15)

    # Social engagement
    if engagement > 100:
        score += 20
    elif engagement > 50:
        score += 10

    # Interest score influence
    score += int(interest_score * 0.2)

    return min(score, 100)


# ─── Database ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn


def article_exists(conn, link):
    c = conn.execute('SELECT 1 FROM articles WHERE link = ? LIMIT 1', (link,))
    return c.fetchone() is not None


def insert_article(conn, article):
    """Insert a new article with all v3 fields."""
    # Normalise date to ISO 8601 on insert (prevents mixed date formats in DB)
    if 'published' in article:
        article['published'] = normalise_date_iso(article['published'])
    boroughs = article['boroughs']
    conn.execute("""
        INSERT OR IGNORE INTO articles (
            id, title, link, source, source_type, published, summary,
            category, content_tier, interest_score, trending_score,
            social_handle, social_avatar, social_platform, social_engagement,
            search_text,
            is_burnley, is_pendle, is_rossendale, is_hyndburn,
            is_ribble_valley, is_blackburn, is_chorley, is_south_ribble,
            is_preston, is_west_lancashire, is_lancaster, is_wyre,
            is_fylde, is_blackpool
        ) VALUES (
            ?,?,?,?,?,?,?,
            ?,?,?,?,
            ?,?,?,?,
            ?,
            ?,?,?,?,
            ?,?,?,?,
            ?,?,?,?,
            ?,?
        )
    """, (
        article['id'], article['title'], article['link'], article['source'],
        article['source_type'], article['published'], article['summary'],
        article['category'], article.get('content_tier', 'aggregated'),
        article['interest_score'], article['trending_score'],
        article.get('social_handle'), article.get('social_avatar'),
        article.get('social_platform'), article.get('social_engagement', 0),
        article['search_text'],
        boroughs.get('is_burnley', 0), boroughs.get('is_pendle', 0),
        boroughs.get('is_rossendale', 0), boroughs.get('is_hyndburn', 0),
        boroughs.get('is_ribble_valley', 0), boroughs.get('is_blackburn', 0),
        boroughs.get('is_chorley', 0), boroughs.get('is_south_ribble', 0),
        boroughs.get('is_preston', 0), boroughs.get('is_west_lancashire', 0),
        boroughs.get('is_lancaster', 0), boroughs.get('is_wyre', 0),
        boroughs.get('is_fylde', 0), boroughs.get('is_blackpool', 0),
    ))


# ─── RSS Crawler ─────────────────────────────────────────────────────────────
def crawl_rss(feeds, categories, boosters, conn):
    """Crawl RSS + council feeds."""
    total_new = 0

    for feed_info in feeds:
        url = feed_info['url']
        name = feed_info['name']
        source_type = feed_info.get('type', 'rss')

        try:
            log.info('RSS: Fetching %s', name)
            feed = feedparser.parse(url)

            if not feed.entries:
                log.warning('RSS: No entries from %s', name)
                continue

            new_count = 0
            for entry in feed.entries[:20]:
                link = entry.get('link', '')
                title = entry.get('title', '')
                summary = entry.get('summary', '')[:800]

                if not link or not title:
                    continue
                if article_exists(conn, link):
                    continue

                # Clean HTML from summary
                summary = re.sub(r'<[^>]+>', '', summary).strip()

                # Combine text for analysis
                full_text = f"{title} {summary}"

                # Auto-detect category
                category, _ = detect_category(full_text, categories)

                # Auto-detect boroughs
                boroughs = detect_boroughs(full_text)
                borough_list = borough_names_for_article(boroughs)

                # Borough hint from feed config
                focus = feed_info.get('borough_focus', '')
                if focus and focus != 'all' and focus != 'east_lancs':
                    flag = f'is_{focus}'
                    if flag in boroughs:
                        boroughs[flag] = 1
                        if focus not in borough_list:
                            borough_list.append(focus)

                # Parse published date
                published = entry.get('published', '')
                if not published:
                    published = entry.get('updated', datetime.now().isoformat())

                # Calculate scores
                interest = calc_interest_score(full_text, category, boosters)
                trending = calc_trending_score(published, name, interest)

                # Build search text
                search_text = f"{title} {summary} {category} {' '.join(borough_list)}"

                article = {
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'title': title,
                    'link': link,
                    'source': name,
                    'source_type': source_type,
                    'published': published,
                    'summary': summary,
                    'category': category,
                    'interest_score': interest,
                    'trending_score': trending,
                    'search_text': search_text,
                    'boroughs': boroughs,
                }

                insert_article(conn, article)
                new_count += 1

            conn.commit()
            total_new += new_count
            log.info('RSS: %s → %d new articles', name, new_count)

        except Exception as ex:
            log.error('RSS: Error fetching %s: %s', name, ex)

        time.sleep(RATE_LIMIT)

    return total_new


# ─── Bluesky Crawler ─────────────────────────────────────────────────────────
def fetch_json(url, timeout=15):
    """Fetch JSON from URL using urllib (no extra deps needed)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'NewsLancashire/3.0 (news aggregator)',
        'Accept': 'application/json'
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def crawl_bluesky(config, categories, boosters, conn):
    """Crawl Bluesky public API for Lancashire figures' posts."""
    if not config or 'accounts' not in config:
        log.info('Bluesky: No accounts configured')
        return 0

    api_base = config.get('api_base', 'https://public.api.bsky.app/xrpc')
    keywords = [kw.lower() for kw in config.get('lancashire_keywords', [])]
    total_new = 0

    for account in config['accounts']:
        handle = account['handle']
        display_name = account['name']
        borough = account.get('borough', '')
        role = account.get('role', '')

        try:
            log.info('Bluesky: Fetching @%s', handle)
            url = (
                f"{api_base}/app.bsky.feed.getAuthorFeed"
                f"?actor={handle}&limit=10&filter=posts_no_replies"
            )
            data = fetch_json(url)

            new_count = 0
            for item in data.get('feed', []):
                post = item.get('post', {})
                record = post.get('record', {})
                text = record.get('text', '')

                if not text or len(text) < 10:
                    continue

                # Build a unique link for this post
                uri = post.get('uri', '')
                # at://did:plc:xxx/app.bsky.feed.post/xxx → web URL
                parts = uri.split('/')
                if len(parts) >= 5:
                    did = parts[2]
                    post_id = parts[4]
                    link = f"https://bsky.app/profile/{handle}/post/{post_id}"
                else:
                    link = f"https://bsky.app/profile/{handle}"

                if article_exists(conn, link):
                    continue

                # Check if post is Lancashire-relevant (for non-MP accounts)
                text_lower = text.lower()
                is_mp = 'mp' in role.lower() or 'speaker' in role.lower()
                if not is_mp:
                    if not any(kw in text_lower for kw in keywords):
                        continue  # Skip irrelevant posts from non-MPs

                # Use post text as both title and summary
                title = text[:120].replace('\n', ' ').strip()
                if len(text) > 120:
                    title += '...'
                summary = text[:500]

                full_text = f"{display_name} {text}"

                # Category detection
                category, _ = detect_category(full_text, categories)
                if category == 'general' and is_mp:
                    category = 'politics'  # MPs default to politics

                # Borough detection
                boroughs = detect_boroughs(full_text)
                if borough and borough != 'all':
                    flag = f'is_{borough}'
                    if flag in boroughs:
                        boroughs[flag] = 1
                borough_list = borough_names_for_article(boroughs)

                # Published time
                published = record.get('createdAt', datetime.now().isoformat())

                # Engagement
                like_count = post.get('likeCount', 0)
                repost_count = post.get('repostCount', 0)
                engagement = like_count + (repost_count * 2)

                # Scores
                interest = calc_interest_score(full_text, category, boosters)
                if is_mp:
                    interest = min(interest + 15, 100)  # Boost MP posts
                trending = calc_trending_score(published, display_name, interest, engagement)

                # Avatar
                author_data = post.get('author', {})
                avatar = author_data.get('avatar', '')

                search_text = f"{display_name} {text} {category} {' '.join(borough_list)}"

                article = {
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'title': title,
                    'link': link,
                    'source': f"{display_name} (Bluesky)",
                    'source_type': 'bluesky',
                    'published': published,
                    'summary': summary,
                    'category': category,
                    'interest_score': interest,
                    'trending_score': trending,
                    'social_handle': f"@{handle}",
                    'social_avatar': avatar,
                    'social_platform': 'bluesky',
                    'social_engagement': engagement,
                    'search_text': search_text,
                    'boroughs': boroughs,
                }

                insert_article(conn, article)
                new_count += 1

            conn.commit()
            total_new += new_count
            if new_count:
                log.info('Bluesky: @%s → %d new posts', handle, new_count)

        except urllib.error.HTTPError as e:
            if e.code == 400:
                log.warning('Bluesky: @%s not found (400)', handle)
            else:
                log.error('Bluesky: @%s HTTP %d', handle, e.code)
        except Exception as ex:
            log.error('Bluesky: @%s error: %s', handle, ex)

        time.sleep(0.5)  # Be gentle with free API

    return total_new


# ─── Burnley Export ──────────────────────────────────────────────────────────
def export_burnley_json(conn):
    """Export latest Burnley articles as JSON for newsburnley.co.uk."""
    os.makedirs(EXPORT, exist_ok=True)
    c = conn.execute("""
        SELECT title, link, source, published, summary, category,
               interest_score, ai_rewrite, source_type
        FROM articles WHERE is_burnley = 1
        ORDER BY fetched_at DESC LIMIT 50
    """)
    articles = []
    for r in c.fetchall():
        articles.append({
            'title': r[0], 'link': r[1], 'source': r[2],
            'published': r[3], 'summary': r[4], 'category': r[5],
            'interest_score': r[6], 'ai_rewrite': r[7],
            'source_type': r[8]
        })
    path = f'{EXPORT}/burnley-news.json'
    with open(path, 'w') as f:
        json.dump(articles, f, indent=2)
    log.info('Exported %d Burnley articles', len(articles))


# ─── Articles JSON Export (for Astro) ────────────────────────────────────────
def export_articles_json(conn):
    """Export all recent articles as JSON for the Astro site build."""
    os.makedirs(EXPORT, exist_ok=True)
    c = conn.execute("""
        SELECT id, title, link, source, source_type, published, summary,
               ai_rewrite, ai_analysis, content_tier, author, category,
               interest_score, trending_score,
               social_handle, social_avatar, social_platform, social_engagement,
               is_burnley, is_pendle, is_rossendale, is_hyndburn,
               is_ribble_valley, is_blackburn, is_chorley, is_south_ribble,
               is_preston, is_west_lancashire, is_lancaster, is_wyre,
               is_fylde, is_blackpool, fetched_at
        FROM articles
        ORDER BY trending_score DESC, fetched_at DESC
        LIMIT 2000
    """)
    columns = [desc[0] for desc in c.description]
    articles = []
    seen_slugs = {}
    seen_titles = set()
    for row in c.fetchall():
        article = dict(zip(columns, row))
        # Skip duplicate titles (syndicated content appears across multiple feeds)
        title_key = article["title"].lower().strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        # Build boroughs list
        article['boroughs'] = [
            b.replace('is_', '') for b in columns
            if b.startswith('is_') and article.get(b) == 1
        ]
        # Normalise date to ISO 8601
        article['published'] = normalise_date_iso(article.get('published', ''))
        # Generate slug from title (handle unicode, ensure uniqueness)
        import unicodedata
        norm_title = unicodedata.normalize('NFKD', article['title'])
        slug = re.sub(r'[^a-z0-9]+', '-', norm_title.lower()).strip('-')[:80]
        if not slug:
            slug = article['id'][:12]
        # Deduplicate slugs
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{slug}-{seen_slugs[slug]}"
        else:
            seen_slugs[slug] = 0
        article['slug'] = slug
        articles.append(article)

    path = f'{EXPORT}/articles.json'
    with open(path, 'w') as f:
        json.dump(articles, f, indent=2)
    log.info('Exported %d articles to articles.json', len(articles))


# ─── Re-score existing articles ──────────────────────────────────────────────
def rescore_recent(conn, categories, boosters):
    """Re-calculate trending scores for recent articles (they decay over time)."""
    c = conn.execute("""
        SELECT id, title, summary, source, published, category,
               interest_score, social_engagement
        FROM articles
        WHERE fetched_at > datetime('now', '-3 days')
    """)
    updated = 0
    for row in c.fetchall():
        aid, title, summary, source, published, category, interest, engagement = row
        new_trending = calc_trending_score(published, source, interest, engagement)
        conn.execute(
            'UPDATE articles SET trending_score = ? WHERE id = ?',
            (new_trending, aid)
        )
        updated += 1
    conn.commit()
    if updated:
        log.info('Re-scored %d recent articles', updated)


# ─── Cleanup ─────────────────────────────────────────────────────────────────
def cleanup_old(conn, days=30):
    """Remove articles older than N days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c = conn.execute('DELETE FROM articles WHERE fetched_at < ?', (cutoff,))
    if c.rowcount:
        log.info('Cleaned up %d old articles', c.rowcount)
    conn.commit()


# ─── Main ────────────────────────────────────────────────────────────────────
def run():
    start = datetime.now()
    log.info('═══ Crawler v3 started ═══')

    # Load config
    with open(f'{CONFIG}/feeds.json', 'r') as f:
        feeds_config = json.load(f)
    categories, boosters = load_categories()

    conn = get_db()

    # 1. Crawl RSS feeds
    rss_feeds = [
        {**feed, 'type': 'rss'}
        for feed in feeds_config.get('rss', [])
    ]
    rss_new = crawl_rss(rss_feeds, categories, boosters, conn)

    # 2. Crawl council feeds
    council_feeds = [
        {**feed, 'type': 'council'}
        for feed in feeds_config.get('council', [])
    ]
    council_new = crawl_rss(council_feeds, categories, boosters, conn)

    # 3. Crawl Bluesky
    bsky_new = crawl_bluesky(
        feeds_config.get('bluesky', {}),
        categories, boosters, conn
    )

    # 4. Re-score trending (decay over time)
    rescore_recent(conn, categories, boosters)

    # 5. Cleanup old articles
    cleanup_old(conn)

    # 6. Export
    export_burnley_json(conn)
    export_articles_json(conn)

    # Stats
    c = conn.execute('SELECT COUNT(*) FROM articles')
    total = c.fetchone()[0]
    c = conn.execute("SELECT COUNT(*) FROM articles WHERE source_type = 'bluesky'")
    bsky_total = c.fetchone()[0]

    elapsed = (datetime.now() - start).total_seconds()
    log.info(
        '═══ Done: RSS +%d, Council +%d, Bluesky +%d | Total: %d (%d social) | %.1fs ═══',
        rss_new, council_new, bsky_new, total, bsky_total, elapsed
    )

    conn.close()


if __name__ == '__main__':
    run()
