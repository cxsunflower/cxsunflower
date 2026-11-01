#!/usr/bin/env python3
"""Publish a public-activity signal for the cxsunflower GitHub profile.

This is an activity indicator, not an online-presence detector. GitHub's
public-events API is eventually consistent and may lag by several hours.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

USERNAME = os.getenv("GITHUB_USERNAME", "cxsunflower")
WINDOW_MINUTES = int(os.getenv("ACTIVITY_WINDOW_MINUTES", "30"))
API_URL = f"https://api.github.com/users/{USERNAME}/events/public?per_page=100"
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

EVENT_LABELS = {
    "PushEvent": "PUSH",
    "PullRequestEvent": "PULL REQUEST",
    "IssuesEvent": "ISSUE",
    "IssueCommentEvent": "ISSUE COMMENT",
    "PullRequestReviewEvent": "PULL REQUEST REVIEW",
    "PullRequestReviewCommentEvent": "REVIEW COMMENT",
    "CreateEvent": "BRANCH / TAG CREATED",
    "DeleteEvent": "BRANCH / TAG DELETED",
    "ReleaseEvent": "RELEASE",
    "WatchEvent": "STAR",
    "ForkEvent": "FORK",
    "PublicEvent": "REPOSITORY MADE PUBLIC",
    "CommitCommentEvent": "COMMIT COMMENT",
}


def fetch_events() -> tuple[list[dict], str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cxsunflower-profile-activity-signal",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(API_URL, headers=headers)
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list):
            return [], "Unexpected API response"
        return payload, None
    except HTTPError as error:
        return [], f"GitHub API HTTP {error.code}"
    except (URLError, TimeoutError):
        return [], "GitHub API temporarily unavailable"
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [], "Could not parse GitHub API response"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def age_label(delta_seconds: float) -> str:
    minutes = max(0, int(delta_seconds // 60))
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    return f"{hours // 24} day(s) ago"


def render_svg(
    status: str,
    detail: str,
    checked_at: str,
    last_seen: str,
    color: str,
) -> str:
    safe_status = html.escape(status)
    safe_detail = html.escape(detail)
    safe_checked = html.escape(checked_at)
    safe_last_seen = html.escape(last_seen)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="190" viewBox="0 0 1000 190" role="img" aria-labelledby="title desc" shape-rendering="crispEdges">
  <title id="title">GitHub public activity signal: {safe_status}</title>
  <desc id="desc">{safe_detail}. This is not a real-time online indicator.</desc>
  <defs>
    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M20 0H0V20" fill="none" stroke="#263252" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="1000" height="190" rx="8" fill="#0b1020"/>
  <rect width="1000" height="190" fill="url(#grid)" opacity=".32"/>
  <rect x="8" y="8" width="984" height="174" fill="none" stroke="#8b5cf6" stroke-width="4"/>
  <rect x="22" y="22" width="956" height="146" fill="#111a31" stroke="#33436f" stroke-width="2"/>
  <g fill="#d7e5ff">
    <rect x="54" y="44" width="4" height="4"/><rect x="92" y="118" width="4" height="4"/>
    <rect x="180" y="38" width="4" height="4"/><rect x="250" y="142" width="4" height="4"/>
    <rect x="874" y="42" width="4" height="4"/><rect x="932" y="126" width="4" height="4"/>
  </g>
  <g transform="translate(48 72)">
    <rect x="0" y="16" width="16" height="16" fill="#8b5cf6"/>
    <rect x="16" y="0" width="32" height="48" fill="#d7e5ff"/>
    <rect x="48" y="16" width="16" height="16" fill="#35d6e8"/>
    <rect x="16" y="16" width="16" height="16" fill="#8b5cf6"/>
    <rect x="-16" y="20" width="16" height="8" fill="#f6c85f">
      <animate attributeName="opacity" values="1;.45;1" dur=".65s" repeatCount="indefinite"/>
    </rect>
    <rect x="64" y="20" width="8" height="8" fill="#35d6e8"/>
  </g>
  <text x="150" y="54" fill="#35d6e8" font-family="monospace" font-size="15" font-weight="bold" letter-spacing="3">MISSION CONTROL / PUBLIC EVENTS API</text>
  <text x="150" y="100" fill="{color}" font-family="monospace" font-size="30" font-weight="bold">{safe_status}</text>
  <text x="150" y="128" fill="#d7e5ff" font-family="monospace" font-size="15">{safe_detail}</text>
  <text x="150" y="153" fill="#94a3b8" font-family="monospace" font-size="12">LAST EVENT: {safe_last_seen}  |  CHECKED: {safe_checked}</text>
  <text x="950" y="153" text-anchor="end" fill="#64748b" font-family="monospace" font-size="10">NOT AN ONLINE STATUS</text>
</svg>
"""


def main() -> int:
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    checked_at = now.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S CST")
    events, error = fetch_events()

    parsed = []
    for event in events:
        created = parse_time(event.get("created_at"))
        if created is not None:
            parsed.append((created, event))
    parsed.sort(key=lambda item: item[0], reverse=True)

    recent = [
        item for item in parsed
        if 0 <= (now - item[0]).total_seconds() <= WINDOW_MINUTES * 60
    ]

    if error:
        status = "SIGNAL UNKNOWN"
        detail = error
        color = "#f6c85f"
        last_seen = "unavailable"
        last_event = None
    elif recent:
        created, event = recent[0]
        event_type = EVENT_LABELS.get(event.get("type", ""), event.get("type", "PUBLIC EVENT"))
        repository = (event.get("repo") or {}).get("name", "GitHub")
        status = "ACTIVE SIGNAL"
        detail = f"{event_type} / {repository}"
        color = "#35d6e8"
        last_seen = age_label((now - created).total_seconds())
        last_event = {
            "type": event.get("type"),
            "repository": repository,
            "created_at": created.isoformat(),
        }
    else:
        status = "QUIET ORBIT"
        color = "#f6c85f"
        if parsed:
            created, event = parsed[0]
            repository = (event.get("repo") or {}).get("name", "GitHub")
            last_seen = age_label((now - created).total_seconds())
            detail = f"No public event in the last {WINDOW_MINUTES} min / last: {repository}"
            last_event = {
                "type": event.get("type"),
                "repository": repository,
                "created_at": created.isoformat(),
            }
        else:
            last_seen = "no recent public events returned"
            detail = f"No public event in the last {WINDOW_MINUTES} min"
            last_event = None

    note = (
        "Based on public events only. GitHub documents variable event latency "
        "(about 30 seconds to 6 hours); this does not indicate real online presence."
    )
    (output_dir / "activity-status.svg").write_text(
        render_svg(status, detail, checked_at, last_seen, color),
        encoding="utf-8",
    )
    (output_dir / "activity.json").write_text(
        json.dumps(
            {
                "username": USERNAME,
                "status": status,
                "window_minutes": WINDOW_MINUTES,
                "checked_at_utc": now.isoformat(),
                "last_event": last_event,
                "api_error": error,
                "note": note,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{status}: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
