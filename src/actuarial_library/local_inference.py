"""Bounded Ollama streaming with heartbeat, interruptible I/O and timing evidence."""

import http.client
import json
import queue
import socket
import threading
import time


class InferenceInterrupted(ValueError):
    """Incomplete generation; partial model output must not be executed."""


def stream_chat(payload, progress, timeout=90, connection_factory=http.client.HTTPConnection):
    """Read native NDJSON from loopback only. Never follow redirects or proxy traffic."""
    events = queue.Queue(maxsize=128)
    stopped = threading.Event()
    transport = {}
    connection = connection_factory("127.0.0.1", 11434, timeout=timeout)
    started = time.monotonic()

    def publish(item):
        while not stopped.is_set():
            try:
                events.put(item, timeout=0.2)
                return
            except queue.Full:
                pass

    def read():
        try:
            connection.request(
                "POST",
                "/api/chat",
                json.dumps({**payload, "stream": True}),
                {"Content-Type": "application/json"},
            )
            transport["socket"] = connection.sock
            response = connection.getresponse()
            if response.status != 200:
                raise InferenceInterrupted(
                    f"Ollama returned HTTP {response.status}. No response was applied."
                )
            size = 0
            while not stopped.is_set():
                line = response.readline(1_000_001)
                if not line:
                    raise InferenceInterrupted(
                        "Ollama ended an incomplete response. Completed evidence is saved."
                    )
                size += len(line)
                if len(line) > 1_000_000 or size > 8_000_000:
                    raise InferenceInterrupted("The local response exceeded the output budget.")
                event = json.loads(line)
                publish(event)
                if event.get("done") or event.get("error"):
                    return
        except (OSError, http.client.HTTPException, ValueError) as exc:
            publish(exc)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    content, calls = [], []
    chunks = 0
    last_progress = -1.0
    try:
        while True:
            elapsed = time.monotonic() - started
            if elapsed >= timeout:
                raise InferenceInterrupted(
                    f"Local model exceeded its {timeout:g}-second generation budget. "
                    "Completed evidence is saved. Choose a smaller model or use a direct workspace action."
                )
            if elapsed - last_progress >= 1:
                phase = (
                    f"Receiving local response · {chunks} chunks"
                    if chunks
                    else "Loading model / reading context"
                )
                progress(phase)
                last_progress = elapsed
            try:
                event = events.get(timeout=min(0.2, max(0.01, timeout - elapsed)))
            except queue.Empty:
                continue
            if isinstance(event, Exception):
                raise InferenceInterrupted(f"Local inference stopped: {event}") from event
            if event.get("error"):
                raise InferenceInterrupted(f"Ollama: {event['error']}")
            message = event.get("message", {})
            if message.get("content"):
                content.append(message["content"])
            calls.extend(message.get("tool_calls", []))
            chunks += 1
            if len(calls) > 4:
                raise InferenceInterrupted(
                    "Too many simultaneous tool calls; no partial calls were executed."
                )
            if event.get("done"):
                progress("Local response complete; validating evidence…")
                result = {
                    "message": {"role": "assistant", "content": "".join(content)},
                    "done_reason": event.get("done_reason"),
                }
                if calls:
                    result["message"]["tool_calls"] = calls
                metrics = {
                    key: event[key]
                    for key in (
                        "total_duration",
                        "load_duration",
                        "prompt_eval_count",
                        "prompt_eval_duration",
                        "eval_count",
                        "eval_duration",
                    )
                    if key in event
                }
                metrics["wall_seconds"] = round(time.monotonic() - started, 3)
                if metrics.get("eval_duration"):
                    metrics["tokens_per_second"] = round(
                        metrics.get("eval_count", 0) / metrics["eval_duration"] * 1e9, 2
                    )
                result["timing"] = metrics
                return result
    finally:
        stopped.set()
        sock = transport.get("socket") or connection.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()
        reader.join(timeout=1)
