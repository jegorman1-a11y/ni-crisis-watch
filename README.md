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

## November 2026: one-screen overview and London Gatwick

The desktop landing page now defaults to a **single-screen overview**, showing the
three dated subjective probability forecasts, candidate signal count, recent source
checks, two linked official headlines, and a London Gatwick (LGW) operations tile.
Use **Full intelligence** or the section navigation to open the original detailed
risk register, assessment rationale, archive, preparedness tracker and source links.
Mobile layouts flow vertically rather than forcing cramped text.

### Flight Watch

Around Me opens on departures for Belfast City, Belfast International, Dublin and
City of Derry. Switch to Gatwick or Arrivals using the board controls. Each row
links to the official airport board. City of Derry has one link for both directions.

The site has no live flight feed configured with permission to republish individual
flight details. Flight Watch displays an explicit unavailable state and links to
the airport boards for flight numbers, routes, times and statuses. The scheduled
dashboard refresh continues to collect Gatwick weather independently.

### Gatwick data integrity

- `scripts/gatwick.py` retrieves the latest **EGKK METAR** (aerodrome weather)
  from NOAA Aviation Weather Center, not a forecast of flight reliability.
- The dashboard always links to the **official Gatwick arrivals and departures**
  boards, which show individual flight delays/cancellations. A separate FlightRadar24
  link provides a convenient third-party delay tracker.
- There is **no authenticated, licensed airport-wide delays/cancellations API**
  configured. Counts are intentionally displayed as *Check official board* rather
  than zero, stale, or fabricated. Weather does not prove flights are running.
- Failed METAR collection is labelled unavailable and never carried forward as a
  current observation. All displayed checks have their own timestamp.
- The GitHub workflow runs `scripts/gatwick.py` on the existing ~two-hour cadence,
  commits `data/gatwick.json`, and Cloudflare Pages publishes the revision.
- While the page stays open, all overview JSON files are rechecked every five minutes;
  this does **not** increase the upstream two-hour collection frequency.

To upgrade your existing GitHub Desktop clone, copy the contents of this ZIP over
existing repository files, retain any existing `data/live.json`, commit and push.
Run the GitHub Action manually once and inspect the **Gatwick weather** log and
Cloudflare deployment. The NOAA endpoint may temporarily throttle/deny requests;
that must display as unavailable, not an all-clear.

### County Down disruptions and daily overview

The overview reads NI-wide Met Office warnings from the existing official feed
and collects TrafficWatchNI incidents and roadworks during the existing refresh.
County Down road matches are based on place names. Provider links open Translink
travel updates and the official power and water postcode checkers.

The browser remembers the last successful snapshot for each source locally. A
notice disappearing from a successful feed is shown as no longer listed.
An unavailable or stale feed never removes notices from the comparison baseline.

The news filter matches crisis-related topics within the regional feeds. Fuel
prices show their individual reporting dates, saved status and the difference
from the previous dated reading when one is available.

### Public Health Watch

The regional tabs show curated, dated official reports from
data/public-health.json. Update the file after checking the original bulletin.
Record a count only when the bulletin reports it for the named area and period.
Use omitted fields for unpublished counts and retain explicit zeroes. Keep
seasonal surveillance and mortality registrations in the seasonal section.
Regional source links provide current advice and bulletins between manual updates.

### Security Watch

Security Watch replaces Flight Watch in the overview. The existing refresh
checks MI5’s two published threat levels and the latest PSNI news listing.
Change dates are taken from the first history entry for the matching level.
If a check fails, the panel labels the last verified levels as saved.
PSNI matches use place names and notice terms in published titles and do not
classify an incident as terrorism. The Garda 2025 assessment and MI5 and MI6
briefings are dated references with links to current official releases.
