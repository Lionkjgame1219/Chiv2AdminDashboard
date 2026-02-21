from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Callable, Optional

# Auto-update for the PyInstaller onefile Windows build.
# Normal mode: on startup, check GitHub releases for the latest .exe asset and update if needed.
# Updater mode: invoked as a *separate* executable copy so it can replace the original exe.

GITHUB_REPO = "Lionkjgame1219/Chiv2AdminDashboard"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=100"
APPDATA_DIRNAME = "Chiv2AdminDashboard"


def _safe_status(cb: Optional[Callable[[str], None]], msg: str) -> None:
    if not cb:
        return
    try:
        cb(str(msg))
    except Exception:
        pass


def _maybe_make_qt_progress_ui(title: str = "Updating..."):
    """Best-effort tiny UI for the updater process (no console in onefile builds).

    Returns a tuple: (status_callback, progress_callback, close_callback)
    where callbacks can be None.
    """

    try:
        # Import locally so source runs / unit tests don't require Qt.
        from PyQt5.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget
        from PyQt5.QtCore import Qt

        app = QApplication.instance()
        if app is None:
            # Don't forward our argv (contains --apply-update etc.) into Qt.
            app = QApplication([])

        w = QWidget()
        w.setWindowTitle(title)
        w.setMinimumWidth(420)
        w.setWindowFlags(w.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(w)
        label = QLabel("Starting update...")
        label.setWordWrap(True)
        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate
        layout.addWidget(label)
        layout.addWidget(bar)

        w.show()
        try:
            w.raise_()
            w.activateWindow()
        except Exception:
            pass
        app.processEvents()

        def _set_status(msg: str) -> None:
            label.setText(str(msg))
            app.processEvents()

        def _set_progress(percent: Optional[int]) -> None:
            if percent is None:
                bar.setRange(0, 0)
            else:
                bar.setRange(0, 100)
                bar.setValue(int(percent))
            app.processEvents()

        def _close() -> None:
            try:
                w.close()
                app.processEvents()
            except Exception:
                pass

        return _set_status, _set_progress, _close
    except Exception:
        return None, None, None


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _state_path() -> str:
    base = os.getenv("LOCALAPPDATA") or tempfile.gettempdir()
    d = os.path.join(base, APPDATA_DIRNAME)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "autoupdate_state.json")


def _load_state() -> dict:
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(state or {}, f, indent=2)
    except Exception:
        pass


_semver_re = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?")


def parse_semver(text: str):
    if not text:
        return None
    m = _semver_re.search(str(text))
    if not m:
        return None
    a, b, c, d = m.groups()
    return (int(a), int(b), int(c), int(d or 0))


def _http_json(url: str, timeout_s: float = 5.0):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Chiv2AdminDashboard-Autoupdater",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_latest_exe_asset(releases, preferred_filename: str = ""):
    # Prefer stable releases; fall back to pre-releases if no stable exe exists.
    preferred_lc = (preferred_filename or "").strip().lower()
    preferred_stem = os.path.splitext(preferred_lc)[0] if preferred_lc else ""

    def candidates(allow_prerelease: bool):
        for rel in releases or []:
            if rel.get("draft"):
                continue
            if (not allow_prerelease) and rel.get("prerelease"):
                continue
            tag_ver = parse_semver(rel.get("tag_name") or "")
            for a in rel.get("assets") or []:
                name = a.get("name") or ""
                if not name.lower().endswith(".exe"):
                    continue
                yield rel, a, tag_ver

    best = None
    for allow_pre in (False, True):
        for rel, asset, tag_ver in candidates(allow_pre):
            name = asset.get("name") or ""
            v = parse_semver(name) or tag_ver

            name_lc = name.lower()
            # Prefer the exact current executable name (or containing it) if possible.
            if preferred_lc and name_lc == preferred_lc:
                prefer = 3
            elif preferred_lc and preferred_lc in name_lc:
                prefer = 2
            elif preferred_stem and (name_lc.startswith(preferred_stem) or preferred_stem in name_lc):
                prefer = 2
            elif "admindashboard" in name_lc or "dashboard" in name_lc:
                prefer = 1
            else:
                prefer = 0

            key = (prefer, v is not None, v or (0, 0, 0, 0), asset.get("updated_at") or "")
            if best is None or key > best[0]:
                best = (key, rel, asset, v)
        if best is not None:
            break

    if best is None:
        return None
    _, rel, asset, v = best
    return {
        "asset_name": asset.get("name"),
        "download_url": asset.get("browser_download_url"),
        "version_tuple": v,
        "release_tag": rel.get("tag_name"),
    }


def _get_file_version_tuple(path: str):
    try:
        import win32api  # type: ignore

        info = win32api.GetFileVersionInfo(path, "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return None


def _download(
    url: str,
    out_path: str,
    timeout_s: float = 300.0,
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[Optional[int]], None]] = None,
) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Chiv2AdminDashboard-Autoupdater"})
    with urllib.request.urlopen(req, timeout=timeout_s) as r, open(out_path, "wb") as f:
        total = None
        try:
            cl = r.headers.get("Content-Length")
            if cl:
                total = int(cl)
        except Exception:
            total = None

        downloaded = 0
        last_t = 0.0
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)

            downloaded += len(chunk)
            now = time.time()
            if (now - last_t) >= 0.5:
                last_t = now
                pct = None
                if total and total > 0:
                    pct = int(downloaded * 100 / total)
                if progress_callback:
                    try:
                        progress_callback(pct)
                    except Exception:
                        pass
                if status_callback:
                    mb = 1024 * 1024
                    if total and total > 0:
                        _safe_status(
                            status_callback,
                            f"Downloading update... {downloaded / mb:.1f} / {total / mb:.1f} MB ({pct}%)",
                        )
                    else:
                        _safe_status(status_callback, f"Downloading update... {downloaded / mb:.1f} MB")

        if progress_callback and total:
            try:
                progress_callback(100)
            except Exception:
                pass


def _replace_with_retry(src: str, dst: str, timeout_s: float = 60.0) -> None:
    deadline = time.time() + float(timeout_s)
    last_err = None
    while time.time() < deadline:
        try:
            os.replace(src, dst)
            return
        except Exception as e:
            last_err = e
            time.sleep(0.5)
    raise last_err  # type: ignore


def _parse_apply_args(argv):
    url = target = remote_ver = None
    passthrough = []
    if "--" in argv:
        i = argv.index("--")
        passthrough = argv[i + 1 :]
        argv = argv[:i]
    it = iter(argv)
    for tok in it:
        if tok == "--url":
            url = next(it, None)
        elif tok == "--target":
            target = next(it, None)
        elif tok == "--remote-version":
            remote_ver = next(it, None)
    return url, target, remote_ver, passthrough


def _run_apply_update(
    argv,
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[Optional[int]], None]] = None,
) -> None:
    url, target, remote_ver, passthrough = _parse_apply_args(argv)
    if not url or not target:
        return

    backup = target + ".old"
    try:
        _safe_status(status_callback, "Preparing update...")
        tmp_dir = tempfile.mkdtemp(prefix="chiv2adm_update_")
        dl_path = os.path.join(tmp_dir, "new.exe")
        _safe_status(status_callback, "Downloading update...")
        _download(url, dl_path, status_callback=status_callback, progress_callback=progress_callback)

        _safe_status(status_callback, "Installing update...")

        if os.path.exists(target):
            try:
                _replace_with_retry(target, backup)
            except Exception:
                # If we can't move the old exe out of the way, the update can't be applied.
                raise

        _replace_with_retry(dl_path, target)

        st = _load_state()
        # Note: this value is used as an opaque "update id" (usually a semver string like "1.2.3.0").
        st["installed_remote_version"] = remote_ver
        st["installed_remote_id"] = remote_ver
        st["installed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        st["installed_path"] = target
        _save_state(st)

    except Exception as e:
        # Best-effort fallback: try to relaunch the previous executable.
        try:
            print(f"[UPDATE] Apply-update failed: {e}")
        except Exception:
            pass

        _safe_status(status_callback, f"Update failed: {e}\nRelaunching previous version...")
        for candidate in (target, backup):
            try:
                if candidate and os.path.exists(candidate):
                    subprocess.Popen([candidate] + passthrough, close_fds=True)
                    break
            except Exception:
                pass
        return

    # Launch updated exe.
    try:
        _safe_status(status_callback, "Launching updated version...")
        subprocess.Popen([target] + passthrough, close_fds=True)
        # User requested removing the old version: best-effort cleanup of the backup.
        try:
            if os.path.exists(backup):
                os.remove(backup)
        except Exception:
            pass
    except Exception:
        pass


def handle_update_flow(argv=None, status_callback: Optional[Callable[[str], None]] = None) -> bool:
    argv = list(argv or sys.argv[1:])

    # Updater mode
    if "--apply-update" in argv:
        # In updater mode, show a minimal progress window if possible (packaged app has no console).
        ui_status = ui_progress = ui_close = None
        if status_callback is None:
            ui_status, ui_progress, ui_close = _maybe_make_qt_progress_ui(title="Updating AdminDashboard")
            status_callback = ui_status
        try:
            _run_apply_update(argv, status_callback=status_callback, progress_callback=ui_progress)
        finally:
            if ui_close:
                ui_close()
        return True

    # Normal mode (only for the packaged exe)
    if (not _is_frozen()) or ("--skip-update" in argv):
        return False

    try:
        _safe_status(status_callback, "Checking for updates...")
        releases = _http_json(GITHUB_RELEASES_API, timeout_s=5.0)
        pick = find_latest_exe_asset(releases, preferred_filename=os.path.basename(sys.executable))
        if not pick or not pick.get("download_url"):
            return False

        exe_path = sys.executable
        current_v = _get_file_version_tuple(exe_path)
        remote_v = pick.get("version_tuple")
        st = _load_state()

        installed_id = st.get("installed_remote_id") or st.get("installed_remote_version")

        # Compare using a consistent remote id:
        # - Prefer a semver extracted from asset name/tag
        # - Fall back to the release tag
        remote_id = None
        if remote_v:
            try:
                remote_id = ".".join(map(str, tuple(remote_v)))
            except Exception:
                remote_id = str(remote_v)
        if not remote_id:
            remote_id = pick.get("release_tag") or None

        if remote_v is None and installed_id == pick.get("release_tag"):
            return False

        needs = False
        if current_v and remote_v:
            needs = tuple(remote_v) > tuple(current_v)
        elif remote_v:
            needs = str(remote_id) != str(installed_id)
        else:
            needs = pick.get("release_tag") != installed_id

        if not needs:
            _safe_status(status_callback, "No updates available.")
            return False

        # Spawn updater from a temp copy of ourselves so the original exe can be replaced.
        tmp = tempfile.gettempdir()
        updater = os.path.join(tmp, f"Chiv2AdminDashboard_updater_{os.getpid()}.exe")
        try:
            shutil.copy2(exe_path, updater)
        except Exception:
            return False

        # IMPORTANT: keep this consistent with the comparison logic above.
        remote_ver_s = remote_id or ""
        cmd = [
            updater,
            "--apply-update",
            "--url",
            str(pick["download_url"]),
            "--target",
            exe_path,
            "--remote-version",
            remote_ver_s,
            "--",
        ] + argv

        subprocess.Popen(cmd, close_fds=True)
        _safe_status(status_callback, "Update found. Starting updater...")
        return True
    except Exception:
        return False

