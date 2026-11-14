# Undertow

A standalone Quickshell desktop monitor. Starts with Hyprland and lives on the
Wayland **bottom layer**: above wallpaper, below normal windows, without reserving
space or taking keyboard focus. One surface per connected display shares one
collector. Launch **Undertow** from the app launcher, run `undertow`, or click
**Open ↗** on the desktop to open its interactive window.

It keeps out of the space the bar (or any panel) reserves, on whichever edge
the bar is docked, and centres in what is left. A screen whose windows cover
three quarters of it, or that shows a fullscreen window, has its dashboard put
away (not drawn, not updated) until it is uncovered; this is where most of
Undertow's CPU went. Where windows sit comes from Hyprland, asked again when
windows open, close, move or change focus, and every ten seconds. Its panels are as see-through
as an unfocused window under Omarchy's Window Opacity setting (Appearance >
Windows): solid when windows are opaque, the `transparent-window` opacity from
the Hyprland config when transparent (0.90 here), and no more than 0.8 when
glassy. The collector reads the setting (`look.py`) every five seconds, so a
change shows within that. A card on the dashboard's backdrop is made thinner so
that the two together come to the windows' opacity. Hyprland blurs what is
behind, as for the bar, through a layer rule for `undertow-desktop` in
`~/.config/hypr/looknfeel.lua`.

- F11 or the expand button: fullscreen. Escape: leave fullscreen.
- Space or Pause: freeze the displayed history. Collection continues.
- Hover a chart: inspect the same timestamp in all four graphs.
- Waves: toggle ambient animation. Move over the strip to bend its waves.
- **Hardware**: CPU/GFX/APU power histories, physical-core watts/clocks,
  video engine activity, GPU/SoC/fabric/memory clocks, DRAM bandwidth and GTT/VRAM.
- **Overview**: CPU/GPU utilization, system RAM and network histories, with
  logical-CPU activity bars and current power/GPU-memory readings.
- **Processes**: every running app in a sidebar down the right third, in both
  views: CPU (100% = one core), memory, GPU, disk activity, threads and CPU time,
  and the pid where there is room. Click a column heading to rank by it.
  **Apps** lists each app; click one to see its process tree. **Names** folds
  every app of one name into a row (every claude together); click one to see
  its instances. **Tree** is every process under the one that started it.
  A process with a thread holding one core while others idle carries a red
  **pinned 7m** pill (**orphan · pinned** when nothing started it any more),
  read from zen-flow's watcher (`$XDG_RUNTIME_DIR/zen-flow/pinned.json`, see
  `pinned.py`). A list more than a minute old is ignored.
- **Agents**: the coding agents (Claude Code, Codex, OpenCode, pi) beside
  Processes, GitHub-style. Each row is the session's title with a coloured state
  mark (amber: waiting on you, green: working, cyan: done, grey: idle); the
  header counts each state. Beneath it, chips: the harness and model with a
  gauge of how full the context is, **pinned core · 12m** when one of its
  processes (or an orphan probably its) holds a core, the project, the worktree or branch, a
  preview server's port, the Herdr space, the change, and the busiest command
  it is running. Chips that do not fit are left out, most telling first. An
  agent at work or waiting adds the step it is on. Click one to open
  everything it started beneath it.
- **Top · Off/3/5/10**: each graph also draws its busiest contributors as lines.
- Ctrl+Q or close the interactive window: return to the desktop; collection continues.
- To stop completely: `quickshell ipc --config undertow call undertow quit`.

History is collected once per second and bounded to one hour. It is also kept
in `$XDG_RUNTIME_DIR/undertow/history.jsonl`, which lives in memory and is
cleared at logout, so a reload or a restart of the app carries on with the hour
it had; the time it was not running shows as a gap. Empty history stays empty.
CPU is busy time across all cores; RAM is total minus available memory. Network
shows the default-route interface (falling back to an active interface), with
independent download/upload rates computed using actual elapsed time. GPU reads
the first available AMD sysfs utilization device; unsupported readings show —
or "unavailable". Detailed power uses the version-checked AMD gpu_metrics v3.0
ABI on this Z13's Ryzen AI Max+ 395; other ABIs retain the basic metrics.

The process sidebar is refreshed every two seconds. It shows the present, not
the hovered timestamp, and holds still while paused. An app is a process
together with the descendants running the same program, so a browser's tabs
count as the browser; `×14` says how many processes that is. Each row gives:

- **CPU**: percent of one core since the previous refresh, as top and htop show
  it: an app keeping two cores busy reads 200%, and this machine's 32 threads
  go up to 3200%. (The CPU graph is a share of the whole machine instead, so
  one busy core is about 3% there.) It includes processes that started and
  finished between refreshes, which no scan sees: the kernel adds what they
  used to the process that waited for them, so a build's compiler runs count
  for `make` and a script's commands for the script. When a parent and its
  child both end within one refresh, which one ended first cannot be told
  afterwards, so the app that ran them may read low for that refresh rather
  than another app being credited with the child's whole past. No app can read
  more than the whole machine was busy.
- **Memory**: resident memory summed over its processes. Pages they share are
  counted once for each, so the total can overstate what closing it would free.
- **Disk**: bytes read from and written to storage per second. The kernel only
  tells an app's owner, so other users' apps show —; blank means none.
- **GPU**: the share of the graphics and compute engines its GPU clients kept
  busy, from the DRM fdinfo the kernel keeps for each open GPU handle (blank
  when none). Only the user's own processes can be read.
- **Threads**: how many its processes are running.
- **CPU time**: what its running processes have used since they started.

The bar behind a row compares it with the top of the column the table is ranked
by. Kernel threads that did nothing since the last refresh are left out. The
table scrolls; a narrower sidebar drops the pid column, then threads, then GPU.
An app that is a coding agent has its project after its name. In a tree, each
row counts the process and everything below it, so an agent's row is what it
and all it started use; `+12` on a closed row says how many are below it.
None of the tables is part of the saved history.

Every icon is a glyph from the GeistMono Nerd Font, chosen by program, then by
name, then by kind (kernel thread, another user's service, the user's own).
`Icons.js` is written by `tools/make_icons.py`, which checks each glyph name
against the installed font; add a program there and run it again.

Agents come from herdr-core: `hc ls` finds the agent terminals and `hc get`
gives each one's status, current step, session title, `flow.change` label,
space and tab, model and context use. A working agent is asked every refresh,
the rest when Herdr says they moved or every ten seconds. Agent programs
outside Herdr are found by their process. The project, worktree and branch come
from git for the folder the agent's commands run in, its change's worktree, or
its own folder. Preview servers come from the Previews mod's
`previews.mjs --json`, run every two minutes; an agent has one when a server
runs from the checkout it works in.

## Contributor lines

With Top on 3, 5 or 10, each graph draws, beside its total, the busiest
contributors over the window shown. The total is the brightest, thickest line,
over a faint area; contributors are thin lines in the categorical slots, each
keeping its colour while it stays in that graph (slots nine and ten repeat the
first two hues, dashed). The legend gives each line's value at the inspected
moment and counts the lines it has no room for; hover the graph for a readout of
every line, most first, and to pick out the line nearest the pointer. Up to four
lines are also labelled at their ends.

The lines follow the sidebar: apps on Apps and Tree, names on Names, the
instances of a name once it is opened, and agents (with all they started) on
the Agents tab. CPU is the share of the whole machine, on the graph's own scale;
GPU is engine time; memory is resident memory; GPU memory is the VRAM and GTT
each app's GPU clients hold, and the total line becomes VRAM and GTT together.
The power graphs' lines are estimates: each app gets the share of the measured
CPU-core or GFX watts that matches its share of CPU or GPU time; the APU line
is both, and the rest of the chip is not shared out. Network has no lines: the
kernel keeps per-process network figures to root.

Every two seconds the collector writes a compact record of the busiest apps,
names and agents to `$XDG_RUNTIME_DIR/undertow/contributors.jsonl`, beside the
history and kept for the same hour, so the lines survive reloads too. Records
older than fifteen minutes are thinned to one per ten seconds in the app.

Power is reported separately for CPU cores, GFX and APU total. The kernel's
generic AMD hwmon PPT sensor is **not GPU-only power** on this machine. Per-core
watts are firmware-calculated; clocks are target clocks. Firmware filtering and
domain boundaries mean the readings need not add up; no derived "other power"
is invented. GTT usage/budget is GPU-accessible system memory, not additional
installed RAM. The APU's VRAM reservation also comes from physical system memory.

The existing **z13ctl** daemon supplies profile, AC status, temperature and fan
speed using read-only `get-state` every five seconds. It is optional. Active
PL1/PL2/PL3 limits come from the same asus-armoury sysfs backend used by z13ctl,
not the daemon's saved custom-profile projection. Limits are not consumption.
No profile, power limit, fan setting, or device permissions are changed.

The interference strip is **reactive art**, not another measurement chart:
each signal drives a normalized amplitude, all four contribute to a shared
displacement, and additive blending lights up intersections. Network normalizes
against its chart scale. It does not indicate causation between resources.
Motion is capped at 20 fps. In desktop mode it animates on hover; otherwise the
waves react at sample cadence, avoiding constant background animation. The
interactive window animates while focused. Pause and Waves also stop animation.
The collector continues while the resident app is running.

Everything is drawn by the GPU. The strip is a fragment shader (`waves.frag`,
compiled to `waves.frag.qsb`) that works out, for each pixel, how near it is
to each wave; animating it costs the CPU only the few numbers it is handed (a
fifth of what drawing it on a canvas cost). The graphs' lines are Qt Quick
Shapes: once a sample the CPU turns the samples into polylines, thinned to a
lowest and highest point per screen pixel on long ranges, and the GPU draws
them; between samples the layer only slides. After editing the shader, rebuild
it from this directory, and the app reloads:

```sh
/usr/lib/qt6/bin/qsb --glsl "100 es,120,150" --hlsl 50 --msl 12 -o waves.frag.qsb waves.frag
```

## Changes apply themselves

Saving a file in this directory is enough; nothing needs restarting by hand.
The collector looks at the directory once a second and acts once the files have
held still, so several files saved together are picked up together.

- A saved `.qml`, `.js` or rebuilt `.qsb` file reloads the whole app, about two seconds later. A
  reload keeps the history, the view, the time range, the ranking, the sidebar's
  tab and grouping, what is opened in it, and the Top setting.
- A saved `.py` file restarts only the collector. The history and the current
  view are kept.
- A collector that stops for any reason is started again every two seconds, so
  one broken by a bad edit comes back once the file is fixed. The header shows
  "Collector offline" in the meantime.
- Tests (`test_*.py`) are not watched.

"Changed" means "differs from what is running", not "changed since the collector
started": the app hands each collector the identity of the QML it loaded, and a
collector notes its own Python before reading it. A file saved while the app
was still loading therefore causes one more reload instead of leaving old and
new code running together. Quickshell's own file watching is switched off: it
reloads the instant one file is written, which can load half of a change, and
it misses saves that replace a file.

`quickshell ipc --config undertow call undertow status` prints what the running
app holds: samples, apps, processes, agents, contributor records, the lines each
graph has, whether the collector is running, the view and the sidebar's state.

## Checks

From this directory:

```sh
python3 -m unittest -v
/usr/lib/qt6/bin/qmllint --unqualified disable --missing-property disable --uncreatable-type disable -I /usr/lib/qt6/qml *.qml
QT_QPA_PLATFORM=offscreen quickshell --path verify.qml
```

Use Qt 6's linter; `/usr/bin/qmllint` here is Qt 5 and cannot parse typed IPC
methods. The lint command excludes dynamic Loader/JS-object typing and
Quickshell's runtime-selected PanelWindow backend from static warnings.
The offscreen Qt plugin reports expected Wayland/window-mask warnings. The
integration check exercises live Z13 hardware, including the power/GTT fields.
Set `UNDERTOW_CAPTURE=/absolute/path.png` on the integration check to capture
its rendered content. Add `QT_QUICK_BACKEND=rhi` to render offscreen on the GPU,
as the desktop does: without it the offscreen plugin falls back to Qt's software
renderer, which cannot run the waves shader.

Dependencies: Quickshell, Qt Quick/Layouts, Python 3; no web runtime or pip packages.

Autostart: `~/.config/hypr/autostart.lua`. Remove its Undertow line to disable
startup. History does not outlive the login session.
