# SPDX-License-Identifier: LGPL-2.1-or-later
"""MCP JSON-RPC handling (fission180/ai/mcp_core.py) with a fake Fission 180. Runs without
FreeCAD."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180.ai import mcp_core, tools_core  # noqa: E402


def request(method, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


class FakeFission180:
    def __init__(self, answer=None, fail=False):
        self.calls = []
        self.answer = answer or {"text": "done", "image_png_base64": None, "is_error": False}
        self.fail = fail

    def __call__(self, name, args):
        self.calls.append((name, args))
        if self.fail:
            raise RuntimeError("the bridge broke")
        return self.answer


class Lifecycle(unittest.TestCase):
    def handle(self, message, fake=None):
        return mcp_core.handle(message, fake or FakeFission180(), version="1.2.3")

    def test_initialize_echoes_a_supported_version(self):
        for version in ("2025-06-18", "2025-03-26", "2024-11-05"):
            reply = self.handle(request("initialize", {"protocolVersion": version}))
            self.assertEqual(reply["jsonrpc"], "2.0")
            self.assertEqual(reply["id"], 1)
            result = reply["result"]
            self.assertEqual(result["protocolVersion"], version)
            self.assertEqual(
                result["capabilities"],
                {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
            )
            self.assertEqual(
                result["serverInfo"], {"name": "fission180", "title": "Fission 180", "version": "1.2.3"}
            )
            self.assertIn("mm", result["instructions"])
            self.assertIn("get_design", result["instructions"])
            self.assertIn("undo", result["instructions"])

    def test_initialize_offers_the_newest_for_an_unknown_version(self):
        reply = self.handle(request("initialize", {"protocolVersion": "2099-01-01"}))
        self.assertEqual(reply["result"]["protocolVersion"], mcp_core.LATEST)
        self.assertIn(mcp_core.LATEST, mcp_core.PROTOCOL_VERSIONS)

    def test_initialize_needs_a_version(self):
        reply = self.handle(request("initialize", {}))
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_PARAMS)

    def test_notifications_get_no_reply(self):
        fake = FakeFission180()
        self.assertIsNone(self.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertIsNone(
            self.handle(
                {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 3}}
            )
        )
        self.assertIsNone(
            self.handle(
                {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "undo"}}, fake
            )
        )
        self.assertEqual(fake.calls, [])  # a notification never runs a tool
        self.assertIsNone(self.handle({"jsonrpc": "2.0", "id": 5, "result": {}}))

    def test_ping(self):
        self.assertEqual(
            self.handle(request("ping", request_id="a")),
            {"jsonrpc": "2.0", "id": "a", "result": {}},
        )

    def test_unknown_method(self):
        reply = self.handle(request("completion/complete"))  # (resources/list exists now)
        self.assertEqual(reply["error"]["code"], mcp_core.METHOD_NOT_FOUND)
        self.assertEqual(reply["id"], 1)

    def test_bad_requests(self):
        reply = self.handle({"id": 1, "method": "ping"})  # no jsonrpc
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_REQUEST)
        reply = self.handle({"jsonrpc": "2.0", "id": True, "method": "ping"})
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_REQUEST)
        self.assertIsNone(reply["id"])
        reply = self.handle(request("ping", params=[1, 2]))
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_PARAMS)
        reply = self.handle("not a dict")
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_REQUEST)


class Tools(unittest.TestCase):
    def handle(self, message, fake):
        return mcp_core.handle(message, fake, version="1")

    def test_tools_list(self):
        reply = self.handle(request("tools/list"), FakeFission180())
        self.assertEqual(reply["result"]["tools"], tools_core.mcp_tools())
        self.assertNotIn("nextCursor", reply["result"])

    def test_call_happy_path(self):
        fake = FakeFission180({"text": "Extruded 10 mm", "is_error": False})
        args = {"profile": "s1", "distance": 10}
        reply = self.handle(request("tools/call", {"name": "extrude", "arguments": args}), fake)
        self.assertEqual(fake.calls, [("extrude", args)])
        self.assertEqual(
            reply["result"],
            {"content": [{"type": "text", "text": "Extruded 10 mm"}], "isError": False},
        )

    def test_call_with_image(self):
        fake = FakeFission180({"text": "iso view", "image_png_base64": "iVBORw0K", "is_error": False})
        reply = self.handle(request("tools/call", {"name": "screenshot"}), fake)
        self.assertEqual(fake.calls, [("screenshot", {})])
        content = reply["result"]["content"]
        self.assertEqual(content[1], {"type": "image", "data": "iVBORw0K", "mimeType": "image/png"})

    def test_bridge_error_is_a_tool_error(self):
        fake = FakeFission180({"text": "Fission 180 is busy", "is_error": True})
        reply = self.handle(request("tools/call", {"name": "undo", "arguments": {}}), fake)
        self.assertTrue(reply["result"]["isError"])

    def test_validation_problems_are_tool_errors(self):
        fake = FakeFission180()
        args = {"edges": {"count": 4}, "radius": -1}
        reply = self.handle(request("tools/call", {"name": "fillet", "arguments": args}), fake)
        self.assertEqual(fake.calls, [])
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("radius must be a number above 0", reply["result"]["content"][0]["text"])

    def test_unknown_tool_and_bad_params(self):
        fake = FakeFission180()
        reply = self.handle(request("tools/call", {"name": "format_disk"}), fake)
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_PARAMS)
        reply = self.handle(request("tools/call", {"name": "undo", "arguments": [1]}), fake)
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_PARAMS)
        reply = self.handle(request("tools/call", {}), fake)
        self.assertEqual(reply["error"]["code"], mcp_core.INVALID_PARAMS)
        self.assertEqual(fake.calls, [])

    def test_a_failing_bridge_never_escapes(self):
        reply = self.handle(request("tools/call", {"name": "undo"}), FakeFission180(fail=True))
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("the bridge broke", reply["result"]["content"][0]["text"])
        reply = self.handle(request("tools/call", {"name": "undo"}), lambda name, args: None)
        self.assertTrue(reply["result"]["isError"])


class Framing(unittest.TestCase):
    def test_parse_line(self):
        message, error = mcp_core.parse_line(b'{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n')
        self.assertEqual(message["method"], "ping")
        self.assertIsNone(error)
        self.assertEqual(mcp_core.parse_line("   \r\n"), (None, None))

    def test_parse_error(self):
        message, error = mcp_core.parse_line("{not json")
        self.assertIsNone(message)
        self.assertEqual(error["error"]["code"], mcp_core.PARSE_ERROR)
        self.assertIsNone(error["id"])
        _, error = mcp_core.parse_line(b"\xff\xfe")
        self.assertEqual(error["error"]["code"], mcp_core.PARSE_ERROR)

    def test_batch_refused(self):
        line = json.dumps([{"jsonrpc": "2.0", "id": 1, "method": "ping"}])
        message, error = mcp_core.parse_line(line)
        self.assertIsNone(message)
        self.assertEqual(error["error"]["code"], mcp_core.INVALID_REQUEST)
        self.assertIn("batch", error["error"]["message"])
        _, error = mcp_core.parse_line("42")
        self.assertEqual(error["error"]["code"], mcp_core.INVALID_REQUEST)

    def test_encode_is_one_line(self):
        data = mcp_core.encode({"jsonrpc": "2.0", "id": 1, "result": {"text": "a\nb é"}})
        self.assertTrue(data.endswith(b"\n"))
        self.assertEqual(data.count(b"\n"), 1)
        self.assertEqual(json.loads(data.decode("utf-8"))["result"]["text"], "a\nb é")


# -- wave 8, ai-behaviour: the AI app's own question form, the guard, the instructions' size ----
class AskPerson(unittest.TestCase):
    """ask_person through MCP elicitation where the AI app declared it (Claude Code in a
    terminal declares elicitation {form, url}; Gemini CLI's client declares roots only:
    docs/fission180/parity/ai.md "Wave 8"), the sentence to ask in the reply elsewhere."""

    QUESTIONS = [{"question": "A solid or a timeline?", "choices": ["solid", "timeline"],
                  "default": "solid"}]

    def setUp(self):
        mcp_core.reset_session()
        mcp_core.set_sender(None)

    tearDown = setUp

    def initialize(self, capabilities):
        mcp_core.handle(request("initialize", {"protocolVersion": "2025-11-25",
                                               "capabilities": capabilities}), FakeFission180())

    def ask(self, fake=None, request_id=7):
        answer = mcp_core.handle(
            request("tools/call", {"name": "ask_person",
                                   "arguments": {"questions": self.QUESTIONS}}, request_id),
            fake or FakeFission180(),
        )
        return answer["result"]["content"][0]["text"], answer["result"]["isError"]

    def test_no_elicitation_says_ask_in_the_reply(self):
        fake = FakeFission180()
        self.initialize({"roots": {"listChanged": True}})
        text, err = self.ask(fake)
        self.assertFalse(err)
        self.assertIn("ask the questions in your reply", text)
        self.assertEqual(fake.calls, [])  # (answered by the server: works with Fission 180 closed)

    def test_capabilities(self):
        self.assertTrue(mcp_core._client_elicits({"elicitation": {}}))
        self.assertTrue(mcp_core._client_elicits({"elicitation": {"form": {}, "url": {}}}))
        self.assertFalse(mcp_core._client_elicits({"elicitation": {"url": {}}}))
        self.assertFalse(mcp_core._client_elicits({"roots": {}}))
        self.assertFalse(mcp_core._client_elicits(None))

    def _app(self, reply):
        """A fake AI app: answers our elicitation/create on another thread, as fission180_mcp's
        reading thread hands the answer to mcp_core.handle."""
        import threading

        sent = []

        def send(message):
            sent.append(message)
            if message.get("method") == "elicitation/create" and reply is not None:
                answer = {"jsonrpc": "2.0", "id": message["id"], "result": reply}
                threading.Timer(0.05, mcp_core.handle, (answer, FakeFission180())).start()

        return send, sent

    def test_the_form_round_trip(self):
        send, sent = self._app({"action": "accept", "content": {"q1": "timeline"}})
        mcp_core.set_sender(send, set())
        self.initialize({"elicitation": {"form": {}}})
        text, err = self.ask()
        self.assertFalse(err)
        self.assertIn("The person answered", text)
        self.assertIn("A solid or a timeline? timeline", text)
        create = [m for m in sent if m.get("method") == "elicitation/create"][0]
        field = create["params"]["requestedSchema"]["properties"]["q1"]
        self.assertEqual(field["enum"], ["solid", "timeline"])
        self.assertEqual(mcp_core._PENDING, {})

    def test_declined(self):
        send, _sent = self._app({"action": "decline"})
        mcp_core.set_sender(send, set())
        self.initialize({"elicitation": {}})
        text, _err = self.ask()
        self.assertIn("declined", text)

    def test_a_cancelled_call_stops_waiting_and_cancels_the_form(self):
        cancelled = set()
        send, sent = self._app(None)  # (the app never answers)
        mcp_core.set_sender(send, cancelled)
        self.initialize({"elicitation": {}})
        import threading

        threading.Timer(0.1, cancelled.add, (7,)).start()
        text, _err = self.ask(request_id=7)
        self.assertIn("ask them in your reply", text)
        self.assertTrue(any(m.get("method") == "notifications/cancelled" for m in sent))

    def test_an_answer_nobody_waits_for_is_ignored(self):
        self.assertIsNone(mcp_core.handle({"jsonrpc": "2.0", "id": "fission180-99",
                                           "result": {}}, FakeFission180()))


class Guard(unittest.TestCase):
    def test_the_same_small_step_again_and_again_gets_a_note(self):
        mcp_core.reset_session()
        fake = FakeFission180({"text": "Done: AI: Extrude.", "image_png_base64": None,
                               "is_error": False})
        texts = []
        for i in range(8):
            for name, args in (
                ("create_sketch", {"plane": "XY", "geometry": [{"rect": [i, 0, i + 1, 1]}]}),
                ("extrude", {"profile": "Sketch%d" % (i + 1), "distance": 0.5}),
            ):
                answer = mcp_core.handle(
                    request("tools/call", {"name": name, "arguments": args}), fake
                )
                texts.append(answer["result"]["content"][0]["text"])
        self.assertTrue(any("convert_mesh" in t and "pattern" in t for t in texts))
        self.assertNotIn("Note:", texts[0])
        mcp_core.reset_session()


class Instructions(unittest.TestCase):
    def test_the_essentials_come_first_and_fit_claude_code(self):
        # Claude Code cuts a server's instructions after 4,096 characters
        # (code.claude.com/docs/en/mcp, checked 2026-11-13): what matters most comes first.
        from fission180.ai import catalog

        head = mcp_core.INSTRUCTIONS[:4096]
        self.assertLessEqual(len(catalog.ESSENTIALS), catalog.ESSENTIAL_LIMIT)
        self.assertTrue(mcp_core.INSTRUCTIONS.startswith(catalog.ESSENTIALS))
        for words in ("plan_approach", "ask_person", "in one message", "convert_mesh",
                      "facet by facet", "pattern", "any workspace", "show_workspace",
                      "list_tools with goal", "count", "get_help topics selectors",
                      "must get a descriptive name", "docs_search"):
            self.assertIn(words, head, words)

    def test_initialize_carries_them(self):
        answer = mcp_core.handle(
            request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}}),
            FakeFission180(),
        )
        self.assertEqual(answer["result"]["instructions"], mcp_core.INSTRUCTIONS)
        mcp_core.reset_session()

    def test_a_few_tools_load_upfront(self):
        listed = {t["name"]: t for t in tools_core.mcp_tools()}
        upfront = [n for n, t in listed.items() if t.get("_meta", {}).get("anthropic/alwaysLoad")]
        self.assertIn("plan_approach", upfront)
        self.assertLessEqual(len(upfront), 6)


if __name__ == "__main__":
    unittest.main()
