"""
ui_live.py — watch a game unfold play by play.

The match engine records the game state after every snap (field position,
down & distance, score, win probability and momentum). This dialog replays
those snaps at a speed you choose with a scoreboard, a field diagram, a
win-probability graph, a momentum meter and a running play feed.
"""
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QSlider, QVBoxLayout, QWidget)

import weather as wx
from settings import settings
from ui_theme import T, accent
from ui_widgets import ALIGN_CENTER, Card, TeamBadge, h_label

DELAYS = [1700, 1250, 950, 720, 520, 380, 260, 160, 80, 25]


def has_live_data(res):
    states = getattr(res, "states", None)
    return bool(states) and len(states) == len(res.plays)


class FieldWidget(QWidget):
    """A 100-yard field. The home team defends the left end zone."""

    def __init__(self, home, away, parent=None):
        super().__init__(parent)
        self.home, self.away = home, away
        self.ball = None           # absolute 0..100 from the left goal line
        self.first = None
        self.drive_start = None
        self.home_ball = True
        self.setMinimumHeight(118)

    def set_state(self, ball, first, drive_start, home_ball):
        self.ball, self.first, self.drive_start, self.home_ball = ball, first, drive_start, home_ball
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        ez = w * 0.075
        field_w = w - 2 * ez

        def X(yd):
            return ez + field_w * yd / 100.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#2f6b3a")))
        p.drawRect(QRectF(0, 0, w, h))
        for i in range(10):
            if i % 2 == 0:
                p.setBrush(QBrush(QColor("#357642")))
                p.drawRect(QRectF(X(i * 10), 0, field_w / 10.0, h))
        # End zones
        p.setBrush(QBrush(QColor(self.home.colors[0])))
        p.drawRect(QRectF(0, 0, ez, h))
        p.setBrush(QBrush(QColor(self.away.colors[0])))
        p.drawRect(QRectF(w - ez, 0, ez, h))
        p.setPen(QColor("#ffffff"))
        f = QFont()
        f.setBold(True)
        f.setPointSize(9)
        p.setFont(f)
        p.save()
        p.translate(ez / 2, h / 2)
        p.rotate(-90)
        p.drawText(QRectF(-h / 2, -ez / 2, h, ez), int(ALIGN_CENTER.value), self.home.abbr)
        p.restore()
        p.save()
        p.translate(w - ez / 2, h / 2)
        p.rotate(90)
        p.drawText(QRectF(-h / 2, -ez / 2, h, ez), int(ALIGN_CENTER.value), self.away.abbr)
        p.restore()
        # Yard lines and numbers
        line = QPen(QColor(255, 255, 255, 150))
        line.setWidth(1)
        f.setPointSize(8)
        p.setFont(f)
        for yd in range(5, 100, 5):
            p.setPen(line)
            p.drawLine(QPointF(X(yd), 0), QPointF(X(yd), h))
            if yd % 10 == 0:
                num = yd if yd <= 50 else 100 - yd
                p.setPen(QColor(255, 255, 255, 190))
                p.drawText(QRectF(X(yd) - 14, h - 18, 28, 14), int(ALIGN_CENTER.value), str(num))
        if self.ball is None:
            p.end()
            return
        # Drive start, first-down line, ball
        if self.drive_start is not None:
            pen = QPen(QColor(255, 255, 255, 90))
            pen.setWidth(4)
            p.setPen(pen)
            y = h * 0.42
            p.drawLine(QPointF(X(self.drive_start), y), QPointF(X(self.ball), y))
        if self.first is not None and 0 < self.first < 100:
            pen = QPen(QColor("#f5d90a"))
            pen.setWidth(3)
            p.setPen(pen)
            p.drawLine(QPointF(X(self.first), 4), QPointF(X(self.first), h - 4))
        pen = QPen(QColor("#4ea8ff"))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(QPointF(X(self.ball), 4), QPointF(X(self.ball), h - 4))
        team = self.home if self.home_ball else self.away
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.setBrush(QBrush(QColor("#7a4a22")))
        cx, cy = X(self.ball), h * 0.42
        p.drawEllipse(QPointF(cx, cy), 9, 6)
        # Direction arrow
        d = 1 if self.home_ball else -1
        p.setBrush(QBrush(QColor(team.colors[0])))
        path = QPainterPath()
        path.moveTo(QPointF(cx + d * 14, cy - 6))
        path.lineTo(QPointF(cx + d * 24, cy))
        path.lineTo(QPointF(cx + d * 14, cy + 6))
        path.closeSubpath()
        p.drawPath(path)
        p.end()


class PlayView(QWidget):
    """
    The current play drawn on a zoomed slice of the field: the formation,
    every route or block, the defensive shell, the ball's path and the result.
    The offense moves up the screen.
    """
    BACK, DOWN = 11.0, 30.0          # yards shown behind / beyond the line of scrimmage

    def __init__(self, parent=None):
        super().__init__(parent)
        self.diag = None
        self.off = self.dfn = None
        self.t = 1.0
        self.setMinimumHeight(300)
        self.anim = QTimer(self)
        self.anim.timeout.connect(self._frame)

    def set_play(self, diag, off_team, def_team, animate=True):
        self.diag, self.off, self.dfn = diag, off_team, def_team
        self.t = 0.0 if animate else 1.0
        if animate:
            self.anim.start(30)
        self.update()

    def clear(self):
        self.diag = None
        self.anim.stop()
        self.update()

    def _frame(self):
        self.t = min(1.0, self.t + 0.035)
        if self.t >= 1.0:
            self.anim.stop()
        self.update()

    # geometry
    def _pt(self, x, y):
        w, h = self.width(), self.height()
        sx = w / 56.0
        sy = h / (self.BACK + self.DOWN)
        return QPointF(w / 2.0 + x * sx, h - (y + self.BACK) * sy)

    def _path_upto(self, pts, frac):
        """Points along a polyline up to a fraction of its length."""
        if len(pts) < 2:
            return pts
        seg = [((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
               for i in range(len(pts) - 1)]
        total = sum(seg) or 1.0
        goal = total * frac
        out = [pts[0]]
        run = 0.0
        for i, L in enumerate(seg):
            if run + L >= goal:
                k = (goal - run) / L if L else 0.0
                out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k,
                            pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k))
                return out
            out.append(pts[i + 1])
            run += L
        return out

    def _point_at_depth(self, pts, depth):
        """First point along a route that reaches a given depth (or the last point)."""
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            if (y1 - depth) * (y2 - depth) <= 0 and y1 != y2:
                k = (depth - y1) / (y2 - y1)
                return (x1 + (x2 - x1) * k, depth)
        return pts[-1] if pts else (0.0, depth)

    def paintEvent(self, event):
        import playbook as pb
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#2f6b3a")))
        p.drawRect(QRectF(0, 0, w, h))
        d = self.diag
        los = d.get("los", 25) if d else 25
        # Yard lines every 5 (absolute field lines relative to the line of scrimmage)
        for yd in range(-10, 35):
            absolute = los + yd
            if absolute % 5 != 0 or not 0 <= absolute <= 100:
                continue
            pen = QPen(QColor(255, 255, 255, 140 if absolute % 10 == 0 else 70))
            p.setPen(pen)
            a, b = self._pt(-28, yd), self._pt(28, yd)
            p.drawLine(a, b)
            if absolute % 10 == 0 and 0 < absolute < 100:
                num = absolute if absolute <= 50 else 100 - absolute
                p.drawText(QRectF(4, a.y() - 14, 30, 14), int(ALIGN_CENTER.value), str(num))
        # Goal line / end zone
        if los + self.DOWN >= 100:
            gy = self._pt(0, 100 - los).y()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 35)))
            p.drawRect(QRectF(0, 0, w, gy))
        # Hashes
        p.setPen(QPen(QColor(255, 255, 255, 90)))
        for yd in range(-10, 31):
            for hx in (-3.1, 3.1):
                c = self._pt(hx, yd)
                p.drawLine(QPointF(c.x() - 3, c.y()), QPointF(c.x() + 3, c.y()))
        # Line of scrimmage & line to gain
        p.setPen(QPen(QColor("#4ea8ff"), 2))
        p.drawLine(self._pt(-28, 0), self._pt(28, 0))
        if d is None:
            p.setPen(QColor(255, 255, 255, 200))
            p.drawText(QRectF(0, 0, w, h), int(ALIGN_CENTER.value), "Play diagrams appear here")
            p.end()
            return
        form = pb.FORMATIONS.get(d.get("form"), pb.FORMATIONS["Gun Doubles"])
        mir = -1 if d.get("mirror") else 1
        slots = {k: (x * mir, y) for k, (x, y) in form["slots"].items()}
        qb_xy = (0.0, form["qb"])
        off_col = QColor(self.off.colors[0]) if self.off else QColor("#1f6feb")
        def_col = QColor(self.dfn.colors[0]) if self.dfn else QColor("#d1242f")

        # Defense
        cov = d.get("cov", "Cover 3")
        n_cb, n_s, n_lb = d.get("n_cb", 2), d.get("n_s", 2), d.get("n_lb", 2)
        spots = pb.defense_alignment(d.get("front", "4-3"), n_lb, n_cb, n_s, cov)
        man, deep = pb.COVERAGES.get(cov, (False, 2, ""))[:2]
        if not man and self.t > 0.15:
            zc = QColor(def_col)
            zc.setAlpha(45)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(zc))
            widths = {1: [(-26, 26)], 2: [(-26, 0), (0, 26)]}.get(deep, [])
            if cov.startswith("Cover 3") or cov == "Fire Zone":
                widths = [(-26, -9), (-9, 9), (9, 26)]
            elif cov in ("Cover 4", "Cover 6", "Prevent"):
                widths = [(-26, -13), (-13, 0), (0, 13), (13, 26)]
            for x1, x2 in widths:
                a, b = self._pt(x1 + 0.5, 30), self._pt(x2 - 0.5, 14)
                p.drawRoundedRect(QRectF(a, b), 8, 8)
        dpen = QPen(def_col, 2.5)
        for role, x, y in spots:
            c = self._pt(x, y)
            p.setPen(dpen)
            p.drawLine(QPointF(c.x() - 5, c.y() - 5), QPointF(c.x() + 5, c.y() + 5))
            p.drawLine(QPointF(c.x() - 5, c.y() + 5), QPointF(c.x() + 5, c.y() - 5))

        t = self.t
        target = d.get("target")
        carrier = d.get("carrier")
        routes = d.get("routes", {})
        # Offensive line
        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.setBrush(QBrush(off_col))
        for x, y in pb.OL.values():
            c = self._pt(x, y)
            p.drawRect(QRectF(c.x() - 5, c.y() - 5, 10, 10))
            if d.get("run"):
                tip = self._pt(x + 0.8 * d.get("dir", 1), y + 2.2 * min(1.0, t * 2))
                p.drawLine(c, tip)
        # Routes
        for slot, xy in slots.items():
            rt = routes.get(slot)
            if not rt or rt == "block" or d.get("run"):
                continue
            pts = pb.route_points(xy, rt)
            if len(pts) < 2:
                continue
            show = self._path_upto(pts, min(1.0, t * 1.4))
            hl = slot == target
            pen = QPen(QColor("#f5d90a") if hl else QColor(255, 255, 255, 190), 3 if hl else 1.6)
            p.setPen(pen)
            for i in range(len(show) - 1):
                p.drawLine(self._pt(*show[i]), self._pt(*show[i + 1]))
            if t >= 0.7:
                self._arrow(p, pts[-2], pts[-1], pen.color())
        # Run path
        if d.get("run"):
            start = qb_xy if carrier == "QB" else slots.get(carrier, (0.0, -7.0))
            path = pb.RUN_PATHS.get(d["run"], pb.RUN_PATHS["inside zone"])
            dr = d.get("dir", 1)
            pts = [(start[0] + dx * dr, start[1] + dy) for dx, dy in path]
            # Stretch the end of the path to the actual gain
            gain = d.get("yards", 0)
            last = pts[-1]
            pts[-1] = (last[0], max(min(gain, self.DOWN - 1), -6))
            show = self._path_upto(pts, t)
            p.setPen(QPen(QColor("#f5d90a"), 3))
            for i in range(len(show) - 1):
                p.drawLine(self._pt(*show[i]), self._pt(*show[i + 1]))
            ball = show[-1]
        else:
            ball = None
            if target and target in slots and routes.get(target) not in (None, "block"):
                pts = pb.route_points(slots[target], routes[target])
                catch = self._point_at_depth(pts, d.get("air", 5))
                if t > 0.55 and not d.get("sack"):
                    k = min(1.0, (t - 0.55) / 0.3)
                    bx = qb_xy[0] + (catch[0] - qb_xy[0]) * k
                    by = qb_xy[1] + (catch[1] - qb_xy[1]) * k
                    pen = QPen(QColor(255, 255, 255, 220), 1.5)
                    pen.setStyle(Qt.PenStyle.DashLine)
                    p.setPen(pen)
                    p.drawLine(self._pt(*qb_xy), self._pt(bx, by))
                    ball = (bx, by)
                    if k >= 1.0 and not d.get("inc") and not d.get("to"):
                        end = (catch[0], max(catch[1], min(d.get("yards", 0), self.DOWN - 1)))
                        yac = self._path_upto([catch, end], min(1.0, (t - 0.85) / 0.15))
                        p.setPen(QPen(QColor("#f5d90a"), 3))
                        p.drawLine(self._pt(*yac[0]), self._pt(*yac[-1]))
                        ball = yac[-1]
            if d.get("sack"):
                ball = (qb_xy[0], qb_xy[1] - 2 * t)
        # Skill players and QB
        names = d.get("names", {})
        f = QFont()
        f.setPointSize(7)
        f.setBold(True)
        p.setFont(f)
        for slot, xy in list(slots.items()) + [("QB", qb_xy)]:
            c = self._pt(*xy)
            p.setPen(QPen(QColor("#ffffff"), 1.5))
            p.setBrush(QBrush(off_col))
            p.drawEllipse(c, 8, 8)
            num = names.get(slot, ("", ""))[0]
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(c.x() - 8, c.y() - 8, 16, 16), int(ALIGN_CENTER.value), str(num or slot[:2]))
        # Ball
        if ball is not None:
            c = self._pt(*ball)
            p.setPen(QPen(QColor("#ffffff"), 1))
            p.setBrush(QBrush(QColor("#7a4a22")))
            p.drawEllipse(c, 5, 3.5)
        # Captions
        p.setPen(QColor("#ffffff"))
        f.setPointSize(9)
        p.setFont(f)
        title = f"{d.get('form', '')} · {d.get('play', '')}" + ("  (play-action)" if d.get("pa") else "")
        p.drawText(QRectF(8, 6, w - 16, 18), int(Qt.AlignmentFlag.AlignLeft.value), title)
        p.drawText(QRectF(8, 6, w - 16, 18), int(Qt.AlignmentFlag.AlignRight.value),
                   f"{d.get('front', '')} front · {d.get('dcall') or cov}"
                   + (" · blitz" if d.get("blitz") and "Blitz" not in (d.get("dcall") or "") else ""))
        if t >= 1.0:
            res = ("TOUCHDOWN" if d.get("td") else d.get("to", "").upper() if d.get("to") else
                   "SACK" if d.get("sack") else "INCOMPLETE" if d.get("inc") else
                   f"{d.get('yards', 0):+d} yards")
            f.setPointSize(13)
            p.setFont(f)
            p.drawText(QRectF(0, h - 30, w, 24), int(ALIGN_CENTER.value), res)
        p.end()

    def _arrow(self, p, a, b, color):
        import math
        pa, pb_ = self._pt(*a), self._pt(*b)
        ang = math.atan2(pb_.y() - pa.y(), pb_.x() - pa.x())
        path = QPainterPath()
        path.moveTo(pb_)
        path.lineTo(QPointF(pb_.x() - 8 * math.cos(ang - 0.45), pb_.y() - 8 * math.sin(ang - 0.45)))
        path.lineTo(QPointF(pb_.x() - 8 * math.cos(ang + 0.45), pb_.y() - 8 * math.sin(ang + 0.45)))
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawPath(path)


class WinProbChart(QWidget):
    """Home win probability across the game, filled in team colours."""

    def __init__(self, home, away, total, parent=None):
        super().__init__(parent)
        self.home, self.away = home, away
        self.total = max(1, total)
        self.points = []
        self.setMinimumHeight(150)

    def add(self, i, wp):
        self.points.append((i, wp))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        left, right, top, bottom = 40, 8, 8, 8
        pw, ph = w - left - right, h - top - bottom

        def X(i):
            return left + pw * i / self.total

        def Y(v):
            return top + ph * (1 - v)

        p.setPen(QColor(T("muted")))
        p.drawText(QRectF(0, top - 6, left - 4, 14), int(ALIGN_CENTER.value), self.home.abbr)
        p.drawText(QRectF(0, h - bottom - 8, left - 4, 14), int(ALIGN_CENTER.value), self.away.abbr)
        grid = QPen(QColor(T("border")))
        grid.setStyle(Qt.PenStyle.DashLine)
        p.setPen(grid)
        p.drawLine(QPointF(left, Y(0.5)), QPointF(w - right, Y(0.5)))
        if len(self.points) >= 2:
            for color, above in ((self.home.colors[0], True), (self.away.colors[0], False)):
                path = QPainterPath()
                path.moveTo(QPointF(X(self.points[0][0]), Y(0.5)))
                for i, v in self.points:
                    v = max(v, 0.5) if above else min(v, 0.5)
                    path.lineTo(QPointF(X(i), Y(v)))
                path.lineTo(QPointF(X(self.points[-1][0]), Y(0.5)))
                path.closeSubpath()
                c = QColor(color)
                c.setAlpha(150)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(c))
                p.drawPath(path)
            pen = QPen(QColor(T("text")))
            pen.setWidth(2)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            line = QPainterPath()
            line.moveTo(QPointF(X(self.points[0][0]), Y(self.points[0][1])))
            for i, v in self.points[1:]:
                line.lineTo(QPointF(X(i), Y(v)))
            p.drawPath(line)
        p.end()


class MomentumBar(QWidget):
    """Centered meter: fills toward whichever side owns the momentum."""

    def __init__(self, home, away, parent=None):
        super().__init__(parent)
        self.home, self.away = home, away
        self.value = 0.0
        self.setMinimumHeight(14)

    def set_value(self, v):
        self.value = max(-1.0, min(1.0, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(T("border_soft"))))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        mid = w / 2.0
        span = abs(self.value) * mid
        if span > 1:
            team = self.home if self.value > 0 else self.away
            p.setBrush(QBrush(QColor(team.colors[0])))
            # Home owns the left half of the meter, matching the field
            x = mid - span if self.value > 0 else mid
            p.drawRoundedRect(QRectF(x, 0, span, h), h / 2, h / 2)
        p.setBrush(QBrush(QColor(T("text"))))
        p.drawRect(QRectF(mid - 1, 0, 2, h))
        p.end()


class LiveGameDialog(QDialog):
    def __init__(self, main, res, parent=None):
        super().__init__(parent or main)
        self.main = main
        self.lg = main.lg
        self.res = res
        self.home = self.lg.teams[res.home]
        self.away = self.lg.teams[res.away]
        self.i = 0
        self.n = len(res.plays)
        self.drive_start = None
        self.drive_plays = 0
        self.last_poss = None
        self.game_over = False
        self.setWindowTitle(f"{res.away} @ {res.home} — {res.playoff or 'Week ' + str(res.week)}")
        self.resize(1200, 900)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Scoreboard
        board = Card()
        row = QHBoxLayout()
        self.score_lbl = {}
        self.to_lbl = {}
        for abbr, team, side in ((res.away, self.away, "away"), (res.home, self.home, "home")):
            box = QHBoxLayout()
            if side == "away":
                box.addWidget(TeamBadge(team, 52))
            col = QVBoxLayout()
            col.addWidget(h_label(team.full_name, "h3"))
            rec = self.lg.standings.get(abbr)
            sub = QLabel(rec.wlt() if rec else "")
            sub.setObjectName("muted")
            col.addWidget(sub)
            box.addLayout(col)
            sc = QLabel("0")
            sc.setObjectName("bigvalue")
            self.score_lbl[abbr] = sc
            box.addWidget(sc)
            if side == "home":
                box.addWidget(TeamBadge(team, 52))
            row.addLayout(box, 1)
            if side == "away":
                mid = QVBoxLayout()
                self.clock_lbl = h_label("Kickoff", "h2")
                self.clock_lbl.setAlignment(ALIGN_CENTER)
                mid.addWidget(self.clock_lbl)
                self.sit_lbl = QLabel("")
                self.sit_lbl.setObjectName("caps")
                self.sit_lbl.setAlignment(ALIGN_CENTER)
                mid.addWidget(self.sit_lbl)
                row.addLayout(mid)
        board.body.addLayout(row)
        info = QLabel(self._info_line())
        info.setObjectName("muted")
        info.setAlignment(ALIGN_CENTER)
        board.add(info)
        root.addWidget(board)

        # Field
        self.field = FieldWidget(self.home, self.away)
        root.addWidget(self.field)
        self.banner = QLabel("")
        self.banner.setAlignment(ALIGN_CENTER)
        self.banner.setObjectName("h2")
        root.addWidget(self.banner)

        body = QHBoxLayout()
        # Left: the play diagram and the feed
        left = QVBoxLayout()
        self.has_diagrams = any(getattr(res, "diagrams", None) or [])
        self.playview = PlayView()
        self.playview.setVisible(self.has_diagrams)
        left.addWidget(self.playview, 3)
        left.addWidget(h_label("Play-by-play", "h3"))
        self.feed = QListWidget()
        self.feed.setWordWrap(True)
        left.addWidget(self.feed, 2)
        body.addLayout(left, 3)
        # Right: win probability, momentum, drive, scoring
        right = QVBoxLayout()
        wp_card = Card("Win probability")
        self.wp_lbl = QLabel("")
        wp_card.add(self.wp_lbl)
        self.wp = WinProbChart(self.home, self.away, self.n)
        wp_card.add(self.wp)
        right.addWidget(wp_card)
        mom_card = Card("Momentum")
        labels = QHBoxLayout()
        labels.addWidget(QLabel(self.home.abbr))
        labels.addStretch(1)
        labels.addWidget(QLabel(self.away.abbr))
        mom_card.body.addLayout(labels)
        self.mom = MomentumBar(self.home, self.away)
        mom_card.add(self.mom)
        right.addWidget(mom_card)
        drive_card = Card("Current drive")
        self.drive_lbl = QLabel("—")
        self.drive_lbl.setWordWrap(True)
        drive_card.add(self.drive_lbl)
        right.addWidget(drive_card)
        sc_card = Card("Scoring")
        self.scoring_lbl = QLabel("No scoring yet.")
        self.scoring_lbl.setWordWrap(True)
        sc_card.add(self.scoring_lbl)
        right.addWidget(sc_card)
        right.addStretch(1)
        body.addLayout(right, 2)
        root.addLayout(body, 1)

        # Controls
        ctl = QHBoxLayout()
        self.play_btn = QPushButton("Pause")
        self.play_btn.clicked.connect(self.toggle)
        ctl.addWidget(self.play_btn)
        nxt = QPushButton("Next play")
        nxt.clicked.connect(self.step)
        ctl.addWidget(nxt)
        nd = QPushButton("Next drive")
        nd.clicked.connect(self.next_drive)
        ctl.addWidget(nd)
        nq = QPushButton("End of quarter")
        nq.clicked.connect(self.next_quarter)
        ctl.addWidget(nq)
        ctl.addSpacing(16)
        ctl.addWidget(QLabel("Speed"))
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(1, 10)
        self.speed.setValue(int(settings["watch_speed"] or 5))
        self.speed.setFixedWidth(160)
        self.speed.valueChanged.connect(self._speed_changed)
        ctl.addWidget(self.speed)
        ctl.addStretch(1)
        self.skip_btn = QPushButton("Skip to final")
        self.skip_btn.clicked.connect(self.skip)
        ctl.addWidget(self.skip_btn)
        self.box_btn = QPushButton("Box score")
        self.box_btn.setObjectName("primary")
        self.box_btn.clicked.connect(self.open_box)
        ctl.addWidget(self.box_btn)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        ctl.addWidget(close)
        root.addLayout(ctl)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(DELAYS[self.speed.value() - 1])

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _info_line(self):
        res = self.res
        bits = []
        if res.playoff:
            bits.append(res.playoff)
        else:
            bits.append(f"Week {res.week}")
        bits.append(f"at {self.home.city}")
        w = getattr(res, "weather", None)
        if w:
            bits.append(wx.describe(w))
        return " · ".join(bits)

    def _speed_changed(self, v):
        settings.set("watch_speed", int(v))
        if self.timer.isActive():
            self.timer.start(DELAYS[int(v) - 1])

    def toggle(self):
        if self.game_over:
            return
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText("Play")
        else:
            self.timer.start(DELAYS[self.speed.value() - 1])
            self.play_btn.setText("Pause")

    def _tick(self):
        if self.i >= self.n:
            self._final()
            return
        kind = self.res.plays[self.i][5]
        self.step()
        # Let big moments breathe
        if kind == "score" and self.timer.isActive():
            self.timer.start(DELAYS[self.speed.value() - 1] * 3)
        elif self.timer.isActive():
            self.timer.start(DELAYS[self.speed.value() - 1])

    def step(self):
        if self.i >= self.n:
            self._final()
            return
        self._show(self.i)
        self.i += 1
        if self.i >= self.n:
            self._final()

    def _advance_until(self, stop):
        while self.i < self.n and not stop(self.i):
            self._show(self.i, quiet=True)
            self.i += 1
        if self.i < self.n:
            self._show(self.i)
            self.i += 1
        if self.i >= self.n:
            self._final()

    def next_drive(self):
        start = self.res.states[self.i - 1][7] if self.i > 0 else None
        self._advance_until(lambda j: start is not None and self.res.states[j][7] != start)

    def next_quarter(self):
        q = self.res.plays[self.i][0] if self.i < self.n else None
        self._advance_until(lambda j: self.res.plays[j][0] != q)

    def skip(self):
        while self.i < self.n:
            self._show(self.i, quiet=True)
            self.i += 1
        self._final()

    # ── Rendering a snap ─────────────────────────────────────────────────────

    def _show(self, j, quiet=False):
        res = self.res
        q, clock, team, sit, text, kind = res.plays[j]
        # States are captured as each line is logged (before the play's result is
        # applied), so the state attached to the next line is "after this play".
        yl, down, togo, hs, as_, wp, mom, home_ball = res.states[min(j + 1, self.n - 1)]
        self.score_lbl[res.home].setText(str(hs))
        self.score_lbl[res.away].setText(str(as_))
        self.clock_lbl.setText(f"{q}  {clock}")
        poss = res.home if home_ball else res.away
        if poss != self.last_poss:
            self.last_poss = poss
            self.drive_start = yl
            self.drive_plays = 0
        if kind == "play":
            self.drive_plays += 1
        dn = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(down, "")
        goal = yl + togo >= 100
        self.sit_lbl.setText(f"{poss} ball · {dn} & {'Goal' if goal else togo}")
        absolute = yl if home_ball else 100 - yl
        first = (yl + togo) if home_ball else 100 - (yl + togo)
        start = None
        if self.drive_start is not None:
            start = self.drive_start if home_ball else 100 - self.drive_start
        self.field.set_state(absolute, None if goal else first, start, home_ball)
        self.wp.add(j, wp / 1000.0)
        hw = wp / 10.0
        lead = res.home if hw >= 50 else res.away
        self.wp_lbl.setText(f"<b>{lead}</b> {max(hw, 100 - hw):.0f}%")
        self.mom.set_value(mom / 100.0)
        gained = yl - (self.drive_start or yl)
        self.drive_lbl.setText(f"<b>{poss}</b>: {self.drive_plays} play"
                               f"{'s' if self.drive_plays != 1 else ''}, {gained:+d} yards")
        if kind == "score":
            self._update_scoring(j)
        if quiet:
            return
        diags = getattr(res, "diagrams", None) or []
        diag = diags[j] if j < len(diags) else None
        if diag:
            off = self.home if diag.get("home") else self.away
            dfn = self.away if diag.get("home") else self.home
            self.playview.set_play(diag, off, dfn, animate=self.timer.isActive())
        item = QListWidgetItem(f"{q} {clock}  {team}  {sit + ' — ' if sit else ''}{text}")
        if kind == "score":
            item.setForeground(QBrush(QColor(accent())))
            f = item.font()
            f.setBold(True)
            item.setFont(f)
            self.banner.setText(self._banner_text(text))
        elif kind == "note":
            item.setForeground(QBrush(QColor(T("muted"))))
            if "INJURY" in text:
                item.setForeground(QBrush(QColor(T("warn"))))
        else:
            up = text.upper()
            if "INTERCEPTED" in up or "FUMBLE" in up:
                item.setForeground(QBrush(QColor(T("bad"))))
                self.banner.setText("TURNOVER")
            elif kind == "play":
                self.banner.setText("")
        self.feed.insertItem(0, item)

    def _banner_text(self, text):
        t = text.upper()
        for key in ("TOUCHDOWN", "FIELD GOAL", "SAFETY", "TWO-POINT"):
            if key in t:
                return key
        return "SCORE"

    def _update_scoring(self, upto):
        lines = []
        for q, clock, team, text, h, a in self.res.scoring:
            lines.append((q, clock, team, text, h, a))
        # Only reveal scores that have happened so far
        shown = [s for s in lines if s[4] + s[5] <= int(self.score_lbl[self.res.home].text())
                 + int(self.score_lbl[self.res.away].text())]
        if not shown:
            self.scoring_lbl.setText("No scoring yet.")
            return
        self.scoring_lbl.setText("<br>".join(
            f"<b>{q} {c}</b> {t}: {txt} <span style='color:{T('muted')}'>({self.res.away} {a}-{h} "
            f"{self.res.home})</span>" for q, c, t, txt, h, a in shown[-6:]))

    def _final(self):
        if self.game_over:
            return
        self.game_over = True
        self.timer.stop()
        res = self.res
        self.score_lbl[res.home].setText(str(res.home_score))
        self.score_lbl[res.away].setText(str(res.away_score))
        self._update_scoring(self.n)
        self.clock_lbl.setText("FINAL" + (" / OT" if res.overtime else ""))
        self.sit_lbl.setText("")
        w = res.winner
        self.banner.setText(f"{self.lg.teams[w].full_name} win" if w else "Tie game")
        self.play_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)

    def open_box(self):
        self.skip()
        self.accept()
        self.main.open_game(self.res)

    def done(self, r):
        self.timer.stop()
        self.playview.anim.stop()
        super().done(r)
