"""
ui_state.py — small UI memory kept between sessions: table sort orders and
filter choices per screen (ui_state.json next to settings.json). UI only; the
simulation never reads it.
"""
import json
import os

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_state.json")

_data = None


def _load():
    global _data
    if _data is None:
        _data = {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                _data = loaded
        except (OSError, ValueError):
            pass
    return _data


def get(key, default=None):
    return _load().get(key, default)


def set(key, value):
    d = _load()
    if d.get(key) == value:
        return
    d[key] = value
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except OSError:
        pass


def reset():
    """Forget everything (used by tests)."""
    global _data
    _data = {}
