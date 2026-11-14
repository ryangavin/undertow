import QtQuick
import QtQuick.Layouts
import "Icons.js" as Icons

// The right third of the dashboard: every process, grouped three ways, and
// the coding agents. One table draws them all. Where it was left (tab, mode,
// the name or tree opened) is kept by the dashboard across reloads, and the
// graphs' contributor lines follow it.
Rectangle {
    id: card
    required property var dashboard
    readonly property var root: dashboard
    readonly property bool agentsTab: root.sidebarTab === "agents"
    readonly property string mode: root.procMode
    radius: 16; color: root.card("#101a25"); border.color: "#263140"

    // Narrower sidebars drop the least telling columns instead of crushing names.
    readonly property var processColumns: [
        { key: "pid", title: "PID", width: 58, tint: "", shown: card.width >= 640 },
        { key: "cpu", title: "CPU", width: 46, tint: "#67dcec", shown: true },
        { key: "mem", title: "MEMORY", width: 68, tint: "#e8bf80", shown: true },
        { key: "gpu", title: "GPU", width: 44, tint: "#b49afa", shown: card.width >= 520 },
        { key: "disk", title: "DISK", width: 70, tint: "#75dfb4", shown: true },
        { key: "threads", title: "THREADS", width: 64, tint: "#b49afa", shown: card.width >= 590 },
        { key: "time", title: "CPU TIME", width: 64, tint: "#6b9ff0", shown: true },
    ].filter(column => column.shown)
    readonly property var agentColumns: [
        { key: "cpu", title: "CPU", width: 46, tint: "#67dcec", shown: true },
        { key: "mem", title: "MEMORY", width: 68, tint: "#e8bf80", shown: true },
    ].filter(column => column.shown)

    function reading(row, key) {
        if (key === "cpu") return cores(row.cpu);
        if (key === "mem") return root.bytes(row.mem);
        if (key === "gpu") return row.gpu ? row.gpu.toFixed(row.gpu < 10 ? 1 : 0) + "%" : "";
        if (key === "disk") return root.rate(row.disk);
        if (key === "time") return root.duration(row.time);
        return row[key] === undefined ? "" : String(row[key]);
    }
    // Percent of one core, as top shows it; past 100 means several cores at once.
    function cores(v) { return v === undefined || v === null ? "—" : (v < 9.95 ? v.toFixed(1) : String(Math.round(v))) + "%"; }

    // Highest first for figures, A to Z for names, low to high for pids.
    function ranked(rows, order) {
        const out = rows.slice();
        if (order === "name") out.sort((a, b) => a.name.localeCompare(b.name) || a.pid - b.pid);
        else if (order === "pid") out.sort((a, b) => a.pid - b.pid);
        else out.sort((a, b) => (b[order] || 0) - (a[order] || 0) || (b.cpu || 0) - (a.cpu || 0) || (b.mem || 0) - (a.mem || 0));
        return out;
    }

    // Worked out only for the views that show them: a binding is redone on
    // every refresh of what it reads, whether anything on screen uses it or not.
    readonly property bool wantsNames: !agentsTab && mode === "names"
    readonly property bool wantsTree: (agentsTab && root.agentOpen.replace(/\|/g, "") !== "") || (!agentsTab && mode === "tree") || !!root.treeRoot

    // Apps added up by name: every claude together.
    readonly property var names: {
        if (!wantsNames) return [];
        const groups = {};
        for (const app of root.apps) {
            const g = groups[app.name] || (groups[app.name] = { key: "n" + app.name, name: app.name, program: app.program, kind: app.kind,
                pid: app.pid, instances: 0, count: 0, threads: 0, cpu: 0, mem: 0, gpu: 0, gmem: 0, disk: null, time: 0 });
            g.instances++; g.count += app.count; g.threads += app.threads; g.cpu += app.cpu || 0; g.mem += app.mem;
            g.gpu += app.gpu || 0; g.gmem += app.gmem || 0; g.time += app.time;
            if (app.disk !== null && app.disk !== undefined) g.disk = (g.disk || 0) + app.disk;
        }
        return Object.values(groups).map(g => Object.assign(g, { suffix: g.instances > 1 ? g.instances + " running" : g.count > 1 ? "×" + g.count : "" }));
    }

    // The process tree. Each row counts the process and everything below it,
    // so an agent's row is what it and all it started use.
    readonly property var tree: {
        if (!wantsTree) return ({ byPid: {}, children: {} });
        const byPid = {}, children = {};
        for (const p of root.procs) byPid[p.pid] = Object.assign({}, p, { own: p });
        for (const p of root.procs) if (byPid[p.parent] && p.parent !== p.pid) (children[p.parent] = children[p.parent] || []).push(p.pid);
        const total = pid => {
            const node = byPid[pid];
            if (node.below !== undefined) return node;
            node.below = 0;
            for (const child of children[pid] || []) {
                const c = total(child);
                node.below += 1 + c.below;
                node.cpu = (node.cpu || 0) + (c.cpu || 0); node.mem += c.mem; node.gpu = Math.min(100, (node.gpu || 0) + (c.gpu || 0));
                node.gmem += c.gmem; node.threads += c.threads; node.time += c.time;
                node.disk = node.disk === null && c.disk === null ? null : (node.disk || 0) + (c.disk || 0);
            }
            return node;
        };
        for (const pid in byPid) total(pid);
        return { byPid: byPid, children: children };
    }

    function has(list, pid) { return list.indexOf("|" + pid + "|") >= 0; }
    function flip(list, pid) { return has(list, pid) ? list.replace("|" + pid + "|", "|") : (list || "|") + pid + "|"; }

    // Rows for the subtree under `pid`, deepest first in order. `openByDefault`
    // says how a node starts out; `toggled` lists the ones clicked the other way.
    function treeRows(pid, depth, openByDefault, toggled, order, out) {
        const node = tree.byPid[pid];
        if (!node) return out;
        const kids = ranked((tree.children[pid] || []).map(child => tree.byPid[child]), order);
        const open = kids.length > 0 && (has(toggled, pid) ? !openByDefault(depth) : openByDefault(depth));
        out.push(Object.assign({}, node, { key: "p" + pid, depth: depth, expandable: kids.length > 0, expanded: open,
            suffix: !open && node.below ? "+" + node.below : "" }));
        if (open) for (const kid of kids) treeRows(kid.pid, depth + 1, openByDefault, toggled, order, out);
        return out;
    }

    readonly property var statusOrder: ({ blocked: 0, working: 1, done: 2, idle: 3 })
    readonly property var statusColor: ({ working: "#75dfb4", blocked: "#e8bf80", done: "#67dcec", idle: "#68788f" })
    // Context use as a colour: calm, filling, nearly full.
    function contextTint(percent) { return percent >= 80 ? "#e66767" : percent >= 60 ? "#e8bf80" : "#67dcec"; }
    // GitHub-style: the session's title is the line; a coloured mark says its
    // state; the specifics are chips beneath, most telling first; and only an
    // agent at work (or waiting on you) adds the step it is on.
    function agentRows() {
        const tops = [];
        for (const agent of root.agents) {
            const branch = agent.worktree ? agent.worktree.split("/").pop() : agent.branch && !["main", "master", "HEAD"].includes(agent.branch) ? agent.branch : "";
            const context = agent.context !== null && agent.context !== undefined ? agent.context : null;
            const busy = agent.running ? agent.running.split(" ").slice(0, 2).map(part => part.split("/").pop()).join(" ") : "";
            const chips = [
                // A model's name without the description some providers put after it in brackets.
                { icon: { program: agent.program, name: agent.name }, text: (agent.model || agent.kind).replace(/\s*\(.*\)\s*$/, ""),
                  meter: context === null ? null : context / 100, tint: context === null ? "" : contextTint(context) },
                // A thread of its holding one core while others idle: telling, so it comes early.
                { symbol: "pinned", text: agent.pinned ? "pinned core · " + agent.pinned : "", tint: "#e66767" },
                { symbol: "folder", text: root.agentPlace(agent) },
                { symbol: "branch", text: branch, tint: "#b49afa" },
            ];
            for (const preview of agent.previews || [])
                chips.push({ symbol: "preview", text: ":" + (preview.url.match(/:(\d+)/) || ["", preview.url])[1], tint: "#75dfb4" });
            chips.push({ symbol: "space", text: agent.where, tint: "#67dcec" });
            chips.push({ symbol: "change", text: agent.changeName && agent.changeName !== branch ? agent.changeName : "", tint: "#e8bf80" });
            chips.push({ symbol: "running", text: busy });
            const active = agent.status === "working" || agent.status === "blocked";
            tops.push(Object.assign({}, agent, { key: "g" + agent.pid,
                name: agent.title || agent.step || (agent.terminal ? agent.where : agent.kind + " · outside Herdr"),
                program: agent.program, kind: "user", depth: 0,
                state: { symbol: statusColor[agent.status] ? agent.status : "unknown", color: statusColor[agent.status] || "#68788f" },
                chips: chips.filter(chip => chip.text),
                // Herdr puts "answer: " before what a waiting agent last said; its mark says that already.
                lines: active && agent.step && agent.step !== agent.title ? [agent.step.replace(/^answer:\s*/, "")] : [],
                expandable: agent.count > 1, expanded: has(root.agentOpen, agent.pid) }));
        }
        // Waiting on you first, then working, then the rest; or by a clicked column.
        const sorted = root.agentOrder === "status"
            ? tops.sort((a, b) => (statusOrder[a.status] ?? 4) - (statusOrder[b.status] ?? 4) || (b.cpu || 0) - (a.cpu || 0))
            : ranked(tops, root.agentOrder);
        const out = [];
        for (const top of sorted) {
            out.push(top);
            if (top.expanded)
                for (const kid of ranked((tree.children[top.pid] || []).map(child => tree.byPid[child]), "cpu"))
                    treeRows(kid.pid, 1, () => true, root.agentToggled, "cpu", out);
        }
        return out;
    }

    readonly property var rows: {
        if (agentsTab) return agentRows();
        if (root.treeRoot) return treeRows(root.treeRoot, 0, () => true, root.treeToggled, root.appOrder, []);
        if (mode === "tree") {
            const out = [];
            for (const top of ranked(root.procs.filter(p => !tree.byPid[p.parent]).map(p => tree.byPid[p.pid]), root.appOrder))
                treeRows(top.pid, 0, depth => depth < 2, root.treeToggled, root.appOrder, out);
            return out;
        }
        const apps = mode === "names" && !root.nameFilter ? names
                   : root.apps.filter(app => mode !== "names" || app.name === root.nameFilter)
                         .map(app => Object.assign({}, app, { key: "a" + app.pid, suffix: appSuffix(app) }));
        return ranked(apps, root.appOrder);
    }

    // After an app's name: where it works, when it is an agent, and how many processes it is.
    function appSuffix(app) {
        const agent = root.agentByPid[app.pid];
        return [agent ? root.agentPlace(agent) : "", app.count > 1 ? "×" + app.count : ""].filter(text => text).join("  ");
    }

    readonly property var focused: root.treeRoot ? tree.byPid[root.treeRoot] || null : null
    readonly property string summary: {
        if (agentsTab) {
            const working = root.agents.filter(a => a.status === "working").length, blocked = root.agents.filter(a => a.status === "blocked").length;
            return root.agents.length + " agents · " + working + " working" + (blocked ? " · " + blocked + " waiting" : "");
        }
        if (root.treeRoot) return focused ? (focused.below + 1) + " processes · " + cores(focused.cpu) + " CPU · " + root.bytes(focused.mem) : "That process has ended";
        if (mode === "tree") return "Each row counts everything it started";
        if (mode === "names" && root.nameFilter) return rows.length + " running · click for its tree";
        if (mode === "names") return root.apps.length + " apps under " + names.length + " names";
        return root.processCount + " running · " + root.apps.length + " apps · 100% = 1 core";
    }

    function openTree(row, from) {
        root.treeFrom = from;
        root.treeToggled = "";
        root.treeRoot = row.pid;
    }
    function back() {
        if (root.treeRoot) { root.treeRoot = 0; root.treeToggled = ""; if (root.treeFrom === "agents") root.sidebarTab = "agents"; return; }
        root.nameFilter = "";
    }

    component Tab: Label {
        id: tab
        property string value
        font.pixelSize: 11; font.letterSpacing: 2
        color: root.sidebarTab === value ? "#dce7f6" : pick.containsMouse ? "#9eafc5" : "#68788f"
        MouseArea { id: pick; anchors.fill: parent; anchors.margins: -5; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.sidebarTab = tab.value }
        Rectangle { visible: root.sidebarTab === tab.value; anchors.top: parent.bottom; anchors.topMargin: 4; width: parent.width; height: 2; radius: 1; color: "#67dcec" }
    }
    component Pick: Rectangle {
        id: pick
        property string text
        property bool selected
        signal clicked()
        implicitWidth: caption.implicitWidth + 16; implicitHeight: 22; radius: 6
        color: selected ? "#293b4c" : area.containsMouse ? "#1d2a38" : "transparent"
        border.color: selected ? "#467283" : "#263140"
        Label { id: caption; anchors.centerIn: parent; text: pick.text; font.pixelSize: 11; color: pick.selected ? "#b8f1ed" : "#9eafc5" }
        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: pick.clicked() }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 14; anchors.topMargin: 14; anchors.bottomMargin: 12
        spacing: 0
        RowLayout {
            spacing: 18; Layout.bottomMargin: 14; Layout.rightMargin: 6
            Tab { text: "PROCESSES"; value: "processes" }
            Tab { text: "AGENTS"; value: "agents" }
            Item { Layout.fillWidth: true }
            Label { visible: !card.agentsTab || !!root.treeRoot; text: card.summary; font.pixelSize: 11; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true; Layout.maximumWidth: implicitWidth }
            // On the Agents tab: how many are in each state, as their marks.
            Row {
                visible: card.agentsTab && !root.treeRoot
                spacing: 12
                Repeater {
                    model: ["blocked", "working", "done", "idle"]
                    Row {
                        required property string modelData
                        readonly property int count: root.agents.filter(agent => agent.status === modelData).length
                        visible: count > 0
                        spacing: 4
                        Text { text: Icons.symbol(parent.modelData); color: card.statusColor[parent.modelData]; font.family: Icons.font; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                        Label { text: String(parent.count); font.pixelSize: 11; color: "#c3cfdd"; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }
        }
        RowLayout {
            spacing: 6; Layout.bottomMargin: 10; Layout.rightMargin: 6
            visible: !card.agentsTab || root.treeRoot
            // Where a drill-down started, to go back to it.
            Label {
                visible: !!root.treeRoot || (card.mode === "names" && !!root.nameFilter)
                text: "‹ " + (root.treeRoot ? ({ apps: "Apps", names: root.nameFilter || "Names", tree: "Tree", agents: "Agents" })[root.treeFrom] || "Back" : "All names")
                font.pixelSize: 12; color: backArea.containsMouse ? "#dce7f6" : "#9eafc5"
                MouseArea { id: backArea; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: card.back() }
            }
            Label {
                visible: !!root.treeRoot || (card.mode === "names" && !!root.nameFilter)
                text: "/  " + (root.treeRoot ? (card.focused ? card.focused.name + " " + root.treeRoot : "pid " + root.treeRoot) : root.nameFilter)
                font.pixelSize: 12; color: "#dce7f6"; Layout.fillWidth: true
            }
            Item { visible: !root.treeRoot && !(card.mode === "names" && root.nameFilter); Layout.fillWidth: true }
            Repeater {
                model: card.agentsTab ? [] : [{ label: "Apps", value: "apps" }, { label: "Names", value: "names" }, { label: "Tree", value: "tree" }]
                Pick {
                    required property var modelData
                    text: modelData.label
                    selected: card.mode === modelData.value && !root.treeRoot
                    onClicked: { root.treeRoot = 0; root.treeToggled = ""; root.nameFilter = ""; root.procMode = modelData.value; }
                }
            }
        }
        ProcessTable {
            Layout.fillWidth: true; Layout.fillHeight: true
            columns: card.agentsTab && !root.treeRoot ? card.agentColumns : card.processColumns
            rows: card.rows
            tree: card.agentsTab || card.mode === "tree" || !!root.treeRoot
            order: card.agentsTab && !root.treeRoot ? root.agentOrder : root.appOrder
            reading: card.reading
            emptyText: card.agentsTab ? "No coding agents running" : root.treeRoot ? "That process has ended" : "Listing apps…"
            onRanked: key => { if (card.agentsTab && !root.treeRoot) root.agentOrder = root.agentOrder === key && key !== "status" ? "status" : key; else root.appOrder = key; }
            onToggled: row => {
                if (card.agentsTab && row.key.startsWith("g")) root.agentOpen = card.flip(root.agentOpen, row.pid);
                else if (card.agentsTab) root.agentToggled = card.flip(root.agentToggled, row.pid);
                else root.treeToggled = card.flip(root.treeToggled, row.pid);
            }
            onActivated: row => {
                if (card.agentsTab && row.key.startsWith("g")) { root.agentOpen = card.flip(root.agentOpen, row.pid); return; }
                if (card.agentsTab) { card.openTree(row, "agents"); root.sidebarTab = "processes"; return; }
                if (row.key.startsWith("n")) { root.nameFilter = row.name; return; }
                if (root.treeRoot || card.mode === "tree") { root.treeToggled = card.flip(root.treeToggled, row.pid); return; }
                card.openTree(row, card.mode);
            }
        }
    }
}
