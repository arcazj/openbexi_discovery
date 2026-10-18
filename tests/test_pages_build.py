"""The Pages artifact must publish only public files and preserve private inputs."""

import tempfile
import unittest
from pathlib import Path

from scripts.build_pages import DOCUMENTS, HOSTED_MARKER, build_site


class PagesBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original_index = "<!doctype html><html><head><title>REI</title></head><body>Demo</body></html>"
        (self.root / "index.html").write_text(self.original_index, encoding="utf-8")
        for name in DOCUMENTS:
            (self.root / name).write_text("public documentation", encoding="utf-8")
        (self.root / "licenses").mkdir()
        (self.root / "licenses" / "dependency.txt").write_text("public license", encoding="utf-8")

    def test_artifact_allowlist_excludes_private_inputs_and_marks_only_hosted_copy(self):
        private_paths = (
            ".env", ".env.example", "backend/app.py", ".git/config",
            ".idea/workspace.xml", ".github/workflows/private.yml",
            "licenses/private.env", "licenses/nested/private.txt",
        )
        for name in private_paths:
            private = self.root / name
            private.parent.mkdir(parents=True, exist_ok=True)
            private.write_text("private fixture", encoding="utf-8")
        (self.root / "LICENSE").write_text("optional public license", encoding="utf-8")

        output = build_site(self.root)
        actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
        expected = set(DOCUMENTS) | {"index.html", ".nojekyll", "LICENSE", "licenses/dependency.txt"}
        self.assertEqual(actual, expected)
        self.assertIn(HOSTED_MARKER, (output / "index.html").read_text(encoding="utf-8"))
        self.assertEqual((self.root / "index.html").read_text(encoding="utf-8"), self.original_index)
        for name in private_paths:
            self.assertEqual((self.root / name).read_text(encoding="utf-8"), "private fixture")

    def test_rebuild_removes_stale_generated_files(self):
        license_file = self.root / "licenses" / "dependency.txt"
        build_site(self.root)
        license_file.unlink()
        (self.root / "README.md").write_text("updated documentation", encoding="utf-8")
        output = build_site(self.root)
        self.assertFalse((output / "licenses" / "dependency.txt").exists())
        self.assertEqual((output / "README.md").read_text(encoding="utf-8"), "updated documentation")

    def test_project_license_and_disclaimer_are_required_for_public_artifacts(self):
        for name in ("LICENSE", "DISCLAIMER.md"):
            with self.subTest(document=name):
                path = self.root / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaises(ValueError):
                    build_site(self.root)
                path.write_bytes(original)

    def test_unrecognized_output_is_preserved(self):
        output = self.root / "_site"
        output.mkdir()
        personal = output / "personal.txt"
        personal.write_text("preserve this file", encoding="utf-8")
        with self.assertRaises(ValueError):
            build_site(self.root)
        self.assertEqual(personal.read_text(encoding="utf-8"), "preserve this file")

    def test_unexpected_file_blocks_cleanup_before_any_changes(self):
        output = build_site(self.root)
        personal = output / "personal.txt"
        personal.write_text("preserve this file", encoding="utf-8")
        before = (output / "index.html").read_bytes()
        with self.assertRaises(ValueError):
            build_site(self.root)
        self.assertEqual((output / "index.html").read_bytes(), before)
        self.assertEqual(personal.read_text(encoding="utf-8"), "preserve this file")

    def test_linked_output_is_rejected_without_touching_its_target(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            untouched = outside / "personal.txt"
            untouched.write_text("outside checkout", encoding="utf-8")
            try:
                (self.root / "_site").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Directory symlinks are unavailable on this platform.")
            with self.assertRaises(ValueError):
                build_site(self.root)
            self.assertEqual(untouched.read_text(encoding="utf-8"), "outside checkout")

    def test_linked_public_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "external.txt"
            outside.write_text("private external fixture", encoding="utf-8")
            try:
                (self.root / "licenses" / "external.txt").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("File symlinks are unavailable on this platform.")
            with self.assertRaises(ValueError):
                build_site(self.root)
            self.assertFalse((self.root / "_site").exists())


if __name__ == "__main__":
    unittest.main()
