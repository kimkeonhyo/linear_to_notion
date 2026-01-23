import os
import requests
import notion_client
import inspect
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime, timedelta, timezone
from importlib.metadata import version

# ─────────────────────
# 환경 변수 로드
# ─────────────────────
load_dotenv()

print("NOTION VERSION:", version("notion-client"))
print("NOTION PATH:", inspect.getfile(notion_client))

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

LINEAR_URL = "https://api.linear.app/graphql"

LINEAR_HEADERS = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json"
}

notion = Client(auth=NOTION_API_KEY)

# ─────────────────────
# Linear API
# ─────────────────────
def linear_query(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    res = requests.post(
        LINEAR_URL,
        headers=LINEAR_HEADERS,
        json=payload
    )
    return res.json()

def get_linear_issues():
    since = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()

    query = """
    query ($since: DateTimeOrDuration!) {
      issues(
          filter: { updatedAt: { gte: $since }}
          orderBy: updatedAt
          first: 100
        ) {
        nodes {
          id
          identifier
          title
          state { name }
          assignee { name }
          project { name }
          team { name }
          createdAt
          dueDate
          url
          priority
          updatedAt
        }
      }
    }
    """
    return linear_query(query, {"since": since})["data"]["issues"]["nodes"]

# -------------------
# priority Mapping
# -------------------
PRIORITY_MAP = {
    0: "None",
    1: "Urgent",
    2: "High",
    3: "Normal",
    4: "Low"
}

# ---------------------
# Duration builder (안정성 보장)
# ---------------------
def build_duration(issue):
    start = issue.get("createdAt")
    end = issue.get("dueDate")

    if not start:
        return None

    if end and end >= start:
        return {"date": {"start": start, "end": end}}

    return {"date": {"start": start}}

# ─────────────────────
# Notion Helpers
# ─────────────────────
def find_notion_page(linear_id):
    res = notion.databases.query(
        database_id=NOTION_DB_ID,
        filter={
            "property": "ID",
            "rich_text": {"equals": linear_id}
        }
    )
    return res["results"][0] if res["results"] else None

# ----------------------------
# Create
# ----------------------------
def create_notion_page(issue):
    properties = {
        "ID": {
            "rich_text": [{"text": {"content": issue["id"]}}]
        },
        "Task": {
            "title": [{"text": {"content": issue["title"]}}]
        },
        "Linear ID": {
            "rich_text": [{"text": {"content": issue["identifier"]}}]
        },
        "Status": {
            "select": {"name": issue["state"]["name"]}
        },
        "Assignee": {
            "rich_text": [{"text": {"content": issue["assignee"]["name"] if issue["assignee"] else ""}}]
        },
        "URL": {
            "url": issue["url"]
        },
        "Priority": {
            "select": {"name": PRIORITY_MAP.get(issue["priority"], "None")}
        }
    }

    if issue.get("project"):
        properties["Project"] = {"select": {"name": issue["project"]["name"]}}

    if issue.get("team"):
        properties["Team"] = {"select": {"name": issue["team"]["name"]}}

    duration = build_duration(issue)
    if duration:
        properties["Duration"] = duration

    notion.pages.create(
        parent={"database_id": NOTION_DB_ID},
        properties=properties
    )

# -------------------------------
# Update
# -------------------------------
def update_notion_page(page_id, issue):
    properties = {
        "Task": {
            "title": [{"text": {"content": issue["title"]}}]
        },
        "Linear ID": {
            "rich_text": [{"text": {"content": issue["identifier"]}}]
        },
        "Status": {
            "select": {"name": issue["state"]["name"]}
        },
        "Assignee": {
            "rich_text": [{"text": {"content": issue["assignee"]["name"] if issue["assignee"] else ""}}]
        },
        "URL": {
            "url": issue["url"]
        },
        "Priority": {
            "select": {"name": PRIORITY_MAP.get(issue["priority"], "None")}
        }
    }

    if issue.get("project"):
        properties["Project"] = {"select": {"name": issue["project"]["name"]}}

    if issue.get("team"):
        properties["Team"] = {"select": {"name": issue["team"]["name"]}}

    duration = build_duration(issue)
    if duration:
        properties["Duration"] = duration

    notion.pages.update(
        page_id=page_id,
        properties=properties
    )

# ─────────────────────
# Sync 실행
# ─────────────────────
def sync():
    issues = get_linear_issues()
    print(f"🔄 {len(issues)} issues syncing...")

    for issue in issues:
        try:
            page = find_notion_page(issue["id"])
            if page:
                update_notion_page(page["id"], issue)
                print(f"🟡 Updated: {issue['title']}")
            else:
                create_notion_page(issue)
                print(f"🟢 Created: {issue['title']}")
        except Exception as e:
            print(f"❌ Failed: {issue['title']} → {e}")

if __name__ == "__main__":
    sync()
