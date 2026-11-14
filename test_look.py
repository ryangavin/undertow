import tempfile
import unittest
from pathlib import Path

from look import look


class LookScenarios(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.toggles, self.hypr, self.omarchy = root / "toggles", root / "hypr", root / "omarchy"
        for folder in (self.toggles, self.hypr, self.omarchy / "default" / "hypr"):
            folder.mkdir(parents=True)
        (self.omarchy / "default" / "hypr" / "helpers.lua").write_text(
            'function o.transparent_window(match, opacity)\n  o.window(match, { opacity = opacity or "0.985 0.96", tag = "+transparent-window" })\nend\n')

    def current(self):
        return look(self.toggles, self.hypr, self.omarchy)

    def test_by_default_panels_match_omarchys_unfocused_see_through_windows(self):
        self.assertEqual(self.current(), {"mode": "transparent", "alpha": 0.96})

    def test_the_users_own_rule_for_the_tag_wins(self):
        (self.hypr / "looknfeel.lua").write_text('o.window({ tag = "transparent-window" }, { opacity = "0.94 0.90" })\n')
        self.assertEqual(self.current(), {"mode": "transparent", "alpha": 0.9})

    def test_an_example_in_a_comment_is_not_a_rule(self):
        (self.hypr / "looknfeel.lua").write_text('-- o.window({ tag = "transparent-window" }, { opacity = "0.5 0.5" })\n')
        self.assertEqual(self.current()["alpha"], 0.96)

    def test_opaque_windows_make_solid_panels(self):
        (self.hypr / "looknfeel.lua").write_text('o.window({ tag = "transparent-window" }, { opacity = "0.94 0.90" })\n')
        (self.toggles / "window-opaque.lua").write_text("")
        self.assertEqual(self.current(), {"mode": "opaque", "alpha": 1.0})

    def test_glassy_windows_make_panels_at_least_as_see_through_as_glass(self):
        (self.toggles / "window-glassy.lua").write_text("")
        self.assertEqual(self.current(), {"mode": "glassy", "alpha": 0.8})

    def test_backup_files_are_not_read(self):
        (self.hypr / "looknfeel.lua.bak.1").write_text('o.window({ tag = "transparent-window" }, { opacity = "0.5 0.5" })\n')
        self.assertEqual(self.current()["alpha"], 0.96)


if __name__ == "__main__":
    unittest.main()
