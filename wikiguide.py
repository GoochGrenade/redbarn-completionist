#!/usr/bin/env python3
# Copyright (C) 2026 Redbarn Christian Co.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn a RuneScape Wiki page into a step-by-step guide: details to check first, then sections of steps."""
import hashlib
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import build_requirements
import rs3comp

CACHE = Path.home() / ".cache" / "rs3comp" / "guides"
MAX_AGE = 7 * 24 * 3600
# Page furniture: navigation, hidden tooltips, Leagues notes, map links, references
SKIP_CLASSES = ("hidden", "navbox", "toc", "rs-external-header-links", "mw-kartographer-maplink", "reference",
                "mw-references-wrap", "messagebox", "infobox-bottom-links", "noprint")
SKIP_TAGS = {"img", "figure", "figcaption", "style", "script", "sup", "map"}
SKIP_SECTIONS = {"update history", "references", "gallery", "trivia", "transcript", "see also",
                 "required for completing", "music unlocked"}
DETAILS = ("start point", "requirements", "required items", "items required", "recommended", "combat",
           "enemies to defeat", "description", "length")
VOID = {"br", "img", "hr", "wbr", "input", "meta", "link", "source", "col", "area", "base"}


class GuideError(Exception):
    pass


def training_page(skill):
    """The wiki's training guide for a skill; plain "<Skill> training" is often a disambiguation page."""
    return "Pay-to-play melee training" if skill in ("Attack", "Strength", "Defence") else f"Pay-to-play {skill} training"


def fetch(page):
    """{title, html, stale} for a wiki page, from a 7-day cache when possible; a stale copy beats no copy."""
    path = CACHE / (hashlib.sha1(page.encode()).hexdigest() + ".json")
    cached = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if cached and time.time() - cached["fetched"] < MAX_AGE:
        return {**cached, "stale": False}
    try:
        d = build_requirements.api(action="parse", page=page, prop="text", redirects=1, disableeditsection=1)
        if "error" in d:
            raise GuideError(f"The RuneScape Wiki has no page called “{page}”.")
        fresh = {"title": d["parse"]["title"], "html": d["parse"]["text"], "fetched": time.time()}
    except GuideError:
        raise
    except Exception as e:  # offline or wiki down
        if cached:
            return {**cached, "stale": True}
        raise GuideError(f"Couldn't reach the RuneScape Wiki: {e}") from e
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fresh), encoding="utf-8")
    return {**fresh, "stale": False}


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.details, self.sections, self.skills = [], [{"title": "", "blocks": []}], []
        self.stack = []  # (tag, what) for open elements; what says what to do on close
        self.skipping = 0
        self.lists = 0  # open <ul>/<ol> depth outside the details table
        self.buf = []  # text of the block being read
        self.heading = None
        self.details_depth = 0  # >0 inside the quest details table or achievement infobox
        self.cells = []
        self.label = None  # an infobox header row ("Requirements") whose content is the next row
        self.chat = None

    # -- helpers
    def flush(self, kind=None):
        text = re.sub(r"[ \t\r\f\v]+", " ", "".join(self.buf)).replace(" \n", "\n").strip()
        self.buf = []
        if not text or self.details_depth or self.heading is not None:
            return text
        section = self.sections[-1]
        if kind == "step":
            section["blocks"].append(("step", max(self.lists - 1, 0), text))
        elif kind == "row":
            section["blocks"].append(("row", 0, text))
        else:
            section["blocks"].append(("text", 0, text))
        return text

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        skip = (tag in SKIP_TAGS or "display:none" in (a.get("style") or "").replace(" ", "")
                or any(c in SKIP_CLASSES or c.startswith("league") for c in classes))
        if tag == "img" and not self.skipping and self.chat is None and a.get("alt") in rs3comp.SKILLS:
            self.buf.append(f" {a['alt']}")  # a skill icon after a level, e.g. "30 [Defence icon]"
        if self.skipping or skip:
            if tag not in VOID:
                self.skipping += 1
                self.stack.append((tag, "skip"))
            return
        if self.chat is not None:  # inside a chat-options span: keep only the option titles
            if "chat-options-underline" in classes:
                self.chat.append(a.get("title") or "")
            if tag not in VOID:
                self.stack.append((tag, "chat-inner"))
            return
        if tag in VOID:
            if tag == "br":
                self.buf.append("\n")
            return
        what = None
        if tag == "span" and "skillreq" in classes and a.get("data-skill"):
            skill, level = a["data-skill"], int(a.get("data-level") or 0)
            self.skills.append((skill, level))
            self.buf.append(f" {level} {skill} ")
            self.skipping += 1  # its own text is the level and an icon link
            what = "skip"
        elif tag == "span" and "chat-options" in classes:
            self.chat, what = [], "chat"
        elif tag == "span" and "coins" in classes:
            what = "coins"
        elif tag == "table" and ({"questdetails", "infobox-achievement", "rsw-infobox"} & set(classes) or self.details_depth):
            self.details_depth += 1
            what = "details"
        elif self.details_depth:
            if tag == "tr" and self.details_depth == 1:
                self.cells, self.buf, what = [], [], "detail-row"
            elif tag in ("th", "td") and self.details_depth == 1:
                self.buf, what = [], "detail-cell"
            elif tag == "li":
                self.buf.append("\n• ")
        elif re.fullmatch(r"h[2-4]", tag):
            self.flush()
            self.heading, what = [], "heading"
        elif tag in ("ul", "ol"):
            self.flush("step" if self.lists else None)  # a list inside a step: the step's own text comes first
            self.lists += 1
            what = "list"
        elif tag == "li":
            self.flush("step" if self.lists > 1 else None)
            what = "step"
        elif tag == "p":
            self.flush()
            what = "text"
        elif tag == "tr":
            self.flush()
            self.cells, what = [], "row"
        elif tag in ("td", "th") and self.stack_has("row"):
            self.flush_cell()
            what = "cell"
        self.stack.append((tag, what))

    def stack_has(self, what):
        return any(w == what for _, w in self.stack)

    def flush_cell(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            self.cells.append(text)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        # close up to the matching open tag; wiki HTML is well formed, this guards the odd stray tag
        while self.stack:
            open_tag, what = self.stack.pop()
            self.close_element(what)
            if open_tag == tag:
                break

    def close_element(self, what):
        if what == "skip":
            self.skipping -= 1
        elif what == "chat":
            options = [o for o in self.chat if o]
            self.chat = None
            if options:
                self.buf.append(" (Chat: " + " → ".join(options) + ")")
        elif what == "coins":
            self.buf.append(" coins")
        elif what == "details":
            self.details_depth -= 1
        elif what == "detail-cell":
            self.cells.append(re.sub(r"[ \t]+", " ", "".join(self.buf)).strip())
            self.buf = []
        elif what == "detail-row":
            cells = [c for c in self.cells if c]
            if not cells:  # spacer row
                pass
            elif len(cells) == 1 and self.label is None:
                self.label = cells[0]
            else:
                label, content = (self.label, cells[0]) if len(cells) == 1 else (cells[0], cells[1])
                self.label = None
                label = label.split("\n")[0].strip()
                if label.lower().startswith(DETAILS) and (text := tidy(content, self.own)):
                    self.details.append((label, text))
            self.cells = []
        elif what == "heading":
            title = re.sub(r"\s+", " ", "".join(self.heading)).strip()
            self.heading = None
            self.sections.append({"title": title, "blocks": []})
        elif what == "list":
            self.flush("step")
            self.lists -= 1
        elif what == "step":
            self.flush("step")
        elif what == "text":
            self.flush()
        elif what == "cell":
            self.flush_cell()
        elif what == "row":
            self.flush_cell()
            if self.cells:
                self.sections[-1]["blocks"].append(("row", 0, " · ".join(self.cells)))
            self.cells = []

    def handle_data(self, data):
        if self.skipping or self.chat is not None:
            return
        (self.heading if self.heading is not None else self.buf).append(data.replace("\xa0", " "))


def tidy(text, own):
    """Requirement text without filler: "• None" lines, and the quest's own name heading its requirement tree."""
    text = re.sub(r"\s*\(X/\d+\)", "", text)  # the in-game progress counter
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    lines = [l for l in lines if l and l not in ("• None", f"• {own}")]
    if all(l.endswith(":") for l in lines):  # only headings like "Quests:" are left
        return "None"
    return "\n".join(l for i, l in enumerate(lines) if not (l.endswith(":") and (i + 1 == len(lines) or lines[i + 1].endswith(":"))))


def parse(html, own=""):
    """{details: [(label, text)], sections: [{title, blocks: [(kind, depth, text)]}], skills: [(skill, level)]}.

    kind is "step" (a list item; depth 0 is top level), "text" (a paragraph) or "row" (a table row).
    own is the page's own quest name, left out of its requirement list.
    """
    # shortcut: generic HTML-to-steps flattening; pages with unusual layouts read plainly, add handling if one reads badly
    p = _Parser()
    p.own = own
    p.feed(html)
    p.close()
    p.flush()
    sections = [s for s in p.sections if s["blocks"] and s["title"].lower() not in SKIP_SECTIONS]
    return {"details": p.details, "sections": with_goal_step(sections), "skills": p.skills}


GOAL = re.compile(r"^.{1,150}? is an? (?:[\w-]+ )?achievement (?:(?:that|which) requires (?:the )?(?:players? )?(?:to )?"
                  r"|(?:that is |which is )?completed by "
                  r"|(?:that|which) tracks the player's progress (?:into|in|towards?) )(.+)$", re.S)


def with_goal_step(sections):
    """Achievement pages open with "X is an achievement that requires the player to do Y. …".

    Lift "Do Y." out as a first step to tick, leaving the rest of the paragraph as text. Thin pages
    have no other steps, so this gives every achievement a clear goal.
    """
    for s in sections:
        for i, (kind, _, text) in enumerate(s["blocks"]):
            if kind != "text":
                continue
            m = GOAL.match(text)
            if not m:
                return sections  # only the page's opening paragraph can state the goal
            goal, _, rest = m.group(1).partition(". ")
            goal = goal[0].upper() + goal[1:].rstrip(".") + "."
            blocks = s["blocks"][:i] + ([("text", 0, rest)] if rest.strip() else []) + s["blocks"][i + 1:]
            return [{"title": "Do this", "blocks": [("step", 0, goal)]}] + \
                [dict(x, blocks=blocks) if x is s else x for x in sections if x is not s or blocks]
    return sections


def level_range(title):
    """(start, end) from a heading like "Levels 35-48: …" or "Level 20+"; end is None for open-ended."""
    m = re.match(r"Levels?\s+(\d+)\s*(?:[-–]\s*(\d+))?\s*(\+)?", title)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else (None if m.group(3) else start)
    return start, end


def level_section(sections, level):
    """Index of the "Levels A-B" section that covers this level, preferring the most specific (highest start)."""
    fits = [(r[0], i) for i, s in enumerate(sections)
            if (r := level_range(s["title"])) and r[0] <= level and (r[1] is None or level <= r[1])]
    return max(fits)[1] if fits else None
