"""Installer/launcher boundaries without creating GUI windows or using a real key."""

import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from installer import desktop
from scripts import build_windows


class LauncherTests(unittest.TestCase):
    def test_profile_data_is_separate_from_installation_and_scopes_instances(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"LOCALAPPDATA": directory}):
            private = desktop.private_directory()
            self.assertEqual(private, Path(directory).resolve() / "REIResearchExplorer")
            self.assertNotIn("Programs", private.parts)
            self.assertNotEqual(desktop.ipc_names(private), desktop.ipc_names(private / "other-account"))

    def test_bad_saved_port_cannot_redirect_the_launcher_to_an_arbitrary_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for port in ("https://example.com", True, 0, 65536):
                with self.subTest(port=port):
                    (root / "desktop.json").write_text(json.dumps({"port": port, "instance_id": "x" * 36}), encoding="utf-8")
                    self.assertEqual(desktop.read_settings(root)["port"], desktop.DEFAULT_PORT)

    def test_settings_persist_port_and_instance_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desktop.write_settings(root, 18081, "a" * 36)
            self.assertEqual(desktop.read_settings(root), {"port": 18081, "instance_id": "a" * 36})
            self.assertFalse((root / "desktop.json.tmp").exists())

    def test_busy_preferred_port_does_not_replace_its_existing_listener(self):
        occupied = socket.socket()
        if os.name == "nt":
            occupied.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        self.addCleanup(occupied.close)
        listener = desktop.reserve_listener(occupied.getsockname()[1])
        self.addCleanup(listener.close)
        self.assertEqual(listener.getsockname()[0], "127.0.0.1")
        self.assertNotEqual(listener.getsockname()[1], occupied.getsockname()[1])
        self.assertGreater(occupied.fileno(), -1)


class BundlePrivacyTests(unittest.TestCase):
    def test_private_files_and_actual_key_are_rejected_from_the_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            bundle.mkdir()
            key = "sk-fixture-never-a-real-key"
            (root / ".env").write_text("OPENAI_API_KEY=" + key, encoding="utf-8")
            with patch.object(build_windows, "ROOT", root):
                for filename in (".env", ".env.backup", "private.iml", "user_profiles", "discovery_library", ".discovery"):
                    item = bundle / filename
                    item.write_text("private", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        build_windows.verify_bundle(bundle)
                    item.unlink()
                item = bundle / "innocent.txt"
                item.write_text(key, encoding="utf-8")
                with self.assertRaises(ValueError):
                    build_windows.verify_bundle(bundle)
                item.write_text("public documentation", encoding="utf-8")
                build_windows.verify_bundle(bundle)

    def test_build_output_cannot_leave_the_expected_workspace(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory).resolve()
            with patch.object(build_windows, "ROOT", root):
                self.assertEqual(build_windows.safe_output(root / "build/windows"), root / "build/windows")
                with self.assertRaises(ValueError):
                    build_windows.safe_output(Path(outside).resolve() / "build")


if __name__ == "__main__":
    unittest.main()
