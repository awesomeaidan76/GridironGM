"""
settings.py — persistent game settings (saved to settings.json next to
the game files). Every slider in the Settings window maps to a key here.
"""
import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(_DIR, "settings.json")

# key: (default, group, label, kind, extra)
#   kind = "bool" | "int" | "float" | "choice"
#   extra = (min, max, step) for numbers, list of options for choice
SPEC = {
    # ── Display ──────────────────────────────────────────────────────────────
    "theme":               ("dark", "Display", "Theme", "choice", ["dark", "light"]),
    "accent":              ("crimson", "Display", "Accent colour", "choice",
                            ["crimson", "royal", "emerald", "amber", "violet", "teal"]),
    "font_size":           (13, "Display", "Font size", "int", (10, 18, 1)),
    "table_density":       ("normal", "Display", "Table density", "choice",
                            ["compact", "normal", "comfortable"]),
    "show_ca_number":      (True, "Display", "Show overall ratings as numbers (off = tier names)", "bool", None),
    "show_pa_number":      (True, "Display", "Show scouted potential", "bool", None),
    "show_archetype":      (True, "Display", "Show player archetypes", "bool", None),
    "show_hidden_stats":   (False, "Display", "Reveal hidden personality traits", "bool", None),
    "color_attributes":    (True, "Display", "Colour-code attribute values", "bool", None),
    "highlight_player_team": (True, "Display", "Highlight your team in tables", "bool", None),

    # ── Match engine ─────────────────────────────────────────────────────────
    "home_field_advantage": (True, "Match Engine", "Home field advantage", "bool", None),
    "home_field_strength": (1.0, "Match Engine", "Home field strength", "float", (0.0, 3.0, 0.1)),
    "game_randomness":     (1.0, "Match Engine", "Game-day randomness", "float", (0.2, 2.5, 0.1)),
    "turnover_rate":       (1.0, "Match Engine", "Turnover rate", "float", (0.0, 3.0, 0.1)),
    "sack_rate":           (1.0, "Match Engine", "Sack rate", "float", (0.0, 3.0, 0.1)),
    "big_play_rate":       (1.0, "Match Engine", "Big play rate", "float", (0.2, 3.0, 0.1)),
    "penalty_rate":        (1.0, "Match Engine", "Penalty rate", "float", (0.0, 3.0, 0.1)),
    "fg_accuracy":         (1.0, "Match Engine", "Field goal accuracy", "float", (0.5, 1.5, 0.05)),
    "pat_distance":        (33, "Match Engine", "Extra point kick distance (yds)", "int", (19, 43, 1)),
    "fourth_down_aggression": (1.0, "Match Engine", "League 4th-down aggression", "float", (0.0, 3.0, 0.1)),
    "weather":             (True, "Match Engine", "Weather effects", "bool", None),
    "momentum":            (1.0, "Match Engine", "In-game momentum swings", "float", (0.0, 3.0, 0.1)),
    "streakiness":         (1.0, "Match Engine", "Hot & cold streaks between games", "float", (0.0, 2.0, 0.1)),
    "injury_rate":         (1.0, "Match Engine", "Injury frequency", "float", (0.0, 3.0, 0.1)),
    "injury_severity":     (1.0, "Match Engine", "Injury severity", "float", (0.3, 2.5, 0.1)),
    "pass_tendency":       (1.0, "Match Engine", "League pass/run lean (above 1 = more passing)", "float", (0.5, 1.5, 0.05)),
    "pace":                (1.0, "Match Engine", "Pace of play (more snaps per game)", "float", (0.7, 1.4, 0.05)),
    "completion_rate":     (1.0, "Match Engine", "Completion rate", "float", (0.8, 1.2, 0.02)),
    "run_efficiency":      (1.0, "Match Engine", "Rushing efficiency", "float", (0.7, 1.3, 0.05)),
    "fatigue_rate":        (1.0, "Match Engine", "Fatigue build-up", "float", (0.0, 2.5, 0.1)),
    "fatigue_effect":      (1.0, "Match Engine", "Effect of fatigue on performance", "float", (0.0, 2.5, 0.1)),

    # ── League & season ──────────────────────────────────────────────────────
    "playoff_teams":       (6, "League", "Playoff teams per conference", "int", (2, 8, 1)),
    "overtime_rules":      ("modern", "League", "Overtime rules", "choice",
                            ["modern", "sudden death", "full period"]),
    "salary_cap":          (255_000_000, "League", "Salary cap ($)", "int",
                            (100_000_000, 600_000_000, 5_000_000)),
    "cap_growth":          (0.05, "League", "Salary cap growth per season", "float", (0.0, 0.15, 0.01)),
    "hard_cap":            (True, "League", "Enforce hard cap", "bool", None),
    "roster_size":         (53, "League", "Regular season roster size", "int", (45, 65, 1)),
    "trade_deadline_week": (9, "League", "Trade deadline (week)", "int", (1, 18, 1)),
    "practice_squad_size": (16, "League", "Practice squad size", "int", (0, 20, 1)),

    # ── Player development ───────────────────────────────────────────────────
    "growth_rate":         (1.0, "Development", "Young player growth", "float", (0.2, 3.0, 0.1)),
    "decline_rate":        (1.0, "Development", "Veteran decline", "float", (0.2, 3.0, 0.1)),
    "breakout_rate":       (1.0, "Development", "Breakout / late bloomer frequency", "float", (0.0, 3.0, 0.1)),
    "bust_rate":           (1.0, "Development", "Bust frequency", "float", (0.0, 3.0, 0.1)),
    "retirement_age_shift": (0, "Development", "Retirement age shift (years)", "int", (-4, 4, 1)),
    "draft_class_strength": (1.0, "Development", "Draft class strength", "float", (0.5, 1.5, 0.05)),

    # ── AI behaviour ─────────────────────────────────────────────────────────
    "ai_trade_willingness": (1.0, "AI", "AI trade willingness", "float", (0.0, 2.0, 0.1)),
    "ai_fa_aggression":    (1.0, "AI", "AI free agency aggression", "float", (0.2, 2.0, 0.1)),
    "coach_hot_seat":      (1.0, "AI", "Coach firing frequency", "float", (0.0, 3.0, 0.1)),
    "gm_hot_seat":         (1.0, "AI", "CPU general manager firing frequency", "float", (0.0, 3.0, 0.1)),
    "ai_personality_strength": (1.0, "AI", "How different CPU front offices are (0 = all alike)", "float",
                                (0.0, 2.0, 0.1)),
    "holdout_rate":        (1.0, "AI", "Contract holdout frequency", "float", (0.0, 3.0, 0.1)),

    # ── Game ─────────────────────────────────────────────────────────────────
    "watch_games":         (True, "Game", "Watch your games live (Continue)", "bool", None),
    "watch_speed":         (5, "Game", "Live game speed (1 slow - 10 fast)", "int", (1, 10, 1)),
    "gm_can_be_fired":     (True, "Game", "The owner can fire you", "bool", None),
    "auto_roster_moves":   (True, "Game", "Staff handle injured reserve and the practice squad for you", "bool", None),
    "autosave":            (True, "Game", "Autosave after each week", "bool", None),
    "autosave_slots":      (5, "Game", "Autosaves to keep", "int", (1, 20, 1)),
    "confirm_actions":     (True, "Game", "Ask before releasing / trading players", "bool", None),
}

DEFAULTS = {k: v[0] for k, v in SPEC.items()}
GROUPS = ["Display", "Match Engine", "League", "Development", "AI", "Game"]


# Groups that belong to a league (saved inside it, like ZenGM's league settings).
# The global settings file holds the values new leagues start with.
LEAGUE_GROUPS = ("Match Engine", "League", "Development", "AI")
LEAGUE_KEYS = frozenset(k for k, v in SPEC.items() if v[1] in LEAGUE_GROUPS)


class Settings:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._league = None          # the active league's own settings dict
        self.load()

    def use_league(self, lg):
        """Make this league's settings active (creating them from the current defaults)."""
        own = getattr(lg, "custom_settings", None)
        if not isinstance(own, dict):
            own = {}
        for k in LEAGUE_KEYS:
            if k not in own:
                own[k] = self._data.get(k, DEFAULTS[k])
        lg.custom_settings = own
        self._league = own

    def release_league(self):
        self._league = None

    def load(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in saved.items():
                if k in DEFAULTS and type(v) is type(DEFAULTS[k]):
                    self._data[k] = v
                elif k in DEFAULTS and isinstance(DEFAULTS[k], float) \
                        and isinstance(v, int):
                    self._data[k] = float(v)
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            print(f"Could not save settings: {e}")

    def get(self, key, fallback=None):
        lg = self._league
        if lg is not None and key in lg:
            return lg[key]
        if key in self._data:
            return self._data[key]
        return DEFAULTS.get(key, fallback)

    def set(self, key, value):
        if key not in DEFAULTS:
            return
        if isinstance(DEFAULTS[key], bool):
            value = bool(value)
        elif isinstance(DEFAULTS[key], int):
            value = int(round(value))
        elif isinstance(DEFAULTS[key], float):
            value = float(value)
        self._data[key] = value
        if self._league is not None and key in LEAGUE_KEYS:
            self._league[key] = value

    def reset(self, group=None):
        for k, spec in SPEC.items():
            if group is None or spec[1] == group:
                self._data[k] = spec[0]
                if self._league is not None and k in LEAGUE_KEYS:
                    self._league[k] = spec[0]
        self.save()

    def __getitem__(self, key):
        return self.get(key)


settings = Settings()
