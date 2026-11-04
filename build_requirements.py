#!/usr/bin/env python3
# Copyright (C) 2026 Redbarn Christian Co.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild requirements.json from the RuneScape Wiki. Rerun when Jagex changes any cape's requirements."""
import datetime
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://runescape.wiki/api.php"
UA = {"User-Agent": "rs3comp (personal completionist cape guide)"}
# list key -> wiki achievement category whose rendered list is that cape's requirements
LISTS = {"comp": "Completionist Cape", "mqc": "Master Quest Cape", "comp_t": "Trimmed Completionist Cape"}
LICENSE = "Text and lists from the RuneScape Wiki, under CC BY-NC-SA 3.0 (creativecommons.org/licenses/by-nc-sa/3.0)"
BREAKDOWNS = ["Completionist Cape (achievement)/Breakdown", "Trimmed Completionist Cape (achievement)/Breakdown"]


def api(**params):
    q = urllib.parse.urlencode({"format": "json", "formatversion": 2, **params})
    with urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers=UA), timeout=60) as r:
        return json.load(r)


def wikitext(titles):
    """{requested title: wikitext}, following redirects so callers can look up the titles they asked for."""
    d = api(action="query", prop="revisions", rvprop="content", rvslots="main", redirects=1, titles="|".join(titles))["query"]
    hops = {x["from"]: x["to"] for x in d.get("normalized", []) + d.get("redirects", [])}
    text = {p["title"]: p["revisions"][0]["slots"]["main"]["content"] for p in d["pages"] if "revisions" in p}
    out = {}
    for t in titles:
        final = t
        while final in hops and final not in text:
            final = hops[final]
        if final in text:
            out[t] = text[final]
    return out


def field(text, name):
    m = re.search(rf"^\|\s*{name}\s*=(.*?)(?=^\||^\}}\}})", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def plain(s):
    s = re.sub(r"\{\{[^{}]*\}\}", "", re.sub(r"\{\{[^{}]*\}\}", "", s))  # two passes for nested templates
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    return re.sub(r"\s*\(X/[^)]*\)|\s*\(\)", "", s).strip()


def display(title):
    return title.removesuffix(" (achievement)")


def cape_list(category):
    """Page titles of every achievement a cape needs, from the wiki's rendered achievement list."""
    rendered = api(action="parse", prop="text", contentmodel="wikitext",
                   text=f"{{{{Achievements list|{category}|sequence_number=No}}}}")["parse"]["text"]
    return [html.unescape(t) for t in re.findall(r"<tr[^>]*>\s*<td[^>]*>.*?title=\"([^\"]+)\"", rendered, re.S)]


def considerations():
    """{achievement: (section, note)} from the wiki's Breakdown pages: time gated, time heavy, team, farming."""
    found = {}
    for text in wikitext(BREAKDOWNS).values():
        for section, body in re.findall(r"^=== (.+?) ===\n(.*?)(?=^==|\Z)", text, re.M | re.S):
            for row in body.split("|-")[1:]:
                cells = re.split(r"\n\|", "\n" + row.strip().removesuffix("|}").strip())[1:]  # last row holds table end
                note = "; ".join(filter(None, (plain(l.lstrip("* ")) for l in cells[-1].splitlines()))) if len(cells) > 2 else ""
                for name in re.findall(r"\[\[([^\]|]+)", cells[0] if cells else ""):
                    found.setdefault(display(name), (section, note))
    return found


def quest_guide():
    """{quest title: {order, length, quick}} from the wiki's optimal quest order (Quests/Progression guide)."""
    text = wikitext(["Quests/Progression guide"])["Quests/Progression guide"]
    out = {}
    for row in text.split('|- data-rowid="')[1:]:
        title = html.unescape(row.split('"', 1)[0])
        cells = re.split(r"\n\|", "\n" + row.split("\n", 1)[1].strip())[1:]
        if title not in out:
            out[title] = {"order": len(out), "length": plain(cells[2]).strip() if len(cells) > 2 else "",
                          "quick": "/Quick guide" in row}
    return out


def main():
    lists = {key: cape_list(cat) for key, cat in LISTS.items()}
    titles = list(dict.fromkeys(t for ts in lists.values() for t in ts))
    pages = {}
    for i in range(0, len(titles), 50):  # API limit: 50 titles per query
        pages.update(wikitext(titles[i:i + 50]))
    consider = considerations()
    achievements = {}
    for title in titles:
        text, name = pages.get(title, ""), display(title)
        reqs = field(text, "requirements")
        achievements[name] = {
            "name": name,
            "page": title,
            "description": plain(field(text, "description")),
            "category": plain(field(text, "maincategory")) or "Other",
            "subcategory": plain(field(text, "subcategory")),
            "skills": {s: int(l) for s, l in re.findall(r"\{\{Skillreq\|([^|}]+)\|(\d+)", reqs)},
            "after": re.findall(r"\[\[([^\]|]+)", reqs),
            "consider": consider.get(name, (None, ""))[0],
            "note": consider.get(name, (None, ""))[1],
        }
    quests = quest_guide()
    if (min(map(len, lists.values())) < 50 or not achievements.get("Master Skiller", {}).get("skills")
            or not achievements.get("Quest Cape", {}).get("after") or len(quests) < 200):
        raise RuntimeError("The wiki page layout changed, so the current requirements were kept.")
    out = {"source": "https://runescape.wiki", "license": LICENSE, "fetched": datetime.date.today().isoformat(),
           "achievements": achievements, "lists": {k: [display(t) for t in ts] for k, ts in lists.items()},
           "quests": quests}
    Path(__file__).with_name("requirements.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(achievements)} achievements, lists " + ", ".join(f"{k} {len(v)}" for k, v in lists.items())
          + f", {len(quests)} quests in guide order")
    return out


if __name__ == "__main__":
    main()
