# News Lancashire — Next Steps Plan

## Current State (Feb 2026)

- Live at newslancashire.co.uk, built with Astro v3 (static site)
- 342+ articles across 14 boroughs and 9 categories
- Sources: BBC Lancashire, Lancashire Telegraph, Burnley Express, Blackpool Gazette, LEP, Google News, Parliament data, Police data
- Social feed: Bluesky posts from Lancashire MPs
- AI summaries on every article; AI analysis on high-interest stories
- Automated pipeline updates every 30 minutes
- Free, no ads, no paywalls

---

## Priority 1 — User Experience & Engagement

### 1.1 Working search
The search icon exists in the nav bar but the site needs a functional client-side search (e.g. Pagefind, Fuse.js, or Lunr). This is the most immediately useful feature for returning visitors.

### 1.2 Dark mode
The CSS uses custom properties (`--bg-primary`, `--text-primary`, etc.) which makes adding a dark theme straightforward. Add a toggle in the nav and persist the preference in localStorage.

### 1.3 "Last updated" timestamp
Show a visible "Last updated: X minutes ago" indicator on the homepage so users know content is fresh.

### 1.4 Article date formatting
Replace "Just now" / "3h ago" relative times with a progressive format that shows exact dates for older articles.

---

## Priority 2 — Content & Sources

### 2.1 More social platforms
Expand beyond Bluesky to include posts from Lancashire council accounts, local organisations, and other platforms where public figures post.

### 2.2 Council & planning data
Integrate Lancashire County Council meeting minutes, planning applications, and public consultations. These are high-value for engaged local residents.

### 2.3 Local events
Aggregate event listings from local venues, council event calendars, and community groups.

### 2.4 Live transport data
Integrate real-time road and rail disruption information for Lancashire routes (M6, M65, West Coast Main Line, etc.).

---

## Priority 3 — Growth & Distribution

### 3.1 Newsletter
Email digest (daily or weekly) of top Lancashire stories. Can be built with a simple email service and the existing RSS feed.

### 3.2 PWA support
Add a service worker and web app manifest so the site can be installed on mobile home screens and works offline with cached articles.

### 3.3 Google News inclusion
Submit to Google News Publisher Center. The site already has good structured data (NewsMediaOrganization schema) and an RSS feed — both requirements.

### 3.4 Social media accounts
Create dedicated News Lancashire accounts on Bluesky and other platforms to share articles and build audience.

---

## Priority 4 — Data Journalism

### 4.1 More statistical articles
Expand beyond crime statistics to include:
- House prices by borough
- School Ofsted ratings
- NHS waiting times at Lancashire hospitals
- Employment / benefits data

### 4.2 Borough comparison dashboards
Interactive pages comparing boroughs across key metrics (crime, house prices, schools, health).

### 4.3 Weather integration
Dedicated weather page with Lancashire-specific forecasts beyond what the current weather category covers.

---

## Priority 5 — Technical Improvements

### 5.1 Accessibility audit
Run Lighthouse and axe-core audits. Ensure all interactive elements are keyboard-accessible and screen-reader friendly.

### 5.2 Privacy-respecting analytics
Add a lightweight, cookie-free analytics solution (e.g. Plausible, Umami) to understand which boroughs and categories get the most traffic.

### 5.3 Automated testing
Add tests for the content pipeline to catch issues before they reach production (broken links, missing summaries, malformed HTML).

### 5.4 Image support
Articles currently have no images. Consider adding Open Graph images per article or source logos to improve visual appeal and social sharing.

---

## Recommended starting point

**Search (1.1)** is the highest-impact, lowest-effort next step. Pagefind integrates directly with Astro, indexes at build time, requires no server, and gives users the ability to find articles across 342+ pages immediately.
