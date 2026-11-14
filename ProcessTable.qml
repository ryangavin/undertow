import QtQuick
import QtQuick.Layouts
import "Icons.js" as Icons

// A table of processes, apps or agents, shared by every list in the sidebar.
// Each row is an object:
//   key          unique within the table
//   name, suffix the name, and muted words after it ("×14", "+3")
//   program, kind  what picks its icon (see Icons.js)
//   depth        indentation, for trees
//   expandable, expanded  draws the disclosure arrow
//   badge        optional {text, color}: a status pill after the name
//   state        optional {symbol, color}: a coloured state mark in place of
//                the icon, GitHub-style (see the symbols in Icons.js)
//   chips        optional [{symbol | icon: {program, name, kind}, text, tint, meter}]:
//                a line of small labelled pills beneath the name; `meter`
//                (0 to 1) draws a short gauge in the pill
//   lines        optional extra lines of muted text beneath those
//   ...          anything `reading` turns into a cell
// The rows arrive in the order to show them; the table only draws.
Item {
    id: table
    property var columns: []      // {key, title, width, tint}
    property var rows: []
    property string order: "cpu"  // the column the rows are ranked by, if any
    property var reading: (row, key) => String(row[key] === undefined ? "" : row[key])
    property bool tree: false     // leaves room for disclosure arrows
    property string emptyText: "Nothing to show"
    readonly property int rowHeight: 20
    readonly property int lineHeight: 15
    readonly property int chipHeight: 20
    readonly property var ranking: columns.find(column => column.key === order) || null
    // The bar behind a row compares it with the most in the ranked column.
    // Trees go without: a parent holds all below it, so the bars say nothing.
    readonly property real peak: {
        if (!ranking || !ranking.tint || tree) return 0;
        let most = 0;
        for (const row of shown) most = Math.max(most, row[order] || 0);
        return most;
    }
    function heightOf(row) {
        if (!row) return rowHeight;
        const extra = (row.lines || []).length, chips = (row.chips || []).length ? 1 : 0;
        return rowHeight + chips * chipHeight + extra * lineHeight + (extra || chips ? 6 : 0);
    }
    // Rows, even in the moment before whoever fills the table has any.
    readonly property var shown: rows || []
    // Where each row starts. Only the rows in view get drawn: a fixed pool of
    // them, moved along as the view scrolls, so a long list costs no more
    // than a short one and new figures update rows instead of rebuilding them.
    readonly property var tops: {
        const out = [0];
        for (const row of shown) out.push(out[out.length - 1] + heightOf(row));
        return out;
    }
    readonly property int first: {
        let low = 0, high = shown.length;
        while (low < high) { const mid = (low + high) >> 1; if (tops[mid + 1] <= view.contentY) low = mid + 1; else high = mid; }
        return low;
    }
    readonly property int pool: Math.ceil(view.height / rowHeight) + 2
    signal activated(var row)
    signal toggled(var row)
    signal ranked(string key)

    component Heading: Label {
        id: heading
        property string key
        font.pixelSize: 10; font.letterSpacing: 1.5
        color: table.order === key ? "#b8f1ed" : pick.containsMouse ? "#9eafc5" : "#68788f"
        MouseArea { id: pick; anchors.fill: parent; anchors.margins: -5; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: table.ranked(heading.key) }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        RowLayout {
            spacing: 8; Layout.bottomMargin: 6; Layout.rightMargin: 8
            Heading { key: "name"; text: "NAME"; Layout.fillWidth: true; Layout.leftMargin: table.tree ? 14 : 0 }
            Repeater {
                model: table.columns
                Heading { required property var modelData; key: modelData.key; text: modelData.title; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: modelData.width }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#263140" }
        Flickable {
            id: view
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.topMargin: 4
            clip: true
            contentHeight: body.height
            boundsBehavior: Flickable.StopAtBounds
            Item {
                id: body
                width: view.width - 8
                height: table.tops[table.tops.length - 1]
                Label { visible: table.shown.length === 0; text: table.emptyText; font.pixelSize: 11; color: "#68788f"; height: table.rowHeight; verticalAlignment: Text.AlignVCenter }
                Repeater {
                    model: table.pool
                    Item {
                        id: line
                        required property int index
                        readonly property int at: table.first + index
                        readonly property var row: table.shown[at] || ({})
                        readonly property var extra: row.lines || []
                        readonly property var chips: row.chips || []
                        readonly property real indent: (row.depth || 0) * 14
                        visible: at < table.shown.length
                        y: table.tops[at] || 0
                        width: body.width
                        height: table.heightOf(row)
                        Rectangle {
                            anchors.fill: parent; anchors.leftMargin: -6; anchors.rightMargin: -6; radius: 4
                            color: "#1d2a38"; visible: hover.containsMouse
                        }
                        // How this row compares with the top of the ranked column.
                        Rectangle {
                            visible: table.peak > 0
                            x: -6; y: 1; height: table.rowHeight - 2; radius: 4
                            width: table.peak > 0 ? (parent.width + 12) * Math.min(1, (line.row[table.order] || 0) / table.peak) : 0
                            color: table.ranking ? table.ranking.tint || "transparent" : "transparent"; opacity: 0.11
                        }
                        MouseArea {
                            id: hover
                            anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: mouse => {
                                if (line.row.expandable && mouse.x < line.indent + 16) table.toggled(line.row);
                                else table.activated(line.row);
                            }
                        }
                        RowLayout {
                            x: 0; width: parent.width; height: table.rowHeight; spacing: 8
                            Text {
                                visible: table.tree
                                text: line.row.expandable ? Icons.symbol(line.row.expanded ? "open" : "closed") : ""
                                font.family: Icons.font; font.pixelSize: 11; color: "#68788f"
                                Layout.leftMargin: line.indent; Layout.preferredWidth: 10
                            }
                            Item {
                                implicitWidth: 16; implicitHeight: 16; Layout.leftMargin: table.tree ? -4 : 0
                                ProcessIcon { visible: !line.row.state; anchors.centerIn: parent; program: line.row.program || ""; name: line.row.name || ""; kind: line.row.kind || "user" }
                                // A state mark: one glyph, its colour saying the state.
                                Text {
                                    visible: !!line.row.state; anchors.centerIn: parent
                                    text: line.row.state ? Icons.symbol(line.row.state.symbol) : ""
                                    color: line.row.state ? line.row.state.color : "transparent"
                                    font.family: Icons.font; font.pixelSize: 15
                                }
                            }
                            // The name takes what it needs; its suffix and badge follow it,
                            // and only when all of that does not fit does the name give way.
                            Item {
                                id: naming
                                Layout.fillWidth: true; implicitHeight: table.rowHeight
                                readonly property real after: (suffix.visible ? suffix.implicitWidth + 6 : 0) + (badge.visible ? badge.width + 6 : 0)
                                Label { id: title; text: line.row.name || ""; color: "#dce7f6"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; width: Math.max(30, Math.min(implicitWidth, naming.width - naming.after)) }
                                Label { id: suffix; text: line.row.suffix || ""; font.pixelSize: 11; color: "#68788f"; visible: text.length > 0; x: title.width + 6; anchors.verticalCenter: parent.verticalCenter }
                                Rectangle {
                                    id: badge
                                    visible: !!line.row.badge
                                    x: title.width + 6 + (suffix.visible ? suffix.implicitWidth + 6 : 0); anchors.verticalCenter: parent.verticalCenter
                                    width: pill.implicitWidth + 12; height: 15; radius: 7.5
                                    color: "transparent"; border.color: line.row.badge ? line.row.badge.color : "transparent"
                                    Label { id: pill; anchors.centerIn: parent; text: line.row.badge ? line.row.badge.text : ""; font.pixelSize: 10; color: "#c3cfdd" }
                                }
                            }
                            Repeater {
                                model: table.columns
                                Label {
                                    required property var modelData
                                    text: line.visible ? table.reading(line.row, modelData.key) : ""
                                    color: table.order === modelData.key ? "#dce7f6" : "#8e9bb0"
                                    font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: modelData.width
                                }
                            }
                        }
                        Column {
                            x: line.indent + (table.tree ? 34 : 24); y: table.rowHeight + 2
                            width: parent.width - x
                            // Chips: each detail a small pill with its own icon and tint,
                            // most telling first. One that does not fit whole is left out,
                            // rather than cut off at the edge.
                            Item {
                                id: chipLine
                                visible: line.chips.length > 0
                                width: parent.width; height: table.chipHeight
                                    Repeater {
                                        id: chipItems
                                        model: line.chips.length
                                        Rectangle {
                                            id: chip
                                            required property int index
                                            readonly property var info: line.chips[index] || ({ text: "" })
                                            readonly property color tint: info.tint || "#8e9bb0"
                                            // Laid out by hand: after the chips before it that are shown.
                                            x: {
                                                let at = 0;
                                                for (let i = 0; i < index; i++) {
                                                    const before = chipItems.itemAt(i);
                                                    if (before && before.visible) at += before.width + 5;
                                                }
                                                return at;
                                            }
                                            visible: x + width <= chipLine.width
                                            anchors.verticalCenter: parent.verticalCenter
                                            height: 17; radius: 8.5
                                            width: chipContent.implicitWidth + 14
                                            color: Qt.rgba(tint.r, tint.g, tint.b, info.tint ? 0.12 : 0.06)
                                            border.color: Qt.rgba(tint.r, tint.g, tint.b, info.tint ? 0.42 : 0.22)
                                            Row {
                                                id: chipContent
                                                x: 7; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                                                // Only a chip with a program's mark builds one.
                                                Loader {
                                                    active: !!chip.info.icon; visible: active; anchors.verticalCenter: parent.verticalCenter
                                                    sourceComponent: ProcessIcon {
                                                        size: 10
                                                        program: chip.info.icon ? chip.info.icon.program || "" : ""
                                                        name: chip.info.icon ? chip.info.icon.name || "" : ""
                                                        kind: chip.info.icon ? chip.info.icon.kind || "user" : "user"
                                                    }
                                                }
                                                Text {
                                                    visible: !chip.info.icon && !!chip.info.symbol; anchors.verticalCenter: parent.verticalCenter
                                                    text: Icons.symbol(chip.info.symbol || ""); font.family: Icons.font; font.pixelSize: 11; color: chip.tint
                                                }
                                                // A long detail ends in an ellipsis rather than taking the line.
                                                Label { text: chip.info.text || ""; font.pixelSize: 10; color: "#c3cfdd"; width: Math.min(implicitWidth, 150); anchors.verticalCenter: parent.verticalCenter }
                                                // A short gauge, for a share such as how full a context is.
                                                Rectangle {
                                                    visible: chip.info.meter !== undefined && chip.info.meter !== null
                                                    width: 22; height: 4; radius: 2; color: "#263140"; anchors.verticalCenter: parent.verticalCenter
                                                    Rectangle { width: parent.width * Math.min(1, Math.max(0, chip.info.meter || 0)); height: 4; radius: 2; color: chip.tint }
                                                }
                                            }
                                        }
                                    }
                            }
                            Repeater {
                                model: line.extra.length
                                Label { required property int index; text: line.extra[index] || ""; width: parent.width; height: table.lineHeight; font.pixelSize: 11; color: "#8e9bb0" }
                            }
                        }
                    }
                }
            }
        }
    }
    // Where the view sits in a list longer than the card.
    Rectangle {
        visible: view.contentHeight > view.height
        anchors.right: parent.right
        y: view.y + view.height * (view.contentY / Math.max(1, view.contentHeight))
        width: 3; radius: 1.5; color: "#3a4a5e"
        height: Math.max(20, view.height * view.height / Math.max(1, view.contentHeight))
    }
}
