"""The coding agents running on this machine, and as much as can be found out about what each is doing.

Agents in Herdr terminals come from herdr-core (`hc ls`, `hc get`): their
status, the step they are on, the session title, the change they are working
on (the flow.change label), the space and tab they sit in, the model and how
full its context is. Agent programs running anywhere else are found by their
process, with less to say. Git says which project and worktree an agent works
in; the Previews mod's script says which preview servers run, and an agent has
one when a server runs from the folder it works in. Everything an agent started
counts towards its CPU and memory. No third-party dependencies.
"""
import glob
import json
import os
import subprocess
import threading
import time

# Herdr's names for agent harnesses, and the programs that are agents.
HARNESSES = {"claude-code": "claude", "claude": "claude", "opencode": "opencode", "codex": "codex", "pi": "pi"}
PROGRAMS = {"claude": "claude", "codex": "codex", "opencode": "opencode", "opencode.exe": "opencode", "pi": "pi"}
PROJECTS = os.path.expanduser("~/Projects")
WORKTREES = os.path.join(PROJECTS, ".worktrees")
PREVIEWS = os.path.join(PROJECTS, "satoramoto/zen-flow/herdr/scripts/previews.mjs")


def run_json(argv, timeout=3):
    """A command's JSON output, or None when it is missing, fails or says nothing useful."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def terminal(record):
    """What one `hc get` record says about the agent in it."""
    labels = record.get("labels") or {}
    status = record.get("status") or {}
    foreground = record.get("foreground") or {}
    chat = {}
    try:
        chat = json.loads(((record.get("records") or {}).get("unified-chat") or {}).get("msg") or "{}")
    except ValueError:
        pass
    context = chat.get("percent")
    if context is None and chat.get("used") and chat.get("window"):
        context = round(100 * chat["used"] / chat["window"])
    change = labels.get("flow.change") or ""
    return {
        "terminal": record.get("address") or "",
        "pid": foreground.get("pid"),
        "cwd": foreground.get("cwd") or record.get("cwd") or "",
        "status": status.get("state") or "",
        "step": status.get("msg") or "",
        # OpenCode puts its own mark in front of the session title.
        "title": (record.get("title") or "").removeprefix("OC | "),
        "where": labels.get("where") or "",
        "change": change,
        "model": chat.get("model") or "",
        "context": context,
    }


def change_parts(change):
    """A flow.change label as (repository folder or store name, change name)."""
    place, _, name = change.rpartition("#")
    return place.removeprefix("store:"), name


def git_place(folder, run=subprocess.run):
    """The repository a folder is in: (main checkout, the checkout the folder is in, branch), or None."""
    try:
        done = run(["git", "-C", folder, "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir",
                    "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = done.stdout.split("\n")
    if done.returncode != 0 or len(lines) < 3:
        return None
    top, common, branch = lines[0], lines[1], lines[2]
    main = os.path.dirname(common) if os.path.basename(common) == ".git" else top
    return main, top, branch


def short(folder):
    """A folder as it reads under ~/Projects, or with ~ for home."""
    if folder == PROJECTS or folder.startswith(PROJECTS + "/"):
        return folder[len(PROJECTS) + 1:] or "Projects"
    home = os.path.expanduser("~")
    return "~" + folder[len(home):] if folder.startswith(home) else folder


def descendants(pid, children):
    """Every process below `pid`, nearest first."""
    found, queue = [], list(children.get(pid, []))
    while queue:
        child = queue.pop(0)
        found.append(child)
        queue.extend(children.get(child, []))
    return found


def servers(report):
    """The running preview servers in a previews.mjs --json report, as {dir, url, kind}."""
    found = []

    def visit(project):
        for kind_ in ("running", "extras"):
            for server in project.get(kind_) or []:
                host = server.get("host") or "localhost"
                host = "localhost" if host in ("0.0.0.0", "127.0.0.1", "::") else host
                found.append({"dir": server.get("cwd") or project.get("dir") or "", "kind": server.get("kind") or "",
                              "url": f"http://{host}:{server.get('port')}/"})
        for worktree in project.get("worktrees") or []:
            visit(worktree)
    for project in (report or {}).get("projects") or []:
        visit(project)
    for stray in (report or {}).get("strays") or []:
        visit({"running": [stray]})
    return found


def previews_for(folder, running):
    """The preview servers running from `folder` or below it, each URL once."""
    if not folder:
        return []
    found, seen = [], set()
    for server in running:
        place = server["dir"].rstrip("/")
        if (place == folder or place.startswith(folder + "/")) and server["url"] not in seen:
            seen.add(server["url"])
            found.append({"url": server["url"], "kind": server["kind"]})
    return found


class Agents:
    """Keeps the agent list current. Call refresh() with the latest process rows."""

    # Previews change seldom, and asking costs a Node start (about a third of
    # a second of CPU): every two minutes is often enough.
    def __init__(self, hc="hc", previews_every=120, places_every=60, cwd=None, git=git_place):
        self.hc = hc
        self.previews_every = previews_every
        self.places_every = places_every
        self.cwd = cwd or (lambda pid: os.readlink(f"/proc/{pid}/cwd"))
        self.git = git
        self.places = {}  # folder -> (looked at, git_place result)
        self.running = []
        self.previews_at = None
        self.records = {}  # terminal -> (fetched at, status, turn, hc get record)
        self.lock = threading.Lock()

    def place(self, folder, now):
        known = self.places.get(folder)
        if known is None or now - known[0] > self.places_every:
            known = (now, self.git(folder))
            self.places[folder] = known
        return known[1]

    def refresh_previews(self):
        report = run_json(["node", PREVIEWS, "--json"], timeout=20) if os.path.exists(PREVIEWS) else None
        with self.lock:
            self.running = servers(report)

    def herdr(self, now):
        """(harness, hc get record) for each agent terminal. A working agent's record is fetched every time;
        others only when their status or turn moves, or every ten seconds."""
        listing = run_json([self.hc, "ls", "--json"])
        records, kept = [], {}
        for item in (listing or {}).get("terminals") or []:
            harness = HARNESSES.get(item.get("agent"))
            if not harness:
                continue
            address, status, turn = item["address"], item.get("status"), item.get("turn")
            known = self.records.get(address)
            if (known is None or status in ("working", "blocked") or (status, turn) != known[1:3]
                    or now - known[0] > 10):
                record = run_json([self.hc, "get", address, "--json"])
                known = (now, status, turn, record) if record else None
            if known:
                kept[address] = known
                records.append((harness, known[3]))
        self.records = kept
        return records

    def refresh(self, procs, now=None, herdr=None):
        """The agent rows for the processes in `procs` (process_rows() output)."""
        now = time.monotonic() if now is None else now
        if self.previews_at is None or now - self.previews_at > self.previews_every:
            self.previews_at = now
            threading.Thread(target=self.refresh_previews, daemon=True).start()
        by_pid = {row["pid"]: row for row in procs}
        children = {}
        for row in procs:
            children.setdefault(row["parent"], []).append(row["pid"])
        agents = []
        for harness, record in (self.herdr(now) if herdr is None else herdr):
            agent = terminal(record)
            if agent["pid"] in by_pid:
                agent["kind"] = harness
                agents.append(agent)
        # Agent programs nobody's terminal claims: the topmost of each kind.
        claimed = set()
        for agent in agents:
            claimed.add(agent["pid"])
            claimed.update(descendants(agent["pid"], children))
        for row in procs:
            sort = PROGRAMS.get(row["program"])
            if not sort or row["pid"] in claimed or row["kind"] != "user":
                continue
            if PROGRAMS.get(by_pid.get(row["parent"], {}).get("program")) == sort:
                continue
            claimed.add(row["pid"])
            claimed.update(descendants(row["pid"], children))
            try:
                folder = self.cwd(row["pid"])
            except OSError:
                folder = ""
            agents.append({"terminal": "", "pid": row["pid"], "cwd": folder, "status": "", "step": "", "title": "",
                           "where": "", "change": "", "model": "", "context": None, "kind": sort})
        with self.lock:
            running = list(self.running)
        return [self.describe(agent, by_pid, children, running, now) for agent in agents]

    def describe(self, agent, by_pid, children, running, now):
        below = descendants(agent["pid"], children)
        rows = [by_pid[agent["pid"]]] + [by_pid[pid] for pid in below]
        agent.update({
            "count": len(rows),
            "cpu": round(sum(row["cpu"] or 0 for row in rows), 2),
            "mem": sum(row["mem"] for row in rows),
            "gpu": round(min(100.0, sum(row["gpu"] for row in rows)), 2),
            "gmem": sum(row["gmem"] for row in rows),
            "name": by_pid[agent["pid"]]["name"],
            "program": by_pid[agent["pid"]]["program"],
        })
        # The busiest thing it started, unless that is its own helper program.
        busiest = max((by_pid[pid] for pid in below if PROGRAMS.get(by_pid[pid]["program"]) != agent["kind"]),
                      key=lambda row: row["cpu"] or 0, default=None)
        agent["running"] = busiest["cmd"] if busiest and (busiest["cpu"] or 0) >= 5 and busiest["cmd"] else ""
        # Where it works: a worktree its commands run in, its change's worktree, or its own folder.
        folders = []
        for pid in below:
            try:
                folders.append(self.cwd(pid))
            except OSError:
                pass
        repo, name = change_parts(agent["change"])
        if name:
            # A change spanning repositories has a worktree in each; its own repository's comes first.
            folders.append(os.path.join(WORKTREES, os.path.basename(repo), name))
            folders.extend(sorted(glob.glob(os.path.join(glob.escape(WORKTREES), "*", glob.escape(name)))))
        folders.append(agent["cwd"])
        work = next((f for f in folders if f.startswith(WORKTREES + "/") and os.path.isdir(f)), agent["cwd"])
        place = self.place(work, now) if work else None
        agent["project"] = short(place[0]) if place else short(agent["cwd"]) if agent["cwd"] else ""
        agent["worktree"] = short(place[1]) if place and place[1] != place[0] else ""
        agent["branch"] = place[2] if place else ""
        # Outside any repository (~/Projects itself, say) no server is its own.
        agent["previews"] = previews_for(place[1], running) if place else []
        agent["changeName"] = name
        return agent
