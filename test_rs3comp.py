import json
import unittest
from pathlib import Path

import rs3comp
import wikiguide

HERE = Path(__file__).resolve().parent
REQS = json.loads((HERE / "requirements.json").read_text(encoding="utf-8"))


def load(name):
    profile = json.loads((HERE / "fixtures" / f"{name}.profile.json").read_text(encoding="utf-8"))
    return profile, json.loads((HERE / "fixtures" / f"{name}.quests.json").read_text(encoding="utf-8"))["quests"]


def player(name, done=(), cape="comp"):
    return rs3comp.guide(*load(name), REQS, set(done), cape)


class Guide(unittest.TestCase):
    def test_xp_table(self):
        self.assertEqual([rs3comp.xp_for(l) for l in (1, 2, 99, 110, 120)], [0, 83, 13_034_431, 38_737_661, 104_273_167])
        self.assertEqual(rs3comp.xp_for(120, elite=True), 80_618_654)
        self.assertEqual(rs3comp.xp_for(99, elite=True), 36_073_511)

    def test_beginner(self):
        g = player("beginner")
        self.assertTrue(g["quests"])
        self.assertTrue(all(q["userEligible"] and q["status"] != "COMPLETED" for q in g["quests"]))
        self.assertEqual(g["summary"]["skills"], (0, 29))
        keys = [(not s["blocks"], s["xp_left"]) for s in g["skills"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(g["summary"]["checklist"], (0, 100))
        self.assertTrue(0 < g["overall"] < 0.05)  # a few quests and levels
        self.assertEqual(g["xp_left"], sum(s["xp_left"] for s in g["skills"]))
        ranks = [rs3comp.CONSIDER.get(a["consider"], (1,))[0] for a in g["items"]]
        self.assertEqual(ranks, sorted(ranks))  # start-early first, long grinds last
        self.assertEqual(g["items"][0]["consider"], "Time gated")
        # a level-1 player can't do a 90 Mining achievement
        self.assertIn("Everything Is Oresome", [a["name"] for a, _ in g["items_locked"]])

    def test_maxed_player_and_ticks(self):
        g = player("maxed")
        self.assertEqual([s["skill"] for s in g["skills"]], ["Necromancy"])  # 200m in every older skill
        self.assertNotIn("My Last Resort", [a["name"] for a, _ in g["items_locked"]])  # combat 152 >= 60
        self.assertTrue(0.5 < g["overall"] < 1)
        name = g["items"][0]["name"]
        g2 = player("maxed", done=[name])
        self.assertNotIn(name, [a["name"] for a in g2["items"]])
        self.assertEqual(g2["summary"]["checklist"][0], g["summary"]["checklist"][0] + 1)
        self.assertEqual(rs3comp.render("Maxed", g, 5, "test").count("\n - "), 5 + 5 + 1)  # quests + items capped, plus Necromancy


class Capes(unittest.TestCase):
    def test_every_cape_for_a_beginner(self):
        for cape in rs3comp.CAPES:
            self.assertTrue(0 < player("beginner", cape=cape)["overall"] < 0.05, cape)

    def test_skills_use_xp_not_level(self):
        self.assertEqual(player("maxed", cape="max")["overall"], 1)  # Necromancy 100 clears 99
        g = player("maxed", cape="master_max")
        # Defence reports level 99 at 200m XP; only Necromancy is short of 120
        self.assertEqual([s["skill"] for s in g["skills"]], ["Necromancy"])
        self.assertEqual(set(g["summary"]), {"skills"})

    def test_nesting(self):
        _, q, comp, _ = rs3comp.resolve("comp", REQS)
        _, _, mqc, _ = rs3comp.resolve("mqc", REQS)
        targets, quests, trimmed, includes = rs3comp.resolve("comp_t", REQS)
        self.assertTrue(q and quests and comp | mqc <= trimmed and not trimmed & rs3comp.META)
        self.assertEqual(includes, ["comp", "mqc"])
        self.assertEqual(targets["Hunter"], 110)  # from Master Skiller via comp
        master, _, _, _ = rs3comp.resolve("master_comp_t", REQS)
        self.assertEqual(set(master.values()), {120})  # master max raises every skill to 120
        self.assertEqual(rs3comp.resolve("quest", REQS)[1:3], (True, set()))

    def test_quests_follow_optimal_guide(self):
        g = player("beginner", cape="quest")
        orders = [q.get("order", 10_000) for q in g["quests"]]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(g["quests"][0]["title"], "The Blood Pact")

    def test_progress_all(self):
        overall, closest = rs3comp.progress_all(*load("maxed"), REQS, set())
        self.assertEqual(list(overall), list(rs3comp.CAPES))
        self.assertEqual(closest, "master_max")  # max is done; master max needs only Necromancy


class WikiGuide(unittest.TestCase):
    def page(self, name, own=""):
        return wikiguide.parse((HERE / "fixtures" / "wiki" / f"{name}.html").read_text(encoding="utf-8"), own)

    def test_quest_quick_guide(self):
        g = self.page("cooks_assistant_quick_guide", "Cook's Assistant")
        details = dict(g["details"])
        self.assertIn("Lumbridge Castle", details["Start point"])
        self.assertEqual(details["Requirements"], "None")  # its own name and "None" filler are dropped
        self.assertIn("• Bucket", details["Required items"])
        steps = [(d, t) for s in g["sections"] if s["title"] == "Walkthrough" for k, d, t in s["blocks"] if k == "step"]
        self.assertTrue(steps[0][1].startswith("Obtain the following items"))
        self.assertIn(2, [d for d, _ in steps])  # nested sub-steps keep their depth
        self.assertTrue(any("(Chat: What's Wrong? → [Accept Quest] → Can I help?)" in t for _, t in steps))
        text = json.dumps(g)
        self.assertNotIn("Show on map", text)  # page furniture is skipped
        self.assertNotIn("League", text)

    def test_achievement(self):
        g = self.page("kudos_to_you")
        details = dict(g["details"])
        self.assertEqual(details["Description"], "Reach full Kudos with the Varrock Museum.")
        self.assertIn("• Demon Slayer", details["Requirements"].splitlines())
        self.assertNotIn("Update history", [s["title"] for s in g["sections"]])

    def test_training_guide(self):
        g = self.page("ranged_training")
        titles = [s["title"] for s in g["sections"]]
        pick = lambda level: titles[wikiguide.level_section(g["sections"], level)]  # noqa: E731
        self.assertEqual([pick(1), pick(20), pick(45), pick(99), pick(120)],
                         ["Levels 1-20", "Levels 20-40", "Levels 40-50", "Levels 70-120", "Levels 70-120"])
        rows = [t for s in g["sections"] for k, _, t in s["blocks"] if k == "row"]
        self.assertTrue(any("30 Defence, Broken Home" in t for t in rows))  # skill icon alt text kept
        self.assertEqual(wikiguide.level_range("Level 20+"), (20, None))
        self.assertEqual(wikiguide.level_range("Level 1–46+"), (1, 46))
        self.assertIsNone(wikiguide.level_range("Rings"))

    def test_training_page_names(self):
        self.assertEqual(wikiguide.training_page("Defence"), "Pay-to-play melee training")
        self.assertEqual(wikiguide.training_page("Mining"), "Pay-to-play Mining training")


class WrittenGuides(unittest.TestCase):
    def test_guides_are_complete(self):
        guides = json.loads((HERE / "guides.json").read_text(encoding="utf-8"))["guides"]
        self.assertTrue(guides)
        for name, g in guides.items():
            with self.subTest(name):
                self.assertIn(name, REQS["achievements"])  # keyed by the same name the app uses
                self.assertTrue(g["summary"] and g["steps"] and g["checked"])
                for step, subs in g["steps"]:
                    self.assertTrue(step and isinstance(subs, list))
                self.assertTrue(g["sources"] and all(url.startswith("https://") for _, url in g["sources"]))


if __name__ == "__main__":
    unittest.main()
