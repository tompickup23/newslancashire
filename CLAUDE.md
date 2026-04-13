# News Lancashire — Project Guide

## What This Is
Independent local news website covering 14 Lancashire boroughs. Astro 5 static site deployed to Cloudflare Pages at newslancashire.co.uk.

## Architecture
- **Stack:** Astro 5 + Tailwind CSS 4 + Preact islands
- **OG Images:** Satori + Sharp (per-article + per-borough)
- **Content:** Astro content collections (markdown articles with Zod-validated frontmatter)
- **Deploy:** `npm run build && npx wrangler pages deploy dist/`
- **Domain:** newslancashire.co.uk (Cloudflare)
- **Design:** Dark glass morphism (#0a0a0a bg, #0a84ff accent), Inter Variable font

## Key Files
- `src/content.config.ts` — Zod schema for articles (13 categories, 15 boroughs)
- `src/data/boroughs.ts` — 14 Lancashire boroughs + lancashire-wide
- `src/data/categories.ts` — 13 news categories with colours
- `src/lib/site.ts` — SITE_NAME, SITE_URL, formatDate, escapeXml
- `src/lib/articles.ts` — articleSlug() and articlePath() helpers (strips .md from IDs)
- `src/layouts/BaseLayout.astro` — Master layout: full SEO, OG, structured data, CSP
- `src/styles/global.css` — CSS custom properties + Tailwind + all component styles
- `src/components/SiteHeader.astro` — Nav with borough dropdown, search, mobile drawer
- `src/components/Footer.astro` — Borough grid, categories, legal links
- `src/pages/og/[...slug].png.ts` — OG image generation via Satori + Sharp
- `src/pages/news-sitemap.xml.ts` — Google News sitemap
- `src/pages/feed.xml.ts` — RSS 2.0 feed

## Content
Articles live in `src/content/articles/` as markdown files with frontmatter:
```yaml
---
headline: "The headline"
date: "2026-04-13"
category: "council"
borough: "burnley"
source: "Source Name"
source_url: "https://..."
interest_score: 78
content_tier: "investigation"
summary: "One-line summary under 200 chars"
fact_check_score: 92
---
Article body in markdown...
```

## URL Structure
- Articles: `/{borough}/{slug}/` (e.g. `/burnley/council-spending-review/`)
- Boroughs: `/{borough}/` (e.g. `/burnley/`)
- Categories: `/{category}/` (e.g. `/politics/`)
- Investigations: `/investigations/`

## Build
```bash
npm run build    # 42+ pages in ~2.5s
npm run dev      # Dev server on port 4325
```

## 14 Boroughs
Burnley, Pendle, Hyndburn, Rossendale, Ribble Valley, Lancaster, Wyre, Fylde, Chorley, South Ribble, Preston, West Lancashire, Blackpool, Blackburn

## Key Rules
1. No emdashes, no semicolons, no AI language (33 banned patterns in style guide)
2. Every claim sourced — use source_url in frontmatter
3. Quality over quantity — only publish articles scoring >= 40 interest
4. Dark theme only — no light mode
5. wrangler NEVER runs on vps-news (1GB, OOM risk)
6. News Burnley stays separate (not merged into borough pages)

## SEO
- NewsArticle + Organization + BreadcrumbList schema on every article
- Google News sitemap at /news-sitemap.xml
- RSS feed at /feed.xml
- Per-article OG images (1200x630) at /og/{borough}/{slug}.png
- Canonical URLs, article:published_time, news_keywords meta

## Pipeline (NOT YET BUILT — Session 2)
vps-news crawlers -> article_engine (two-pass) -> fact_checker -> export_astro -> rsync to vps-main -> npm run build -> wrangler deploy

## Related Projects
- AI DOGE: `/Users/tompickup/clawd/` — 29 councils, spending forensics
- Labour Tracker: `/Users/tompickup/clawd/labour-tracker/` — 403 MP dossiers
- Situation Room: `/Users/tompickup/clawd/situation-room/` — editorial control room
- Style guide: `/Users/tompickup/clawd/burnley-council/scripts/style_guide.json`
- Fact checker: `/Users/tompickup/clawd/burnley-council/scripts/fact_checker.py`
- LLM router: `/Users/tompickup/clawd/burnley-council/scripts/llm_router.py`
