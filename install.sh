#!/bin/sh
# Install Undertow for the current user.
#
#   ./install.sh            copy the app into place (a normal install)
#   ./install.sh --link     link the app to this checkout instead, so a saved
#                           edit here reloads the running app (for working on it)
#   ./install.sh --uninstall
#
# Installs the app as Quickshell config "undertow", the `undertow` launcher in
# ~/.local/bin and an app launcher entry. Nothing needs root.
set -eu

here=$(cd "$(dirname "$0")" && pwd -P)
config_home=${XDG_CONFIG_HOME:-$HOME/.config}
data_home=${XDG_DATA_HOME:-$HOME/.local/share}
app_dir=$config_home/quickshell/undertow
bin_dir=$HOME/.local/bin
launcher=$bin_dir/undertow
desktop=$data_home/applications/undertow.desktop
marker=.installed-by-undertow

mode=copy
case "${1:-}" in
    "") ;;
    --link) mode=link ;;
    --uninstall) mode=uninstall ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

say() { printf '%s\n' "$*"; }

# Whether $app_dir is something this installer put there (a copy carrying the
# marker, or a link), as opposed to a folder someone made by hand.
ours() {
    [ -L "$app_dir" ] || [ -e "$app_dir/$marker" ]
}

# Make way for a new install at $app_dir. A hand-made folder is kept as a
# dated backup beside it rather than deleted.
clear_app_dir() {
    if [ -L "$app_dir" ]; then
        rm "$app_dir"
    elif [ -d "$app_dir" ]; then
        if ours; then
            rm -rf "$app_dir"
        else
            backup=$config_home/quickshell/.undertow.bak.$(date +%Y%m%d%H%M%S)
            mv "$app_dir" "$backup"
            say "Kept the existing $app_dir as $backup"
        fi
    elif [ -e "$app_dir" ]; then
        echo "$app_dir exists and is not a folder; move it and try again" >&2
        exit 1
    fi
}

write_desktop() {
    mkdir -p "$(dirname "$desktop")"
    cat > "$desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Undertow
Comment=Live CPU, GPU, memory and network currents
Exec=$launcher
Icon=utilities-system-monitor
Terminal=false
Categories=System;Monitor;
Keywords=performance;cpu;gpu;memory;network;graphs;
EOF
    command -v update-desktop-database >/dev/null 2>&1 &&
        update-desktop-database -q "$(dirname "$desktop")" 2>/dev/null || true
}

if [ "$mode" = uninstall ]; then
    if ours; then
        quickshell ipc --config undertow call undertow quit >/dev/null 2>&1 || true
        rm -rf "$app_dir"
        say "Removed $app_dir"
    elif [ -e "$app_dir" ]; then
        say "Left $app_dir: it was not installed by this script"
    fi
    for f in "$launcher" "$desktop"; do
        [ -e "$f" ] || [ -L "$f" ] && rm "$f" && say "Removed $f"
    done
    say "Undertow's autostart line and blur rule, if you added them, are still in your Hyprland config."
    exit 0
fi

for need in quickshell python3; do
    command -v "$need" >/dev/null 2>&1 || say "Note: $need is not installed; Undertow needs it to run."
done

mkdir -p "$config_home/quickshell" "$bin_dir"
clear_app_dir

if [ "$mode" = link ]; then
    ln -s "$here" "$app_dir"
    ln -sf "$here/bin/undertow" "$launcher"
    say "Linked $app_dir -> $here"
    say "Saved edits in $here reload the running app."
else
    mkdir -p "$app_dir/tools"
    for f in "$here"/*.qml "$here"/*.js "$here"/*.py "$here"/*.frag "$here"/*.qsb "$here"/README.md; do
        cp "$f" "$app_dir/"
    done
    cp "$here"/tools/*.py "$app_dir/tools/"
    : > "$app_dir/$marker"
    rm -f "$launcher"
    cp "$here/bin/undertow" "$launcher"
    chmod 755 "$launcher"
    say "Installed Undertow to $app_dir"
fi
write_desktop
say "Installed $launcher and $desktop"

# Starting with Hyprland, and the blur behind the dashboard, are lines in the
# user's own Hyprland config: say what to add rather than editing it.
if ! grep -rqs 'config undertow' "$config_home/hypr" 2>/dev/null; then
    cat <<'EOF'

To start Undertow with Hyprland, add to your autostart:
    quickshell --config undertow --no-duplicate
For the frosted blur behind it, add a layer rule for the namespace
"undertow-desktop" with blur on (ignore_alpha 0.2), as for your bar.
EOF
fi

# A running Undertow loaded the files it was started from; a copy install
# replaces them with new files, which it notices and reloads within seconds.
