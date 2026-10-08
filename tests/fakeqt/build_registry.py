"""Parse PyQt6 .pyi stubs into a JSON registry used by the strict fake."""
import ast, json, sys, os

STUBS = sys.argv[1]
MODULES = ["QtCore", "QtGui", "QtWidgets"]

def ann(node):
    return ast.unparse(node) if node is not None else None

def parse_func(fn, in_class):
    a = fn.args
    params = []
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    for i, (arg, d) in enumerate(zip(pos, defaults)):
        if in_class and i == 0 and arg.arg in ("self", "cls"):
            continue
        params.append([arg.arg, ann(arg.annotation), d is not None, "pos"])
    if a.vararg:
        params.append([a.vararg.arg, ann(a.vararg.annotation), True, "var"])
    for arg, d in zip(a.kwonlyargs, a.kw_defaults):
        params.append([arg.arg, ann(arg.annotation), d is not None, "kwonly"])
    if a.kwarg:
        params.append([a.kwarg.arg, ann(a.kwarg.annotation), True, "varkw"])
    decos = [ast.unparse(d) for d in fn.decorator_list]
    return {"params": params, "ret": ann(fn.returns), "static": "staticmethod" in decos,
            "classmethod": "classmethod" in decos}

def parse_class(cls, prefix, out):
    name = prefix + cls.name
    info = {"bases": [ast.unparse(b) for b in cls.bases], "methods": {}, "classvars": {},
            "members": [], "enum": None}
    for b in info["bases"]:
        if b.startswith("enum."):
            info["enum"] = b.split(".")[1]
    for node in cls.body:
        if isinstance(node, ast.FunctionDef):
            info["methods"].setdefault(node.name, []).append(parse_func(node, True))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            info["classvars"][node.target.id] = ann(node.annotation)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    if info["enum"]:
                        info["members"].append(t.id)
                    else:
                        info["classvars"][t.id] = None
        elif isinstance(node, ast.ClassDef):
            parse_class(node, name + ".", out)
    out[name] = info

registry = {}
for m in MODULES:
    tree = ast.parse(open(os.path.join(STUBS, m + ".pyi")).read())
    mod = {"classes": {}, "functions": {}, "variables": {}}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            parse_class(node, "", mod["classes"])
        elif isinstance(node, ast.FunctionDef):
            mod["functions"].setdefault(node.name, []).append(parse_func(node, False))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            mod["variables"][node.target.id] = ann(node.annotation)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    mod["variables"][t.id] = ast.unparse(node.value)
    registry[m] = mod
json.dump(registry, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.json"), "w"))
print({m: len(v["classes"]) for m, v in registry.items()})
