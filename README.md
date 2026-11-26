# UK & Northern Ireland Crisis Watch — automatic public-source edition

A responsive, static, free-to-host dashboard. Original probability estimates remain explicitly **editorial snapshots**; the separate "Automatic source updates" area receives new public-feed titles and links from an automated GitHub Actions workflow.

## Deploy — no coding required

1. Create a **public GitHub repository** (e.g. `ni-crisis-watch`) and upload the *contents* of this folder, including the `.github` folder. GitHub's web uploader may hide dotfiles; verify `.github/workflows/refresh.yml` appears in the repository. Alternatively use `git push`.
2. On GitHub, open **Settings → Actions → General → Workflow permissions** and enable **Read and write permissions** for `GITHUB_TOKEN`. Allow Actions to run. If your organisation disallows this, use a personal repository or an alternative deploy process.
3. Open **Actions → Refresh public-source dashboard → Run workflow**. It fetches available feeds, writes `data/live.json`, runs tests and commits the result. Check the run log for sources marked `unavailable`.
4. On **Cloudflare → Workers & Pages → Create → Pages → Connect to Git**, select that repository. Build command: leave empty (or `exit 0`). Output directory: `/` (repository root, sometimes entered as `.`). Deploy. Cloudflare automatically redeploys on data-file commits.
5. Open the public `*.pages.dev` URL. Automatic checks are configured for **07 minutes past every second hour**, but GitHub scheduled jobs may start late or be skipped under load; the site is **periodically updated, not real-time**. This also depends on Cloudflare build and propagation time.

## What updates, and what does not

- **Automatic:** linked public announcements from Met Office Northern Ireland warnings and selected health and education agency feeds, where their published RSS/Atom endpoints work. Each feed shows whether its fetch succeeded, with a timestamp. An unavailable source remains visibly unavailable. These feeds may change endpoints or block automation.
- **Manual/editorial:** the forecast percentages, risk labels, government preparedness tracker and dated analysis from the original 25 November snapshot. They will **not** change merely because a headline appears. Update the `<script id="snapshot">` JSON in `index.html` after an evidence-based review. A ChatGPT scheduled task cannot write into your GitHub repository automatically.
- **Not currently ingested:** live NIE outages, NI Water property-level status, WHO case counts, legislation and government procurement datasets, HSC operational directives, real-time price feeds, or AI-authored commentary. These require dedicated reliable integrations and often API keys/permissions. The site links to the relevant official pages. Don't describe them as live feeds until integrated and tested.

## Local testing

```bash
python -m unittest discover -s tests -v
python scripts/update.py     # requires internet; produces data/live.json
python -m http.server 8000
# Open http://localhost:8000
```

The initial `data/live.json` intentionally has no update timestamp. It is **not** a fake live reading. In the browser the source block shows "not configured" until the workflow successfully runs.

## Safety and transparency

The website is unaffiliated with public authorities. It must not imply an official emergency has been declared without an exact source. Weather warning feeds are **regional**, not proof a specific BT33 address is affected. Published source headlines may be incorrect, preliminary, duplicated or delayed. Confirm the original publication before deciding on action. A failed feed is never equivalent to zero threats. This is not an emergency alerting service; always consult Met Office, local utility operators and emergency services directly.

## Costs

Static hosting and ordinary scheduled public-repository GitHub Actions usage can fit free plans subject to platform terms, quotas, security requirements and future changes. No OpenAI API usage or paid API keys are required for the automatic-source edition.

## Automated intelligence upgrade (November 2026)

The `scripts/analyse.py` stage runs after `scripts/update.py`. It creates `data/assessment.json`, a candidate escalation analysis, and `data/reports.json` with archive records under `data/archive/` (one Monday summary even when nothing notable is found, and material candidate updates on other days). GitHub commits those files, and Cloudflare Pages automatically redeploys them. The browser checks fresh files every five minutes and on tab reactivation. Use the refresh button for an immediate fetch.

**Limits and safeguards:** The basic free implementation is **rules-based screening**, not an LLM intelligence analyst, an emergency authority, or exhaustive monitoring of all the requested agencies. It currently searches headline patterns in configured primary-source feeds and requires corroboration between distinct source feeds for a maximum +1 percentage point (12-month) and +2 percentage points (five-year) provisional infrastructure/restrictions adjustments. It deliberately cannot automatically change the nationwide-lockdown baseline from headline-only evidence. It does not treat unavailable feeds as reassuring. Forecasts are subjective and uncalibrated. Weekly archived records are *automated source digests*, not independently researched reports. The original ChatGPT weekly reports are **not** automatically imported. All percentages remain conditional on source coverage and should never drive emergency decisions alone.

To add actual **AI-powered intelligence reports** and broad procurement/legislation/WHO/NCSC coverage, a separate verified data-ingestion pipeline, optional API key with spending limits and human review for urgent determinations are required. Do not insert private API keys into public HTML or commit them to GitHub.

### How to update existing GitHub repository

Use GitHub's web UI to upload files and directories from this package into the root of `jegorman1-a11y/ni-crisis-watch`, replacing existing files, including `.github/workflows/refresh.yml`. GitHub's web upload may not overwrite existing paths in one action; edit/replace files one by one or use GitHub Desktop to commit the contents. Keep `index.html` and `data/` at repository root. Verify the Actions job and Cloudflare production deployment both succeed. Check `data/assessment.json` after the job for a valid `generated_at` and make sure the archive is created on Mondays. Automated commits must **not** include `[skip ci]`.
