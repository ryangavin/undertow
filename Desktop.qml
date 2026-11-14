import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

Scope {
    id: desktopRoot
    property var dashboard: null

    // Where windows sit is only in Hyprland's own report of them, which is not
    // kept current by itself: ask again when windows come, go, move or change
    // focus, and every ten seconds for resizes, which send no event.
    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (["openwindow", "closewindow", "movewindowv2", "changefloatingmode", "fullscreen", "workspacev2",
                 "focusedmonv2", "activewindowv2"].includes(event.name))
                refresh.restart();
        }
    }
    Timer { id: refresh; interval: 150; onTriggered: Hyprland.refreshToplevels() }
    Timer { interval: 10000; running: true; repeat: true; onTriggered: Hyprland.refreshToplevels() }
    Component.onCompleted: Hyprland.refreshToplevels()

    Variants {
        model: desktopRoot.dashboard ? Quickshell.screens : []
        PanelWindow {
            id: surface
            required property var modelData
            screen: modelData
            color: "transparent"
            anchors { top: true; bottom: true; left: true; right: true }
            // Kept out of the space the bar (or any panel) reserves, on
            // whichever edge it is docked, so the dashboard centres in what
            // is left: dead centre between the bar and the far edge. It
            // reserves none of its own.
            exclusionMode: ExclusionMode.Normal
            exclusiveZone: 0
            WlrLayershell.layer: WlrLayer.Bottom
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            // Hyprland blurs what is behind this surface by this name (a layer
            // rule in ~/.config/hypr/looknfeel.lua), as it does for the bar.
            WlrLayershell.namespace: "undertow-desktop"

            // A screen whose windows cover most of it (tiled ones fill it, a
            // big floating one can too) or that has a fullscreen window is
            // covered: the dashboard there would be drawn for nobody, and it
            // is the costliest thing Undertow does. Small floating windows
            // leave it showing. Without Hyprland (a check run) nothing is.
            readonly property var workspace: {
                const monitor = Hyprland.monitorFor(modelData);
                return monitor ? monitor.activeWorkspace : null;
            }
            readonly property bool covered: {
                if (!workspace) return false;
                if (workspace.hasFullscreen) return true;
                const left = modelData.x, top = modelData.y, right = left + modelData.width, bottom = top + modelData.height;
                let area = 0;
                for (const window of workspace.toplevels.values) {
                    const ipc = window.lastIpcObject;
                    if (!ipc || !ipc.at || !ipc.size || ipc.hidden) continue;
                    const w = Math.min(ipc.at[0] + ipc.size[0], right) - Math.max(ipc.at[0], left);
                    const h = Math.min(ipc.at[1] + ipc.size[1], bottom) - Math.max(ipc.at[1], top);
                    if (w > 0 && h > 0) area += w * h;
                }
                return area >= 0.75 * modelData.width * modelData.height;
            }
            // Shown at once when uncovered; put away only once it has stayed
            // covered a moment, so flicking through workspaces does not churn.
            property bool shown: true
            onCoveredChanged: { if (covered) hide.restart(); else { hide.stop(); shown = true; } }
            onShownChanged: console.log("Desktop dashboard on " + modelData.name + (shown ? ": shown" : ": put away, covered by windows"))
            Timer { id: hide; interval: 2000; onTriggered: surface.shown = !surface.covered }

            mask: Region { item: content.item ? content.item.board : null }
            Loader {
                id: content
                anchors.fill: parent
                active: surface.shown
                sourceComponent: Item {
                    readonly property alias board: desktopContent
                    Rectangle {
                        anchors.fill: desktopContent; anchors.margins: -18
                        radius: 24; color: Qt.rgba(0.043, 0.071, 0.110, desktopRoot.dashboard ? desktopRoot.dashboard.backdropAlpha : 0.81)
                    }
                    Dashboard {
                        id: desktopContent
                        anchors.centerIn: parent
                        // Wider than it used to be: the app table takes a third.
                        // A screen turned on its side gets its height too, with
                        // the app table beneath the graphs.
                        width: Math.min(parent.width - 80, 2400)
                        height: Math.min(parent.height - 110, parent.height > parent.width ? 2400 : 1100)
                        dashboard: desktopRoot.dashboard; desktop: true
                        // Hover animates the strip; history still updates at 1 Hz.
                        animate: false
                        onExpand: desktopRoot.dashboard.windowShown = true
                    }
                }
            }
        }
    }
}
