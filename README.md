# Innebandy schedule -> iPhone calendar subscription

Uses a real headless browser (Playwright + Chromium) to load the public
schedule page exactly like a visitor would, and captures the JSON response
the page itself fetches from `api.innebandy.se`. No manual auth token
needed or stored -- this only ever sees what any anonymous site visitor
sees, and doesn't rely on any personal or paid API credential.

## 1. Install dependencies and test locally

```bash
pip install -r requirements.txt
playwright install chromium   # downloads the browser binary, one-time
python generate_ics.py
```

This writes `schedule.ics`. Open it in a text editor, or double-click it
on a Mac to preview in Calendar, to confirm the events look right.

If it fails with "Could not capture the schedule API response," the page
likely changed -- open DevTools on the schedule page again and check
whether the API path still matches `API_URL_PATTERN` in
`generate_ics.py`.

## 2. Host it somewhere with a stable URL, refreshed weekly

**GitHub Pages + GitHub Actions (free, no server to maintain):**

1. Create a new GitHub repo and push this folder's contents to it.
2. In the repo Settings -> Pages, set the source to the `main` branch
   (root), so files are served at
   `https://<your-username>.github.io/<repo-name>/schedule.ics`.
3. The included workflow (`.github/workflows/update-calendar.yml`) runs
   every Monday: installs Playwright + Chromium on GitHub's runner (which
   isn't behind any corporate firewall), regenerates `schedule.ics`, and
   commits it -- Pages auto-publishes the update. Trigger it manually
   from the Actions tab ("Run workflow") any time to test.

## 3. Subscribe on iPhone

1. Settings -> Calendar -> Accounts -> Add Account -> Other ->
   **Add Subscribed Calendar**.
2. Paste the URL, e.g.
   `webcal://<your-username>.github.io/<repo-name>/schedule.ics`.
3. iOS decides its own refresh interval for subscribed calendars
   (typically daily), comfortably satisfying "no more than once a week"
   since the source file itself only changes weekly.

## Notes

- Events get a stable UID from each match's `MatchID`, so re-running the
  script won't create duplicate events -- updates overwrite in place.
- Cancelled matches are prefixed "INSTALLD:", postponed ones "FLYTTAD:",
  and finished matches show the final score in the title.
- If your local network's DNS/firewall blocks `api.innebandy.se` directly
  (common on corporate networks), that won't affect GitHub Actions --
  it runs on GitHub's own infrastructure. Test locally on a different
  network (e.g. phone hotspot) if you want to debug outside of CI.
