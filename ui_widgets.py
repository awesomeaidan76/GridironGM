"""
ui_widgets.py — reusable widgets: sortable tables, cards, tiles, bars, charts.
"""
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QSizePolicy, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from contracts import fmt_money
from ratings import stars_text
from settings import settings
from ui_theme import T, accent, attr_color, ca_color, ovr_color, fs

USER_ROLE = Qt.ItemDataRole.UserRole
ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


# ── Formatting helpers ────────────────────────────────────────────────────────

def money(v):
    return fmt_money(int(v))


def cell(text, sort=None, color=None, bold=False, tip=None, align=None):
    """A table cell spec: display text plus optional sort key, colour, etc."""
    return {"text": "" if text is None else str(text), "sort": sort, "color": color,
            "bold": bold, "tip": tip, "align": align}


def ovr_cell(v, show=True):
    """A 1-99 rating cell (player OVR, team unit rating, scouted estimate)."""
    if not show:
        from ratings import ovr_tier
        return cell(ovr_tier(v), sort=v)
    return cell(v, sort=v, color=ovr_color(v), bold=True)


def pot_text(p, scouting=10):
    lo, hi = p.scouted_pot_range(scouting)
    return f"{lo}" if lo == hi else f"{lo}–{hi}"


def pot_cell(p, scouting=10):
    lo, hi = p.scouted_pot_range(scouting)
    return cell(pot_text(p, scouting), sort=hi, color=ovr_color((lo + hi) // 2))


def team_cell(value, unit):
    """Team unit strength shown on the 1-99 team scale."""
    from ratings import unit_ovr
    return ovr_cell(unit_ovr(value, unit))


def attr_cell(v):
    if settings["color_attributes"]:
        return cell(v, sort=v, color=attr_color(v), bold=v >= 75)
    return cell(v, sort=v)






def personality(p):
    """FM-style personality description from hidden traits."""
    h = p.hidden
    w, t, a, amb, c, bg = (h.get("work_rate", 50), h.get("temperament", 50),
                           h.get("adaptability", 50), h.get("ambition", 50),
                           h.get("consistency", 50), h.get("big_game", 50))
    if w >= 80 and t >= 70:
        return "Model Professional"
    if w >= 80 and amb >= 75:
        return "Driven"
    if amb >= 80:
        return "Ambitious"
    if bg >= 82:
        return "Big-Game Player"
    if t <= 25:
        return "Volatile"
    if w <= 25:
        return "Lazy"
    if c <= 25:
        return "Inconsistent"
    if t >= 80:
        return "Composed"
    if a >= 80:
        return "Quick Learner"
    if w >= 70:
        return "Hard Worker"
    if amb <= 25:
        return "Content"
    return "Balanced"


def form_cell(p):
    """Hot / cold indicator from a player's current game-to-game form."""
    if not p.season_stats.get("gp"):
        return cell("—", 0.0, color=T("muted"))
    z = getattr(p, "form_z", 0.0)
    if z >= 1.0:
        return cell("▲▲ Hot", z, color=T("good"), tip="On a hot streak")
    if z >= 0.4:
        return cell("▲ Good", z, color=T("good"))
    if z <= -1.0:
        return cell("▼▼ Cold", z, color=T("bad"), tip="Struggling for form")
    if z <= -0.4:
        return cell("▼ Poor", z, color=T("warn"))
    return cell("● Steady", z, color=T("text2"))


def trait_word(v):
    if v >= 85:
        return "Exceptional"
    if v >= 70:
        return "Very good"
    if v >= 55:
        return "Good"
    if v >= 40:
        return "Average"
    if v >= 25:
        return "Poor"
    return "Very poor"


def h_label(text, kind="h2"):
    lbl = QLabel(text)
    lbl.setObjectName(kind)
    return lbl


def divider():
    f = QFrame()
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def confirm(parent, title, text):
    if not settings["confirm_actions"]:
        return True
    btn = QMessageBox.question(parent, title, text,
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return btn == QMessageBox.StandardButton.Yes


def info(parent, title, text):
    QMessageBox.information(parent, title, text)


# ── Table ─────────────────────────────────────────────────────────────────────

class SortItem(QTableWidgetItem):
    """Table item that sorts by a numeric key when one is provided."""

    def __init__(self, text, key=None):
        super().__init__(text)
        self._key = key

    def __lt__(self, other):
        a = self._key if self._key is not None else self.text()
        b = getattr(other, "_key", None)
        if b is None:
            b = other.text()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a < b
        return str(a) < str(b)


class DataTable(QTableWidget):
    """
    Read-only, sortable table. Fill it with set_rows(); each cell is either a
    plain value or a dict from cell(). keys[i] is attached to row i so that
    double-click and selection still work after the user re-sorts.
    """

    def __init__(self, columns, stretch=None, sortable=True, parent=None):
        super().__init__(parent)
        self.columns = list(columns)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(self.columns)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        hh = self.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setDefaultAlignment(ALIGN_LEFT)
        if stretch is not None:
            hh.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
        else:
            hh.setStretchLastSection(True)
        row_h = {"compact": 24, "normal": 30, "comfortable": 36}.get(settings["table_density"], 30)
        self.verticalHeader().setDefaultSectionSize(row_h)
        self._sortable = sortable
        self._user_sorted = False
        self._internal = False
        hh.sortIndicatorChanged.connect(self._sort_changed)
        self.cellDoubleClicked.connect(self._double_clicked)
        self.on_activate = None
        self.setSortingEnabled(False)

    def _sort_changed(self, section, order):
        if not self._internal:
            self._user_sorted = True

    def _double_clicked(self, row, col):
        if self.on_activate is not None:
            key = self.key_at(row)
            if key is not None:
                self.on_activate(key)

    def set_rows(self, rows, keys=None):
        hh = self.horizontalHeader()
        sort_col = hh.sortIndicatorSection()
        sort_order = hh.sortIndicatorOrder()
        self.setSortingEnabled(False)
        # Drop the old rows rather than clearContents(): refilling a table that has been sorted
        # with clearContents() is quadratic in Qt 6 (a 1,500-row Players list took minutes).
        self.setRowCount(0)
        self.setRowCount(len(rows))
        bold = QFont()
        bold.setBold(True)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                if c >= len(self.columns):
                    break
                if isinstance(value, dict):
                    text, key = value["text"], value["sort"]
                else:
                    text = "" if value is None else str(value)
                    key = value if isinstance(value, (int, float)) else None
                item = SortItem(text, key)
                numeric = key is not None and isinstance(key, (int, float)) and c > 0
                align = value.get("align") if isinstance(value, dict) else None
                flag = align if align is not None else (ALIGN_CENTER if numeric else ALIGN_LEFT)
                item.setTextAlignment(int(flag.value))
                if isinstance(value, dict):
                    if value["color"]:
                        item.setForeground(QBrush(QColor(value["color"])))
                    if value["bold"]:
                        item.setFont(bold)
                    if value["tip"]:
                        item.setToolTip(value["tip"])
                if c == 0 and keys is not None and r < len(keys):
                    item.setData(USER_ROLE, keys[r])
                self.setItem(r, c, item)
        if self._sortable:
            self._internal = True
            if self._user_sorted and sort_col >= 0:
                self.setSortingEnabled(True)
                self.sortItems(sort_col, sort_order)
            else:
                hh.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
                self.setSortingEnabled(True)
            self._internal = False

    def key_at(self, row):
        item = self.item(row, 0)
        return item.data(USER_ROLE) if item is not None else None

    def selected_key(self):
        row = self.currentRow()
        return self.key_at(row) if row >= 0 else None

    def fit_height(self, max_rows=None):
        n = self.rowCount() if max_rows is None else min(self.rowCount(), max_rows)
        h = self.verticalHeader().defaultSectionSize() * n + 34
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)


# ── Containers ────────────────────────────────────────────────────────────────

class Card(QFrame):
    def __init__(self, title=None, right=None, parent=None, margins=14):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(margins, margins - 2, margins, margins)
        self.body.setSpacing(8)
        if title is not None or right is not None:
            head = QHBoxLayout()
            head.setSpacing(8)
            self.title_label = QLabel(title or "")
            self.title_label.setObjectName("h3")
            head.addWidget(self.title_label)
            head.addStretch(1)
            if right is not None:
                head.addWidget(right)
            self.body.addLayout(head)

    def add(self, w, stretch=0):
        self.body.addWidget(w, stretch)
        return w


class StatTile(QFrame):
    def __init__(self, label, value="—", sub="", parent=None):
        super().__init__(parent)
        self.setObjectName("tile")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self.lbl = QLabel(label.upper())
        self.lbl.setObjectName("caps")
        self.val = QLabel(str(value))
        self.val.setObjectName("bigvalue")
        self.sub = QLabel(sub)
        self.sub.setObjectName("muted")
        lay.addWidget(self.lbl)
        lay.addWidget(self.val)
        lay.addWidget(self.sub)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set(self, value, sub=None, color=None):
        self.val.setText(str(value))
        self.val.setStyleSheet(f"color: {color};" if color else "")
        if sub is not None:
            self.sub.setText(sub)


class TeamBadge(QLabel):
    def __init__(self, team=None, size=34, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(ALIGN_CENTER)
        if team is not None:
            self.set_team(team)

    def set_team(self, team):
        c1, c2 = team.colors
        self.setText(team.abbr)
        r = self._size // 2
        self.setStyleSheet(f"background: {c1}; color: #ffffff; border: 2px solid {c2};"
                           f"border-radius: {r}px; font-weight: 800;"
                           f"font-size: {max(8, self._size // 3 - 1)}px;")


class Chip(QLabel):
    def __init__(self, text, color=None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("chip")
        if color:
            self.setStyleSheet(f"color: {color}; border-color: {color};")


# ── Painted widgets ───────────────────────────────────────────────────────────

class AttrBar(QWidget):
    """Name, coloured value and a slim bar — the core of the player profile."""

    def __init__(self, name, value, maximum=100, parent=None, tip=None):
        super().__init__(parent)
        self.name = name
        self.value = value
        self.maximum = maximum
        self.setMinimumHeight(22)
        self.setMaximumHeight(24)
        if tip:
            self.setToolTip(tip)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        num_w = 34
        name_w = int(w * 0.48)
        p.setPen(QColor(T("text2")))
        p.drawText(QRectF(0, 0, name_w, h), int(ALIGN_LEFT.value), self.name)
        col = QColor(attr_color(self.value) if self.maximum == 100 else ca_color(self.value))
        bar_x = name_w + 4
        bar_w = max(10, w - name_w - num_w - 10)
        bar_h = 6
        y = (h - bar_h) / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(T("border_soft"))))
        p.drawRoundedRect(QRectF(bar_x, y, bar_w, bar_h), 3, 3)
        frac = max(0.0, min(1.0, self.value / float(self.maximum)))
        p.setBrush(QBrush(col))
        p.drawRoundedRect(QRectF(bar_x, y, bar_w * frac, bar_h), 3, 3)
        f = QFont(p.font())
        f.setBold(True)
        p.setFont(f)
        p.setPen(col)
        p.drawText(QRectF(w - num_w, 0, num_w, h), int(ALIGN_RIGHT.value), str(self.value))
        p.end()


class LineChart(QWidget):
    """Minimal multi-series line chart drawn with QPainter."""

    def __init__(self, parent=None, y_label="", height=220):
        super().__init__(parent)
        self.series = []          # [(name, color, [(x, y), ...])]
        self.y_label = y_label
        self.setMinimumHeight(height)

    def set_series(self, series):
        self.series = series
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        left, right, top, bottom = 46, 14, 14, 28
        pts = [pt for _, _, s in self.series for pt in s]
        p.setPen(QColor(T("muted")))
        if not pts:
            p.drawText(QRectF(0, 0, w, h), int(ALIGN_CENTER.value), "No data yet")
            p.end()
            return
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        if x1 == x0:
            x0, x1 = x0 - 1, x1 + 1
        pad = (y1 - y0) * 0.12 or 1.0
        y0, y1 = y0 - pad, y1 + pad
        pw, ph = w - left - right, h - top - bottom

        def X(x):
            return left + (x - x0) / (x1 - x0) * pw

        def Y(y):
            return top + (1 - (y - y0) / (y1 - y0)) * ph

        grid = QPen(QColor(T("border_soft")))
        grid.setWidth(1)
        for i in range(5):
            gy = top + ph * i / 4
            p.setPen(grid)
            p.drawLine(QPointF(left, gy), QPointF(w - right, gy))
            val = y1 - (y1 - y0) * i / 4
            p.setPen(QColor(T("muted")))
            p.drawText(QRectF(0, gy - 8, left - 6, 16), int(ALIGN_RIGHT.value), f"{val:.1f}")
        step = max(1, int(round((x1 - x0) / 8.0)))
        x = int(x0)
        while x <= x1:
            p.drawText(QRectF(X(x) - 20, h - bottom + 6, 40, 16), int(ALIGN_CENTER.value), str(x))
            x += step
        for name, color, s in self.series:
            if not s:
                continue
            pen = QPen(QColor(color))
            pen.setWidth(2)
            p.setPen(pen)
            path = QPainterPath()
            path.moveTo(QPointF(X(s[0][0]), Y(s[0][1])))
            for sx, sy in s[1:]:
                path.lineTo(QPointF(X(sx), Y(sy)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setBrush(QBrush(QColor(color)))
            for sx, sy in s:
                p.drawEllipse(QPointF(X(sx), Y(sy)), 2.5, 2.5)
        p.end()


class MeterBar(QWidget):
    """Horizontal comparison meter (e.g. trade value: give vs get)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.left = 0.0
        self.right = 0.0
        self.setMinimumHeight(16)

    def set_values(self, left, right):
        self.left, self.right = max(0.0, left), max(0.0, right)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        tot = self.left + self.right
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(T("border_soft"))))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        if tot > 0:
            lw = w * self.left / tot
            p.setBrush(QBrush(QColor(accent())))
            p.drawRoundedRect(QRectF(0, 0, lw, h), h / 2, h / 2)
            p.setBrush(QBrush(QColor(T("info"))))
            p.drawRoundedRect(QRectF(lw, 0, w - lw, h), h / 2, h / 2)
        p.end()


def screen_header(title, subtitle=""):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 4)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("h1")
    lay.addWidget(t)
    s = QLabel(subtitle)
    s.setObjectName("sub")
    lay.addWidget(s)
    w.title_label = t
    w.sub_label = s
    return w


def filter_chips(options, on_change, initial=None):
    """A row of mutually exclusive chip buttons. Returns (widget, getter)."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    buttons = []
    state = {"value": initial if initial is not None else options[0][0]}

    def pick(value):
        state["value"] = value
        for b, v in buttons:
            b.setChecked(v == value)
        on_change(value)

    for value, label in options:
        b = QPushButton(label)
        b.setObjectName("chipbtn")
        b.setCheckable(True)
        b.setChecked(value == state["value"])
        b.clicked.connect(lambda _checked=False, v=value: pick(v))
        lay.addWidget(b)
        buttons.append((b, value))
    lay.addStretch(1)
    return w, (lambda: state["value"])


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            break
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        else:
            child = item.layout()
            if child is not None:
                clear_layout(child)
