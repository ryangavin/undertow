"""Pinned threads, as zen-flow's watcher lists them in $XDG_RUNTIME_DIR/zen-flow/pinned.json.

Undertow only shows them: a pinned mark on the process row and a "pinned core" chip on the
agent that owns it. A missing, unreadable or stale list (over a minute old) shows nothing."""
import json
import os
import time

MAX_AGE = 60
TINT = "#e66767"


def path():
    return os.path.join(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}", "zen-flow", "pinned.json")


def start_of(pid):
    """A process's start time (field 22 of its stat), or None when it is gone."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            text = f.read()
        return int(text[text.rindex(")") + 2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def read(file=None, now=None):
    """The pinned entries by pid, or {} when the list is missing, unreadable or stale."""
    now = time.time() if now is None else now
    try:
        with open(file or path()) as f:
            data = json.load(f)
        if now - data["at"] / 1000 > MAX_AGE:
            return {}
        out = {}
        for entry in data.get("pinned") or []:
            had = out.get(entry["pid"])
            if not had or entry["since"] < had["since"]:
                out[entry["pid"]] = entry
        return out
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def minutes(entry, now):
    return max(1, round((now * 1000 - entry["since"]) / 60000))


def held(m):
    return f"{m}m" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def mark(rows, pinned, now=None, start=start_of):
    """Give each process row whose process is pinned a badge saying for how long."""
    now = time.time() if now is None else now
    for row in rows:
        entry = pinned.get(row["pid"])
        if not entry or start(row["pid"]) != entry["start"]:
            continue
        text = f"pinned {held(minutes(entry, now))}"
        row["badge"] = {"text": f"orphan · {text}" if entry.get("orphaned") else text, "color": TINT}
    return rows


def chips(agents, pinned, now=None):
    """Give each agent that owns a pinned process (or probably owns an orphan) the longest time."""
    now = time.time() if now is None else now
    for agent in agents:
        terminal = agent.get("terminal")
        if not terminal:
            continue
        times = [minutes(e, now) for e in pinned.values()
                 if (e.get("owner") or {}).get("terminal") == terminal or (e.get("probable") or {}).get("terminal") == terminal]
        if times:
            agent["pinned"] = held(max(times))
    return agents
