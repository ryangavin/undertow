import QtQuick
import Quickshell
import Quickshell.Io

ShellRoot {
    id: controller
    readonly property alias dashboardContent: content.item
    property var history: []
    property var frozen: []
    // Every running app, process and coding agent, as of the collector's
    // latest look. Not history.
    property var apps: []
    property var procs: []
    property var agents: []
    readonly property var agentByPid: {
        const found = {};
        for (const agent of agents) found[agent.pid] = agent;
        return found;
    }
    // Where an agent works, in a word: its project, or its Herdr space when it
    // is in no repository, or its folder.
    function agentPlace(agent) {
        if (agent.project && agent.project !== "Projects") return agent.project.split("/").pop();
        if (agent.where) return agent.where.split(" / ")[0];
        return (agent.cwd || agent.name).split("/").pop() || agent.kind;
    }
    property int cores: 1
    property int processCount: 0
    // Who used what, every two seconds, for the graphs' contributor lines.
    // An hour of it; past fifteen minutes one record in five is kept.
    property var contrib: []
    property var contribFrozen: []
    readonly property var contribSource: paused ? contribFrozen : contrib
    readonly property int contribCount: contribSource.length
    property bool paused: false
    // How the dashboard was left: kept across a reload, so a saved change
    // does not put it back on the Overview.
    PersistentProperties {
        id: view
        reloadableId: "undertowView"
        property bool motion: true
        property bool details: false
        property int rangeSeconds: 120
        property string appOrder: "cpu"
        // The sidebar: which tab, how processes are grouped, and what is opened.
        property string sidebarTab: "processes"
        property string procMode: "apps"
        property string nameFilter: ""
        property int treeRoot: 0
        property string treeFrom: "apps"
        property string treeToggled: ""
        property string agentOpen: ""
        property string agentToggled: ""
        property string agentOrder: "status"
        // How many contributor lines each graph draws: 0, 3, 5 or 10.
        property int lineCount: 5
        // How opaque the panels are, as the collector last read it from
        // Omarchy's Window Opacity setting; kept so a reload does not flash.
        property real panelAlpha: 1
        property string panelMode: "opaque"
        // Which QML this run of the app loaded: the digest from the collector
        // that asked for the reload, handed on to the collector we start.
        property string loadedQml: ""
    }
    // The collector decides when to reload, after the files have held still.
    // Quickshell's own watcher reloads the instant one file is written, which
    // can load a half-saved set, and it misses saves that replace a file.
    Component.onCompleted: Quickshell.watchFiles = false
    property alias motion: view.motion
    property alias details: view.details
    property alias rangeSeconds: view.rangeSeconds
    // The column the app table is ranked by: "cpu", "mem", "disk", "threads", "time", "pid" or "name".
    property alias appOrder: view.appOrder
    property alias sidebarTab: view.sidebarTab
    property alias procMode: view.procMode
    property alias nameFilter: view.nameFilter
    property alias treeRoot: view.treeRoot
    property alias treeFrom: view.treeFrom
    property alias treeToggled: view.treeToggled
    property alias agentOpen: view.agentOpen
    property alias agentToggled: view.agentToggled
    property alias agentOrder: view.agentOrder
    property alias lineCount: view.lineCount
    readonly property bool checking: Quickshell.env("QT_QPA_PLATFORM") === "offscreen"
    property bool desktopEnabled: !checking
    property bool windowShown: !desktopEnabled || Quickshell.env("UNDERTOW_WINDOW") === "1"
    property real hoverFraction: -1
    property var latest: history.length ? history[history.length - 1] : ({})
    property var source: paused ? frozen : history
    property real endTime: source.length ? source[source.length - 1].time : Date.now() / 1000
    // The samples in the window shown: found by halving, not by testing all
    // of the hour's 3,600 every second.
    property var viewSamples: {
        const from = endTime - rangeSeconds;
        let low = 0, high = source.length;
        while (low < high) { const mid = (low + high) >> 1; if (source[mid].time < from) low = mid + 1; else high = mid; }
        return source.slice(low);
    }

    // Smooth scrolling. On the two-minute view the graphs run one sample
    // behind and glide towards the newest one between samples, instead of
    // jumping a step each second. Wider ranges move less than a pixel a
    // second, so there they stay put and show the newest sample at the edge.
    readonly property bool sliding: !paused && rangeSeconds <= 120
    // Seconds between samples, as they actually arrive.
    property real samplePeriod: 1
    property real arrivedAt: 0
    readonly property real lag: sliding ? samplePeriod : 0
    // The moment at the graphs' right edge.
    property real displayEnd: endTime
    function glide() {
        displayEnd = sliding ? endTime - lag + Math.min(lag, (Date.now() - arrivedAt) / 1000) : endTime;
    }
    onEndTimeChanged: glide()
    onSlidingChanged: glide()
    // About a screen pixel a step on the two-minute view: the plots move 7 to
    // 10 device pixels a second, and every step redraws the screen.
    Timer { interval: 150; running: controller.sliding; repeat: true; onTriggered: controller.glide() }

    property var inspected: {
        if (hoverFraction < 0) return source.length ? source[source.length - 1] : {};
        const time = displayEnd - (1 - hoverFraction) * rangeSeconds;
        let best = null, distance = 2;
        for (const s of viewSamples) { const d = Math.abs(s.time - time); if (d < distance) { best = s; distance = d; } }
        return best || {};
    }
    property real netCeiling: {
        let peak = 1048576;
        for (const s of viewSamples) peak = Math.max(peak, s.down || 0, s.up || 0);
        return Math.pow(2, Math.ceil(Math.log2(peak)));
    }
    property real lastReceived: 0
    property real powerCeiling: {
        let peak = Math.max(20, latest.pl1 || 0);
        for (const s of viewSamples) peak = Math.max(peak, s.cpuPower || 0, s.gpuPower || 0, s.apuPower || 0);
        return Math.ceil(peak / 10) * 10;
    }
    property bool stale: false
    function watts(v) { return v == null ? "unavailable" : v.toFixed(1) + " W"; }
    function clock(v) { return v == null ? "—" : (v / 1000).toFixed(2) + " GHz"; }
    function bandwidth(v) { return v == null ? "—" : (v / 1000).toFixed(1) + " GB/s"; }
    function timeLabel(seconds) { return Qt.formatDateTime(new Date(seconds * 1000), "HH:mm:ss"); }
    function percent(v) { return v === undefined || v === null ? "—" : v.toFixed(0) + "%"; }
    function share(v) { return v === undefined || v === null ? "—" : v.toFixed(1) + "%"; }
    // Bytes a second; nothing at all reads better than a column of zeros.
    function rate(v) { return v === undefined || v === null ? "—" : v < 1024 ? "" : bytes(v) + "/s"; }
    function duration(seconds) {
        if (seconds === undefined || seconds === null) return "—";
        const two = n => String(Math.floor(n)).padStart(2, "0");
        if (seconds < 60) return Math.floor(seconds) + "s";
        if (seconds < 3600) return Math.floor(seconds / 60) + "m " + two(seconds % 60) + "s";
        if (seconds < 86400) return Math.floor(seconds / 3600) + "h " + two(seconds % 3600 / 60) + "m";
        return Math.floor(seconds / 86400) + "d " + two(seconds % 86400 / 3600) + "h";
    }
    function bytes(v) {
        if (v === undefined || v === null) return "—";
        if (v >= 1073741824) return (v / 1073741824).toFixed(1) + " GiB";
        if (v >= 1048576) return (v / 1048576).toFixed(1) + " MiB";
        return (v / 1024).toFixed(0) + " KiB";
    }
    function pause() { if (!paused) { frozen = history.slice(); contribFrozen = contrib.slice(); } paused = !paused; }

    // Panels as see-through as the desktop's windows. A card sits on the
    // dashboard's backdrop, so each is made thinner than the windows' opacity
    // in such a way that the two together come to exactly that: a card reads
    // like an unfocused window, and the gaps between cards a little clearer.
    property alias panelAlpha: view.panelAlpha
    property alias panelMode: view.panelMode
    readonly property real backdropAlpha: panelAlpha * 0.86
    readonly property real cardAlpha: panelAlpha >= 1 ? 1 : Math.max(0, 1 - (1 - panelAlpha) / (1 - backdropAlpha))
    // A colour at the card's see-through.
    function card(hex) { const c = Qt.color(hex); return Qt.rgba(c.r, c.g, c.b, cardAlpha); }

    // Contributor lines follow the sidebar: agents on the Agents tab, names
    // when processes are grouped by name, otherwise apps (of one name, when
    // a name is opened).
    readonly property string lineGroup: sidebarTab === "agents" ? "g" : procMode === "names" && !nameFilter ? "n" : "a"
    readonly property string lineFilter: sidebarTab !== "agents" && procMode === "names" ? nameFilter : ""
    // Each line set: the fields of a contributor record it adds up, and the
    // factor to the graph's units (records keep memory in MiB).
    readonly property var lineFields: ({ cpu: [3], gpu: [4], mem: [5], gpumem: [6], cpuPower: [7], gpuPower: [8], apuPower: [7, 8] })
    readonly property var lineScale: ({ mem: 1048576, gpumem: 1048576 })
    // An app missing from a record was not among the busiest: for rates that
    // is near enough nothing; for sizes it is unknown, and leaves a gap.
    readonly property var lineGaps: ({ mem: true, gpumem: true })
    property var lineSeries: ({})
    property var slotOf: ({})
    property string slotScope: ""
    // The busiest `lineCount` over the window shown, per graph, each with the
    // colour slot it keeps in that graph while it is shown. Slots are each
    // graph's own, so a graph of four lines never reaches the dashed ones.
    function refreshLines() {
        const scope = lineGroup + "|" + lineFilter;
        if (scope !== slotScope || JSON.stringify(slotOf).length > 20000) { slotOf = {}; slotScope = scope; }
        if (!lineCount) { lineSeries = {}; return; }
        const end = endTime, start = end - rangeSeconds;
        const records = contribSource.filter(r => r.time >= start - 3 && r.time <= end + 1);
        const result = {};
        for (const set of details ? ["cpuPower", "gpuPower", "gpumem", "apuPower"] : ["cpu", "gpu", "mem"]) {
            const fields = lineFields[set];
            const value = e => { let v = 0; for (const i of fields) v += e[i] || 0; return v; };
            const score = {}, info = {};
            for (const r of records) {
                const entries = r[lineGroup] || {};
                for (const key in entries) {
                    const e = entries[key];
                    if (lineFilter && e[0] !== lineFilter) continue;
                    const v = value(e);
                    if (v > 0) { score[key] = (score[key] || 0) + v; info[key] = e; }
                }
            }
            const lines = Object.keys(score).sort((a, b) => score[b] - score[a]).slice(0, lineCount)
                .map(key => ({ key: key, name: info[key][0], program: info[key][1], kind: info[key][2], points: [] }));
            if (lineGroup === "a" || lineGroup === "g") {
                // An app that is an agent is named for where it works, as the
                // sidebar names it; lines that still share a name are told
                // apart by pid.
                for (const line of lines) {
                    const agent = agentByPid[line.key];
                    if (agent) line.name = (lineGroup === "g" ? agent.kind : line.name) + " · " + agentPlace(agent);
                }
                const named = {};
                for (const line of lines) named[line.name] = (named[line.name] || 0) + 1;
                for (const line of lines) if (named[line.name] > 1) line.name += " " + line.key;
            }
            // Colour follows the entity, never its rank. A remembered slot past
            // this graph's count is let go, so the lines fill the first slots.
            const taken = {}, kept = slotOf[set] || (slotOf[set] = {});
            for (const line of lines) { const s = kept[line.key]; if (s !== undefined && s < lines.length && !taken[s]) { line.slot = s; taken[s] = true; } }
            for (const line of lines) if (line.slot === undefined) { let s = 0; while (taken[s]) s++; line.slot = s; taken[s] = true; kept[line.key] = s; }
            for (const r of records) {
                const entries = r[lineGroup] || {};
                for (const line of lines) {
                    const e = entries[line.key];
                    line.points.push([r.time, e ? value(e) * (lineScale[set] || 1) : lineGaps[set] ? null : 0]);
                }
            }
            result[set] = lines;
        }
        lineSeries = result;
    }
    // Several of these change together; work the lines out once after them.
    Timer { id: linesLater; interval: 30; onTriggered: controller.refreshLines() }
    onLineCountChanged: linesLater.restart()
    onLineGroupChanged: linesLater.restart()
    onLineFilterChanged: linesLater.restart()
    onRangeSecondsChanged: linesLater.restart()
    onDetailsChanged: linesLater.restart()
    onPausedChanged: linesLater.restart()
    // Past fifteen minutes the screen has fewer pixels than records: keep one in five.
    // Every record only for the two-minute view; older, no more than a view
    // can draw: one per 10 s up to fifteen minutes, one per 30 s beyond. The
    // records are most of what the app holds in memory, and the garbage
    // collector walks all of it.
    function thinned(records, now) {
        const out = [];
        let bucket = -1;
        for (const r of records) {
            if (r.time < now - 3600) continue;
            if (r.time >= now - 150) { out.push(r); continue; }
            const size = r.time >= now - 900 ? 10 : 30;
            const b = Math.floor(r.time / size) * size;
            if (b !== bucket) { out.push(r); bucket = b; }
        }
        return out;
    }
    property int contribAdded: 0
    Process {
        id: collector
        // A check run must not read or add to the resident app's saved hour.
        command: ["python3", "-u", Qt.resolvedUrl("metrics.py").toString().replace("file://", "")]
            .concat(controller.checking ? ["--no-history"] : [])
            .concat(view.loadedQml ? ["--loaded-qml=" + view.loadedQml] : [])
        running: true
        stdout: SplitParser {
            onRead: data => {
                try {
                    const sample = JSON.parse(data);
                    if (sample.reload) {
                        console.log("Sources changed, reloading:", sample.reload.join(", "));
                        view.loadedQml = sample.sources || "";
                        Quickshell.reload(false);
                        return;
                    }
                    // How see-through the windows are, whenever it changes.
                    if (sample.look) {
                        controller.panelAlpha = sample.look.alpha;
                        controller.panelMode = sample.look.mode;
                        return;
                    }
                    // The tables of running apps, processes and agents, sent whole every other second.
                    if (sample.apps) {
                        if (!controller.paused) {
                            controller.apps = sample.apps; controller.processCount = sample.processes || 0;
                            controller.procs = sample.procs || []; controller.agents = sample.agents || [];
                            controller.cores = sample.cores || 1;
                        }
                        return;
                    }
                    if (sample.contrib) {
                        const next = controller.contrib.concat([sample.contrib]);
                        controller.contribAdded++;
                        controller.contrib = controller.contribAdded % 30 === 0 ? controller.thinned(next, sample.contrib.time) : next;
                        if (!controller.paused) linesLater.restart();
                        return;
                    }
                    // The hour of contributor records the collector before this one kept.
                    if (sample.contribHistory) {
                        if (sample.contribHistory.length > controller.contrib.length)
                            controller.contrib = controller.thinned(sample.contribHistory, Date.now() / 1000);
                        linesLater.restart();
                        return;
                    }
                    // A collector's first words: the hour saved by the one before it.
                    // After a reload that is all the history there is; after a
                    // collector restart we already hold it, and keep ours.
                    if (sample.history) {
                        const past = sample.history.filter(s => s.time >= Date.now() / 1000 - 3600);
                        if (past.length > controller.history.length) controller.history = past;
                        return;
                    }
                    // Anything else without a time is a message this version does
                    // not know. Taking it for a sample would empty the graphs.
                    if (typeof sample.time !== "number") return;
                    // How far apart samples come, smoothed, so the glide between
                    // them lasts as long as the wait for the next one.
                    const gap = sample.time - (controller.latest.time || 0);
                    if (gap > 0.5 && gap < 3) controller.samplePeriod = 0.8 * controller.samplePeriod + 0.2 * gap;
                    controller.arrivedAt = Date.now();
                    // One copy of the hour, less what fell out of it, plus the new sample.
                    let drop = 0;
                    while (drop < controller.history.length && controller.history[drop].time < sample.time - 3600) drop++;
                    const next = controller.history.slice(drop);
                    next.push(sample);
                    controller.history = next;
                    controller.lastReceived = Date.now(); controller.stale = false;
                } catch (error) { console.warn("Invalid metric sample:", error); }
            }
        }
        // It leaves when its own code changes, and may crash: start it again
        // either way. History is kept here, so the graphs carry on.
        onExited: (exitCode, exitStatus) => { console.log("Collector stopped (" + exitCode + "), starting it again"); restart.start(); }
    }
    Timer { id: restart; interval: 2000; onTriggered: collector.running = true }
    Timer { interval: 2000; running: true; repeat: true; onTriggered: controller.stale = !collector.running || (controller.lastReceived > 0 && Date.now() - controller.lastReceived > 4000) }
    IpcHandler {
        target: "undertow"
        function show(): void { controller.windowShown = true; }
        function quit(): void { Qt.quit(); }
        // What the running app holds, for checking it without seeing the screen.
        function status(): string {
            return JSON.stringify({
                samples: controller.history.length,
                seconds: controller.history.length ? Math.round(controller.latest.time - controller.history[0].time) : 0,
                apps: controller.apps.length, processes: controller.processCount,
                // The busiest apps as the collector last sent them (CPU: 100 = one core).
                top: controller.apps.slice(0, 3).map(a => ({ name: a.name, cpu: a.cpu })),
                procs: controller.procs.length, agents: controller.agents.length,
                working: controller.agents.filter(a => a.status === "working").length,
                contrib: controller.contrib.length, lines: controller.lineCount, lineGroup: controller.lineGroup,
                // How many lines each graph has now, and the first few names in the CPU one.
                lineSets: Object.keys(controller.lineSeries).map(k => k + ":" + controller.lineSeries[k].length).join(" "),
                cpuLines: (controller.lineSeries.cpu || controller.lineSeries.cpuPower || []).slice(0, 3).map(l => l.name),
                sidebar: controller.sidebarTab + "/" + controller.procMode + (controller.nameFilter ? "/" + controller.nameFilter : "") + (controller.treeRoot ? "/tree " + controller.treeRoot : ""),
                collector: collector.running ? "running" : "stopped", stale: controller.stale, paused: controller.paused,
                view: controller.details ? "hardware" : "overview", range: controller.rangeSeconds, order: controller.appOrder,
                loadedQml: view.loadedQml
            });
        }
    }
    Loader {
        active: controller.desktopEnabled
        source: "Desktop.qml"
        onLoaded: item.dashboard = controller
    }
    FloatingWindow {
        id: window
        visible: controller.windowShown
        title: "Undertow — System currents"
        implicitWidth: 1440; implicitHeight: 960
        minimumSize: Qt.size(1100, 850)
        // Solid when windows are; otherwise as see-through as the desktop's backdrop.
        color: controller.panelAlpha >= 1 ? "#0b121c" : Qt.rgba(0.043, 0.071, 0.110, controller.backdropAlpha)
        onClosed: controller.windowShown = false
        Shortcut { sequence: "F11"; onActivated: window.fullscreen = !window.fullscreen }
        Shortcut { sequence: "Escape"; onActivated: window.fullscreen = false }
        Shortcut { sequence: "Space"; onActivated: controller.pause() }
        Shortcut { sequence: "Ctrl+Q"; onActivated: controller.windowShown = false }
        // Built only while the window is open: hidden, it would still redo
        // every update the desktop's dashboards do, for nobody to see.
        Loader {
            id: content
            active: controller.windowShown
            anchors.fill: parent; anchors.margins: 28
            sourceComponent: Dashboard {
                dashboard: controller
                animate: controller.windowShown && !window.minimized && Window.active
                onExpand: window.fullscreen = !window.fullscreen
            }
        }
    }
}
