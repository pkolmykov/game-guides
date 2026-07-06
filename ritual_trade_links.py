#!/usr/bin/env python3
"""
Generate POE2 trade search links for the Ritual farming setup.
(Guide: https://www.youtube.com/watch?v=C2elk9YSOBM&t=625s
 "[PoE 2] FARM Ritual EFFICIENTLY - IN DEPTH Guide + Atlas Tree Strategy")

Setup:
  1. Copy .env.example to .env
  2. Set POE_POESESSID to your POESESSID cookie value
     (find it in browser DevTools → Application → Cookies → pathofexile.com)
  3. Run: python3 ritual_trade_links.py
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

# ── Stat IDs (Ritual Tablet) ─────────────────────────────────────────────────
# explicit.stat_159726667  -> Monsters Sacrificed at Ritual Altars grant % increased Tribute
# explicit.stat_4219853180 -> Ritual Favours have % increased chance to be Omens
# explicit.stat_2500154144 -> Can Reroll Favours at Ritual Altars twice as many times
# explicit.stat_120737942  -> Ritual Altars allow rerolling Favours an additional time
# explicit.stat_937291386  -> Favours Rerolled have % chance to cost no Tribute
# explicit.stat_3793155082 -> Map has % increased number of Rare Monsters
# explicit.stat_2017682521 -> % increased Pack Size in Map
# explicit.stat_4142653832 -> Map has % increased Monster Rarity

FIRST_MAP_SEARCHES = [
    ("🟢 Budget : Increased Pack Size in Map", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_2017682521", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🟢 Budget : Map has increased number of Rare Monsters", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_3793155082", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🟢 Budget : Map has increased Monster Rarity", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4142653832", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("⭐ Budget combo: Pack Size AND Rare Monsters (cheap density)", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_2017682521", "value": {"min": 1}},
                {"id": "explicit.stat_3793155082", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    # Weighted, price-capped search: cheap density filler for chain/build-up maps.
    # No hard-required mod — just maximize density per divine spent.
    #
    # Stat                                          weight  tier
    # Map has % increased number of Rare Monsters      3     filler
    # % increased Pack Size in Map                      2     filler
    # Map has % increased Monster Rarity                 2     filler
    ("🏆 Cheapest density filler (weighted, price-capped)", {
        "query": {
            "status": STATUS_BUYOUT,
            "type": "Ritual Tablet",
            "stats": [
                {"type": "weight", "disabled": False, "filters": [
                    {"id": "explicit.stat_3793155082", "value": {"weight": 3}, "disabled": False},
                    {"id": "explicit.stat_2017682521", "value": {"weight": 2}, "disabled": False},
                    {"id": "explicit.stat_4142653832", "value": {"weight": 2}, "disabled": False},
                ]},
            ],
            "filters": {
                "trade_filters": {"filters": {"price": {"max": 50}}}
            },
        },
        "sort": {"price": "asc"}
    }),
]

LAST_MAP_SEARCHES = [
    ("🟣 S+ : Monsters Sacrificed grant increased Tribute (core mod)", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_159726667", "value": {"min": 30}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S : Ritual Favours increased chance to be Omens", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4219853180", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S : Reroll Favours twice as many times", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_2500154144"}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("⭐ Best combo: Tribute% AND Omen chance%", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_159726667", "value": {"min": 20}},
                {"id": "explicit.stat_4219853180", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🟡 A : Favours Rerolled % chance to cost no Tribute", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_937291386", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🟡 A : Extra Altar Reroll + Pack Size/Rare Monster filler", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_120737942"},
                {"id": "explicit.stat_2017682521", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    # Weighted search: hard require the core Tribute mod, weighted sum covers the rest.
    #
    # Stat                                                    weight  tier
    # Monsters Sacrificed grant % increased Tribute (req)       —     S+ (required)
    # Ritual Favours % increased chance to be Omens              4     S
    # Can Reroll Favours twice as many times (binary)            3     S
    # Favours Rerolled % chance to cost no Tribute                2     A
    # Ritual Altars allow rerolling an additional time (binary)  2     A
    # Map has % increased number of Rare Monsters                 1     A
    # % increased Pack Size in Map                                 1     A
    ("🏆 S+ required + weighted sort (best overall)", {
        "query": {
            "status": STATUS_BUYOUT,
            "type": "Ritual Tablet",
            "stats": [
                {"type": "weight", "disabled": False, "filters": [
                    {"id": "explicit.stat_4219853180", "value": {"weight": 4}, "disabled": False},
                    {"id": "explicit.stat_2500154144", "value": {"weight": 3}, "disabled": False},
                    {"id": "explicit.stat_937291386", "value": {"weight": 2}, "disabled": False},
                    {"id": "explicit.stat_120737942", "value": {"weight": 2}, "disabled": False},
                    {"id": "explicit.stat_3793155082", "value": {"weight": 1}, "disabled": False},
                    {"id": "explicit.stat_2017682521", "value": {"weight": 1}, "disabled": False},
                ]},
                {"type": "and", "filters": [
                    {"id": "explicit.stat_159726667", "value": {"min": 20}, "disabled": False},
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


FIRST_MAP_SEARCHES = [(name, with_uses_remaining(search)) for name, search in FIRST_MAP_SEARCHES]
LAST_MAP_SEARCHES = [(name, with_uses_remaining(search)) for name, search in LAST_MAP_SEARCHES]


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
print(f"  POE2 Ritual Tablet Trade Links — {LEAGUE}")
print(f"  Instant buyout only")
print(f"{'='*60}\n")


def run_searches(searches, label):
    print(f"--- {label} ---\n")
    out = []
    for name, query in searches:
        try:
            data = json.dumps(query).encode()
            req = urllib.request.Request(api_url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                sid = result.get("id", "")
                url = f"{trade_base}/{sid}"
                print(f"{name}")
                print(f"  {url}\n")
                out.append((name, url))
        except Exception as e:
            print(f"{name}")
            print(f"  ERROR: {e}\n")
            out.append((name, None))
        time.sleep(3)
    return out


first_map_results = run_searches(FIRST_MAP_SEARCHES, "First Maps (Build Tribute)")
last_map_results = run_searches(LAST_MAP_SEARCHES, "Last Map (Cash-Out)")

# ── Insert/update Trade Links section in ritual_setup.md ────────────────────

md_path = os.path.join(os.path.dirname(__file__), "ritual_setup.md")
generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")


def build_table(results):
    lines = ["| # | Search | Link |\n", "|---|--------|------|\n"]
    for i, (name, url) in enumerate(results, 1):
        if url:
            lines.append(f"| {i} | {name} | [trade link]({url}) |\n")
        else:
            lines.append(f"| {i} | {name} | ❌ failed |\n")
    return lines


table_lines = ["## Tablet Trade Links\n\n", f"> Generated: {generated_at} · Instant buyout only · 10 uses remaining (anti-scam)\n\n",
               "### First Maps (Build Tribute)\n\n", "Cheap density tablets — clear efficiently and build up Tribute without overspending.\n\n"]
table_lines += build_table(first_map_results)
table_lines += ["\n### Last Map (Cash-Out)\n\n", "Best/juiced tablets — spend saved Tribute here for max Omens/Uniques.\n\n"]
table_lines += build_table(last_map_results)

with open(md_path) as f:
    content = f.read()

marker_start = "## Tablet Trade Links"
if marker_start in content:
    before, _, after = content.partition(marker_start)
    rest_after_heading = after.split("\n---\n", 1)
    remainder = "\n---\n" + rest_after_heading[1] if len(rest_after_heading) > 1 else ""
    new_content = before + "".join(table_lines) + "\n" + remainder.lstrip("\n")
else:
    anchor = "## Map Running & Tribute Management"
    before, _, after = content.partition(anchor)
    new_content = before + "".join(table_lines) + "\n---\n\n" + anchor + after

with open(md_path, "w") as f:
    f.write(new_content)

print(f"✅ Updated {md_path}")
