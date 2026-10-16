"""The `fumi` command: start the local server and open the browser."""

import argparse
import socket
import threading
import webbrowser
from pathlib import Path

import uvicorn

from fumi import spec
from fumi.server import create_app

HOST = "127.0.0.1"
PORT = 3737  # Easy to remember and always the same.


def port_free() -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((HOST, PORT))
            return True
        except OSError:
            return False


class Server(uvicorn.Server):
    """Closes open event streams first so Ctrl+C exits at once and quietly."""

    def __init__(self, app):
        super().__init__(uvicorn.Config(app, host=HOST, port=PORT, log_level="warning"))
        self.events = app.state.events

    def handle_exit(self, sig, frame) -> None:
        self.events.close()
        super().handle_exit(sig, frame)


def main() -> None:
    parser = argparse.ArgumentParser(prog="fumi", description="A calm local workbench for any API with an OpenAPI file.")
    parser.add_argument("spec", nargs="?", help="OpenAPI JSON file to open")
    parser.add_argument("--no-browser", action="store_true", help="print the address instead of opening it")
    args = parser.parse_args()

    initial = None
    if args.spec:
        try:
            initial = spec.resolve(args.spec)
        except spec.SpecError as e:
            raise SystemExit(str(e))
    if not port_free():
        raise SystemExit(f"Port {PORT} is busy. Fumi is probably running already: stop it first.")

    url = f"http://{HOST}:{PORT}"
    print(f"fumi running at {url}")
    if not args.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    Server(create_app(initial)).run()


if __name__ == "__main__":
    main()
