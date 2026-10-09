"""Stateful behaviour for commonly used classes in the strict PyQt6 fake."""
import functools

from . import _core
from ._core import IMPLS, CTORS, STATIC_IMPLS, CLASSES, FakeTypeError

CONFIG = {"dialog_result": 0, "question_answer": "Yes", "input_text": ("Test", True)}
APP = {}


def impl(key, name=None):
    def deco(fn):
        IMPLS.setdefault(key, {})[name or fn.__name__] = fn
        return fn
    return deco


def ctor(key):
    def deco(fn):
        CTORS[key] = fn
        return fn
    return deco


def st(self):
    return self.__dict__.setdefault("_st", {})


def C(name):
    return CLASSES[name]


def enum(path):
    mod, rest = path.split(".", 1)
    obj = None
    parts = rest.split(".")
    obj = CLASSES[f"{mod}.{'.'.join(parts[:-1])}"]
    return getattr(obj, parts[-1])


# ── QObject / QWidget ─────────────────────────────────────────────────────────

@impl("QtCore.QObject")
def setObjectName(self, name):
    st(self)["objname"] = name


@impl("QtCore.QObject")
def objectName(self):
    return st(self).get("objname", "")


@impl("QtCore.QObject")
def setProperty(self, name, value):
    st(self).setdefault("props", {})[name] = value
    return True


@impl("QtCore.QObject")
def property(self, name):
    return st(self).get("props", {}).get(name)


@impl("QtCore.QObject")
def deleteLater(self):
    st(self)["deleted"] = True


@impl("QtCore.QObject")
def parent(self):
    return st(self).get("parent")


@ctor("QtWidgets.QWidget")
def _w_ctor(self, *args, **kw):
    s = st(self)
    s.setdefault("visible", True)
    s.setdefault("enabled", True)
    for a in args:
        if isinstance(a, C("QtWidgets.QWidget")):
            s["parent"] = a
    if "parent" in kw:
        s["parent"] = kw["parent"]


for _n, _f in {
    "setVisible": lambda self, v: st(self).__setitem__("visible", bool(v)),
    "isVisible": lambda self: st(self).get("visible", True),
    "isHidden": lambda self: not st(self).get("visible", True),
    "show": lambda self: st(self).__setitem__("visible", True),
    "hide": lambda self: st(self).__setitem__("visible", False),
    "setEnabled": lambda self, v: st(self).__setitem__("enabled", bool(v)),
    "isEnabled": lambda self: st(self).get("enabled", True),
    "setToolTip": lambda self, t: st(self).__setitem__("tooltip", t),
    "toolTip": lambda self: st(self).get("tooltip", ""),
    "setStyleSheet": lambda self, s: st(self).__setitem__("qss", s),
    "styleSheet": lambda self: st(self).get("qss", ""),
    "setWindowTitle": lambda self, t: st(self).__setitem__("title", t),
    "windowTitle": lambda self: st(self).get("title", ""),
    "width": lambda self: st(self).get("w", 900),
    "height": lambda self: st(self).get("h", 600),
    "close": lambda self: True,
    "setParent": lambda self, *a: st(self).__setitem__("parent", a[0] if a else None),
}.items():
    IMPLS.setdefault("QtWidgets.QWidget", {})[_n] = _f


@impl("QtWidgets.QWidget")
def setLayout(self, layout):
    st(self)["layout"] = layout


@impl("QtWidgets.QWidget")
def layout(self):
    return st(self).get("layout")


@impl("QtWidgets.QWidget")
def rect(self):
    return C("QtCore.QRect")(0, 0, self.width(), self.height())


@impl("QtWidgets.QWidget")
def size(self):
    return C("QtCore.QSize")(self.width(), self.height())


@impl("QtWidgets.QWidget")
def resize(self, *a):
    if len(a) == 2:
        st(self)["w"], st(self)["h"] = a


@impl("QtWidgets.QWidget")
def font(self):
    return C("QtGui.QFont")()


@impl("QtWidgets.QWidget")
def fontMetrics(self):
    return C("QtGui.QFontMetrics")(C("QtGui.QFont")())


@impl("QtWidgets.QWidget")
def palette(self):
    return C("QtGui.QPalette")()


# ── Layouts ───────────────────────────────────────────────────────────────────

def _items(self):
    return st(self).setdefault("items", [])


def _wrap(w):
    it = C("QtWidgets.QWidgetItem")._fake_new()
    st(it)["widget"] = w
    return it


@impl("QtWidgets.QLayout")
def addWidget(self, w, *a, **k):
    _items(self).append(_wrap(w))


@impl("QtWidgets.QLayout")
def addItem(self, item):
    _items(self).append(item)


@impl("QtWidgets.QLayout")
def count(self):
    return len(_items(self))


@impl("QtWidgets.QLayout")
def itemAt(self, i):
    items = _items(self)
    return items[i] if 0 <= i < len(items) else None


@impl("QtWidgets.QLayout")
def takeAt(self, i):
    items = _items(self)
    return items.pop(i) if 0 <= i < len(items) else None


for _cls in ("QtWidgets.QBoxLayout", "QtWidgets.QGridLayout", "QtWidgets.QFormLayout"):
    IMPLS.setdefault(_cls, {})["addWidget"] = addWidget
    IMPLS.setdefault(_cls, {})["count"] = count
    IMPLS.setdefault(_cls, {})["itemAt"] = itemAt
    IMPLS.setdefault(_cls, {})["takeAt"] = takeAt


@impl("QtWidgets.QBoxLayout")
def addLayout(self, layout, *a):
    it = C("QtWidgets.QWidgetItem")._fake_new()
    st(it)["layout"] = layout
    _items(self).append(it)


@impl("QtWidgets.QBoxLayout")
def addStretch(self, *a):
    _items(self).append(C("QtWidgets.QSpacerItem")._fake_new())


@impl("QtWidgets.QBoxLayout")
def addSpacing(self, *a):
    _items(self).append(C("QtWidgets.QSpacerItem")._fake_new())


@impl("QtWidgets.QBoxLayout")
def insertWidget(self, index, w, *a, **k):
    items = _items(self)
    if index < 0:
        index = len(items)
    items.insert(index, _wrap(w))


@impl("QtWidgets.QGridLayout")
def addLayout(self, layout, *a):
    it = C("QtWidgets.QWidgetItem")._fake_new()
    st(it)["layout"] = layout
    _items(self).append(it)


@impl("QtWidgets.QFormLayout")
def addRow(self, *a):
    for x in a:
        if isinstance(x, C("QtWidgets.QWidget")):
            _items(self).append(_wrap(x))


@impl("QtWidgets.QLayoutItem")
def widget(self):
    return st(self).get("widget")


@impl("QtWidgets.QLayoutItem")
def layout(self):
    return st(self).get("layout")


IMPLS.setdefault("QtWidgets.QWidgetItem", {})["widget"] = widget
IMPLS.setdefault("QtWidgets.QSpacerItem", {})["widget"] = lambda self: None
IMPLS.setdefault("QtWidgets.QSpacerItem", {})["layout"] = lambda self: None

# ── Labels, buttons, text inputs ──────────────────────────────────────────────


def _text_ctor(self, *args, **kw):
    _w_ctor(self, *args, **kw)
    for a in args:
        if isinstance(a, str):
            st(self)["text"] = a
            break
    if "text" in kw:
        st(self)["text"] = kw["text"]


for _cls in ("QtWidgets.QLabel", "QtWidgets.QPushButton", "QtWidgets.QCheckBox",
             "QtWidgets.QRadioButton", "QtWidgets.QToolButton", "QtWidgets.QLineEdit",
             "QtWidgets.QGroupBox"):
    CTORS[_cls] = _text_ctor
for _cls in ("QtWidgets.QWidget", "QtWidgets.QFrame", "QtWidgets.QDialog", "QtWidgets.QMainWindow",
             "QtWidgets.QTableWidget", "QtWidgets.QListWidget", "QtWidgets.QComboBox",
             "QtWidgets.QStackedWidget", "QtWidgets.QTabWidget", "QtWidgets.QScrollArea",
             "QtWidgets.QSpinBox", "QtWidgets.QDoubleSpinBox", "QtWidgets.QSlider",
             "QtWidgets.QProgressBar", "QtWidgets.QTextBrowser", "QtWidgets.QTextEdit",
             "QtWidgets.QPlainTextEdit", "QtWidgets.QSplitter"):
    CTORS.setdefault(_cls, _w_ctor)


def _set_text(self, t):
    st(self)["text"] = t


def _get_text(self):
    return st(self).get("text", "")


for _cls in ("QtWidgets.QLabel", "QtWidgets.QAbstractButton"):
    IMPLS.setdefault(_cls, {})["setText"] = _set_text
    IMPLS.setdefault(_cls, {})["text"] = _get_text


@impl("QtWidgets.QGroupBox")
def setTitle(self, t):
    st(self)["text"] = t


@impl("QtWidgets.QGroupBox")
def title(self):
    return st(self).get("text", "")


@impl("QtWidgets.QAbstractButton")
def setCheckable(self, v):
    st(self)["checkable"] = bool(v)


@impl("QtWidgets.QAbstractButton")
def isCheckable(self):
    return st(self).get("checkable", isinstance(self, (C("QtWidgets.QCheckBox"), C("QtWidgets.QRadioButton"))))


@impl("QtWidgets.QAbstractButton")
def setChecked(self, v):
    old = st(self).get("checked", False)
    st(self)["checked"] = bool(v)
    if old != bool(v):
        self.toggled.emit(bool(v))
        if isinstance(self, C("QtWidgets.QCheckBox")):
            self.stateChanged.emit(2 if v else 0)


@impl("QtWidgets.QAbstractButton")
def isChecked(self):
    return st(self).get("checked", False)


@impl("QtWidgets.QAbstractButton")
def click(self):
    if not st(self).get("enabled", True):
        return
    if self.isCheckable():
        self.setChecked(not self.isChecked())
    self.clicked.emit(self.isChecked())


@impl("QtWidgets.QLineEdit")
def setText(self, t):
    st(self)["text"] = t
    self.textChanged.emit(t)


@impl("QtWidgets.QLineEdit")
def text(self):
    return st(self).get("text", "")


@impl("QtWidgets.QLineEdit")
def clear(self):
    self.setText("")


for _cls in ("QtWidgets.QTextEdit", "QtWidgets.QPlainTextEdit"):
    IMPLS.setdefault(_cls, {}).update({
        "setHtml": lambda self, t: st(self).__setitem__("text", t),
        "setPlainText": lambda self, t: st(self).__setitem__("text", t),
        "toPlainText": lambda self: st(self).get("text", ""),
        "toHtml": lambda self: st(self).get("text", ""),
        "append": lambda self, t: st(self).__setitem__("text", st(self).get("text", "") + "\n" + t),
        "clear": lambda self: st(self).__setitem__("text", ""),
        "appendPlainText": lambda self, t: st(self).__setitem__("text", st(self).get("text", "") + "\n" + t),
    })

# ── Combo box ─────────────────────────────────────────────────────────────────


def _cb(self):
    s = st(self)
    s.setdefault("items", [])
    s.setdefault("cur", -1)
    return s


@impl("QtWidgets.QComboBox")
def addItem(self, *a):
    s = _cb(self)
    if a and isinstance(a[0], str):
        text, data = a[0], (a[1] if len(a) > 1 else None)
    else:
        text, data = a[1], (a[2] if len(a) > 2 else None)
    s["items"].append([text, data])
    if s["cur"] == -1:
        s["cur"] = 0
        self.currentIndexChanged.emit(0)
        self.currentTextChanged.emit(text)


@impl("QtWidgets.QComboBox")
def addItems(self, texts):
    for t in texts:
        self.addItem(t)


@impl("QtWidgets.QComboBox")
def count(self):
    return len(_cb(self)["items"])


@impl("QtWidgets.QComboBox")
def currentIndex(self):
    return _cb(self)["cur"]


@impl("QtWidgets.QComboBox")
def setCurrentIndex(self, i):
    s = _cb(self)
    if not (-1 <= i < len(s["items"])):
        return
    if s["cur"] != i:
        s["cur"] = i
        self.currentIndexChanged.emit(i)
        self.currentTextChanged.emit(s["items"][i][0] if i >= 0 else "")


@impl("QtWidgets.QComboBox")
def currentText(self):
    s = _cb(self)
    return s["items"][s["cur"]][0] if s["cur"] >= 0 else ""


@impl("QtWidgets.QComboBox")
def setCurrentText(self, t):
    s = _cb(self)
    for i, (txt, _) in enumerate(s["items"]):
        if txt == t:
            self.setCurrentIndex(i)
            return


@impl("QtWidgets.QComboBox")
def itemText(self, i):
    s = _cb(self)
    return s["items"][i][0] if 0 <= i < len(s["items"]) else ""


@impl("QtWidgets.QComboBox")
def itemData(self, i, role=None):
    s = _cb(self)
    return s["items"][i][1] if 0 <= i < len(s["items"]) else None


@impl("QtWidgets.QComboBox")
def currentData(self, role=None):
    s = _cb(self)
    return s["items"][s["cur"]][1] if s["cur"] >= 0 else None


@impl("QtWidgets.QComboBox")
def findText(self, t, *a):
    for i, (txt, _) in enumerate(_cb(self)["items"]):
        if txt == t:
            return i
    return -1


@impl("QtWidgets.QComboBox")
def findData(self, d, *a):
    for i, (_, dd) in enumerate(_cb(self)["items"]):
        if dd == d:
            return i
    return -1


@impl("QtWidgets.QComboBox")
def clear(self):
    s = _cb(self)
    s["items"] = []
    if s["cur"] != -1:
        s["cur"] = -1
        self.currentIndexChanged.emit(-1)
        self.currentTextChanged.emit("")


# ── Spin boxes / sliders / progress ───────────────────────────────────────────

def _range_impls(key, value_type):
    def _s(self):
        s = st(self)
        s.setdefault("min", 0)
        s.setdefault("max", 99 if value_type is int else 99.99)
        s.setdefault("val", s["min"])
        return s

    def setRange(self, lo, hi):
        s = _s(self)
        s["min"], s["max"] = lo, hi
        setValue(self, s["val"])

    def setMinimum(self, v):
        _s(self)["min"] = v

    def setMaximum(self, v):
        _s(self)["max"] = v

    def minimum(self):
        return _s(self)["min"]

    def maximum(self):
        return _s(self)["max"]

    def value(self):
        return _s(self)["val"]

    def setValue(self, v):
        s = _s(self)
        v = max(s["min"], min(s["max"], v))
        if value_type is int:
            v = int(v)
        if s["val"] != v:
            s["val"] = v
            sig = getattr(self, "valueChanged", None)
            if sig is not None:
                sig.emit(v)
        else:
            s["val"] = v

    d = IMPLS.setdefault(key, {})
    d.update({"setRange": setRange, "setMinimum": setMinimum, "setMaximum": setMaximum,
              "minimum": minimum, "maximum": maximum, "value": value, "setValue": setValue})


_range_impls("QtWidgets.QSpinBox", int)
_range_impls("QtWidgets.QDoubleSpinBox", float)
_range_impls("QtWidgets.QAbstractSlider", int)
_range_impls("QtWidgets.QProgressBar", int)

# ── Item widgets ──────────────────────────────────────────────────────────────


@ctor("QtWidgets.QTableWidgetItem")
def _twi_ctor(self, *args, **kw):
    s = st(self)
    s["data"] = {}
    for a in args:
        if isinstance(a, str):
            s["data"][0] = a


@ctor("QtWidgets.QListWidgetItem")
def _lwi_ctor(self, *args, **kw):
    s = st(self)
    s["data"] = {}
    for a in args:
        if isinstance(a, str):
            s["data"][0] = a
        elif isinstance(a, C("QtWidgets.QListWidget")):
            a.addItem(self)


def _role_key(role):
    return role.value if hasattr(role, "value") else role


for _cls in ("QtWidgets.QTableWidgetItem", "QtWidgets.QListWidgetItem"):
    IMPLS.setdefault(_cls, {}).update({
        "text": lambda self: st(self).setdefault("data", {}).get(0, ""),
        "setText": lambda self, t: st(self).setdefault("data", {}).__setitem__(0, t),
        "data": lambda self, role: st(self).setdefault("data", {}).get(_role_key(role)),
        "setData": lambda self, role, v: st(self).setdefault("data", {}).__setitem__(_role_key(role), v),
        "setToolTip": lambda self, t: st(self).setdefault("data", {}).__setitem__(3, t),
        "toolTip": lambda self: st(self).setdefault("data", {}).get(3, ""),
        "row": lambda self: st(self).get("pos", (-1, -1))[0],
        "column": lambda self: st(self).get("pos", (-1, -1))[1],
        "tableWidget": lambda self: st(self).get("table"),
        "listWidget": lambda self: st(self).get("list"),
    })


def _tw(self):
    s = st(self)
    s.setdefault("rows", 0)
    s.setdefault("cols", 0)
    s.setdefault("cells", {})
    s.setdefault("widgets", {})
    s.setdefault("cur", -1)
    s.setdefault("headers", [])
    return s


@ctor("QtWidgets.QTableWidget")
def _tw_ctor(self, *args, **kw):
    _w_ctor(self, *args, **kw)
    s = _tw(self)
    ints = [a for a in args if isinstance(a, int)]
    if len(ints) == 2:
        s["rows"], s["cols"] = ints


@impl("QtWidgets.QTableWidget")
def setRowCount(self, n):
    s = _tw(self)
    s["rows"] = n
    s["cells"] = {k: v for k, v in s["cells"].items() if k[0] < n}
    s["widgets"] = {k: v for k, v in s["widgets"].items() if k[0] < n}
    if s["cur"] >= n:
        s["cur"] = -1


@impl("QtWidgets.QTableWidget")
def rowCount(self):
    return _tw(self)["rows"]


@impl("QtWidgets.QTableWidget")
def setColumnCount(self, n):
    _tw(self)["cols"] = n


@impl("QtWidgets.QTableWidget")
def columnCount(self):
    return _tw(self)["cols"]


@impl("QtWidgets.QTableWidget")
def setHorizontalHeaderLabels(self, labels):
    _tw(self)["headers"] = list(labels)
    _tw(self)["header_items"] = [C("QtWidgets.QTableWidgetItem")(str(t)) for t in labels]


@impl("QtWidgets.QTableWidget")
def horizontalHeaderItem(self, c):
    items = _tw(self).get("header_items", [])
    return items[c] if 0 <= c < len(items) else None


@impl("QtWidgets.QTableWidget")
def setItem(self, r, c, item):
    s = _tw(self)
    if st(self).get("sorting"):
        raise FakeTypeError("QTableWidget.setItem() called while sorting is enabled — rows "
                            "will be reshuffled mid-fill in real Qt. Disable sorting first.")
    if not (0 <= r < s["rows"] and 0 <= c < s["cols"]):
        return
    s["cells"][(r, c)] = item
    st(item)["pos"] = (r, c)
    st(item)["table"] = self


@impl("QtWidgets.QTableWidget")
def item(self, r, c):
    return _tw(self)["cells"].get((r, c))


@impl("QtWidgets.QTableWidget")
def takeItem(self, r, c):
    return _tw(self)["cells"].pop((r, c), None)


@impl("QtWidgets.QTableWidget")
def setCellWidget(self, r, c, w):
    _tw(self)["widgets"][(r, c)] = w


@impl("QtWidgets.QTableWidget")
def cellWidget(self, r, c):
    return _tw(self)["widgets"].get((r, c))


@impl("QtWidgets.QTableWidget")
def clearContents(self):
    s = _tw(self)
    s["cells"] = {}
    s["widgets"] = {}


@impl("QtWidgets.QTableWidget")
def clear(self):
    clearContents(self)


@impl("QtWidgets.QTableWidget")
def currentRow(self):
    return _tw(self)["cur"]


@impl("QtWidgets.QTableWidget")
def setCurrentCell(self, r, c, *a):
    _tw(self)["cur"] = r
    self.itemSelectionChanged.emit()


@impl("QtWidgets.QTableView")
def selectRow(self, r):
    if isinstance(self, C("QtWidgets.QTableWidget")):
        _tw(self)["cur"] = r
        self.itemSelectionChanged.emit()


@impl("QtWidgets.QTableWidget")
def currentItem(self):
    s = _tw(self)
    return s["cells"].get((s["cur"], 0))


@impl("QtWidgets.QTableWidget")
def selectedItems(self):
    s = _tw(self)
    return [v for (r, c), v in sorted(s["cells"].items()) if r == s["cur"]]


@impl("QtWidgets.QTableView")
def setSortingEnabled(self, v):
    st(self)["sorting"] = bool(v)


@impl("QtWidgets.QTableView")
def isSortingEnabled(self):
    return st(self).get("sorting", False)


@impl("QtWidgets.QTableWidget")
def sortItems(self, col, order=None):
    s = _tw(self)
    rows = []
    for r in range(s["rows"]):
        rows.append(({c: s["cells"].get((r, c)) for c in range(s["cols"])},
                     {c: s["widgets"].get((r, c)) for c in range(s["cols"])}))

    def cmp(a, b):
        ia, ib = a[0].get(col), b[0].get(col)
        if ia is None or ib is None:
            return 0
        if ia < ib:
            return -1
        if ib < ia:
            return 1
        return 0
    rows.sort(key=functools.cmp_to_key(cmp))
    desc = order is not None and getattr(order, "name", "") == "DescendingOrder"
    if desc:
        rows.reverse()
    s["cells"], s["widgets"] = {}, {}
    for r, (cells, widgets) in enumerate(rows):
        for c, it in cells.items():
            if it is not None:
                s["cells"][(r, c)] = it
                st(it)["pos"] = (r, c)
        for c, w in widgets.items():
            if w is not None:
                s["widgets"][(r, c)] = w


@impl("QtWidgets.QTableWidget")
def insertRow(self, r):
    s = _tw(self)
    s["cells"] = {((k[0] + 1) if k[0] >= r else k[0], k[1]): v for k, v in s["cells"].items()}
    s["rows"] += 1


@impl("QtWidgets.QTableWidget")
def removeRow(self, r):
    s = _tw(self)
    s["cells"] = {((k[0] - 1) if k[0] > r else k[0], k[1]): v for k, v in s["cells"].items()
                  if k[0] != r}
    s["rows"] = max(0, s["rows"] - 1)


def _header(self, key):
    s = st(self)
    if key not in s:
        s[key] = C("QtWidgets.QHeaderView")._fake_new()
    return s[key]


IMPLS.setdefault("QtWidgets.QTableView", {})["horizontalHeader"] = lambda self: _header(self, "hh")
IMPLS.setdefault("QtWidgets.QTableView", {})["verticalHeader"] = lambda self: _header(self, "vh")


def _lw(self):
    s = st(self)
    s.setdefault("items", [])
    s.setdefault("cur", -1)
    return s


@impl("QtWidgets.QListWidget")
def addItem(self, item):
    if isinstance(item, str):
        it = C("QtWidgets.QListWidgetItem")(item)
    else:
        it = item
    st(it)["list"] = self
    _lw(self)["items"].append(it)


@impl("QtWidgets.QListWidget")
def addItems(self, labels):
    for l in labels:
        self.addItem(l)


@impl("QtWidgets.QListWidget")
def insertItem(self, row, item):
    it = C("QtWidgets.QListWidgetItem")(item) if isinstance(item, str) else item
    st(it)["list"] = self
    _lw(self)["items"].insert(row, it)


@impl("QtWidgets.QListWidget")
def count(self):
    return len(_lw(self)["items"])


@impl("QtWidgets.QListWidget")
def item(self, i):
    items = _lw(self)["items"]
    return items[i] if 0 <= i < len(items) else None


@impl("QtWidgets.QListWidget")
def takeItem(self, i):
    items = _lw(self)["items"]
    return items.pop(i) if 0 <= i < len(items) else None


@impl("QtWidgets.QListWidget")
def row(self, item):
    items = _lw(self)["items"]
    return items.index(item) if item in items else -1


@impl("QtWidgets.QListWidget")
def clear(self):
    s = _lw(self)
    s["items"] = []
    s["cur"] = -1


@impl("QtWidgets.QListWidget")
def currentRow(self):
    return _lw(self)["cur"]


@impl("QtWidgets.QListWidget")
def setCurrentRow(self, r, *a):
    s = _lw(self)
    if s["cur"] != r:
        s["cur"] = r
        self.currentRowChanged.emit(r)
        it = self.item(r)
        self.currentItemChanged.emit(it, None)


@impl("QtWidgets.QListWidget")
def currentItem(self):
    s = _lw(self)
    return self.item(s["cur"])


@impl("QtWidgets.QListWidget")
def selectedItems(self):
    it = currentItem(self)
    return [it] if it else []


# ── Containers ────────────────────────────────────────────────────────────────

def _sw(self):
    s = st(self)
    s.setdefault("pages", [])
    s.setdefault("cur", -1)
    return s


@impl("QtWidgets.QStackedWidget")
def addWidget(self, w):
    s = _sw(self)
    s["pages"].append(w)
    if s["cur"] == -1:
        s["cur"] = 0
    return len(s["pages"]) - 1


@impl("QtWidgets.QStackedWidget")
def setCurrentWidget(self, w):
    s = _sw(self)
    if w not in s["pages"]:
        raise FakeTypeError("setCurrentWidget: widget is not in the stack")
    s["cur"] = s["pages"].index(w)
    self.currentChanged.emit(s["cur"])


@impl("QtWidgets.QStackedWidget")
def currentWidget(self):
    s = _sw(self)
    return s["pages"][s["cur"]] if s["cur"] >= 0 else None


@impl("QtWidgets.QStackedWidget")
def setCurrentIndex(self, i):
    _sw(self)["cur"] = i
    self.currentChanged.emit(i)


@impl("QtWidgets.QStackedWidget")
def currentIndex(self):
    return _sw(self)["cur"]


@impl("QtWidgets.QStackedWidget")
def count(self):
    return len(_sw(self)["pages"])


@impl("QtWidgets.QStackedWidget")
def widget(self, i):
    p = _sw(self)["pages"]
    return p[i] if 0 <= i < len(p) else None


@impl("QtWidgets.QStackedWidget")
def indexOf(self, w):
    p = _sw(self)["pages"]
    return p.index(w) if w in p else -1


def _tabs(self):
    s = st(self)
    s.setdefault("tabs", [])
    s.setdefault("cur", -1)
    return s


@impl("QtWidgets.QTabWidget")
def addTab(self, w, *a):
    s = _tabs(self)
    label = a[-1]
    s["tabs"].append([w, label])
    if s["cur"] == -1:
        s["cur"] = 0
    return len(s["tabs"]) - 1


@impl("QtWidgets.QTabWidget")
def count(self):
    return len(_tabs(self)["tabs"])


@impl("QtWidgets.QTabWidget")
def currentIndex(self):
    return _tabs(self)["cur"]


@impl("QtWidgets.QTabWidget")
def setCurrentIndex(self, i):
    s = _tabs(self)
    s["cur"] = i
    self.currentChanged.emit(i)


@impl("QtWidgets.QTabWidget")
def widget(self, i):
    t = _tabs(self)["tabs"]
    return t[i][0] if 0 <= i < len(t) else None


@impl("QtWidgets.QTabWidget")
def currentWidget(self):
    return self.widget(_tabs(self)["cur"])


@impl("QtWidgets.QTabWidget")
def tabText(self, i):
    t = _tabs(self)["tabs"]
    return t[i][1] if 0 <= i < len(t) else ""


@impl("QtWidgets.QTabWidget")
def clear(self):
    s = _tabs(self)
    s["tabs"] = []
    s["cur"] = -1


@impl("QtWidgets.QScrollArea")
def setWidget(self, w):
    st(self)["inner"] = w


@impl("QtWidgets.QScrollArea")
def widget(self):
    return st(self).get("inner")


# ── Dialogs & app ─────────────────────────────────────────────────────────────

@impl("QtWidgets.QDialog")
def exec(self):
    st(self)["executed"] = True
    hook = CONFIG.get("on_exec")
    if hook:
        res = hook(self)
        if res is not None:
            return res
    return st(self).get("result", CONFIG["dialog_result"])


@impl("QtWidgets.QDialog")
def accept(self):
    st(self)["result"] = 1
    self.accepted.emit()
    self.finished.emit(1)


@impl("QtWidgets.QDialog")
def reject(self):
    st(self)["result"] = 0
    self.rejected.emit()
    self.finished.emit(0)


@impl("QtWidgets.QDialog")
def done(self, r):
    st(self)["result"] = r


@impl("QtWidgets.QDialog")
def result(self):
    return st(self).get("result", 0)


def _mb_answer(*a, **k):
    name = CONFIG["question_answer"]
    return getattr(CLASSES["QtWidgets.QMessageBox.StandardButton"], name)


STATIC_IMPLS["QMessageBox.question"] = _mb_answer
STATIC_IMPLS["QMessageBox.information"] = lambda *a, **k: CLASSES["QtWidgets.QMessageBox.StandardButton"].Ok
STATIC_IMPLS["QMessageBox.warning"] = lambda *a, **k: CLASSES["QtWidgets.QMessageBox.StandardButton"].Ok
STATIC_IMPLS["QMessageBox.critical"] = lambda *a, **k: CLASSES["QtWidgets.QMessageBox.StandardButton"].Ok
STATIC_IMPLS["QInputDialog.getText"] = lambda *a, **k: CONFIG["input_text"]
STATIC_IMPLS["QFileDialog.getSaveFileName"] = lambda *a, **k: ("", "")
STATIC_IMPLS["QFileDialog.getOpenFileName"] = lambda *a, **k: ("", "")
STATIC_IMPLS["QApplication.instance"] = lambda: APP.get("app")
STATIC_IMPLS["QCoreApplication.instance"] = lambda: APP.get("app")


def _timer_single(*a, **k):
    fn = a[-1]
    if callable(fn):
        fn()


STATIC_IMPLS["QTimer.singleShot"] = _timer_single


@ctor("QtWidgets.QApplication")
def _app_ctor(self, *a, **k):
    APP["app"] = self


@impl("QtCore.QCoreApplication")
def exec(self):
    return 0


@impl("QtCore.QThread")
def start(self, *a):
    self.started.emit()
    self.run()
    self.finished.emit()


@impl("QtCore.QThread")
def isRunning(self):
    return False


@impl("QtCore.QThread")
def wait(self, *a):
    return True


# ── Geometry & painting value types ───────────────────────────────────────────

def _geo_ctor(self, *a, **k):
    s = st(self)
    nums = [x for x in a if isinstance(x, (int, float))]
    pts = [x for x in a if type(x).__name__ in ("QPoint", "QPointF")]
    sizes = [x for x in a if type(x).__name__ in ("QSize", "QSizeF")]
    if len(nums) == 4:
        s["x"], s["y"], s["w"], s["h"] = nums
    elif len(nums) == 2:
        s["x"], s["y"] = nums
        s["w"], s["h"] = nums
    elif len(pts) == 2:
        s["x"], s["y"] = pts[0].x(), pts[0].y()
        s["w"], s["h"] = pts[1].x() - pts[0].x(), pts[1].y() - pts[0].y()
    elif pts and sizes:
        s["x"], s["y"] = pts[0].x(), pts[0].y()
        s["w"], s["h"] = sizes[0].width(), sizes[0].height()
    elif a and type(a[0]).__name__ in ("QRect", "QRectF"):
        o = st(a[0])
        s.update({k2: o.get(k2, 0) for k2 in ("x", "y", "w", "h")})
    s.setdefault("x", 0)
    s.setdefault("y", 0)
    s.setdefault("w", 0)
    s.setdefault("h", 0)


for _cls in ("QtCore.QRect", "QtCore.QRectF", "QtCore.QPoint", "QtCore.QPointF",
             "QtCore.QSize", "QtCore.QSizeF"):
    CTORS[_cls] = _geo_ctor


def _g(self, k):
    s = st(self)
    if not s:
        _geo_ctor(self)
    return s.get(k, 0)


def _rect_impls(key, cast):
    F = "QtCore.QRectF" if key.endswith("F") else "QtCore.QRect"
    P = "QtCore.QPointF" if key.endswith("F") else "QtCore.QPoint"
    IMPLS.setdefault(key, {}).update({
        "x": lambda self: cast(_g(self, "x")), "y": lambda self: cast(_g(self, "y")),
        "left": lambda self: cast(_g(self, "x")), "top": lambda self: cast(_g(self, "y")),
        "width": lambda self: cast(_g(self, "w")), "height": lambda self: cast(_g(self, "h")),
        "right": lambda self: cast(_g(self, "x") + _g(self, "w") - (1 if cast is int else 0)),
        "bottom": lambda self: cast(_g(self, "y") + _g(self, "h") - (1 if cast is int else 0)),
        "center": lambda self: C(P)(cast(_g(self, "x") + _g(self, "w") / 2),
                                    cast(_g(self, "y") + _g(self, "h") / 2)),
        "adjusted": lambda self, a, b, c, d: C(F)(cast(_g(self, "x") + a), cast(_g(self, "y") + b),
                                                  cast(_g(self, "w") - a + c), cast(_g(self, "h") - b + d)),
        "topLeft": lambda self: C(P)(cast(_g(self, "x")), cast(_g(self, "y"))),
        "isEmpty": lambda self: _g(self, "w") <= 0 or _g(self, "h") <= 0,
    })


_rect_impls("QtCore.QRect", int)
_rect_impls("QtCore.QRectF", float)
for _key, _cast in (("QtCore.QPoint", int), ("QtCore.QPointF", float)):
    IMPLS.setdefault(_key, {}).update({"x": (lambda c: lambda self: c(_g(self, "x")))(_cast),
                                       "y": (lambda c: lambda self: c(_g(self, "y")))(_cast)})
for _key, _cast in (("QtCore.QSize", int), ("QtCore.QSizeF", float)):
    IMPLS.setdefault(_key, {}).update({"width": (lambda c: lambda self: c(_g(self, "x")))(_cast),
                                       "height": (lambda c: lambda self: c(_g(self, "y")))(_cast)})


@ctor("QtGui.QColor")
def _color_ctor(self, *a, **k):
    s = st(self)
    s["name"] = a[0] if a and isinstance(a[0], str) else "#000000"
    s["alpha"] = 255
    if len(a) >= 3 and all(isinstance(x, int) for x in a[:3]):
        s["name"] = "#%02x%02x%02x" % tuple(max(0, min(255, x)) for x in a[:3])
        if len(a) == 4:
            s["alpha"] = a[3]


def _hex(self):
    n = st(self).get("name", "#000000")
    if not (isinstance(n, str) and n.startswith("#") and len(n) == 7):
        return (0, 0, 0)
    return tuple(int(n[i:i + 2], 16) for i in (1, 3, 5))


IMPLS.setdefault("QtGui.QColor", {}).update({
    "name": lambda self, *a: st(self).get("name", "#000000"),
    "red": lambda self: _hex(self)[0], "green": lambda self: _hex(self)[1],
    "blue": lambda self: _hex(self)[2],
    "alpha": lambda self: st(self).get("alpha", 255),
    "setAlpha": lambda self, a: st(self).__setitem__("alpha", a),
    "lighter": lambda self, *a: C("QtGui.QColor")(st(self).get("name", "#000000")),
    "darker": lambda self, *a: C("QtGui.QColor")(st(self).get("name", "#000000")),
    "isValid": lambda self: True,
})

IMPLS.setdefault("QtGui.QFontMetrics", {}).update({
    "horizontalAdvance": lambda self, t, *a: 7 * len(t) if isinstance(t, str) else 7,
    "height": lambda self: 15, "ascent": lambda self: 12, "descent": lambda self: 3,
    "elidedText": lambda self, t, *a: t,
})
IMPLS.setdefault("QtGui.QFont", {}).update({
    "pointSize": lambda self: st(self).get("pt", 10),
    "setPointSize": lambda self, v: st(self).__setitem__("pt", v),
    "pointSizeF": lambda self: float(st(self).get("pt", 10)),
})
