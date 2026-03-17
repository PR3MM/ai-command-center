
# routes to fetch new activity from GitHub, Jira, and Slack.

from fastapi import APIRouter, Query
from dotenv import load_dotenv
from datetime import datetime
from typing import Any
import httpx
import os
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# JIRA_TOKEN = os.getenv("JIRA_TOKEN")
# SLACK_TOKEN = os.getenv("SLACK_TOKEN")

router = APIRouter()


@router.get("/sync")
async def sync():
    github_activity = await fetch_github_activity(GITHUB_TOKEN)
    return {
        "github_activity": github_activity,
    }



# GitHub API
async def fetch_github_activity(github_token: str, last_sync_time: datetime | None = None) -> list[dict[str, Any]]:
    
    url = "https://api.github.com/notifications"        
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params: dict[str, Any] = {"all": "false"}
    if last_sync_time:
        params["since"] = last_sync_time.isoformat()

    unified_tasks = []

    # httpx.AsyncClient is much faster and better for FastAPI than standard 'requests'
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        
        # Always handle API limits or auth failures gracefully
        if response.status_code != 200:
            print(f"Error fetching GitHub data: {response.status_code} - {response.text}")
            return []
            
        notifications = response.json()
        
        for notif in notifications:
            # 1. Extract the core data we care about
            subject = notif.get("subject", {})
            reason = notif.get("reason")  # e.g., 'assign', 'mention', 'review_requested'
            repository = notif.get("repository", {}).get("full_name")
            
            # 2. Convert GitHub's API URL to a clickable Web URL for your UI
            # (GitHub API returns api.github.com/repos/..., we want github.com/...)
            api_url = subject.get("url") or ""
            web_url = api_url.replace("api.github.com/repos/", "github.com/").replace("/pulls/", "/pull/")
            if not web_url:
                web_url = f"https://github.com/{repository}"

            # 3. Identify the AI Trigger! 
            # If someone assigned you an issue, we tell the system to wake up LangGraph.
            needs_ai = False
            if reason == "assign" and subject.get("type") == "Issue":
                needs_ai = True
            
            # 4. Map it to the Unified Task format for your Supabase database
            task = {
                "source_app": "github",
                "source_id": notif.get("id"),
                "title": f"[{repository}] {subject.get('title')}",
                "source_url": web_url,
                "event_type": reason,
                "needs_ai_processing": needs_ai,
                # We save the raw payload in case the AI needs deeper context later
                "raw_payload": notif 
            }
            
            unified_tasks.append(task)
            print(f"Added task: {task}")
    return unified_tasks

# Jira API
async def fetch_jira_activity(jira_token: str):
    return {"message": "Hello, World!"}

# Slack API
async def fetch_slack_activity(slack_token: str):
    return {"message": "Hello, World!"}