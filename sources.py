"""Notice when Undertow's own files change, so a save is picked up without a restart by hand."""
import hashlib
import os


def fingerprint(folder):
    """What identifies each QML and Python source right now.

    Size, modification time and inode together change whether a file is
    rewritten in place or replaced by a new one of the same name. Tests are
    left out: nothing running was loaded from them.
    """
    found = {}
    for entry in os.scandir(folder):
        if entry.name.endswith(QML + (".py",)) and not entry.name.startswith("test_") and entry.is_file():
            info = entry.stat()
            found[entry.name] = (info.st_mtime_ns, info.st_size, info.st_ino)
    return found


def changed(before, after):
    """Names added, removed or rewritten between two fingerprints."""
    return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


# What the app itself loads: its QML, the JavaScript the QML imports, and
# compiled shaders (a rebuilt .qsb needs a reload to be used).
QML = (".qml", ".js", ".qsb")


def only(found, ending):
    return {name: identity for name, identity in found.items() if name.endswith(ending)}


def digest(found):
    """A fingerprint as a short string that can be handed from one run of the app to the next."""
    return hashlib.sha1(repr(sorted(found.items())).encode()).hexdigest()


class Watch:
    """Says when the files on disk are no longer the ones that are running.

    What is running was loaded at two different moments, so there are two
    things to compare against. The Python is this collector's own: `loaded`
    is the fingerprint taken before its modules were read. The QML belongs to
    the app that started us, which loaded it before we existed: `loaded_qml`
    is the digest it was handed by the collector that asked for that reload.
    Comparing against the moment we started instead would miss a file saved
    while the app was still loading, and leave old and new code running
    together.

    A change is reported once the files have held still between two looks, so
    several files saved together are picked up together and none half written.
    """

    def __init__(self, folder, loaded=None, loaded_qml=None, read=fingerprint):
        self.folder = folder
        self.read = read
        self.seen = loaded if loaded is not None else read(folder)
        self.python = only(self.seen, ".py")
        self.qml_files = only(self.seen, QML)
        self.qml = loaded_qml or digest(self.qml_files)

    def poll(self):
        """(digest of the QML to reload to, or None; whether our own Python changed)."""
        now = self.read(self.folder)
        settled = now == self.seen
        self.seen = now
        if not settled:
            return None, False
        qml = digest(only(now, QML))
        reload_to = qml if qml != self.qml else None
        # Asked for once: if the reload fails, the next save asks again.
        self.qml = qml
        return reload_to, only(now, ".py") != self.python

    def qml_changes(self):
        """Names for the log: the QML that differs from what we first saw."""
        names = changed(self.qml_files, only(self.seen, QML))
        self.qml_files = only(self.seen, QML)
        return sorted(names) or ["saved while the app was loading"]
