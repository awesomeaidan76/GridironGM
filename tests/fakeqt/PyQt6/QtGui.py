from ._core import MODULES as _M
globals().update(_M["QtGui"])


def __getattr__(name):
    raise AttributeError(f"module 'PyQt6.QtGui' has no attribute '{name}' (not in the PyQt6 API)")
