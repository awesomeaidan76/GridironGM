"""
Strict headless stand-in for PyQt6, generated from the official PyQt6 stubs.

* Every class, method, enum member and module attribute must exist in the
  real PyQt6 API, otherwise AttributeError is raised.
* Every call is checked against the stub overloads (argument count, keyword
  names, and types: str/int/float/bool, Qt classes and Qt enums). PyQt6 is
  strict about enums and ints-vs-floats, and so is this fake.
* Commonly used widgets keep real state (text, items, values, rows) and
  emit their signals, so UI code paths can be exercised in tests.
"""
import ast
import inspect
import json
import os

_REG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "registry.json")))
MODULES = {"QtCore": {}, "QtGui": {}, "QtWidgets": {}}
CLASSES = {}          # "QtCore.QObject" -> class ; "QtCore.Qt.AlignmentFlag" -> enum class
CALL_LOG = []
STRICT_ERRORS = []


class FakeTypeError(TypeError):
    pass


# ── Enums ─────────────────────────────────────────────────────────────────────

class FakeEnum:
    _members = {}
    _kind = "Enum"

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __or__(self, other):
        if not self._is_flag():
            raise FakeTypeError(f"unsupported | for enum {type(self).__qualname__}")
        ov = other.value if isinstance(other, FakeEnum) else int(other)
        return type(self)(f"{self.name}|{getattr(other, 'name', other)}", self.value | ov)

    __ror__ = __or__

    def __and__(self, other):
        ov = other.value if isinstance(other, FakeEnum) else int(other)
        return type(self)(f"{self.name}&", self.value & ov)

    def __invert__(self):
        return type(self)(f"~{self.name}", ~self.value)

    def __bool__(self):
        return bool(self.value)

    def __int__(self):
        if self._kind in ("IntEnum", "IntFlag"):
            return self.value
        raise FakeTypeError(f"int() of non-int enum {type(self).__qualname__}")

    def __index__(self):
        return int(self)

    def __eq__(self, other):
        if isinstance(other, FakeEnum):
            return type(other) is type(self) and other.value == self.value
        if isinstance(other, int) and self._kind in ("IntEnum", "IntFlag"):
            return self.value == other
        return False

    def __hash__(self):
        return hash((type(self).__qualname__, self.value))

    def __repr__(self):
        return f"<{type(self).__qualname__}.{self.name}: {self.value}>"

    @classmethod
    def _is_flag(cls):
        return cls._kind in ("Flag", "IntFlag")


SPECIAL_VALUES = {
    "QtWidgets.QDialog.DialogCode": {"Rejected": 0, "Accepted": 1},
    "QtCore.Qt.ItemDataRole": {"DisplayRole": 0, "DecorationRole": 1, "EditRole": 2,
                               "ToolTipRole": 3, "UserRole": 256},
}


def make_enum(qualname, info):
    kind = info["enum"] or "Enum"
    cls = type(qualname.split(".")[-1], (FakeEnum,), {"_kind": kind})
    cls.__qualname__ = qualname.split(".", 1)[1] if "." in qualname else qualname
    members = {}
    special = SPECIAL_VALUES.get(qualname, {})
    for i, m in enumerate(info["members"]):
        if m in special:
            v = special[m]
        elif kind in ("Flag", "IntFlag"):
            v = 1 << (i % 62)
        else:
            v = i + (1000 if special else 0)
        inst = cls(m, v)
        members[m] = inst
        setattr(cls, m, inst)
    cls._members = members
    return cls


# ── Annotation checking ───────────────────────────────────────────────────────

_CHECK_CACHE = {}
ANY_NAMES = {"typing.Any", "object", "PYQT_SLOT", "PYQT_SIGNAL", "T", "QObjectT", "FuncT",
             "sip.voidptr", "sip.array", "sip.simplewrapper", "sip.wrapper", "PyQt6.sip.array",
             "QtCore.PYQT_SLOT", "QtCore.PYQT_SIGNAL"}


def _resolve(name, module):
    name = name.strip('"').strip("'")
    for cand in (name, f"{module}.{name}"):
        if cand in CLASSES:
            return CLASSES[cand]
    for m in MODULES:
        if f"{m}.{name}" in CLASSES:
            return CLASSES[f"{m}.{name}"]
    return None


def _checker(node, module):
    if node is None:
        return lambda v: True
    if isinstance(node, ast.Constant):
        if node.value is None:
            return lambda v: v is None
        if isinstance(node.value, str):
            try:
                return _checker(ast.parse(node.value, mode="eval").body, module)
            except SyntaxError:
                return lambda v: True
        return lambda v: True
    text = ast.unparse(node)
    if text in ANY_NAMES or text.startswith(("typing.Callable", "typing.Iterable", "typing.List",
                                              "typing.Sequence", "typing.Tuple", "typing.Dict",
                                              "typing.Type", "typing.Mapping", "typing.Collection",
                                              "typing.Iterator", "typing.Generator", "typing.Set")):
        if text.startswith(("typing.Iterable", "typing.List", "typing.Sequence")):
            return lambda v: hasattr(v, "__iter__") and not isinstance(v, str) or isinstance(v, str) and "str" in text
        return lambda v: True
    if isinstance(node, ast.Subscript):
        base = ast.unparse(node.value)
        if base == "typing.Optional":
            inner = _checker(node.slice, module)
            return lambda v: v is None or inner(v)
        if base == "typing.Union":
            elts = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            cs = [_checker(e, module) for e in elts]
            return lambda v: any(c(v) for c in cs)
        return lambda v: True
    if text == "str":
        return lambda v: isinstance(v, str)
    if text == "int":
        return lambda v: isinstance(v, int) or (isinstance(v, FakeEnum) and v._kind in ("IntEnum", "IntFlag"))
    if text == "float":
        return lambda v: isinstance(v, (int, float)) or (isinstance(v, FakeEnum) and v._kind in ("IntEnum", "IntFlag"))
    if text == "bool":
        return lambda v: isinstance(v, (bool, int)) and not isinstance(v, FakeEnum)
    if text == "None":
        return lambda v: v is None
    if text in ("bytes", "bytearray"):
        return lambda v: isinstance(v, (bytes, bytearray, str))
    holder = {}

    def check(v):
        if "cls" not in holder:
            holder["cls"] = _resolve(text, module)
        cls = holder["cls"]
        if cls is None:
            return True
        if isinstance(v, cls):
            return True
        # PyQt6 implicit conversions the stubs don't spell out
        if cls.__name__ == "QVariant" or text.endswith("QVariant"):
            return True
        if cls.__name__ in ("QKeySequence",) and isinstance(v, str):
            return True
        if cls.__name__ == "QIcon" and type(v).__name__ == "QPixmap":
            return True
        return False
    return check


def checker_for(text, module):
    key = (text, module)
    if key not in _CHECK_CACHE:
        if text is None:
            _CHECK_CACHE[key] = lambda v: True
        else:
            try:
                node = ast.parse(text, mode="eval").body
            except SyntaxError:
                node = None
            _CHECK_CACHE[key] = _checker(node, module)
    return _CHECK_CACHE[key]


def _match(ov, args, kwargs, module):
    params = ov["params"]
    pos_params = [p for p in params if p[3] == "pos"]
    var = any(p[3] == "var" for p in params)
    varkw = any(p[3] == "varkw" for p in params)
    if len(args) > len(pos_params) and not var:
        return False
    supplied = set()
    for i, v in enumerate(args):
        if i < len(pos_params):
            p = pos_params[i]
            if not checker_for(p[1], module)(v):
                return False
            supplied.add(p[0])
    names = {p[0]: p for p in params if p[3] in ("pos", "kwonly")}
    for k, v in kwargs.items():
        if k in names:
            if k in supplied:
                return False
            if not checker_for(names[k][1], module)(v):
                return False
            supplied.add(k)
        elif not varkw:
            return False
    for p in params:
        if p[3] in ("pos", "kwonly") and not p[2] and p[0] not in supplied:
            return False
    return True


def _describe(args, kwargs):
    def d(v):
        if isinstance(v, FakeEnum):
            return type(v).__qualname__
        return type(v).__name__
    s = ", ".join(d(a) for a in args)
    if kwargs:
        s += ", " + ", ".join(f"{k}={d(v)}" for k, v in kwargs.items())
    return s


# sip accepts None for these pointer arguments even though the stubs omit Optional
_NONE_OK = {("setParent", 0)}


def validate(module, owner, meth, overloads, args, kwargs):
    if meth == "setParent" and args and args[0] is None and not kwargs:
        return overloads[0]
    for ov in overloads:
        if _match(ov, args, kwargs, module):
            return ov
    sigs = "\n    ".join(", ".join(f"{p[0]}: {p[1]}" for p in ov["params"]) for ov in overloads)
    err = FakeTypeError(f"{owner}.{meth}({_describe(args, kwargs)}) matches no overload:\n    {sigs}")
    STRICT_ERRORS.append(str(err))
    raise err


def default_for(ret, module):
    if ret in (None, "None"):
        return None
    if ret == "int":
        return 0
    if ret == "float":
        return 0.0
    if ret == "str":
        return ""
    if ret == "bool":
        return False
    text = ret
    if text.startswith("typing.Optional["):
        text = text[len("typing.Optional["):-1]
    if text.startswith(("typing.List", "typing.Iterable", "typing.Sequence")):
        return []
    if text.startswith("typing.Tuple"):
        return ()
    cls = _resolve(text, module)
    if cls is None:
        return None
    if issubclass(cls, FakeEnum):
        return next(iter(cls._members.values())) if cls._members else None
    return cls._fake_new()


# ── Signals ───────────────────────────────────────────────────────────────────

def _max_args(fn):
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return 99
    n = 0
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL,):
            return 99
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            n += 1
    return n


class BoundSignal:
    def __init__(self, name):
        self.name = name
        self.slots = []

    def connect(self, slot):
        if not callable(slot) and not isinstance(slot, BoundSignal):
            raise FakeTypeError(f"signal {self.name}.connect() needs a callable")
        self.slots.append(slot)
        return None

    def disconnect(self, slot=None):
        if slot is None:
            self.slots = []
        elif slot in self.slots:
            self.slots.remove(slot)

    def emit(self, *args):
        for s in list(self.slots):
            if isinstance(s, BoundSignal):
                s.emit(*args)
                continue
            n = _max_args(s)
            s(*args[:n])

    def __getitem__(self, key):
        return self


class pyqtSignal:
    def __init__(self, *types, name=None):
        self.types = types
        self.attr = None

    def __set_name__(self, owner, name):
        self.attr = name

    def __get__(self, inst, owner):
        if inst is None:
            return self
        key = "_sig_" + (self.attr or "x")
        d = inst.__dict__
        if key not in d:
            d[key] = BoundSignal(self.attr)
        return d[key]


def pyqtSlot(*types, **kw):
    def deco(fn):
        return fn
    return deco


# ── Classes ───────────────────────────────────────────────────────────────────

class FakeRoot:
    _fake_module = "QtCore"
    _fake_qualname = "FakeRoot"

    @classmethod
    def _fake_new(cls):
        obj = object.__new__(cls)
        obj._fake_init_state()
        return obj

    def _fake_init_state(self):
        st = self.__dict__.setdefault("_st", {})
        return st

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}' "
                             f"(not in the PyQt6 API)")


def _make_method(module, owner, meth, overloads):
    static = all(ov["static"] for ov in overloads)

    if meth == "__init__":
        def __init__(self, *args, **kwargs):
            validate(module, owner, meth, overloads, args, kwargs)
            self._fake_init_state()
            hook = getattr(type(self), "_ctor", None)
            if hook:
                hook(self, *args, **kwargs)
        return __init__

    ret = overloads[0]["ret"]

    if static:
        def smethod(*args, **kwargs):
            ov = validate(module, owner, meth, overloads, args, kwargs)
            impl = STATIC_IMPLS.get(f"{owner}.{meth}")
            if impl:
                return impl(*args, **kwargs)
            return default_for(ov["ret"], module)
        return staticmethod(smethod)

    def method(self, *args, **kwargs):
        ov = validate(module, owner, meth, overloads, args, kwargs)
        impl = getattr(type(self), "_impl_" + meth, None)
        if impl is not None:
            return impl(self, *args, **kwargs)
        return default_for(ov["ret"], module)
    method.__name__ = meth
    return method


IMPLS = {}         # "QtWidgets.QComboBox" -> {meth: fn}
STATIC_IMPLS = {}  # "QMessageBox.question" -> fn
CTORS = {}         # "QtWidgets.QLabel" -> fn(self, *args, **kw)


def build():
    # Create in dependency order
    pending = {}
    for m, data in _REG.items():
        for cname, info in data["classes"].items():
            pending[f"{m}.{cname}"] = (m, cname, info)

    def base_key(m, b):
        b = b.strip('"')
        if b.startswith("enum.") or b in ("sip.simplewrapper", "sip.wrapper", "PyQt6.sip.simplewrapper",
                                          "PyQt6.sip.wrapper", "typing.Generic"):
            return None
        if "." in b and b.split(".")[0] in MODULES:
            return b
        for mm in (m, "QtCore", "QtGui", "QtWidgets"):
            if f"{mm}.{b}" in pending or f"{mm}.{b}" in CLASSES:
                return f"{mm}.{b}"
        return None

    def create(key):
        if key in CLASSES:
            return CLASSES[key]
        m, cname, info = pending[key]
        if info["enum"]:
            cls = make_enum(key, info)
        else:
            bases = []
            for b in info["bases"]:
                bk = base_key(m, b)
                if bk and bk in pending:
                    bases.append(create(bk))
            if not bases:
                bases = [FakeRoot]
            ns = {"_fake_module": m, "_fake_qualname": cname}
            for meth, ovs in info["methods"].items():
                if meth in ("__getattr__", "__setattr__", "__new__", "__get__",
                            "__getitem__", "__eq__", "__ne__", "__hash__", "__lt__",
                            "__le__", "__gt__", "__ge__", "__bool__", "__len__", "__iter__",
                            "__contains__", "__repr__", "__str__", "__int__", "__float__",
                            "__index__", "__reduce__", "__copy__", "__deepcopy__",
                            "__or__", "__and__", "__add__", "__sub__", "__mul__", "__truediv__",
                            "__neg__", "__iadd__", "__isub__", "__imul__", "__itruediv__",
                            "__radd__", "__rsub__", "__rmul__", "__invert__", "__xor__",
                            "__ror__", "__rand__", "__rxor__", "__ixor__", "__ior__", "__iand__",
                            "__setitem__", "__delitem__", "__call__", "__matmul__", "__abs__",
                            "__pos__", "__lshift__", "__rshift__"):
                    continue
                ns[meth] = _make_method(m, cname, meth, ovs)
            for cv, ann in info["classvars"].items():
                if ann and "pyqtSignal" in ann:
                    sig = pyqtSignal()
                    sig.attr = cv
                    ns[cv] = sig
                else:
                    ns.setdefault(cv, None)
            for meth, fn in IMPLS.get(key, {}).items():
                ns["_impl_" + meth] = fn
            if key in CTORS:
                ns["_ctor"] = CTORS[key]
            cls = type(cname.split(".")[-1], tuple(bases), ns)
            cls.__qualname__ = cname
        CLASSES[key] = cls
        return cls

    for key in list(pending):
        create(key)
    # Attach nested classes and populate module namespaces
    for key, cls in CLASSES.items():
        m, cname = key.split(".", 1)
        if "." in cname:
            parent_key = f"{m}.{cname.rsplit('.', 1)[0]}"
            parent = CLASSES.get(parent_key)
            if parent is not None:
                setattr(parent, cname.rsplit(".", 1)[1], cls)
                # Scoped enum members are NOT accessible on the parent in PyQt6
        else:
            MODULES[m][cname] = cls
    for m, data in _REG.items():
        for fname, ovs in data["functions"].items():
            if fname in ("pyqtSlot",):
                continue
            MODULES[m][fname] = _make_function(m, fname, ovs)
        for vname, val in data["variables"].items():
            if vname.endswith("_STR"):
                MODULES[m][vname] = "6.6.0"
            elif vname in ("PYQT_VERSION", "QT_VERSION"):
                MODULES[m][vname] = 0x060600
    MODULES["QtCore"]["pyqtSignal"] = pyqtSignal
    MODULES["QtCore"]["pyqtSlot"] = pyqtSlot
    MODULES["QtCore"]["pyqtBoundSignal"] = BoundSignal


def _make_function(module, name, ovs):
    def fn(*args, **kwargs):
        ov = validate(module, module, name, ovs, args, kwargs)
        return default_for(ov["ret"], module)
    fn.__name__ = name
    return fn
