# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT > Insert Catalogue Part...: the rules, without Qt or FreeCAD (unit tested).

Fusion's Insert McMaster-Carr Component is that company's online catalogue in a window: you
find the part, pick STEP, and the file is downloaded and dropped into the design at the origin
with Move. Fission 180 embeds nobody's catalogue (their data, their terms, and Fission 180
needs no cloud): the catalogue stays the supplier's own website, opened in the person's own
web browser, and Fission 180 does the second half: it takes the STEP (or IGES) file the person
downloaded and inserts it as a component, then Move.

Here: the short list of suppliers (a name and an address; the person can change it), the
address a part number makes, and which file in the Downloads folder is "the one I just
downloaded". Nothing here goes online.
"""

import json
import os
from urllib.parse import quote

# A name and its website. "{}" is where a part number or search words go (left out when
# nothing was typed). Only addresses: no data of theirs is in Fission 180.
DEFAULT_SUPPLIERS = (
    ("McMaster-Carr", "https://www.mcmaster.com/{}"),
    ("MISUMI", "https://us.misumi-ec.com/vona2/result/?Keyword={}"),
    ("TraceParts", "https://www.traceparts.com/en/search?Keywords={}"),
)
EXTENSIONS = (".step", ".stp", ".iges", ".igs")
INFO = (
    "The catalogue is the supplier's own website: find the part there, download its 3D "
    "model as STEP, then insert the file here."
)


class CatalogueError(ValueError):
    """Said in the dialog."""


def clean_address(address):
    """An address a web browser opens: "https://" put in front of a bare host name. Only
    web addresses (http, https) are taken."""
    address = (address or "").strip()
    if not address:
        raise CatalogueError("Give the supplier's web address (https://...).")
    if "://" not in address:
        address = "https://" + address
    if not address.lower().startswith(("https://", "http://")):
        raise CatalogueError("Only a web address (https://...) can be opened.")
    if any(c.isspace() for c in address):
        raise CatalogueError("A web address has no spaces.")
    return address


def clean_suppliers(rows):
    """[(name, address)] kept as given, the unusable rows (no name, no web address) and the
    repeated names dropped."""
    found, seen = [], set()
    for row in rows or []:
        try:
            name, address = (str(v).strip() for v in row)
            address = clean_address(address)
        except (CatalogueError, TypeError, ValueError):
            continue
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        found.append((name, address))
    return found


def load_suppliers(text):
    """The supplier list from its saved text (JSON); the default list when there is none or
    it cannot be read."""
    try:
        rows = clean_suppliers(json.loads(text)) if text else []
    except (TypeError, ValueError):
        rows = []
    return rows or list(DEFAULT_SUPPLIERS)


def dump_suppliers(rows):
    return json.dumps([list(r) for r in clean_suppliers(rows)])


def address_for(address, words=""):
    """The address to open: the supplier's, with the part number or search words where its
    "{}" is (the part of the address from "{}" on is left out when nothing was typed and
    the "{}" stands in a question)."""
    address = clean_address(address)
    words = (words or "").strip()
    if "{}" not in address:
        return address
    if words:
        return address.replace("{}", quote(words, safe=""))
    head, _, _tail = address.partition("{}")
    if "?" in head:
        head = head.split("?", 1)[0]
    return head


def downloads_folder(env=None, saved="", standard=""):
    """Where downloaded files are looked for: FISSION180_DOWNLOADS (the tests), else the
    folder the person browsed to last, else the system's Downloads folder, else
    ~/Downloads."""
    env = os.environ if env is None else env
    for candidate in (env.get("FISSION180_DOWNLOADS", ""), saved, standard):
        if candidate and os.path.isdir(candidate):
            return candidate
    return os.path.join(os.path.expanduser("~"), "Downloads")


def downloaded_files(folder, limit=12):
    """The STEP / IGES files of a folder, newest first: [(path, time changed)]. A browser's
    unfinished download (.crdownload, .part) has another ending and is left out."""
    found = []
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if not entry.name.lower().endswith(EXTENSIONS):
                    continue
                try:
                    if entry.is_file() and entry.stat().st_size > 0:
                        found.append((entry.path, entry.stat().st_mtime))
                except OSError:
                    continue
    except OSError:
        return []
    found.sort(key=lambda f: (-f[1], f[0]))
    return found[:limit]


def age_text(seconds):
    """ "just now", "5 min ago", "3 h ago", "2 days ago"."""
    seconds = max(0.0, float(seconds))
    if seconds < 90:
        return "just now"
    if seconds < 3600 * 1.5:
        return "%d min ago" % round(seconds / 60.0)
    if seconds < 86400 * 1.5:
        return "%d h ago" % round(seconds / 3600.0)
    return "%d days ago" % round(seconds / 86400.0)


def file_label(path, changed, now):
    return "%s  (%s)" % (os.path.basename(path), age_text(now - changed))
