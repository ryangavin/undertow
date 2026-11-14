"""Linux metrics, one JSON sample per second. No third-party dependencies."""
import json
import os
import socket
import sys
import time
from pathlib import Path
import sources

# Taken before the modules below are read, so one saved while we start is
# still seen as changed. See sources.Watch.
HERE = Path(__file__).resolve().parent
LOADED = sources.fingerprint(HERE)

from amd_metrics import decode  # noqa: E402
import agents  # noqa: E402
import contributors  # noqa: E402
import gpu_clients  # noqa: E402
import history  # noqa: E402
import look  # noqa: E402
import pinned  # noqa: E402
import processes  # noqa: E402

# Listing apps walks all of /proc, so it runs on every other sample.
APP_SCAN_EVERY = 2


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return ""


def number(path):
    try:
        return int(read(path))
    except ValueError:
        return None


def cpu_counters(text):
    values = [int(v) for v in text.splitlines()[0].split()[1:9]]
    return sum(values), values[3] + values[4]


def cpu_percent(previous, current):
    total = current[0] - previous[0]
    return max(0, min(100, 100 * (1 - (current[1] - previous[1]) / total))) if total > 0 else None


def per_cpu(text):
    return {line.split()[0]: cpu_counters(line) for line in text.splitlines()
            if line.startswith("cpu") and line.split()[0] != "cpu"}


def cpu_threads(previous, current):
    """Each logical CPU's busy percentage, in order (cpu0 first). Plain numbers, not
    objects: an hour of samples holds 115,000 fewer objects for the app to keep."""
    return [cpu_percent(previous[key], value) if key in previous else None for key, value in current.items()]


def z13_state():
    """Read the existing daemon; never send a setting command or start it."""
    try:
        runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(0.15)
            client.connect(runtime + "/z13ctl/z13ctl.sock")
            client.sendall(b'{"cmd":"get-state"}\n')
            data = bytearray()
            deadline = time.monotonic() + 0.15
            while b"\n" not in data and len(data) < 65536:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {}
                client.settimeout(remaining)
                chunk = client.recv(min(4096, 65536 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
        response = json.loads(data)
        state = response.get("state", {}) if response.get("ok") else {}
        if not isinstance(state, dict):
            return {}
        return {"profile": str(state.get("profile", "Unknown"))[:80],
                "fanRpm": state.get("fan_rpm"), "cpuTemp": state.get("temperature"),
                "onAC": state.get("on_ac"), "z13Connected": bool(state)}
    except (OSError, ValueError, AttributeError):
        return {}


def power_limits():
    # Same read-only firmware backend as z13ctl. Its get-state TDP is a saved
    # profile projection, so read the actual active limits instead.
    base = Path("/sys/class/firmware-attributes/asus-armoury/attributes")
    return {key: number(base / name / "current_value") for key, name in
            [("pl1", "ppt_pl1_spl"), ("pl2", "ppt_pl2_sppt"), ("pl3", "ppt_pl3_fppt")]}


def memory(text):
    fields = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in text.splitlines()}
    total = fields["MemTotal"]
    return {"mem": total - fields["MemAvailable"], "memTotal": total,
            "swap": fields.get("SwapTotal", 0) - fields.get("SwapFree", 0)}


def network(text):
    result = {}
    for line in text.splitlines()[2:]:
        name, values = line.split(":", 1)
        fields = values.split()
        result[name.strip()] = (int(fields[0]), int(fields[8]))
    return result


def rates(previous, current, elapsed):
    if previous is None or elapsed <= 0 or any(b < a for a, b in zip(previous, current)):
        return None, None
    return tuple((b - a) / elapsed for a, b in zip(previous, current))


def interface(counters):
    for line in read("/proc/net/route").splitlines()[1:]:
        fields = line.split()
        if fields[1] == "00000000" and int(fields[3], 16) & 1 and fields[0] in counters:
            return fields[0]
    for name in counters:
        if name != "lo" and read(f"/sys/class/net/{name}/operstate") == "up":
            return name
    return None


def gpu():
    for device in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
        busy = number(device / "gpu_busy_percent")
        if busy is None:
            continue
        result = {"gpu": busy, "vram": number(device / "mem_info_vram_used"),
                  "vramTotal": number(device / "mem_info_vram_total"), "gpuTemp": None,
                  "gtt": number(device / "mem_info_gtt_used"),
                  "gttTotal": number(device / "mem_info_gtt_total"),
                  "videoBusy": number(device / "vcn_busy_percent")}
        try:
            result.update(decode((device / "gpu_metrics").read_bytes()))
        except OSError:
            pass
        for sensor in device.glob("hwmon/hwmon*/temp1_input"):
            value = number(sensor)
            if value is not None:
                result["gpuTemp"] = value / 1000
                break
        return result
    return {"gpu": None, "vram": None, "vramTotal": None, "gpuTemp": None}


def main():
    # A check run passes --no-history so it neither reads nor adds to the
    # resident app's hour.
    store = None if "--no-history" in sys.argv else history.Store(history.default_path())
    # Who used what, every app scan, kept beside the samples for the same hour.
    shares = None if "--no-history" in sys.argv else history.Store(history.default_path().with_name("contributors.jsonl"))
    if store:
        saved = store.recent(time.time())
        if saved:
            print('{"history":[' + ",".join(saved) + "]}", flush=True)
    if shares:
        saved = shares.recent(time.time())
        if saved:
            print('{"contribHistory":[' + ",".join(saved) + "]}", flush=True)
    gpu_users = gpu_clients.Clients()
    agent_finder = agents.Agents()
    commands = {}
    stat = read("/proc/stat")
    previous_cpu = cpu_counters(stat)
    previous_threads = per_cpu(stat)
    previous_net = network(read("/proc/net/dev"))
    previous_time = time.monotonic()
    z13 = {}
    next_z13 = 0
    looked = None
    scanned = processes.scan()
    running = processes.programs(scanned[0], {})
    scanned_cpu, scanned_at = previous_cpu, time.monotonic()
    count = 0
    # The app tells us which QML it loaded, as the digest it got from the
    # collector that asked for its reload. With none, it has only just been
    # launched and what is on disk now is what it loaded.
    handed = [argument.split("=", 1)[1] for argument in sys.argv if argument.startswith("--loaded-qml=")]
    watch = sources.Watch(HERE, loaded=LOADED, loaded_qml=handed[0] if handed and handed[0] else None)
    while True:
        time.sleep(1)
        reload_to, python_saved = watch.poll()
        if reload_to:
            # The app reloads on this, which replaces this collector too, and
            # tells the next one which QML it loaded.
            print(json.dumps({"reload": watch.qml_changes(), "sources": reload_to}), flush=True)
        if python_saved:
            return  # our own code changed: leave, and the app starts the new one
        now = time.monotonic()
        stat = read("/proc/stat")
        current_cpu = cpu_counters(stat)
        current_threads = per_cpu(stat)
        current_net = network(read("/proc/net/dev"))
        nic = interface(current_net)
        down, up = rates(previous_net.get(nic), current_net.get(nic, (0, 0)), now - previous_time)
        if now >= next_z13:
            z13 = z13_state()
            next_z13 = now + 5
            # How see-through the windows are, sent when it changes, so the
            # panels follow Omarchy's Window Opacity setting.
            seen = look.look()
            if seen != looked:
                print(json.dumps({"look": seen}), flush=True)
                looked = seen
        count += 1
        scanned_apps = None
        if count % APP_SCAN_EVERY == 0:
            found = processes.scan()
            # Timed at the scans themselves, so a slow tick elsewhere does not
            # stretch or squeeze the interval the CPU figures are divided by.
            found_at = time.monotonic()
            gpu_use = gpu_users.sample(time.monotonic_ns())
            running = processes.programs(found[0], running)
            busy = (current_cpu[0] - scanned_cpu[0]) - (current_cpu[1] - scanned_cpu[1])
            elapsed = found_at - scanned_at
            rows = processes.table(scanned, found, running, elapsed, busy_ticks=busy, gpu=gpu_use)
            procs = processes.process_rows(scanned, found, running, elapsed, busy_ticks=busy, gpu=gpu_use, commands=commands)
            agent_rows = agent_finder.refresh(procs)
            # zen-flow's watcher says which threads hold one core while others idle.
            found_pinned = pinned.read()
            pinned.mark(procs, found_pinned)
            pinned.chips(agent_rows, found_pinned)
            # The tables go out on their own, and are not part of the saved
            # history: they are large, and only the present ones are shown.
            # Command lines stay here (the agent finder names a busy command
            # from them); the app does not show them, and they were a sixth
            # of what it had to read every two seconds.
            shown = [{key: value for key, value in proc.items() if key != "cmd"} for proc in procs]
            print(json.dumps({"apps": rows, "processes": len(found[0]), "procs": shown, "agents": agent_rows,
                              "cores": len(current_threads)}, allow_nan=False, separators=(",", ":")), flush=True)
            scanned, scanned_cpu, scanned_at = found, current_cpu, found_at
            scanned_apps = rows, agent_rows
        sample = {"time": time.time(), "cpu": cpu_percent(previous_cpu, current_cpu),
                  "threads": cpu_threads(previous_threads, current_threads),
                  "down": down, "up": up, "interface": nic or "No active interface",
                  **memory(read("/proc/meminfo")), **gpu(), **z13, **power_limits()}
        line = json.dumps(sample, allow_nan=False)
        print(line, flush=True)
        if store:
            store.append(line, sample["time"])
        if scanned_apps:
            # Watts are shared out from this same second's power readings.
            record = contributors.snapshot(sample["time"], scanned_apps[0], scanned_apps[1], len(current_threads),
                                           sample.get("cpuPower"), sample.get("gpuPower"))
            shared = json.dumps(record, allow_nan=False, separators=(",", ":"))
            print('{"contrib":' + shared + "}", flush=True)
            if shares:
                shares.append(shared, record["time"])
        previous_cpu, previous_net, previous_time = current_cpu, current_net, now
        previous_threads = current_threads


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
