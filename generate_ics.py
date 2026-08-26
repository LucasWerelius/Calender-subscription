#!/usr/bin/env python3
"""
Load the public schedule page in a real (headless) browser, capture the
JSON response the page itself fetches from api.innebandy.se, and generate
an .ics file from it -- no manual auth token required, since this only ever
sees what any anonymous visitor to the page sees.

Usage:
    playwright install chromium   # once, downloads the browser binary
    python generate_ics.py
"""

import re
from datetime import datetime, timedelta

from icalendar import Calendar, Event
from playwright.sync_api import sync_playwright

# ----------------------------- CONFIG ---------------------------------

SEASON_ID = 44
TEAM_ID = 4634

PAGE_URL = f"https://stats.innebandy.se/sasong/{SEASON_ID}/lag/{TEAM_ID}/spelprogram"

# Match any API call whose path looks like .../seasons/{SEASON_ID}/teams/{TEAM_ID}
# (not hardcoding the full host in case it's proxied/versioned differently).
API_URL_PATTERN = re.compile(rf"seasons/{SEASON_ID}/teams/{TEAM_ID}(?:$|[/?])")

OUTPUT_FILE = "schedule.ics"
DEFAULT_DURATION_MINUTES = 90

# ------------------------------------------------------------------------


def fetch_data_via_browser():
    """
    Open the public page in headless Chromium, wait for it to make its own
    API call (using whatever auth the page itself obtains), and capture
    that response body. This mirrors exactly what a visitor's browser sees.
    """
    captured = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        def handle_response(response):
            if API_URL_PATTERN.search(response.url) and response.status == 200:
                try:
                    captured["data"] = response.json()
                except Exception:
                    pass

        page.on("response", handle_response)
        page.goto(PAGE_URL, wait_until="networkidle", timeout=30000)

        # Give any late XHR calls a moment to land.
        page.wait_for_timeout(2000)
        browser.close()

    if "data" not in captured:
        raise RuntimeError(
            "Could not capture the schedule API response. The page's "
            "structure or API path may have changed -- inspect DevTools "
            "again and update API_URL_PATTERN."
        )

    return captured["data"]


def all_matches(data):
    """Flatten Competitions[].Matches[] into one list."""
    matches = []
    for competition in data.get("Competitions") or []:
        matches.extend(competition.get("Matches") or [])
    return matches


def match_to_event(m):
    dt = datetime.fromisoformat(m["MatchDateTime"])  # e.g. "2026-09-04T20:00:00"

    home = m.get("HomeTeam") or "?"
    away = m.get("AwayTeam") or "?"
    venue = m.get("Venue") or m.get("MainVenue")

    summary = f"{home} - {away}"
    if m.get("Cancelled"):
        summary = f"INSTALLD: {summary}"
    elif m.get("Postponed"):
        summary = f"FLYTTAD: {summary}"

    goals_home = m.get("GoalsHomeTeam")
    goals_away = m.get("GoalsAwayTeam")
    if goals_home is not None and goals_away is not None:
        summary += f" ({goals_home}-{goals_away})"

    event = Event()
    event.add("summary", summary)
    event.add("dtstart", dt)
    event.add("dtend", dt + timedelta(minutes=DEFAULT_DURATION_MINUTES))
    event.add("dtstamp", datetime.utcnow())
    if venue:
        event.add("location", venue)
    if m.get("CompetitionName"):
        event.add("description", m["CompetitionName"])
    event.add("uid", f"innebandy-match-{m['MatchID']}@stats.innebandy.se")
    return event


def build_calendar(matches):
    cal = Calendar()
    cal.add("prodid", "-//Innebandy Schedule Sync//")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Varmdo IF - Matcher")
    cal.add("x-published-ttl", "P1W")

    count = 0
    for m in matches:
        if not m.get("MatchDateTime"):
            continue
        cal.add_component(match_to_event(m))
        count += 1

    return cal, count


def main():
    data = fetch_data_via_browser()
    matches = all_matches(data)

    if not matches:
        print("No matches found -- check the page/API structure hasn't changed.")
        return

    cal, count = build_calendar(matches)

    with open(OUTPUT_FILE, "wb") as f:
        f.write(cal.to_ical())

    print(f"Wrote {count} events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
