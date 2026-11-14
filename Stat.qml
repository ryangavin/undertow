import QtQuick
import QtQuick.Layouts

ColumnLayout {
    property string label
    property string value
    spacing: 3
    Label { text: parent.label; font.pixelSize: 11; Layout.fillWidth: true }
    Label { text: parent.value; color: "#dce7f6"; font.pixelSize: 15; Layout.fillWidth: true }
}
