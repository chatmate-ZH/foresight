# Deployment & Submission Guide

You now have a complete, working repo (`foresight/`). This tells you exactly how to get the
shareable links the submission form asks for. Nothing here needs code changes — just accounts.

## 1. Push the code to GitHub (needed for almost everything else)

```bash
cd foresight
git init
git add .
git commit -m "Project FORESIGHT — initial submission"
```
Create a new repo on github.com (public, or private + add your mentor as a collaborator), then:
```bash
git remote add origin https://github.com/<you>/foresight.git
git branch -M main
git push -u origin main
```
This is your **D1 repository link** and satisfies the "Repository & notebooks" submission criterion.

## 2. Deploy the dashboard (D5) — Streamlit Community Cloud (free, easiest)

1. Go to https://share.streamlit.io and sign in with GitHub.
2. "New app" → pick your `foresight` repo, branch `main`, main file path `app/app.py`.
3. Before it can load real numbers, the pipeline outputs need to exist in the deployed environment.
   Streamlit Cloud runs `requirements.txt` automatically, but it won't run your pipeline scripts —
   add a tiny `app/app.py` startup step, **or** simpler: commit the generated `data/processed/*`
   files to the repo just for deployment purposes (remove them from `.gitignore`), so the dashboard
   has data to read the moment it boots. Either approach is fine; the second is faster to ship.
4. Deploy. You'll get a URL like `https://<yourapp>.streamlit.app` — that's your **D5 dashboard link**.

*(Alternative: Hugging Face Spaces with the "Streamlit" SDK works the same way — push the repo, add
a `requirements.txt`, and it builds automatically.)*

## 3. Deploy the scoring service (D6) — Render (free tier) or Hugging Face Spaces

**Render:**
1. https://render.com → New → Web Service → connect your GitHub repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn service.main:app --host 0.0.0.0 --port $PORT`
4. Same data note as above — commit `data/processed/*` so the service has something to serve.
5. Deploy. You'll get a URL like `https://foresight-api.onrender.com` — test `/health` and `/docs`.
   That's your **D6 scoring service link**.

## 4. Record the demo video (3–5 minutes)

A simple script that covers everything the acceptance criteria (Section 13) ask for:
1. (30s) The brief in your own words — NorthBay's stockout/overstock problem.
2. (60s) Run `python src/pipeline.py` and show the data-quality log — what was messy, how you fixed it.
3. (60s) Show `reports/backtest_results.json` or the chart — model vs. baseline WAPE, honestly.
4. (60s) Walk through the live dashboard — decisioning grid, reorder list, one SKU detail view.
5. (30s) Hit the scoring API `/score/{sku_id}` live (or via `/docs`), show it returns forecast + risk.
6. (30s) Close with the rupee impact numbers from the executive deck.

Record with Loom (unlisted, free) or OBS → upload to YouTube (unlisted) → that's your **demo video link**.

## 5. Submission checklist

- [ ] GitHub repo link (public or mentor has access)
- [ ] Live dashboard URL (Streamlit Cloud / HF Spaces)
- [ ] Live scoring service URL (Render / HF Spaces)
- [ ] `README.md` — already written, includes problem, data, setup, backtest result, assumptions
- [ ] `reports/Executive_Readout.pptx` — already built
- [ ] `reports/EDA_insight_memo.md` — already written
- [ ] Demo video (unlisted link)
- [ ] Cohort submission form with all the above links

Check every link in an incognito window before submitting — no login prompts allowed.
