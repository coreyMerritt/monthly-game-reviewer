#!/usr/bin/env python3
import os
import time
import argparse
import calendar
from datetime import datetime

import requests
from rich.console import Console
from rich.table import Table

# Parse required CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument("--month", required=True, type=int, choices=range(1, 13), metavar="[1-12]", help="Month (1-12)")
parser.add_argument("--year", required=True, type=int, metavar="xxxx", help="Year (ex 2026)")
args = parser.parse_args()

# Determine start and end dates for the given month/year
LAST_DAY = calendar.monthrange(args.year, args.month)[1]
START_DATE = f"{args.year}-{args.month}-01"
END_DATE = f"{args.year}-{args.month}-{LAST_DAY}"

# Rich instantiation
console = Console()
table = Table()
table.add_column("Date")
table.add_column("Title")
table.add_column("Platforms")
table.add_column("Rating")

# Determine the platform query
platform_query_list = []
platform_query_list.append("6")
platform_query_list.append("167")
PLATFORM_QUERY_STRING = ", ".join(map(str, platform_query_list))

# Convert to UNIX timestamps (UTC)
START = int(datetime.strptime(START_DATE, "%Y-%m-%d").timestamp())
END = int(datetime.strptime(END_DATE, "%Y-%m-%d").timestamp())

# Get credentials from environment
CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
  raise RuntimeError("Missing IGDB_CLIENT_ID or IGDB_CLIENT_SECRET in environment variables")

# Request access token
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_URL = "https://api.igdb.com/v4/games"
token_data = {
  "client_id": CLIENT_ID,
  "client_secret": CLIENT_SECRET,
  "grant_type": "client_credentials"
}
token_resp = requests.post(TOKEN_URL, data=token_data, timeout=60).json()
access_token = token_resp.get("access_token")
if not access_token:
  raise RuntimeError(f"Failed to get token: {token_resp}")
headers = {
  "Client-ID": CLIENT_ID,
  "Authorization": f"Bearer {access_token}",
  "Content-Type": "text/plain"
}

# Pagination settings
LIMIT = 50
OFFSET = 0
all_games = []

while True:
  query = f"""
  fields name, rating, first_release_date, platforms.name;
  where (
    first_release_date >= {START}
    & first_release_date <= {END}
    & rating >= 60 & platforms = ({PLATFORM_QUERY_STRING})
  );
  sort first_release_date asc;
  limit {LIMIT};
  offset {OFFSET};
  """
  resp = requests.post(IGDB_URL, headers=headers, data=query, timeout=60)
  games = resp.json()
  if not games:
    break
  all_games.extend(games)
  OFFSET += LIMIT

# Sort games by rating descending
sorted_games = sorted(
  all_games,
  key=lambda g: g.get("rating") if isinstance(g.get("rating"), (int, float)) else 0,
  reverse=True
)

# Table insertions
for game in sorted_games:
  name = game.get("name", "Unknown Title")
  date = time.strftime('%Y-%m-%d', time.gmtime(game.get("first_release_date", 0)))
  rating = game.get("rating", "N/A")
  raw_platforms = [p.get("name", "Unknown") for p in game.get("platforms", [])]
  filtered = []
  for p in raw_platforms:
    if p == "PC (Microsoft Windows)":
      filtered.append("PC")
    elif p == "PlayStation 5":
      filtered.append("PS5")
  platforms = ", ".join(filtered)
  platforms = platforms[:23] + "…" if len(platforms) > 26 else platforms
  table.add_row(str(date), str(name), str(platforms), f"{rating:.1f}")

# Output
console.print(table)
