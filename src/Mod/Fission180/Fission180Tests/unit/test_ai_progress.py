# SPDX-License-Identifier: LGPL-2.1-or-later
"""A long AI call's safe points, its working line and its Stop (fission180/ai/progress.py).
Runs without FreeCAD."""

import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180.ai import progress  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.saved = (progress.PUMP_EVERY, progress._state["pump"], progress._state["guard"])
        self.pumps = []
        progress.set_pump(lambda call: self.pumps.append(call["what"]))
        progress.set_guard(None)
        progress.PUMP_EVERY = 0.0

    def tearDown(self):
        progress.PUMP_EVERY, pump, guard = self.saved
        progress.set_pump(pump)
        progress.set_guard(guard)
        while progress._state["call"] is not None:
            progress.end(progress._state["call"])


class Calls(Base):
    def test_outside_a_call_step_does_nothing(self):
        progress.step("nothing", 1, 2)
        self.assertEqual(self.pumps, [])
        self.assertIsNone(progress.current())
        self.assertFalse(progress.working())

    def test_a_call_records_and_pumps(self):
        token = progress.begin("compare_to_reference", "c1")
        self.assertTrue(progress.working())
        time.sleep(0.01)
        progress.step("comparing faces", 3, 10)
        status = progress.current()
        self.assertEqual(status["tool"], "compare_to_reference")
        self.assertEqual(status["call_id"], "c1")
        self.assertEqual(
            (status["what"], status["done"], status["total"]), ("comparing faces", 3, 10)
        )
        self.assertGreater(status["seconds"], 0)
        self.assertEqual(self.pumps, ["comparing faces"])
        record = progress.end(token)
        self.assertFalse(progress.working())
        self.assertEqual(record["steps"], 1)
        self.assertEqual(record["pumps"], 1)

    def test_done_alone_keeps_what(self):
        token = progress.begin("t")
        progress.step("reading faces", 0, 9)
        progress.step(done=4)
        status = progress.current()
        self.assertEqual((status["what"], status["done"], status["total"]), ("reading faces", 4, 9))
        progress.end(token)

    def test_pumps_are_rate_limited(self):
        progress.PUMP_EVERY = 10.0
        token = progress.begin("t")
        token["next_pump"] = time.monotonic() + 10.0
        for i in range(1000):
            progress.step("loop", i, 1000)
        self.assertEqual(self.pumps, [])
        self.assertEqual(token["steps"], 1000)
        progress.end(token)

    def test_a_slow_pump_waits_longer(self):
        progress.set_pump(lambda call: time.sleep(0.05))
        token = progress.begin("t")
        progress.step("x")
        self.assertGreaterEqual(token["next_pump"] - time.monotonic(), 0.15)
        progress.end(token)

    def test_nested_begin_is_the_same_call(self):
        outer = progress.begin("outer")
        inner = progress.begin("inner")
        self.assertIsNone(inner)
        self.assertEqual(progress.current()["tool"], "outer")
        progress.end(inner)
        self.assertTrue(progress.working())
        progress.end(outer)
        self.assertFalse(progress.working())

    def test_listeners_hear_begin_and_end(self):
        heard = []

        def listener(event, call):
            heard.append((event, call["tool"]))

        progress.add_listener(listener)
        try:
            progress.end(progress.begin("x"))
        finally:
            progress.remove_listener(listener)
        self.assertEqual(heard, [("begin", "x"), ("end", "x")])

    def test_a_failing_pump_or_listener_never_fails_the_call(self):
        def boom(*_args):
            raise RuntimeError("display gone")

        progress.set_pump(boom)
        progress.add_listener(boom)
        try:
            token = progress.begin("x")
            progress.step("still fine")
            progress.end(token)
        finally:
            progress.remove_listener(boom)


class Stop(Base):
    def test_stop_raises_at_the_next_safe_point(self):
        progress.PUMP_EVERY = 100.0
        token = progress.begin("t", "c1")
        token["next_pump"] = time.monotonic() + 100.0
        self.assertTrue(progress.request_stop("stopped by the person"))
        with self.assertRaises(progress.Stopped) as caught:
            progress.step("x")
        self.assertEqual(caught.exception.reason, "stopped by the person")
        self.assertTrue(token["stopped"])
        self.assertTrue(progress.current()["stopping"])
        with self.assertRaises(progress.Stopped):  # (sticky: a swallowed one comes back)
            progress.step("y")
        progress.end(token)

    def test_stopped_is_not_an_exception(self):
        self.assertFalse(issubclass(progress.Stopped, Exception))
        token = progress.begin("t")
        progress.request_stop("stop")
        try:
            try:
                progress.step("x")
            except Exception:
                self.fail("except Exception swallowed Stopped")
        except progress.Stopped:
            pass
        progress.end(token)

    def test_stop_pressed_during_the_pump(self):
        progress.set_pump(lambda call: progress.request_stop("pressed"))
        token = progress.begin("t")
        with self.assertRaises(progress.Stopped):
            progress.step("x")
        progress.end(token)

    def test_stop_only_the_named_call(self):
        token = progress.begin("t", "mine")
        self.assertFalse(progress.request_stop("cancelled", call_id="other"))
        self.assertIsNone(token["stop"])
        self.assertTrue(progress.request_stop("cancelled", call_id="mine"))
        progress.end(token)

    def test_stop_only_read_only(self):
        token = progress.begin("start_rebuild", read_only=False)
        self.assertFalse(progress.request_stop("nobody waits", only_read_only=True))
        progress.end(token)
        token = progress.begin("inspect_design", read_only=True)
        self.assertTrue(progress.request_stop("nobody waits", only_read_only=True))
        progress.end(token)

    def test_no_call_no_stop(self):
        self.assertFalse(progress.request_stop("x"))

    def test_the_guard_holds_a_stop_inside_a_recompute(self):
        inside = {"recompute": True}
        progress.set_guard(lambda: inside["recompute"])
        token = progress.begin("t")
        progress.request_stop("stop")
        progress.step("in a recompute")  # (no raise, no pump)
        progress.check()
        self.assertEqual(self.pumps, [])
        inside["recompute"] = False
        with self.assertRaises(progress.Stopped):
            progress.step("after it")
        progress.end(token)

    def test_check(self):
        token = progress.begin("t")
        progress.check()
        progress.request_stop("x")
        with self.assertRaises(progress.Stopped):
            progress.check()
        progress.end(token)

    def test_stop_from_another_thread(self):
        progress.PUMP_EVERY = 0.0
        token = progress.begin("t")
        threading.Thread(target=lambda: progress.request_stop("from the bridge")).start()
        deadline = time.monotonic() + 5.0
        with self.assertRaises(progress.Stopped):
            while time.monotonic() < deadline:
                progress.step("waiting")
                time.sleep(0.001)
        progress.end(token)


class Words(unittest.TestCase):
    def test_line(self):
        status = {
            "tool": "compare_to_reference",
            "seconds": 12.4,
            "what": "comparing faces",
            "done": 1200,
            "total": 3209,
        }
        self.assertEqual(
            progress.line(status),
            "AI: working on compare_to_reference (12 s): comparing faces 1,200 of 3,209",
        )
        status["stopping"] = True
        self.assertTrue(progress.line(status).startswith("AI: stopping compare_to_reference"))
        self.assertEqual(progress.line(None), "")
        self.assertEqual(
            progress.line({"tool": "check_design", "seconds": 75}),
            "AI: working on check_design (1 min 15 s)",
        )

    def test_doing_words(self):
        self.assertEqual(progress.doing_words("faces", 3), "faces 3")
        self.assertEqual(progress.doing_words("", 2, 5), "2 of 5")
        self.assertEqual(progress.doing_words("x", 0.5, 1), "x 0.5 of 1")

    def test_stopped_text(self):
        self.assertEqual(
            progress.stopped_text("check_design", "stopped by the person in Fission 180", 3.2),
            "Stopped after 3 s: check_design did not finish (stopped by the person in Fission "
            "180). Nothing was changed.",
        )
        text = progress.stopped_text("start_rebuild", "stop", 61, ["AI: Start rebuild"])
        self.assertIn("1 min 1 s", text)
        self.assertIn("Done before the stop, and kept: AI: Start rebuild.", text)


if __name__ == "__main__":
    unittest.main()
