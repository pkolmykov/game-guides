#!/usr/bin/env python3
"""
Generate POE2 trade search links for the Abyss Juice farming setup.
(Perra's guide: https://youtu.be/8b4yK-Qtd7M?t=354)

Setup:
  1. Copy .env.example to .env
  2. Set POE_POESESSID to your POESESSID cookie value
     (find it in browser DevTools → Application → Cookies → pathofexile.com)
  3. Run: python3 trade_links.py
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

# ── Searches ──────────────────────────────────────────────────────────────────

SEARCHES = [
    ("🟣 Unforeseen Consequences (unique — mandatory)", {
        "query": {
            "name": "Unforeseen Consequences",
            "type": "Abyss Tablet",
            "status": STATUS_BUYOUT,
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S+ : +2 Rare Monsters spawned from Abysses", {
        "query": {
            "type": "Abyss Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_243380454", "value": {"min": 2}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S : Natural Rare Monsters have extra Abyssal Modifier", {
        "query": {
            "type": "Abyss Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_2789248444"}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🔴 S : Rare Monsters %", {
        "query": {
            "type": "Abyss Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_3793155082", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("⭐ Best combo: S+ (+2 Rare) AND S (extra Abyssal Modifier)", {
        "query": {
            "type": "Abyss Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_243380454", "value": {"min": 2}},
                {"id": "explicit.stat_2789248444"}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    ("🟡 A : Monster Rarity + Extra Abysses", {
        "query": {
            "type": "Abyss Tablet",
            "status": STATUS_BUYOUT,
            "stats": [{"type": "and", "filters": [
                {"id": "explicit.stat_4142653832", "value": {"min": 1}},
                {"id": "explicit.stat_3490187949", "value": {"min": 1}}
            ]}],
        },
        "sort": {"price": "asc"}
    }),
    # Slot 4: hard require +2 Rare Monsters (min:2), weighted sum covers all useful mods.
    # Sort by price (cheapest qualifying tablet first).
    # Weights normalised so each mod contributes proportionally to its game impact:
    #
    # Stat                                          typ.value  weight  ~score  tier
    # +2 Rare Monsters from Abysses (required)          2       —      req     S+
    # % Abyssal Mod chance (more Amanamu → Omen)       25        4     100     S
    # % increased Rare Monsters                         30        3      90     S
    # Abysses spawn % increased Monsters                25        2      50     S
    # Monsters have % increased Effectiveness           20        2      40     A
    # Abyss Pits twice as likely to have Rewards         1       40      40     A  (binary)
    # # additional Abysses                               1       10      10     A
    # % chance for 4 additional Abysses                 50        1      50     A
    # Abyssal Monsters % Effectiveness per pit          20        1      20     A
    # % Monster Rarity                                  30        1      30     A
    # % Rarity of Items found in Map                    20        1      20     B
    # % increased Pack Size                             20        1      20     B
    ("🏆 Slot 4: S+ required + weighted sort (best overall)", {
        "query": {
            "status": {"option": "securable"},
            "type": "Abyss Tablet",
            "stats": [
                {"type": "weight", "disabled": False, "filters": [
                    {"id": "explicit.stat_2789248444", "value": {"weight": 4},  "disabled": False},
                    {"id": "explicit.stat_3793155082", "value": {"weight": 3},  "disabled": False},
                    {"id": "explicit.stat_944630113",  "value": {"weight": 2},  "disabled": False},
                    {"id": "explicit.stat_2890355696", "value": {"weight": 1},  "disabled": False},
                    {"id": "explicit.stat_4256531808", "value": {"weight": 40}, "disabled": False},
                    {"id": "explicit.stat_664606484",  "value": {"weight": 1},  "disabled": False},
                    {"id": "explicit.stat_4142653832", "value": {"weight": 1},  "disabled": False},
                    {"id": "explicit.stat_2017682521", "value": {"weight": 1},  "disabled": False},
                    {"id": "explicit.stat_3490187949", "value": {"weight": 10}, "disabled": False},
                    {"id": "explicit.stat_2306002879", "value": {"weight": 1},  "disabled": False},
                    {"id": "explicit.stat_2065500219", "value": {"weight": 2},  "disabled": False},
                ]},
                {"type": "and", "filters": [
                    {"id": "explicit.stat_243380454", "value": {"min": 2}, "disabled": False},
                    {"id": "explicit.stat_2789248444", "disabled": True},
                    {"id": "explicit.stat_3793155082", "disabled": True},
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
print(f"  POE2 Abyss Juice Tablet Trade Links — {LEAGUE}")
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

# ── Save to markdown ──────────────────────────────────────────────────────────

md_path = os.path.join(os.path.dirname(__file__), "abyss_setup.md")
generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

with open(md_path, "w") as f:
    f.write(f"# POE2 Abyss Juice Tablet Setup — {LEAGUE}\n\n")
    f.write(f"> Guide: [Perra — BEST CURRENCY FARM (150 Div/Hour)](https://youtu.be/8b4yK-Qtd7M?t=354)  \n")
    f.write(f"> Generated: {generated_at} · Instant buyout only · 10 uses remaining (anti-scam)\n\n")
    f.write("---\n\n")
    f.write("## Trade Links\n\n")
    f.write("| # | Search | Link |\n")
    f.write("|---|--------|------|\n")
    for i, (name, url) in enumerate(results, 1):
        # strip emoji for table
        clean = name.split(":", 1)[-1].strip() if ":" in name else name
        if url:
            f.write(f"| {i} | {name} | [trade link]({url}) |\n")
        else:
            f.write(f"| {i} | {name} | ❌ failed |\n")
    f.write("\n---\n\n")
    f.write("## Tablet Modifier Tier List\n\n")
    f.write("| Tier | Modifier | Priority |\n")
    f.write("|------|----------|----------|\n")
    f.write("| **S+** | +2 Rare Monsters spawned from Abysses | Mandatory on every tablet |\n")
    f.write("| **S** | Extra Abyssal Modifiers on Rares | Stack with S+ |\n")
    f.write("| **S** | Map has % increased Rare Monsters | Stack with S+ |\n")
    f.write("| **A** | Map has % increased Monster Rarity | Filler |\n")
    f.write("| **A** | Map contains additional Abysses | Filler |\n")
    f.write("\n---\n\n")
    f.write("## Setup Steps\n\n")
    f.write("1. Find a **City biome** map (for the extra tablet slot)\n")
    f.write("2. Apply **200% Delirium** via Grand Mirror\n")
    f.write("3. Add **Ritual** via Head of the King (not ritual tablets)\n")
    f.write("4. Use **Unforeseen Consequences** unique tablet\n")
    f.write("5. Fill remaining slots with **S+/S tier** abyss tablets\n")
    f.write("6. Target **~15 additional Abysses** per map\n")
    f.write("7. Stack **~240% Item Rarity** on gear\n")

print(f"✅ Saved to {md_path}")

