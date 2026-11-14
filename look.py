"""How see-through the desktop's windows are, so Undertow's panels can match them.

Omarchy's Window Opacity setting (Appearance > Windows) has three modes:
opaque, transparent (the default) and glassy. The windows it makes see-through
carry the "transparent-window" tag, and take the opacity Omarchy gives that
tag, or the one the user's Hyprland config gives it instead. The opaque mode
makes them solid; glassy blurs what is behind them and thins terminal
backgrounds further. A panel on the desktop is never focused, so it matches
the unfocused figure. No third-party dependencies.
"""
import os
import re
from pathlib import Path

TOGGLES = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "omarchy" / "toggles" / "hypr"
HYPR = Path.home() / ".config" / "hypr"
OMARCHY = Path(os.environ.get("OMARCHY_PATH") or "/usr/share/omarchy")
# A rule for the tag: o.window({ tag = "transparent-window" }, { opacity = "0.94 0.90" })
RULE = re.compile(r'tag\s*=\s*"transparent-window"\s*\}\s*,\s*\{[^}]*?opacity\s*=\s*"([\d.]+)\s+([\d.]+)"')
# Omarchy's own: o.window(match, { opacity = opacity or "0.985 0.96", ... })
DEFAULT = re.compile(r'opacity\s+or\s+"([\d.]+)\s+([\d.]+)"')
# Glassy is meant to read as glass; Omarchy's glassy GTK apps are 0.75.
GLASSY = 0.8


def mode(toggles=TOGGLES):
    """"opaque", "glassy" or "transparent", as omarchy-hyprland-window-transparency reports it."""
    if (toggles / "window-opaque.lua").is_file():
        return "opaque"
    if (toggles / "window-glassy.lua").is_file():
        return "glassy"
    return "transparent"


def uncommented(text):
    """Lua source without its -- comments, so an example in a comment is not taken for a rule."""
    return "\n".join(line.split("--", 1)[0] for line in text.splitlines())


def unfocused(hypr=HYPR, omarchy=OMARCHY):
    """The opacity an unfocused see-through window has: the user's rule for the tag, else Omarchy's."""
    found = 0.96
    try:
        match = DEFAULT.search((omarchy / "default" / "hypr" / "helpers.lua").read_text())
        if match:
            found = float(match.group(2))
    except (OSError, UnicodeError):
        pass
    for path in sorted(hypr.glob("*.lua")):
        try:
            rules = RULE.findall(uncommented(path.read_text()))
        except (OSError, UnicodeError):
            continue
        if rules:
            found = float(rules[-1][1])
    return max(0.0, min(1.0, found))


def look(toggles=TOGGLES, hypr=HYPR, omarchy=OMARCHY):
    """{"mode", "alpha"}: how opaque Undertow's panels should be to match the windows."""
    chosen = mode(toggles)
    if chosen == "opaque":
        return {"mode": chosen, "alpha": 1.0}
    alpha = unfocused(hypr, omarchy)
    return {"mode": chosen, "alpha": round(min(alpha, GLASSY) if chosen == "glassy" else alpha, 3)}
