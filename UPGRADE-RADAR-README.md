# NI Crisis Watch — Radar, weather, news & fuel patch

This **patch** upgrades your existing `jegorman1-a11y/ni-crisis-watch` project. Copy the *contents* of the ZIP into your local GitHub Desktop repository. It does **not** replace your `data/live.json`, `data/assessment.json`, `data/reports.json`, `data/archive/` or any historical records.

## New dashboard sections

- **Aircraft radar**: defaults to **Around me (County Down)**, focused approximately on Seaforde. Toggle to Gatwick. The third-party AvioADSB map is intentionally provided by an embedded official widget; it refreshes aircraft positions separately from GitHub Actions. Aircraft visibility depends on volunteer receiver coverage and it is not an aviation safety service. If the embedded map is blocked, use the widget website. Location is a fixed regional default, *not* your live phone location. The AvioADSB attribution/banner must remain visible under its terms.
- **16-day forecasts**: County Down and London, supplied by Open-Meteo and collected every scheduled run. Days 8–16 have substantial uncertainty. This is model output, **not** an official weather warning. Met Office warning link is retained.
- **News and politics**: UK, Northern Ireland and Republic of Ireland tabs. Five most recent items from successfully retrieved, dated RSS feeds (BBC, RTÉ, and a Google News RTÉ/Irish Times search fallback). This is *recency selection*, not editorial ranking or fact-checking. Stale/future-dated items excluded. Empty or failed feeds are visibly unavailable, not a false ‘no news’ statement.
- **NI oil, petrol and diesel**: strictly parsed published Northern Ireland *average* prices from the Consumer Council. Heating oil shown in **£ for 900 litres**, petrol and diesel in **pence/litre**. These are not a live supplier quote or closest filling-station prices. If the Consumer Council changes its page, fields show **Unavailable** rather than guessed numbers. Source links are always shown.

## Deploy using GitHub Desktop

1. In GitHub Desktop click **Pull origin** before copying the patch, so the local clone includes the latest automated data commits.
2. Extract the ZIP and copy its contents into the local repository folder, retaining folder paths. Replace `index.html` and `.github/workflows/refresh.yml`. Add `scripts/extended.py`, `tests/test_extended.py`, and this document. **Do not overwrite the existing `data/` directory.**
3. Commit as `Add live aircraft radar, weather, news and NI fuel prices`; click **Push origin**. If an automated Actions commit has appeared in the meantime, **Pull origin** again, resolve any conflict, and push.
4. Open your GitHub **Actions → Refresh public-source dashboard** workflow, select **Run workflow** on `main`. It now runs `scripts/extended.py` and publishes `data/extended.json` to GitHub; Cloudflare Pages automatically deploys the new commit. Confirm the `extended.py` line succeeded and the page shows a fresh collection timestamp.
5. Open https://ni-crisis-watch.pages.dev and refresh. Browser rechecks the JSON every five minutes while the page is open; source collection runs on the existing ~two-hour GitHub schedule.

## Accuracy and security

No private GitHub/API token is needed. Never put secrets in `index.html`. The radar uses a third-party embedded map and its own network requests; the page also requests map tiles as part of that widget. All news links open publishers in new tabs. The source collector uses timeouts and only outputs validated data. No individual flight delay/cancellation numbers are inferred from radar positions or weather.

## Troubleshooting

- **Map blank:** Third-party iframe may be blocked by the browser/provider; open the radar provider's widget page and confirm the embed code, or check its coverage for County Down. This external map may change independently.
- **Weather unavailable:** Open the `extended.py` step log, and check Open-Meteo. Do not treat an unsuccessful fetch as clear weather.
- **News empty:** The RSS source may be stale or inaccessible. The collector only accepts items with trustworthy publication timestamps within eight days.
- **Prices unavailable:** Verify the Consumer Council pages are accessible and inspect the `extended.py` collector's `status`. Do not hard-code old prices as current.
- **Dashboard hasn't changed:** Check GitHub Actions completed, `data/extended.json` was committed, and Cloudflare successfully redeployed the latest commit. Browser should not need manual refresh after five minutes, but network or browser throttling may delay the automatic check.

**Testing:** `python -m unittest discover -s tests -v` and (when network is available) `python scripts/extended.py`.
