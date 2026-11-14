import os
import tempfile
import unittest
from pathlib import Path
from sources import Watch, changed, digest, fingerprint, only


def reader(states):
    """A stand-in for the directory: each look returns the next state."""
    return lambda folder: states.pop(0)


class SourceScenarios(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.folder / "shell.qml").write_text("one")
        (self.folder / "metrics.py").write_text("one")

    def test_a_file_rewritten_in_place_is_noticed(self):
        before = fingerprint(self.folder)
        (self.folder / "shell.qml").write_text("longer")
        self.assertEqual(changed(before, fingerprint(self.folder)), {"shell.qml"})

    def test_a_file_replaced_by_a_new_one_of_the_same_size_is_noticed(self):
        before = fingerprint(self.folder)
        (self.folder / "shell.qml.tmp").write_text("two")
        os.utime(self.folder / "shell.qml.tmp", ns=(before["shell.qml"][0], before["shell.qml"][0]))
        os.replace(self.folder / "shell.qml.tmp", self.folder / "shell.qml")
        self.assertEqual(changed(before, fingerprint(self.folder)), {"shell.qml"})

    def test_new_and_deleted_sources_are_noticed(self):
        before = fingerprint(self.folder)
        (self.folder / "Extra.qml").write_text("new")
        (self.folder / "metrics.py").unlink()
        self.assertEqual(changed(before, fingerprint(self.folder)), {"Extra.qml", "metrics.py"})

    def test_tests_and_other_files_are_not_sources(self):
        (self.folder / "test_metrics.py").write_text("test")
        (self.folder / "README.md").write_text("words")
        (self.folder / "shell.qml.tmp").write_text("scratch")
        self.assertEqual(set(fingerprint(self.folder)), {"shell.qml", "metrics.py"})

    def test_nothing_is_reported_when_nothing_changes(self):
        watch = Watch(self.folder)
        self.assertEqual(watch.poll(), (None, False))
        self.assertEqual(watch.poll(), (None, False))

    def test_saved_qml_asks_for_a_reload_once_the_files_hold_still(self):
        start, half, done = {"a.qml": 1, "b.qml": 1}, {"a.qml": 2, "b.qml": 1}, {"a.qml": 2, "b.qml": 2}
        watch = Watch("unused", read=reader([start, half, done, done, done]))
        self.assertEqual(watch.poll(), (None, False))             # a.qml just changed: wait
        self.assertEqual(watch.poll(), (None, False))             # b.qml followed: still moving
        self.assertEqual(watch.poll(), (digest(done), False))     # still for a look: both at once
        self.assertEqual(watch.poll(), (None, False))             # and only once
        self.assertEqual(watch.qml_changes(), ["a.qml", "b.qml"])

    def test_saved_javascript_reloads_the_app_like_qml(self):
        (self.folder / "Icons.js").write_text("one")
        start = fingerprint(self.folder)
        (self.folder / "Icons.js").write_text("longer")
        done = fingerprint(self.folder)
        watch = Watch("unused", read=reader([start, done, done]))
        self.assertEqual(watch.poll(), (None, False))
        self.assertEqual(watch.poll(), (digest(only(done, (".qml", ".js", ".qsb"))), False))
        self.assertEqual(watch.qml_changes(), ["Icons.js"])

    def test_a_rebuilt_shader_reloads_the_app(self):
        (self.folder / "waves.frag.qsb").write_bytes(b"one")
        start = fingerprint(self.folder)
        (self.folder / "waves.frag.qsb").write_bytes(b"longer")
        done = fingerprint(self.folder)
        watch = Watch("unused", read=reader([start, done, done]))
        self.assertEqual(watch.poll(), (None, False))
        self.assertEqual(watch.poll()[1], False)
        self.assertEqual(watch.qml_changes(), ["waves.frag.qsb"])

    def test_saved_python_says_so_without_asking_for_a_reload(self):
        start, done = {"a.qml": 1, "m.py": 1}, {"a.qml": 1, "m.py": 2}
        watch = Watch("unused", read=reader([start, done, done]))
        self.assertEqual(watch.poll(), (None, False))
        self.assertEqual(watch.poll(), (None, True))

    def test_qml_saved_while_the_app_was_loading_is_caught_by_the_next_collector(self):
        # The collector before us asked for a reload at `asked`. The app loaded,
        # a.qml was saved again meanwhile, and only then did we start.
        asked, later = {"a.qml": 2}, {"a.qml": 3}
        watch = Watch("unused", loaded_qml=digest(asked), read=reader([later, later]))
        self.assertEqual(watch.poll(), (digest(later), False))

    def test_a_handed_over_digest_that_still_matches_asks_for_nothing(self):
        asked = {"a.qml": 2}
        watch = Watch("unused", loaded_qml=digest(asked), read=reader([asked, asked, asked]))
        self.assertEqual(watch.poll(), (None, False))
        self.assertEqual(watch.poll(), (None, False))

    def test_python_saved_while_this_collector_was_starting_is_caught(self):
        # `loaded` was taken before our modules were read; m.py changed just after.
        loaded, later = {"m.py": 1}, {"m.py": 2}
        watch = Watch("unused", loaded=loaded, read=reader([later, later]))
        self.assertEqual(watch.poll(), (None, False))             # first look differs from `loaded`: wait
        self.assertEqual(watch.poll(), (None, True))

    def test_a_failed_reload_is_not_asked_for_every_second(self):
        start, broken = {"a.qml": 1}, {"a.qml": 2}
        watch = Watch("unused", read=reader([start, broken, broken, broken, broken]))
        watch.poll(), watch.poll()
        self.assertEqual(watch.poll(), (None, False))
        self.assertEqual(watch.poll(), (None, False))

    def test_only_keeps_one_kind_of_source(self):
        self.assertEqual(only({"a.qml": 1, "m.py": 2}, ".py"), {"m.py": 2})


if __name__ == "__main__":
    unittest.main()
