import json
import tempfile
import unittest
from pathlib import Path
from history import Store


def sample(when, **more):
    return json.dumps({"time": when, **more})


class HistoryScenarios(unittest.TestCase):
    def setUp(self):
        self.path = Path(self.enterContext(tempfile.TemporaryDirectory())) / "undertow" / "history.jsonl"

    def store(self, path=None, **options):
        opened = Store(path or self.path, **options)
        self.addCleanup(opened.close)
        return opened

    def test_a_new_collector_finds_what_the_last_one_saved(self):
        first = self.store()
        first.append(sample(1000, cpu=5), now=1000)
        first.append(sample(1001, cpu=6), now=1001)
        self.assertEqual(self.store().recent(now=1002), [sample(1000, cpu=5), sample(1001, cpu=6)])

    def test_samples_older_than_the_hour_are_left_behind(self):
        store = self.store(keep=3600)
        store.append(sample(1000), now=1000)
        store.append(sample(4000), now=4000)
        self.assertEqual(store.recent(now=4700), [sample(4000)])

    def test_samples_from_the_future_are_ignored_after_a_clock_change(self):
        store = self.store()
        store.append(sample(9000), now=9000)
        self.assertEqual(store.recent(now=5000), [])

    def test_the_file_is_trimmed_so_it_stays_about_an_hour_long(self):
        store = self.store(keep=10, trim_every=5)
        for second in range(100):
            store.append(sample(second), now=second)
        stored = self.path.read_text().splitlines()
        self.assertLessEqual(len(stored), 10 + 1 + 5)
        self.assertEqual(json.loads(stored[-1])["time"], 99)
        self.assertEqual(len(store.recent(now=99)), 11)

    def test_a_line_cut_short_is_skipped_not_fatal(self):
        store = self.store()
        store.append(sample(1000), now=1000)
        with open(self.path, "a") as damaged:
            damaged.write('{"time": 1001, "cp')
        self.assertEqual(self.store().recent(now=1002), [sample(1000)])

    def test_no_file_yet_means_no_history(self):
        self.assertEqual(self.store().recent(now=1000), [])

    def test_a_place_that_cannot_be_written_does_not_stop_the_collector(self):
        blocker = self.path.parent.parent / "blocker"
        blocker.write_text("a file where a directory is needed")
        store = self.store(blocker / "undertow" / "history.jsonl")
        store.append(sample(1000), now=1000)
        self.assertEqual(store.recent(now=1000), [])


if __name__ == "__main__":
    unittest.main()
