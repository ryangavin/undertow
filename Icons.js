.pragma library

// Made by tools/make_icons.py from GeistMono Nerd Font. Each entry: [code point, mark colour].
// Glyph names (as in the font) are given beside each, so an entry can be checked or changed.
const font = "GeistMono Nerd Font";

const programs = {
    "claude": [0xec82, "#d97757"],  // cod-claude
    "codex": [0xec81, "#e5edf7"],  // cod-openai
    "opencode": [0xf0169, "#75dfb4"],  // md-code_braces
    "opencode.exe": [0xf0169, "#75dfb4"],  // md-code_braces
    "pi": [0xf03ff, "#e8bf80"],  // md-pi
    "zsh": [0xe795, "#8e9bb0"],  // dev-terminal
    "bash": [0xe795, "#8e9bb0"],  // dev-terminal
    "sh": [0xe795, "#8e9bb0"],  // dev-terminal
    "dash": [0xe795, "#8e9bb0"],  // dev-terminal
    "fish": [0xe795, "#8e9bb0"],  // dev-terminal
    "nu": [0xe795, "#8e9bb0"],  // dev-terminal
    "ghostty": [0xe795, "#8e9bb0"],  // dev-terminal
    "foot": [0xe795, "#8e9bb0"],  // dev-terminal
    "kitty": [0xe795, "#8e9bb0"],  // dev-terminal
    "alacritty": [0xe795, "#8e9bb0"],  // dev-terminal
    "herdr-app": [0xf0843, "#67dcec"],  // md-view_dashboard_variant
    "herdr-core": [0xf08a9, "#67dcec"],  // md-console_network
    "herdr": [0xf08a9, "#67dcec"],  // md-console_network
    "node": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "node-mainthread": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "npm": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "npx": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "pnpm": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "yarn": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "npm exec storyb": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "npm run storybo": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "npm run preview": [0xe718, "#7cc36e"],  // dev-nodejs_small
    "python": [0xe73c, "#f2c94c"],  // dev-python
    "python3": [0xe73c, "#f2c94c"],  // dev-python
    "pip": [0xe73c, "#f2c94c"],  // dev-python
    "deno": [0xe7c0, "#e5edf7"],  // dev-denojs
    "bun": [0xe76f, "#f4e3c1"],  // dev-bun
    "esbuild": [0xf140b, "#ffcf00"],  // md-lightning_bolt
    "vite": [0xe8d7, "#a685ff"],  // dev-vitejs
    "storybook": [0xe8b3, "#ff4785"],  // dev-storybook
    "astro": [0xe735, "#ff7e33"],  // dev-astro
    "cargo": [0xe7a8, "#dea584"],  // dev-rust
    "rustc": [0xe7a8, "#dea584"],  // dev-rust
    "rust-analyzer": [0xe7a8, "#dea584"],  // dev-rust
    "go": [0xe724, "#6ad7e5"],  // dev-go
    "gopls": [0xe724, "#6ad7e5"],  // dev-go
    "tsserver": [0xe8ca, "#3987e5"],  // dev-typescript
    "git": [0xe702, "#f05033"],  // dev-git
    "nvim": [0xe7c5, "#57a143"],  // dev-vim
    "vim": [0xe7c5, "#57a143"],  // dev-vim
    "code": [0xe8da, "#3987e5"],  // dev-vscode
    "make": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "cmake": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "ninja": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "gcc": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "g++": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "cc1": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "cc1plus": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "ld": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "clang": [0xf1323, "#8e9bb0"],  // md-hammer_wrench
    "ssh": [0xf08c0, "#8e9bb0"],  // md-ssh
    "sshd": [0xf08c0, "#68788f"],  // md-ssh
    "btop": [0xf012a, "#8e9bb0"],  // md-chart_line
    "htop": [0xf012a, "#8e9bb0"],  // md-chart_line
    "top": [0xf012a, "#8e9bb0"],  // md-chart_line
    "big-red-synth": [0xf067d, "#e66767"],  // md-piano
    "floorp": [0xf0239, "#ff9a3d"],  // md-firefox
    "firefox": [0xf0239, "#ff9a3d"],  // md-firefox
    "chrome": [0xe743, "#4f9cf5"],  // dev-chrome
    "chromium": [0xe743, "#4f9cf5"],  // dev-chrome
    "chrome-headless-shell": [0xe743, "#4f9cf5"],  // dev-chrome
    "chrome-headless": [0xe743, "#4f9cf5"],  // dev-chrome
    "headless_shell": [0xe743, "#4f9cf5"],  // dev-chrome
    "playwright": [0xe863, "#2ead33"],  // dev-playwright
    "1password": [0xf030b, "#3b8bff"],  // md-key_variant
    "1password-crash-handler": [0xf030b, "#3b8bff"],  // md-key_variant
    "quickshell": [0xf0a07, "#b49afa"],  // md-monitor_dashboard
    "qs": [0xf0a07, "#b49afa"],  // md-monitor_dashboard
    "hyprland": [0xf359, "#58e1ff"],  // linux-hyprland
    "start-hyprland": [0xf359, "#58e1ff"],  // linux-hyprland
    "xwayland": [0xf369, "#f28834"],  // linux-xorg
    "pipewire": [0xf147d, "#75dfb4"],  // md-waveform
    "pipewire-pulse": [0xf147d, "#75dfb4"],  // md-waveform
    "wireplumber": [0xf147d, "#75dfb4"],  // md-waveform
    "qpwgraph": [0xf147d, "#75dfb4"],  // md-waveform
    "fcitx5": [0xf030c, "#8e9bb0"],  // md-keyboard
    "voxtype": [0xf036c, "#e66767"],  // md-microphone
    "z13ctl": [0xf0322, "#e8bf80"],  // md-laptop
    "z13gui": [0xf0322, "#e8bf80"],  // md-laptop
    "wl-copy": [0xf014c, "#8e9bb0"],  // md-clipboard_outline
    "wl-paste": [0xf014c, "#8e9bb0"],  // md-clipboard_outline
    "sleep": [0xf04b2, "#8e9bb0"],  // md-sleep
    "waitpid": [0xf04b2, "#8e9bb0"],  // md-sleep
    "inotifywait": [0xf06d0, "#8e9bb0"],  // md-eye_outline
    "socat": [0xf04e1, "#8e9bb0"],  // md-swap_horizontal
    "socat1": [0xf04e1, "#8e9bb0"],  // md-swap_horizontal
    "journalctl": [0xf082e, "#8e9bb0"],  // md-notebook
    "systemctl": [0xf08bb, "#8e9bb0"],  // md-cog_outline
    "systemd-inhibit": [0xf08bb, "#8e9bb0"],  // md-cog_outline
    "bwrap": [0xf03d6, "#8e9bb0"],  // md-package_variant
    "flatpak-session-helper": [0xf03d6, "#8e9bb0"],  // md-package_variant
    "xdg-dbus-proxy": [0xf03d6, "#8e9bb0"],  // md-package_variant
    "gnome-keyring-daemon": [0xf033e, "#8e9bb0"],  // md-lock
    "p11-kit-server": [0xf033e, "#8e9bb0"],  // md-lock
    "dconf-service": [0xf062e, "#8e9bb0"],  // md-tune
    "localsearch-3": [0xf0349, "#8e9bb0"],  // md-magnify
    "docker": [0xe7b0, "#1d91e6"],  // dev-docker
    "dockerd": [0xe7b0, "#1d91e6"],  // dev-docker
    "containerd": [0xe7b0, "#1d91e6"],  // dev-docker
    "systemd": [0xf0493, "#68788f"],  // md-cog
    "(sd-pam)": [0xf0493, "#68788f"],  // md-cog
    "systemd-journal": [0xf082e, "#68788f"],  // md-notebook
    "systemd-journald": [0xf082e, "#68788f"],  // md-notebook
    "systemd-resolve": [0xf01d6, "#68788f"],  // md-dns
    "systemd-resolved": [0xf01d6, "#68788f"],  // md-dns
    "systemd-oomd": [0xf035b, "#68788f"],  // md-memory
    "systemd-udevd": [0xf0553, "#68788f"],  // md-usb
    "systemd-logind": [0xf0342, "#68788f"],  // md-login
    "systemd-timesyn": [0xf0150, "#68788f"],  // md-clock_outline
    "systemd-timesyncd": [0xf0150, "#68788f"],  // md-clock_outline
    "sddm": [0xf0342, "#68788f"],  // md-login
    "sddm-helper": [0xf0342, "#68788f"],  // md-login
    "polkitd": [0xf099d, "#68788f"],  // md-shield_lock
    "networkmanager": [0xf05a9, "#68788f"],  // md-wifi
    "wpa_supplicant": [0xf05a9, "#68788f"],  // md-wifi
    "avahi-daemon": [0xf0317, "#68788f"],  // md-lan
    "bluetoothd": [0xf00af, "#3987e5"],  // md-bluetooth
    "bt-agent": [0xf00af, "#3987e5"],  // md-bluetooth
    "cupsd": [0xf042a, "#68788f"],  // md-printer
    "udisksd": [0xf02ca, "#68788f"],  // md-harddisk
    "fusermount3": [0xf02ca, "#68788f"],  // md-harddisk
    "upowerd": [0xf0079, "#68788f"],  // md-battery
    "fwupd": [0xf061a, "#68788f"],  // md-chip
    "passimd": [0xf061a, "#68788f"],  // md-chip
    "boltd": [0xf0241, "#68788f"],  // md-flash
    "accounts-daemon": [0xf0004, "#68788f"],  // md-account
    "rtkit-daemon": [0xf051b, "#68788f"],  // md-timer_outline
    "kthreadd": [0xf061a, "#4f6276"],  // md-chip
};

const prefixes = [
    ["python", 0xe73c, "#f2c94c"],  // dev-python
    ["node", 0xe718, "#7cc36e"],  // dev-nodejs_small
    ["chrome", 0xe743, "#4f9cf5"],  // dev-chrome
    ["systemd", 0xf0493, "#68788f"],  // md-cog
    ["dbus", 0xf0d3d, "#8e9bb0"],  // md-transit_connection_variant
    ["xdg-", 0xf081a, "#8e9bb0"],  // md-door
    ["gvfs", 0xf02ca, "#8e9bb0"],  // md-harddisk
    ["at-spi", 0xf02e6, "#8e9bb0"],  // md-human
    ["voxtype", 0xf036c, "#e66767"],  // md-microphone
    ["1password", 0xf030b, "#3b8bff"],  // md-key_variant
    ["pipewire", 0xf147d, "#75dfb4"],  // md-waveform
    ["herdr", 0xf08a9, "#67dcec"],  // md-console_network
    ["vite", 0xe8d7, "#a685ff"],  // dev-vitejs
    ["storybook", 0xe8b3, "#ff4785"],  // dev-storybook
    ["web content", 0xf0239, "#ff9a3d"],  // md-firefox
    ["isolated web", 0xf0239, "#ff9a3d"],  // md-firefox
    ["rdd process", 0xf0239, "#ff9a3d"],  // md-firefox
];

const fallback = {
    "kernel": [0xf061a, "#4f6276"],  // md-chip
    "system": [0xf08bb, "#68788f"],  // md-cog_outline
    "user": [0xf0614, "#8e9bb0"],  // md-application_outline
};

const symbols = {
    "branch": 0xf062c,  // md-source_branch
    "space": 0xf11d9,  // md-view_grid_outline
    "preview": 0xf059f,  // md-web
    "model": 0xf09d1,  // md-brain
    "change": 0xf0645,  // md-file_tree
    "running": 0xf07b7,  // md-console_line
    "pinned": 0xf061a,  // md-chip
    "folder": 0xf0256,  // md-folder_outline
    "open": 0xf0140,  // md-chevron_down
    "closed": 0xf0142,  // md-chevron_right
    "sum": 0xf04a0,  // md-sigma
    "working": 0xf040c,  // md-play_circle
    "blocked": 0xf0028,  // md-alert_circle
    "done": 0xf05e0,  // md-check_circle
    "idle": 0xf03e5,  // md-pause_circle
    "unknown": 0xf0766,  // md-circle_outline
};

// The mark for a process: its program first, then its name, then a name's
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
