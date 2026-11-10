# SPDX-License-Identifier: LGPL-2.1-or-later
"""Answers word by word (fission180/ai/providers/_stream.py and each adapter's StreamReader):
the server-sent events format, each provider's stream put back together into the answer
the non-streamed request gives (so tool calls and the history stay exactly as before), the
chat loop with a streamed answer (pieces shown before the step ends, a tool call made of
pieces of JSON, Stop in the middle, a connection lost in the middle, an error event, a
server that does not stream), and once over real HTTP on 127.0.0.1 (pieces read while the
server is still sending, Stop closing the connection at once, a dropped connection). Runs
without FreeCAD."""

import http.server
import json
import os
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180.ai import chat_core, providers  # noqa: E402
from fission180.ai.providers import _stream, anthropic, gemini, openai, openai_compat  # noqa: E402

KEY = "sk-ant-api03-STREAMSECRET0123456789"
SKETCH = {"plane": "XY", "geometry": [{"center_rect": [0, 0, 40, 30]}]}


def sse(name, data):
    """One server-sent event as the providers send it."""
    text = json.dumps(data) if not isinstance(data, str) else data
    return ("event: %s\n" % name if name else "") + "data: %s\n\n" % text


def claude_events(text_pieces=(), tool=None, thinking=None, stop="end_turn", text2=None):
    """The events of one streamed Claude answer: a thinking block, a text block in pieces,
    a tool call whose arguments come in pieces of JSON, and another text block."""
    out = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-opus-5-5",
                    "content": [],
                    "stop_reason": None,
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 1,
                        "cache_read_input_tokens": 100,
                    },
                },
            },
        ),
        ("ping", {"type": "ping"}),
    ]
    index = 0
    if thinking:
        out += [
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "thinking", "thinking": "", "signature": ""},
                },
            ),
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "thinking_delta", "thinking": thinking},
                },
            ),
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "signature_delta", "signature": "SIG=="},
                },
            ),
            ("content_block_stop", {"type": "content_block_stop", "index": index}),
        ]
        index += 1
    if text_pieces:
        out.append(
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "text", "text": ""},
                },
            )
        )
        for piece in text_pieces:
            out.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "text_delta", "text": piece},
                    },
                )
            )
        out.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
        index += 1
    if tool:
        call_id, name, args = tool
        raw = json.dumps(args)
        cuts = [raw[i : i + 7] for i in range(0, len(raw), 7)]  # (cut in the middle of words)
        out.append(
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "tool_use", "id": call_id, "name": name, "input": {}},
                },
            )
        )
        out.append(
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "input_json_delta", "partial_json": ""},
                },
            )
        )
        for cut in cuts:
            out.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "input_json_delta", "partial_json": cut},
                    },
                )
            )
        out.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
        index += 1
    if text2:
        out.append(
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "text", "text": ""},
                },
            )
        )
        out.append(
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "text_delta", "text": text2},
                },
            )
        )
        out.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
    out += [
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop, "stop_sequence": None},
                "usage": {"output_tokens": 42},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    return out


def feed_all(reader, events):
    shown = []
    for name, data in events:
        shown += reader.feed(name, json.dumps(data) if not isinstance(data, str) else data)
    return shown


def texts(shown):
    return "".join(piece for kind, piece in shown if kind == "text")


class Lines:
    """A stand-in for an HTTP answer: readline() gives the next line (bytes), or raises."""

    def __init__(self, text, fail_after=None, error=None):
        self.lines = [line.encode("utf-8") for line in text.splitlines(keepends=True)]
        self.fail_after = fail_after
        self.error = error or ConnectionResetError(104, "Connection reset by peer")
        self.read = 0

    def readline(self, *_args):
        if self.fail_after is not None and self.read >= self.fail_after:
            raise self.error
        self.read += 1
        return self.lines.pop(0) if self.lines else b""


# -- the format ----------------------------------------------------------------------------
class ServerSentEvents(unittest.TestCase):
    def events(self, text, **kwargs):
        got = []
        problem = _stream.read_events(Lines(text, **kwargs), lambda n, d: got.append((n, d)))
        return got, problem

    def test_events_data_lines_and_comments(self):
        text = (
            ": a comment (keep-alive)\n"
            'event: one\ndata: {"a": 1}\n\n'
            "data: first line\ndata:second line\n\n"  # (no space after the colon: kept)
            "event: three\r\ndata: crlf\r\n\r\n"
            "id: 7\nretry: 100\ndata: x\n\n"
            "\n\n"  # (blank lines without data: nothing)
            "data: no blank line at the end"
        )
        got, problem = self.events(text)
        self.assertIsNone(problem)
        self.assertEqual(
            got,
            [
                ("one", '{"a": 1}'),
                ("message", "first line\nsecond line"),
                ("three", "crlf"),
                ("message", "x"),
                ("message", "no blank line at the end"),
            ],
        )

    def test_lines_that_are_not_sse_come_last_as_stray(self):
        got, _problem = self.events('data: {"a": 1}\n\n{\n  "error": {"code": 503}\n}\n')
        self.assertEqual(got[0], ("message", '{"a": 1}'))
        self.assertEqual(got[1][0], _stream.STRAY)
        self.assertEqual(json.loads(got[1][1]), {"error": {"code": 503}})

    def test_reading_stops_when_the_answer_is_complete(self):
        got = []
        answer = Lines("data: 1\n\ndata: 2\n\ndata: 3\n\n")
        problem = _stream.read_events(answer, lambda n, d: got.append(d) or d == "2")
        self.assertIsNone(problem)
        self.assertEqual(got, ["1", "2"])

    def test_a_broken_connection_and_stop(self):
        got, problem = self.events("data: 1\n\ndata: 2\n\ndata: 3\n\n", fail_after=3)
        self.assertEqual([d for _n, d in got], ["1"])
        self.assertTrue(problem.startswith("cut: network:"), problem)
        self.assertIn("reset", problem)
        got, problem = self.events("data: 1\n\n", fail_after=0, error=socket.timeout("timed out"))
        self.assertEqual(problem, "cut: timeout")
        stop = {"now": False}
        seen = []

        def on_event(_name, data):
            seen.append(data)
            stop["now"] = True  # (Stop pressed while the first piece was shown)

        problem = _stream.read_events(
            Lines("data: 1\n\ndata: 2\n\n"), on_event, lambda: stop["now"]
        )
        self.assertEqual((problem, seen), ("stopped", ["1"]))
        # the connection closed under the reading by Stop: "stopped", not "cut"
        problem = _stream.read_events(
            Lines("data: 1\n\n", fail_after=0), lambda n, d: None, lambda: True
        )
        self.assertEqual(problem, "stopped")

    def test_error_status_words(self):
        self.assertEqual(_stream.error_status({"type": "overloaded_error"}), 529)
        self.assertEqual(_stream.error_status({"type": "rate_limit_error"}), 429)
        self.assertEqual(_stream.error_status({"code": "rate_limit_exceeded"}), 429)
        self.assertEqual(_stream.error_status({"code": 503, "status": "UNAVAILABLE"}), 503)
        self.assertEqual(_stream.error_status({"status": "INVALID_ARGUMENT"}), 400)
        self.assertEqual(_stream.error_status({"message": "?"}), 500)
        self.assertEqual(_stream.error_status(None), 500)


# -- each provider's stream ------------------------------------------------------------------
class ClaudeStream(unittest.TestCase):
    def test_text_thinking_and_a_tool_call_in_pieces(self):
        adapter = anthropic.Adapter()
        reader = adapter.stream_reader()
        events = claude_events(
            ["I'll ", "make the ", "sketch."],
            tool=("toolu_1", "create_sketch", SKETCH),
            thinking="A rectangle on XY first.",
            stop="tool_use",
        )
        shown = feed_all(reader, events)
        self.assertEqual(
            shown,
            [
                ("progress", "A rectangle on XY first."),
                ("text", "I'll "),
                ("text", "make the "),
                ("text", "sketch."),
            ],
        )
        self.assertTrue(reader.complete and reader.finished)
        self.assertIsNone(reader.error)
        turn = adapter.parse_response(reader.result())
        self.assertEqual(turn["text"], "I'll make the sketch.")
        self.assertEqual(turn["stop"], "tool_use")
        self.assertEqual(
            turn["tool_calls"], [{"id": "toolu_1", "name": "create_sketch", "args": SKETCH}]
        )
        self.assertEqual(turn["progress"], ["A rectangle on XY first."])
        self.assertEqual(turn["usage"]["input_tokens"], 120)
        self.assertEqual(turn["usage"]["output_tokens"], 42)
        self.assertEqual(turn["usage"]["cache_read_input_tokens"], 100)
        # the history gets the blocks as the non-streamed answer has them (thinking signed)
        content = turn["raw"]["content"]
        self.assertEqual([b["type"] for b in content], ["thinking", "text", "tool_use"])
        self.assertEqual(content[0]["signature"], "SIG==")
        self.assertEqual(content[2]["input"], SKETCH)
        self.assertEqual(turn["raw"]["model"], "claude-opus-5-5")

    def test_two_text_blocks_show_as_two_paragraphs(self):
        reader = anthropic.Adapter().stream_reader()
        shown = feed_all(reader, claude_events(["First."], text2="Second."))
        turn = anthropic.Adapter().parse_response(reader.result())
        self.assertEqual(texts(shown), "First.\n\nSecond.")
        self.assertEqual(turn["text"], texts(shown))

    def test_a_fallback_in_the_middle(self):
        # (a server-side fallback: the declined model's words stay, the marker goes)
        events = claude_events(["Declined part. "])
        fallback = {
            "type": "fallback",
            "from": {"model": "claude-opus-5-5"},
            "to": {"model": "claude-sonnet-5-5"},
            "trigger": {"type": "refusal"},
        }
        events[5:5] = [
            (
                "content_block_start",
                {"type": "content_block_start", "index": 1, "content_block": fallback},
            ),
            ("content_block_stop", {"type": "content_block_stop", "index": 1}),
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 2,
                    "content_block": {"type": "text", "text": ""},
                },
            ),
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 2,
                    "delta": {"type": "text_delta", "text": "Answer."},
                },
            ),
            ("content_block_stop", {"type": "content_block_stop", "index": 2}),
        ]
        reader = anthropic.Adapter().stream_reader()
        shown = feed_all(reader, events)
        turn = anthropic.Adapter().parse_response(reader.result())
        self.assertEqual(texts(shown), "Declined part. \n\nAnswer.")
        self.assertEqual(turn["text"], "Declined part. \n\nAnswer.")
        self.assertEqual(turn["raw"]["model"], "claude-sonnet-5-5")
        self.assertEqual([b["type"] for b in turn["raw"]["content"]], ["text", "text"])

    def test_an_error_in_the_middle_and_a_stream_that_broke_off(self):
        reader = anthropic.Adapter().stream_reader()
        events = claude_events(["Hel"])[:4]
        events.append(
            (
                "error",
                {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}},
            )
        )
        feed_all(reader, events)
        self.assertEqual(reader.error[0], 529)
        self.assertIn("Overloaded", json.dumps(reader.error[1]))
        reader = anthropic.Adapter().stream_reader()
        feed_all(reader, claude_events(["Hel"], stop="end_turn")[:4])
        self.assertFalse(reader.complete)
        # an unknown event, a piece that is not JSON and a delta for no block: skipped
        self.assertEqual(reader.feed("mystery", '{"type": "mystery"}'), [])
        self.assertEqual(reader.feed("content_block_delta", "{not json"), [])
        self.assertEqual(
            reader.feed(
                "content_block_delta",
                json.dumps({"type": "content_block_delta", "index": 9, "delta": {}}),
            ),
            [],
        )

    def test_the_request_asks_for_a_stream(self):
        adapter = anthropic.Adapter()
        url, headers, body = adapter.build_request("claude-opus-5-5", "sys", [], [], key=KEY)
        s_url, s_headers, s_body = adapter.stream_request(url, headers, body)
        self.assertEqual((s_url, s_body["stream"]), (url, True))
        self.assertNotIn("stream", body)  # (the one-piece request is left as it was)
        self.assertEqual(s_headers["x-api-key"], KEY)


class OpenAIStream(unittest.TestCase):
    def events(self, with_output=True):
        call = {
            "type": "function_call",
            "id": "fc_1",
            "call_id": "call_1",
            "name": "create_sketch",
            "arguments": json.dumps(SKETCH),
            "status": "completed",
        }
        message = {
            "type": "message",
            "role": "assistant",
            "id": "msg_1",
            "content": [{"type": "output_text", "text": "Making it."}],
        }
        reasoning = {
            "type": "reasoning",
            "id": "rs_1",
            "summary": [{"type": "summary_text", "text": "Plan: a sketch."}],
        }
        response = {
            "id": "resp_1",
            "status": "completed",
            "model": "gpt-6-astra",
            "output": [reasoning, message, call] if with_output else [],
            "usage": {"input_tokens": 300, "output_tokens": 20},
        }
        return [
            (
                "response.created",
                {"type": "response.created", "response": {"status": "in_progress"}},
            ),
            (
                "response.output_item.done",
                {"type": "response.output_item.done", "output_index": 0, "item": reasoning},
            ),
            (
                "response.output_text.delta",
                {
                    "type": "response.output_text.delta",
                    "output_index": 1,
                    "content_index": 0,
                    "delta": "Making ",
                },
            ),
            (
                "response.output_text.delta",
                {
                    "type": "response.output_text.delta",
                    "output_index": 1,
                    "content_index": 0,
                    "delta": "it.",
                },
            ),
            (
                "response.output_item.done",
                {"type": "response.output_item.done", "output_index": 1, "item": message},
            ),
            (
                "response.function_call_arguments.delta",
                {
                    "type": "response.function_call_arguments.delta",
                    "output_index": 2,
                    "delta": '{"pl',
                },
            ),
            (
                "response.output_item.done",
                {"type": "response.output_item.done", "output_index": 2, "item": call},
            ),
            ("response.completed", {"type": "response.completed", "response": response}),
        ]

    def test_text_reasoning_and_a_call(self):
        adapter = openai.Adapter()
        for with_output in (True, False):
            reader = adapter.stream_reader()
            shown = feed_all(reader, self.events(with_output))
            self.assertEqual(
                shown, [("progress", "Plan: a sketch."), ("text", "Making "), ("text", "it.")]
            )
            self.assertTrue(reader.complete and reader.finished)
            turn = adapter.parse_response(reader.result())
            self.assertEqual(turn["text"], "Making it.")
            self.assertEqual(
                turn["tool_calls"], [{"id": "call_1", "name": "create_sketch", "args": SKETCH}]
            )
            self.assertEqual(turn["stop"], "tool_use")
            self.assertEqual(turn["progress"], ["Plan: a sketch."])
            self.assertEqual(len(turn["raw"]["items"]), 3)

    def test_errors(self):
        reader = openai.Adapter().stream_reader()
        feed_all(
            reader,
            [("error", {"type": "error", "code": "rate_limit_exceeded", "message": "Slow down"})],
        )
        self.assertEqual(reader.error[0], 429)
        self.assertEqual(reader.error[1]["error"]["message"], "Slow down")
        reader = openai.Adapter().stream_reader()
        feed_all(
            reader,
            [
                (
                    "response.failed",
                    {
                        "type": "response.failed",
                        "response": {
                            "status": "failed",
                            "error": {"code": "server_error", "message": "Oops"},
                        },
                    },
                )
            ],
        )
        self.assertEqual(reader.error[0], 500)

    def test_the_request_asks_for_a_stream(self):
        adapter = openai.Adapter()
        url, headers, body = adapter.build_request("gpt-6-astra", "sys", [], [], key="sk-x")
        self.assertTrue(adapter.stream_request(url, headers, body)[2]["stream"])


class CompatibleStream(unittest.TestCase):
    def chunk(self, delta, finish=None):
        return {
            "id": "c",
            "object": "chat.completion.chunk",
            "model": "qwen3:8b",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }

    def test_text_and_two_calls_in_pieces(self):
        adapter = openai_compat.Adapter()
        reader = adapter.stream_reader()
        args = json.dumps(SKETCH)
        events = [
            (None, self.chunk({"role": "assistant", "content": ""})),
            (None, self.chunk({"content": "Sure"})),
            (None, self.chunk({"content": ", building."})),
            (
                None,
                self.chunk(
                    {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_a",
                                "type": "function",
                                "function": {"name": "create_sketch", "arguments": ""},
                            }
                        ]
                    }
                ),
            ),
            (None, self.chunk({"tool_calls": [{"index": 0, "function": {"arguments": args[:9]}}]})),
            (None, self.chunk({"tool_calls": [{"index": 0, "function": {"arguments": args[9:]}}]})),
            (
                None,
                self.chunk(
                    {
                        "tool_calls": [
                            {
                                "index": 1,
                                "id": "call_b",
                                "type": "function",
                                "function": {"name": "get_design", "arguments": "{}"},
                            }
                        ]
                    }
                ),
            ),
            (None, self.chunk({}, "tool_calls")),
            (None, "[DONE]"),
        ]
        shown = feed_all(reader, events)
        self.assertEqual(texts(shown), "Sure, building.")
        self.assertTrue(reader.finished and reader.complete)
        turn = adapter.parse_response(reader.result())
        self.assertEqual(turn["text"], "Sure, building.")
        self.assertEqual(turn["stop"], "tool_use")
        self.assertEqual(
            turn["tool_calls"],
            [
                {"id": "call_a", "name": "create_sketch", "args": SKETCH},
                {"id": "call_b", "name": "get_design", "args": {}},
            ],
        )

    def test_whole_calls_each_numbered_0_and_broken_json(self):
        reader = openai_compat.Adapter().stream_reader()
        feed_all(
            reader,
            [
                (
                    None,
                    self.chunk(
                        {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {"name": "get_design", "arguments": {}},
                                }
                            ]
                        }
                    ),
                ),
                (
                    None,
                    self.chunk(
                        {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c2",
                                    "function": {"name": "extrude", "arguments": '{"distance": '},
                                }
                            ]
                        },
                        "stop",
                    ),
                ),
            ],
        )
        self.assertTrue(reader.complete)  # (finish_reason without [DONE])
        turn = openai_compat.Adapter().parse_response(reader.result())
        self.assertEqual([c["name"] for c in turn["tool_calls"]], ["get_design", "extrude"])
        self.assertEqual(turn["stop"], "tool_use")
        self.assertIn("bad_args", turn["tool_calls"][1])  # (sent back to the model as an error)

    def test_an_error_chunk(self):
        reader = openai_compat.Adapter().stream_reader()
        feed_all(
            reader, [(None, {"error": {"message": "model not loaded", "type": "invalid_request"}})]
        )
        self.assertEqual(reader.error[0], 400)
        self.assertTrue(reader.finished)


class GeminiStream(unittest.TestCase):
    def chunk(self, parts, finish=None, usage=None):
        candidate = {"content": {"role": "model", "parts": parts}}
        if finish:
            candidate["finishReason"] = finish
        data = {"candidates": [candidate], "modelVersion": "gemini-3-flash"}
        if usage:
            data["usageMetadata"] = usage
        return data

    def test_pieces_thoughts_a_call_and_signatures(self):
        adapter = gemini.Adapter()
        reader = adapter.stream_reader()
        call = {
            "functionCall": {"name": "create_sketch", "args": SKETCH, "id": "fc1"},
            "thoughtSignature": "SIG1",
        }
        events = [
            (None, self.chunk([{"text": "Think ", "thought": True}])),
            (None, self.chunk([{"text": "about XY.", "thought": True}])),
            (None, self.chunk([{"text": "Making "}])),
            (None, self.chunk([{"text": "it."}])),
            (None, self.chunk([call])),
            (
                None,
                self.chunk(
                    [{"text": "", "thoughtSignature": "SIG2"}],
                    "STOP",
                    {"promptTokenCount": 50, "candidatesTokenCount": 9},
                ),
            ),
        ]
        shown = feed_all(reader, events)
        self.assertEqual(
            shown, [("progress", "Think about XY."), ("text", "Making "), ("text", "it.")]
        )
        self.assertTrue(reader.complete)
        self.assertFalse(reader.finished)  # (Gemini's answer ends when the connection does)
        turn = adapter.parse_response(reader.result())
        self.assertEqual(turn["text"], "Making it.")
        self.assertEqual(turn["progress"], ["Think about XY."])
        self.assertEqual(
            turn["tool_calls"], [{"name": "create_sketch", "id": "fc1", "args": SKETCH}]
        )
        self.assertEqual(turn["usage"], {"input_tokens": 50, "output_tokens": 9})
        parts = turn["raw"]["content"]["parts"]
        self.assertEqual(parts[2]["thoughtSignature"], "SIG1")  # (kept as it came)
        self.assertEqual(parts[3], {"text": "", "thoughtSignature": "SIG2"})
        self.assertEqual(len(parts), 4)

    def test_errors_and_the_url(self):
        reader = gemini.Adapter().stream_reader()
        feed_all(
            reader,
            [
                (
                    _stream.STRAY,
                    json.dumps(
                        {"error": {"code": 503, "message": "busy", "status": "UNAVAILABLE"}}
                    ),
                )
            ],
        )
        self.assertEqual(reader.error[0], 503)
        reader = gemini.Adapter().stream_reader()
        feed_all(reader, [(None, {"error": {"code": 429, "message": "quota"}})])
        self.assertEqual(reader.error[0], 429)
        adapter = gemini.Adapter()
        url, headers, body = adapter.build_request("gemini-flash-latest", "s", [], [], key="AIzaX")
        s_url = adapter.stream_request(url, headers, body)[0]
        self.assertTrue(
            s_url.endswith("/v1beta/models/gemini-flash-latest:streamGenerateContent?alt=sse"),
            s_url,
        )

    def test_a_blocked_prompt_is_complete(self):
        reader = gemini.Adapter().stream_reader()
        feed_all(reader, [(None, {"promptFeedback": {"blockReason": "SAFETY"}})])
        self.assertTrue(reader.complete)
        self.assertEqual(gemini.Adapter().parse_response(reader.result())["stop"], "refusal")

    def test_every_provider_streams(self):
        for name in providers.ORDER:
            adapter = providers.adapter(name)
            self.assertTrue(callable(adapter.stream_request), name)
            self.assertIsInstance(adapter.stream_reader(), _stream.StreamReader, name)


# -- the chat loop with streamed answers ----------------------------------------------------
class FakeStream:
    """A fake streaming provider for chat_core: each answer is a list of (event name, data)
    events, optionally ending in a problem: ("cut", reason), ("stop_after", n) (the person
    presses Stop after n events), ("plain", (status, data, problem)) (an answer in one
    piece) or ("error_status", status) (an HTTP error)."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []
        self.aborted = 0
        self.chat = None

    def __call__(self, url, headers, body, on_event, should_stop, on_open):
        self.requests.append({"url": url, "body": json.loads(json.dumps(body))})
        answer = self.answers.pop(0)
        if answer and answer[0] == "plain":
            return answer[1] + (False,)
        on_open(self.abort)
        try:
            events, ending = answer
            for number, (name, data) in enumerate(events):
                if should_stop():
                    return 200, None, "stopped", True
                if on_event(name, json.dumps(data) if not isinstance(data, str) else data):
                    return 200, None, None, True
                if ending and ending[0] == "stop_after" and number + 1 == ending[1]:
                    self.chat.stop()  # (as the panel's Stop does, from another thread)
            if ending and ending[0] == "cut":
                return 200, None, "cut: " + ending[1], True
            if should_stop():
                return 200, None, "stopped", True
            return 200, None, None, True
        finally:
            on_open(None)

    def abort(self):
        self.aborted += 1


class Recorder:
    def __init__(self):
        self.events, self.lines = [], []

    def event(self, kind, data):
        self.events.append((kind, data))

    def log(self, line):
        self.lines.append(line)

    def kinds(self):
        return [kind for kind, _data in self.events]


def make_chat(stream, tools=None, http=None, adapter=None, **kwargs):
    rec = Recorder()
    calls = []

    def call_tool(name, args):
        calls.append((name, args))
        return {
            "text": "%s done: its id is 'Sketch1'" % name,
            "image_png_base64": None,
            "is_error": False,
        }

    chat = chat_core.Chat(
        adapter or anthropic.Adapter(),
        "claude-opus-5-5",
        key=KEY,
        call_tool=call_tool,
        log=rec.log,
        http=http or (lambda *a: (_ for _ in ()).throw(AssertionError("asked in one piece"))),
        stream_http=stream,
        sleep=lambda s: None,
        **kwargs,
    )
    stream.chat = chat
    return chat, rec, calls


class StreamedChat(unittest.TestCase):
    def test_words_show_before_the_step_ends_and_a_tool_call_runs(self):
        stream = FakeStream(
            (
                claude_events(
                    ["Making ", "a sketch."],
                    tool=("toolu_1", "create_sketch", SKETCH),
                    thinking="XY plane.",
                    stop="tool_use",
                ),
                None,
            ),
            (claude_events(["Done: ", "a 40 x 30 sketch."]), None),
        )
        chat, rec, calls = make_chat(stream)
        done = chat.send("make a sketch", rec.event)
        self.assertTrue(done["ok"], done)
        self.assertEqual(done["text"], "Done: a 40 x 30 sketch.")
        self.assertEqual(calls, [("create_sketch", SKETCH)])
        self.assertEqual(
            rec.kinds(),
            [
                "progress",
                "text_delta",
                "text_delta",
                "text",
                "tool_call",
                "tool_result",
                "text_delta",
                "text_delta",
                "text",
                "done",
            ],
        )
        self.assertEqual(rec.events[3][1], {"text": "Making a sketch.", "streamed": True})
        self.assertEqual(rec.events[1][1], {"text": "Making "})
        # the requests asked for a stream; the second carries the tool's answer, and the
        # first answer went back as it came (thinking signed, the call's whole arguments)
        self.assertTrue(all(r["body"]["stream"] for r in stream.requests))
        messages = stream.requests[1]["body"]["messages"]
        self.assertEqual(messages[1]["content"][0]["signature"], "SIG==")
        self.assertEqual(messages[1]["content"][2]["input"], SKETCH)
        self.assertEqual(messages[2]["content"][0]["type"], "tool_result")
        self.assertIn("Sketch1", json.dumps(messages[2]))
        self.assertEqual(chat.usage["output_tokens"], 84)
        self.assertIsNone(chat._abort)

    def test_stop_in_the_middle_of_an_answer(self):
        events = claude_events(["One ", "two ", "three ", "four."])
        stream = FakeStream((events, ("stop_after", 5)))
        chat, rec, calls = make_chat(stream)
        done = chat.send("count", rec.event)
        self.assertEqual((done["ok"], done["reason"]), (True, "stopped"))
        self.assertEqual(stream.aborted, 1)  # (the connection was closed at once)
        shown = "".join(d["text"] for k, d in rec.events if k == "text_delta")
        self.assertEqual(shown, "One two ")
        self.assertEqual(rec.events[-2], ("text", {"text": "One two", "streamed": True}))
        self.assertEqual(chat.history[-1], {"role": "assistant", "text": "One two"})
        self.assertFalse(chat.busy())
        # the next message goes on from there
        stream.answers.append((claude_events(["Five."]), None))
        done = chat.send("go on", rec.event)
        self.assertEqual(done["text"], "Five.")
        roles = [m["role"] for m in stream.requests[-1]["body"]["messages"]]
        self.assertEqual(roles, ["user", "assistant", "user"])

    def test_a_connection_lost_in_the_middle(self):
        stream = FakeStream(
            (
                claude_events(["Half an ", "answer"])[:6],
                ("cut", "network: [Errno 104] Connection reset by peer"),
            )
        )
        chat, rec, calls = make_chat(stream)
        done = chat.send("hello", rec.event)
        self.assertEqual((done["ok"], done["reason"]), (False, "error"))
        self.assertIn("connection to Claude (Anthropic) was lost", done["text"])
        self.assertIn("Connection reset by peer", done["text"])
        self.assertEqual(len(stream.requests), 1)  # (words were shown: not asked again)
        errors = [d for k, d in rec.events if k == "error"]
        self.assertEqual(len(errors), 1)
        # an answer that just ended without its end mark
        stream = FakeStream((claude_events(["Half"])[:4], None))
        chat, rec, calls = make_chat(stream)
        done = chat.send("hello", rec.event)
        self.assertIn("was lost before the answer was complete (it ended early)", done["text"])

    def test_an_error_event_before_any_word_is_asked_again(self):
        overloaded = [
            (
                "error",
                {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}},
            )
        ]
        stream = FakeStream((overloaded, None), (claude_events(["Fine."]), None))
        chat, rec, calls = make_chat(stream)
        done = chat.send("hi", rec.event)
        self.assertEqual(done["text"], "Fine.")
        self.assertEqual(len(stream.requests), 2)
        stream = FakeStream((overloaded, None), (overloaded, None), (overloaded, None))
        chat, rec, calls = make_chat(stream)
        done = chat.send("hi", rec.event)
        self.assertIn("had a problem (error 529)", done["text"])

    def test_a_server_that_does_not_stream(self):
        # it answers in one piece (application/json): read the old way, shown at once
        plain = (
            200,
            {
                "type": "message",
                "content": [{"type": "text", "text": "One piece."}],
                "stop_reason": "end_turn",
                "usage": {},
            },
            None,
        )
        stream = FakeStream(("plain", plain))
        chat, rec, calls = make_chat(stream)
        done = chat.send("hi", rec.event)
        self.assertEqual(done["text"], "One piece.")
        self.assertEqual(rec.kinds(), ["text", "done"])
        self.assertEqual(rec.events[0][1], "One piece.")
        # it refuses a streamed request (400): asked again in one piece, and from then on
        refused = (400, {"error": {"message": "stream not supported"}}, None)
        stream = FakeStream(("plain", refused))
        one_piece = []

        def http(url, headers, body):
            one_piece.append(body)
            return (
                200,
                {
                    "type": "message",
                    "content": [{"type": "text", "text": "Ok."}],
                    "stop_reason": "end_turn",
                    "usage": {},
                },
                None,
            )

        chat, rec, calls = make_chat(stream, http=http)
        self.assertEqual(chat.send("hi", rec.event)["text"], "Ok.")
        self.assertEqual(chat.send("again", rec.event)["text"], "Ok.")
        self.assertEqual(len(stream.requests), 1)
        self.assertEqual(len(one_piece), 2)
        self.assertNotIn("stream", one_piece[0])
        self.assertFalse(chat.streams())

    def test_a_400_that_is_not_about_streaming(self):
        bad = (400, {"error": {"message": "prompt is too long"}}, None)
        stream = FakeStream(("plain", bad))
        chat, rec, calls = make_chat(stream, http=lambda *a: bad)
        done = chat.send("hi", rec.event)
        self.assertIn("prompt is too long", done["text"])
        self.assertTrue(chat.streams())  # (still streams next time)

    def test_the_default_streams_and_a_fake_http_does_not(self):
        chat = chat_core.Chat(anthropic.Adapter(), "claude-opus-5-5", key=KEY)
        self.assertIs(chat.stream_http, _stream.post_stream)
        self.assertTrue(chat.streams())
        chat = chat_core.Chat(anthropic.Adapter(), "m", key=KEY, http=lambda *a: None)
        self.assertFalse(chat.streams())

    def test_keys_never_show(self):
        stream = FakeStream(("plain", (401, {"error": {"message": "bad key %s" % KEY}}, None)))
        chat, rec, calls = make_chat(stream, http=lambda *a: (401, {}, None))
        done = chat.send("hi", rec.event)
        self.assertIn("key was refused", done["text"])
        self.assertNotIn(KEY, json.dumps(rec.events) + json.dumps(rec.lines))


# -- over real HTTP --------------------------------------------------------------------------
class _SSEServer(http.server.BaseHTTPRequestHandler):
    """Streams the scripted events of a plan, a piece at a time (chunked, HTTP/1.1)."""

    protocol_version = "HTTP/1.1"
    plans = []
    log = []

    def log_message(self, *_args):
        pass

    def chunk(self, text):
        raw = text.encode("utf-8")
        self.wfile.write(b"%x\r\n%s\r\n" % (len(raw), raw))
        self.wfile.flush()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        plan = type(self).plans.pop(0)
        type(self).log.append(body)
        if plan.get("json") is not None:
            raw = json.dumps(plan["json"]).encode("utf-8")
            self.send_response(plan.get("status", 200))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            for number, (name, data) in enumerate(plan["events"]):
                self.chunk(sse(name, data))
                gate = plan.get("gate")
                if gate is not None and number == plan.get("gate_after", 0):
                    # the client must have shown this event before the rest is sent
                    plan["read_while_sending"] = gate.wait(5)
                if plan.get("hold_after") == number:
                    plan["held"].wait(10)  # (until the test is over: Stop must not wait)
                    return
                if plan.get("drop_after") == number:
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
            self.wfile.write(b"0\r\n\r\n")
        except OSError:
            plan["client_left"] = True


class OverHttp(unittest.TestCase):
    def setUp(self):
        _SSEServer.plans, _SSEServer.log = [], []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _SSEServer)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        for plan in _SSEServer.plans:
            if plan.get("held") is not None:
                plan["held"].set()
        self.server.shutdown()
        self.server.server_close()

    def test_pieces_are_read_while_the_server_is_still_sending(self):
        gate = threading.Event()
        plan = {"events": claude_events(["Hello ", "there."]), "gate": gate}
        _SSEServer.plans.append(plan)
        reader = anthropic.Adapter().stream_reader()
        shown = []

        def on_event(name, data):
            shown.extend(reader.feed(name, data))
            gate.set()
            return reader.finished

        status, data, problem, streamed = _stream.post_stream(
            self.base + "/v1/messages", {}, {"stream": True}, on_event
        )
        self.assertEqual((status, data, problem, streamed), (200, None, None, True))
        self.assertTrue(plan["read_while_sending"])
        self.assertEqual(texts(shown), "Hello there.")
        self.assertTrue(reader.complete)

    def test_a_plain_answer_and_an_http_error(self):
        _SSEServer.plans.append({"json": {"type": "message", "content": []}})
        _SSEServer.plans.append({"json": {"error": {"message": "bad key"}}, "status": 401})
        status, data, problem, streamed = _stream.post_stream(
            self.base + "/v1/messages", {}, {}, lambda n, d: None
        )
        self.assertEqual((status, data["type"], problem, streamed), (200, "message", None, False))
        status, data, problem, streamed = _stream.post_stream(
            self.base + "/v1/messages", {}, {}, lambda n, d: None
        )
        self.assertEqual((status, data["error"]["message"], streamed), (401, "bad key", False))
        status, data, problem, streamed = _stream.post_stream(
            "http://127.0.0.1:9/v1", {}, {}, lambda n, d: None, timeout=5
        )
        self.assertEqual((status, problem, streamed), (0, "refused", False))

    def test_stop_closes_the_connection_at_once(self):
        held = threading.Event()
        events = claude_events(["Thinking it over"])
        plan = {"events": events, "hold_after": 3, "held": held}
        _SSEServer.plans.append(plan)
        stop = threading.Event()
        box = {}

        def on_open(abort):
            if abort is not None:
                box["abort"] = abort

        def on_event(name, data):
            if name == "content_block_delta" and "abort" in box:
                # Stop pressed (on another thread) while the server holds the answer open
                def press():
                    stop.set()
                    box["abort"]()

                threading.Timer(0.2, press).start()

        start = time.monotonic()
        status, data, problem, streamed = _stream.post_stream(
            self.base + "/v1/messages", {}, {}, on_event, stop.is_set, on_open, timeout=30
        )
        took = time.monotonic() - start
        held.set()
        self.assertEqual((problem, streamed), ("stopped", True))
        self.assertLess(took, 5, "Stop waited for the server")

    def test_a_dropped_connection(self):
        plan = {"events": claude_events(["Half ", "an answer"]), "drop_after": 4}
        _SSEServer.plans.append(plan)
        reader = anthropic.Adapter().stream_reader()
        status, data, problem, streamed = _stream.post_stream(
            self.base + "/v1/messages",
            {},
            {},
            lambda n, d: reader.feed(n, d) and False,
            timeout=10,
        )
        self.assertTrue(streamed)
        self.assertFalse(reader.complete)
        self.assertTrue(problem is None or problem.startswith("cut"), problem)

    def test_a_whole_chat_with_a_tool_call(self):
        gate = threading.Event()
        first = {
            "events": claude_events(
                ["On ", "it."], tool=("toolu_9", "create_sketch", SKETCH), stop="tool_use"
            ),
            "gate": gate,
            "gate_after": 3,
        }
        _SSEServer.plans.append(first)
        _SSEServer.plans.append({"events": claude_events(["Done."])})
        rec = Recorder()
        calls = []

        def on_event(kind, data):
            rec.event(kind, data)
            if kind == "text_delta":
                gate.set()

        chat = chat_core.Chat(
            anthropic.Adapter(),
            "claude-opus-5-5",
            key=KEY,
            base_url=self.base,
            call_tool=lambda n, a: calls.append((n, a)) or {"text": "ok"},
            log=rec.log,
        )
        done = chat.send("make a sketch", on_event)
        self.assertEqual(done["text"], "Done.")
        self.assertEqual(calls, [("create_sketch", SKETCH)])
        self.assertEqual(_SSEServer.plans, [])
        self.assertTrue(first["read_while_sending"])  # ("On " shown while the rest was held)
        self.assertTrue(all(body.get("stream") for body in _SSEServer.log))
        self.assertIn("text_delta", rec.kinds())
        self.assertNotIn(KEY, json.dumps(rec.lines))


if __name__ == "__main__":
    unittest.main()
