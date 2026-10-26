"""VoiceNPS: run this file and the app opens in its own window.

    python demo_app.py

Nothing is hosted online. The engine runs on this computer only (127.0.0.1) and the window is a normal
desktop app window (Chrome or Edge in "app mode": no tabs, no address bar). Close the window, press
Ctrl+C, or say "end" and then close the window, and everything stops.

Options:  --port 8765   --browser /path/to/chrome   --no-window (just print the address)
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app import server  # noqa: E402


def find_browser(explicit=None):
    """Chrome / Edge / Chromium: the browsers that have the speech recognition the app needs."""
    if explicit:
        return explicit
    env = os.environ.get("VOICENPS_BROWSER")
    if env:
        return env
    cands = []
    if sys.platform == "darwin":
        for n in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"):
            cands.append(f"/Applications/{n}.app/Contents/MacOS/{n}")
            cands.append(str(pathlib.Path.home() / f"Applications/{n}.app/Contents/MacOS/{n}"))
    elif sys.platform.startswith("win"):
        for base in filter(None, (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA"))):
            cands += [rf"{base}\Google\Chrome\Application\chrome.exe", rf"{base}\Microsoft\Edge\Application\msedge.exe"]
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"):
        p = shutil.which(n)
        if p:
            cands.append(p)
    return next((c for c in cands if c and pathlib.Path(c).exists()), None)


def open_window(browser, url):
    profile = pathlib.Path(os.environ.get("VOICENPS_PROFILE") or (pathlib.Path.home() / ".voicenps" / "window"))
    try:
        profile.mkdir(parents=True, exist_ok=True)
    except OSError:
        profile = pathlib.Path(tempfile.mkdtemp(prefix="voicenps-"))
    args = [browser, f"--app={url}", f"--user-data-dir={profile}", "--window-size=1180,880",
            "--no-first-run", "--no-default-browser-check", "--disable-features=Translate",
            "--use-fake-ui-for-media-stream"]          # microphone allowed for this app window without a prompt
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser(description="VoiceNPS voice payment assistant")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--browser", help="path to Chrome or Edge")
    ap.add_argument("--no-window", action="store_true", help="only start the engine and print the address")
    a = ap.parse_args()

    httpd = server.make_server(a.port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print("VoiceNPS is running on this computer. Close the window or press Ctrl+C to stop.")

    try:
        import gtts  # noqa: F401
    except ImportError:
        print("Note: Nepali voice needs 'pip install gTTS' (and internet). Until then the browser's own voice is used.")

    proc = None
    if a.no_window:
        print("Open", url, "in Chrome or Edge.")
    else:
        browser = find_browser(a.browser)
        if browser:
            proc = open_window(browser, url)
        else:
            print("Chrome or Edge was not found, opening your default browser instead (use Chrome for speech).")
            webbrowser.open(url)
            print("Address:", url)

    try:
        started, seen_exit = time.time(), None
        while True:
            time.sleep(1)
            now, last = time.time(), server.PING["last"]
            if last:                                           # window alive = heartbeat every 3 s
                if now - last > 12:
                    break
            elif now - started > 45 and not a.no_window:       # window never connected
                break
            if proc is not None and proc.poll() is not None:   # window process is gone
                seen_exit = seen_exit or now
                if now - seen_exit > 6 and (not last or now - last > 6):
                    break
    except KeyboardInterrupt:
        pass
    httpd.shutdown()
    if proc is not None and proc.poll() is None:
        proc.terminate()
    print("VoiceNPS stopped.")


if __name__ == "__main__":
    main()
