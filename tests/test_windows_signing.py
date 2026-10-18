"""Signing configuration and failure handling, without keys or signing requests."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.sign_windows import WindowsSigner, verify_signature
from scripts import build_windows


class WindowsSigningTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.tool = self.root / "signtool.exe"
        self.tool.write_bytes(b"test tool")
        os.environ["OPENBEXI_SIGNTOOL"] = str(self.tool)
        self.binary = self.root / "Setup with spaces.exe"
        self.binary.write_bytes(b"test unsigned executable")

    def test_signed_release_requires_an_identity_but_local_build_can_be_unsigned(self):
        self.assertIsNone(WindowsSigner.from_environment())
        with self.assertRaisesRegex(RuntimeError, "signing identity is required"):
            WindowsSigner.from_environment(required=True)

    def test_signs_selected_certificate_with_sha256_timestamp_then_verifies_trust(self):
        os.environ["OPENBEXI_SIGN_CERT_SHA1"] = "ab" * 20
        signer = WindowsSigner.from_environment(required=True)
        with patch("scripts.sign_windows.subprocess.run", return_value=Mock(returncode=0)) as run:
            signer.sign(self.binary)
        command = run.call_args_list[0].args[0]
        self.assertEqual(command[:4], [str(self.tool.resolve()), "sign", "/fd", "SHA256"])
        self.assertEqual(command[command.index("/sha1") + 1], "ab" * 20)
        self.assertEqual(command[command.index("/td") + 1], "SHA256")
        self.assertEqual(command[-1], str(self.binary.resolve()))
        self.assertEqual(run.call_args_list[1].args[0],
                         [str(self.tool.resolve()), "verify", "/pa", "/all", "/tw", str(self.binary.resolve())])
        self.assertNotIn("/p", command, "Private-key passwords must not be passed on the command line")
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_cloud_signing_uses_existing_identity_metadata_and_dlib(self):
        dlib, metadata = self.root / "cloud signing.dll", self.root / "metadata.json"
        dlib.write_bytes(b"fixture")
        metadata.write_text('{}', encoding="utf-8")
        os.environ.update(OPENBEXI_SIGN_DLIB=str(dlib), OPENBEXI_SIGN_METADATA=str(metadata))
        signer = WindowsSigner.from_environment(required=True)
        self.assertEqual(signer.identity_arguments, ["/dlib", str(dlib.resolve()), "/dmdf", str(metadata.resolve())])

    def test_partial_or_ambiguous_identity_never_falls_back_to_unsigned(self):
        for values in ({"OPENBEXI_SIGN_CERT_SHA1": "invalid"},
                       {"OPENBEXI_SIGN_DLIB": str(self.tool)},
                       {"OPENBEXI_SIGN_METADATA": str(self.tool)},
                       {"OPENBEXI_SIGN_CERT_SHA1": "ab" * 20, "OPENBEXI_SIGN_DLIB": str(self.tool)}):
            with self.subTest(values=list(values)), patch.dict(os.environ, values):
                with self.assertRaises(ValueError):
                    WindowsSigner.from_environment()

    def test_failed_signing_or_timestamp_warning_stops_before_verification(self):
        signer = WindowsSigner(str(self.tool), ["/sha1", "ab" * 20], "http://timestamp.acs.microsoft.com")
        for code in (1, 2):
            with self.subTest(returncode=code), patch("scripts.sign_windows.subprocess.run", return_value=Mock(returncode=code)) as run:
                with self.assertRaises(RuntimeError):
                    signer.sign(self.binary)
                self.assertEqual(run.call_count, 1)

    def test_invalid_signature_or_missing_timestamp_is_rejected(self):
        with patch("scripts.sign_windows.subprocess.run", return_value=Mock(returncode=2)):
            with self.assertRaises(RuntimeError):
                verify_signature(self.binary, str(self.tool))

    def test_provider_error_does_not_print_secrets_and_missing_tools_fail(self):
        with patch("scripts.sign_windows.subprocess.run", side_effect=subprocess.TimeoutExpired("fixture-secret", 180)):
            with self.assertRaises(RuntimeError) as error:
                verify_signature(self.binary, str(self.tool))
            self.assertNotIn("fixture-secret", str(error.exception))
        os.environ.update(OPENBEXI_SIGN_CERT_SHA1="ab" * 20, OPENBEXI_SIGNTOOL=str(self.root / "missing.exe"))
        with self.assertRaisesRegex(RuntimeError, "OPENBEXI_SIGNTOOL"):
            WindowsSigner.from_environment()

    def test_packaging_embeds_signed_app_and_checksums_the_final_signed_installer(self):
        root = self.root.resolve()
        for name in (*build_windows.DOCUMENTS, "index.html", "LICENSE.txt", "COPYING.txt", "COPYING", "vcruntime140.dll"):
            (root / name).write_text("public fixture", encoding="utf-8")
        for name in ("assets", "templates", "themes", "prompts/runtime", "schemas", "documentation", "licenses"):
            (root / name).mkdir(parents=True, exist_ok=True)
        bundle = root / "build/windows/dist/REIResearchExplorer"
        app = bundle / "REIResearchExplorer.exe"
        setup = root / "dist" / f"OpenBEXIDiscovery-{build_windows.VERSION}-Windows-x64-Setup.exe"
        events = []

        def sign(path):
            events.append(("sign", path.name))
            path.write_bytes(path.read_bytes() + b" signed")

        def compile_package(arguments, **kwargs):
            if "PyInstaller" in arguments:
                for name in ("LICENSE", "DISCLAIMER.md", "COMMERCIAL_LICENSING.md"):
                    self.assertIn(str(root / name) + ";.", arguments)
                bundle.mkdir(parents=True)
                app.write_bytes(b"app")
            else:
                events.append(("package", setup.name))
                self.assertEqual(app.read_bytes(), b"app signed")
                self.assertTrue(json.loads((bundle / "BUILD-INFO.json").read_text())["signed"])
                self.assertTrue(any(arg.startswith("/DSIGN_SCRIPT=") for arg in arguments))
                self.assertTrue(any(arg.startswith("/DSIGN_PYTHON=") for arg in arguments))
                self.assertIn("/DPROJECT_LICENSE=" + str(root / "LICENSE"), arguments)
                setup.write_bytes(b"setup")

        signer = Mock()
        signer.sign.side_effect = sign
        distribution = Mock(files=[Path("COPYING.txt")])
        distribution.locate_file.return_value = root / "COPYING.txt"
        runtime = SimpleNamespace(version_info=(3, 12), version="3.12.10", base_prefix=str(root), executable="python.exe")
        with patch.object(build_windows, "ROOT", root), \
                patch.object(build_windows, "os", SimpleNamespace(name="nt", pathsep=";")), \
                patch.object(build_windows, "sys", runtime), \
                patch.object(build_windows, "nsis_compiler", return_value=self.tool), \
                patch.object(build_windows.WindowsSigner, "from_environment", return_value=signer) as configure, \
                patch.object(build_windows.importlib.metadata, "distribution", return_value=distribution), \
                patch.object(build_windows.importlib.metadata, "version", return_value="fixture"), \
                patch.object(build_windows.subprocess, "check_output", return_value="fixture"), \
                patch.object(build_windows.subprocess, "run", side_effect=compile_package):
            self.assertEqual(build_windows.build(require_signing=True), setup)
        configure.assert_called_once_with(required=True)
        self.assertEqual(events, [("sign", app.name), ("package", setup.name), ("sign", setup.name)])
        self.assertEqual(setup.read_bytes(), b"setup signed")
        digest, filename = (setup.parent / "SHA256SUMS-Windows.txt").read_text().split()
        self.assertEqual(filename, setup.name)
        self.assertEqual(digest, hashlib.sha256(setup.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
