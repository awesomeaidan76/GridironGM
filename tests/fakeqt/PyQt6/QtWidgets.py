from ._core import MODULES as _M
globals().update(_M["QtWidgets"])


def __getattr__(name):
    raise AttributeError(f"module 'PyQt6.QtWidgets' has no attribute '{name}' (not in the PyQt6 API)")
