import QtQuick
import QtQuick.Layouts

GridLayout {
    id: grid
    required property var sample
    required property var dashboard
    // Beside the app table a cell is too narrow for "C12 · 13.1 W" on one
    // line: the core and its watts move to opposite ends, without the unit.
    readonly property bool compact: width < 8 * 76
    columns: 8; columnSpacing: 5; rowSpacing: 5
    // A count, not the array: each new sample updates the cells in place.
    Repeater {
        model: (grid.sample.corePower || []).length
        Rectangle {
            required property int index
            readonly property var modelData: (grid.sample.corePower || [])[index]
            Layout.fillWidth: true; Layout.preferredWidth: 1; implicitHeight: 49
            color: grid.dashboard.card("#1b2937"); radius: 5
            Column {
                anchors.fill: parent; anchors.margins: 5; spacing: 2
                Label { visible: !grid.compact; width: parent.width; text: "C" + index + " · " + grid.dashboard.watts(modelData); color: "#b9eaf2"; font.pixelSize: 11 }
                Item {
                    visible: grid.compact; width: parent.width; height: reading.implicitHeight
                    Label { id: core; anchors.left: parent.left; anchors.baseline: reading.baseline; text: "C" + index; font.pixelSize: 9 }
                    Label {
                        id: reading
                        anchors.right: parent.right; width: parent.width - core.implicitWidth - 2; horizontalAlignment: Text.AlignRight
                        text: modelData == null ? "—" : modelData.toFixed(1); color: "#b9eaf2"; font.pixelSize: 11
                        fontSizeMode: Text.HorizontalFit; minimumPixelSize: 8; elide: Text.ElideNone
                    }
                }
                Label {
                    width: parent.width; text: grid.dashboard.clock((grid.sample.coreClock || [])[index]); font.pixelSize: 10
                    fontSizeMode: grid.compact ? Text.HorizontalFit : Text.FixedSize; minimumPixelSize: 8; elide: grid.compact ? Text.ElideNone : Text.ElideRight
                }
                Rectangle { height: 2; radius: 1; width: parent.width * Math.min(1, (modelData || 0) / 10); color: "#67dcec" }
            }
        }
    }
}
