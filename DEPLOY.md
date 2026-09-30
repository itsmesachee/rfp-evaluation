# Deploy to Streamlit Community Cloud

## Prerequisites
- A GitHub account
- Git installed on your machine

## Steps

### 1. Push the project to GitHub
```bash
cd rfp-evaluation
git init
git add .
git commit -m "Agentic RFP Evaluation mini project"
git branch -M main
git remote add origin https://github.com/<your-username>/rfp-evaluation.git
git push -u origin main
```
(Create the empty repo `rfp-evaluation` on github.com first.)

> Note: `rfp_evaluation.db` is git-ignored — the app rebuilds it from
> `init_db.py` on first run in the cloud.

### 2. Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Select repository `rfp-evaluation`, branch `main`, main file path `app.py`.
4. Click **Deploy**. First build takes ~2–5 minutes.

### 3. (Optional) Add your OpenAI key
Without a key the app uses the built-in mock evaluator (fine for the demo).
To use a real LLM you have two options:
- **In the app sidebar**: paste your OpenRouter API key under Settings
  (model defaults to `openai/gpt-4o-mini`) — no redeploy needed, and
- **Via Secrets**: Settings → Secrets → add `OPENAI_API_KEY = "sk-..."`.

The sidebar key takes precedence over secrets.

### 4. Submit
Copy the public URL (e.g. `https://<your-app>.streamlit.app`) and submit it
as required by the brief.

## Verify after deploy
- Criteria section shows 5 criteria totaling 100%.
- Upload the 4 PDFs from `data/sample_pdfs/`, enter metadata, click **Evaluate Batch**.
- Leaderboard + scorecards render; JSON download works.
