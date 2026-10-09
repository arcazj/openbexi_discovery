"""Exercise the actual installer/bundled app in an isolated Windows test directory."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request

from scripts.build_windows import VERSION


def wait_for(callback, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if callback():
            return
        time.sleep(0.1)
    raise AssertionError("The installer/app did not complete the expected transition.")


def smoke(setup, test_tray=False, previous_setup=None):
    if os.name != "nt":
        raise RuntimeError("Installer checks require Windows.")
    import winreg
    key_name = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name):
            raise RuntimeError("An existing REI installation was detected; test in a clean Windows account.")
    except FileNotFoundError:
        pass
    appdata = Path(os.environ["APPDATA"])
    menu = appdata / "Microsoft/Windows/Start Menu/Programs/OpenBEXI Discovery"
    if menu.exists():
        raise RuntimeError("Existing REI shortcuts detected; test in a clean Windows account.")
    if (menu.parent / "REI Research Explorer").exists():
        raise RuntimeError("Existing legacy shortcuts detected; test in a clean Windows account.")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix="REI Installer QA ") as directory:
        root = Path(directory).resolve()
        install = root / "Installed app é"
        private = root / "Private settings"
        # These resolved test targets are checked before any install/uninstall operation.
        if not install.resolve().is_relative_to(root) or not private.resolve().is_relative_to(root):
            raise ValueError("Installer test target leaves its temporary workspace.")
        process = None
        executable = install / "REIResearchExplorer.exe"
        # The target executable must work even when Python is unavailable on PATH.
        environment = dict(os.environ)
        environment["PATH"] = os.environ["SystemRoot"] + r"\System32;" + os.environ["SystemRoot"]
        for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "REI_DATA_DIR", "REI_DESKTOP_INSTANCE", "DISCOVERY_DATA_DIR", "DISCOVERY_LIBRARY_DIR"):
            environment.pop(name, None)
        def run(arguments, timeout=60):
            return subprocess.run(arguments, env=environment, timeout=timeout, check=True,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        def install_package(package=setup):
            # NSIS requires its final /D argument without quotes, even for spaces.
            # Pass the exact native command line, with no shell involved.
            run(subprocess.list2cmdline([str(package), "/S"]) + " /D=" + str(install))
        def start():
            return subprocess.Popen([str(executable), "--no-browser" if test_tray else "--headless", "--data-dir", str(private)],
                                    env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        def ready():
            try:
                settings = json.loads((private / "desktop.json").read_text(encoding="utf-8"))
                with opener.open("http://127.0.0.1:" + str(settings["port"]) + "/api/health", timeout=1) as response:
                    data = json.load(response)
                return data.get("desktop", {}).get("instance_id") == settings["instance_id"]
            except (OSError, ValueError, KeyError):
                return False
        def get(path):
            settings = json.loads((private / "desktop.json").read_text(encoding="utf-8"))
            return opener.open("http://127.0.0.1:" + str(settings["port"]) + path, timeout=5)
        def post(path, value, raw=False):
            settings = json.loads((private / "desktop.json").read_text(encoding="utf-8"))
            url = "http://127.0.0.1:" + str(settings["port"])
            request = urllib.request.Request(url + "/api/discovery" + path,
                data=json.dumps(value).encode(), headers={"Content-Type": "application/json", "Origin": url}, method="POST")
            with opener.open(request, timeout=15) as response:
                return response.read() if raw else json.load(response)
        def verify_current_version():
            manifest = json.loads((install / "BUILD-INFO.json").read_text(encoding="utf-8"))
            assert manifest["version"] == VERSION
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
                assert winreg.QueryValueEx(key, "DisplayVersion")[0] == VERSION
            with get("/api/health") as response:
                assert json.load(response)["version"] == VERSION
            with get("/") as response:
                html = response.read().decode("utf-8")
                assert 'id="app-version"' in html and ">V" + VERSION + "</span>" in html
                assert 'id="context-tip" class="side-card tip"' in html
                assert "#evidence-area{min-width:0;padding:16px" in html
                assert ".record[data-source]" in html
            with get("/api/discovery/bootstrap") as response:
                data = json.load(response)
                assert next(p for p in data["profiles"] if p["id"] == "rei")["learning_level"] == "advanced"
            with get("/api/discovery/taxonomy") as response:
                assert len(json.load(response)["nodes"]) > 1000
            for path in ("/assets/discovery.js", "/assets/discovery.css", "/documentation/USER_GUIDE.md"):
                with get(path) as response:
                    assert response.status == 200
            with get("/api/discovery/templates/general") as response:
                profile = json.load(response)
            profile["name"] = "Installer fixture"
            saved = post("/profiles/save", {"profile": profile, "create": True})
            pid = saved["id"]
            fixture = root / "synthetic.sqlite"
            db = sqlite3.connect(str(fixture))
            try:
                db.execute("CREATE TABLE IF NOT EXISTS evidence (gene TEXT)")
                db.execute("DELETE FROM evidence")
                db.execute("INSERT INTO evidence VALUES ('BRCA1')")
                db.commit()
            finally:
                db.close()
            connection = post("/connections", {"name": "Synthetic data", "path": str(fixture), "sensitive": False})
            query = {"connection_id": connection["id"], "table": "evidence", "fields": ["gene"], "profile_id": pid}
            assert post("/connections/query", query)["rows"] == [{"gene": "BRCA1"}]
            post("/connections/query", dict(query, snapshot=True, consent_local=True))
            post("/settings", {"local_only": True})
            note = post("/library", {"profile_id": pid, "kind": "note", "title": "Offline fixture", "content": "No external connection needed."})
            archive = post("/archives/export", {"profile_id": pid}, raw=True)
            opened = post("/archives/open", {"file_base64": base64.b64encode(archive).decode()})
            assert any(a["id"] == note["id"] for a in opened["activities"])
            assert post("/archives/import", {"id": opened["id"]})["skipped"] >= 2
            assert post("/budget", {"period": "cumulative", "token_limit": 0, "cost_limit": None})["blocked"]
            assert (private / "user_profiles" / (pid + ".json")).is_file()
            assert (private / ".discovery" / "usage.sqlite").is_file()
            assert (menu / "OpenBEXI Discovery.lnk").is_file()
            assert not (menu.parent / "REI Research Explorer").exists()
        try:
            install_package(previous_setup or setup)
            wait_for(executable.is_file)
            assert (install / "Uninstall.exe").is_file()
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
                assert Path(winreg.QueryValueEx(key, "InstallLocation")[0]).resolve() == install
            initial_menu = menu.parent / "REI Research Explorer" if previous_setup else menu
            assert (initial_menu / ("REI Research Explorer.lnk" if previous_setup else "OpenBEXI Discovery.lnk")).is_file()
            process = start()
            wait_for(ready)
            if test_tray:
                time.sleep(1)
                assert process.poll() is None, "Native tray initialization failed."
            if previous_setup is None:
                verify_current_version()
            initial = json.loads((private / "desktop.json").read_text(encoding="utf-8"))
            with get("/") as response:
                assert b"Make the next step useful" in response.read()
            with get("/api/health") as response:
                assert json.load(response)["ai"]["configured"] is False
            for name in ("README.md", "HELP.md", "WINDOWS_INSTALLATION.md", "COMMERCIAL_LICENSING.md", "THIRD_PARTY_NOTICES.md"):
                with get("/api/docs/" + name) as response:
                    assert response.status == 200
            for path in ("/.env", "/backend/app.py", "/desktop.json"):
                try:
                    get(path)
                    raise AssertionError("Private/backend route was exposed.")
                except urllib.error.HTTPError as error:
                    assert error.code == 404
            run([str(executable), "--headless", "--data-dir", str(private)], timeout=30)
            assert process.poll() is None
            assert json.loads((private / "desktop.json").read_text(encoding="utf-8"))["instance_id"] == initial["instance_id"]
            fake_key = "sk-installer-fixture-key-never-a-live-key"
            url = "http://127.0.0.1:" + str(initial["port"])
            request = urllib.request.Request(url + "/api/ai/configure", data=json.dumps({"api_key": fake_key}).encode(),
                                             headers={"Content-Type": "application/json", "Origin": url}, method="POST")
            with opener.open(request, timeout=5) as response:
                text = response.read().decode()
                assert fake_key not in text
                assert json.loads(text)["configured"] is True
            assert fake_key in (private / ".env").read_text(encoding="utf-8")
            assert not list(install.rglob(".env"))
            user_file = install / "my research note.txt"
            user_file.write_text("Keep this user file.", encoding="utf-8")
            run([str(executable), "--quit", "--data-dir", str(private)], timeout=30)
            assert process.wait(timeout=20) == 0
            # Reinstall over the existing package; private configuration must survive.
            install_package()
            assert user_file.read_text(encoding="utf-8") == "Keep this user file."
            process = start()
            wait_for(ready)
            verify_current_version()
            with get("/api/health") as response:
                text = response.read().decode()
                assert json.loads(text)["ai"]["configured"] is True
                assert fake_key not in text
            run([str(executable), "--quit", "--data-dir", str(private)], timeout=30)
            assert process.wait(timeout=20) == 0
            run([str(install / "Uninstall.exe"), "/S"])
            wait_for(lambda: not executable.exists())
            assert user_file.read_text(encoding="utf-8") == "Keep this user file."
            assert fake_key in (private / ".env").read_text(encoding="utf-8")
            wait_for(lambda: not menu.exists())
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name):
                    raise AssertionError("Uninstall registration was left behind.")
            except FileNotFoundError:
                pass
            print("Windows installer " + VERSION + " checks passed: install, current UI/version, shortcuts, bundled runtime without Python on PATH, singleton, private key setup, restart, upgrade, and uninstall preserving user data.")
        finally:
            if process and process.poll() is None:
                if executable.is_file():
                    run([str(executable), "--quit", "--data-dir", str(private)], timeout=30)
                process.wait(timeout=20)
            if (install / "Uninstall.exe").is_file():
                run([str(install / "Uninstall.exe"), "/S"])
                wait_for(lambda: not executable.exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", type=Path, default=Path(f"dist/OpenBEXIDiscovery-{VERSION}-Windows-x64-Setup.exe"))
    parser.add_argument("--tray", action="store_true", help="Also verify the native tray in an interactive Windows desktop session.")
    parser.add_argument("--previous-installer", type=Path, help="Start with an earlier installer and verify upgrading it to the current package.")
    options = parser.parse_args()
    smoke(options.installer.resolve(), options.tray, options.previous_installer.resolve() if options.previous_installer else None)
