import QtQuick
import Quickshell

ShellRoot {
    Loader { id: app; source: "shell.qml" }
    Timer {
        interval: 4500; running: true
        onTriggered: {
            const d = app.item;
            function check(ok, message) { if (!ok) { console.error("FAIL: " + message); Qt.exit(1); throw new Error(message); } }
            check(d !== null && d.history.length >= 3, "Live collector supplies samples");
            check(d.latest.cpu >= 0 && d.latest.cpu <= 100, "CPU stays in range");
            check(d.latest.mem > 0 && d.latest.mem <= d.latest.memTotal, "Memory is valid");
            check(d.latest.threads.length > 0, "Logical CPU breakdown is available");
            check(d.apps.length > 5 && d.processCount >= d.apps.length, "Running apps are listed");
            check(d.apps.every(a => a.name.length > 0 && a.pid > 0 && a.count >= 1 && a.threads >= 1 && a.cpu >= 0 && a.cpu <= 100 * d.latest.threads.length && a.mem >= 0 && a.time >= 0), "Every app row carries its readings");
            check(d.apps[0].cpu >= d.apps[d.apps.length - 1].cpu, "The busiest app comes first");
            check(d.apps.some(a => a.disk !== null) , "Disk activity is known for the user's own apps");
            check(d.appOrder === "cpu", "The app table starts ranked by CPU");
            check(d.apps.every(a => a.program.length > 0 && ["kernel", "system", "user"].includes(a.kind) && a.gpu >= 0 && a.gmem >= 0), "Every app says what program and kind it is, and its GPU use");
            check(d.procs.length >= d.apps.length && d.procs.every(p => p.pid > 0 && p.parent >= 0 && p.cmd === undefined), "Every process is listed with its parent, without its command line");
            check(Array.isArray(d.agents) && d.agents.every(a => a.pid > 0 && ["claude", "codex", "opencode", "pi"].includes(a.kind) && a.count >= 1), "Coding agents are listed with what they started");
            check(d.contrib.length >= 1 && d.contrib[0].a && d.contrib[0].n && d.contrib[0].g, "Contributor records arrive");
            d.refreshLines();
            const lines = d.lineSeries.cpu || [];
            check(lines.length > 0 && lines.length <= d.lineCount, "The CPU graph has its busiest apps as lines");
            check(new Set(lines.map(l => l.slot)).size === lines.length, "Each line in a graph has its own colour");
            d.procMode = "names"; d.refreshLines();
            check(d.lineGroup === "n" && (d.lineSeries.cpu || []).every(l => l.key === l.name), "Grouped by name, the lines are names");
            d.procMode = "apps"; d.lineCount = 0; d.refreshLines();
            check(Object.keys(d.lineSeries).length === 0, "Lines can be turned off");
            d.lineCount = 5;
            check(d.latest.gtt >= 0 && d.latest.gtt <= d.latest.gttTotal, "GTT usage is within budget");
            check(d.latest.corePower.length === 16 && d.latest.cpuPower >= 0 && d.latest.gpuPower >= 0, "Z13 firmware power breakdown is available");
            d.details = true;
            d.pause();
            const count = d.source.length;
            const shown = d.apps;
            d.history = d.history.concat([Object.assign({}, d.latest, {time: d.latest.time + 1})]);
            check(d.source.length === count, "Pause freezes inspection history");
            check(d.apps === shown, "Pause holds the app table still");
            d.rangeSeconds = 900;
            d.hoverFraction = 0;
            check(d.inspected.cpu === undefined, "Unrecorded history does not invent values");
            d.hoverFraction = 1;
            check(d.inspected.cpu !== undefined, "Linked cursor selects the latest sample");
            d.pause();
            check(d.source.length === count + 1, "Resume returns to live data");
            console.log("PASS: live collection, CPU/memory bounds, app table, processes, agents, contributor lines, Z13 power + GTT + core breakdown, pause/resume, range and linked cursor");
            const output = Quickshell.env("UNDERTOW_CAPTURE");
            if (output) {
                d.rangeSeconds = 120; d.hoverFraction = -1;
                const started = d.dashboardContent.grabToImage(result => {
                    check(result.saveToFile(output), "Render capture saved");
                    Qt.quit();
                });
                check(started, "Render capture started");
            } else Qt.quit();
        }
    }
}
