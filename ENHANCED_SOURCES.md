# Enhanced News Sources - Outside the Box Analysis

## Executive Summary

This document outlines unconventional and alternative news sources for News Lancashire, designed to:
1. Reduce dependency on legacy media
2. Generate original data-driven journalism
3. Capture alternative voices (podcasters, creators, community figures)
4. Exploit publicly available data that others ignore

## Current Legacy Media Dependence

**Existing RSS Feeds (Legacy/Corporate):**
- BBC Lancashire (state broadcaster)
- Lancashire Telegraph (Reach PLC - hedge fund owned)
- Burnley Express (same)
- Blackpool Gazette (same)
- Lancaster Guardian (same)
- LEP (same)

**Problem:** All owned by same 2-3 corporations, same editorial line, declining quality.

## NEW SOURCE CATEGORIES

### 1. DATA-DRIVEN ORIGINAL JOURNALISM (Highest Priority)

**Sources We Already Collect (But Don't Turn Into Stories):**

| Data Source | Story Type | Frequency | Implementation |
|-------------|------------|-----------|----------------|
| Police API crime stats | Monthly crime reports | Monthly | data_journalist.py |
| AI DOGE spending data | Weekly spending digests | Weekly | data_journalist.py |
| GOV.UK budget data | Quarterly budget analysis | Quarterly | data_journalist.py |
| Planning applications | Development tracker | Daily | NEW - scraper |
| Council meeting minutes | Decision alerts | Real-time | NEW - PDF scraper |

**Impact:** 100% original content, zero aggregation, competitive advantage.

### 2. ALTERNATIVE VOICES (High Priority)

**YouTube Creators:**
- June Slater (political commentary)
- Reform UK Lancashire channels
- Independent Lancashire creators
- Local business vlogs
- Community group channels

**Podcasts:**
- Lancashire-focused shows
- Political commentary
- Business interviews
- Community discussions

**Substack/Newsletters:**
- Independent writers
- Niche community voices
- Local business newsletters

**Implementation:** RSS feeds + transcription (Whisper) + segment extraction

### 3. REGULATORY & PUBLIC SAFETY (Medium Priority)

**Food Hygiene (FSA API):**
- New 0-2 star ratings (urgent)
- Restaurant closures
- Re-inspections
- **API:** http://api.ratings.food.gov.uk
- **Cost:** Free

**Health & Care (CQC API):**
- Care home inspection reports
- Hospital ratings
- GP practice updates
- **API:** https://api.cqc.org.uk
- **Cost:** Free

**Education (Ofsted):**
- School inspection reports
- Rating changes
- New academy conversions
- **Source:** RSS feeds
- **Cost:** Free

**Emergency Services:**
- Fire service incidents (Lancashire Fire & Rescue publishes daily)
- Lifeboat launches (RNLI Morecambe, Blackpool)
- Mountain rescue (Bowland, Pendle Hill)

### 4. INFRASTRUCTURE & TRANSPORT

**Traffic & Roads:**
- Traffic England API (M65, M6, A56 incidents)
- Roadworks.org (planned closures)
- National Rail API (Northern Rail disruptions)
- Bus tracking (Blackburn Bus Company, Transdev)

**Utilities:**
- Power cuts (Electricity North West)
- Water outages (United Utilities)
- BT/Openreach faults

**Environment:**
- Air quality (Defra stations in Lancaster, Preston, Blackpool)
- River levels (Calder, Ribble, Wyre, Lune)
- Flood warnings (Environment Agency)
- Met Office weather warnings
- Pollen counts (summer months)

### 5. LEGAL & JUSTICE

**Courts:**
- Court listings (Burnley Magistrates daily)
- Crown Court hearings
- Tribunal decisions (employment, housing)
- Planning appeals (Planning Inspectorate)

**Companies:**
- New incorporations (Companies House streaming API)
- Insolvencies (The Gazette)
- Liquidations, bankruptcies
- Director appointments/resignations

**Property:**
- Land Registry price paid data (monthly)
- Major transactions (£1M+)
- New build registrations

### 6. COMMERCIAL INTELLIGENCE

**Business Signals:**
- Job postings (Indeed API, Reed)
- LinkedIn company updates
- Glassdoor reviews (sentiment shifts)
- Google Business Profile changes (openings/closures)
- Charity Commission (new charities, annual returns)

**Retail & Hospitality:**
- Opening Soon signs (Street View changes)
- Lease boards (commercial property)
- Pub/shop closures
- Restaurant openings

### 7. SOCIAL SIGNALS

**Community Intelligence:**
- Reddit r/Lancashire, r/Burnley (hot posts, sentiment)
- Nextdoor (community concerns - scraper)
- Facebook groups (public posts)
- X/Twitter lists (Lancashire politicians, activists)

**Fundraising & Petitions:**
- GoFundMe (local tragedies, community projects)
- Change.org (Lancashire petitions trending)
- Crowdfunder (local business campaigns)

**Events:**
- Eventbrite (local events)
- Meetup (community groups)
- Facebook Events (public)

### 8. CULTURAL & SPORT

**Football:**
- Burnley FC fixtures, results
- Blackpool FC
- Preston North End
- Accrington Stanley
- Non-league: Nelson, Colne, etc.

**Entertainment:**
- Gig listings (Ticketmaster, Songkick, Bandcamp)
- Theatre shows (King George's Hall, etc.)
- Museum exhibitions
- Library events

### 9. OBSCURE/ESOTERIC (Differentiation)

**Unusual but Newsworthy:**
- **Aurora alerts** (visible from Lancashire during solar storms)
- **Seismic data** (British Geological Survey - tracking quakes/fracking)
- **FlightRadar24** (unusual aircraft over Lancashire)
- **Satellite imagery** (Sentinel-2 - land use changes, development)
- **Shipping AIS** (Heysham port activity)

**Government Data:**
- FOI request logs (what others are asking)
- GDPR breach notifications (ICO)
- ONS neighbourhood statistics
- Census 2021 updates

### 10. AUDIO MINING

**Radio Monitoring:**
- BBC Radio Lancashire (automated capture)
- Key interview transcription
- Breaking news detection

**Podcast Search:**
- Apple Podcasts API
- Spotify for Podcasters
- Transcribe Lancashire mentions

## IMPLEMENTATION ROADMAP

### Phase 1: Immediate (This Week)
- [x] YouTube RSS crawler
- [x] Data journalist (crime, spending, budgets)
- [ ] Add channel IDs for June Slater etc.
- [ ] Integrate into pipeline_v3.sh

### Phase 2: Short-term (Next 2 Weeks)
- [ ] Food hygiene API integration
- [ ] Traffic England API
- [ ] Court listings scraper
- [ ] Planning applications scraper

### Phase 3: Medium-term (Next Month)
- [ ] Companies House streaming
- [ ] Reddit monitoring
- [ ] GoFundMe/Change.org tracking
- [ ] Job posting aggregator

### Phase 4: Experimental
- [ ] Radio audio mining
- [ ] Satellite imagery analysis
- [ ] Social graph analysis
- [ ] Predictive news detection

## COMPETITIVE ADVANTAGES

1. **Data Originality:** No other Lancashire news source has AI DOGE spending data
2. **Alternative Voices:** Legacy media ignores YouTubers/podcasters
3. **Regulatory Alerts:** FSA/CQC data is public but underutilised
4. **Speed:** API-driven beats RSS by hours
5. **Granularity:** Ward-level crime, not just borough-level

## COST ANALYSIS

| Source Type | Implementation Cost | Running Cost | Content Value |
|-------------|---------------------|--------------|---------------|
| Data-driven | Dev time | £0 | Very High |
| YouTube | Dev time | £0 | High |
| FSA/CQC | Dev time | £0 | Medium |
| Traffic | Dev time | £0 | Medium |
| Courts | Dev time | £0 | High |
| Companies House | Dev time | API key | Medium |
| Reddit | Dev time | £0 | Low-Medium |
| Audio mining | Dev time + Whisper | £0 | High |

**Total: Zero ongoing API costs for most sources.**

## CONTENT MIX PROJECTION

**Current (Legacy Dependent):**
- 80% legacy media aggregation
- 20% social/Bluesky

**Target (Diversified):**
- 30% data-driven originals
- 20% alternative voices
- 20% regulatory alerts
- 20% legacy aggregation (for breaking news)
- 10% community intelligence

**Result:** 70% unique/original content, 30% aggregation.

## NEXT STEPS

1. **Add YouTube channel IDs** for June Slater and other Lancashire creators
2. **Test data journalist** - run manually, verify output
3. **Integrate into pipeline** - add to cron schedule
4. **Build FSA crawler** - food hygiene alerts
5. **Scrape planning portals** - all 14 Lancashire councils

---

*Document created: 2026-02-07*
*Status: Phase 1 implementation in progress*
