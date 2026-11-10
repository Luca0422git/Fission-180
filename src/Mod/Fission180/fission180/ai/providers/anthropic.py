# SPDX-License-Identifier: LGPL-2.1-or-later
"""Claude through Anthropic's Messages API (POST /v1/messages), with plain urllib.

Checked against Anthropic's claude-api reference (October 2026):
  * headers x-api-key, anthropic-version: 2023-06-01, and anthropic-beta (comma-separated)
    for beta features;
  * tools are {name, description, input_schema}; the answer's content is a list of blocks
    (text, thinking, tool_use {id, name, input}); stop_reason end_turn, tool_use,
    max_tokens, refusal, pause_turn...;
  * tool results go back in ONE user message of tool_result blocks {tool_use_id, content,
    is_error}; content may hold text and image blocks (base64 PNG), so screenshots work;
  * the assistant turn is sent back exactly as it came (thinking blocks included);
  * GET /v1/models lists the models (data[].id, has_more, last_id).
Model-specific extras, only for the models known to take them (anything else gets the
plain request): an explicit effort (Claude Opus 5.5 defaults to medium; we say it), the
"updates" thinking display so the short notes the model writes between tool calls reach
the chat panel. No server-side fallback to another model: the chat always talks to the
model the person picked (a reply that comes back after a fallback elsewhere is still read).
Top-level cache_control caches the repeated tools + history: an agent loop resends them
every step, so this cuts the cost a lot.

Streaming ("stream": true, server-sent events; StreamReader below, put together as the
anthropic SDK 2.7.0's lib/streaming accumulate_event does, read November 2026):
message_start (the message without content), content_block_start / content_block_delta
(text_delta, input_json_delta: a tool call's arguments in pieces of JSON text,
thinking_delta, signature_delta, citations_delta, compaction_delta) / content_block_stop
for each block, message_delta (the stop_reason and the usage so far: totals, not
additions), message_stop; ping events keep the connection open and an error event
(overloaded_error...) can come in the middle. The blocks are put together into the message
the non-streamed request returns.
"""

import copy
import json

from . import _common, _stream

NAME = "anthropic"
DISPLAY_NAME = "Claude (Anthropic)"
NEEDS_KEY = True
BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-opus-5-5"
SUPPORTS_IMAGES = True
API_VERSION = "2023-06-01"
MAX_TOKENS = 16000
EFFORT = "medium"  # balanced cost and care; the person pays per use

BETA_UPDATES = "thinking-display-updates-2026-08-18"

_EFFORT_MODELS = {
    "claude-fable-5-1",
    "claude-fable-5",
    "claude-mythos-5-1",
    "claude-mythos-5",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5-5",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-haiku-5-5",
}
_UPDATES_MODELS = {
    "claude-fable-5-1",
    "claude-mythos-5-1",
    "claude-fable-5",
    "claude-opus-5-5",
    "claude-sonnet-5-5",
}

_STOPS = {
    "end_turn": "end",
    "stop_sequence": "end",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "model_context_window_exceeded": "max_tokens",
    "refusal": "refusal",
    "pause_turn": "pause",
}


class Adapter:
    name = NAME
    display_name = DISPLAY_NAME
    needs_key = NEEDS_KEY
    base_url = BASE_URL
    default_model = DEFAULT_MODEL
    supports_images = SUPPORTS_IMAGES

    def tools(self, tools):
        return [
            {"name": name, "description": description, "input_schema": copy.deepcopy(schema)}
            for name, description, schema in _common.tool_list(tools)
        ]

    def build_request(
        self, model, system, messages, tools, max_tokens=MAX_TOKENS, key=None, base_url=None
    ):
        base = base_url or BASE_URL
        headers = {"anthropic-version": API_VERSION, "content-type": "application/json"}
        if key:
            headers["x-api-key"] = key
        body = {
            "model": model,
            "max_tokens": int(max_tokens or MAX_TOKENS),
            "cache_control": {"type": "ephemeral"},
            "messages": messages,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = self.tools(tools)
        betas = []
        if model in _EFFORT_MODELS and EFFORT:
            body["output_config"] = {"effort": EFFORT}
        if model in _UPDATES_MODELS:
            body["thinking"] = {"type": "adaptive", "display": "updates"}
            betas.append(BETA_UPDATES)
        if betas:
            headers["anthropic-beta"] = ",".join(betas)
        return _common.join(base, "/v1/messages"), headers, body

    def stream_request(self, url, headers, body):
        """The same request, answered as a stream."""
        body = dict(body)
        body["stream"] = True
        return url, dict(headers), body

    def stream_reader(self):
        return StreamReader()

    def parse_response(self, data):
        try:
            return self._parse(data)
        except Exception:  # an answer in a shape we do not know
            return _common.neutral_turn(stop="unreadable")

    def _parse(self, data):
        data = data if isinstance(data, dict) else {}
        content = _after_fallback(data.get("content") or [])
        texts, calls, progress = [], [], []
        for index, block in enumerate(content):
            kind = block.get("type") if isinstance(block, dict) else None
            if kind == "text" and block.get("text"):
                texts.append(block["text"])
            elif kind == "thinking" and (block.get("thinking") or "").strip():
                progress.append(block["thinking"].strip())
            elif kind == "tool_use":
                args = block.get("input")
                call = {"id": block.get("id") or "call_%d" % index, "name": block.get("name")}
                if isinstance(args, dict):
                    call["args"] = args
                else:
                    call["args"], call["bad_args"] = {}, "the arguments must be a JSON object"
                calls.append(call)
        usage = data.get("usage") or {}
        stop = _STOPS.get(data.get("stop_reason"), data.get("stop_reason") or "end")
        return _common.neutral_turn(
            text="\n\n".join(texts),
            tool_calls=calls,
            stop=stop,
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            },
            progress=progress,
            raw={"provider": NAME, "model": data.get("model"), "content": content},
        )

    def tool_results_message(self, calls_and_results):
        blocks = []
        for call, result in calls_and_results:
            content = [{"type": "text", "text": _common.result_text(result)}]
            image = result.get("image_png_base64") if isinstance(result, dict) else None
            if image:
                content.append(
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": image},
                    }
                )
            block = {
                "type": "tool_result",
                "tool_use_id": _common.safe_id(call.get("id")),
                "content": content,
            }
            if isinstance(result, dict) and result.get("is_error"):
                block["is_error"] = True
            blocks.append(block)
        return [{"role": "user", "content": blocks}] if blocks else []

    def to_provider_messages(self, history, model=None):
        messages = []
        for entry in history:
            if entry.get("role") == "user":
                if entry.get("tool_results"):
                    pairs = [(r["call"], r["result"]) for r in entry["tool_results"]]
                    messages.extend(self.tool_results_message(pairs))
                elif entry.get("text"):
                    messages.append({"role": "user", "content": entry["text"]})
                continue
            raw = _common.raw_for(entry, NAME)  # any Claude model: the API drops what it
            if raw and raw.get("content"):  # cannot read, so the turn goes back unchanged
                content = copy.deepcopy(raw["content"])
            else:
                content = []
                if entry.get("text"):
                    content.append({"type": "text", "text": entry["text"]})
                for index, call in enumerate(entry.get("tool_calls") or []):
                    content.append(
                        {
                            "type": "tool_use",
                            "id": _common.safe_id(call.get("id"), index),
                            "name": call.get("name"),
                            "input": call.get("args") or {},
                        }
                    )
            if content:
                messages.append({"role": "assistant", "content": content})
        return messages

    def list_models(self, key, base_url=None, http_get=_common.get_json):
        """Model ids from GET /v1/models (newest first, as the API lists them); [] on any
        problem."""
        try:
            headers = {"anthropic-version": API_VERSION}
            if key:
                headers["x-api-key"] = key
            ids, after = [], None
            for _page in range(10):
                url = _common.join(base_url or BASE_URL, "/v1/models?limit=1000")
                if after:
                    url += "&after_id=" + after
                status, data, _problem = http_get(url, headers)
                if status != 200 or not isinstance(data, dict):
                    break
                ids.extend(m["id"] for m in data.get("data") or [] if m.get("id"))
                after = data.get("last_id")
                if not data.get("has_more") or not after:
                    break
            return ids
        except Exception:
            return []

    def key_refused(self, status, data):
        return status in (401, 403)


class StreamReader(_stream.StreamReader):
    """One streamed Messages answer, put back together as the message parse_response
    reads (see the module's notes)."""

    def __init__(self):
        super().__init__()
        self.message = {"type": "message", "role": "assistant", "content": [], "usage": {}}
        self.blocks = {}  # index -> the block as it grows
        self.order = []  # the indexes in the order the blocks started
        self.json = {}  # index -> a tool call's arguments so far (JSON text)
        self.stopped = False  # message_stop came

    @property
    def complete(self):
        return self.stopped or bool(self.message.get("stop_reason"))

    @complete.setter
    def complete(self, _value):
        pass  # (worked out from what came)

    def _feed(self, name, event):
        kind = event.get("type") or name
        if kind == "message_start":
            start = event.get("message") or {}
            for key, value in start.items():
                if key != "content":
                    self.message[key] = copy.deepcopy(value)
            self.message.setdefault("usage", {})
        elif kind == "content_block_start":
            index = event.get("index", len(self.order))
            block = copy.deepcopy(event.get("content_block") or {})
            if index not in self.blocks:
                self.order.append(index)
            self.blocks[index] = block
            to = block.get("to") if block.get("type") == "fallback" else None
            if isinstance(to, dict) and to.get("model"):
                self.message["model"] = to["model"]  # (the model that answered after all)
            if block.get("type") == "text":
                self._new_block()
                return self._text(block.get("text"))
        elif kind == "content_block_delta":
            return self._delta(event.get("index"), event.get("delta") or {})
        elif kind == "content_block_stop":
            return self._stop(event.get("index"))
        elif kind == "message_delta":
            delta = event.get("delta") or {}
            for key, value in delta.items():
                self.message[key] = value
            for key in ("context_management", "input_transformations"):
                if event.get(key) is not None:
                    self.message[key] = event[key]
            usage = event.get("usage") or {}
            self.message.setdefault("usage", {}).update(
                {key: value for key, value in usage.items() if value is not None}
            )
        elif kind == "message_stop":
            self.stopped = True
            self.finished = True
        elif kind == "error":
            self._set_error(event)
        return []

    def _delta(self, index, delta):
        block = self.blocks.get(index)
        if block is None:
            return []
        kind = delta.get("type")
        if kind == "text_delta":
            piece = delta.get("text") or ""
            block["text"] = (block.get("text") or "") + piece
            return self._text(piece)
        if kind == "input_json_delta":
            self.json[index] = self.json.get(index, "") + (delta.get("partial_json") or "")
        elif kind == "thinking_delta":
            block["thinking"] = (block.get("thinking") or "") + (delta.get("thinking") or "")
        elif kind == "signature_delta":
            block["signature"] = delta.get("signature") or ""
        elif kind == "citations_delta" and delta.get("citation") is not None:
            block.setdefault("citations", []).append(delta["citation"])
        elif kind == "compaction_delta":
            block["content"] = delta.get("content")
            block["encrypted_content"] = delta.get("encrypted_content")
        return []

    def _stop(self, index):
        block = self.blocks.get(index)
        if block is None:
            return []
        if index in self.json:
            block["input"] = _tool_input(self.json.pop(index))
        if block.get("type") == "thinking" and (block.get("thinking") or "").strip():
            return [("progress", block["thinking"].strip())]
        return []

    def result(self):
        message = dict(self.message)
        content = []
        for index in self.order:
            block = self.blocks[index]
            if index in self.json:  # (a block that never stopped: the answer was cut)
                block["input"] = _tool_input(self.json[index])
            content.append(block)
        message["content"] = content
        return message


def _tool_input(text):
    """A tool call's arguments from their JSON text: {} when there were none; anything
    that is not a JSON object stays {} too (the tool then says what it is missing)."""
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _after_fallback(content):
    """After a server-side fallback the blocks before the last "fallback" marker are the
    declined model's partial work: keep only its text, as Anthropic's guide says, and drop
    the marker itself."""
    content = [b for b in content if isinstance(b, dict)]
    marks = [i for i, block in enumerate(content) if block.get("type") == "fallback"]
    if not marks:
        return content
    last = marks[-1]
    before = [b for b in content[:last] if b.get("type") == "text"]
    return before + content[last + 1 :]
