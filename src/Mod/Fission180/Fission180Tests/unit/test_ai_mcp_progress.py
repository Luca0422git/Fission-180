# SPDX-License-Identifier: LGPL-2.1-or-later
"""The MCP server's side of a long call (wave 8, ai-speed): progress notifications while
Fission 180 works on a call that asked for them, a cancel passed on to Fission 180, the bridge's
/status and /stop messages (fission180/ai/fission180_mcp.py, bridge_core.py). Runs without
FreeCAD."""

import json
import os
import queue
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180.ai import bridge_core, fission180_mcp, progress  # noqa: E402

WAIT = 20.0


class _Stdin:
    def __init__(self):
        self.lines = queue.Queue()

    def put(self, message):
        self.lines.put((json.dumps(message) + "\n").encode("utf-8"))

    def readline(self):
        line = self.lines.get()
        return line or b""

    def close(self):
        self.lines.put(None)


class _Stdout:
    def __init__(self):
        self.messages = queue.Queue()
        self.all = []
        self.lock = threading.Lock()

    def write(self, data):
        for line in data.decode("utf-8").splitlines():
            if line.strip():
                message = json.loads(line)
                with self.lock:
                    self.all.append(message)
                self.messages.put(message)

    def flush(self):
        pass

    def until(self, test, what):
        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            try:
                message = self.messages.get(timeout=0.1)
            except queue.Empty:
                continue
            if test(message):
                return message
        raise AssertionError("no %s in %s" % (what, self.all))


class Fission180Fake:
    """A Fission 180 that works on one call for `seconds` and says what it is doing."""

    def __init__(self, seconds=3.0):
        self.seconds = seconds
        self.calls = []
        self.stops = []
        self.running = None
        self.release = threading.Event()

    def call_tool(self, name, args, call_id=None):
        self.calls.append((name, call_id))
        self.running = {"tool": name, "call_id": call_id, "started": time.monotonic()}
        try:
            self.release.wait(self.seconds)
        finally:
            self.running = None
        return bridge_core.result("done %s" % name)

    def status(self):
        live = self.running
        if live is None:
            return {"working": False}
        return {
            "working": True,
            "tool": live["tool"],
            "call_id": live["call_id"],
            "seconds": time.monotonic() - live["started"],
            "what": "comparing faces",
            "done": 1200,
            "total": 3209,
        }

    def stop(self, call_id, reason):
        self.stops.append((call_id, reason))
        self.release.set()
        return {"stopped": True, "running": True}


class ProgressNotifications(unittest.TestCase):
    def setUp(self):
        self.saved = (fission180_mcp.PROGRESS_FIRST, fission180_mcp.PROGRESS_EVERY)
        fission180_mcp.PROGRESS_FIRST, fission180_mcp.PROGRESS_EVERY = 0.2, 0.3
        self.stdin, self.stdout = _Stdin(), _Stdout()
        self.fake = Fission180Fake()
        self.server = fission180_mcp.Server(
            self.fake.call_tool,
            self.stdin,
            self.stdout,
            "test",
            status=self.fake.status,
            stop=self.fake.stop,
            call_ids=True,
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

    def tearDown(self):
        fission180_mcp.PROGRESS_FIRST, fission180_mcp.PROGRESS_EVERY = self.saved
        self.fake.release.set()
        self.stdin.close()
        self.thread.join(WAIT)

    def call(self, ident, name, token=None):
        params = {"name": name, "arguments": {}}
        if token is not None:
            params["_meta"] = {"progressToken": token}
        self.stdin.put({"jsonrpc": "2.0", "id": ident, "method": "tools/call", "params": params})

    def test_notifications_while_it_works_and_none_after(self):
        self.fake.seconds = 1.5
        self.call(1, "compare_to_reference", token="tok-1")
        answer = self.stdout.until(lambda m: m.get("id") == 1, "answer")
        notes = [m for m in self.stdout.all if m.get("method") == "notifications/progress"]
        self.assertGreaterEqual(len(notes), 2, notes)
        values = [n["params"]["progress"] for n in notes]
        self.assertEqual(values, sorted(set(values)), "progress must grow every time")
        self.assertTrue(all(n["params"]["progressToken"] == "tok-1" for n in notes))
        self.assertIn(
            "Fission 180 is working on compare_to_reference", notes[-1]["params"]["message"]
        )
        self.assertIn("comparing faces 1,200 of 3,209", notes[-1]["params"]["message"])
        self.assertEqual(answer["result"]["content"][0]["text"], "done compare_to_reference")
        index = self.stdout.all.index(answer)
        time.sleep(0.8)  # on purpose: no notification may come after the answer
        later = [m for m in self.stdout.all[index:] if m.get("method") == "notifications/progress"]
        self.assertEqual(later, [])
        self.assertTrue(self.fake.calls[0][1].endswith("-1"), self.fake.calls)

    def test_no_token_no_notifications(self):
        self.fake.seconds = 0.8
        self.call(2, "check_design")
        self.stdout.until(lambda m: m.get("id") == 2, "answer")
        self.assertEqual(
            [m for m in self.stdout.all if m.get("method") == "notifications/progress"], []
        )

    def test_cancel_stops_it_there_and_sends_no_answer(self):
        self.fake.seconds = 10.0
        self.call(3, "inspect_design", token=7)
        self.stdout.until(lambda m: m.get("method") == "notifications/progress", "notification")
        self.stdin.put(
            {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled",
                "params": {"requestId": 3, "reason": "timed out"},
            }
        )
        deadline = time.monotonic() + WAIT
        while not self.fake.stops and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(len(self.fake.stops), 1)
        call_id, reason = self.fake.stops[0]
        self.assertEqual(call_id, self.fake.calls[0][1])
        self.assertIn("the AI app cancelled it (timed out)", reason)
        # the worker is free again: the next call is answered, the cancelled one never is
        self.fake.seconds = 0.0
        self.fake.release = threading.Event()
        self.call(4, "get_design")
        self.stdout.until(lambda m: m.get("id") == 4, "the next answer")
        self.assertEqual([m for m in self.stdout.all if m.get("id") == 3], [])


class Words(unittest.TestCase):
    def test_progress_token(self):
        make = fission180_mcp.progress_token
        self.assertEqual(make({"params": {"_meta": {"progressToken": "a"}}}), "a")
        self.assertEqual(make({"params": {"_meta": {"progressToken": 5}}}), 5)
        self.assertIsNone(make({"params": {"_meta": {"progressToken": True}}}))
        self.assertIsNone(make({"params": {"_meta": {"progressToken": 1.5}}}))
        self.assertIsNone(make({"params": {}}))
        self.assertIsNone(make({}))

    def test_progress_message(self):
        status = {"working": True, "tool": "x", "call_id": "s-1", "what": "reading", "done": 2,
                  "total": 4}  # fmt: skip
        self.assertEqual(
            fission180_mcp.progress_message("x", 12, status, "s-1"),
            "Fission 180 is working on x (12 s): reading 2 of 4",
        )
        self.assertEqual(
            fission180_mcp.progress_message("y", 3, dict(status, seconds=40), "s-2"),
            "Fission 180 is still busy with x (40 s); y waits for it (3 s)",
        )
        self.assertEqual(
            fission180_mcp.progress_message("y", 3, None, "s-2"), "Fission 180: y (3 s)"
        )
        status["stopping"] = True
        self.assertIn("is stopping x", fission180_mcp.progress_message("x", 1, status, "s-1"))


class BridgeMessages(unittest.TestCase):
    def test_paths(self):
        for path in (bridge_core.CALL_PATH, bridge_core.STATUS_PATH, bridge_core.STOP_PATH):
            self.assertEqual(bridge_core.check_request("POST", path, "k", "k")[0], 200)
        self.assertEqual(bridge_core.check_request("POST", "/other", "k", "k")[0], 404)
        self.assertEqual(bridge_core.check_request("POST", "/status", "bad", "k")[0], 403)

    def test_call_ids(self):
        body = bridge_core.encode_request("extrude", {"distance": 5}, "abc-1")
        self.assertEqual(bridge_core.decode_call(body), ("extrude", {"distance": 5}, "abc-1"))
        self.assertEqual(bridge_core.decode_request(body), ("extrude", {"distance": 5}))
        old = bridge_core.encode_request("extrude", {})
        self.assertEqual(bridge_core.decode_call(old), ("extrude", {}, None))

    def test_status(self):
        self.assertEqual(bridge_core.status_answer(None), {"working": False})
        live = {"tool": "t", "call_id": "c", "seconds": 1.5, "what": "w", "done": 1, "total": 2,
                "stopping": False, "read_only": True}  # fmt: skip
        answer = bridge_core.status_answer(live, "AI: working on t (1 s): w 1 of 2")
        self.assertTrue(answer["working"])
        self.assertEqual(answer["line"], "AI: working on t (1 s): w 1 of 2")
        round_trip = bridge_core.decode_status(json.dumps(answer).encode("utf-8"))
        self.assertEqual(round_trip["call_id"], "c")
        self.assertEqual(bridge_core.decode_status(b"not json"), {"working": False})

    def test_stop(self):
        body = json.dumps({"call_id": "c-2", "reason": "timed out"}).encode("utf-8")
        self.assertEqual(bridge_core.decode_stop(body), ("c-2", "timed out"))
        self.assertEqual(
            bridge_core.decode_stop(b'{"call_id": "c"}'), ("c", "the AI app cancelled it")
        )
        with self.assertRaises(bridge_core.BridgeError):
            bridge_core.decode_stop(b"{}")

    def test_busy_says_what_it_does(self):
        text = bridge_core.busy_text("inspect_design", "compare_to_reference", 30, "faces 1 of 2")
        self.assertIn("(for 30 s; now faces 1 of 2)", text)
        self.assertIn("press Stop", text)


class UndoSteps(unittest.TestCase):
    def test_added_steps(self):
        self.assertEqual(progress.added_steps(["b", "a"], ["b", "a"]), [])
        self.assertEqual(progress.added_steps(["c", "b", "a"], ["b", "a"]), ["c"])
        self.assertEqual(progress.added_steps(["d", "c", "b", "a"], ["b", "a"]), ["c", "d"])
        # a full Undo list: the oldest of before is gone
        self.assertEqual(progress.added_steps(["c", "b"], ["b", "a"]), ["c"])
        self.assertEqual(progress.added_steps([], []), [])


if __name__ == "__main__":
    unittest.main()
