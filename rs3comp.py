#!/usr/bin/env python3
# Copyright (C) 2026 Redbarn Christian Co.
# SPDX-License-Identifier: GPL-3.0-or-later
"""RS3 cape guide (quest, max, completionist and their master/trimmed versions): what to do next, from RuneMetrics."""
import argparse
import difflib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRESS = Path.home() / ".config" / "rs3comp" / "progress.json"
WIKI = "https://runescape.wiki/w/"
# RuneMetrics skillvalues ids, in order
SKILLS = ["Attack", "Defence", "Strength", "Constitution", "Ranged", "Prayer", "Magic", "Cooking",
          "Woodcutting", "Fletching", "Fishing", "Firemaking", "Crafting", "Smithing", "Mining", "Herblore",
          "Agility", "Thieving", "Slayer", "Farming", "Runecrafting", "Hunter", "Construction", "Summoning",
          "Dungeoneering", "Divination", "Invention", "Archaeology", "Necromancy"]
ELITE_XP = {99: 36_073_511, 120: 80_618_654}  # Invention uses the elite curve; only cape targets are needed
# Sections of the wiki's comp cape Breakdown page: (sort rank, advice)
CONSIDER = {"Time gated": (0, "Start early: progress is limited per day or week"),
            "Farming": (0, "Start early: crops take time to grow"),
            "Minigames & team based activities": (2, "Needs other players"),
            "Time heavy": (3, "Long grind")}
# In route order. Each cape is a wiki achievement list, a level in every skill, or other capes.
CAPES = {
    "quest": {"title": "Quest Cape", "achievements": ["Quest Cape"], "wiki": "Quest Cape",
              "claim": "Buy it from the Wise Old Man in Draynor Village for 99,000 coins."},
    "max": {"title": "Max cape", "skills": 99, "wiki": "Max cape",
            "claim": "Buy it from Max in Varrock (later from Elen Anterth in the Max Guild) for 2,871,000 coins."},
    "mqc": {"title": "Master quest cape", "list": "mqc", "wiki": "Master quest cape",
            "claim": "Buy it from Curator Haig Halen in Varrock Museum for 120,000 coins."},
    "comp": {"title": "Completionist cape", "list": "comp", "wiki": "Completionist cape",
             "claim": "Buy it from the Museum guard on the top floor of Varrock Museum for 5,000,000 coins."},
    "comp_t": {"title": "Completionist cape (t)", "list": "comp_t", "wiki": "Completionist cape (t)",
               "claim": "Buy it from the Museum guard on the top floor of Varrock Museum for 5,000,000 coins."},
    "master_max": {"title": "Master max cape", "skills": 120, "wiki": "Master max cape",
                   "claim": "Put the blurite keystone in the ornate grave in Falador Park, then buy it from Minerva "
                            "in Falador for 3,480,000 coins."},
    "master_comp": {"title": "Master completionist cape", "capes": ["master_max", "comp"],
                    "wiki": "Master completionist cape",
                    "claim": "Admire the ornate grave in Falador Park while wearing the master max cape, with a "
                             "completionist cape you've worn in your inventory."},
    "master_comp_t": {"title": "Master completionist cape (t)", "capes": ["master_max", "comp_t"],
                      "wiki": "Master completionist cape (t)",
                      "claim": "Admire the ornate grave in Falador Park while wearing the master max cape, with a "
                               "completionist cape (t) in your inventory."},
}
# Achievements that stand for a whole cape; Quest Cape and Master Skiller are checked from RuneMetrics instead
NESTED = {"Completionist Cape": "comp", "Master Quest Cape": "mqc"}
META = {"Quest Cape", "Master Skiller", *NESTED}
DIFFICULTY = ["Novice", "Intermediate", "Experienced", "Master", "Grandmaster", "Special"]


def advice(a):
    return " · ".join(filter(None, (CONSIDER.get(a.get("consider"), (1, ""))[1], a.get("note"))))


def xp_for(level, elite=False):
    if elite:
        return ELITE_XP[level]
    return sum(int(n + 300 * 2 ** (n / 7)) for n in range(1, level)) // 4


def fetch(url):
    # RuneMetrics answers 403 to Python's default User-Agent
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "rs3comp"}), timeout=30) as r:
        return json.load(r)


class PlayerError(Exception):
    pass


def load_player(rsn):
    q = urllib.parse.quote(rsn)
    try:
        profile = fetch(f"https://apps.runescape.com/runemetrics/profile/profile?user={q}&activities=0")
        quests = fetch(f"https://apps.runescape.com/runemetrics/quests?user={q}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise PlayerError(f"Could not reach RuneMetrics: {e}")
    if profile.get("error") == "PROFILE_PRIVATE":
        raise PlayerError(f"{rsn}'s RuneMetrics profile is private. Make it public in game: "
                 "Settings > Gameplay > Hiscores/RuneMetrics, or on runescape.com/runemetrics.")
    if "error" in profile:
        raise PlayerError(f"No RuneMetrics profile for '{rsn}' ({profile['error']}). Check the spelling; "
                 "the profile appears after logging in once with RuneMetrics enabled.")
    return profile, quests["quests"]


def resolve(cape, reqs):
    """(skill targets, needs every quest, checklist names, included capes) for a cape, nested capes flattened."""
    c = CAPES[cape]
    targets = {s: c["skills"] for s in SKILLS} if "skills" in c else {}
    needs_quests, checklist, includes = False, set(), []
    names = reqs["lists"][c["list"]] if "list" in c else c.get("achievements", [])
    for n in names:
        if n == "Quest Cape":
            needs_quests = True
        elif n == "Master Skiller":
            for s, t in reqs["achievements"][n]["skills"].items():
                targets[s] = max(targets.get(s, 0), t)
        elif n not in NESTED:
            checklist.add(n)
    for sub in c.get("capes", []) + [NESTED[n] for n in names if n in NESTED]:
        t, q, cl, inc = resolve(sub, reqs)
        for s, lvl in t.items():
            targets[s] = max(targets.get(s, 0), lvl)
        needs_quests, checklist, includes = needs_quests or q, checklist | cl, includes + [sub] + inc
    return targets, needs_quests, checklist, list(dict.fromkeys(includes))


def guide(profile, quests, reqs, done, cape="comp"):
    """Pure ranking for one cape: profile/quests are RuneMetrics JSON, reqs is requirements.json, done is ticked names."""
    levels = {SKILLS[s["id"]]: s["level"] for s in profile["skillvalues"]}
    levels["Combat"] = profile["combatlevel"]  # wiki lists combat level as a skill requirement
    xp = {SKILLS[s["id"]]: s["xp"] // 10 for s in profile["skillvalues"]}  # API reports xp x10
    quest = {q["title"]: {**q, **reqs["quests"].get(q["title"], {})} for q in quests}
    achs = reqs["achievements"]
    targets, needs_quests, names, includes = resolve(cape, reqs)
    cape_quests = achs["Quest Cape"]["after"] if needs_quests else []

    def missing(a):
        need = [f"{s} {l}" for s, l in a["skills"].items() if levels.get(s, 1) < l]
        need += [t for t in a["after"] if t in quest and quest[t]["status"] != "COMPLETED"]
        return need

    def quest_order(q):  # the wiki's optimal order; quests it doesn't list go last, easiest first
        return (q["status"] != "STARTED", q.get("order", 10_000 + q["difficulty"]), q["title"])

    open_quests = sorted((quest[t] for t in cape_quests if quest[t]["status"] != "COMPLETED"), key=quest_order)
    checklist = [achs[n] for n in sorted(names) if n not in done]
    # shortcut: the wiki gives no time per achievement, so this orders by its Breakdown sections only
    doable_items = sorted((a for a in checklist if not missing(a)), key=lambda a: CONSIDER.get(a["consider"], (1,))[0])
    locked_items = [(a, missing(a)) for a in checklist if missing(a)]
    # XP, not level: RuneMetrics caps 99-max skills at level 99 even at 200m XP
    target_xp = {s: xp_for(t, s == "Invention") for s, t in targets.items()}
    skills = sorted(
        ({"skill": s, "level": levels[s], "target": targets[s], "xp_left": target_xp[s] - xp[s],
          "blocks": [a["name"] for a in checklist if a["skills"].get(s, 0) > levels[s]]}
         for s in targets if xp[s] < target_xp[s]),
        key=lambda r: (not r["blocks"], r["xp_left"]))  # skills that unlock achievements first
    xp_left = sum(r["xp_left"] for r in skills)
    summary, fractions = {}, []
    for key, total, left in (("skills", len(targets), len(skills)), ("quests", len(cape_quests), len(open_quests)),
                             ("checklist", len(names), len(checklist))):
        if total:
            summary[key] = (total - left, total)
            fractions.append(1 - xp_left / sum(target_xp.values()) if key == "skills" else 1 - left / total)
    return {
        "cape": cape, "includes": includes,
        "quests": [q for q in open_quests if q["userEligible"]],
        "quests_locked": [q for q in open_quests if not q["userEligible"]],
        "items": doable_items, "items_locked": locked_items, "skills": skills, "xp_left": xp_left,
        # shortcut: equal weight for skill XP, quests and checklist; a guess at "how far along", not time left
        "overall": sum(fractions) / len(fractions), "summary": summary,
    }


def progress_all(profile, quests, reqs, done):
    """({cape: overall}, the unfinished cape closest to done or None)."""
    overall = {c: guide(profile, quests, reqs, done, c)["overall"] for c in CAPES}
    left = [c for c, f in overall.items() if f < 1]
    return overall, max(left, key=overall.get) if left else None


def link(name):
    return WIKI + urllib.parse.quote(name.replace(" ", "_"))


def render(name, g, limit, fetched):
    out = [f"{CAPES[g['cape']]['title']} guide for {name}  (requirements from the RS Wiki, {fetched})", ""]
    cut = (lambda xs: xs) if limit is None else (lambda xs: xs[:limit])

    def more(xs):
        if limit is not None and len(xs) > limit:
            out.append(f"   ...and {len(xs) - limit} more (--all)")

    out.append("1. Quests you can do now (quests unlock content and give XP, so do these first)")
    for q in cut(g["quests"]):
        tag = "STARTED, finish it" if q["status"] == "STARTED" else q.get("length") or DIFFICULTY[min(q["difficulty"], 5)]
        out.append(f" - {q['title']}  [{tag}]  {link(q['title'])}")
    more(g["quests"])
    if g["quests_locked"]:
        out.append(f"   {len(g['quests_locked'])} more quests need higher skills or other quests first.")
    if "quests" not in g["summary"]:
        out.append("   None needed for this cape.")
    elif not g["quests"] and not g["quests_locked"]:
        out.append("   All done: every quest is complete.")

    out += ["", "2. Achievements you can do now: start-early ones first, long grinds last (tick off with --done \"Name\")"]
    for a in cut(g["items"]):
        tip = f"  [{advice(a)}]" if advice(a) else ""
        out.append(f" - {a['name']}: {a['description']}{tip}  {link(a['name'])}")
    more(g["items"])
    if limit is None:
        for a, need in g["items_locked"]:
            out.append(f" x {a['name']}: needs {', '.join(need[:6])}{' ...' if len(need) > 6 else ''}")
    elif g["items_locked"]:
        out.append(f"   {len(g['items_locked'])} more are locked behind skills or quests (--all to see what each needs).")

    out += ["", "3. Skills to train (ones that unlock achievements first, then closest to target)"]
    for s in cut(g["skills"]):
        blocks = f"  unlocks {len(s['blocks'])} achievement(s)" if s["blocks"] else ""
        out.append(f" - {s['skill']}: {s['level']} -> {s['target']}, {s['xp_left']:,} xp left{blocks}")
    more(g["skills"])
    if "skills" not in g["summary"]:
        out.append("   None needed for this cape.")
    elif not g["skills"]:
        out.append("   All done: every skill is at its target.")

    sm = g["summary"]
    out += ["", "Progress: " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in sm.items())
            + f"  (overall {g['overall']:.0%}, {g['xp_left']:,} skill xp left)"]
    return "\n".join(out)


def load_progress():
    return json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}


def save_done(rsn, done):
    progress = load_progress()
    progress[rsn.lower()] = sorted(done)
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=1) + "\n")


def tick(rsn, query, names, add):
    match = [n for n in names if n.lower() == query.lower()] or [n for n in names if query.lower() in n.lower()]
    if len(match) != 1:
        hint = match or difflib.get_close_matches(query, names, n=5, cutoff=0.4)
        sys.exit(f"'{query}' matches {len(match)} achievements." + (f" Did you mean: {', '.join(hint)}?" if hint else ""))
    done = set(load_progress().get(rsn.lower(), []))
    done.add(match[0]) if add else done.discard(match[0])
    save_done(rsn, done)
    print(f"{'Ticked' if add else 'Unticked'}: {match[0]}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rsn", help="RuneScape name (RuneMetrics profile must be public)")
    ap.add_argument("--done", metavar="ACHIEVEMENT", help="tick off a checklist achievement")
    ap.add_argument("--undo", metavar="ACHIEVEMENT", help="untick a checklist achievement")
    ap.add_argument("--all", action="store_true", help="show every step, not just the top few")
    ap.add_argument("--cape", choices=CAPES, default="comp", help="which cape to guide (default: comp)")
    args = ap.parse_args()

    reqs = json.loads((HERE / "requirements.json").read_text())
    names = [n for n in reqs["achievements"] if n not in META]
    for query, add in ((args.done, True), (args.undo, False)):
        if query:
            tick(args.rsn, query, names, add)
    try:
        profile, quests = load_player(args.rsn)
    except PlayerError as e:
        sys.exit(str(e))
    done = set(load_progress().get(args.rsn.lower(), []))
    print(render(profile["name"], guide(profile, quests, reqs, done, args.cape), None if args.all else 5, reqs["fetched"]))


if __name__ == "__main__":
    main()
