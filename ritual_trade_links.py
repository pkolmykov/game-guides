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
# explicit.stat_2500154144 -> Can Reroll Favours at Ritual Altars twice as many times (unique: Freedom of Faith)
# explicit.stat_120737942  -> Ritual Altars allow rerolling Favours # additional time(s)
# explicit.stat_2282052746 -> Rerolling Favours at Ritual Altars costs % increased Tribute (negative = reduced cost)

# ── Map 1 setup: outside the City ────────────────────────────────────────────
# Per the guide: your first map (outside the City) only exists to set up/unlock
# the rest of the Head of the King chain. Use a very cheap tablet — "increased
# chance to be Omens" is the one mod worth having here, everything else is
# basically free/irrelevant since you're not spending real Tribute yet.

MAP1_OUTSIDE_CITY_SEARCHES = [
    ("🟢 Cheap : Increased chance to be Omens (Map 1 only)", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4219853180", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("⭐ Cheap combo (if cheap): Omen chance AND increased Tribute", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4219853180", "value": {"min": 1}},
                {"id": "explicit.stat_159726667", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    # Weighted, price-capped: cheapest tablet with any Omen chance — this is
    # a "set up the chain" tablet, not a real investment.
    ("🏆 Cheapest Omen-chance tablet (weighted, price-capped)", {
        "query": {
            "status": STATUS_BUYOUT,
            "type": "Ritual Tablet",
            "stats": [
                {"type": "weight", "disabled": False, "filters": [
                    {"id": "explicit.stat_4219853180", "value": {"weight": 3}, "disabled": False},
                    {"id": "explicit.stat_159726667", "value": {"weight": 1}, "disabled": False},
                ]},
            ],
            "filters": {
                "trade_filters": {"filters": {"price": {"max": 10}}}
            },
        },
        "sort": {"price": "asc"}
    }),
]

# ── Maps 2-7 setup: inside the City (4-tablet slot) ─────────────────────────
# Per the guide: once you reach the City (2nd map onward), you get 4 tablet
# slots. Run this SAME 4-tablet combo on every City map in the chain — Head
# of the King naturally grants more Tribute/rerolls the further into the
# chain you are, so the last City map pays out the most without needing a
# different tablet set.
#
# Slot 1: Freedom of Faith (unique) — mandatory, reroll Favours twice as many times.
# Slot 2: Reroll tablet — most expensive slot (13-20 divine); buy the cheapest
#         with just "reroll Favours 3 additional times", only pay extra for
#         bonus mods if the price gap is small.
# Slot 3: Increased chance to be Omens + Monsters Sacrificed grant increased Tribute.
# Slot 4: Rerolling Favours costs reduced Tribute + more chance to be Omens.

CITY_SEARCHES = [
    ("🟣 Slot 1 : Freedom of Faith (unique — mandatory)", {
        "query": {
            "name": "Freedom of Faith",
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 Slot 2 : Reroll Favours 3 additional times (most expensive slot)", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_120737942", "value": {"min": 3}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 Slot 3 : Omen chance + increased Tribute", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4219853180", "value": {"min": 1}},
                {"id": "explicit.stat_159726667", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 Slot 4 : Reduced Tribute cost on reroll + more Omen chance", {
        "query": {
            "type": "Ritual Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_2282052746", "value": {"max": -1}},
                {"id": "explicit.stat_4219853180", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    # Weighted search for Slot 2: hard require the 3x reroll mod, weighted sum
    # covers the rest so you find the cheapest tablet that's "good enough"
    # without overpaying for a perfect roll.
    #
    # Stat                                                    weight  tier
    # Ritual Altars allow rerolling Favours 3x (required)        —    mandatory
    # Monsters Sacrificed grant % increased Tribute                2    bonus
    # Ritual Favours % increased chance to be Omens                2    bonus
    ("🏆 Slot 2 : 3x reroll required + weighted sort (best value)", {
        "query": {
            "status": STATUS_BUYOUT,
            "type": "Ritual Tablet",
            "stats": [
                {"type": "weight", "disabled": False, "filters": [
                    {"id": "explicit.stat_159726667", "value": {"weight": 2}, "disabled": False},
                    {"id": "explicit.stat_4219853180", "value": {"weight": 2}, "disabled": False},
                ]},
                {"type": "and", "filters": [
                    {"id": "explicit.stat_120737942", "value": {"min": 3}, "disabled": False},
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


MAP1_OUTSIDE_CITY_SEARCHES = [(name, with_uses_remaining(search)) for name, search in MAP1_OUTSIDE_CITY_SEARCHES]
CITY_SEARCHES = [(name, with_uses_remaining(search)) for name, search in CITY_SEARCHES]


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


map1_results = run_searches(MAP1_OUTSIDE_CITY_SEARCHES, "Map 1 - Outside the City (cheap setup)")
city_results = run_searches(CITY_SEARCHES, "Maps 2-7 - Inside the City (4-tablet setup)")

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
               "### Map 1 — Outside the City (cheap setup)\n\n",
               "Only mod that matters here is Omen chance — this map just sets up the rest of the chain.\n\n"]
table_lines += build_table(map1_results)
table_lines += ["\n### Maps 2-7 — Inside the City (4-tablet setup)\n\n",
                "Run this same 4-tablet combo on every City map in the chain; Head of the King naturally pays out\n"
                "more Tribute/rerolls the further into the chain you are.\n\n"]
table_lines += build_table(city_results)

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
