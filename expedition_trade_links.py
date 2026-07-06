#!/usr/bin/env python3
"""
Generate POE2 trade search links for the Grand Expedition farming setup.
(Guide: https://youtu.be/7WqPIdTeYiY?si=zZhwocIEX1lbDXJk
 Strats: https://mobalytics.gg/poe-2/atlas-trees/fubgun-atlas-tree-strats)

Setup:
  1. Copy .env.example to .env
  2. Set POE_POESESSID to your POESESSID cookie value
     (find it in browser DevTools → Application → Cookies → pathofexile.com)
  3. Run: python3 expedition_trade_links.py
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

LEAGUE = "Runes of Aldur"
POESESSID = os.environ.get("POE_POESESSID", "")

# ── Load .env if present ──────────────────────────────────────────────────────

env_file = next(
    (os.path.join(os.path.dirname(__file__), f) for f in (".env", "local.env") if os.path.exists(os.path.join(os.path.dirname(__file__), f))),
    None
)
if not POESESSID and env_file and os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("POE_POESESSID=") and "=" in line:
                POESESSID = line.split("=", 1)[1].strip()

if not POESESSID:
    print("ERROR: POE_POESESSID not set.")
    print("  Set it in .env or as an environment variable.")
    raise SystemExit(1)

# ── Buyout filter (instant buyout only) ──────────────────────────────────────

STATUS_BUYOUT = {"option": "securable"}

# ── Stat IDs (Irradiated / Expedition Tablet) ────────────────────────────────
# explicit.stat_588512487  -> Map has # additional random Modifier
# explicit.stat_2694800111 -> % increased number of Rare Expedition Monsters in Map
# explicit.stat_2065500219 -> Monsters have % increased Effectiveness
# explicit.stat_3793155082 -> Map has % increased number of Rare Monsters
# explicit.stat_4142653832 -> Map has % increased Monster Rarity
# explicit.stat_2306002879 -> % increased Rarity of Items found in Map

SEARCHES = [
    ("🟣 Aldur Saga: +2 Random Map Modifiers (core mod)", {
        "query": {
            "type": "Irradiated Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_588512487", "value": {"min": 2}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S : Monster Effectiveness", {
        "query": {
            "type": "Irradiated Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_2065500219", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S : Increased Number of Rare Monsters", {
        "query": {
            "type": "Irradiated Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_3793155082", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("⭐ Best combo (Aldur Saga): +2 Modifiers AND Monster Effectiveness", {
        "query": {
            "type": "Irradiated Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_588512487", "value": {"min": 2}},
                {"id": "explicit.stat_2065500219", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("⭐ Best combo (Aldur Saga): +2 Modifiers AND Increased Rare Monsters", {
        "query": {
            "type": "Irradiated Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_588512487", "value": {"min": 2}},
                {"id": "explicit.stat_3793155082", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🟡 A : Monster Rarity + Item Rarity (budget/non-Aldur)", {
        "query": {
            "type": "Irradiated Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4142653832", "value": {"min": 1}},
                {"id": "explicit.stat_2306002879", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    # Weighted search: hard require the Aldur Saga core mod, weighted sum covers the rest.
    #
    # Stat                                          typ.value  weight  tier
    # Map has +2 additional random Modifiers (req)      2        —     S+ (required)
    # Monsters have % increased Effectiveness           20        4     S
    # Map has % increased number of Rare Monsters        30        4     S
    # Map has % increased Monster Rarity                 30        2     A
    # % increased Rarity of Items found in Map           20        1     A
    ("🏆 Aldur Saga: S+ required + weighted sort (best overall)", {
        "query": {
            "status": STATUS_BUYOUT,
            "type": "Irradiated Tablet",
            "stats": [
                {"type": "weight", "disabled": False, "filters": [
                    {"id": "explicit.stat_2065500219", "value": {"weight": 4}, "disabled": False},
                    {"id": "explicit.stat_3793155082", "value": {"weight": 4}, "disabled": False},
                    {"id": "explicit.stat_4142653832", "value": {"weight": 2}, "disabled": False},
                    {"id": "explicit.stat_2306002879", "value": {"weight": 1}, "disabled": False},
                ]},
                {"type": "and", "filters": [
                    {"id": "explicit.stat_588512487", "value": {"min": 2}, "disabled": False},
                ]},
            ],
            "filters": {
                "trade_filters": {"filters": {"price": {"max": 400}}}
            },
        },
        "sort": {"price": "asc"}
    }),
]

# ── Anti-scam filter: require full "Uses Remaining" on every search ─────────
# Scammers list partially-used tablets that look like fresh ones in the search
# preview. Requiring min:10 uses remaining (max charges) filters these out.

USES_REMAINING_FILTER = {"id": "pseudo.pseudo_number_of_uses_remaining", "value": {"min": 10}, "disabled": False}


def with_uses_remaining(search):
    """Ensure every search's query requires min:10 Tablet uses remaining."""
    stats = search["query"].setdefault("stats", [])
    and_group = next((g for g in stats if g.get("type") == "and"), None)
    if and_group is None:
        and_group = {"type": "and", "filters": []}
        stats.append(and_group)
    and_group["filters"].append(USES_REMAINING_FILTER)
    return search


SEARCHES = [(name, with_uses_remaining(search)) for name, search in SEARCHES]

# ── Generate links ────────────────────────────────────────────────────────────

api_url = f"https://www.pathofexile.com/api/trade2/search/{urllib.parse.quote(LEAGUE)}"
trade_base = f"https://www.pathofexile.com/trade2/search/{urllib.parse.quote(LEAGUE)}"

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Cookie": f"POESESSID={POESESSID}",
    "Origin": "https://www.pathofexile.com",
    "Referer": f"https://www.pathofexile.com/trade2/search/{urllib.parse.quote(LEAGUE)}",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

print(f"\n{'='*60}")
print(f"  POE2 Irradiated (Expedition) Tablet Trade Links — {LEAGUE}")
print(f"  Instant buyout only")
print(f"{'='*60}\n")

results = []

for name, query in SEARCHES:
    try:
        data = json.dumps(query).encode()
        req = urllib.request.Request(api_url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            sid = result.get("id", "")
            url = f"{trade_base}/{sid}"
            print(f"{name}")
            print(f"  {url}\n")
            results.append((name, url))
    except Exception as e:
        print(f"{name}")
        print(f"  ERROR: {e}\n")
        results.append((name, None))
    time.sleep(3)

# ── Insert/update Trade Links section in expedition_setup.md ────────────────

md_path = os.path.join(os.path.dirname(__file__), "expedition_setup.md")
generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

table_lines = ["## Tablet Trade Links\n\n", f"> Generated: {generated_at} · Instant buyout only · 10 uses remaining (anti-scam)\n\n",
               "| # | Search | Link |\n", "|---|--------|------|\n"]
for i, (name, url) in enumerate(results, 1):
    if url:
        table_lines.append(f"| {i} | {name} | [trade link]({url}) |\n")
    else:
        table_lines.append(f"| {i} | {name} | ❌ failed |\n")

with open(md_path) as f:
    content = f.read()

marker_start = "## Tablet Trade Links"
if marker_start in content:
    before, _, after = content.partition(marker_start)
    # find the next "---" section separator after the marker to know where the old section ends
    rest_after_heading = after.split("\n---\n", 1)
    remainder = "\n---\n" + rest_after_heading[1] if len(rest_after_heading) > 1 else ""
    new_content = before + "".join(table_lines) + "\n" + remainder.lstrip("\n")
else:
    # insert after the "Map & Tablet Setup" section (before Explosive / Remnant Loop)
    anchor = "## Explosive / Remnant Loop"
    before, _, after = content.partition(anchor)
    new_content = before + "".join(table_lines) + "\n---\n\n" + anchor + after

with open(md_path, "w") as f:
    f.write(new_content)

print(f"✅ Updated {md_path}")
