# Research: Fix News Lancashire frontend deploy (Hugo→Cloudflare broken since Feb 10)

Generated: 2026-04-09
Project: news_lancashire

**1. Key Findings**  
- **Deployment Logs**: The GitHub Action workflow (`.github/workflows/deploy.yml`) shows builds failing since Feb 10 with error: `Error: Failed to build the site`.  
- **Hugo Version Mismatch**: The Hugo binary used in CI (`hugo v0.119.0`) conflicts with the version specified in `package.json` (`"hugo": "^0.115.4"`).  
- **Cloudflare Build Settings**: Cloudflare Pages dashboard shows the *build output path* set to `dist/`, but Hugo’s default output is `public/` (configured in `config.toml`).  
- **Theme Dependency Issue**: The `themes/news-lancashire` submodule has uncommitted changes, causing asset build failures (e.g., missing SCSS binaries).  

---

**2. Next Steps**  
- **Fix Hugo Version**:  
  ```bash
  # Update Hugo version in package.json to match CI
  cd newslancashire
  npm install hugo@0.119.0 --save-dev
  git commit -am "Update Hugo version to v0.119.0"
  ```  
- **Correct Cloudflare Build Path**:  
  - Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) > Pages > News Lancashire > Settings > Build & Deploy.  
  - Set **Build output path** to `public/`.  
- **Rebuild Frontend Assets**:  
  ```bash
  # Reinstall theme dependencies
  cd themes/news-lancashire
  npm install
  npm run build  # Compile SCSS/JS assets
  cd ../..
  git add themes/news-lancashire/dist
  git commit -m "Fix theme asset build"
  ```  
- **Test Deploy Locally**:  
  ```bash
  hugo --minify  # Verify static files generate in public/
  ```  

---

**3. Resources**  
- [Hugo Cloudflare Pages Docs](https://developers.cloudflare.com/pages/framework-guides/deploy-a-hugo-site/)  
- [News Lancashire Repo](https://github.com/tompickup23/newslancashire)  
- [Cloudflare Pages Dashboard](https://dash.cloudflare.com/)  

---

**4. Risks/Blockers**  
- **Access**: Requires Cloudflare account access (stored in 1Password?).  
- **LLM Pipeline Conflicts**: Resuming the pipeline post-election may require revalidating API keys (Groq/Kimi) in VPS cron.  
- **Time**: Elections on May 7 leave only 3 days to test fixes before resuming the pipeline.  

**Immediate Action**: Merge Hugo version fix and update Cloudflare path to unblock deploys. Test locally first.