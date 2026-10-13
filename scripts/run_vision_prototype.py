"""Serve only the read-only visual study on loopback; no actuarial runtime data."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if __name__ == "__main__":
    directory = Path(__file__).resolve().parents[1] / "web" / "vision-prototype"
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 8766), handler)
    print("Read-only vision prototype: http://127.0.0.1:8766/index.html?variant=A", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
