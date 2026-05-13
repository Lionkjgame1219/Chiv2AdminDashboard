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
import calendar
from typing import Callable, Optional

# Auto-update for the PyInstaller onefile Windows build.
# Normal mode checks GitHub releases at startup. Updater mode runs as a separate
# exe copy so it can overwrite the original.

GITHUB_REPO = "Lionkjgame1219/Chiv2AdminDashboard"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=10"
APPDATA_DIRNAME = "Chiv2AdminDashboard"


def _safe_status(cb: Optional[Callable[[str], None]], msg: str) -> None:
    if not cb:
        return
    try:
        cb(str(msg))
    except Exception:
        pass


def _maybe_make_qt_progress_ui(title: str = "Updating..."):
    """Tiny progress window for the updater process. Returns (status, progress, close), any may be None."""

    try:
        # Local import so source runs and unit tests don't require Qt.
        from PyQt5.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget
        from PyQt5.QtCore import Qt

        app = QApplication.instance()
        if app is None:
            # Pass an empty argv so Qt doesn't see --apply-update etc.
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
    # Prefer stable releases; fall back to pre-releases only if no stable .exe exists.
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
            # Prefer assets whose name matches the running exe.
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


def _format_version(v) -> str:
    if not v:
        return "unknown"
    try:
        return ".".join(map(str, tuple(v)))
    except Exception:
        return str(v)


def _exe_fingerprint(path: str):
    """Cheap (size, mtime) fingerprint used to detect update loops when file version metadata is unreliable."""

    try:
        return int(os.path.getsize(path)), int(os.path.getmtime(path))
    except Exception:
        return None, None


def _installed_recently(state: dict, window_s: float = 15 * 60) -> bool:
    try:
        ts = state.get("installed_at")
        if not ts:
            return False
        # Stored as UTC ISO-8601, e.g. 2025-01-01T00:00:00Z.
        t = time.strptime(str(ts), "%Y-%m-%dT%H:%M:%SZ")
        installed_epoch = calendar.timegm(t)
        return (time.time() - float(installed_epoch)) <= float(window_s)
    except Exception:
        return False


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
    url = target = remote_ver = release_tag = None
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
        elif tok == "--release-tag":
            release_tag = next(it, None)
    return url, target, remote_ver, release_tag, passthrough


def _run_apply_update(
    argv,
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[Optional[int]], None]] = None,
) -> None:
    url, target, remote_ver, release_tag, passthrough = _parse_apply_args(argv)
    # Don't carry a stale --post-update flag into the relaunch.
    passthrough = [a for a in passthrough if not a.startswith("--post-update=")]
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
            # If we can't move the old exe aside, we can't apply the update.
            _replace_with_retry(target, backup)

        _replace_with_retry(dl_path, target)

        st = _load_state()
        # Opaque "update id", usually a semver string like "1.2.3.0".
        st["installed_remote_version"] = remote_ver
        st["installed_remote_id"] = remote_ver
        st["installed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        st["installed_path"] = target

        # Fingerprint lets us recognize this exe later if the embedded file version is missing or stale.
        size, mtime = _exe_fingerprint(target)
        st["installed_exe_size"] = size
        st["installed_exe_mtime"] = mtime
        try:
            st["installed_local_file_version"] = _format_version(_get_file_version_tuple(target))
        except Exception:
            st["installed_local_file_version"] = None

        _save_state(st)

    except Exception as e:
        # Fall back to relaunching the previous executable.
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

    # The new version detects "first launch after update" via the state file, so no extra argv flag.
    try:
        _safe_status(status_callback, "Launching updated version...")
        launch_args = [target] + passthrough
        subprocess.Popen(launch_args, close_fds=True)
        try:
            if os.path.exists(backup):
                os.remove(backup)
        except Exception:
            pass
    except Exception:
        pass


def handle_update_flow(argv=None, status_callback: Optional[Callable[[str], None]] = None) -> bool:
    argv = list(argv or sys.argv[1:])

    # Updater mode: show a minimal progress window since the packaged app has no console.
    if "--apply-update" in argv:
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

    # Normal mode only runs on the packaged exe.
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

        # Pick a stable remote id: semver from asset name/tag, else the release tag.
        remote_id = None
        if remote_v:
            try:
                remote_id = ".".join(map(str, tuple(remote_v)))
            except Exception:
                remote_id = str(remote_v)
        if not remote_id:
            remote_id = pick.get("release_tag") or None

        # Loop guard: skip if we already applied this remote_id to this exact exe.
        cur_size, cur_mtime = _exe_fingerprint(exe_path)
        st_size = st.get("installed_exe_size")
        st_mtime = st.get("installed_exe_mtime")
        fingerprint_matches = (
            cur_size is not None
            and cur_mtime is not None
            and st_size is not None
            and st_mtime is not None
            and int(st_size) == int(cur_size)
            and int(st_mtime) == int(cur_mtime)
        )

        # Antivirus/copy/restore can change the file timestamp and break the fingerprint match.
        # The recorded local file version is a backup signal that this is still the installed exe.
        state_local_v = st.get("installed_local_file_version")
        version_matches_state = bool(state_local_v) and (_format_version(current_v) == str(state_local_v))

        already_installed = (
            remote_id is not None
            and installed_id is not None
            and str(remote_id) == str(installed_id)
            and (fingerprint_matches or version_matches_state or _installed_recently(st))
        )

        _safe_status(
            status_callback,
            f"Current version: {_format_version(current_v)} | Latest: {_format_version(remote_v)}",
        )

        if remote_v is None and installed_id == pick.get("release_tag"):
            return False

        needs = False
        if already_installed:
            needs = False
        elif current_v and remote_v:
            needs = tuple(remote_v) > tuple(current_v)
        elif remote_v:
            # No readable local file version — fall back to state + fingerprint.
            needs = (str(remote_id) != str(installed_id)) or (not fingerprint_matches)
        else:
            needs = pick.get("release_tag") != installed_id

        if not needs:
            _safe_status(status_callback, "No updates available.")
            return False

        # Run the updater from a temp copy of ourselves so the original exe is free to overwrite.
        tmp = tempfile.gettempdir()
        updater = os.path.join(tmp, f"Chiv2AdminDashboard_updater_{os.getpid()}.exe")
        try:
            shutil.copy2(exe_path, updater)
        except Exception:
            return False

        # Strip --post-update=... so a follow-up update can't re-fire it.
        clean_argv = [a for a in argv if not a.startswith("--post-update=")]

        # Must stay consistent with the comparison logic above.
        remote_ver_s = remote_id or ""
        release_tag_s = str(pick.get("release_tag") or "")
        cmd = [
            updater,
            "--apply-update",
            "--url",
            str(pick["download_url"]),
            "--target",
            exe_path,
            "--remote-version",
            remote_ver_s,
            "--release-tag",
            release_tag_s,
            "--",
        ] + clean_argv

        subprocess.Popen(cmd, close_fds=True)
        _safe_status(status_callback, "Update found. Starting updater...")
        return True
    except Exception:
        return False

