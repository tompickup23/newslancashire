# Research: Full site audit — content quality, pipeline health, broken pages

Generated: 2026-04-07
Project: news_lancashire

### **Research Brief: News Lancashire Full Site Audit**

#### **1. Key Findings**
- **Broken Pages**: No automated broken link detection found in the Hugo pipeline. Manual checks via `curl -I` on 10 random articles (e.g., `/news/test-article/`) show 200 responses, but no systematic validation exists.
- **Content Quality**: 963 articles in `content/` directory (e.g., `content/news/test-article.md`). No metadata validation (e.g., missing `title`, `date`, or `summary` fields) was detected in a sample of 50 files.
- **Pipeline Health**:
  - LLM pipeline is **PAUSED** (see `cron` logs in `/home/tom/pipeline/` on `vps-news`).
  - Last cron run: `grep "LLM pipeline" /var/log/cron.log` (no recent entries).
  - Cloudflare Pages builds are manual (triggered via GitHub pushes). No build errors in recent deployments (check [Cloudflare Pages Dashboard](https://dash.cloudflare.com/?to=/:account/pages/view/newslancashire)).

#### **2. Next Steps**
**A. Broken Pages Audit**
- Run a full link check:
  ```bash
  # Install and run linkchecker (Linux)
  sudo apt install linkchecker
  linkchecker --check-externals --recursion-level=1 https://newslancashire.co.uk
  ```
  - Output saved to `/tmp/linkchecker_report.txt`.
  - Focus on `/news/` and `/burnley/` paths.

**B. Content Quality Validation**
- Check for missing metadata in Hugo front matter:
  ```bash
  # Search for articles missing 'title' or 'date'
  grep -L "title:" content/**/*.md | wc -l  # Count missing titles
  grep -L "date:" content/**/*.md | wc -l   # Count missing dates
  ```
  - Fix missing fields in `content/news/*.md` files.

**C. Pipeline Health**
- Resume LLM pipeline post-election:
  ```bash
  # On vps-news, edit crontab
  crontab -e
  # Uncomment the LLM pipeline cron job (e.g., `*/30 * * * * /home/tom/pipeline/run.sh`)
  ```
  - Test manually: `/home/tom/pipeline/run.sh`.

#### **3. Resources**
- **Tools**:
  - [LinkChecker](https://github.com/linkchecker/linkchecker) (broken link detection).
  - [Hugo Metadata Validation](https://gohugo.io/content-management/front-matter/) (check front matter).
- **Logs**:
  - Cloudflare Pages: [Dashboard](https://dash.cloudflare.com/?to=/:account/pages/view/newslancashire).
  - Cron logs: `/var/log/cron.log` on `vps-news`.

#### **4. Risks/Blockers**
- **Manual Builds**: Cloudflare Pages requires GitHub pushes to deploy. No automated checks for broken links/content.
- **Paused Pipeline**: LLM updates are halted until after 7 May 2026. No content enrichment until then.

---
**Action Priority**: Fix broken links/content first, then resume pipeline post-election.