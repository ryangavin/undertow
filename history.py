"""The last hour of samples, kept in a file so a reload or a restart carries on where it left off."""
import json
import os
from pathlib import Path

KEEP_SECONDS = 3600
# Appends between trims: the file never grows much past the hour it keeps.
TRIM_EVERY = 600


def default_path():
    """In the session's runtime directory: memory-backed, private, and gone at logout."""
    chosen = os.environ.get("UNDERTOW_HISTORY")
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(chosen) if chosen else Path(runtime) / "undertow" / "history.jsonl"


class Store:
    def __init__(self, path, keep=KEEP_SECONDS, trim_every=TRIM_EVERY):
        self.path = Path(path)
        self.keep = keep
        self.trim_every = trim_every
        self.output = None
        self.appended = 0

    def recent(self, now):
        """Stored samples no older than the hour, oldest first, as the lines they were written as."""
        try:
            lines = self.path.read_text().splitlines()
        except (OSError, UnicodeError):
            return []
        kept = []
        for line in lines:
            try:
                when = json.loads(line)["time"]
                if now - self.keep <= when <= now:
                    kept.append(line)
            except (ValueError, KeyError, TypeError):
                continue  # a line cut short when the collector was stopped mid-write
        return kept

    def append(self, line, now):
        """Add one sample. A full disk or a missing directory costs the history, never the collector."""
        try:
            if self.output is None or self.appended >= self.trim_every:
                self._trim(now)
            self.output.write(line + "\n")
            self.output.flush()
            self.appended += 1
        except OSError:
            self.output = None

    def close(self):
        if self.output is not None:
            self.output.close()
            self.output = None

    def _trim(self, now):
        kept = self.recent(now)
        self.close()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        scratch = self.path.with_name(self.path.name + ".new")
        scratch.write_text("".join(line + "\n" for line in kept))
        os.replace(scratch, self.path)
        self.output = open(self.path, "a")
        self.appended = 0
