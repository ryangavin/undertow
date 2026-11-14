import json
import os
import tempfile
import unittest

import pinned

NOW = 1_800_000_000.0


def entry(pid, minutes_ago, **over):
    e = {"pid": pid, "start": 1000, "tid": pid, "since": (NOW - minutes_ago * 60) * 1000, "orphaned": False,
         "owner": {"terminal": "t1kb"}, "probable": None}
    e.update(over)
    return e


class PinnedList(unittest.TestCase):
    def write(self, data):
        folder = tempfile.mkdtemp()
        self.addCleanup(lambda: (os.remove(os.path.join(folder, "pinned.json")), os.rmdir(folder)))
        with open(os.path.join(folder, "pinned.json"), "w") as f:
            json.dump(data, f)
        return os.path.join(folder, "pinned.json")

    def test_a_pinned_process_in_the_list_is_marked_with_how_long(self):
        found = pinned.read(self.write({"at": NOW * 1000 - 5000, "pinned": [entry(500, 7)]}), now=NOW)
        rows = pinned.mark([{"pid": 500}, {"pid": 501}], found, now=NOW, start=lambda pid: 1000)
        self.assertEqual(rows[0]["badge"]["text"], "pinned 7m")
        self.assertNotIn("badge", rows[1])

    def test_a_pinned_orphan_is_marked_as_orphaned(self):
        found = pinned.read(self.write({"at": NOW * 1000, "pinned": [entry(500, 7, orphaned=True, owner=None)]}), now=NOW)
        rows = pinned.mark([{"pid": 500}], found, now=NOW, start=lambda pid: 1000)
        self.assertEqual(rows[0]["badge"]["text"], "orphan · pinned 7m")

    def test_nothing_is_marked_when_the_list_is_stale_or_missing(self):
        self.assertEqual(pinned.read(self.write({"at": NOW * 1000 - 61000, "pinned": [entry(500, 7)]}), now=NOW), {})
        self.assertEqual(pinned.read("/nonexistent/pinned.json", now=NOW), {})
        self.assertEqual(pinned.read(self.write({"nope": 1}), now=NOW), {})

    def test_a_reused_pid_is_not_marked(self):
        found = {500: entry(500, 7)}
        rows = pinned.mark([{"pid": 500}], found, now=NOW, start=lambda pid: 2000)
        self.assertNotIn("badge", rows[0])

    def test_an_agent_with_a_pinned_job_gets_the_chip_with_the_longest_time(self):
        found = {500: entry(500, 12), 501: entry(501, 3)}
        agents = pinned.chips([{"terminal": "t1kb"}, {"terminal": "t1jw"}], found, now=NOW)
        self.assertEqual(agents[0]["pinned"], "12m")
        self.assertNotIn("pinned", agents[1])

    def test_the_probable_owner_of_an_orphan_gets_the_chip(self):
        found = {500: entry(500, 75, orphaned=True, owner=None, probable={"terminal": "t1jw"})}
        agents = pinned.chips([{"terminal": "t1jw"}, {"terminal": ""}], found, now=NOW)
        self.assertEqual(agents[0]["pinned"], "1h15m")
        self.assertNotIn("pinned", agents[1])


if __name__ == "__main__":
    unittest.main()
