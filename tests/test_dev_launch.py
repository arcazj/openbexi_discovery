"""IDE entry points must start the real API even from a non-root working directory."""
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch

import run_discovery

ROOT = Path(__file__).resolve().parent.parent


class DevelopmentLaunchTests(unittest.TestCase):
    def test_restart_reuses_closed_connections_but_never_an_active_listener(self):
        import socket
        listener = run_discovery.create_listener(0, allow_fallback=False)
        port = listener.getsockname()[1]
        try:
            with self.assertRaises(OSError):
                run_discovery.create_listener(port, allow_fallback=False)
            listener.settimeout(5)
            with socket.create_connection(("127.0.0.1", port), timeout=5) as peer:
                connection, _ = listener.accept()
                connection.close()  # Server initiates close, producing TIME_WAIT on Unix.
                self.assertEqual(peer.recv(1), b"")
        finally:
            listener.close()
        restarted = run_discovery.create_listener(port, allow_fallback=False)
        restarted.close()

    def test_missing_dependency_reports_environment_specific_repair(self):
        for project_environment in (True, False):
            with self.subTest(project_environment=project_environment):
                prefix = ROOT / (".venv" if project_environment else "other-python")
                missing = ModuleNotFoundError("No module named 'cryptography'", name="cryptography")
                with patch.object(sys, "prefix", str(prefix)), \
                        patch("builtins.__import__", side_effect=missing), \
                        self.assertRaises(SystemExit) as failure:
                    run_discovery.run()
                message = str(failure.exception)
                self.assertIn("Missing dependency: cryptography", message)
                self.assertIn("-m pip install -r", message)
                self.assertIn(str(ROOT / "requirements.lock.txt"), message)
                self.assertEqual("dependencies are incomplete" in message, project_environment)
                self.assertEqual("select the project interpreter" in message, not project_environment)

    def test_ide_entry_points_serve_full_discovery_without_ai(self):
        for script in ("run_discovery.py", "serve_frontend.py", "backend/app.py"):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                environment = dict(os.environ, OPENAI_API_KEY="", DISCOVERY_DATA_DIR=directory, DISCOVERY_LIBRARY_DIR="", PYTHONUNBUFFERED="1")
                process = subprocess.Popen([sys.executable, str(ROOT / script), "--port", "0"], cwd=ROOT / "backend",
                    env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                lines = queue.Queue()
                def collect():
                    for line in process.stdout:
                        lines.put(line)
                reader = threading.Thread(target=collect, daemon=True)
                reader.start()
                try:
                    output = []
                    while True:
                        line = lines.get(timeout=30)
                        output.append(line)
                        if "Uvicorn running" in line or "Application startup complete" in line:
                            break
                    address = re.search(r"http://127\.0\.0\.1:\d+", "".join(output)).group()
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open(address + "/api/discovery/bootstrap", timeout=10) as response:
                        result = json.load(response)
                    self.assertEqual(result['settings']['active_profile'], 'rei')
                    self.assertEqual(result['profiles'][0]['learning_level'], 'advanced')
                    with opener.open(address + "/assets/discovery.js", timeout=5) as response:
                        self.assertEqual(response.status, 200)
                finally:
                    process.terminate()
                    process.wait(timeout=15)
                    reader.join(timeout=3)
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
