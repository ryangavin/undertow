import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes

Rectangle {
    id: card
    required property var dashboard
    property string heading
    property string metric
    property string secondary: ""
    property color accent: "#67dcec"
    property string valueText
    property string detail
    property string footer
    property real ceiling: 100
    property string unit: "%"
    property string scaleText: ceiling.toFixed(0) + " " + unit
    property Component extra: null
    // Contributor lines: which of the dashboard's line sets this graph draws
    // ("" for none), how to write one of its values, and a note on where the
    // figures come from. `combine` makes the total the metric plus the secondary.
    property string lines: ""
    property bool combine: false
    property string linesNote: ""
    property var format: v => v.toFixed(0) + " " + unit
    readonly property bool contributing: dashboard.lineCount > 0 && lines !== ""
    readonly property var series: contributing ? dashboard.lineSeries[lines] || [] : []
    // The line being looked at: from the legend, or the one nearest the pointer.
    property string highlight: ""
    // The lines are drawn on the GPU (Qt Quick Shapes); what the CPU does is
    // turn samples into polylines, in rebuild(), once a sample or when what is
    // drawn changes. Highlighting a line only changes its width and opacity.
    function later() { Qt.callLater(card.rebuild); }
    onMetricChanged: later()
    onSecondaryChanged: later()
    onCeilingChanged: later()
    onContributingChanged: later()
    // New figures for the same lines arrive every two seconds, and the next
    // sample's rebuild (within a second) takes them; a different set of lines
    // (another Top, another grouping) or a paused graph is rebuilt at once.
    property string builtLines: ""
    readonly property string lineKeys: series.map(line => line.key + ":" + line.slot).join(",")
    onSeriesChanged: { if (dashboard.paused || lineKeys !== builtLines) later(); }
    Connections {
        target: card.dashboard
        function onViewSamplesChanged() { card.later() }
        function onLagChanged() { card.later() }
    }
    radius: 16
    color: dashboard.card("#131c27")
    border.color: "#263140"

    // Categorical slots, stepped for this dark surface and checked for colour
    // blindness in this order. Slots past eight reuse a hue with a dash.
    readonly property var palette: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
    readonly property color totalColor: "#eef4fb"
    function slotColor(slot) { return palette[slot % palette.length]; }
    function total(s) {
        const v = s[metric];
        if (!combine) return v;
        return v === null || v === undefined ? v : v + (s[secondary] || 0);
    }
    // A line's value at a time: its nearest point, if one lies within a refresh or two.
    function at(line, time) {
        let best = null, distance = 3;
        for (let i = line.points.length - 1; i >= 0; i--) {
            const d = Math.abs(line.points[i][0] - time);
            if (d < distance) { best = line.points[i][1]; distance = d; }
            else if (line.points[i][0] < time - 3) break;
        }
        return best;
    }
    readonly property real inspectedTime: dashboard.inspected.time || dashboard.endTime
    function yOf(v, h) { return h - Math.min(1, v / card.ceiling) * (h - 4); }
    // Smooth scrolling: the lines are drawn once a sample onto a canvas a
    // little wider than the plot, which then slides left until the next one,
    // so between samples nothing is redrawn but a position.
    readonly property real step: plot.width * dashboard.samplePeriod / dashboard.rangeSeconds
    // The newest sample time the canvas was last drawn with.
    property real paintedEnd: 0
    // Whole screen pixels: lines stay sharp, and a tick that would move the
    // canvas less than a pixel changes nothing, so nothing is drawn again.
    readonly property real pixelRatio: Screen.devicePixelRatio || 1
    readonly property real slideX: Math.round(pixelRatio * Math.max(-(graph.width - plot.width),
        Math.min(0, -(dashboard.displayEnd - (paintedEnd - dashboard.lag)) / dashboard.rangeSeconds * plot.width))) / pixelRatio

    // What the shapes draw, as polylines in the sliding layer's coordinates:
    // each a list of points, broken where samples are missing.
    property var areaPaths: []
    property var totalPaths: []
    property var metricPaths: []
    property var secondaryPaths: []
    property var contribPaths: []
    // Names at the right edge for up to four lines: {name, slot, y (the line), at (the name)}.
    property var edgeLabels: []

    // Points (time, value) as polylines. `gap` is how many seconds apart two
    // points may be and still be joined. Where there are more points than
    // device pixels across, each pixel column keeps its lowest and highest,
    // so a long range keeps its peaks and costs no more to draw than it shows.
    function polylines(points, start, w, h, gap) {
        const out = [];
        const columns = w * pixelRatio, crowded = points.length > columns * 2;
        let current = null, lastTime = 0, column = -1, low = null, high = null;
        const flush = () => {
            if (!current || low === null) return;
            if (low[0] <= high[0]) { current.push(Qt.point(low[0], low[1])); if (high !== low) current.push(Qt.point(high[0], high[1])); }
            else { current.push(Qt.point(high[0], high[1])); current.push(Qt.point(low[0], low[1])); }
            low = high = null;
        };
        for (const p of points) {
            if (p[1] === null || p[1] === undefined) { flush(); current = null; continue; }
            const x = (p[0] - start) / dashboard.rangeSeconds * w, y = yOf(p[1], h);
            if (!current || p[0] - lastTime > gap) { flush(); current = []; out.push(current); column = -1; }
            lastTime = p[0];
            if (!crowded) { current.push(Qt.point(x, y)); continue; }
            const c = Math.floor(x * pixelRatio);
            if (c !== column) { flush(); column = c; }
            // Lower on screen is a larger y: "low" is the smallest value.
            if (low === null || y > low[1]) low = [x, y];
            if (high === null || y < high[1]) high = [x, y];
        }
        flush();
        return out.filter(line => line.length > 0);
    }
    function rebuild() {
        const w = plot.width, h = graph.height - 2;
        if (w <= 0 || h <= 0) return;
        const end = dashboard.endTime;
        // Running a sample behind, the left edge starts that much earlier.
        const start = end - dashboard.lag - dashboard.rangeSeconds;
        const source = dashboard.source;
        let first = source.length;
        while (first > 0 && source[first - 1].time >= start - 2) first--;
        const samples = source.slice(first);
        if (contributing) {
            const totals = samples.map(s => [s.time, total(s)]);
            const lines = polylines(totals, start, w, h, 3);
            totalPaths = lines;
            // The area under the total: each stretch closed down to the baseline.
            areaPaths = lines.map(line => [Qt.point(line[0].x, h)].concat(line, [Qt.point(line[line.length - 1].x, h)]));
            // Older records are kept 10 s apart, and past fifteen minutes 30 s.
            contribPaths = series.map(line => polylines(line.points, start, w, h, 45));
            metricPaths = []; secondaryPaths = [];
        } else {
            metricPaths = polylines(samples.map(s => [s.time, s[metric]]), start, w, h, 3);
            secondaryPaths = secondary ? polylines(samples.map(s => [s.time, s[secondary]]), start, w, h, 3) : [];
            totalPaths = []; areaPaths = []; contribPaths = [];
        }
        paintedEnd = end;
        builtLines = lineKeys;
        // Up to four lines carry their name at the plot's right edge: at the
        // moment the right edge showed when the lines were built.
        const placed = [];
        if (contributing && series.length > 0 && series.length <= 4) {
            const edge = end - dashboard.lag, ph = plot.height - 2;
            for (const line of series) {
                const v = at(line, edge);
                if (v === null) continue;
                const y = yOf(v, ph);
                placed.push({ name: line.name.length > 18 ? line.name.slice(0, 17) + "…" : line.name, slot: line.slot, y: y, at: y - 9 });
            }
            placed.sort((a, b) => a.at - b.at);
            // Pushed apart downwards, then back up so the last stays inside the plot.
            for (let i = 0; i < placed.length; i++) {
                placed[i].at = Math.max(8, placed[i].at);
                if (i > 0) placed[i].at = Math.max(placed[i].at, placed[i - 1].at + 13);
            }
            for (let i = placed.length - 1; i >= 0; i--)
                placed[i].at = Math.min(placed[i].at, i === placed.length - 1 ? ph - 8 : placed[i + 1].at - 13);
        }
        edgeLabels = placed;
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 22; spacing: 8
        RowLayout {
            Rectangle { width: 6; height: 6; radius: 3; color: card.accent }
            Label { text: card.heading; color: "#e5edf7"; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true }
            Label { text: card.detail; Layout.maximumWidth: card.width * 0.5 }
        }
        RowLayout {
            Label { text: card.valueText; color: "#f0f5fc"; font.pixelSize: 36; font.weight: Font.Medium; Layout.fillWidth: true }
            Label { text: card.scaleText; color: "#68788f" }
        }
        Item {
            id: plot
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 70
            clip: true
            // The grid: hairlines that stay put.
            Repeater {
                model: 5
                Rectangle { required property int index; width: plot.width; height: 1; y: Math.round((plot.height - 2) * index / 4); color: "#263140" }
            }
            // The lines, drawn by the GPU. The layer is a little wider than the
            // plot and slides left between samples (see slideX), so between
            // samples nothing is redrawn but a position.
            Item {
                id: graph
                x: card.slideX
                width: plot.width + 2 * card.step + 2; height: plot.height
                onWidthChanged: card.later()
                onHeightChanged: card.later()
                // The area under the total, and the plain lines when no contributors are drawn.
                Shape {
                    anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        strokeColor: "transparent"; strokeWidth: 0
                        fillColor: Qt.rgba(card.accent.r, card.accent.g, card.accent.b, 0.10)
                        PathMultiline { paths: card.areaPaths }
                    }
                    ShapePath {
                        strokeColor: card.accent; strokeWidth: 2; fillColor: "transparent"; joinStyle: ShapePath.RoundJoin; capStyle: ShapePath.RoundCap
                        PathMultiline { paths: card.metricPaths }
                    }
                    ShapePath {
                        strokeColor: "#6b9ff0"; strokeWidth: 2; fillColor: "transparent"; joinStyle: ShapePath.RoundJoin; capStyle: ShapePath.RoundCap
                        PathMultiline { paths: card.secondaryPaths }
                    }
                }
                // Contributors: thin, in their slots' colours; slots past eight dashed.
                Repeater {
                    model: card.series.length
                    Shape {
                        id: contributor
                        required property int index
                        readonly property var line: card.series[index] || ({ key: "", slot: 0 })
                        anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                        opacity: !card.highlight || card.highlight === line.key ? 0.95 : 0.22
                        ShapePath {
                            strokeColor: card.slotColor(contributor.line.slot)
                            strokeWidth: card.highlight === contributor.line.key ? 2.5 : 1.5
                            fillColor: "transparent"; joinStyle: ShapePath.RoundJoin; capStyle: ShapePath.FlatCap
                            strokeStyle: contributor.line.slot >= card.palette.length ? ShapePath.DashLine : ShapePath.SolidLine
                            // Six on and four off, in units of the line's width.
                            dashPattern: [6 / strokeWidth, 4 / strokeWidth]
                            PathMultiline { paths: card.contribPaths[contributor.index] || [] }
                        }
                    }
                }
                // The total: brightest and thickest, over everything else.
                Shape {
                    anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        strokeColor: card.totalColor; strokeWidth: 2.5; fillColor: "transparent"; joinStyle: ShapePath.RoundJoin; capStyle: ShapePath.RoundCap
                        PathMultiline { paths: card.totalPaths }
                    }
                }
            }
            // Up to four lines carry their name at the plot's right edge. They sit
            // still while the lines glide past.
            Repeater {
                model: card.edgeLabels.length
                Item {
                    id: edgeLabel
                    required property int index
                    readonly property var place: card.edgeLabels[index] || ({ name: "", slot: 0, y: 0, at: 0 })
                    anchors.fill: parent
                    Rectangle {
                        x: plot.width - 8 - name.implicitWidth - 3; y: edgeLabel.place.at - 7
                        width: name.implicitWidth + 6; height: 14; color: "#e6131c27"
                    }
                    Label { id: name; text: edgeLabel.place.name; font.pixelSize: 11; color: "#c3cfdd"; x: plot.width - 8 - implicitWidth; y: edgeLabel.place.at - height / 2 }
                    // A leader from the name to its line at the edge, when they sit apart.
                    Shape {
                        visible: Math.abs(edgeLabel.place.at - edgeLabel.place.y) > 6
                        anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                        ShapePath {
                            strokeColor: card.slotColor(edgeLabel.place.slot); strokeWidth: 1; fillColor: "transparent"
                            startX: plot.width - 6; startY: edgeLabel.place.at
                            PathLine { x: plot.width; y: edgeLabel.place.y }
                        }
                    }
                }
            }
            // The linked cursor: where the pointer is, on every graph.
            Rectangle {
                visible: card.dashboard.hoverFraction >= 0
                x: Math.round(card.dashboard.hoverFraction * plot.width); width: 1; height: plot.height - 2
                color: "#75889d"
            }
            MouseArea {
                id: pointer
                anchors.fill: parent; hoverEnabled: true
                onPositionChanged: mouse => {
                    card.dashboard.hoverFraction = mouse.x / width;
                    // The contributor line nearest the pointer, if one is close.
                    const time = card.dashboard.displayEnd - (1 - mouse.x / width) * card.dashboard.rangeSeconds;
                    let best = "", distance = 10;
                    for (const line of card.series) {
                        const v = card.at(line, time);
                        if (v === null) continue;
                        const d = Math.abs(card.yOf(v, height - 2) - mouse.y);
                        if (d < distance) { best = line.key; distance = d; }
                    }
                    card.highlight = best;
                }
                onExited: { card.dashboard.hoverFraction = -1; card.highlight = ""; }
            }
            Label { anchors.centerIn: parent; visible: card.dashboard.viewSamples.length < 2; text: "Collecting history…" }
            // At the pointer: the total and every line, most first.
            Rectangle {
                id: readout
                visible: pointer.containsMouse && card.contributing && card.series.length > 0
                readonly property var entries: visible ? card.series.map(line => ({ line: line, value: card.at(line, card.inspectedTime) }))
                                                                  .filter(e => e.value !== null).sort((a, b) => b.value - a.value) : []
                x: Math.min(Math.max(0, pointer.mouseX + 14), plot.width - width)
                y: Math.max(0, Math.min(pointer.mouseY - height / 2, plot.height - height))
                width: readoutColumn.implicitWidth + 16; height: readoutColumn.implicitHeight + 10
                radius: 8; color: "#ee0d151f"; border.color: "#2f3d4f"
                Column {
                    id: readoutColumn
                    x: 8; y: 5; spacing: 2
                    // Where the per-app figures come from, estimates above all.
                    Label { visible: card.linesNote !== ""; text: card.linesNote; font.pixelSize: 10; color: "#8e9bb0"; width: 204; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    Row {
                        spacing: 6
                        Rectangle { width: 12; height: 3; radius: 1.5; color: card.totalColor; anchors.verticalCenter: parent.verticalCenter }
                        Label { text: "Total"; color: "#dce7f6"; font.pixelSize: 11; width: 110 }
                        Label { text: card.dashboard.inspected.time ? card.format(card.total(card.dashboard.inspected) || 0) : "—"; color: "#dce7f6"; font.pixelSize: 11; width: 58; horizontalAlignment: Text.AlignRight }
                    }
                    Repeater {
                        model: readout.entries.length
                        Row {
                            required property int index
                            readonly property var modelData: readout.entries[index] || ({ line: { key: "", name: "", program: "", kind: "user", slot: 0 }, value: 0 })
                            spacing: 6
                            Rectangle { width: 12; height: 2; radius: 1; color: card.slotColor(modelData.line.slot); anchors.verticalCenter: parent.verticalCenter }
                            ProcessIcon { program: modelData.line.program; name: modelData.line.name; kind: modelData.line.kind; font.pixelSize: 11; height: 14 }
                            Label { text: modelData.line.name; color: modelData.line.key === card.highlight ? "#f0f5fc" : "#c3cfdd"; font.pixelSize: 11; width: 88 }
                            Label { text: card.format(modelData.value); color: "#c3cfdd"; font.pixelSize: 11; width: 58; horizontalAlignment: Text.AlignRight }
                        }
                    }
                }
            }
        }
        RowLayout {
            // To the second, so it changes with each sample, not with each glide step.
            Label { text: card.dashboard.timeLabel(card.dashboard.endTime - card.dashboard.lag - card.dashboard.rangeSeconds) }
            Item { Layout.fillWidth: true }
            Label { text: card.dashboard.hoverFraction >= 0 ? card.dashboard.timeLabel(card.dashboard.displayEnd - (1 - card.dashboard.hoverFraction) * card.dashboard.rangeSeconds) : "now"; color: card.dashboard.hoverFraction >= 0 ? "#d7e6f5" : "#8e9bb0" }
        }
        // The legend: one line, there whenever lines are on, in the lines'
        // order, with each value at the inspected moment. Hover a name to pick
        // its line out; the readout on the graph lists any that do not fit.
        Item {
            id: legendBox
            visible: card.dashboard.lineCount > 0
            Layout.fillWidth: true; implicitHeight: 16; clip: true
            // How many entries the line holds, so the rest can be counted.
            readonly property int fits: {
                let shown = 0;
                for (let i = 0; i < legendItems.count; i++) {
                    const item = legendItems.itemAt(i);
                    if (item && item.y === 0) shown++;
                }
                return shown;
            }
        Flow {
            id: legend
            width: parent.width - more.width - 6
            spacing: 12
            Row {
                visible: card.lines !== ""
                spacing: 5; height: 16
                Rectangle { width: 12; height: 3; radius: 1.5; color: card.totalColor; anchors.verticalCenter: parent.verticalCenter }
                Label { text: "Total"; color: "#c3cfdd"; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
            }
            // Counts, not arrays, as models here: new lines every two seconds
            // then update the entries instead of building them again.
            Repeater {
                id: legendItems
                model: card.series.length
                Item {
                    id: entry
                    required property int index
                    readonly property var modelData: card.series[index] || ({ key: "", name: "", program: "", kind: "user", slot: 0, points: [] })
                    readonly property var value: card.at(modelData, card.inspectedTime)
                    width: entryRow.implicitWidth; height: 16
                    opacity: !card.highlight || card.highlight === modelData.key ? 1 : 0.45
                    MouseArea { anchors.fill: parent; hoverEnabled: true; onEntered: card.highlight = entry.modelData.key; onExited: card.highlight = "" }
                  Row {
                    id: entryRow
                    spacing: 5; height: 16
                    Row {
                        anchors.verticalCenter: parent.verticalCenter; spacing: 2
                        Rectangle { width: entry.modelData.slot >= card.palette.length ? 5 : 12; height: 2; radius: 1; color: card.slotColor(entry.modelData.slot) }
                        Rectangle { visible: entry.modelData.slot >= card.palette.length; width: 5; height: 2; radius: 1; color: card.slotColor(entry.modelData.slot) }
                    }
                    ProcessIcon { program: entry.modelData.program; name: entry.modelData.name; kind: entry.modelData.kind; font.pixelSize: 11; height: 16 }
                    Label { text: entry.modelData.name; color: "#c3cfdd"; font.pixelSize: 11; width: Math.min(implicitWidth, 96); anchors.verticalCenter: parent.verticalCenter }
                    Label { text: entry.value === null ? "" : card.format(entry.value); color: "#8e9bb0"; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
                  }
                }
            }
            Label { visible: card.lines !== "" && card.series.length === 0; text: card.dashboard.contribCount ? "Nothing listed used any in this window" : "Collecting who uses what…"; font.pixelSize: 11; color: "#68788f" }
            // A graph with no per-app figures says why, where its legend would be.
            Label { visible: card.lines === ""; text: card.linesNote; font.pixelSize: 11; color: "#68788f" }
        }
            Label {
                id: more
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                text: "+" + Math.max(0, card.series.length - legendBox.fits)
                visible: card.series.length > legendBox.fits
                font.pixelSize: 11; color: "#8e9bb0"
            }
        }
        Label { text: card.footer; Layout.fillWidth: true; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
        Loader { sourceComponent: card.extra; active: card.extra !== null; visible: active; Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0 }
    }
}
