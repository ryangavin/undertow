"""Which apps are running and what each uses, read from /proc. No third-party dependencies."""
import os

PAGE_BYTES = os.sysconf("SC_PAGE_SIZE")
TICKS_PER_SECOND = os.sysconf("SC_CLK_TCK")


def parse_stat(text):
    """One /proc/<pid>/stat as (cpu ticks, start time, resident pages, name, parent pid, threads,
    cpu ticks of the children it has waited for)."""
    # The name sits in parentheses and may itself hold spaces or parentheses.
    opened, closed = text.find("("), text.rfind(")")
    fields = text[closed + 2:].split()
    return (int(fields[11]) + int(fields[12]), int(fields[19]), int(fields[21]), text[opened + 1:closed],
            fields[1], int(fields[17]), int(fields[13]) + int(fields[14]))


def parse_io(text):
    """The bytes a process has read from and written to storage, from its /proc/<pid>/io."""
    values = dict(line.split(": ", 1) for line in text.splitlines())
    return int(values["read_bytes"]) + int(values["write_bytes"])


def scan():
    """Every running process keyed by pid, and the storage bytes of those we may ask about."""
    found, storage = {}, {}
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        try:
            with open(entry.path + "/stat") as stat:
                found[entry.name] = parse_stat(stat.read())
        except (OSError, IndexError, ValueError):
            continue  # it exited while we were looking
        try:
            with open(entry.path + "/io") as io:
                storage[entry.name] = parse_io(io.read())
        except (OSError, KeyError, ValueError):
            pass  # another user's process: the kernel keeps this to its owner
    return found, storage


def programs(found, known):
    """The program each process runs, asking the kernel only about processes new since `known`."""
    result = {}
    for pid, entry in found.items():
        started, name = entry[1], entry[3]
        earlier = known.get(pid)
        if earlier and earlier[0] == started:
            result[pid] = earlier
            continue
        try:
            result[pid] = (started, os.readlink(f"/proc/{pid}/exe"))
        except OSError:
            # Another user's process or a kernel thread: the name is all we may see.
            result[pid] = (started, name)
    return result


def owners(found, running):
    """The app each process belongs to: its topmost ancestor running the same program.

    A browser's tabs and helpers run the browser's own program beneath it, so
    they count as the browser. Two scripts under one interpreter stay apart,
    since neither started the other.
    """
    result = {}
    for pid in found:
        top = pid
        while found[top][4] in running and running[found[top][4]][1] == running[top][1]:
            top = found[top][4]
        result[pid] = top
    return result


def full_name(pid, name):
    """The kernel cuts names at 15 characters; recover the rest when the command line has it."""
    if len(name) == 15:
        try:
            with open(f"/proc/{pid}/cmdline") as source:
                command = os.path.basename(source.read().split("\0")[0])
            if command.startswith(name) and " " not in command:
                name = command
        except (OSError, UnicodeError):
            pass
    return "".join(c if c.isprintable() else "?" for c in name)[:40]


def finished(earlier, found):
    """CPU ticks of processes that ended between two scans, credited to the process that waited for them.

    A process that ends before the next scan takes its own count with it, but
    the kernel adds all it used, its whole life long, to the process that waits
    for it (usually its parent). That covers processes too brief for any scan
    to see. The earlier scan's view of an ending process is taken back off, so
    a long-lived process that ends does not bring its whole past with it.
    Keyed by pid, for the processes in `found`.
    """
    def lasted(pid):
        return pid in earlier and pid in found and earlier[pid][1] == found[pid][1]
    result = {pid: entry[6] - (earlier[pid][6] if lasted(pid) else 0) for pid, entry in found.items()}
    # A process whose parent ends is taken in by an adopter: init, a systemd
    # user manager, or another process seen doing it since the earlier scan.
    adopters = {"1"} | {pid for pid, entry in found.items() if lasted(pid) and entry[3] == "systemd"}
    adopters |= {entry[4] for pid, entry in found.items() if lasted(pid) and entry[4] != earlier[pid][4]}
    for pid, entry in earlier.items():
        past = entry[0] + entry[6]
        if lasted(pid) or not past:
            continue
        if lasted(entry[4]):
            result[entry[4]] -= past  # its parent outlived it, so its parent waited for it
            continue
        # Its parent ended too. If the parent went second, it waited for this
        # one and the nearest ancestor still running waited for both; if it went
        # first, an adopter above took this one in. Nothing left tells which, so
        # the past comes off all of them: one may then read low for a refresh,
        # but none is credited with a past it did not just use.
        waiter, hops, nearest = entry[4], 0, True
        while waiter in earlier and hops < 64:
            if lasted(waiter) and (nearest or waiter in adopters):
                result[waiter] -= past
                nearest = False
            waiter, hops = earlier[waiter][4], hops + 1
    return {pid: max(0, ticks) for pid, ticks in result.items()}


def kind(pid, found, running):
    """"kernel" for the kernel's own threads, "system" for another user's process, "user" for the user's."""
    if pid == "2" or found[pid][4] == "2":
        return "kernel"
    # The kernel shows a process's program only to its owner.
    return "user" if running.get(pid, (0, ""))[1].startswith("/") else "system"


def program(pid, found, running):
    """The file name of the program a process runs, or its name when that is hidden from us."""
    path = running.get(pid, (0, ""))[1]
    if path.startswith("/"):
        return os.path.basename(path.removesuffix(" (deleted)"))
    return found[pid][3]


def command_line(pid, limit=200):
    """What a process was started with, spaces between the arguments, cut to `limit` characters."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as source:
            text = source.read(limit * 4).replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except OSError:
        return ""
    return "".join(c if c.isprintable() else "?" for c in text)[:limit]


def usage(previous, current):
    """Per process: CPU ticks used and storage bytes moved since the `previous` scan.

    The ticks include processes that started and ended between the scans,
    counted for the process that waited for them; see finished(). Storage is
    None for processes the kernel will not tell us about.
    """
    earlier, earlier_storage = previous
    found, storage = current
    ended = finished(earlier, found)
    used, moved = {}, {}
    for pid, entry in found.items():
        before = earlier.get(pid)
        # A process missing from the previous scan, or a reused pid, began after it.
        same = bool(before) and before[1] == entry[1]
        used[pid] = (entry[0] - before[0] if same else entry[0]) + ended[pid]
        if pid in storage:
            moved[pid] = max(0, storage[pid] - (earlier_storage.get(pid, storage[pid]) if same else 0))
        else:
            moved[pid] = None
    return used, moved


def percent(ticks, elapsed_seconds, busy_ticks=None):
    """Ticks as a percentage of one core over the interval, never more than the whole machine was busy."""
    one_core = elapsed_seconds * TICKS_PER_SECOND
    if one_core <= 0:
        return None
    if busy_ticks is not None:
        ticks = min(ticks, max(0, busy_ticks))
    return round(100 * ticks / one_core, 2)


def table(previous, current, running, elapsed_seconds, busy_ticks=None, gpu=None, name=full_name):
    """One row per app: what it used since the `previous` scan and what it holds now.

    `previous` and `current` are results of scan(), taken `elapsed_seconds`
    apart. CPU is a percentage of one core, as top and htop show it: an app
    keeping two cores busy reads 200%. It includes processes that started or
    ended between the scans, counted with the app of the process that waited
    for them, and never exceeds `busy_ticks`, what the whole machine was busy
    for, when that is given. Memory is resident memory summed over the app's
    processes; pages they share are counted once for each. Disk is bytes read
    and written per second, or None when the app belongs to someone else. Time
    is the CPU seconds its running processes have used since they started.
    GPU is the share of the graphics engines its processes kept busy and GPU
    memory what they hold, from `gpu` ({pid: (percent, bytes)}, see
    gpu_clients). Kernel threads that did nothing are left out. Busiest first.
    """
    found = current[0]
    used, moved = usage(previous, current)
    gpu = gpu or {}
    apps = {}
    for pid, top in owners(found, running).items():
        app = apps.setdefault(top, {"used": 0, "ticks": 0, "pages": 0, "count": 0, "threads": 0, "moved": None,
                                    "gpu": 0.0, "gmem": 0})
        app["used"] += used[pid]
        app["ticks"] += found[pid][0]
        app["pages"] += found[pid][2]
        app["count"] += 1
        app["threads"] += found[pid][5]
        if moved[pid] is not None:
            app["moved"] = (app["moved"] or 0) + moved[pid]
        if pid in gpu:
            app["gpu"] += gpu[pid][0]
            app["gmem"] += gpu[pid][1]
    rows = []
    for top, app in apps.items():
        if app["pages"] == 0 and app["used"] == 0:
            continue
        rows.append({
            "pid": int(top),
            "parent": int(found[top][4]),
            "name": name(top, found[top][3]),
            "program": program(top, found, running),
            "kind": kind(top, found, running),
            "count": app["count"],
            "threads": app["threads"],
            "cpu": percent(app["used"], elapsed_seconds, busy_ticks),
            "mem": app["pages"] * PAGE_BYTES,
            "disk": round(app["moved"] / elapsed_seconds) if app["moved"] is not None and elapsed_seconds > 0 else None,
            "time": round(app["ticks"] / TICKS_PER_SECOND),
            "gpu": round(min(100.0, app["gpu"]), 2),
            "gmem": app["gmem"],
        })
    rows.sort(key=lambda row: (row["cpu"] or 0, row["mem"]), reverse=True)
    return rows


def process_rows(previous, current, running, elapsed_seconds, busy_ticks=None, gpu=None, name=full_name,
                 command=command_line, commands=None):
    """One row per process, with its parent, for drawing the process tree.

    The figures are the process's own, measured as in table(). Kernel threads
    that did nothing are left out, but kthreadd, the parent of them all, stays.
    `commands` caches command lines by (pid, start time), since they seldom change.
    """
    found = current[0]
    used, moved = usage(previous, current)
    gpu = gpu or {}
    commands = {} if commands is None else commands
    rows, seen = [], set()
    for pid, entry in found.items():
        sort = kind(pid, found, running)
        if sort == "kernel" and used[pid] == 0 and pid != "2":
            continue
        key = (pid, entry[1])
        seen.add(key)
        if key not in commands:
            commands[key] = command(pid) if sort != "kernel" else ""
        rows.append({
            "pid": int(pid),
            "parent": int(entry[4]),
            "name": name(pid, entry[3]),
            "program": program(pid, found, running),
            "kind": sort,
            "threads": entry[5],
            "cpu": percent(used[pid], elapsed_seconds, busy_ticks),
            "mem": entry[2] * PAGE_BYTES,
            "disk": round(moved[pid] / elapsed_seconds) if moved[pid] is not None and elapsed_seconds > 0 else None,
            "time": round(entry[0] / TICKS_PER_SECOND),
            "gpu": round(gpu[pid][0], 2) if pid in gpu else 0.0,
            "gmem": gpu[pid][1] if pid in gpu else 0,
            "cmd": commands[key],
        })
    for key in [key for key in commands if key not in seen]:
        del commands[key]
    rows.sort(key=lambda row: row["pid"])
    return rows
