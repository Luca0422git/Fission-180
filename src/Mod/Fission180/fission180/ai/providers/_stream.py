# SPDX-License-Identifier: LGPL-2.1-or-later
"""Answers that arrive word by word ("streaming"), as Claude's and ChatGPT's own apps show them.

Every provider here can send its answer as server-sent events (SSE: the "text/event-stream"
format, lines of "event: ..." and "data: ..." with a blank line after each event) instead of
one JSON document at the end. Two parts:

  post_stream(url, headers, body, on_event, should_stop, on_open)
      the request, read event by event; never raises. A server that answers with one plain
      JSON document after all (an error, or a server that does not stream) gets the same
      answer as request_json gives, so the chat falls back to the non-streamed way.
  StreamReader (one subclass in each adapter module, adapter.stream_reader())
      reads the events of one answer: feed(name, data) says which pieces of text (and which
      thinking notes) to show at once, and result() gives back the answer the
      non-streamed request would have given, so the adapter's parse_response reads it as
      before (tool calls, stop reasons, usage, the "raw" turn kept for the history).

Stop: should_stop() is asked after every line, and on_open hands the caller a function
that closes the connection from another thread (the chat panel's Stop), so a stream that
waits for its next piece ends at once too.

Pure Python standard library: no FreeCAD, no Qt.
"""

import json
import socket
import urllib.error
import urllib.request

from . import _common

STRAY = "_stray"  # the event name given to lines that are not SSE (a JSON error, say)


class SSEParser:
    """The server-sent events format (html.spec.whatwg.org, "Server-sent events"), fed line
    by line (without the line break): "event:" names the event, "data:" lines (several are
    joined with line breaks) hold its text, a blank line ends it; "id:" and "retry:" are
    not needed here and lines starting with ":" are comments (keep-alive). Lines that are
    none of these are kept in `stray` (some servers send an error as plain JSON lines)."""

    def __init__(self):
        self.event = ""
        self.data = []
        self.stray = []

    def feed_line(self, line):
        """One line -> (event name, data) when the line ends an event, else None."""
        if line == "":
            if not self.data:
                self.event = ""
                return None
            done = (self.event or "message", "\n".join(self.data))
            self.event, self.data = "", []
            return done
        if line.startswith(":"):
            return None
        field, colon, value = line.partition(":")
        if colon and value.startswith(" "):
            value = value[1:]
        if field == "event":
            self.event = value
        elif field == "data":
            self.data.append(value)
        elif field not in ("id", "retry"):
            self.stray.append(line)
        return None

    def finish(self):
        """At the end of the answer: an event whose closing blank line never came."""
        return self.feed_line("")


def _aborter(answer):
    """A function that ends the reading of `answer` at once from another thread: it shuts
    the connection down (the plain socket's shutdown, also under TLS), so the reading
    thread's wait for the next line returns."""

    def abort():
        try:
            sock = answer.fp.raw._sock
            socket.socket.shutdown(sock, socket.SHUT_RDWR)
        except Exception:  # already closed, or not a socket we know: the line check stops it
            pass

    return abort


def read_events(answer, on_event, should_stop=None):
    """Read an open text/event-stream answer to its end. on_event(name, data) for each
    event; when it returns True the answer is complete and reading stops. Returns None
    (read to the end), "stopped" (should_stop() said so) or "cut: <reason>" (the
    connection broke off)."""
    parser = SSEParser()
    while True:
        if should_stop is not None and should_stop():
            return "stopped"
        try:
            line = answer.readline()
        except Exception as exc:
            if should_stop is not None and should_stop():
                return "stopped"  # (Stop closed the connection under the reading)
            return "cut: %s" % _common._problem(exc)
        if not line:
            break
        text = line.decode("utf-8", "replace").rstrip("\r\n")
        for part in text.split("\r"):  # (a lone CR ends a line too)
            event = parser.feed_line(part)
            if event is not None and on_event(*event):
                return None
    if should_stop is not None and should_stop():
        return "stopped"
    event = parser.finish()
    if event is not None and on_event(*event):
        return None
    if parser.stray:
        on_event(STRAY, "\n".join(parser.stray))
    return None


def post_stream(
    url,
    headers,
    body,
    on_event,
    should_stop=None,
    on_open=None,
    timeout=_common.DEFAULT_TIMEOUT,
):
    """POST JSON and read the answer as server-sent events. Never raises.

    on_event(name, data): each event (see read_events); should_stop(): asked after every
    line; on_open(abort): called with a function that ends the reading at once from
    another thread while the answer is read, and with None when it is over. timeout:
    the longest wait for the answer to start and for each next line.

    Returns (status, data, problem, streamed):
      streamed True: the answer came as a stream; data None; problem None (read to its
        end; the reader says whether it was complete), "stopped" or "cut: <reason>";
      streamed False: a plain answer (an HTTP error, or a server that does not stream):
        status, data and problem as request_json gives them."""
    try:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        all_headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
        all_headers.update(headers or {})
        req = urllib.request.Request(url, data=payload, headers=all_headers, method="POST")
        try:
            answer = _common._opener(url).open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read()
            except Exception:
                raw = b""
            data, problem = _common.decode_answer(exc.code, raw)
            return exc.code, data, problem, False
        except (urllib.error.URLError, OSError) as exc:
            return 0, None, _common._problem(exc), False
        with answer:
            status = answer.status
            kind = (answer.headers.get("Content-Type") or "").lower()
            if "text/event-stream" not in kind:
                data, problem = _common.decode_answer(status, answer.read())
                return status, data, problem, False
            if on_open is not None:
                on_open(_aborter(answer))
            try:
                problem = read_events(answer, on_event, should_stop)
            finally:
                if on_open is not None:
                    on_open(None)
            return status, None, problem, True
    except Exception as exc:  # a broken URL or anything else: still an answer
        return 0, None, "network: %s" % exc, False


class StreamReader:
    """Collects one streamed answer; each adapter module has its own subclass.

    feed(name, data) -> [("text", piece) | ("progress", note), ...] to show now
    complete   the provider said the answer is complete (else it broke off)
    finished   nothing more to read (the provider's end mark came)
    error      (status, data) when the provider sent an error inside the stream
    result()   the answer as the non-streamed request gives it (for parse_response)

    The text pieces put together are the turn's text as parse_response joins it: a new
    block of text after an earlier one starts with a blank line."""

    def __init__(self):
        self.complete = False
        self.finished = False
        self.error = None
        self._shown = False  # some text was shown already
        self._fresh = True  # the next piece starts a new block of text

    def feed(self, name, data):
        """Never raises: a piece in a shape we do not know is skipped."""
        try:
            if name == STRAY:
                return self._stray(data) or []
            data = (data or "").strip()
            if not data:
                return []
            if data == "[DONE]":
                return self._done() or []
            try:
                event = json.loads(data)
            except ValueError:
                return []
            if not isinstance(event, dict):
                return []
            return self._feed(name, event) or []
        except Exception:
            return []

    def result(self):
        return {}

    # -- for the subclasses
    def _feed(self, name, event):
        return []

    def _done(self):
        self.finished = True
        return []

    def _stray(self, text):
        """Lines that were not SSE: a JSON error some servers send that way."""
        try:
            data = json.loads(text)
        except ValueError:
            return []
        if isinstance(data, dict) and data.get("error"):
            self._set_error(data)
        return []

    def _set_error(self, data, status=None):
        error = data.get("error") if isinstance(data, dict) else None
        if status is None:
            status = error_status(error)
        self.error = (status, data if isinstance(data, dict) else {"error": data})
        self.finished = True

    def _new_block(self):
        self._fresh = True

    def _text(self, piece):
        if not isinstance(piece, str) or not piece:
            return []
        if self._fresh and self._shown:
            piece = "\n\n" + piece
        self._fresh = False
        self._shown = True
        return [("text", piece)]


# an error sent inside a stream (the HTTP status was 200 already) -> the status it stands for
_ERROR_STATUS = {
    # Anthropic's error types
    "invalid_request_error": 400,
    "authentication_error": 401,
    "billing_error": 402,
    "permission_error": 403,
    "not_found_error": 404,
    "request_too_large": 413,
    "rate_limit_error": 429,
    "api_error": 500,
    "timeout_error": 504,
    "overloaded_error": 529,
    # OpenAI's error codes and Google's status words
    "rate_limit_exceeded": 429,
    "insufficient_quota": 429,
    "server_error": 500,
    "RESOURCE_EXHAUSTED": 429,
    "INTERNAL": 500,
    "UNAVAILABLE": 503,
    "DEADLINE_EXCEEDED": 504,
    "INVALID_ARGUMENT": 400,
    "PERMISSION_DENIED": 403,
    "UNAUTHENTICATED": 401,
    "NOT_FOUND": 404,
}


def error_status(error):
    """The HTTP status an error inside a stream stands for (500 when nothing says)."""
    if not isinstance(error, dict):
        return 500
    code = error.get("code")
    if isinstance(code, int) and 400 <= code < 600:
        return code
    for key in ("type", "code", "status"):
        value = error.get(key)
        if isinstance(value, str) and value in _ERROR_STATUS:
            return _ERROR_STATUS[value]
    words = " ".join(str(error.get(k) or "") for k in ("type", "code", "status")).lower()
    if "rate" in words or "quota" in words:
        return 429
    if "invalid" in words:
        return 400
    return 500
