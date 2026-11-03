#!/usr/bin/env python3
# Copyright (C) 2026 Redbarn Christian Co.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Redbarn Completionist: desktop window for the RS3 cape guides. The logic lives in rs3comp.py.

  rs3comp_gui.py --install     add it to your app menu (Linux)
  rs3comp_gui.py --uninstall   remove it from your app menu
  rs3comp_gui.py --self-test   build every cape's guide from the sample players, offline
"""
import ctypes
import functools
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import rs3comp

WINDOWS = sys.platform == "win32"
if WINDOWS and sys.stdout is None and len(sys.argv) > 1 and ctypes.windll.kernel32.AttachConsole(-1):
    # The packaged app has no console of its own; print --self-test to the one it was run from.
    sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8")
elif WINDOWS and sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the console's default code page can't print ✓
APP_ID = "co.redbarn.CompletionistGuide"
APP_NAME = "Redbarn Completionist"
VERSION = "1.1.0"
DEVELOPER = "Redbarn Christian Co."
COPYRIGHT = "© 2026 Redbarn Christian Co."
TAGLINE = "Step-by-step guides to every RuneScape 3 quest, max and completionist cape."
ICON_DIR = rs3comp.HERE / "data"
PACKAGES = ("Fedora: sudo dnf install python3-gobject gtk4 libadwaita\n"
            "  Ubuntu/Debian: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1")


def desktop_quote(path):
    # Desktop-entry rules: \"\`$ and backslash escaped inside quotes, % doubled.
    escaped = {"\"": "\\\"", "`": "\\`", "$": "\\$", "\\": "\\\\\\\\", "%": "%%"}
    return '"' + "".join(escaped.get(ch, ch) for ch in path) + '"'


def install_paths():
    share = Path.home() / ".local" / "share"
    return share / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg", share / "applications" / f"{APP_ID}.desktop"


def refresh_menus():
    share = Path.home() / ".local" / "share"
    for command in (["update-desktop-database", str(share / "applications")],
                    ["gtk-update-icon-cache", "-q", "-t", "-f", str(share / "icons" / "hicolor")]):
        if shutil.which(command[0]):
            subprocess.run(command, capture_output=True)


def ui_ready():
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gtk  # noqa: F401
        return True
    except (ImportError, ValueError):
        return False


def install():
    icon, launcher = install_paths()
    program = Path(__file__).resolve()
    program.chmod(program.stat().st_mode | 0o111)  # unzipped downloads lose the executable bit
    icon.parent.mkdir(parents=True, exist_ok=True)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICON_DIR / f"{APP_ID}.svg", icon)
    launcher.write_text(f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment={TAGLINE.rstrip(".")}
Exec={desktop_quote(str(program))}
Icon={APP_ID}
Categories=Game;
Keywords=RuneScape;RS3;completionist;quest cape;max cape;master;
StartupWMClass={APP_ID}
Terminal=false
""")
    refresh_menus()
    print(f"Installed {APP_NAME}. Open it from your app menu.\n"
          f"It runs from {program.parent}, so keep that folder where it is.")
    if not ui_ready():
        print(f"\nIt needs GTK 4, libadwaita and PyGObject before it can open:\n  {PACKAGES}")


def uninstall():
    for path in install_paths():
        path.unlink(missing_ok=True)
    refresh_menus()
    print(f"Removed {APP_NAME} from your app menu.")


if __name__ == "__main__" and sys.argv[1:2] in (["--install"], ["--uninstall"]):
    if WINDOWS:
        sys.exit(f"On Windows, open {APP_NAME} from the folder you unzipped; there's nothing to install.")
    {"--install": install, "--uninstall": uninstall}[sys.argv[1]]()
    sys.exit(0)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk
except (ImportError, ValueError):
    if __name__ != "__main__":
        raise
    sys.exit(f"{APP_NAME} needs GTK 4, libadwaita and PyGObject:\n  {PACKAGES}")

import build_requirements  # noqa: E402
LAST_NAME = rs3comp.PROGRESS.with_name("last-name")
DARK_MODE = rs3comp.PROGRESS.with_name("dark-mode")
CAPE_FILE = rs3comp.PROGRESS.with_name("cape")
SUMMARY_LABELS = {"skills": "Skills at target", "quests": "Quests", "checklist": "Achievements ticked off"}
# Redbarn Studio's colours; .dark-ui because CSS media queries don't follow a forced colour scheme
CSS = """
:root { --accent-bg-color: #a32a22; --accent-fg-color: #ffffff; --accent-color: #a32a22; }
.dark-ui { --accent-color: #ee7a70; }
/* finished rows go green; their check boxes and progress bars follow via the accent variables */
.completed { --accent-bg-color: var(--success-bg-color); --accent-color: var(--success-color);
             background-color: alpha(var(--success-color), 0.14); }
.completed label.title { color: var(--success-color); font-weight: 600; }
"""
# The Redbarn barn, the same artwork as Redbarn Studio's icon
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect x="8" y="8" width="112" height="112" rx="24" fill="#2a2523"/>
  <path d="M64 22 L96 42 L104 66 L104 106 L24 106 L24 66 L32 42 Z" fill="#a32a22"/>
  <path d="M64 22 L96 42 L104 66 L104 72 L98 72 L91 46 L64 29 L37 46 L30 72 L24 72 L24 66 L32 42 Z" fill="#f4efe6"/>
  <rect x="55" y="48" width="18" height="14" rx="1.5" fill="#2a2523" stroke="#f4efe6" stroke-width="3"/>
  <path d="M64 48 V62 M55 55 H73" stroke="#f4efe6" stroke-width="2"/>
  <rect x="44" y="72" width="40" height="34" fill="#7f1f19" stroke="#f4efe6" stroke-width="3.5"/>
  <path d="M44 72 L84 106 M84 72 L44 106 M64 72 V106" stroke="#f4efe6" stroke-width="3"/>
</svg>
"""


def open_url(widget, url):
    Gtk.UriLauncher.new(url).launch(widget.get_root(), None, None)


def linkify(r, url):
    r.set_activatable(True)
    r.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
    r.connect("activated", open_url, url)


def row(title, subtitle="", url=None):
    r = Adw.ActionRow(use_markup=False)  # names contain "&"; set text after, or it is parsed as markup first
    r.set_title(title)
    r.set_subtitle(subtitle)
    if url:
        linkify(r, url)
    return r


def link_button(url):
    b = Gtk.Button(icon_name="adw-external-link-symbolic", valign=Gtk.Align.CENTER, tooltip_text="Open wiki guide")
    b.add_css_class("flat")
    b.connect("clicked", open_url, url)
    return b


def pill(label, callback, *args):
    b = Gtk.Button(label=label, halign=Gtk.Align.CENTER, css_classes=["pill", "suggested-action"])
    b.connect("clicked", callback, *args)
    return b


def bar(fraction):
    return Gtk.ProgressBar(fraction=fraction, valign=Gtk.Align.CENTER, width_request=160)


# Cape icons, drawn here: colour is the family, a gold edge means trimmed, a gold star means master
CAPE_CLOTH = {"quest": (47, 95, 179), "max": (163, 42, 34), "comp": (91, 42, 158)}
CAPE_LOOK = {"quest": ("quest", False, False), "mqc": ("quest", False, True),
             "max": ("max", False, False), "master_max": ("max", False, True),
             "comp": ("comp", False, False), "comp_t": ("comp", True, False),
             "master_comp": ("comp", False, True), "master_comp_t": ("comp", True, True)}
GOLD = "#e3b23c"
STAR = '<path d="M32 21l3 6.2 6.8 1-4.9 4.7 1.2 6.7L32 36.4l-6.1 3.2 1.2-6.7-4.9-4.7 6.8-1z" fill="#f3d77a" stroke="#8a6414" stroke-width="1"/>'


@functools.cache
def cape_texture(key):
    family, trimmed, master = CAPE_LOOK[key]
    cloth = CAPE_CLOTH[family]
    hex_of = lambda rgb, f: "#" + "".join(f"{min(255, int(c * f)):02x}" for c in rgb)  # noqa: E731
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <path d="M17 11h30l9 41q-24 9-48 0z" fill="{GOLD if trimmed else hex_of(cloth, 0.6)}"/>
  <path d="M21 11h22l6 37q-17 6-34 0z" fill="{hex_of(cloth, 1)}"/>
  <path d="M27 11h4l-1 36q-3 0-5-1z" fill="{hex_of(cloth, 1.25)}" opacity="0.6"/>
  <rect x="14" y="6" width="36" height="8" rx="4" fill="{GOLD if trimmed or master else hex_of(cloth, 1.5)}"/>
  {STAR if master else ""}
</svg>"""
    try:
        return Gdk.Texture.new_from_bytes(GLib.Bytes.new(svg.encode()))
    except GLib.Error:  # no SVG loader: icons are decoration, so go without
        return None


def cape_image(key, size):
    return Gtk.Image(paintable=cape_texture(key), pixel_size=size, valign=Gtk.Align.CENTER)


def footer():
    try:
        logo = Gtk.Image(paintable=Gdk.Texture.new_from_bytes(GLib.Bytes.new(LOGO_SVG.encode())), pixel_size=24)
    except GLib.Error:  # no SVG loader: fall back to Redbarn Studio's installed icon
        logo = Gtk.Image(icon_name="co.redbarn.Studio", pixel_size=24)
    box = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER, margin_top=6, margin_bottom=6)
    box.append(logo)
    box.append(Gtk.Label(label=COPYRIGHT, css_classes=["caption", "dim-label"]))
    return box


def done_row(title, subtitle):
    r = row(title, subtitle)
    r.add_css_class("completed")
    r.add_suffix(Gtk.Image(icon_name="object-select-symbolic", css_classes=["success"]))
    return r


def expander(title, rows):
    e = Adw.ExpanderRow(use_markup=False)
    e.set_title(title)
    for r in rows:
        e.add_row(r)
    return e


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME, default_width=1120, default_height=880)
        self.set_size_request(360, 480)
        self.reqs = json.loads((rs3comp.HERE / "requirements.json").read_text())
        self.profile, self.batching, self.search_items = None, False, []
        self.cape = CAPE_FILE.read_text().strip() if CAPE_FILE.exists() else None
        self.cape = self.cape if self.cape in rs3comp.CAPES else None  # else the closest cape, once a profile loads

        self.entry = Gtk.Entry(placeholder_text="RuneScape name", width_chars=22,
                               primary_icon_name="avatar-default-symbolic")
        self.entry.connect("activate", self.load)
        self.button = Gtk.Button(label="Load", tooltip_text="Load or refresh (Ctrl+R)")
        self.button.add_css_class("suggested-action")
        self.button.connect("clicked", self.load)
        top = Gtk.Box(spacing=6)
        top.append(self.entry)
        top.append(self.button)
        header = Adw.HeaderBar(title_widget=top)
        menu = Gio.Menu()
        menu.append("Search", "win.search")
        menu.append("Refresh", "win.refresh")
        menu.append("Update Requirements", "win.update-requirements")
        about = Gio.Menu()
        if hasattr(Adw, "ShortcutsDialog"):  # libadwaita 1.8+
            about.append("Keyboard Shortcuts", "win.shortcuts")
        about.append(f"About {APP_NAME}", "win.about")
        menu.append_section(None, about)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu, tooltip_text="Main Menu",
                                       primary=True))
        dark = not DARK_MODE.exists() or DARK_MODE.read_text().strip() == "1"  # dark by default, like Redbarn Studio
        self.set_dark(dark)
        toggle = Gtk.ToggleButton(icon_name="weather-clear-night-symbolic", active=dark, tooltip_text="Dark mode")
        toggle.connect("toggled", lambda t: self.set_dark(t.get_active(), save=True))
        header.pack_end(toggle)
        self.search = Gtk.SearchEntry(placeholder_text="Search quests, achievements and skills", hexpand=True)
        self.search.connect("search-changed", self.on_search)
        self.search_bar = Gtk.SearchBar(child=Adw.Clamp(maximum_size=560, child=self.search))
        self.search_bar.connect_entry(self.search)
        find = Gtk.ToggleButton(icon_name="system-search-symbolic", tooltip_text="Search (Ctrl+F)")
        find.bind_property("active", self.search_bar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL)
        header.pack_end(find)
        for name, callback in (("refresh", self.load), ("update-requirements", self.update_requirements),
                               ("shortcuts", self.show_shortcuts), ("about", self.show_about),
                               ("focus-name", lambda *_: self.entry.grab_focus()),
                               ("search", lambda *_: find.set_active(not find.get_active()))):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        self.toasts = Adw.ToastOverlay()
        content = Adw.ToolbarView(content=self.toasts)
        content.add_top_bar(header)
        content.add_top_bar(self.search_bar)
        content.add_bottom_bar(footer())
        self.content = Adw.NavigationPage(title=APP_NAME, child=content)

        brand = Gtk.Box(spacing=8)
        brand.append(Gtk.Image(icon_name=APP_ID, pixel_size=24))
        brand.append(Gtk.Label(label=APP_NAME, css_classes=["heading"]))
        self.cape_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.cape_rows = {}
        for key, cape in rs3comp.CAPES.items():
            r = row(cape["title"], "Load your name to see progress")
            r.add_prefix(cape_image(key, 32))
            r.cape = key
            self.cape_list.append(r)
            self.cape_rows[key] = r
        self.cape_list.connect("row-selected", self.on_cape_selected)
        sidebar = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=self.cape_list, vexpand=True,
                                                             hscrollbar_policy=Gtk.PolicyType.NEVER))
        sidebar.add_top_bar(Adw.HeaderBar(title_widget=brand))
        self.split = Adw.NavigationSplitView(sidebar=Adw.NavigationPage(title="Capes", child=sidebar),
                                             content=self.content, min_sidebar_width=250, max_sidebar_width=300)
        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 720sp"))
        narrow.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(narrow)
        self.set_content(self.split)
        self.set_focus(self.entry)  # a focused sidebar would select its first cape before we pick the closest
        if self.cape:
            self.cape_list.select_row(self.cape_rows[self.cape])
        self.welcome()
        if LAST_NAME.exists():
            self.entry.set_text(LAST_NAME.read_text().strip())
            self.load()

    def set_dark(self, dark, save=False):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT)
        (self.add_css_class if dark else self.remove_css_class)("dark-ui")
        if save:
            DARK_MODE.parent.mkdir(parents=True, exist_ok=True)
            DARK_MODE.write_text("1" if dark else "0")

    def toast(self, title, button=None, on_button=None):
        t = Adw.Toast(title="", use_markup=False, timeout=4)
        t.set_title(title)
        if button:
            t.set_button_label(button)
            t.connect("button-clicked", lambda *_: on_button())
        self.toasts.add_toast(t)

    def status(self, title, text, icon=None, child=None):
        page = Adw.StatusPage(title=title, description=text, child=child)
        if icon:
            page.set_icon_name(icon)
        self.toasts.set_child(page)

    def welcome(self):
        steps = Adw.PreferencesGroup()
        for title, text in (("1. Make your RuneMetrics profile public", "In game: Settings › Gameplay › Hiscores/RuneMetrics"),
                            ("2. Enter your RuneScape name above", "Press Enter or Load"),
                            ("3. Pick the cape you're working on", "Then follow its steps from the top")):
            steps.add(row(title, text))
        steps.add(row("What is RuneMetrics?", "How Jagex shares your stats and quests", "https://runescape.wiki/w/RuneMetrics"))
        self.status(APP_NAME, TAGLINE, APP_ID, Adw.Clamp(maximum_size=480, child=steps))

    def load(self, *_):
        name = self.entry.get_text().strip()
        if not name:
            self.entry.grab_focus()
            return
        if not self.button.get_sensitive():  # Enter while a load is running
            return
        self.button.set_sensitive(False)
        self.status(f"Loading {name}…", "Fetching stats and quests from RuneMetrics.",
                    child=Adw.Spinner(width_request=48, height_request=48, halign=Gtk.Align.CENTER)
                    if hasattr(Adw, "Spinner")  # libadwaita 1.6+
                    else Gtk.Spinner(spinning=True, width_request=48, height_request=48, halign=Gtk.Align.CENTER))

        def work():
            try:
                profile, quests = rs3comp.load_player(name)
            except Exception as e:  # PlayerError or an API change; show it rather than hang
                GLib.idle_add(self.failed, name, str(e))
            else:
                GLib.idle_add(self.show, name, profile, quests)

        threading.Thread(target=work, daemon=True).start()

    def failed(self, name, text):
        self.button.set_sensitive(True)
        self.profile = None  # so a requirements update doesn't bring back the previous player
        self.status(f"Couldn't load {name}", text, "dialog-warning-symbolic", pill("Try Again", self.load))

    def show(self, name, profile, quests):
        self.button.set_sensitive(True)
        LAST_NAME.parent.mkdir(parents=True, exist_ok=True)
        LAST_NAME.write_text(name)
        self.name, self.profile, self.quests = name, profile, quests
        self.loaded_at = time.strftime("%H:%M")
        self.done = set(rs3comp.load_progress().get(name.lower(), []))
        closest = self.update_sidebar()
        if self.cape is None:  # first run: start on the cape that's nearest to done
            self.cape_list.select_row(self.cape_rows[closest or "comp"])  # renders via on_cape_selected
        else:
            self.render_guide()

    def on_cape_selected(self, _list, r):
        if r is None:
            return
        changed, self.cape = r.cape != self.cape, r.cape
        self.content.set_title(rs3comp.CAPES[r.cape]["title"])
        if changed:
            CAPE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CAPE_FILE.write_text(r.cape)
            if self.profile:
                self.render_guide()
            self.split.set_show_content(True)

    def update_sidebar(self):
        overall, closest = rs3comp.progress_all(self.profile, self.quests, self.reqs, self.done)
        for key, r in self.cape_rows.items():
            f = overall[key]
            r.set_subtitle("Complete" if f >= 1 else f"{f:.0%} done" + (" · Closest to done" if key == closest else ""))
            (r.add_css_class if f >= 1 else r.remove_css_class)("completed")
        return closest

    def track(self, r, group, parent=None):
        """Remember a row for search."""
        self.search_items.append((r, f"{r.get_title()} {r.get_subtitle() or ''}".lower(), group, parent))
        return r

    def render_guide(self):
        cape = rs3comp.CAPES[self.cape]
        g = rs3comp.guide(self.profile, self.quests, self.reqs, self.done, self.cape)
        self.search_items = []
        page = Adw.PreferencesPage()
        profile = self.profile

        summary = Adw.PreferencesGroup(
            title=f"{profile['name']} · {cape['title']}",
            description=f"Combat level {profile['combatlevel']} · Total level {profile['totalskill']:,} · "
                        f"Updated {self.loaded_at} · Requirements from {self.reqs['fetched']}")
        summary.set_header_suffix(cape_image(self.cape, 56))
        if g["overall"] >= 1:
            summary.add(done_row("Cape complete!", "Every requirement is met. Claim it below."))
        self.overall = Gtk.Label(css_classes=["title-1", "accent"], valign=Gtk.Align.CENTER)
        hero = self.hero = row("Overall progress", "Skill XP, quests and achievements, weighted equally"
                               if len(g["summary"]) > 1 else "")
        hero.add_suffix(self.overall)
        summary.add(hero)
        self.summary = {}
        for key in g["summary"]:
            r, b = row(SUMMARY_LABELS[key]), bar(0)
            r.add_suffix(b)
            summary.add(r)
            self.summary[key] = (r, b)
        if g["includes"]:
            includes = row("Includes", ", ".join(rs3comp.CAPES[k]["title"] for k in g["includes"]))
            for k in g["includes"]:
                includes.add_suffix(cape_image(k, 24))
            summary.add(includes)
        page.add(summary)
        self.update_summary(g)
        step = 0

        if "quests" in g["summary"]:
            step += 1
            group = Adw.PreferencesGroup(title=f"{step}. Quests you can do now",
                                         description="In the wiki's optimal order: each quest's rewards help with "
                                                     "the next, so you train as little as possible.")
            for q in g["quests"]:
                tag = "Started, finish it" if q["status"] == "STARTED" else q.get("length") or \
                    rs3comp.DIFFICULTY[min(q["difficulty"], 5)]
                url = rs3comp.link(f"{q['title']}/Quick guide" if q.get("quick") else q["title"])
                group.add(self.track(row(q["title"], tag + (" · Quick guide" if q.get("quick") else ""), url), group))
            if g["quests_locked"]:
                rows = [row(q["title"], q.get("length", ""), rs3comp.link(q["title"])) for q in g["quests_locked"]]
                e = expander(f"Locked: {len(rows)} need higher skills or other quests first", rows)
                group.add(e)
                for r in rows:
                    self.track(r, group, e)
            if not g["quests"] and not g["quests_locked"]:
                group.add(done_row("All done", "Every quest is complete."))
            page.add(group)

        if "checklist" in g["summary"]:
            step += 1
            group = Adw.PreferencesGroup(title=f"{step}. Achievements you can do now",
                                         description="Start-early ones first, then by category. The game doesn't "
                                                     "share these, so tick them off as you finish them.")
            early = [a for a in g["items"] if rs3comp.CONSIDER.get(a["consider"], (1,))[0] == 0]
            for a in early:
                group.add(self.track(self.tick_row(a, False), group))
            by_category = {}
            for a in g["items"]:
                if a not in early:
                    by_category.setdefault(a["category"], []).append(a)
            for category, items in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
                rows = [self.tick_row(a, False) for a in items]
                e = expander(f"{category} · {len(items)} to do", rows)
                tick_all = Gtk.Button(label="Tick all", valign=Gtk.Align.CENTER, css_classes=["flat"],
                                      tooltip_text=f"Mark every {category} achievement here as done")
                tick_all.connect("clicked", self.tick_all, [r.check for r in rows], category)
                e.add_suffix(tick_all)
                group.add(e)
                for r in rows:
                    self.track(r, group, e)
            done = [self.reqs["achievements"][n] for n in sorted(self.done & rs3comp.resolve(self.cape, self.reqs)[2])]
            if done:
                rows = [self.tick_row(a, True) for a in done]
                e = expander(f"Done ({len(rows)})", rows)
                group.add(e)
                for r in rows:
                    self.track(r, group, e)
            if g["items_locked"]:
                rows = [row(a["name"], "Needs " + ", ".join(need), rs3comp.link(a["name"])) for a, need in g["items_locked"]]
                e = expander(f"Locked ({len(rows)})", rows)
                group.add(e)
                for r in rows:
                    self.track(r, group, e)
            page.add(group)

        if "skills" in g["summary"]:
            step += 1
            group = Adw.PreferencesGroup(title=f"{step}. Skills to train",
                                         description=f"{g['xp_left']:,} XP to go. Skills that unlock achievements "
                                                     "come first, then the closest to target. Click one for the "
                                                     "wiki's training guide.")
            for s in g["skills"]:
                target_xp = rs3comp.xp_for(s["target"], s["skill"] == "Invention")
                unlocks = f" · unlocks {len(s['blocks'])} achievement(s)" if s["blocks"] else ""
                r = row(s["skill"], f"{s['level']} → {s['target']} · {s['xp_left']:,} xp left{unlocks}")
                r.add_suffix(bar(1 - s["xp_left"] / target_xp))
                linkify(r, rs3comp.link(f"{s['skill']} training"))
                group.add(self.track(r, group))
            if not g["skills"]:
                group.add(done_row("All done", "Every skill is at its target."))
            page.add(group)

        step += 1
        claim = Adw.PreferencesGroup(title=f"{step}. Claim your cape")
        claim.add(row("How to get it", cape["claim"], rs3comp.link(cape["wiki"])))
        if "checklist" in g["summary"]:
            claim.add(row("Check in game", "Hero › Achievements › Completionist lists anything still missing",
                          rs3comp.link("Completionist achievements")))
        keys = list(rs3comp.CAPES)
        if self.cape != keys[-1]:
            following = keys[keys.index(self.cape) + 1]
            r = row(f"Next: {rs3comp.CAPES[following]['title']}", "Open its guide")
            r.add_prefix(cape_image(following, 32))
            r.set_activatable(True)
            r.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            r.connect("activated", lambda *_: self.cape_list.select_row(self.cape_rows[following]))
            claim.add(r)
        page.add(claim)
        self.toasts.set_child(page)
        if self.search.get_text():
            self.on_search(self.search)

    def tick_row(self, a, checked):
        r = row(a["name"], "\n".join(filter(None, (a["description"], rs3comp.advice(a)))))
        r.check = Gtk.CheckButton(active=checked, valign=Gtk.Align.CENTER, tooltip_text="Done")
        r.check.connect("toggled", self.on_tick, a["name"])
        r.add_prefix(r.check)
        if checked:
            r.add_css_class("completed")
        r.set_activatable_widget(r.check)
        r.add_suffix(link_button(rs3comp.link(a["name"])))
        return r

    def on_tick(self, check, name):
        # rows stay put until the next Load so the list doesn't jump while ticking
        self.done.add(name) if check.get_active() else self.done.discard(name)
        (check.get_ancestor(Adw.ActionRow).add_css_class if check.get_active()
         else check.get_ancestor(Adw.ActionRow).remove_css_class)("completed")
        if not self.batching:
            self.save_and_refresh()
            if check.get_active():
                self.toast(f"“{name}” ticked off", "Undo", lambda: check.set_active(False))

    def tick_all(self, _button, checks, category):
        todo = [c for c in checks if not c.get_active()]
        if todo:
            self.set_checks(todo, True)
            self.toast(f"Ticked off {len(todo)} {category} achievements", "Undo", lambda: self.set_checks(todo, False))

    def set_checks(self, checks, active):
        self.batching = True  # one save and one refresh for the whole batch
        for c in checks:
            c.set_active(active)
        self.batching = False
        self.save_and_refresh()

    def save_and_refresh(self):
        rs3comp.save_done(self.name, self.done)
        self.update_summary(rs3comp.guide(self.profile, self.quests, self.reqs, self.done, self.cape))
        self.update_sidebar()

    def update_summary(self, g):
        self.overall.set_label(f"{g['overall']:.0%}")
        (self.hero.add_css_class if g["overall"] >= 1 else self.hero.remove_css_class)("completed")
        for key, (have, total) in g["summary"].items():
            r, b = self.summary[key]
            r.set_subtitle(f"{have} / {total}" + (" · Complete" if have == total else ""))
            (r.add_css_class if have == total else r.remove_css_class)("completed")
            b.set_fraction(have / total)

    def on_search(self, entry):
        q = entry.get_text().strip().lower()
        groups, expanders = {}, {}
        for r, text, group, parent in self.search_items:
            r.set_visible(q in text)
            groups[group] = groups.get(group, False) or q in text
            if parent:
                expanders[parent] = expanders.get(parent, False) or q in text
        for e, hit in expanders.items():
            e.set_visible(hit or not q)
            if q:
                e.set_expanded(hit)
        for group, hit in groups.items():
            group.set_visible(hit or not q)

    def update_requirements(self, *_):
        self.toast("Checking the RuneScape Wiki for requirement changes…")
        old = set(self.reqs["achievements"])

        def work():
            try:
                new = build_requirements.main()
            except Exception as e:  # network or wiki layout; the old file is untouched
                GLib.idle_add(self.toast, f"Couldn't update requirements: {e}")
            else:
                GLib.idle_add(self.requirements_updated, old, new)

        threading.Thread(target=work, daemon=True).start()

    def requirements_updated(self, old, new):
        self.reqs = new
        names = set(new["achievements"])
        added, removed = len(names - old), len(old - names)
        self.toast(f"Requirements updated: {added} added, {removed} removed" if added or removed
                   else "Requirements are up to date")
        if self.profile:
            self.show(self.name, self.profile, self.quests)

    def show_shortcuts(self, *_):
        dialog = Adw.ShortcutsDialog()
        section = Adw.ShortcutsSection(title="General")
        for title, accel in (("Load or refresh", "<Control>r"), ("Type a RuneScape name", "<Control>l"),
                             ("Search", "<Control>f"), ("Main menu", "F10"),
                             ("Keyboard shortcuts", "<Control>question"), ("Quit", "<Control>q")):
            section.add(Adw.ShortcutsItem(title=title, accelerator=accel))
        dialog.add(section)
        dialog.present(self)

    def show_about(self, *_):
        about = Adw.AboutDialog(
            application_name=APP_NAME, application_icon=APP_ID, version=VERSION, developer_name=DEVELOPER,
            copyright=COPYRIGHT, comments=TAGLINE + " It reads your public RuneMetrics profile and suggests "
            "what to do next: quests in the wiki's optimal order, achievements to work on, and skills to train.")
        about.add_acknowledgement_section("Data", ["RuneScape Wiki https://runescape.wiki",
                                                   "RuneMetrics by Jagex https://apps.runescape.com/runemetrics"])
        about.add_legal_section("RuneScape Wiki", None, Gtk.License.CUSTOM,
                                "Requirement lists, descriptions, tips and the quest order come from the RuneScape "
                                "Wiki and are used under the Creative Commons Attribution-NonCommercial-ShareAlike "
                                "3.0 licence.")
        about.add_legal_section("RuneScape", None, Gtk.License.CUSTOM,
                                "RuneScape and RuneMetrics are trademarks of Jagex Ltd. " + APP_NAME + " is an "
                                "unofficial fan tool and is not affiliated with or endorsed by Jagex.")
        about.present(self)


def self_test(app, win):
    """Show both sample players (no network) and open every cape's guide; print ✓/✗ per check."""
    def check(ok, what):
        print(f"  {'✓' if ok else '✗'} {what}", flush=True)
        if not ok:
            app.failures.append(what)

    try:
        check(all(cape_texture(k) for k in rs3comp.CAPES), "Cape icons draw (SVG support is present)")
        check(Gtk.IconTheme.get_for_display(win.get_display()).has_icon(APP_ID), "App icon found")
        for who in ("beginner", "maxed"):
            profile = json.loads((rs3comp.HERE / "fixtures" / f"{who}.profile.json").read_text())
            quests = json.loads((rs3comp.HERE / "fixtures" / f"{who}.quests.json").read_text())["quests"]
            win.show(who, profile, quests)
            for key, cape in rs3comp.CAPES.items():
                win.cape_list.select_row(win.cape_rows[key])
                check(win.cape == key and isinstance(win.toasts.get_child(), Adw.PreferencesPage)
                      and win.content.get_title() == cape["title"], f"{profile['name']}: {cape['title']} guide")
        win.search.set_text("museum")
        check(any(r.get_visible() for r, *_ in win.search_items), "Search finds matches")
    except Exception as e:  # a crash is a failure too, and must not leave the app running
        check(False, f"crashed: {e!r}")
    print("\nself-test passed" if not app.failures else f"\nself-test FAILED: {len(app.failures)} problem(s)")
    app.quit()


class App(Adw.Application):
    def __init__(self, test=False):
        super().__init__(application_id=APP_ID)
        self.test, self.failures = test, []

    def do_startup(self):
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(ICON_DIR))  # Windows, or not installed
        Gtk.Window.set_default_icon_name(APP_ID)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        for action, accels in (("app.quit", ["<Control>q"]), ("win.refresh", ["<Control>r", "F5"]),
                               ("win.focus-name", ["<Control>l"]), ("win.shortcuts", ["<Control>question"]),
                               ("win.search", ["<Control>f"])):
            self.set_accels_for_action(action, accels)

    def do_activate(self):
        win = self.get_active_window() or Window(self)
        win.present()
        if self.test:
            GLib.idle_add(self_test, self, win)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # Saved names, ticks and settings go to a throwaway folder, never the user's own
        tmp = Path(tempfile.mkdtemp())
        rs3comp.PROGRESS = tmp / "progress.json"
        LAST_NAME, DARK_MODE, CAPE_FILE = (tmp / n for n in ("last-name", "dark-mode", "cape"))
        app = App(test=True)
        app.set_application_id(APP_ID + ".SelfTest")  # don't signal a copy that's already open
        app.run([sys.argv[0]])
        sys.exit(1 if app.failures else 0)
    sys.exit(App().run(sys.argv))
