from dotenv import load_dotenv
import os
import requests

load_dotenv()  # ❗ 이 줄 필수

URL = "https://api.linear.app/graphql"
HEADERS = {
    "Authorization": os.getenv('LINEAR_API_KEY'),
    "Content-Type": "application/json"
}

def linear_query(query, variables=None):
    return requests.post(
        URL,
        headers=HEADERS,
        json={"query": query, "variables": variables}
    ).json()

query = """
query {
  issues(first: 50) {
    nodes {
      id
      identifier
      title
      state { name }
      estimate
      dueDate
      labels { nodes { name } }
    }
  }
}
"""

data = linear_query(query)
print(f"{data}\n") 
issues = data["data"]["issues"]["nodes"]