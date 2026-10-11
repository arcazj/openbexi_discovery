"""Browser-only serving must keep files outside its public allowlist private."""

import errno
import http.client
import re
import socket
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch, sentinel

import serve_frontend


class QuietHandler(serve_frontend.FrontendHandler):
    def log_message(self, *args):
        pass


class BrowserOnlyServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        cls.assets = re.findall(r'(?:src|href)="(assets/[^"]+)"', (serve_frontend.ROOT / "index.html").read_text(encoding="utf-8"))
        (root / "assets").mkdir()
        for asset in cls.assets:
            (root / asset).write_text("/* public frontend asset */", encoding="utf-8")
        (root / "assets" / "private.js").write_text("private server implementation", encoding="utf-8")
        (root / "index.html").write_text("<html>research workspace</html>", encoding="utf-8")
        for document in serve_frontend.DOCUMENTS:
            (root / document).write_text("public documentation", encoding="utf-8")
        (root / "licenses").mkdir()
        (root / "licenses" / "dependency.txt").write_text("dependency license", encoding="utf-8")
        (root / ".env").write_text("OPENAI_API_KEY=secret-static-test", encoding="utf-8")
        (root / "backend").mkdir()
        (root / "backend" / "app.py").write_text("private server implementation", encoding="utf-8")
        cls.root_patch = patch.object(serve_frontend, "ROOT", root)
        cls.root_patch.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.root_patch.stop()
        cls.directory.cleanup()

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            connection.close()

    def test_frontend_documentation_and_dependency_licenses_are_reachable(self):
        paths = ["/", "/index.html", "/README.md", "/api/docs/HELP.md", "/licenses/dependency.txt"]
        for path in paths:
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertTrue(body)
                self.assertEqual(dict(headers)["X-Content-Type-Options"], "nosniff")
                self.assertNotIn(b"secret-static-test", body)

    def test_all_scripts_and_styles_referenced_by_the_workspace_are_reachable(self):
        self.assertIn("assets/ai_progress.js", self.assets)
        for asset in self.assets:
            with self.subTest(asset=asset):
                status, headers, body = self.request("/" + asset)
                self.assertEqual(status, 200)
                self.assertTrue(body)
                media_type = "text/javascript" if asset.endswith(".js") else "text/css"
                self.assertTrue(dict(headers)["Content-Type"].startswith(media_type))
                self.assertEqual(dict(headers)["X-Content-Type-Options"], "nosniff")

    def test_secret_and_server_paths_are_denied_including_encoded_traversal(self):
        paths = [
            "/.env", "/backend/app.py", "/../.env", "/%2e%2e/.env",
            "/assets/private.js",
            "/api/docs/../.env", "/api/docs/%2e%2e%2f.env",
            "/licenses/../.env", "/licenses/%2e%2e%2f.env",
            "/licenses/../backend/app.py", "/licenses/nested/dependency.txt",
        ]
        for path in paths:
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"secret-static-test", body)
                self.assertNotIn(b"private server implementation", body)

    def test_head_returns_headers_without_document_body(self):
        status, headers, body = self.request("/index.html", "HEAD")
        self.assertEqual(status, 200)
        self.assertGreater(int(dict(headers)["Content-Length"]), 0)
        self.assertEqual(body, b"")


class FrontendStartupTests(unittest.TestCase):
    def test_windows_access_denial_uses_an_alternate_local_port(self):
        denied = OSError(errno.EACCES, "fixture access denial")
        denied.winerror = 10013
        with patch.object(serve_frontend, "LocalFrontendServer", side_effect=[denied, sentinel.server]) as constructor:
            server = serve_frontend.create_server(8000)
        self.assertIs(server, sentinel.server)
        addresses = [call.args[0] for call in constructor.call_args_list]
        self.assertEqual(addresses[0], ("127.0.0.1", 8000))
        self.assertEqual(addresses[1], ("127.0.0.1", serve_frontend.DEFAULT_PORT))

    def test_busy_default_port_is_not_retried_as_its_own_fallback(self):
        busy = OSError(errno.EADDRINUSE, "fixture occupied port")
        busy.winerror = 10048
        with patch.object(serve_frontend, "LocalFrontendServer", side_effect=[busy, sentinel.server]) as constructor:
            server = serve_frontend.create_server(serve_frontend.DEFAULT_PORT)
        self.assertIs(server, sentinel.server)
        ports = [call.args[0][1] for call in constructor.call_args_list]
        self.assertEqual(ports, [serve_frontend.DEFAULT_PORT, serve_frontend.DEFAULT_PORT + 1])

    def test_windows_codes_and_posix_permission_errors_trigger_fallback(self):
        failures = [OSError(errno.EPERM, "fixture denied"), OSError(errno.EACCES, "fixture denied")]
        for code in (10013, 10048):
            failure = OSError("fixture Windows bind failure")
            failure.winerror = code
            failures.append(failure)
        for failure in failures:
            with self.subTest(errno=failure.errno, winerror=getattr(failure, "winerror", None)):
                with patch.object(serve_frontend, "LocalFrontendServer", side_effect=[failure, sentinel.server]) as constructor:
                    self.assertIs(serve_frontend.create_server(8000), sentinel.server)
                self.assertEqual(constructor.call_count, 2)

    def test_unrelated_socket_error_propagates_without_retrying(self):
        failure = OSError(errno.EIO, "fixture unrelated socket failure")
        with patch.object(serve_frontend, "LocalFrontendServer", side_effect=failure) as constructor:
            with self.assertRaises(OSError) as error:
                serve_frontend.create_server(8000)
        self.assertIs(error.exception, failure)
        self.assertEqual(constructor.call_count, 1)

    def test_strict_port_preserves_bind_error_without_fallback(self):
        busy = OSError(errno.EADDRINUSE, "fixture occupied port")
        with patch.object(serve_frontend, "LocalFrontendServer", side_effect=busy) as constructor:
            with self.assertRaises(OSError) as error:
                serve_frontend.create_server(8000, allow_fallback=False)
        self.assertIs(error.exception, busy)
        self.assertEqual(constructor.call_count, 1)

    def test_port_zero_is_passed_to_the_operating_system(self):
        with patch.object(serve_frontend, "LocalFrontendServer", return_value=sentinel.server) as constructor:
            server = serve_frontend.create_server(0)
        self.assertIs(server, sentinel.server)
        constructor.assert_called_once_with(("127.0.0.1", 0), serve_frontend.FrontendHandler)

    def test_actual_occupied_port_falls_back_without_replacing_existing_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(3)
            original_address = listener.getsockname()
            server = serve_frontend.create_server(original_address[1])
            try:
                self.assertNotEqual(server.server_port, original_address[1])
                self.assertEqual(server.server_address[0], "127.0.0.1")
                self.assertEqual(listener.getsockname(), original_address)
                with socket.create_connection(original_address, timeout=3):
                    accepted, _ = listener.accept()
                    accepted.close()
            finally:
                server.server_close()


if __name__ == "__main__":
    unittest.main()
