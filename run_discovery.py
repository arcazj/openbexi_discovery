"""Start the complete local application from a terminal or IntelliJ Run/Debug."""
import argparse
import errno
import os
import socket
import sys
from pathlib import Path


def create_listener(port, allow_fallback=True):
    candidates = [port]
    if port and allow_fallback:
        candidates.extend(range(port + 1, min(port + 11, 65536)))
    for index, candidate in enumerate(candidates):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if os.name == "nt":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", candidate))
            listener.listen(128)
            listener.setblocking(False)
            return listener
        except OSError as exc:
            listener.close()
            unavailable = exc.errno in {errno.EACCES, errno.EADDRINUSE, errno.EPERM} or getattr(exc, "winerror", None) in {10013, 10048}
            if not unavailable or index == len(candidates) - 1:
                raise


def run(port=8000, allow_fallback=True):
    try:
        import uvicorn
        from backend.app import app
    except ModuleNotFoundError as exc:
        root = Path(__file__).resolve().parent
        interpreter = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        install_command = ('& ' if os.name == "nt" else '') + '"' + str(interpreter) + '" -m pip install -r "' + str(root / "requirements.lock.txt") + '"'
        raise SystemExit(
            "Missing dependency: " + str(exc.name) + "\n"
            "Current interpreter: " + sys.executable + "\n"
            "In IntelliJ, edit THIS Run/Debug configuration and select the project interpreter:\n"
            + str(interpreter) + "\n"
            "Then stop the current session and run it again. The module interpreter does not override an existing configuration's explicit interpreter.\n"
            "If the project environment needs packages, run: " + install_command
        ) from None
    try:
        listener = create_listener(port, allow_fallback)
    except OSError:
        raise SystemExit("Cannot open a local port. Stop the previous Run session or use --port 0.") from None
    actual = listener.getsockname()[1]
    if port and port != actual:
        print("Requested port is busy; using " + str(actual) + ". Browser-only legacy storage belongs to its original URL.", flush=True)
    print("OpenBEXI Discovery - full application: http://127.0.0.1:" + str(actual), flush=True)
    print("Profiles, themes, library, SQLite, quizzes, and AI settings are available. AI generation requires your configured key.", flush=True)
    print("Project: " + str(Path(__file__).resolve().parent), flush=True)
    try:
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=actual)).run(sockets=[listener])
    finally:
        listener.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--strict-port", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    run(args.port, not args.strict_port)


if __name__ == "__main__":
    main()
