import json
import unittest
from pathlib import Path

import rs3comp

HERE = Path(__file__).resolve().parent
REQS = json.loads((HERE / "requirements.json").read_text())


def load(name):
    profile = json.loads((HERE / "fixtures" / f"{name}.profile.json").read_text())
    return profile, json.loads((HERE / "fixtures" / f"{name}.quests.json").read_text())["quests"]


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


if __name__ == "__main__":
    unittest.main()
