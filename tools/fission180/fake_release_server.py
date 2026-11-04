#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Try "Update now" without publishing anything: a small stand-in for GitHub's releases list that
serves the files of a release made by a dry run of fission180-build.yml.

  1. Run "Fission 180 build" by hand on a branch (publish stays off). Its "release-files-..." artifact
     holds fission180-release.json, SHA256SUMS.txt, release-notes.md and the quick update zip. Download
     it and unzip it into a folder. (For the full-installer path, put the installer .exe from the
     build's "Fission180-Windows-installer-..." artifact in the same folder.)
  2. Start this server on the PC that has the OLDER Fission 180 installed. Fission 180's own Python does
     it, no other program needed:
         "C:\\Program Files\\Fission180\\bin\\python.exe" fake_release_server.py C:\\path\\to\\that\\folder
  3. Start the older Fission 180 with the address of this server (a PowerShell window):
         $env:FISSION180_UPDATE_API = "http://127.0.0.1:8765"
         & "C:\\Program Files\\Fission180\\bin\\Fission180.exe"
  4. In Fission 180: Help > Check for Updates > Update now.

The older Fission 180 must be older than the version in fission180-release.json. Only this computer can
reach the server (127.0.0.1). Nothing leaves it. Stop with Ctrl+C.
"""

import http.server
import json
import os
import sys
import urllib.parse

REPO = "Luca0422git/Fission-180"
MANIFEST = "fission180-release.json"


def build_listing(folder, base):
    """What GitHub's releases list would answer for the release in ``folder``: one entry whose
    assets are the files there, with addresses on ``base``. Raises ValueError with a plain
    sentence when the folder is not a release."""
    path = os.path.join(folder, MANIFEST)
    if not os.path.isfile(path):
        raise ValueError("%s is not in %s: unzip the dry run's release-files artifact there" % (MANIFEST, folder))
    with open(path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    tag, version = manifest.get("tag"), manifest.get("version")
    if not tag or not version:
        raise ValueError("%s has no tag and version" % MANIFEST)
    assets = []
    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if os.path.isfile(full) and not name.endswith(".md"):
            assets.append(
                {
                    "name": name,
                    "browser_download_url": "%s/dl/%s" % (base, urllib.parse.quote(name)),
                    "size": os.path.getsize(full),
                }
            )
    return [
        {
            "tag_name": tag,
            "draft": False,
            "prerelease": "-" in version,
            "html_url": manifest.get("notes_url") or "https://github.com/%s/releases/tag/%s" % (REPO, tag),
            "assets": assets,
        }
    ]


def make_server(folder, port, talk=False):
    """The web server (not started): port 0 picks a free one. Returns (server, base address,
    the releases list it answers)."""
    folder = os.path.abspath(folder)
    holder = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path == "/repos/%s/releases" % REPO:
                body, status = json.dumps(holder["listing"]).encode("utf-8"), 200
            elif url.path.startswith("/dl/"):
                name = os.path.basename(urllib.parse.unquote(url.path[4:]))
                full = os.path.join(folder, name)
                if os.path.isfile(full):
                    with open(full, "rb") as handle:
                        body, status = handle.read(), 200
                else:
                    body, status = b"not here", 404
            else:
                body, status = b"{}", 404
            if talk:
                print("[Fission 180] fake release server: %s -> %d" % (self.path, status), flush=True)
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    base = "http://127.0.0.1:%d" % server.server_address[1]
    holder["listing"] = build_listing(folder, base)
    return server, base, holder["listing"]


def serve(folder, port):
    server, base, listing = make_server(folder, port, talk=True)
    print(
        "[Fission 180] fake release server for %s on %s (Ctrl+C stops it)\n"
        "  start the older Fission 180 with FISSION180_UPDATE_API=%s" % (listing[0]["tag_name"], base, base),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    port = int(argv[2]) if len(argv) > 2 else 8765
    try:
        serve(argv[1], port)
    except ValueError as exc:
        print("[Fission 180] fake release server: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
