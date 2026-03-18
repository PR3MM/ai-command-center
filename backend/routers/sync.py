
# routes + core sync logic for GitHub and Jira.

from fastapi import APIRouter
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Any
from supabase import create_client, Client
import httpx
import os

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
JIRA_TOKEN   = os.getenv("JIRA_TOKEN")
JIRA_EMAIL   = os.getenv("JIRA_EMAIL")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()


# ── Supabase helpers ──────────────────────────────────────────────────────────

def get_last_sync(source: str) -> datetime | None:
    """Read the last successful sync timestamp for a given source."""
    row = (
        supabase.table("sync_state")
        .select("last_successful_sync")
        .eq("source", source)
        .single()
        .execute()
    )
    raw = row.data.get("last_successful_sync") if row.data else None
    if raw:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return None


def set_last_sync(source: str) -> None:
    """Write now() as the last successful sync timestamp for a given source."""
    supabase.table("sync_state").upsert(
        {"source": source, "last_successful_sync": datetime.now(timezone.utc).isoformat()},
        on_conflict="source",
    ).execute()


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    """Upsert unified tasks — duplicate (source_app, source_id) pairs are updated, not duplicated."""
    if not tasks:
        return
    supabase.table("unified_tasks").upsert(tasks, on_conflict="source_app,source_id").execute()


# ── Core sync function (called by scheduler AND the manual /sync endpoint) ────

async def run_sync() -> dict[str, Any]:
    """
    Fetches new activity from all sources since their last successful sync,
    saves to unified_tasks, and updates sync_state timestamps.
    """
    github_last_sync = get_last_sync("github")
    jira_last_sync   = get_last_sync("jira")

    github_tasks = await fetch_github_activity(GITHUB_TOKEN, last_sync_time=github_last_sync)
    jira_tasks   = await fetch_jira_activity(JIRA_EMAIL, JIRA_TOKEN, last_sync_time=jira_last_sync)

    save_tasks(github_tasks + jira_tasks)

    # Only advance the timestamp if the fetch succeeded (non-empty or explicit success)
    if github_tasks is not None:
        set_last_sync("github")
    if jira_tasks is not None:
        set_last_sync("jira")

    return {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "github_new": len(github_tasks),
        "jira_new": len(jira_tasks),
        "total_saved": len(github_tasks) + len(jira_tasks),
    }


# ── Manual trigger endpoint ───────────────────────────────────────────────────

@router.get("/sync")
async def sync():
    """Manually trigger a sync. Useful for testing; in production the scheduler runs this."""
    return await run_sync()


# ── GitHub API ────────────────────────────────────────────────────────────────

async def fetch_github_activity(
    github_token: str,
    last_sync_time: datetime | None = None,
) -> list[dict[str, Any]]:
    url = "https://api.github.com/notifications"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params: dict[str, Any] = {"all": "false"}
    if last_sync_time:
        params["since"] = last_sync_time.isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"[GitHub] Fetch error {response.status_code}: {response.text}")
        return []

    tasks = []
    for notif in response.json():
        subject    = notif.get("subject", {})
        reason     = notif.get("reason")
        repository = notif.get("repository", {}).get("full_name")

        api_url = subject.get("url") or ""
        web_url = api_url.replace("api.github.com/repos/", "github.com/").replace("/pulls/", "/pull/")
        if not web_url:
            web_url = f"https://github.com/{repository}"

        needs_ai = reason == "assign" and subject.get("type") == "Issue"

        tasks.append({
            "source_app":          "github",
            "source_id":           notif.get("id"),
            "title":               f"[{repository}] {subject.get('title')}",
            "source_url":          web_url,
            "event_type":          reason,
            "needs_ai_processing": needs_ai,
            "raw_payload":         notif,
        })

    return tasks


# ── Jira API ──────────────────────────────────────────────────────────────────

async def fetch_jira_activity(
    jira_email: str,
    jira_api_token: str,
    last_sync_time: datetime | None = None,
) -> list[dict[str, Any]]:
    domain = JIRA_BASE_URL.rstrip("/")
    url    = f"{domain}/rest/api/3/search/jql"

    jql = "assignee = currentUser() ORDER BY updated DESC"
    if last_sync_time:
        since_str = last_sync_time.strftime("%Y-%m-%d %H:%M")
        jql = f"assignee = currentUser() AND updated >= '{since_str}' ORDER BY updated DESC"

    payload = {
        "jql":        jql,
        "maxResults": 25,
        "fields":     ["summary", "status", "priority", "updated", "issuetype"],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, auth=(jira_email, jira_api_token))

    if response.status_code != 200:
        print(f"[Jira] Fetch error {response.status_code}: {response.text}")
        return []

    tasks = []
    for issue in response.json().get("issues", []):
        key    = issue.get("key")
        fields = issue.get("fields", {})
        tasks.append({
            "source_app":          "jira",
            "source_id":           key,
            "title":               f"[{key}] {fields.get('summary')}",
            "source_url":          f"{domain}/browse/{key}",
            "status":              fields.get("status", {}).get("name", "Unknown"),
            "priority":            fields.get("priority", {}).get("name", "Medium"),
            "event_type":          "ticket_updated",
            "needs_ai_processing": False,
            "raw_payload":         issue,
        })

    return tasks


# ── Slack API (stub — implement later) ────────────────────────────────────────

async def fetch_slack_activity(slack_token: str) -> list[dict[str, Any]]:
    return []
