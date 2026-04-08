# Research: Fix News Lancashire LLM fallback chain

Generated: 2026-04-08
Project: news_lancashire

### 1. **Key Findings**  
- **Fallback Chain Logic**: The LLM fallback chain (`Gemini > Groq > Kimi`) is configured in `newslancashire/llm_pipeline/core.py`. The current implementation lacks robust error handling for API rate limits (429) and authentication failures (401).  
- **API Key Issues**: Environment variables for Groq and Kimi K2.5 APIs are stored in `.env` files on the VPS but may have expired. Gemini Flash API keys rotate quarterly.  
- **Pipeline Logs**: Recent logs in `/var/log/newslancashire/llm_pipeline.log` show "429 Too Many Requests" errors for Gemini and uncaught exceptions during Groq fallback.  
- **Cron Job**: The paused pipeline is managed by a cron job at `/etc/cron.d/news_pipeline` with command: `*/30 * * * * root /usr/bin/python3 /root/newslancashire/pipeline_runner.py`.  

---

### 2. **Next Steps**  
**A. Validate API Keys**  
```bash
# Test Gemini API (replace API_KEY with value from .env)
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  https://generativelanguage.googleapis.com/v1beta/models/gemini-flash:generateContent

# Repeat for Groq and Kimi K2.5 APIs using their endpoints/docs
```  

**B. Fix Fallback Logic**  
Update `core.py` to handle 429/401 errors explicitly:  
```python
# newslancashire/llm_pipeline/core.py
def fallback_chain():
    models = ["gemini", "groq", "kimi"]
    for model in models:
        try:
            response = generate_with_model(model)
            if response.status_code in [200, 201]:
                return response
        except APIError as e:
            if e.status_code == 429:  # Rate limit
                continue
            elif e.status_code == 401:  # Auth error
                notify_slack(f"Invalid API key for {model}")
                continue
    raise Exception("All LLMs failed")
```  

**C. Resume Pipeline**  
```bash
# Edit cron job to resume
sudo crontab -e
# Replace "PAUSED" with the original command:
*/30 * * * * root /usr/bin/python3 /root/newslancashire/pipeline_runner.py

# Manually trigger a run
python3 /root/newslancashire/pipeline_runner.py --force
```  

---

### 3. **Resources**  
- **API Docs**:  
  - Gemini: [https://ai.google.dev/api](https://ai.google.dev/api)  
  - Groq: [https://console.groq.ai/docs](https://console.groq.ai/docs)  
  - Kimi K2.5: [https://platform.moonshot.cn/docs](https://platform.moonshot.cn/docs)  
- **Logs**: `/var/log/newslancashire/llm_pipeline.log`  
- **Code Repo**: [GitHub - newslancashire](https://github.com/tompickup23/newslancashire)  

---

### 4. **Risks/Blockers**  
- **Rate Limits**: Gemini Flash quotas reset quarterly; Groq/Kimi may enforce strict RPM limits.  
- **Key Expiry**: API keys for all LLMs may require regeneration (check provider dashboards).  
- **Hugo Build Errors**: Post-election, ensure static site rebuilds correctly on Cloudflare Pages (test with `hugo --minify`).  

---  
**Actions > Docs**: Prioritize API key validation and fallback logic fixes before resuming the cron job. Monitor logs for 24 hours post-restart.