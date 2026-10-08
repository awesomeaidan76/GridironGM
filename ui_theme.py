"""
ui_theme.py — colours, fonts and the application stylesheet.
"""
from settings import settings

ACCENTS = {
    "crimson": "#e5484d",
    "royal": "#3b82f6",
    "emerald": "#10b981",
    "amber": "#f59e0b",
    "violet": "#8b5cf6",
    "teal": "#14b8a6",
}

DARK = {
    "bg0": "#0d1219", "bg1": "#121924", "bg2": "#18212e", "card": "#161e2a",
    "card_alt": "#1a2331", "hover": "#202b3b", "border": "#253043",
    "border_soft": "#1e2836", "text": "#e6ebf2", "text2": "#a3afc0",
    "muted": "#66748a", "good": "#3fb950", "warn": "#d29922", "bad": "#f85149",
    "info": "#58a6ff", "gold": "#e3b341", "input": "#0f1620", "header": "#121a25",
    "chip": "#202a39",
}
LIGHT = {
    "bg0": "#eef1f6", "bg1": "#ffffff", "bg2": "#f6f8fb", "card": "#ffffff",
    "card_alt": "#f7f9fc", "hover": "#eaf0f8", "border": "#d9e0ea",
    "border_soft": "#e7ecf2", "text": "#121826", "text2": "#475467",
    "muted": "#8590a2", "good": "#1a7f37", "warn": "#9a6700", "bad": "#cf222e",
    "info": "#0969da", "gold": "#9a6700", "input": "#ffffff", "header": "#f3f6fa",
    "chip": "#eef2f7",
}

# Attribute (1-100) colour bands, FM style
ATTR_BANDS_DARK = [(90, "#38bdf8"), (75, "#34d399"), (60, "#a3e635"), (45, "#fbbf24"), (0, "#f87171")]
ATTR_BANDS_LIGHT = [(90, "#0369a1"), (75, "#047857"), (60, "#4d7c0f"), (45, "#b45309"), (0, "#b91c1c")]
# Current Ability (1-200) bands
CA_BANDS = [(180, 90), (140, 75), (100, 60), (70, 45), (0, 0)]


def palette():
    return LIGHT if settings["theme"] == "light" else DARK


def T(key):
    return palette()[key]


def accent():
    return ACCENTS.get(settings["accent"], ACCENTS["crimson"])


def attr_color(value):
    bands = ATTR_BANDS_LIGHT if settings["theme"] == "light" else ATTR_BANDS_DARK
    for floor, col in bands:
        if value >= floor:
            return col
    return bands[-1][1]


def ca_color(ca):
    for floor, attr_equiv in CA_BANDS:
        if ca >= floor:
            return attr_color(attr_equiv)
    return attr_color(0)


def ovr_color(v):
    """Colour for a 1-99 rating (75 = average starter)."""
    for floor, attr_equiv in ((90, 95), (82, 82), (74, 68), (66, 52), (0, 30)):
        if v >= floor:
            return attr_color(attr_equiv)
    return attr_color(0)


def morale_color(m):
    if m >= 75:
        return T("good")
    if m >= 50:
        return T("text2")
    if m >= 30:
        return T("warn")
    return T("bad")


def result_color(r):
    return {"W": T("good"), "L": T("bad"), "T": T("warn")}.get(r, T("text2"))


def fs(delta=0):
    return max(8, settings["font_size"] + delta)


def font_family():
    return "'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif"


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def stylesheet():
    p = palette()
    a = accent()
    f = settings["font_size"]
    pad = {"compact": "2px 6px", "normal": "5px 8px", "comfortable": "8px 10px"}.get(
        settings["table_density"], "5px 8px")
    return f"""
    * {{ font-family: {font_family()}; font-size: {f}px; }}
    QMainWindow, QDialog {{ background: {p['bg0']}; color: {p['text']}; }}
    QWidget {{ color: {p['text']}; }}
    QWidget#screen {{ background: {p['bg0']}; }}
    QLabel {{ background: transparent; }}
    QLabel#h1 {{ font-size: {f + 9}px; font-weight: 700; }}
    QLabel#h2 {{ font-size: {f + 4}px; font-weight: 700; }}
    QLabel#h3 {{ font-size: {f + 1}px; font-weight: 700; }}
    QLabel#sub {{ color: {p['text2']}; }}
    QLabel#muted {{ color: {p['muted']}; font-size: {f - 1}px; }}
    QLabel#caps {{ color: {p['muted']}; font-size: {f - 2}px; font-weight: 700;
                   }}
    QLabel#bigvalue {{ font-size: {f + 13}px; font-weight: 800; }}
    QLabel#chip {{ background: {p['chip']}; border: 1px solid {p['border']};
                   border-radius: 9px; padding: 1px 8px; color: {p['text2']};
                   font-size: {f - 2}px; font-weight: 600; }}

    QFrame#topbar {{ background: {p['bg1']}; border-bottom: 1px solid {p['border']}; }}
    QFrame#sidebar {{ background: {p['bg1']}; border-right: 1px solid {p['border']}; }}
    QFrame#card {{ background: {p['card']}; border: 1px solid {p['border_soft']};
                   border-radius: 10px; }}
    QFrame#tile {{ background: {p['card']}; border: 1px solid {p['border_soft']};
                   border-radius: 10px; }}
    QFrame#hero {{ border-radius: 12px; }}
    QFrame#divider {{ background: {p['border']}; max-height: 1px; min-height: 1px; }}

    QPushButton {{ background: {p['bg2']}; border: 1px solid {p['border']};
                   border-radius: 7px; padding: 6px 14px; color: {p['text']}; }}
    QPushButton:hover {{ background: {p['hover']}; }}
    QPushButton:pressed {{ background: {p['border']}; }}
    QPushButton:disabled {{ color: {p['muted']}; background: {p['bg1']};
                            border-color: {p['border_soft']}; }}
    QPushButton#primary {{ background: {a}; border: 1px solid {a}; color: white;
                           font-weight: 700; padding: 7px 18px; }}
    QPushButton#primary:hover {{ background: {_rgba(a, 0.85)}; }}
    QPushButton#primary:disabled {{ background: {_rgba(a, 0.35)}; border-color: transparent;
                                    color: {_rgba('#ffffff', 0.6)}; }}
    QPushButton#danger {{ color: {p['bad']}; }}
    QPushButton#ghost {{ background: transparent; border: none; color: {p['text2']};
                         padding: 4px 8px; }}
    QPushButton#ghost:hover {{ color: {p['text']}; background: {p['hover']}; }}
    QPushButton#nav {{ background: transparent; border: none; border-radius: 7px;
                       text-align: left; padding: 7px 12px; color: {p['text2']}; }}
    QPushButton#nav:hover {{ background: {p['hover']}; color: {p['text']}; }}
    QPushButton#nav:checked {{ background: {_rgba(a, 0.16)}; color: {p['text']};
                               font-weight: 700; border-left: 3px solid {a}; }}
    QPushButton#chipbtn {{ background: {p['chip']}; border: 1px solid {p['border']};
                           border-radius: 12px; padding: 3px 11px; color: {p['text2']};
                           font-size: {f - 1}px; }}
    QPushButton#chipbtn:checked {{ background: {_rgba(a, 0.2)}; border-color: {a};
                                   color: {p['text']}; font-weight: 700; }}
    QToolButton {{ background: {p['bg2']}; border: 1px solid {p['border']};
                   border-radius: 7px; padding: 6px 8px; color: {p['text']}; }}
    QToolButton:hover {{ background: {p['hover']}; }}
    QToolButton::menu-indicator {{ image: none; }}

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {p['input']}; border: 1px solid {p['border']}; border-radius: 7px;
        padding: 5px 8px; color: {p['text']}; selection-background-color: {a}; }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {a}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{ background: {p['card']}; border: 1px solid {p['border']};
        selection-background-color: {_rgba(a, 0.3)}; color: {p['text']}; }}

    QTableWidget, QTableView {{ background: {p['card']}; alternate-background-color: {p['card_alt']};
        border: 1px solid {p['border_soft']}; border-radius: 8px; gridline-color: transparent;
        selection-background-color: {_rgba(a, 0.28)}; selection-color: {p['text']}; }}
    QTableWidget::item {{ padding: {pad}; border-bottom: 1px solid {p['border_soft']}; }}
    QHeaderView::section {{ background: {p['header']}; color: {p['muted']}; border: none;
        border-bottom: 1px solid {p['border']}; padding: 6px 8px; font-weight: 700;
        font-size: {f - 2}px; }}
    QHeaderView::section:hover {{ color: {p['text']}; }}
    QTableCornerButton::section {{ background: {p['header']}; border: none; }}

    QListWidget {{ background: {p['card']}; border: 1px solid {p['border_soft']};
                   border-radius: 8px; padding: 4px; }}
    QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {_rgba(a, 0.25)}; color: {p['text']}; }}
    QListWidget::item:hover {{ background: {p['hover']}; }}

    QTextBrowser {{ background: {p['card']}; border: 1px solid {p['border_soft']};
                    border-radius: 8px; padding: 6px; }}

    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ background: transparent; color: {p['muted']}; padding: 8px 14px;
                    border: none; border-bottom: 2px solid transparent; font-weight: 600; }}
    QTabBar::tab:selected {{ color: {p['text']}; border-bottom: 2px solid {a}; }}
    QTabBar::tab:hover {{ color: {p['text']}; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['muted']}; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 4px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
                            border: 1px solid {p['border']}; background: {p['input']}; }}
    QCheckBox::indicator:checked {{ background: {a}; border-color: {a}; }}
    QSlider::groove:horizontal {{ height: 6px; background: {p['border']}; border-radius: 3px; }}
    QSlider::sub-page:horizontal {{ background: {a}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: white; border: 2px solid {a}; width: 14px;
                                  height: 14px; margin: -6px 0; border-radius: 8px; }}
    QProgressBar {{ background: {p['border_soft']}; border: none; border-radius: 4px;
                    height: 8px; text-align: center; color: transparent; }}
    QProgressBar::chunk {{ background: {a}; border-radius: 4px; }}
    QMenu {{ background: {p['card']}; border: 1px solid {p['border']}; padding: 4px; }}
    QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {_rgba(a, 0.25)}; }}
    QToolTip {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['border']};
                padding: 5px; }}
    QStatusBar {{ background: {p['bg1']}; color: {p['text2']}; border-top: 1px solid {p['border']}; }}
    QGroupBox {{ border: 1px solid {p['border_soft']}; border-radius: 8px; margin-top: 14px;
                 padding: 10px; font-weight: 700; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {p['muted']}; }}
    QSplitter::handle {{ background: {p['border_soft']}; }}
    """
