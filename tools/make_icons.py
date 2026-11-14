"""Writes Icons.js: process programs and names to Nerd Font glyphs, resolved from the installed font.

Run from the undertow folder: python3 tools/make_icons.py Icons.js (needs fontTools).
"""
import json, sys
from fontTools.ttLib import TTFont
cmap = TTFont("/usr/share/fonts/OTF/GeistMonoNerdFont-Regular.otf").getBestCmap()
glyphs = {name: cp for cp, name in cmap.items()}
MUTED, SYSTEM, KERNEL = "#8e9bb0", "#68788f", "#4f6276"
# Program or name (lower case) -> (glyph, colour). Colours are marks beside text, never text.
PROGRAMS = {
    # Coding agents
    "claude": ("cod-claude", "#d97757"), "codex": ("cod-openai", "#e5edf7"),
    "opencode": ("md-code_braces", "#75dfb4"), "opencode.exe": ("md-code_braces", "#75dfb4"), "pi": ("md-pi", "#e8bf80"),
    # Shells and terminals
    **{n: ("dev-terminal", MUTED) for n in ("zsh", "bash", "sh", "dash", "fish", "nu", "ghostty", "foot", "kitty", "alacritty")},
    "herdr-app": ("md-view_dashboard_variant", "#67dcec"), "herdr-core": ("md-console_network", "#67dcec"),
    "herdr": ("md-console_network", "#67dcec"),
    # Runtimes and dev tools
    **{n: ("dev-nodejs_small", "#7cc36e") for n in ("node", "node-mainthread", "npm", "npx", "pnpm", "yarn", "npm exec storyb", "npm run storybo", "npm run preview")},
    **{n: ("dev-python", "#f2c94c") for n in ("python", "python3", "pip")},
    "deno": ("dev-denojs", "#e5edf7"), "bun": ("dev-bun", "#f4e3c1"), "esbuild": ("md-lightning_bolt", "#ffcf00"),
    "vite": ("dev-vitejs", "#a685ff"), "storybook": ("dev-storybook", "#ff4785"), "astro": ("dev-astro", "#ff7e33"),
    "cargo": ("dev-rust", "#dea584"), "rustc": ("dev-rust", "#dea584"), "rust-analyzer": ("dev-rust", "#dea584"),
    "go": ("dev-go", "#6ad7e5"), "gopls": ("dev-go", "#6ad7e5"), "tsserver": ("dev-typescript", "#3987e5"),
    "git": ("dev-git", "#f05033"), "nvim": ("dev-vim", "#57a143"), "vim": ("dev-vim", "#57a143"), "code": ("dev-vscode", "#3987e5"),
    **{n: ("md-hammer_wrench", MUTED) for n in ("make", "cmake", "ninja", "gcc", "g++", "cc1", "cc1plus", "ld", "clang")},
    "ssh": ("md-ssh", MUTED), "sshd": ("md-ssh", SYSTEM),
    **{n: ("md-chart_line", MUTED) for n in ("btop", "htop", "top")},
    "big-red-synth": ("md-piano", "#e66767"),
    # Browsers
    "floorp": ("md-firefox", "#ff9a3d"), "firefox": ("md-firefox", "#ff9a3d"),
    **{n: ("dev-chrome", "#4f9cf5") for n in ("chrome", "chromium", "chrome-headless-shell", "chrome-headless", "headless_shell")},
    "playwright": ("dev-playwright", "#2ead33"),
    # Desktop
    "1password": ("md-key_variant", "#3b8bff"), "1password-crash-handler": ("md-key_variant", "#3b8bff"),
    "quickshell": ("md-monitor_dashboard", "#b49afa"), "qs": ("md-monitor_dashboard", "#b49afa"),
    "hyprland": ("linux-hyprland", "#58e1ff"), "start-hyprland": ("linux-hyprland", "#58e1ff"),
    "xwayland": ("linux-xorg", "#f28834"),
    **{n: ("md-waveform", "#75dfb4") for n in ("pipewire", "pipewire-pulse", "wireplumber", "qpwgraph")},
    "fcitx5": ("md-keyboard", MUTED), "voxtype": ("md-microphone", "#e66767"),
    "z13ctl": ("md-laptop", "#e8bf80"), "z13gui": ("md-laptop", "#e8bf80"),
    "wl-copy": ("md-clipboard_outline", MUTED), "wl-paste": ("md-clipboard_outline", MUTED),
    "sleep": ("md-sleep", MUTED), "waitpid": ("md-sleep", MUTED), "inotifywait": ("md-eye_outline", MUTED),
    "socat": ("md-swap_horizontal", MUTED), "socat1": ("md-swap_horizontal", MUTED), "journalctl": ("md-notebook", MUTED),
    "systemctl": ("md-cog_outline", MUTED), "systemd-inhibit": ("md-cog_outline", MUTED),
    "bwrap": ("md-package_variant", MUTED), "flatpak-session-helper": ("md-package_variant", MUTED),
    "xdg-dbus-proxy": ("md-package_variant", MUTED),
    "gnome-keyring-daemon": ("md-lock", MUTED), "p11-kit-server": ("md-lock", MUTED),
    "dconf-service": ("md-tune", MUTED), "localsearch-3": ("md-magnify", MUTED),
    "docker": ("dev-docker", "#1d91e6"), "dockerd": ("dev-docker", "#1d91e6"), "containerd": ("dev-docker", "#1d91e6"),
    # System services
    "systemd": ("md-cog", SYSTEM), "(sd-pam)": ("md-cog", SYSTEM), "systemd-journal": ("md-notebook", SYSTEM),
    "systemd-journald": ("md-notebook", SYSTEM), "systemd-resolve": ("md-dns", SYSTEM), "systemd-resolved": ("md-dns", SYSTEM),
    "systemd-oomd": ("md-memory", SYSTEM), "systemd-udevd": ("md-usb", SYSTEM), "systemd-logind": ("md-login", SYSTEM),
    "systemd-timesyn": ("md-clock_outline", SYSTEM), "systemd-timesyncd": ("md-clock_outline", SYSTEM),
    "sddm": ("md-login", SYSTEM), "sddm-helper": ("md-login", SYSTEM), "polkitd": ("md-shield_lock", SYSTEM),
    "networkmanager": ("md-wifi", SYSTEM), "wpa_supplicant": ("md-wifi", SYSTEM), "avahi-daemon": ("md-lan", SYSTEM),
    "bluetoothd": ("md-bluetooth", "#3987e5"), "bt-agent": ("md-bluetooth", "#3987e5"),
    "cupsd": ("md-printer", SYSTEM), "udisksd": ("md-harddisk", SYSTEM), "fusermount3": ("md-harddisk", SYSTEM),
    "upowerd": ("md-battery", SYSTEM), "fwupd": ("md-chip", SYSTEM), "passimd": ("md-chip", SYSTEM), "boltd": ("md-flash", SYSTEM),
    "accounts-daemon": ("md-account", SYSTEM), "rtkit-daemon": ("md-timer_outline", SYSTEM),
    "kthreadd": ("md-chip", KERNEL),
}
# Name beginnings for families with many members.
PREFIXES = [
    ("python", ("dev-python", "#f2c94c")), ("node", ("dev-nodejs_small", "#7cc36e")), ("chrome", ("dev-chrome", "#4f9cf5")),
    ("systemd", ("md-cog", SYSTEM)), ("dbus", ("md-transit_connection_variant", MUTED)), ("xdg-", ("md-door", MUTED)),
    ("gvfs", ("md-harddisk", MUTED)), ("at-spi", ("md-human", MUTED)), ("voxtype", ("md-microphone", "#e66767")),
    ("1password", ("md-key_variant", "#3b8bff")), ("pipewire", ("md-waveform", "#75dfb4")), ("herdr", ("md-console_network", "#67dcec")),
    ("vite", ("dev-vitejs", "#a685ff")), ("storybook", ("dev-storybook", "#ff4785")),
    ("web content", ("md-firefox", "#ff9a3d")), ("isolated web", ("md-firefox", "#ff9a3d")), ("rdd process", ("md-firefox", "#ff9a3d")),
]
FALLBACK = {"kernel": ("md-chip", KERNEL), "system": ("md-cog_outline", SYSTEM), "user": ("md-application_outline", MUTED)}
# Interface symbols, for chips and controls.
SYMBOLS = {"branch": "md-source_branch", "space": "md-view_grid_outline", "preview": "md-web",
           "model": "md-brain", "change": "md-file_tree", "running": "md-console_line", "pinned": "md-chip", "folder": "md-folder_outline",
           "open": "md-chevron_down", "closed": "md-chevron_right", "sum": "md-sigma",
           # An agent's state, GitHub-style: one coloured mark at the head of its row.
           "working": "md-play_circle", "blocked": "md-alert_circle", "done": "md-check_circle",
           "idle": "md-pause_circle", "unknown": "md-circle_outline"}

def code(name):
    return glyphs[name]

out = ['.pragma library', '',
       '// Made by tools/make_icons.py from GeistMono Nerd Font. Each entry: [code point, mark colour].',
       '// Glyph names (as in the font) are given beside each, so an entry can be checked or changed.',
       'const font = "GeistMono Nerd Font";', '',
       'const programs = {']
for key, (glyph, colour) in PROGRAMS.items():
    out.append(f'    {json.dumps(key)}: [0x{code(glyph):x}, "{colour}"],  // {glyph}')
out += ['};', '', 'const prefixes = [']
for prefix, (glyph, colour) in PREFIXES:
    out.append(f'    [{json.dumps(prefix)}, 0x{code(glyph):x}, "{colour}"],  // {glyph}')
out += ['];', '', 'const fallback = {']
for key, (glyph, colour) in FALLBACK.items():
    out.append(f'    {json.dumps(key)}: [0x{code(glyph):x}, "{colour}"],  // {glyph}')
out += ['};', '', 'const symbols = {']
for key, glyph in SYMBOLS.items():
    out.append(f'    {json.dumps(key)}: 0x{code(glyph):x},  // {glyph}')
out += ['};', '', '''// The mark for a process: its program first, then its name, then a name's
// beginning, then what kind of process it is.
function lookup(program, name, kind) {
    const keys = [String(program || "").toLowerCase(), String(name || "").toLowerCase()];
    for (const key of keys)
        if (programs[key]) return { glyph: String.fromCodePoint(programs[key][0]), color: programs[key][1] };
    for (const key of keys)
        for (const entry of prefixes)
            if (key.startsWith(entry[0])) return { glyph: String.fromCodePoint(entry[1]), color: entry[2] };
    const last = fallback[kind] || fallback.user;
    return { glyph: String.fromCodePoint(last[0]), color: last[1] };
}

function symbol(name) {
    return symbols[name] ? String.fromCodePoint(symbols[name]) : "";
}
''']
open(sys.argv[1], "w").write("\n".join(out))
print(len(PROGRAMS), "programs,", len(PREFIXES), "prefixes")
