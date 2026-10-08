"""
Gridiron GM — American football management simulation.

Run:  python main.py
"""
import os
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

import save_manager
from ui_dialogs import LoadDialog, NewGameDialog, StartDialog
from ui_main import MainWindow, apply_palette, log_error, ERROR_LOG


def _excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    log_error(text)
    app = QApplication.instance()
    if app is not None:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unexpected error")
        box.setText(f"Something went wrong. The details were saved to:\n{ERROR_LOG}")
        box.setDetailedText(text)
        box.exec()
    else:
        sys.__excepthook__(exc_type, exc, tb)


def choose_league():
    """Show the start menu until the user starts or loads a career (or quits)."""
    while True:
        start = StartDialog()
        if start.exec() != QDialog.DialogCode.Accepted or start.choice in (None, "quit"):
            return None
        if start.choice == "new":
            dlg = NewGameDialog()
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.league is not None:
                return dlg.league
        elif start.choice == "load":
            dlg = LoadDialog()
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.path:
                try:
                    return save_manager.load(dlg.path)
                except Exception as e:
                    log_error(traceback.format_exc())
                    QMessageBox.warning(start, "Load failed", f"Could not load that save:\n{e}")
        elif start.choice == "continue":
            saves = save_manager.list_saves()
            if saves:
                try:
                    return save_manager.load(saves[0]["path"])
                except Exception as e:
                    log_error(traceback.format_exc())
                    QMessageBox.warning(start, "Load failed", f"Could not load that save:\n{e}")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    try:
        import playbook
        playbook.load_user_plays()
    except Exception:
        log_error(traceback.format_exc())
    app = QApplication(sys.argv)
    app.setApplicationName("Gridiron GM")
    app.setStyle("Fusion")
    apply_palette(app)
    sys.excepthook = _excepthook
    lg = choose_league()
    if lg is None:
        return 0
    win = MainWindow(lg)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
