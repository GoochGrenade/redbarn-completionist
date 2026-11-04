# Redbarn Completionist

Step-by-step guides to every RuneScape 3 quest, max and completionist cape. Enter your RuneScape name, pick the cape you're working on, and it shows what to do next, based on your own stats and quests.

**8 capes:** Quest Cape, Max cape, Master quest cape, Completionist cape, Completionist cape (t), Master max cape, Master completionist cape and Master completionist cape (t).

**How it keeps you efficient:**
- **Quests** come in the RuneScape Wiki's optimal order, so each quest's rewards help with the next and you train as little as possible.
- **Achievements** show only what you can do right now. Time-limited ones come first, so they progress in the background while you do everything else.
- **Skills** that unlock achievements come first.
- Bigger capes include the smaller ones, and ticking an achievement counts towards every cape that needs it.

**Step-by-step guides:** open any quest, achievement, skill or cape for a guide inside the app, taken from the RuneScape Wiki. It lists what you need first, marked ✓ or ✗ against your own levels and quests, then the steps to tick off as you go, with the current one highlighted. Quests use the wiki's quick guides, including which dialogue options to pick. Training guides open at the section for your level. The guides need an internet connection the first time; after that they're saved for a week. They can't see inside the game, so you tick steps yourself. Where the wiki's own page is thin, the app has its own written guides instead (11 so far, starting with the Completionist cape achievements to start early); each lists its sources, and you can still switch to the wiki page.

It also shows your progress on every cape, highlights the one you're closest to, and tells you where to claim each cape and what it costs. You can search everything, and tick off a whole category at once.

**Before you start:** your RuneMetrics profile must be public. In game, go to **Settings > Gameplay > Hiscores/RuneMetrics**. RuneScape doesn't share achievements with other apps, so you tick those off yourself as you finish them.

## Linux

Needs Python 3.9 or newer, GTK 4 and libadwaita 1.5 or newer. Colours look best with libadwaita 1.6 or newer (Fedora 41+, Ubuntu 25.04+).

1. Install what it needs:
   - Fedora: `sudo dnf install python3-gobject gtk4 libadwaita`
   - Ubuntu/Debian: `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`
2. Download this repository (**Code > Download ZIP**) and unzip it somewhere you'll keep it.
3. In a terminal, in the unzipped folder, run:
   ```
   python3 rs3comp_gui.py --install
   ```
   This adds Redbarn Completionist to your app menu. It runs from that folder, so don't move or delete it.

To remove it from your app menu, run `python3 rs3comp_gui.py --uninstall`.

### In a terminal

`rs3comp.py` prints the same guide without a window:

```
python3 rs3comp.py "Your Name" --cape comp
python3 rs3comp.py "Your Name" --done "Kudos to You"
```

`--cape` can be `quest`, `max`, `mqc`, `comp`, `comp_t`, `master_max`, `master_comp` or `master_comp_t`. Add `--all` to see every step.

## Windows

**[Download Redbarn Completionist for Windows](https://github.com/GoochGrenade/redbarn-completionist/releases/download/v1.1.0/Redbarn-Completionist-Windows.zip)** (48 MB)

1. Unzip the download.
2. Open **Redbarn Completionist.exe** in the unzipped folder. If Windows warns that it's from an unknown publisher, click **More info**, then **Run anyway**.

If something's wrong, run `"Redbarn Completionist.exe" --self-test` in a terminal in the unzipped folder. It builds every guide from sample data, without going online.

## Keeping up with game updates

When Jagex adds quests or changes a cape's requirements, choose **Update Requirements** from the app's menu. It downloads the latest lists from the RuneScape Wiki.

## Licence

Redbarn Completionist is free software, released under the GNU General Public License version 3 or later. See [LICENSE](LICENSE).

The written guides in `guides.json` are original text based on the sources listed with each guide, shared under the same CC BY-NC-SA 3.0 licence. The requirement lists, descriptions, tips and quest order in `requirements.json` come from the [RuneScape Wiki](https://runescape.wiki) and are used under [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/). You may share them, with credit, but not sell them.

RuneScape and RuneMetrics are trademarks of Jagex Ltd. Redbarn Completionist is an unofficial fan tool and is not affiliated with or endorsed by Jagex.

© 2026 Redbarn Christian Co.
