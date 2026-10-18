"""Start Discovery; --browser-only serves the restricted static demo instead."""

import argparse
import errno
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8765
FALLBACK_PORTS = range(DEFAULT_PORT, DEFAULT_PORT + 11)
DOCUMENTS = {
    "README.md", "CHANGELOG.md", "WINDOWS_INSTALLATION.md", "HELP.md", "COMMERCIAL_LICENSING.md",
    "THIRD_PARTY_NOTICES.md", "REI_RESEARCH_EXPLORER_PROMPT.md",
    "RELEASE-NOTES-v1.2.0.md",
    "RELEASE-NOTES-v1.2.1.md",
    "RELEASE-NOTES-v1.2.2.md",
}


class FrontendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._serve(send_body=True)

    def do_HEAD(self):
        self._serve(send_body=False)

    def _serve(self, send_body):
        route = unquote(urlsplit(self.path).path)
        file_path = None
        media_type = "text/plain; charset=utf-8"
        if route in {"/", "/index.html"}:
            file_path = ROOT / "index.html"
            media_type = "text/html; charset=utf-8"
        elif route.lstrip("/") in DOCUMENTS and route.count("/") == 1:
            file_path = ROOT / route[1:]
        elif route.startswith("/api/docs/") and route[10:] in DOCUMENTS:
            file_path = ROOT / route[10:]
        elif route in {"/assets/discovery.js", "/assets/discovery.css", "/assets/data.js", "/assets/customize.js",
                       "/assets/captions.js", "/assets/profile_ai.js", "/assets/ai_progress.js", "/assets/search.js", "/assets/search.css"}:
            file_path = ROOT / route[1:]
            media_type = "text/javascript; charset=utf-8" if route.endswith(".js") else "text/css; charset=utf-8"
        elif route.startswith("/documentation/"):
            candidate = (ROOT / route[1:]).resolve()
            if candidate.parent == (ROOT / "documentation").resolve() and candidate.suffix == ".md":
                file_path = candidate
        elif route.startswith("/licenses/"):
            name = route[10:]
            license_root = (ROOT / "licenses").resolve()
            candidate = (license_root / name).resolve()
            if candidate.parent == license_root and candidate.suffix == ".txt" and candidate.is_file():
                file_path = candidate
        if file_path is None or not file_path.is_file():
            self.send_error(404, "Resource not available")
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(content)


class LocalFrontendServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can let a second server take over an occupied port.
    allow_reuse_address = os.name != "nt"


def create_server(port, allow_fallback=True):
    candidates = [port]
    if port and allow_fallback:
        candidates.extend(candidate for candidate in FALLBACK_PORTS if candidate != port)
    for index, candidate in enumerate(candidates):
        try:
            return LocalFrontendServer(("127.0.0.1", candidate), FrontendHandler)
        except OSError as exc:
            unavailable = exc.errno in {errno.EACCES, errno.EADDRINUSE, errno.EPERM} or getattr(exc, "winerror", None) in {10013, 10048}
            if not unavailable or index == len(candidates) - 1:
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="Preferred port (default: 8765); 0 lets Windows/the OS choose.")
    parser.add_argument("--strict-port", action="store_true",
                        help="Fail if the requested port is unavailable instead of trying alternatives.")
    parser.add_argument("--browser-only", action="store_true", help="Serve only static HTML; profiles and the library require a separate backend.")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    if not args.browser_only:
        from run_discovery import run
        run(args.port, allow_fallback=not args.strict_port)
        return
    try:
        server = create_server(args.port, allow_fallback=not args.strict_port)
    except OSError:
        parser.exit(1, "Cannot start the frontend: the port is occupied or blocked. Try --port 0 for an available port.\n")
    actual_port = server.server_address[1]
    if args.port and actual_port != args.port:
        print("Port " + str(args.port) + " is occupied or blocked; using " + str(actual_port) + ".", flush=True)
        print("A different port has separate browser storage. Restore saved research from your JSON backup if needed.", flush=True)
    print("Frontend: http://127.0.0.1:" + str(actual_port), flush=True)
    print("Standalone HTML. For AI and all sources, keep the Python backend running on port 8000; the page connects automatically.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
