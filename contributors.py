"""Who used what at each refresh: the compact record the graphs draw their contributor lines from.

A record keeps, for the busiest apps, names and agents, the figures each graph
shows, in the graph's own units so a contributor's line sits on the same scale
as the total it is part of: CPU as a share of the whole machine, GPU as the
share of the graphics engines, memory and GPU memory in MiB, and CPU and GFX
power in watts. Watts are estimates: the firmware measures power for the CPU
cores and the GPU as a whole, and each app is given the share of it that
matches its share of the CPU or GPU time used. Only the busiest are kept, so a
record stays small enough to keep an hour of them. No third-party dependencies.
"""
FIELDS = ("name", "program", "kind", "cpu", "gpu", "mem", "gmem", "cpuW", "gpuW")
MIB = 1048576


def figures(row, cores, cpu_total, gpu_total, cpu_power, gpu_power):
    """One app, name or agent as [name, program, kind, cpu share, gpu share, mem MiB, gpu mem MiB, cpu W, gpu W]."""
    cpu = row.get("cpu") or 0
    gpu = row.get("gpu") or 0
    return [
        row["name"], row.get("program") or row["name"], row.get("kind") or "user",
        round(cpu / cores, 2) if cores else 0,
        round(gpu, 1),
        round(row.get("mem", 0) / MIB, 1),
        round(row.get("gmem", 0) / MIB, 1),
        round(cpu_power * cpu / cpu_total, 2) if cpu_power and cpu_total > 0 else 0,
        round(gpu_power * gpu / gpu_total, 2) if gpu_power and gpu_total > 0 else 0,
    ]


def by_name(apps):
    """Apps added up by name: every claude together, say. The busiest app of a name lends its program and kind."""
    names = {}
    for app in apps:
        total = names.setdefault(app["name"], {"name": app["name"], "program": app.get("program"), "kind": app.get("kind"),
                                               "cpu": 0, "gpu": 0, "mem": 0, "gmem": 0})
        for key in ("cpu", "gpu", "mem", "gmem"):
            total[key] += app.get(key) or 0
    return list(names.values())


def busiest(rows, keep):
    """The rows that are among the `keep` busiest by any of the figures the graphs draw."""
    chosen = {}
    for key in ("cpu", "gpu", "mem", "gmem"):
        for row in sorted(rows, key=lambda row: row.get(key) or 0, reverse=True)[:keep]:
            if row.get(key):
                chosen[id(row)] = row
    return list(chosen.values())


def snapshot(when, apps, agents, cores, cpu_power=None, gpu_power=None, keep=12, per_name=3):
    """One refresh as {"time", "a": {pid: figures}, "n": {name: figures}, "g": {pid: figures}}.

    "a" holds the busiest apps, and the busiest few of each of the busiest
    names, so a name can be opened into its instances; "n" the busiest names;
    "g" every agent, counted with all it started.
    """
    cpu_total = sum(app.get("cpu") or 0 for app in apps)
    gpu_total = sum(app.get("gpu") or 0 for app in apps)
    def record(row):
        return figures(row, cores, cpu_total, gpu_total, cpu_power, gpu_power)
    names = busiest(by_name(apps), keep)
    chosen = {id(app): app for app in busiest(apps, keep)}
    wanted = {name["name"] for name in names}
    for name in wanted:
        same = [app for app in apps if app["name"] == name]
        for app in busiest(same, per_name):
            chosen[id(app)] = app
    return {
        "time": round(when, 3),
        "a": {str(app["pid"]): record(app) for app in chosen.values()},
        "n": {name["name"]: record(name) for name in names},
        "g": {str(agent["pid"]): record({**agent, "name": label}) for agent, label in zip(agents, agent_labels(agents))},
    }


def agent_labels(agents):
    """What to call each agent in a legend: its harness and project, and its session title where that is not enough."""
    plain = [f"{agent['kind']} · {(agent.get('project') or '').rsplit('/', 1)[-1] or agent['name']}" for agent in agents]
    return [f"{label} · {agent['title'][:24]}" if plain.count(label) > 1 and agent.get("title") else label
            for label, agent in zip(plain, agents)]
