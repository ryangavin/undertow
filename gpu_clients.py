"""What each process asks of the GPU, from the DRM fdinfo the kernel keeps for every open GPU handle.

Each handle a process opens on /dev/dri is a client with an id. Its fdinfo
counts the nanoseconds the client's work has spent on each engine and the
memory it holds. Handles are shared across fork, so a client is counted once,
for the lowest pid holding it. Only the user's own processes can be read; the
kernel keeps the rest to their owners. No third-party dependencies.
"""
import os

# The engines the GPU graph's busy figure covers. Video encode and decode are
# their own engine with their own reading.
GRAPHICS = ("drm-engine-gfx", "drm-engine-compute")


def parse_fdinfo(text):
    """One fdinfo as (client id, graphics nanoseconds, memory bytes), or None for a handle that is not a GPU client."""
    values = {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        values[key.strip()] = value.strip()
    client = values.get("drm-client-id")
    if not client:
        return None
    busy = 0
    for key in GRAPHICS:
        if key in values:
            busy += int(values[key].split()[0])

    def size(key):
        if key not in values:
            return None
        number, _, unit = values[key].partition(" ")
        return int(number) * {"": 1, "KiB": 1024, "MiB": 1048576, "GiB": 1073741824}.get(unit, 1)
    memory = 0
    for kind in ("vram", "gtt"):
        # amdgpu names memory drm-memory-*; the newer common keys are drm-resident-*.
        held = size(f"drm-memory-{kind}")
        memory += held if held is not None else size(f"drm-resident-{kind}") or 0
    return client, busy, memory


class Clients:
    """Per-process GPU busy share and memory, refreshed on each call to sample()."""

    def __init__(self, rescan_every=5, proc="/proc"):
        self.proc = proc
        self.rescan_every = rescan_every
        self.calls = 0
        self.handles = {}  # pid -> fds open on /dev/dri
        self.before = {}   # client id -> graphics nanoseconds at the previous sample
        self.before_at = None

    def rescan(self):
        """Find the GPU handles every readable process holds. Listing every fd is the costly part, so it is not done each time."""
        handles = {}
        for entry in os.scandir(self.proc):
            if not entry.name.isdigit():
                continue
            try:
                fds = os.listdir(entry.path + "/fd")
            except OSError:
                continue
            for fd in fds:
                try:
                    if os.readlink(f"{entry.path}/fd/{fd}").startswith("/dev/dri/"):
                        handles.setdefault(entry.name, []).append(fd)
                except OSError:
                    continue
        self.handles = handles

    def sample(self, now_ns):
        """{pid: (busy percent of the graphics engines, memory bytes)} for processes holding GPU clients."""
        if self.calls % self.rescan_every == 0:
            self.rescan()
        self.calls += 1
        owner, busy, memory = {}, {}, {}
        for pid in sorted(self.handles, key=int):
            for fd in self.handles[pid]:
                try:
                    with open(f"{self.proc}/{pid}/fdinfo/{fd}") as source:
                        parsed = parse_fdinfo(source.read())
                except (OSError, ValueError):
                    continue
                if parsed is None or parsed[0] in owner:
                    continue
                owner[parsed[0]] = pid
                busy[parsed[0]], memory[parsed[0]] = parsed[1], parsed[2]
        result = {}
        elapsed = now_ns - self.before_at if self.before_at is not None else 0
        for client, pid in owner.items():
            share = 0.0
            if elapsed > 0 and client in self.before:
                share = max(0.0, min(100.0, 100 * (busy[client] - self.before[client]) / elapsed))
            used, held = result.get(pid, (0.0, 0))
            result[pid] = (min(100.0, used + share), held + memory[client])
        self.before, self.before_at = busy, now_ns
        return result
