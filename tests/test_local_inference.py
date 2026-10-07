import json
import threading
import time

import pytest

from actuarial_library.local_inference import InferenceInterrupted, stream_chat


class FakeConnection:
    def __init__(self, events=None, stall=False):
        self.sock = self
        self.closed = threading.Event()
        self.events = iter(events or [])
        self.stall = stall
        self.status = 200
        self.sent = None

    def request(self, method, path, body, headers):
        self.sent = json.loads(body)

    def getresponse(self):
        return self

    def readline(self, limit):
        if self.stall:
            self.closed.wait(3)
            return b""
        event = next(self.events, None)
        return json.dumps(event).encode() + b"\n" if event is not None else b""

    def shutdown(self, _):
        self.closed.set()

    def close(self):
        self.closed.set()


def test_stream_collects_tools_and_timing_without_exposing_reasoning():
    connection = FakeConnection(
        [
            {"message": {"thinking": "hidden", "content": "Ready "}},
            {
                "message": {
                    "content": "now",
                    "tool_calls": [{"function": {"name": "overview", "arguments": {}}}],
                }
            },
            {"done": True, "eval_count": 20, "eval_duration": 1_000_000_000},
        ]
    )
    result = stream_chat({"model": "fake"}, lambda _: None, connection_factory=lambda *a, **kw: connection)
    assert result["message"]["content"] == "Ready now"
    assert len(result["message"]["tool_calls"]) == 1
    assert "hidden" not in json.dumps(result)
    assert result["timing"]["tokens_per_second"] == 20
    assert connection.sent["stream"] is True and connection.closed.is_set()


def test_partial_stream_is_never_returned_as_a_completed_tool_call():
    connection = FakeConnection([{"message": {"tool_calls": [{"function": {"name": "create_artifact"}}]}}])
    with pytest.raises(InferenceInterrupted, match="incomplete"):
        stream_chat({}, lambda _: None, connection_factory=lambda *a, **kw: connection)


def test_deadline_interrupts_stalled_socket_without_waiting_for_generation():
    connection = FakeConnection(stall=True)
    start = time.monotonic()
    with pytest.raises(InferenceInterrupted, match="budget"):
        stream_chat({}, lambda _: None, timeout=0.05, connection_factory=lambda *a, **kw: connection)
    assert time.monotonic() - start < 1
    assert connection.closed.is_set()


def test_cancel_callback_interrupts_inflight_io():
    connection = FakeConnection(stall=True)

    def cancelled(_):
        raise ValueError("Cancelled")

    with pytest.raises(ValueError, match="Cancelled"):
        stream_chat({}, cancelled, connection_factory=lambda *a, **kw: connection)
    assert connection.closed.is_set()
