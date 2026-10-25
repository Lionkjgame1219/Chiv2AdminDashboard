"""Persistent settings stored in the `localconfig` file.

The file is a JSON object mapping each setting key to a string value:

    {
      "primary_webhook": "https://discord.com/api/webhooks/...",
      "discord_channel_id": "1406994740116979875",
      "last_ban_reason": "Teamkilling"
    }

JSON escapes quotes, line breaks and other control characters inside values, so a pasted
multi-line reason can't spill into (and shift) neighbouring settings the way the old
one-setting-per-line layout did. Files still in that legacy layout are migrated on first read.

All values are strings, with the same conventions callers used before (e.g. 'None' for
"asked and left empty"). A missing key reads as the caller's default.
"""
import json
import os
import shutil
import threading

CONFIG_PATH = "localconfig"
LEGACY_BACKUP_PATH = "localconfig.legacy.bak"
CORRUPT_BACKUP_PATH = "localconfig.corrupt.bak"

PRESET_COUNT = 10
ADMIN_PRESET_COUNT = 3
SERVER_PRESET_COUNT = 3

DISCORD_WEBHOOK_PREFIX = "https://discord.com/api/webhooks/"


def preset_key(slot: int) -> str:
    return f"preset_{int(slot)}"


def admin_preset_key(slot: int) -> str:
    return f"admin_preset_{int(slot)}"


def server_preset_key(slot: int) -> str:
    return f"server_preset_{int(slot)}"


# Legacy layout: the setting stored on each line of the old line-based file. Frozen —
# only used to migrate old files. New settings go in SETTING_KEYS, never here.
LEGACY_LINE_KEYS = (
    'primary_webhook',                                      # 0
    'secondary_webhook',                                    # 1
    'discord_user_id',                                      # 2
    *(preset_key(i) for i in range(PRESET_COUNT)),          # 3..12
    'theme',                                                # 13
    'last_ban_reason',                                      # 14
    'last_ban_duration',                                    # 15
    'last_kick_reason',                                     # 16
    'last_admin_msg',                                       # 17
    'last_server_msg',                                      # 18
    'last_add_time',                                        # 19
    *(admin_preset_key(i) for i in range(ADMIN_PRESET_COUNT)),    # 20..22
    *(server_preset_key(i) for i in range(SERVER_PRESET_COUNT)),  # 23..25
    'console_vk',                                           # 26
    'discord_bot_token',                                    # 27
    'discord_channel_id',                                   # 28
    'random_pick_weapons',                                  # 29
    'random_pick_players',                                  # 30
    'random_pick_filters',                                  # 31
    'first_time_guide_shown',                               # 32
)

# Every known setting, in the order they're written to disk. Unknown keys found in the
# file are preserved (written after these) but get_value/set_value reject them, so a
# typo'd key fails loudly instead of silently reading the default.
SETTING_KEYS = LEGACY_LINE_KEYS
_KNOWN_KEYS = frozenset(SETTING_KEYS)

# The whole read-modify-write cycle runs under this lock so concurrent setters (UI thread,
# worker threads) can't drop each other's changes.
_lock = threading.RLock()


class ConfigReadError(Exception):
    """The file exists but couldn't be read; writing now would wipe it."""


def _is_digits_or_none(v: str) -> bool:
    return v == 'None' or v.isdigit()


def _is_json(v: str) -> bool:
    try:
        json.loads(v)
        return True
    except ValueError:
        return False


# Sanity checks for values coming out of a legacy file. Those files may already be
# corrupted by the line-shift bug (a value containing a line break pushed every later
# setting down a line), so anything that doesn't look right for its slot is dropped
# rather than migrated — the user gets re-prompted instead of the app misbehaving.
_LEGACY_VALIDATORS = {
    'primary_webhook':        lambda v: v == 'None' or v.startswith(DISCORD_WEBHOOK_PREFIX),
    'secondary_webhook':      lambda v: v == 'None' or v.startswith(DISCORD_WEBHOOK_PREFIX),
    'discord_user_id':        _is_digits_or_none,
    'theme':                  lambda v: v in ('dark', 'light'),
    'last_ban_duration':      str.isdigit,
    'last_add_time':          lambda v: v.lstrip('-').isdigit(),
    'console_vk':             str.isdigit,
    'discord_bot_token':      lambda v: v == 'None' or (' ' not in v and '.' in v),
    'discord_channel_id':     _is_digits_or_none,
    'random_pick_weapons':    _is_json,
    'random_pick_players':    _is_json,
    'random_pick_filters':    _is_json,
    'first_time_guide_shown': lambda v: v in ('pending', 'true'),
}


def _parse_legacy(text: str) -> dict:
    # Only '\n' ever separated settings in the old writer. Splitting on it alone (instead
    # of splitlines(), which the old reader used) keeps values containing '\r', '\x85',
    # ' ' etc. intact if the file hasn't been rewritten since they were saved.
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    lines = [line[:-1] if line.endswith('\r') else line for line in lines]

    if len(lines) > len(LEGACY_LINE_KEYS):
        print(f"[CONFIG] Legacy localconfig has {len(lines)} lines (expected at most "
              f"{len(LEGACY_LINE_KEYS)}); settings may have been shifted by a multi-line value")

    data = {}
    dropped = []
    for key, value in zip(LEGACY_LINE_KEYS, lines):
        if value == '':
            continue
        validator = _LEGACY_VALIDATORS.get(key)
        if validator is not None and not validator(value):
            dropped.append(key)
            continue
        data[key] = value

    if dropped:
        print(f"[CONFIG] Dropped invalid legacy settings during migration: {', '.join(dropped)}")
    return data


def _coerce(value):
    """Normalise a JSON value to the string form callers expect (None -> skip)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _read_text():
    """File contents, or None if there is no file. Raises ConfigReadError otherwise."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8-sig', newline='') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        raise ConfigReadError(str(e)) from e


def _write(data: dict) -> None:
    ordered = {k: data[k] for k in SETTING_KEYS if k in data}
    ordered.update((k, v) for k, v in data.items() if k not in ordered)

    # Write to a temp file and swap it in, so a reader never sees a half-written file.
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(ordered, f, indent=2, ensure_ascii=False)
        f.write('\n')
    try:
        os.replace(tmp_path, CONFIG_PATH)
    except OSError:
        # Windows refuses the swap while something (AV, an editor) holds the target open.
        shutil.copyfile(tmp_path, CONFIG_PATH)
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _load() -> dict:
    """Read the settings, migrating a legacy or unreadable file. Caller holds _lock."""
    text = _read_text()
    if text is None:
        return {}

    stripped = text.strip()
    if not stripped:
        return {}

    # Legacy files start with a webhook URL, 'None' or a blank line — never '{'.
    if not stripped.startswith('{'):
        data = _parse_legacy(text)
        try:
            shutil.copyfile(CONFIG_PATH, LEGACY_BACKUP_PATH)
        except OSError as e:
            print(f"[CONFIG] Could not back up legacy localconfig: {e}")
        try:
            _write(data)
            print(f"[CONFIG] Migrated legacy localconfig to the keyed format "
                  f"(backup: {LEGACY_BACKUP_PATH})")
        except Exception as e:
            # Still serve the migrated values; the next successful save writes the new format.
            print(f"[CONFIG] Could not write migrated localconfig: {e}")
        return data

    try:
        raw = json.loads(stripped)
    except ValueError:
        raw = None
    if not isinstance(raw, dict):
        print(f"[CONFIG] localconfig is not valid JSON; moved to {CORRUPT_BACKUP_PATH} "
              f"and starting from empty settings")
        try:
            shutil.copyfile(CONFIG_PATH, CORRUPT_BACKUP_PATH)
            _write({})
        except Exception:
            pass
        return {}

    data = {}
    for k, v in raw.items():
        v = _coerce(v)
        if v is not None:
            data[str(k)] = v
    return data


def _check_key(key: str) -> None:
    if key not in _KNOWN_KEYS:
        raise KeyError(f"Unknown localconfig setting: {key!r}")


def exists() -> bool:
    return os.path.exists(CONFIG_PATH)


def load_all() -> dict:
    """Snapshot of every stored setting. Empty if the file is missing or unreadable."""
    with _lock:
        try:
            return dict(_load())
        except ConfigReadError as e:
            print(f"[CONFIG] Could not read localconfig: {e}")
            return {}


def get_value(key: str, default: str = "") -> str:
    _check_key(key)
    return load_all().get(key, default)


def set_values(values: dict) -> bool:
    """Update several settings in one write. Returns False if nothing was saved."""
    for key in values:
        _check_key(key)
    with _lock:
        try:
            data = _load()
        except ConfigReadError as e:
            # Don't overwrite a file we couldn't read — that would wipe every other setting.
            print(f"[CONFIG] Not saving {', '.join(values)}: could not read localconfig: {e}")
            return False
        for key, value in values.items():
            data[key] = "" if value is None else str(value)
        try:
            _write(data)
            return True
        except Exception as e:
            print(f"[CONFIG] Could not save localconfig: {e}")
            return False


def set_value(key: str, value: str) -> bool:
    return set_values({key: value})


def write_all(values: dict) -> bool:
    """Replace the whole file with `values` (used by the initial setup)."""
    for key in values:
        _check_key(key)
    with _lock:
        try:
            _write({k: "" if v is None else str(v) for k, v in values.items()})
            return True
        except Exception as e:
            print(f"[CONFIG] Could not save localconfig: {e}")
            return False
