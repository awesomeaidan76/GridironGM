"""
save_manager.py — saving, loading and exporting games.

Saves are compressed pickles (.gsav) in the "saves" folder next to the game.
Autosaves rotate. JSON export writes a readable snapshot (rosters, standings,
history) — handy for inspecting your league or feeding it to other tools.
"""
import gzip
import json
import os
import pickle
from datetime import datetime

import player as player_mod

SAVE_VERSION = 2
_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(_DIR, "saves")
AUTO_DIR = os.path.join(SAVE_DIR, "autosaves")
EXPORT_DIR = os.path.join(SAVE_DIR, "exports")


def _ensure_dirs():
    for d in (SAVE_DIR, AUTO_DIR, EXPORT_DIR):
        os.makedirs(d, exist_ok=True)


def _meta(lg):
    t = lg.user_team
    rec = lg.standings.get(lg.user_abbr) if lg.standings else None
    return {
        "version": SAVE_VERSION,
        "saved": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "league": lg.name,
        "team": t.full_name if t else "",
        "abbr": lg.user_abbr,
        "year": lg.year,
        "phase": lg.week_label,
        "record": rec.wlt() if rec else "",
    }


def _safe(name):
    s = "".join(c for c in name if c.isalnum() or c in " _-").strip()
    return s or "save"


def save(lg, name, folder=None):
    _ensure_dirs()
    lg.next_player_id = player_mod.get_id_counter()
    path = os.path.join(folder or SAVE_DIR, _safe(name) + ".gsav")
    payload = {"meta": _meta(lg), "league": lg}
    tmp = path + ".tmp"
    with gzip.open(tmp, "wb", compresslevel=5) as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)
    return path


def autosave(lg, keep=5):
    _ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = save(lg, f"auto_{lg.user_abbr}_{lg.year}_{stamp}", folder=AUTO_DIR)
    autos = sorted(f for f in os.listdir(AUTO_DIR) if f.endswith(".gsav"))
    while len(autos) > keep:
        try:
            os.remove(os.path.join(AUTO_DIR, autos.pop(0)))
        except OSError:
            break
    return path


def load(path):
    with gzip.open(path, "rb") as f:
        payload = pickle.load(f)
    lg = payload["league"]
    player_mod.set_id_counter(getattr(lg, "next_player_id", 1))
    # Keep the id counter ahead of every player in the league
    max_id = max((p.id for p in lg.all_players(True) + lg.retired + lg.draft_class), default=0)
    player_mod.set_id_counter(max_id + 1)
    import staff as staff_mod
    staff_mod.ensure_league(lg)
    return lg


def read_meta(path):
    try:
        with gzip.open(path, "rb") as f:
            payload = pickle.load(f)
        return payload.get("meta", {})
    except Exception:
        return {}


def list_saves():
    _ensure_dirs()
    out = []
    for folder, auto in ((SAVE_DIR, False), (AUTO_DIR, True)):
        for fn in os.listdir(folder):
            if not fn.endswith(".gsav"):
                continue
            path = os.path.join(folder, fn)
            out.append({"path": path, "file": fn, "auto": auto,
                        "modified": os.path.getmtime(path),
                        "size_kb": os.path.getsize(path) // 1024})
    out.sort(key=lambda s: -s["modified"])
    return out


def delete(path):
    os.remove(path)


# ── JSON export ───────────────────────────────────────────────────────────────

def _player_json(p):
    return {
        "id": p.id, "name": p.name, "position": p.position, "age": p.age,
        "team": p.team, "archetype": p.archetype, "ovr": p.ovr, "pot": p.pot,
        "roles": dict(p.roles), "ca_internal": p.ca, "pa_internal": p.pa,
        "height": p.height_str, "weight": p.weight, "college": p.college,
        "attributes": p.attrs, "personality": p.hidden, "morale": p.morale,
        "reputation": p.reputation,
        "contract": p.contract, "draft": p.draft,
        "injury": p.injury["name"] if p.injury else None,
        "season_stats": dict(p.season_stats),
        "career": {str(y): {"team": s["team"], "stats": dict(s["stats"])}
                   for y, s in p.career.items()},
        "awards": p.awards,
    }


def export_json(lg, name):
    _ensure_dirs()
    data = {
        "meta": _meta(lg),
        "teams": {
            a: {"name": t.full_name, "conference": t.conference, "division": t.division,
                "overall": t.overall, "coach": {"name": t.coach.name,
                                                "offense": t.coach.off_scheme,
                                                "defense": t.coach.def_scheme,
                                                "record": t.coach.record_str},
                "history": t.history,
                "roster": [_player_json(p) for p in t.roster]}
            for a, t in lg.teams.items()
        },
        "standings": {a: {"w": r.w, "l": r.l, "t": r.t, "pf": r.pf, "pa": r.pa}
                      for a, r in lg.standings.items()},
        "free_agents": [_player_json(p) for p in lg.free_agents],
        "history": [{k: v for k, v in h.items() if k not in ("schemes",)} for h in lg.history],
        "season_trends": {str(k): v for k, v in lg.season_trends.items()},
    }
    path = os.path.join(EXPORT_DIR, _safe(name) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, default=str)
    return path
