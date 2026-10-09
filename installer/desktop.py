"""Windowless Windows launcher; its runtime is bundled in the installer."""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser

APP_NAME = "OpenBEXI Discovery"
DEFAULT_PORT = 18080


def private_directory(override=None):
    if override:
        return Path(override).resolve()
    base = os.getenv("LOCALAPPDATA")
    if not base:
        raise RuntimeError("Windows user profile is unavailable.")
    return Path(base).resolve() / "REIResearchExplorer"


def ipc_names(directory):
    digest = hashlib.sha256(os.path.normcase(str(directory.resolve())).encode()).hexdigest()[:24]
    return ("Local\\REIResearchExplorer-" + digest, "Local\\REIResearchExplorerQuit-" + digest)


def read_settings(directory):
    try:
        data = json.loads((directory / "desktop.json").read_text(encoding="utf-8"))
        if (type(data.get("port")) is int and 1024 <= data["port"] <= 65535
                and isinstance(data.get("instance_id"), str) and len(data["instance_id"]) == 36):
            return data
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return {"port": DEFAULT_PORT, "instance_id": ""}


def reserve_listener(preferred):
    ports = list(dict.fromkeys([preferred, *range(DEFAULT_PORT, DEFAULT_PORT + 11), 0]))
    for port in ports:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if os.name == "nt":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", port))
            listener.listen(128)
            listener.setblocking(False)
            return listener
        except OSError as error:
            listener.close()
            if error.errno not in {13, 48, 98, 10013, 10048} and getattr(error, "winerror", None) not in {10013, 10048}:
                raise
    raise RuntimeError("No local listening port is available.")


def write_settings(directory, port, instance_id):
    target = directory / "desktop.json"
    temporary = directory / "desktop.json.tmp"
    temporary.write_text(json.dumps({"port": port, "instance_id": instance_id}), encoding="utf-8")
    temporary.replace(target)


def existing_url(directory, timeout=20):
    end = time.monotonic() + timeout
    # Local traffic must not go through an enterprise HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < end:
        settings = read_settings(directory)
        url = "http://127.0.0.1:" + str(settings["port"])
        try:
            with opener.open(url + "/api/health", timeout=1) as response:
                health = json.load(response)
            if health.get("desktop", {}).get("instance_id") == settings["instance_id"] and settings["instance_id"]:
                return url
        except (OSError, ValueError, AttributeError):
            pass
        time.sleep(0.1)
    raise RuntimeError("The existing app has not finished starting.")


def windows_api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateEventW.restype = wintypes.HANDLE
    kernel.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenEventW.restype = wintypes.HANDLE
    kernel.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenMutexW.restype = wintypes.HANDLE
    for name in ("CloseHandle", "ReleaseMutex", "SetEvent"):
        getattr(kernel, name).argtypes = [wintypes.HANDLE]
        getattr(kernel, name).restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    return kernel


def quit_existing(kernel, directory):
    mutex_name, event_name = ipc_names(directory)
    event = kernel.OpenEventW(2, False, event_name)
    if not event:
        return 0
    try:
        if not kernel.SetEvent(event):
            return 1
        mutex = kernel.OpenMutexW(0x100000 | 1, False, mutex_name)
        if mutex:
            try:
                result = kernel.WaitForSingleObject(mutex, 15000)
                if result in (0, 0x80):
                    kernel.ReleaseMutex(mutex)
                    return 0
                return 1
            finally:
                kernel.CloseHandle(mutex)
        return 0
    finally:
        kernel.CloseHandle(event)


def tray(url, kernel, quit_event, worker):
    """Small native tray menu: Open research workspace / Quit."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    class WindowClass(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("procedure", callback_type), ("class_extra", ctypes.c_int),
                    ("window_extra", ctypes.c_int), ("instance", wintypes.HINSTANCE), ("icon", wintypes.HICON),
                    ("cursor", wintypes.HANDLE), ("background", wintypes.HBRUSH),
                    ("menu_name", wintypes.LPCWSTR), ("class_name", wintypes.LPCWSTR)]

    class NotifyIcon(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("window", wintypes.HWND), ("id", wintypes.UINT),
                    ("flags", wintypes.UINT), ("callback_message", wintypes.UINT), ("icon", wintypes.HICON),
                    ("tip", wintypes.WCHAR * 128), ("state", wintypes.DWORD), ("state_mask", wintypes.DWORD),
                    ("info", wintypes.WCHAR * 256), ("version", wintypes.UINT), ("info_title", wintypes.WCHAR * 64),
                    ("info_flags", wintypes.DWORD), ("guid", ctypes.c_byte * 16), ("balloon_icon", wintypes.HICON)]

    user.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.DefWindowProcW.restype = ctypes.c_ssize_t
    user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
    user.RegisterClassW.restype = wintypes.ATOM
    user.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                     wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    user.CreateWindowExW.restype = wintypes.HWND
    user.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    user.LoadIconW.restype = wintypes.HICON
    user.CreatePopupMenu.restype = wintypes.HMENU
    user.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    user.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.LPVOID]
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.DestroyMenu.argtypes = [wintypes.HMENU]
    user.DestroyWindow.argtypes = [wintypes.HWND]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user.DispatchMessageW.restype = ctypes.c_ssize_t
    shell.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NotifyIcon)]
    shell.Shell_NotifyIconW.restype = wintypes.BOOL

    def procedure(window, message, first, second):
        if message == 0x8001:
            if second == 0x203:  # double click
                webbrowser.open(url)
            elif second in (0x202, 0x205):
                point = wintypes.POINT()
                user.GetCursorPos(ctypes.byref(point))
                menu = user.CreatePopupMenu()
                user.AppendMenuW(menu, 0, 1, "Open research workspace")
                user.AppendMenuW(menu, 0, 2, "Quit REI Research Explorer")
                user.SetForegroundWindow(window)
                selected = user.TrackPopupMenu(menu, 0x100 | 2, point.x, point.y, 0, window, None)
                user.DestroyMenu(menu)
                if selected == 1:
                    webbrowser.open(url)
                elif selected == 2:
                    kernel.SetEvent(quit_event)
        elif message == 0x10:
            user.DestroyWindow(window)
            return 0
        elif message == 2:
            user.PostQuitMessage(0)
            return 0
        return user.DefWindowProcW(window, message, first, second)

    callback = callback_type(procedure)
    name = "REIResearchExplorerTray-" + str(uuid.uuid4())
    window_class = WindowClass(0, callback, 0, 0, None, None, None, None, None, name)
    if not user.RegisterClassW(ctypes.byref(window_class)):
        raise RuntimeError("Could not create the tray menu.")
    window = user.CreateWindowExW(0, name, APP_NAME, 0, 0, 0, 0, 0, None, None, None, None)
    if not window:
        raise RuntimeError("Could not create the tray window.")
    icon_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "installer" / "rei.ico"
    user.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user.LoadImageW.restype = wintypes.HANDLE
    icon = user.LoadImageW(None, str(icon_path), 1, 32, 32, 0x10)
    if not icon:
        icon = user.LoadIconW(None, ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR))
    notification = NotifyIcon()
    notification.size = ctypes.sizeof(NotifyIcon)
    notification.window = window
    notification.id = 1
    notification.flags = 1 | 2 | 4
    notification.callback_message = 0x8001
    notification.icon = icon
    notification.tip = APP_NAME + " — Open / Quit"
    if not shell.Shell_NotifyIconW(0, ctypes.byref(notification)):
        user.DestroyWindow(window)
        raise RuntimeError("Could not add the tray menu.")

    def monitor():
        while worker.is_alive():
            if kernel.WaitForSingleObject(quit_event, 250) == 0:
                break
        user.PostMessageW(window, 0x10, 0, 0)

    threading.Thread(target=monitor, daemon=True).start()
    try:
        message = wintypes.MSG()
        while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user.TranslateMessage(ctypes.byref(message))
            user.DispatchMessageW(ctypes.byref(message))
    finally:
        shell.Shell_NotifyIconW(2, ctypes.byref(notification))


def main(argv=None):
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--quit", action="store_true", help="Gracefully close this user's running app.")
    parser.add_argument("--headless", action="store_true", help="Run without opening the browser/tray; for checks.")
    parser.add_argument("--no-browser", action="store_true", help="Create the tray without opening a browser; for checks.")
    parser.add_argument("--data-dir", help="Use a separate private settings folder (advanced/checks).")
    options = parser.parse_args(argv)
    if os.name != "nt":
        raise RuntimeError("The desktop launcher requires Windows 10 or 11, 64-bit.")
    directory = private_directory(options.data_dir)
    kernel = windows_api()
    if options.quit:
        return quit_existing(kernel, directory)
    directory.mkdir(parents=True, exist_ok=True)
    mutex_name, event_name = ipc_names(directory)
    ctypes.set_last_error(0)
    mutex = kernel.CreateMutexW(None, True, mutex_name)
    if not mutex:
        raise RuntimeError("Could not create the app instance lock.")
    if ctypes.get_last_error() == 183:
        try:
            url = existing_url(directory)
            if not options.headless and not options.no_browser:
                webbrowser.open(url)
            return 0
        finally:
            kernel.CloseHandle(mutex)
    quit_event = kernel.CreateEventW(None, True, False, event_name)
    listener = None
    server = None
    worker = None
    try:
        if not quit_event:
            raise RuntimeError("Could not create the app exit control.")
        os.environ["REI_DATA_DIR"] = str(directory)
        os.environ["DISCOVERY_DATA_DIR"] = str(directory)
        os.environ["REI_DESKTOP_INSTANCE"] = str(uuid.uuid4())
        import uvicorn
        from backend.app import app
        listener = reserve_listener(read_settings(directory)["port"])
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, loop="asyncio", http="h11",
                                            ws="none", lifespan="on", log_config=None, access_log=False,
                                            timeout_graceful_shutdown=5))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        end = time.monotonic() + 25
        while not server.started and worker.is_alive() and time.monotonic() < end:
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("The local app could not start. Restart the app and try again.")
        write_settings(directory, port, os.environ["REI_DESKTOP_INSTANCE"])
        url = "http://127.0.0.1:" + str(port)
        if options.headless:
            while worker.is_alive() and kernel.WaitForSingleObject(quit_event, 250) != 0:
                pass
        else:
            if not options.no_browser:
                webbrowser.open(url)
            tray(url, kernel, quit_event, worker)
        return 0
    finally:
        if server:
            server.should_exit = True
        if worker:
            worker.join(timeout=10)
        if listener:
            listener.close()
        if quit_event:
            kernel.CloseHandle(quit_event)
        kernel.ReleaseMutex(mutex)
        kernel.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # No raw exceptions, secrets, or research text in a dialog/log.
        if os.name == "nt" and "--headless" not in sys.argv and "--quit" not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None, "The app could not start. Close any previous instance and retry. See Windows installation help in the README.", APP_NAME, 0x10)
        raise SystemExit(1)
