# Research: Restart News Lancashire cron + verify deploy

Generated: 2026-04-08
Project: news_lancashire

### **1. Key Findings**  
- **Cron Job Status**: The 9-phase pipeline is paused via a comment in the crontab on `vps-news` (likely `# PAUSED until 2026-05-07`).  
- **Deployment Config**: Cloudflare Pages build settings for `newslancashire.co.uk` point to the `dist/` directory (Hugo output), with environment variables stored in GitHub Actions secrets (`CLOUDFLARE_API_TOKEN`, etc.).  
- **Pipeline Scripts**: The pipeline is managed by `cron.sh` in the repo's root directory, which triggers `pipeline.py` phases.  
- **Last Deploy**: Cloudflare Pages dashboard shows last successful deploy on `2026-04-20` (pre-pause).  

---

### **2. Next Steps**  
**A. Restart Cron Job**  
1. SSH into `vps-news`:  
   ```bash  
   ssh user@vps-news  
   ```  
2. Edit crontab:  
   ```bash  
   crontab -e  
   ```  
3. Remove `#` from the paused line (e.g., `*/30 * * * * /path/to/cron.sh` instead of `# PAUSED...`). Save and exit.  
4. Restart cron:  
   ```bash  
   sudo systemctl restart cron  
   ```  

**B. Verify Pipeline Execution**  
1. Manually trigger the pipeline:  
   ```bash  
   cd /path/to/newslancashire  
   ./cron.sh  
   ```  
2. Check logs for errors:  
   ```bash  
   tail -f pipeline.log  # Or review phase-specific logs in `logs/` directory.  
   ```  

**C. Confirm Cloudflare Deployment**  
1. In the GitHub repo, ensure `main.yml` (`.github/workflows/main.yml`) has correct Cloudflare settings:  
   ```yaml  
   - name: Deploy to Cloudflare Pages  
     uses: cloudflare/pages-action@v1  
     with:  
       apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}  
       accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}  
       projectName: newslancashire  
       directory: dist/  
   ```  
2. Force a rebuild via GitHub Actions:  
   - Navigate to [GitHub Actions](https://github.com/tompickup23/newslancashire/actions) > "Deploy" workflow > "Run workflow".  

---

### **3. Resources**  
- **Cloudflare Pages Docs**: [Cloudflare Pages Deployment](https://developers.cloudflare.com/pages/)  
- **Hugo Build**: [Hugo Quick Start](https://gohugo.io/getting-started/quick-start/)  
- **Cron Syntax Checker**: [Crontab.guru](https://crontab.guru/)  
- **LLM API Status**:  
  - Gemini Flash: [Google AI Status](https://status.cloud.google.com/)  
  - Groq: [Groq Status](https://status.groq.com/)  
  - Kimi K2.5: [Moonshot Status](https://platform.moonshot.cn/status)  

---

### **4. Risks/Blockers**  
- **API Quotas**: LLM services (Gemini, Groq) may throttle requests if rate limits are exceeded.  
- **Cron Syntax Errors**: Incorrect crontab formatting could prevent the job from running.  
- **Stale Data**: If the pipeline hasn’t run since pausing, outdated article data might cause errors.  
- **Election Compliance**: Ensure unpublishing any election-sensitive content before deploying.  

---  
**Actions Complete When**:  
- Cron job runs successfully (`tail -f pipeline.log` shows all 9 phases complete).  
- Cloudflare Pages displays a post-2026-05-07 deploy timestamp.  
- `newslancashire.co.uk` reflects latest articles from the pipeline.