# SPDX-License-Identifier: LGPL-2.1-or-later
"""The small MCP server an AI app (Claude Desktop, Gemini CLI, Claude Code ...) starts to
reach Fission 180 (docs/fission180/dev/briefs/home-cloud-ai.md, section 4.4):

    python fission180_mcp.py [--bridge] [--bridge-file PATH]
    freecadcmd fission180_mcp.py --pass --headless [--allow-overwrite]

It speaks MCP over stdin / stdout (one JSON message per line, mcp_core.py). By default it
passes each tool call on to the AI bridge inside the running Fission 180 (bridge_core.py) over
127.0.0.1 with the key from bridge.json; it runs with FreeCAD's own Python, so nothing has to
be installed, but it never imports FreeCAD: Fission 180 does the work, this process only carries
messages. When Fission 180 is not reachable a call says so: it never switches to running the
tools itself. With --headless (under FreeCAD's command-line program, which
tools/fission180/fission180-cli finds) the tools run in this process instead, on designs opened
here (fission180/ai/headless.py). Logs go to stderr (stdout is only for MCP messages) and never
contain a key.

A reply that gets lost (the connection breaks, or Fission 180 takes too long) is handled
honestly: a read-only tool is asked again; a tool that changes the design is not, and the
answer says the change may or may not have been applied, so the AI checks the design first
(an idea from CADCraft, docs/fission180/dev/cadcraft-lessons.md idea 3).

Where bridge.json is: --bridge-file, else the FISSION180_BRIDGE_FILE environment variable,
else the first one found of the places Fission 180's user data folder can be (see
candidate_bridge_files), looked up again on every call because Fission 180 may start later.
"""

import argparse
import http.client
import json
import os
import queue
import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))  # <Mod>/Fission180, which holds fission180/
if sys.path and os.path.abspath(sys.path[0] or os.curdir) == _HERE:
    sys.path.pop(0)  # the script's own folder: its module names must not shadow others
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fission180.ai import bridge_core, catalog, mcp_core, progress, tools_core  # noqa: E402,F401

TIMEOUT = 120.0  # seconds; one design step can take a while to compute
# (wave 8, ai-speed) MCP progress notifications for a tools/call that asked for them (its
# params._meta.progressToken): the first after PROGRESS_FIRST seconds, then every
# PROGRESS_EVERY, with what Fission 180 says it is doing (the bridge's /status), until the
# answer goes out. The MCP specification (basic/utilities/progress, 2025-03-26 and later):
# progress must grow with every notification, total and message are optional, none after
# the answer. What AI apps do with them differs (docs/fission180/parity/ai.md, wave 8).
PROGRESS_FIRST = 1.0
PROGRESS_EVERY = 2.0
STATUS_TIMEOUT = 3.0  # seconds for /status and /stop (answered on the bridge's own thread)
ENV_BRIDGE_FILE = "FISSION180_BRIDGE_FILE"
RETRIES = 2  # a read-only tool whose reply was lost is asked again this many times
RETRY_WAIT = 0.5  # seconds before asking again
MAYBE_APPLIED = (
    "The answer from Fission 180 was lost (%s), so the change %s may or may not have been "
    "applied. Do not repeat it blindly: inspect the design first (inspect_design, or "
    "diff_design since a snapshot you took before), then decide."
)


class _LostReply(Exception):
    """The request reached Fission 180 (or may have) but its answer never came back.
    timed_out: no answer in time (Fission 180 busy), which asking again does not help."""

    def __init__(self, text, timed_out=False):
        Exception.__init__(self, text)
        self.timed_out = timed_out


def log(text):
    try:
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def _version():
    try:
        import fission180

        return fission180.__version__
    except Exception:
        return "0"


def _versioned(base):
    """base/v<major>-<minor> folders, newest first, then base itself."""
    found = []
    try:
        for name in os.listdir(base):
            parts = name[1:].split("-") if name.startswith("v") else []
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                found.append((int(parts[0]), int(parts[1]), name))
    except OSError:
        pass
    return [os.path.join(base, name) for _, _, name in sorted(found, reverse=True)] + [base]


def candidate_user_data_dirs(env=None, platform=None, home=None):
    """Where FreeCAD 1.1 puts the user data folder (App.getUserAppDataDir()), Fission 180's first.

    FreeCAD 1.1's layout (src/App/ApplicationDirectories.cpp, configurePaths lines 238-243,
    getStandardPaths lines 468-478, versionStringForPath lines 498-503,
    appendVersionIfPossible lines 163-191): <data home>/<ExeName>/v<major>-<minor>/ when that
    versioned folder exists, where data home is %APPDATA% on Windows, ~/Library/Application
    Support on macOS and $XDG_DATA_HOME or ~/.local/share on Linux; FREECAD_USER_DATA, when
    set, is used as it is (getCustomPaths). Fission 180's ExeName is "Fission180" with the vendor
    left out (src/Main/MainGui.cpp lines 189-193); stock FreeCAD's is "FreeCAD"."""
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    home = os.path.expanduser("~") if home is None else home
    result = []
    if env.get("FREECAD_USER_DATA"):
        result.append(env["FREECAD_USER_DATA"])
    if platform.startswith("win"):
        base = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    for app in ("Fission180", "FreeCAD"):
        result += _versioned(os.path.join(base, app))
    return result


def candidate_bridge_files(env=None, platform=None, home=None):
    return [bridge_core.bridge_path(d) for d in candidate_user_data_dirs(env, platform, home)]


def find_bridge_file(explicit=None, env=None):
    """The bridge file to use now: the given one, the environment's, or the first that
    exists (None when there is none yet)."""
    env = os.environ if env is None else env
    if explicit:
        return explicit
    if env.get(ENV_BRIDGE_FILE):
        return env[ENV_BRIDGE_FILE]
    for path in candidate_bridge_files(env):
        if os.path.isfile(path):
            return path
    return None


class BridgeClient:
    """Sends tool calls to Fission 180's bridge."""

    def __init__(self, bridge_file=None, timeout=TIMEOUT, retries=RETRIES, retry_wait=RETRY_WAIT):
        self.bridge_file = bridge_file
        self.timeout = timeout
        self.retries = retries
        self.retry_wait = retry_wait
        # 127.0.0.1 must never go through a proxy set in the environment (HTTP_PROXY ...)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call_tool(self, name, args, call_id=None):
        try:
            return self._call_honestly(name, args, call_id)
        except Exception as exc:
            log("[Fission 180] MCP: call %s failed: %s" % (name, exc))
            return bridge_core.error_result("Fission 180 could not run %s: %s" % (name, exc))

    def _bridge(self):
        path = find_bridge_file(self.bridge_file)
        info = bridge_core.read_bridge_file(path) if path else None
        if info is None or not bridge_core.pid_alive(info["pid"]):
            return None
        return info

    def _post(self, info, path, payload, timeout):
        request = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (info["port"], path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", bridge_core.KEY_HEADER: info["key"]},
            method="POST",
        )
        with self.opener.open(request, timeout=timeout) as response:
            return response.read()

    def status(self):
        """What Fission 180 is working on now (bridge_core.status_answer), or None when it
        cannot tell (not running, or a Fission 180 from before wave 8). Never raises."""
        try:
            info = self._bridge()
            if info is None:
                return None
            return bridge_core.decode_status(
                self._post(info, bridge_core.STATUS_PATH, {}, STATUS_TIMEOUT)
            )
        except Exception:
            return None

    def stop(self, call_id, reason="the AI app cancelled it"):
        """Ask Fission 180 to stop the call `call_id` (bridge._stop says when it does). The
        answer ({"stopped", "running"}) or None. Never raises."""
        try:
            info = self._bridge()
            if info is None:
                return None
            body = self._post(
                info, bridge_core.STOP_PATH, {"call_id": call_id, "reason": reason}, STATUS_TIMEOUT
            )
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    def _call_honestly(self, name, args, call_id=None):
        """A lost reply: read-only tools are asked again, changing tools never are."""
        read_only = catalog.is_read_only(name)
        attempt = 0
        while True:
            try:
                return self._call(name, args, call_id)
            except _LostReply as lost:
                # (not after a time-out: Fission 180 is busy, and asking again only queued
                # more work behind the long call: Luca's Relic design, 2026-11-13)
                if read_only and attempt < self.retries and not lost.timed_out:
                    attempt += 1
                    log("[Fission 180] MCP: %s: reply lost (%s), asking again" % (name, lost))
                    time.sleep(self.retry_wait)
                    continue
                if read_only and lost.timed_out:
                    return bridge_core.error_result(
                        "Fission 180 did not answer %s (%s): it is busy with a long call (or a "
                        "question waits for the person in Fission 180). It was not asked again, "
                        "which would only add to the wait: wait until Fission 180 responds, then "
                        "try again." % (name, lost)
                    )
                if read_only:
                    return bridge_core.error_result(
                        "Fission 180 did not answer %s (%s), also when asked again. Check that "
                        "Fission 180 is not busy, then try again." % (name, lost)
                    )
                return bridge_core.error_result(MAYBE_APPLIED % (lost, name))

    def _call(self, name, args, call_id=None):
        info = self._bridge()
        if info is None:
            return bridge_core.error_result(bridge_core.NOT_RUNNING)
        request = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (info["port"], bridge_core.CALL_PATH),
            data=bridge_core.encode_request(name, args, call_id),
            headers={"Content-Type": "application/json", bridge_core.KEY_HEADER: info["key"]},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:
                pass
            if exc.code == 403:
                return bridge_core.error_result(bridge_core.BAD_KEY)
            answer = bridge_core.decode_result(body)
            if answer["text"] == bridge_core.UNREADABLE:
                return bridge_core.error_result(
                    "Fission 180 answered with an error (HTTP %d)." % exc.code
                )
            answer["is_error"] = True
            return answer
        except (socket.timeout, TimeoutError):
            raise _LostReply(
                "no answer within %d seconds; it may still be working" % self.timeout, True
            )
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise _LostReply("no answer within %d seconds" % self.timeout, True)
            if isinstance(reason, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
                raise _LostReply("the connection broke")
            return bridge_core.error_result(bridge_core.NOT_RUNNING)  # refused: never sent
        except ConnectionRefusedError:
            return bridge_core.error_result(bridge_core.NOT_RUNNING)
        except (
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError,
            http.client.RemoteDisconnected,
            http.client.IncompleteRead,
            http.client.BadStatusLine,
        ) as exc:
            raise _LostReply("the connection broke: %s" % (exc.__class__.__name__,))
        except ConnectionError:
            return bridge_core.error_result(bridge_core.NOT_RUNNING)
        answer = bridge_core.decode_result(body)
        if answer["text"] == bridge_core.UNREADABLE and not body:
            raise _LostReply("an empty answer")
        return answer


def progress_token(message):
    """The progressToken a request asked for (params._meta.progressToken: a string or an
    integer), or None."""
    params = message.get("params") if isinstance(message, dict) else None
    meta = params.get("_meta") if isinstance(params, dict) else None
    token = meta.get("progressToken") if isinstance(meta, dict) else None
    if isinstance(token, bool) or not isinstance(token, (str, int)):
        return None
    return token


def progress_message(name, seconds, status, call_id):
    """The words of one progress notification for the call `call_id` (tool `name`) after
    `seconds`, from Fission 180's /status answer (None: it cannot tell)."""
    if status and status.get("working") and status.get("call_id") == call_id:
        doing = progress.doing_words(status.get("what"), status.get("done"), status.get("total"))
        head = "Fission 180 is %s %s (%s)" % (
            "stopping" if status.get("stopping") else "working on",
            name,
            progress.seconds_words(seconds),
        )
        return head + (": " + doing if doing else "")
    if status and status.get("working"):
        return "Fission 180 is still busy with %s (%s); %s waits for it (%s)" % (
            status.get("tool") or "another call",
            progress.seconds_words(status.get("seconds") or 0),
            name,
            progress.seconds_words(seconds),
        )
    return "Fission 180: %s (%s)" % (name, progress.seconds_words(seconds))


class _Progress(threading.Thread):
    """Sends progress notifications for one tool call until finish() (never after it)."""

    def __init__(self, server, active):
        threading.Thread.__init__(self, name="fission180-mcp-progress", daemon=True)
        self.server = server
        self.active = active
        self.gate = threading.Lock()
        self.over = threading.Event()
        self.began = time.monotonic()
        self.sent = 0.0  # the progress value of the last notification (it must grow)
        self.count = 0

    def run(self):
        wait = PROGRESS_FIRST
        while not self.over.wait(wait):
            wait = PROGRESS_EVERY
            try:
                status = self.server.status() if self.server.status is not None else None
            except Exception:
                status = None
            seconds = time.monotonic() - self.began
            text = progress_message(self.active["name"], seconds, status, self.active["call_id"])
            with self.gate:
                if self.over.is_set():
                    return
                self.sent = max(round(seconds, 1), round(self.sent + 0.1, 1))
                self.count += 1
                self.server.send(
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/progress",
                        "params": {
                            "progressToken": self.active["token"],
                            "progress": self.sent,
                            "message": text,
                        },
                    }
                )

    def finish(self):
        with self.gate:
            self.over.set()


class Server:
    """Reads MCP messages from stdin and writes answers to stdout. Tool calls run one at a
    time on a worker thread (Fission 180 does one step at a time anyway) so pings and
    tools/list are answered while a step computes.

    status() -> what Fission 180 is doing (BridgeClient.status) and stop(call_id, reason)
    (BridgeClient.stop), when given: a tools/call that asked for progress gets notifications
    while it runs, and one the AI app cancels while Fission 180 works on it is stopped there
    when it changes nothing (bridge._stop). call_ids: call_tool takes call_id= (each call's
    own id, which a stop names)."""

    def __init__(self, call_tool, stdin, stdout, version, status=None, stop=None, call_ids=False):
        self.call_tool = call_tool
        self.stdin = stdin
        self.stdout = stdout
        self.version = version
        self.status = status
        self.stop = stop
        self.call_ids = call_ids
        self.lock = threading.Lock()
        self.jobs = queue.Queue()
        self.cancelled = set()  # ids of tool calls the AI app cancelled (notifications/cancelled)
        self.active = None  # the tools/call being worked on: {id, call_id, name, token, cancelled}
        self.session = secrets.token_hex(4)  # (call ids unique across servers on one bridge)
        self.inline_sent = 0.0  # headless: when the last progress notification went
        self.worker = threading.Thread(target=self._work, name="fission180-mcp-calls", daemon=True)

    def send(self, message):
        if message is None:
            return
        data = mcp_core.encode(message)
        with self.lock:
            try:
                self.stdout.write(data)
                self.stdout.flush()
            except Exception as exc:
                log("[Fission 180] MCP: could not write an answer: %s" % exc)

    def answer(self, message):
        self.send(mcp_core.handle(message, self.call_tool, self.version, log))

    def _work(self):
        while True:
            message = self.jobs.get()
            if message is None:
                return
            with self.lock:
                ident = message.get("id")
                skip = ident in self.cancelled
                self.cancelled.discard(ident)
            if skip:  # (the AI app gave up on it: not sent to Fission 180, and not answered)
                log("[Fission 180] MCP: call %s cancelled by the AI app, not run" % (ident,))
                continue
            self.tool_call(message)

    def tool_call(self, message):
        """One tools/call: answered (with progress notifications while it runs when it asked
        for them), or not answered when the AI app cancelled it meanwhile (MCP: a cancelled
        request gets no answer)."""
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        ident = message.get("id")
        active = {
            "id": ident,
            "call_id": "%s-%s" % (self.session, ident),
            "name": params.get("name") if isinstance(params.get("name"), str) else "the call",
            "token": progress_token(message),
            "cancelled": False,
        }
        with self.lock:
            self.active = active
        ticker = None
        if active["token"] is not None and self.status is not None:
            ticker = _Progress(self, active)
            ticker.start()
        call_id = active["call_id"]

        def call(name, args):
            if self.call_ids:
                return self.call_tool(name, args, call_id=call_id)
            return self.call_tool(name, args)

        try:
            reply = mcp_core.handle(message, call, self.version, log)
        finally:
            if ticker is not None:
                ticker.finish()
            with self.lock:
                self.active = None
                cancelled = active["cancelled"]
                self.cancelled.discard(ident)
        if cancelled:
            log("[Fission 180] MCP: call %s was cancelled by the AI app: no answer" % (ident,))
            return
        self.send(reply)

    def cancel(self, message):
        """notifications/cancelled: a tool call still waiting here is not run (MCP: no answer
        is sent for it). One Fission 180 is working on is asked to stop there (bridge._stop:
        a call that changes nothing stops at its next safe point; a change is left to
        finish, so its result is there when the AI looks) and gets no answer either."""
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        ident = params.get("requestId")
        if ident is None:
            return
        with self.lock:
            if len(self.cancelled) > 1000:  # (ids of calls answered long ago)
                self.cancelled.clear()
            self.cancelled.add(ident)
            active = self.active if self.active is not None and self.active["id"] == ident else None
            if active is not None:
                active["cancelled"] = True
        if active is not None and self.stop is not None:
            reason = params.get("reason")
            why = "the AI app cancelled it" + (
                " (%s)" % reason if isinstance(reason, str) and reason else ""
            )
            threading.Thread(
                target=self._stop_there, args=(active["call_id"], why), daemon=True
            ).start()

    def _stop_there(self, call_id, why):
        try:
            answer = self.stop(call_id, why)
            log("[Fission 180] MCP: asked Fission 180 to stop %s: %s" % (call_id, answer))
        except Exception as exc:
            log("[Fission 180] MCP: could not ask Fission 180 to stop %s: %s" % (call_id, exc))

    def inline_progress(self, call):
        """Headless (the tools run on this thread): progress's pump sends the progress
        notification the call in work asked for, at most every PROGRESS_EVERY seconds."""
        active = self.active
        if active is None or active["token"] is None:
            return
        now = time.monotonic()
        seconds = now - call["started"]
        if seconds < PROGRESS_FIRST or now - self.inline_sent < PROGRESS_EVERY:
            return
        self.inline_sent = now
        status = bridge_core.status_answer(progress.current())
        status["call_id"] = active["call_id"]
        self.send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/progress",
                "params": {
                    "progressToken": active["token"],
                    "progress": round(seconds, 3),
                    "message": progress_message(active["name"], seconds, status, active["call_id"]),
                },
            }
        )

    def run_in_line(self):
        """Every message in turn on this thread (headless: FreeCAD runs the tools here, and
        FreeCAD wants its own thread)."""
        while True:
            try:
                line = self.stdin.readline()
            except Exception as exc:
                log("[Fission 180] MCP: reading stdin failed: %s" % exc)
                break
            if not line:
                break
            try:
                message, error = mcp_core.parse_line(line)
                if error is not None:
                    self.send(error)
                elif isinstance(message, dict) and message.get("method") == "tools/call":
                    self.tool_call(message)
                elif message is not None:
                    self.answer(message)
            except Exception as exc:
                log("[Fission 180] MCP: could not handle a message: %s" % exc)

    def run(self):
        # wave 8, ai-behaviour: a call on the worker may ask the AI app (ask_person's form)
        mcp_core.set_sender(self.send, self.cancelled)
        self.worker.start()
        while True:
            try:
                line = self.stdin.readline()
            except Exception as exc:
                log("[Fission 180] MCP: reading stdin failed: %s" % exc)
                break
            if not line:
                break  # EOF: the AI app closed the connection
            try:
                message, error = mcp_core.parse_line(line)
                if error is not None:
                    self.send(error)
                elif isinstance(message, dict) and message.get("method") == "tools/call":
                    self.jobs.put(message)
                elif (
                    isinstance(message, dict) and message.get("method") == "notifications/cancelled"
                ):
                    self.cancel(message)
                elif message is not None:
                    self.answer(message)
            except Exception as exc:
                log("[Fission 180] MCP: could not handle a message: %s" % exc)
        self.jobs.put(None)
        self.worker.join(TIMEOUT + 5)


def _arguments(argv):
    """Our arguments (FreeCAD's command-line program passes them after --pass)."""
    return [a for a in argv if a != "--pass"]


def main(argv=None, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(description="Fission 180's MCP server (stdio).")
    parser.add_argument("--bridge-file", help="path of Fission 180's bridge.json")
    parser.add_argument(
        "--bridge",
        action="store_true",
        help="forward the tools to the running Fission 180 (the default)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="run the tools in this process (needs FreeCAD's command-line program)",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="headless: tools may replace files that exist",
    )
    raw = sys.argv[1:] if argv is None else argv
    if argv is None:
        for i, item in enumerate(sys.argv):  # under freecadcmd: what follows this file
            if os.path.abspath(item) == os.path.abspath(__file__):
                raw = sys.argv[i + 1 :]
                break
    options = parser.parse_args(_arguments(raw))
    if options.headless and (options.bridge or options.bridge_file):
        log("[Fission 180] MCP: --headless runs the tools here; it takes no bridge options")
        return 2
    if options.headless:
        return _main_headless(options, stdin, stdout)
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    client = BridgeClient(options.bridge_file)
    log("[Fission 180] MCP server %s started" % _version())
    try:
        Server(
            client.call_tool,
            stdin,
            stdout,
            _version(),
            status=client.status,
            stop=client.stop,
            call_ids=True,
        ).run()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log("[Fission 180] MCP server stopped: %s" % exc)
        return 1
    log("[Fission 180] MCP server stopped")
    return 0


def _main_headless(options, stdin=None, stdout=None):
    try:
        import FreeCAD  # noqa: F401
    except ImportError:
        log(
            "[Fission 180] MCP: --headless needs FreeCAD: start it with tools/fission180/fission180-cli "
            "mcp --headless (or freecadcmd fission180_mcp.py --pass --headless)"
        )
        return 2
    from fission180.ai import headless

    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else headless.take_stdout()
    client = headless.InProcessClient(headless.HeadlessHost(options.allow_overwrite))
    log("[Fission 180] MCP server %s started (headless: the tools run here)" % _version())
    try:
        server = Server(client.call_tool, stdin, stdout, _version())
        progress.set_pump(server.inline_progress)  # (no window: only the notifications)
        server.run_in_line()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log("[Fission 180] MCP server stopped: %s" % exc)
        return 1
    log("[Fission 180] MCP server stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
elif len(sys.argv) > 1 and os.path.abspath(sys.argv[1]) == os.path.abspath(__file__):
    _code = main()  # run as a script by FreeCAD's command-line program
    try:
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(_code or 0)
