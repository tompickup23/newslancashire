# Research: Review LLM chain output — fact accuracy, tone, formatting

Generated: 2026-04-07
Project: news_lancashire

### **Research Brief: LLM Chain Output Review (News Lancashire Project)**

#### **1. Key Findings**
- **LLM Chain Architecture**: The pipeline uses **Gemini Flash → Groq → Kimi K2.5** (9-phase process, paused post-elections).
- **Output Review Needed**: No prior structured validation exists for **fact accuracy, tone, or formatting** in generated articles.
- **Current State**:
  - **GitHub Repo**: [`tompickup23/newslancashire`](https://github.com/tompickup23/newslancashire)
  - **Cloudflare Pages**: Deployed at [newslancashire.co.uk](https://newslancashire.co.uk) & [newsburnley.co.uk](https://newsburnley.co.uk)
  - **Cron Job**: Runs every 30min on `vps-news` (paused until 7 May 2026).

#### **2. Next Steps**
**A. Fact Accuracy Validation**
- **File**: `scripts/validate_facts.py` (if exists) or create new.
- **Action**:
  - Use **Google Fact Check API** ([docs](https://developers.google.com/fact-check/tools/api)) to cross-verify claims.
  - **Command**:
    ```bash
    python scripts/validate_facts.py --input data/raw_articles.json --output data/verified_articles.json
    ```
- **Alternative**: Manual review via **BBC Reality Check** ([link](https://www.bbc.com/news/reality_check)).

**B. Tone & Formatting Check**
- **File**: `pipeline/llm_chain.py` (check for `format_output()` function).
- **Action**:
  - Run **Hugging Face’s `textattack/roberta-base-CoLA`** for tone consistency ([model card](https://huggingface.co/textattack/roberta-base-CoLA)).
  - **Command**:
    ```bash
    pip install textattack
    textattack attack --model roberta-base --dataset cola --recipe cola
    ```
- **Formatting**: Ensure Markdown compliance (check `content/articles/*.md`).

**C. Test Pipeline Locally**
- **File**: `docker-compose.yml` (if used).
- **Action**:
  - Unpause cron temporarily:
    ```bash
    sudo systemctl stop news-pipeline-cron  # Pause
    python scripts/run_pipeline.py --test   # Test run
    sudo systemctl start news-pipeline-cron # Resume
    ```

#### **3. Resources**
- **APIs**:
  - Google Fact Check: [API Docs](https://developers.google.com/fact-check/tools/api)
  - Groq API: [Docs](https://console.groq.com/docs)
- **Tools**:
  - TextAttack (tone validation): [GitHub](https://github.com/QData/TextAttack)
  - Markdown Linter: `npm install -g markdownlint-cli` ([rules](https://github.com/DavidAnson/markdownlint))

#### **4. Risks/Blockers**
- **Paused Pipeline**: Must wait until post-elections (7 May 2026) to resume.
- **API Limits**: Groq/Kimi may throttle requests; monitor via `vps-news` logs (`/var/log/news-pipeline.log`).
- **Fact-Checking Gaps**: Local news may lack structured fact-check APIs; manual review needed.

**Priority**: Validate 10 sample articles before full pipeline restart.