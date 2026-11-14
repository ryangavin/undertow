import QtQuick
import "Icons.js" as Icons

// The mark for a process, app or agent: a Nerd Font glyph in its own colour.
// Colour carries identity beside the name; the name is always there too.
//
// Icon fonts size and place their glyphs as their designers chose: some are
// twice as wide as others, some sit high, some small. So each glyph's drawn
// outline is measured, scaled to fill the same square, and centred in it.
Item {
    id: icon
    property string program
    property string name
    property string kind: "user"
    // The square every mark fits: its longer side is this long. Callers that
    // set `font.pixelSize`, as for a Text, get a square of that size.
    property font font: Qt.font({ pixelSize: 14 })
    property real size: font.pixelSize
    readonly property var look: Icons.lookup(program, name, kind)
    implicitWidth: size
    implicitHeight: size

    // Measured large, so the outline is exact, then scaled down to the square.
    readonly property int reference: 64
    TextMetrics { id: ink; font.family: Icons.font; font.pixelSize: icon.reference; text: icon.look.glyph }
    readonly property rect bounds: ink.tightBoundingRect
    readonly property real fit: bounds.width > 0 && bounds.height > 0 ? icon.size / Math.max(bounds.width, bounds.height) : icon.size / icon.reference

    // Drawn at its real size, the nearest whole pixel to the fit: drawing it
    // large and scaling it down looks the same but costs more every frame.
    readonly property int pixels: Math.max(1, Math.round(reference * fit))
    readonly property real ratio: pixels / reference
    Text {
        id: glyph
        text: icon.look.glyph
        color: icon.look.color
        font.family: Icons.font
        font.pixelSize: icon.pixels
        // The outline's centre lands on the square's centre.
        x: icon.width / 2 - (icon.bounds.x + icon.bounds.width / 2) * icon.ratio
        y: icon.height / 2 - glyph.baselineOffset - (icon.bounds.y + icon.bounds.height / 2) * icon.ratio
    }
}
