import QtQuick

Rectangle {
    id: chip
    property string text: ""
    property bool selected: false
    // How opaque its fill is: the dashboard passes its panels' see-through.
    property real alpha: 1
    readonly property color fill: selected ? "#293b4c" : mouse.containsMouse ? "#202b38" : "#151e2a"
    signal clicked()
    implicitWidth: caption.implicitWidth + 26
    implicitHeight: 34
    radius: 8
    color: Qt.rgba(fill.r, fill.g, fill.b, selected ? Math.max(alpha, 0.85) : alpha)
    border.color: selected ? "#467283" : "#263140"
    Label { id: caption; anchors.centerIn: parent; text: chip.text; color: chip.selected ? "#b8f1ed" : "#a1aec0" }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: chip.clicked() }
}
