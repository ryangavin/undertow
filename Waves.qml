import QtQuick

// The interference strip: reactive art, not a chart. Each reading drives the
// amplitude of one wave; all four share a common swell; the pointer bends
// them. Drawn on the GPU by waves.frag, so following every sample, or
// animating, costs the CPU no more than handing the shader a few numbers.
Rectangle {
    id: field
    required property var dashboard
    property bool moving: true
    property real phase: 0
    property real cursor: -1
    readonly property bool hovered: pointer.containsMouse
    radius: 16; color: field.dashboard.card("#101a25"); border.color: "#263140"
    clip: true
    // The latest reading of each, as 0 to 1: CPU, GPU, memory and network.
    readonly property var latest: {
        const samples = field.dashboard.source;
        return samples.length ? samples[samples.length - 1] : {};
    }
    ShaderEffect {
        anchors.fill: parent
        property vector2d size: Qt.vector2d(width, height)
        property real phase: field.phase
        property real cursor: field.cursor
        property vector4d levels: Qt.vector4d((field.latest.cpu || 0) / 100, (field.latest.gpu || 0) / 100,
                                              (field.latest.mem || 0) / (field.latest.memTotal || 1),
                                              Math.min(1, (field.latest.down || 0) / field.dashboard.netCeiling))
        fragmentShader: "waves.frag.qsb"
    }
    Timer { interval: 50; running: field.moving; repeat: true; onTriggered: field.phase += 0.045 }
    MouseArea { id: pointer; anchors.fill: parent; hoverEnabled: true; onPositionChanged: mouse => field.cursor = mouse.x / width; onExited: field.cursor = -1 }
    Label { x: 20; y: 14; text: "INTERFERENCE"; font.pixelSize: 11; font.letterSpacing: 2; color: "#9eafc5" }
    Label { anchors.right: parent.right; anchors.rightMargin: 20; y: 14; text: "Reactive art · normalized amplitudes · move your pointer"; font.pixelSize: 11 }
}
