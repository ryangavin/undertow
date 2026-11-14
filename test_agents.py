import json
import os
import tempfile
import unittest
from unittest import mock

import agents
from agents import Agents, change_parts, previews_for, servers, short, terminal


def proc(pid, parent, name, cpu=0.0, mem=0, program=None, cmd="", kind="user"):
    return {"pid": pid, "parent": parent, "name": name, "program": program or name, "kind": kind, "cpu": cpu, "mem": mem,
            "gpu": 0.0, "gmem": 0, "cmd": cmd}


def record(address, pid, cwd, state="working", msg="", title="", labels=None, chat=None):
    return {"address": address, "foreground": {"pid": pid, "cwd": cwd, "name": "claude"},
            "status": {"state": state, "msg": msg}, "title": title, "labels": labels or {},
            "records": {"unified-chat": {"msg": json.dumps(chat or {})}}}


class AgentScenarios(unittest.TestCase):
    def test_a_herdr_record_gives_the_agents_status_step_change_and_model(self):
        found = terminal(record("t1jw", 1905624, "/p/zen", msg="Fixing two stories", title="Push 3 theme",
                                labels={"where": "zen / 1", "flow.change": "/p/zen#push-3-surface"},
                                chat={"model": "Fable 5.2", "percent": 36}))
        self.assertEqual({key: found[key] for key in ("terminal", "pid", "status", "step", "title", "where", "change", "model", "context")},
                         {"terminal": "t1jw", "pid": 1905624, "status": "working", "step": "Fixing two stories",
                          "title": "Push 3 theme", "where": "zen / 1", "change": "/p/zen#push-3-surface",
                          "model": "Fable 5.2", "context": 36})

    def test_context_is_worked_out_from_tokens_when_the_harness_gives_no_percentage(self):
        found = terminal(record("t1hx", 5, "/p", title="OC | README.md", chat={"used": 86718, "window": 1000000}))
        self.assertEqual((found["context"], found["title"]), (9, "README.md"))

    def test_a_change_label_names_its_repository_or_store_and_the_change(self):
        self.assertEqual(change_parts("/home/r/Projects/satoramoto/zen#push-3-surface"), ("/home/r/Projects/satoramoto/zen", "push-3-surface"))
        self.assertEqual(change_parts("store:zen-flow#headless-shell-only"), ("zen-flow", "headless-shell-only"))
        self.assertEqual(change_parts(""), ("", ""))

    def test_folders_read_as_they_sit_under_projects(self):
        self.assertEqual(short(os.path.join(agents.PROJECTS, "satoramoto/zen")), "satoramoto/zen")
        self.assertEqual(short(agents.PROJECTS), "Projects")

    def test_a_preview_belongs_to_the_folder_it_runs_from_or_below(self):
        report = {"projects": [
            {"dir": "/p/zen-flow/storybook", "running": [{"kind": "storybook", "host": "127.0.0.1", "port": 6030, "cwd": "/p/zen-flow/storybook"}],
             "worktrees": [{"dir": "/w/zen-flow/x", "running": [], "extras": [{"kind": "astro", "host": "0.0.0.0", "port": 4326}]}]},
            {"dir": "/p/zen-flowers", "running": [{"kind": "storybook", "host": "localhost", "port": 6040}]}]}
        running = servers(report)
        self.assertEqual(previews_for("/p/zen-flow", running), [{"url": "http://localhost:6030/", "kind": "storybook"}])
        self.assertEqual(previews_for("/w/zen-flow/x", running), [{"url": "http://localhost:4326/", "kind": "astro"}])
        self.assertEqual(previews_for("", running), [])

    def finder(self, cwds, places):
        def cwd(pid):
            if pid not in cwds:
                raise OSError("no such process")
            return cwds[pid]
        finder = Agents(hc="no-such-hc", cwd=cwd, git=lambda folder: places.get(folder))
        finder.previews_at = 0  # no previews script in a test
        return finder

    def test_an_agent_counts_everything_it_started_and_says_what_it_is_busy_running(self):
        procs = [proc(10, 1, "zsh"), proc(11, 10, "claude", cpu=8, mem=100),
                 proc(12, 11, "zsh", cpu=1, mem=5), proc(13, 12, "node", cpu=150, mem=400, cmd="node vitest run"),
                 proc(14, 11, "claude", cpu=3, mem=50, cmd="claude bg-pty-host")]
        finder = self.finder({12: "/p/zen", 13: "/p/zen", 14: "/p/zen"}, {"/p/zen": ("/p/zen", "/p/zen", "main")})
        found = finder.refresh(procs, now=1, herdr=[("claude", record("t1", 11, "/p/zen"))])
        self.assertEqual([(a["pid"], a["kind"], a["count"], a["cpu"], a["mem"], a["running"], a["branch"]) for a in found],
                         [(11, "claude", 4, 162, 555, "node vitest run", "main")])

    def test_an_agent_working_in_a_worktree_is_shown_there_with_its_preview(self):
        worktree = os.path.join(agents.WORKTREES, "zen", "push-3-surface")
        procs = [proc(11, 1, "claude"), proc(12, 11, "zsh")]
        finder = self.finder({12: worktree}, {worktree: ("/p/zen", worktree, "change/push-3-surface")})
        finder.running = [{"dir": worktree, "url": "http://localhost:6007/", "kind": "storybook"},
                          {"dir": "/p/zen", "url": "http://localhost:6006/", "kind": "storybook"}]
        with mock.patch("os.path.isdir", return_value=True):
            found = finder.refresh(procs, now=1, herdr=[("claude", record("t1", 11, "/p/zen"))])[0]
        self.assertEqual((found["worktree"], found["branch"], found["previews"]),
                         (".worktrees/zen/push-3-surface", "change/push-3-surface", [{"url": "http://localhost:6007/", "kind": "storybook"}]))

    def test_the_changes_worktree_is_found_even_under_another_repository(self):
        with tempfile.TemporaryDirectory() as root:
            worktree = os.path.join(root, "zen", "rewrite-trig")
            os.makedirs(worktree)
            with mock.patch.object(agents, "WORKTREES", root):
                finder = self.finder({}, {worktree: ("/p/zen", worktree, "change/rewrite-trig")})
                found = finder.refresh([proc(11, 1, "opencode.exe", program="opencode.exe")], now=1,
                                       herdr=[("opencode", record("t1", 11, "/p", labels={"flow.change": "/p/zen-flow#rewrite-trig"}))])[0]
        self.assertEqual((found["branch"], found["changeName"]), ("change/rewrite-trig", "rewrite-trig"))

    def test_agent_programs_outside_herdr_are_found_by_their_process_once_each(self):
        procs = [proc(20, 1, "codex"), proc(21, 20, "codex"), proc(30, 1, "claude"), proc(31, 30, "claude"),
                 proc(40, 1, "claude", kind="system")]
        finder = self.finder({20: "/p", 30: "/p/zen"}, {})
        found = finder.refresh(procs, now=1, herdr=[])
        self.assertEqual([(a["pid"], a["kind"], a["count"], a["terminal"]) for a in found], [(20, "codex", 2, ""), (30, "claude", 2, "")])

    def test_a_terminal_whose_agent_has_gone_is_not_listed(self):
        found = self.finder({}, {}).refresh([proc(10, 1, "zsh")], now=1, herdr=[("claude", record("t1", 999, "/p"))])
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
