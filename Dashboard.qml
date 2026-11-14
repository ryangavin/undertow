import QtQuick
import QtQuick.Layouts

GridLayout {
    id: view
    required property var dashboard
    readonly property var root: dashboard
    property bool desktop: false
    property bool animate: false
    signal expand()
    // Landscape: the graphs keep the left two thirds and the app table takes
    // the right third. Portrait (a screen turned on its side): the app table
    // goes beneath the graphs, at the full width.
    readonly property bool stacked: height > width
    columns: stacked ? 1 : 2
    rowSpacing: 14; columnSpacing: 14
    // How wide the graphs' column is, from the dashboard's own size rather
    // than from what the column holds, so what fits in it cannot feed back
    // into how wide it is.
    readonly property real mainWidth: stacked ? width : (width - columnSpacing) * 2 / 3
    ColumnLayout {
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.preferredWidth: 2; Layout.preferredHeight: view.stacked ? 3 : -1
        spacing: 12
        // The controls sit beside the title when there is room for them in
        // one line, and beneath it otherwise, wrapping onto as many lines as
        // they need.
        GridLayout {
            id: header
            Layout.fillWidth: true
            readonly property bool roomy: view.mainWidth >= title.implicitWidth + controls.oneLine + 24
            columns: roomy ? 3 : 1
            rowSpacing: 10
            ColumnLayout {
                id: title
                spacing: 3
                Label { text: "undertow"; font.pixelSize: 28; font.weight: Font.DemiBold; font.letterSpacing: -1; color: "#eaf2fc" }
                Label { text: "Four signals. One machine." }
            }
            Item { visible: header.roomy; Layout.fillWidth: true }
            Flow {
                id: controls
                spacing: 5
                // Their width in one line; none of them changes with the space given.
                readonly property real oneLine: {
                    let total = 0, count = 0;
                    for (const item of children)
                        if (item.implicitWidth > 0) { total += item.implicitWidth; count++; }
                    return total + Math.max(0, count - 1) * spacing;
                }
                Layout.fillWidth: !header.roomy
                Layout.preferredWidth: header.roomy ? oneLine : -1
                Label { text: root.stale ? "● Collector offline" : root.paused ? "Ⅱ Inspecting" : "● Live · 1s"; color: root.stale ? "#e8bf80" : "#75dfb4"; rightPadding: 8; height: 34; verticalAlignment: Text.AlignVCenter }
                Chip { alpha: root.cardAlpha; text: root.details ? "Overview" : "Hardware"; selected: root.details; onClicked: root.details = !root.details }
                Repeater {
                    model: [{label: "2m", seconds: 120}, {label: "15m", seconds: 900}, {label: "1h", seconds: 3600}]
                    Chip { required property var modelData; alpha: root.cardAlpha; text: modelData.label; selected: root.rangeSeconds === modelData.seconds; onClicked: root.rangeSeconds = modelData.seconds }
                }
                // How many of the busiest each graph draws beside its total.
                Label { text: "Top"; color: "#68788f"; leftPadding: 6; height: 34; verticalAlignment: Text.AlignVCenter }
                Repeater {
                    model: [{label: "Off", count: 0}, {label: "3", count: 3}, {label: "5", count: 5}, {label: "10", count: 10}]
                    Chip { required property var modelData; alpha: root.cardAlpha; text: modelData.label; selected: root.lineCount === modelData.count; onClicked: root.lineCount = modelData.count }
                }
                Chip { alpha: root.cardAlpha; text: root.paused ? "Resume" : "Pause"; selected: root.paused; onClicked: root.pause() }
                Chip { alpha: root.cardAlpha; text: "Waves"; selected: root.motion; onClicked: root.motion = !root.motion }
                Chip { alpha: root.cardAlpha; text: view.desktop ? "Open ↗" : "⛶"; onClicked: view.expand() }
            }
        }
        Waves { dashboard: root; moving: root.motion && !root.paused && (view.animate || (view.desktop && hovered)); Layout.fillWidth: true; Layout.preferredHeight: root.details ? 80 : 110 }
        // Two readings side by side, or one above the other when they do not fit.
        GridLayout {
            id: readings
            Layout.fillWidth: true
            columns: view.mainWidth >= z13.implicitWidth + limits.implicitWidth + 30 ? 2 : 1
            rowSpacing: 4
            Label {
                id: z13
                text: (root.latest.z13Connected ? "z13ctl · " + root.latest.profile + " · " + (root.latest.onAC ? "AC" : "Battery") : "z13ctl unavailable")
                      + "   /   Fan " + (root.latest.fanRpm == null ? "—" : root.latest.fanRpm + " RPM")
                Layout.fillWidth: true
            }
            Label { id: limits; text: "Power limits: " + root.watts(root.latest.pl1) + " sustained  ·  " + root.watts(root.latest.pl2) + " short  ·  " + root.watts(root.latest.pl3) + " fast"; Layout.fillWidth: readings.columns === 1 }
        }
        GridLayout {
            // Side by side in pairs; one beneath another, at the full width, when the dashboard stands upright.
            columns: view.stacked ? 1 : 2; columnSpacing: 14; rowSpacing: 14; Layout.fillWidth: true; Layout.fillHeight: true
            Graph {
                dashboard: root; compact: view.stacked; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: root.details ? 1.4 : 1
                heading: root.details ? "CPU cores · power" : "CPU"; metric: root.details ? "cpuPower" : "cpu"; accent: "#67dcec"
                ceiling: root.details ? root.powerCeiling : 100; unit: root.details ? "W" : "%"
                valueText: root.details ? root.watts(root.inspected.cpuPower) : root.percent(root.inspected.cpu)
                detail: root.inspected.cpuTemp == null ? "Temperature unavailable" : root.inspected.cpuTemp.toFixed(0) + "°C · CPU"
                footer: root.details ? "Physical cores · firmware-calculated watts / target clocks" : "CPU cores " + root.watts(root.inspected.cpuPower) + "  ·  APU " + root.watts(root.inspected.apuPower)
                extra: root.details ? cores : threads
                lines: root.details ? "cpuPower" : "cpu"
                format: root.details ? (v => v.toFixed(1) + " W") : (v => v.toFixed(v < 10 ? 1 : 0) + "%")
                linesNote: root.details ? "Per app: estimated, its share of CPU time × core power" : "Per app: share of the whole machine"
                Component { id: cores; CoreGrid { dashboard: root; sample: root.inspected } }
                Component {
                    id: threads
                    RowLayout {
                        spacing: 3
                        // A count, not the array: each new sample then updates the
                        // bars in place instead of building all of them again.
                        Repeater {
                            model: (root.inspected.threads || []).length
                            Rectangle {
                                required property int index
                                // A busy percentage; samples saved before 11 Nov held {id, busy}.
                                readonly property real busy: {
                                    const thread = (root.inspected.threads || [])[index];
                                    return typeof thread === "number" ? thread : thread ? thread.busy || 0 : 0;
                                }
                                Layout.fillWidth: true; Layout.preferredWidth: 1; implicitHeight: 14; radius: 2; color: root.card("#22303d")
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: parent.height * parent.busy / 100; radius: 2; color: "#67dcec" }
                            }
                        }
                    }
                }
            }
            Graph {
                dashboard: root; compact: view.stacked; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: root.details ? 1.4 : 1
                heading: root.details ? "GPU · GFX power" : "GPU"; metric: root.details ? "gpuPower" : "gpu"; accent: "#b49afa"
                ceiling: root.details ? root.powerCeiling : 100; unit: root.details ? "W" : "%"
                valueText: root.details ? root.watts(root.inspected.gpuPower) : root.percent(root.inspected.gpu)
                detail: root.inspected.gpuTemp == null ? "Temperature unavailable" : root.inspected.gpuTemp.toFixed(0) + "°C · GFX"
                footer: root.details ? "AMD firmware readings · clocks and DRAM bandwidth" : "GFX " + root.watts(root.inspected.gpuPower) + "  ·  " + root.clock(root.inspected.gpuClock) + "  ·  Video " + root.percent(root.inspected.videoBusy)
                extra: root.details ? gpuStats : null
                lines: root.details ? "gpuPower" : "gpu"
                format: root.details ? (v => v.toFixed(1) + " W") : (v => v.toFixed(v < 10 ? 1 : 0) + "%")
                linesNote: root.details ? "Per app: estimated, its share of GPU time × GFX power" : "Per app: graphics and compute engine time"
                Component {
                    id: gpuStats
                    GridLayout {
                        columns: 3; columnSpacing: 12; rowSpacing: 10
                        Stat { Layout.fillWidth: true; label: "GFX clock"; value: root.clock(root.inspected.gpuClock) }
                        Stat { Layout.fillWidth: true; label: "SoC / fabric"; value: root.clock(root.inspected.socClock) + " / " + root.clock(root.inspected.fabricClock) }
                        Stat { Layout.fillWidth: true; label: "Video engine"; value: root.percent(root.inspected.videoBusy) }
                        Stat { Layout.fillWidth: true; label: "Memory clock"; value: root.clock(root.inspected.memClock) }
                        Stat { Layout.fillWidth: true; label: "DRAM read"; value: root.bandwidth(root.inspected.dramRead) }
                        Stat { Layout.fillWidth: true; label: "DRAM write"; value: root.bandwidth(root.inspected.dramWrite) }
                    }
                }
            }
            Graph {
                dashboard: root; compact: view.stacked; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: 1
                heading: root.details ? "GPU memory · GTT + VRAM" : "Memory"; metric: root.details ? "gtt" : "mem"; secondary: root.details ? "vram" : ""; accent: "#e8bf80"
                // With contributor lines the total is GTT and VRAM together, as each app's figure is.
                lines: root.details ? "gpumem" : "mem"
                combine: root.details
                format: v => root.bytes(v)
                linesNote: root.details ? "Per app: VRAM + GTT its GPU clients hold; the total line is both" : "Per app: resident memory; shared pages count for each app"
                ceiling: root.details ? (contributing ? (root.latest.gttTotal || 0) + (root.latest.vramTotal || 0) || 1 : Math.max(root.latest.gttTotal || 1, root.latest.vramTotal || 1)) : root.latest.memTotal || 1
                scaleText: root.bytes(ceiling)
                valueText: root.bytes(root.details ? (contributing ? (root.inspected.gtt || 0) + (root.inspected.vram || 0) : root.inspected.gtt) : root.inspected.mem)
                detail: root.details ? (contributing ? "GTT + VRAM used" : "GTT used · amber") : root.bytes(root.latest.memTotal) + " installed"
                footer: "VRAM " + root.bytes(root.inspected.vram) + " / " + root.bytes(root.inspected.vramTotal)
                        + "  ·  GTT " + root.bytes(root.inspected.gtt) + " / " + root.bytes(root.inspected.gttTotal)
                        + (root.details ? (contributing ? "\nGTT budget shares system RAM; it is not extra capacity." : "\nVRAM · blue. GTT budget shares system RAM; it is not extra capacity.") : "")
            }
            Graph {
                dashboard: root; compact: view.stacked; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: 1
                heading: root.details ? "APU · total power" : "Network"; metric: root.details ? "apuPower" : "down"; secondary: root.details ? "" : "up"; accent: "#75dfb4"
                lines: root.details ? "apuPower" : ""
                format: v => v.toFixed(1) + " W"
                linesNote: root.details ? "Per app: estimated, CPU share + GPU share; the rest of the chip is not shared out" : "No per-app network figures: the kernel keeps them to root"
                ceiling: root.details ? root.powerCeiling : root.netCeiling
                scaleText: root.details ? ceiling.toFixed(0) + " W" : root.bytes(ceiling) + "/s"
                valueText: root.details ? root.watts(root.inspected.apuPower) : root.bytes(root.inspected.down) + "/s ↓"
                detail: root.details ? "AMD SMU · package" : root.latest.interface || "Detecting interface…"
                footer: root.details ? "CPU cores " + root.watts(root.inspected.cpuPower) + "  ·  GFX " + root.watts(root.inspected.gpuPower)
                                       + "\nIndependent firmware readings; components need not sum to APU total."
                                     : "↓ Download · green     ↑ Upload · blue  /  " + root.bytes(root.inspected.up) + "/s ↑"
            }
        }
        GridLayout {
            id: footing
            Layout.fillWidth: true
            columns: view.mainWidth >= hint.implicitWidth + sampleCount.implicitWidth + 30 ? 2 : 1
            rowSpacing: 4
            Label { id: hint; text: view.desktop ? "Desktop layer · behind your windows  /  Hover a graph to inspect" : "Hover to inspect  ·  Space to pause  ·  F11 fullscreen  ·  Close to return to desktop"; font.pixelSize: 12; Layout.fillWidth: true }
            Label { id: sampleCount; text: root.history.length + " samples  /  session history"; font.pixelSize: 12; Layout.fillWidth: footing.columns === 1 }
        }
    }
    Sidebar { dashboard: view.dashboard; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: view.stacked ? 2 : -1 }
}
