"""
ui_screens_moves.py — Draft, Free Agency and Trades.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QVBoxLayout, QWidget)

import draft as draft_mod
import roster_rules as rr
from ratings import ovr_from_ca
import free_agency as fa
import trades
from contracts import market_value
from ratings import POSITIONS
from settings import settings
from ui_screens_club import Screen, POS_GROUP_FILTERS, pos_matches
from ui_theme import T, accent, ca_color, ovr_color
from ui_widgets import (Card, DataTable, MeterBar, StatTile, ovr_cell, pot_cell, cell, confirm, filter_chips,
                        h_label, info, money, pot_text, personality, USER_ROLE)


# ── Draft ─────────────────────────────────────────────────────────────────────

class DraftScreen(Screen):
    title = "Draft"

    def __init__(self, main):
        super().__init__(main)
        chips, get = filter_chips(POS_GROUP_FILTERS[:-1], self._set_filter, state_key="draft")
        self.filter = get()
        self.outer.addWidget(chips)
        body = QHBoxLayout()
        body.setSpacing(12)
        self.table = DataTable(["Rank", "Name", "Pos", "Age", "College", "Region", "Proj", "Scouted",
                                "OVR est", "POT est", "40yd", "Bench", "Vert", "Archetype",
                                "Personality"], stretch=1)
        self.table.on_activate = self.main.open_player
        body.addWidget(self.table, 3)
        side = QVBoxLayout()
        side.setSpacing(10)
        self.clock = Card("On the Clock")
        self.clock_lbl = QLabel()
        self.clock_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.clock_lbl.setWordWrap(True)
        self.clock.add(self.clock_lbl)
        self.focus_btn = QPushButton("Scouting Focus On / Off")
        self.focus_btn.setToolTip("Your scouts prioritise focus prospects every week (up to 12)")
        self.focus_btn.clicked.connect(self._focus)
        self.clock.add(self.focus_btn)
        self.pick_btn = QPushButton("Draft Selected Player")
        self.pick_btn.setObjectName("primary")
        self.pick_btn.clicked.connect(self._pick)
        self.clock.add(self.pick_btn)
        self.sim_btn = QPushButton("Sim to My Next Pick")
        self.sim_btn.clicked.connect(self._sim)
        self.clock.add(self.sim_btn)
        self.auto_btn = QPushButton("Auto-Pick (Best Available)")
        self.auto_btn.clicked.connect(self._auto)
        self.clock.add(self.auto_btn)
        side.addWidget(self.clock)
        mine = Card("Your Picks")
        self.my_picks = DataTable(["Rd", "Pick", "Player"], stretch=2, sortable=False)
        mine.add(self.my_picks)
        side.addWidget(mine, 1)
        log = Card("Draft Log")
        self.log = DataTable(["Pick", "Team", "Player", "Pos"], stretch=2, sortable=False)
        log.add(self.log)
        side.addWidget(log, 1)
        wrap = QWidget()
        wrap.setLayout(side)
        wrap.setMinimumWidth(340)
        wrap.setMaximumWidth(420)
        body.addWidget(wrap, 1)
        self.outer.addLayout(body, 1)

    def _set_filter(self, f):
        self.filter = f
        self.refresh()

    def refresh(self):
        lg = self.lg
        user = self.user
        cls = lg.draft_class
        import staff as staff_mod
        staff_mod.ensure_league(lg)
        if not cls:
            self.set_subtitle("The next draft class appears when the new season starts.")
        else:
            focus_n = len(getattr(user, "scout_focus", []))
            self.set_subtitle(f"{lg.year + 1} draft class · {len(cls)} prospects · scouts: "
                              f"{', '.join(s.region for s in user.scouts)} · focus list {focus_n}/"
                              f"{staff_mod.FOCUS_LIMIT}. Estimates sharpen as your scouts watch.")
        rows, keys = [], []
        focus = set(getattr(user, "scout_focus", []))
        for p in cls:
            if not pos_matches(p, self.filter):
                continue
            est_ca, est_pa, _, err = staff_mod.estimate(lg, user, p)
            known = staff_mod.knowledge(lg, user.abbr, p.id)
            c = (p.combine or {}) if lg.phase not in ("regular", "playoffs") else {}
            rows.append([cell(p.proj_rank, p.proj_rank),
                         cell(("◉ " if p.id in focus else "") + p.name, bold=p.id in focus,
                              color=accent() if p.id in focus else None),
                         cell(p.position, POSITIONS.index(p.position)),
                         p.age, p.college, staff_mod.college_region(p.college),
                         cell(f"R{p.proj_round}" if p.proj_round and p.proj_round <= 7 else "UDFA",
                              p.proj_rank),
                         cell(f"{known:.0f}%", known, color=T("good") if known >= 70 else
                              T("warn") if known < 30 else None),
                         ovr_cell(ovr_from_ca(est_ca, p.position)),
                         cell(f"{ovr_from_ca(est_pa - err / 2, p.position)}–"
                              f"{ovr_from_ca(est_pa + err / 2, p.position)}",
                              ovr_from_ca(est_pa, p.position),
                              color=ovr_color(ovr_from_ca(est_pa, p.position))),
                         cell(f"{c.get('forty', 0):.2f}", c.get("forty", 0)), c.get("bench", 0),
                         cell(f"{c.get('vertical', 0):.1f}", c.get("vertical", 0)),
                         p.archetype or "", personality(p)])
            keys.append(p.id)
        self.table.set_rows(rows, keys)
        # Clock
        cur = draft_mod.current_pick(lg)
        on_clock = lg.phase == "draft" and cur is not None and cur[2] == lg.user_abbr
        if lg.phase != "draft":
            order = [o for o in lg.draft_order if o[2] == lg.user_abbr]
            txt = ("Draft order is set. Your picks: " + ", ".join(f"R{r} #{pk}" for r, pk, _ in order[:7])
                   if order else "The draft order is set after the playoffs.")
            self.clock_lbl.setText(txt)
        elif cur is None:
            self.clock_lbl.setText("The draft is complete.")
        else:
            rnd, pk, abbr = cur
            nxt = next((i for i, o in enumerate(lg.draft_order[lg.draft_index:]) if o[2] == lg.user_abbr), None)
            t = lg.teams[abbr]
            self.clock_lbl.setText(
                f"<b>Pick {pk}</b> (Round {rnd}) — <b style='color:{accent() if on_clock else T('text')}'>"
                f"{t.full_name}</b>" + ("<br><b>You are on the clock!</b> Select a prospect and draft him."
                                        if on_clock else
                                        (f"<br>Your next pick is in {nxt} selections." if nxt is not None
                                         else "<br>You have no picks left.")))
        self.pick_btn.setEnabled(on_clock)
        self.auto_btn.setEnabled(on_clock)
        self.sim_btn.setEnabled(lg.phase == "draft" and cur is not None and not on_clock)
        mine = []
        made = {(r, pk): (name, pos) for r, pk, a, pid, name, pos in lg.draft_log if a == lg.user_abbr}
        origs = getattr(lg, "draft_orig", []) or [a for _, _, a in lg.draft_order]
        comp = getattr(lg, "draft_comp", set())
        for (r, pk, a), o in zip(lg.draft_order, origs):
            if a == lg.user_abbr:
                pl = made.get((r, pk))
                note = " (comp)" if pk in comp else (f" (from {o})" if o != a else "")
                mine.append([r, f"{pk}{note}", f"{pl[0]} ({pl[1]})" if pl else ""])
        self.my_picks.set_rows(mine)
        self.log.set_rows([[pk, a, name, pos] for r, pk, a, pid, name, pos in reversed(lg.draft_log[-80:])],
                          [pid for r, pk, a, pid, name, pos in reversed(lg.draft_log[-80:])])
        self.log.on_activate = self.main.open_player

    def _focus(self):
        import staff as staff_mod
        pid = self.table.selected_key()
        if pid is None:
            return
        ok, msg = staff_mod.toggle_focus(self.lg, self.user, pid)
        if not ok:
            info(self, "Scouting", msg)
        self.refresh()

    def _pick(self):
        lg = self.lg
        pid = self.table.selected_key()
        p = next((x for x in lg.draft_class if x.id == pid), None)
        if p is None:
            info(self, "Draft", "Select a prospect in the table first.")
            return
        cur = draft_mod.current_pick(lg)
        if not cur or cur[2] != lg.user_abbr:
            return
        draft_mod.make_pick(lg, lg.user_abbr, p)
        draft_mod.sim_until_user(lg)
        self.main.refresh_all()

    def _sim(self):
        draft_mod.sim_until_user(self.lg)
        self.main.refresh_all()

    def _auto(self):
        lg = self.lg
        cur = draft_mod.current_pick(lg)
        if cur and cur[2] == lg.user_abbr:
            draft_mod.auto_pick_for_user(lg)
            draft_mod.sim_until_user(lg)
            self.main.refresh_all()


# ── Free agency ───────────────────────────────────────────────────────────────

class FreeAgencyScreen(Screen):
    title = "Free Agency"

    def __init__(self, main):
        super().__init__(main)
        tiles = QHBoxLayout()
        self.t_space = StatTile("Cap Space")
        self.t_roster = StatTile("Roster")
        self.t_pool = StatTile("Free Agents")
        for t in (self.t_space, self.t_roster, self.t_pool):
            tiles.addWidget(t)
        self.outer.addLayout(tiles)
        chips, get = filter_chips(POS_GROUP_FILTERS[:-1], self._set_filter, state_key="fa")
        self.filter = get()
        self.outer.addWidget(chips)
        self.table = DataTable(["Name", "Pos", "Age", "OVR", "POT", "Asking", "Market", "Interest",
                                "Personality", "Archetype"], stretch=0)
        self.table.on_activate = self.main.open_player
        self.outer.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.note = QLabel()
        self.note.setObjectName("sub")
        self.note.setWordWrap(True)
        row.addWidget(self.note, 1)
        self.wave_btn = QPushButton("Run Next Signing Wave")
        self.wave_btn.clicked.connect(self._wave)
        row.addWidget(self.wave_btn)
        offer = QPushButton("Make Offer…")
        offer.setObjectName("primary")
        offer.clicked.connect(self._offer)
        row.addWidget(offer)
        self.outer.addLayout(row)

    def _set_filter(self, f):
        self.filter = f
        self.refresh()

    def refresh(self):
        lg, team = self.lg, self.user
        cap = lg.salary_cap
        space = team.cap_space(cap)
        self.t_space.set(money(space), color=T("good") if space > 0 else T("bad"))
        self.t_roster.set(f"{fa.active_count(team)} / {fa.roster_limit(lg)}", "Active players / limit")
        self.t_pool.set(len(lg.free_agents), f"Signing wave {lg.fa_wave}/4" if lg.phase == "free_agency"
                        else "Available any time")
        rows, keys = [], []
        scouting = team.scouting
        for p in sorted(lg.free_agents, key=lambda x: -x.ovr):
            if not pos_matches(p, self.filter):
                continue
            appeal = fa.team_appeal(lg, team, p)
            interest = "Keen" if appeal >= 1.08 else "Open" if appeal >= 0.95 else "Reluctant"
            ask = fa.asking(lg, p)
            rows.append([p.name, cell(p.position, POSITIONS.index(p.position)), p.age,
                         ovr_cell(p.ovr, settings["show_ca_number"]),
                         pot_cell(p, scouting),
                         cell(money(ask), ask),
                         cell(money(market_value(p, cap)), market_value(p, cap)),
                         cell(interest, appeal, color=T("good") if interest == "Keen" else
                              T("warn") if interest == "Reluctant" else None),
                         personality(p), p.archetype or ""])
            keys.append(p.id)
            if len(rows) >= 400:
                break
        self.table.set_rows(rows, keys)
        self.wave_btn.setVisible(lg.phase == "free_agency")
        self.wave_btn.setEnabled(lg.phase == "free_agency" and lg.fa_wave < 4)
        if lg.phase == "free_agency":
            self.note.setText("Rival teams sign players in waves. Each wave you let pass, the best "
                              "free agents may be gone — but asking prices also drop over time.")
        else:
            self.note.setText("Unsigned free agents can be added at any time to cover injuries.")
        self.set_subtitle(f"{lg.year} · {lg.week_label}")

    def _offer(self):
        pid = self.table.selected_key()
        p = next((x for x in self.lg.free_agents if x.id == pid), None)
        if p is None:
            info(self, "Free Agency", "Select a free agent first.")
            return
        from ui_dialogs import OfferDialog
        dlg = OfferDialog(self.main, p)
        if dlg.exec():
            self.main.refresh_all()

    def _wave(self):
        from season import fa_next_wave
        n = fa_next_wave(self.lg)
        self.main.status(f"Signing wave {self.lg.fa_wave}: {n} players signed elsewhere.")
        self.main.refresh_all()


# ── Trades ────────────────────────────────────────────────────────────────────

class TradeScreen(Screen):
    title = "Trades"

    def __init__(self, main):
        super().__init__(main)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Trade partner:"))
        self.partner = QComboBox()
        self.partner.setMinimumWidth(260)
        self.partner.currentIndexChanged.connect(lambda _i: self._partner_changed())
        bar.addWidget(self.partner)
        bar.addStretch(1)
        self.outer.addLayout(bar)
        body = QHBoxLayout()
        body.setSpacing(12)
        left = Card("Your Roster")
        self.mine = DataTable(["Name", "Pos", "Age", "OVR", "Salary", "Yrs"], stretch=0)
        left.add(self.mine)
        add_mine = QPushButton("Add to Offer  →")
        add_mine.clicked.connect(lambda: self._add(self.mine, self.give))
        left.add(add_mine)
        body.addWidget(left, 3)

        mid = Card("The Deal")
        mid.add(QLabel("You give:"))
        self.give = QListWidget()
        mid.add(self.give)
        mid.add(QLabel("You get:"))
        self.get = QListWidget()
        mid.add(self.get)
        rm = QPushButton("Remove Selected")
        rm.clicked.connect(self._remove)
        mid.add(rm)
        self.meter = MeterBar()
        mid.add(self.meter)
        self.verdict = QLabel("Build a trade, then propose it.")
        self.verdict.setWordWrap(True)
        mid.add(self.verdict)
        propose = QPushButton("Propose Trade")
        propose.setObjectName("primary")
        propose.clicked.connect(self._propose)
        mid.add(propose)
        mid.setMinimumWidth(280)
        body.addWidget(mid, 2)

        right = Card("Their Roster")
        self.theirs = DataTable(["Name", "Pos", "Age", "OVR", "Salary", "Yrs"], stretch=0)
        right.add(self.theirs)
        add_theirs = QPushButton("←  Ask For")
        add_theirs.clicked.connect(lambda: self._add(self.theirs, self.get))
        right.add(add_theirs)
        body.addWidget(right, 3)
        self.outer.addLayout(body, 1)
        offers = Card("Offers From Other Teams")
        self.offers = QListWidget()
        self.offers.setMaximumHeight(110)
        offers.add(self.offers)
        orow = QHBoxLayout()
        orow.addStretch(1)
        dec = QPushButton("Decline")
        dec.clicked.connect(self._decline_offer)
        orow.addWidget(dec)
        acc = QPushButton("Accept Offer")
        acc.setObjectName("primary")
        acc.clicked.connect(self._accept_offer)
        orow.addWidget(acc)
        offers.body.addLayout(orow)
        self.outer.addWidget(offers)
        self._partners_loaded = False

    def set_partner(self, abbr):
        idx = self.partner.findData(abbr)
        if idx >= 0:
            self.partner.setCurrentIndex(idx)

    def preload(self, player):
        self.set_partner(player.team)
        self._clear()
        it = QListWidgetItem(f"{player.position} {player.name} ({player.ovr} OVR)")
        it.setData(USER_ROLE, player.id)
        self.get.addItem(it)
        self._evaluate()

    def refresh(self):
        lg = self.lg
        if not self._partners_loaded:
            self.partner.blockSignals(True)
            for t in lg.team_list():
                if t.abbr != lg.user_abbr:
                    self.partner.addItem(t.full_name, t.abbr)
            self.partner.blockSignals(False)
            self._partners_loaded = True
        deadline = settings["trade_deadline_week"]
        closed = (lg.phase == "regular" and lg.week >= deadline) or lg.phase == "playoffs"
        self.set_subtitle("Trades are closed until the season ends." if closed else
                          f"Trade deadline: before week {deadline}. AI teams value ability, age, "
                          f"contract value and their own needs.")
        self._fill_offers()
        self._fill(self.mine, self.user)
        abbr = self.partner.currentData()
        if abbr:
            self._fill(self.theirs, lg.teams[abbr])
        self._prune()
        self._evaluate()

    def _fill_offers(self):
        import market
        lg = self.lg
        self.offers.clear()
        lg.trade_offers = [o for o in getattr(lg, "trade_offers", [])
                           if o.get("expires", 0) >= market._clock(lg)]
        for i, o in enumerate(lg.trade_offers):
            give, get = market.offer_assets(lg, o)
            if any(a is None for a in give + get):
                continue
            txt = (f"{lg.teams[o['from']].full_name} offer "
                   f"{', '.join(trades.asset_label(lg, a) for a in give)}  for  "
                   f"{', '.join(trades.asset_label(lg, a) for a in get)}  ({o.get('made', '')})")
            it = QListWidgetItem(txt)
            it.setData(USER_ROLE, i)
            self.offers.addItem(it)
        if not self.offers.count():
            self.offers.addItem(QListWidgetItem("No offers right now. Teams call when they need "
                                                "someone you have."))

    def _offer_selected(self):
        it = self.offers.currentItem()
        if it is None or it.data(USER_ROLE) is None:
            return None
        i = it.data(USER_ROLE)
        offers = getattr(self.lg, "trade_offers", [])
        return offers[i] if 0 <= i < len(offers) else None

    def _accept_offer(self):
        import market
        o = self._offer_selected()
        if o is None:
            return
        if not confirm(self, "Accept offer", "Accept this trade?"):
            return
        ok, msg = market.accept_offer(self.lg, o)
        info(self, "Trade", msg)
        self.main.refresh_all()

    def _decline_offer(self):
        import market
        o = self._offer_selected()
        if o is None:
            return
        market.decline_offer(self.lg, o)
        self.refresh()

    def _fill(self, table, team):
        rows, keys = [], []
        for p in sorted(team.roster, key=lambda x: (POSITIONS.index(x.position), -x.ca)):
            tag = " (PS)" if p.ps else " (IR)" if p.ir else ""
            rows.append([p.name + tag, cell(p.position, POSITIONS.index(p.position)), p.age, ovr_cell(p.ovr),
                         cell(money(p.salary), p.salary), p.contract_years])
            keys.append(p.id)
        for y, r, o in rr.tradable_picks(self.lg, team.abbr):
            rows.append([cell(rr.pick_label(self.lg, y, r, o, team.abbr) + " pick", color=T("gold")),
                         cell("PICK", 99), "", cell("", 0), cell("", 0), cell("", 0)])
            keys.append(f"pick:{y}:{r}:{o}")
        table.set_rows(rows, keys)
        table.on_activate = lambda k: None if isinstance(k, str) else self.main.open_player(k)

    def _partner_changed(self):
        self.get.clear()
        abbr = self.partner.currentData()
        if abbr:
            self._fill(self.theirs, self.lg.teams[abbr])
        self._evaluate()

    def _add(self, table, target):
        pid = table.selected_key()
        if pid is None:
            return
        for i in range(target.count()):
            if target.item(i).data(USER_ROLE) == pid:
                return
        asset = self._resolve(pid)
        if asset is None:
            return
        if trades.is_pick(asset):
            it = QListWidgetItem(trades.asset_label(self.lg, asset))
        else:
            p = asset
            it = QListWidgetItem(f"{p.position} {p.name} ({p.ovr} OVR, {money(p.salary)})")
        it.setData(USER_ROLE, pid)
        target.addItem(it)
        self._evaluate()

    def _remove(self):
        for lw in (self.give, self.get):
            r = lw.currentRow()
            if r >= 0:
                lw.takeItem(r)
        self._evaluate()

    def _clear(self):
        self.give.clear()
        self.get.clear()

    def _prune(self):
        """Drop players who are no longer on the expected roster."""
        lg = self.lg
        partner = self.partner.currentData()
        for lw, owner in ((self.give, lg.user_abbr), (self.get, partner)):
            for i in reversed(range(lw.count())):
                a = self._resolve(lw.item(i).data(USER_ROLE))
                if a is None:
                    lw.takeItem(i)
                elif trades.is_pick(a):
                    if rr.pick_owner(lg, a[1], a[2], a[3]) != owner:
                        lw.takeItem(i)
                elif a.team != owner:
                    lw.takeItem(i)

    def _resolve(self, key):
        if isinstance(key, str) and key.startswith("pick:"):
            _, y, r, o = key.split(":")
            return ("pick", int(y), int(r), o)
        return self.lg.find_player(key)

    def _players(self, lw):
        out = []
        for i in range(lw.count()):
            a = self._resolve(lw.item(i).data(USER_ROLE))
            if a is not None:
                out.append(a)
        return out

    def _evaluate(self):
        abbr = self.partner.currentData()
        if not abbr:
            return None
        give, get = self._players(self.give), self._players(self.get)
        if not give and not get:
            self.meter.set_values(0, 0)
            self.verdict.setText("Build a trade, then propose it.")
            return None
        ok, msg, vin, vout = trades.evaluate(self.lg, self.user, self.lg.teams[abbr], give, get)
        self.meter.set_values(vin, vout)
        self.verdict.setText(f"Value you send: {vin:.0f} · value you ask for: {vout:.0f}\n{msg}")
        self.verdict.setStyleSheet(f"color: {T('good') if ok else T('text2')};")
        return ok

    def _propose(self):
        abbr = self.partner.currentData()
        if not abbr:
            return
        give, get = self._players(self.give), self._players(self.get)
        ok, msg, vin, vout = trades.evaluate(self.lg, self.user, self.lg.teams[abbr], give, get)
        if not ok:
            info(self, "Trade rejected", msg)
            return
        names_out = ", ".join(trades.asset_label(self.lg, a) for a in give) or "nothing"
        names_in = ", ".join(trades.asset_label(self.lg, a) for a in get) or "nothing"
        if not confirm(self, "Confirm trade", f"Send {names_out} for {names_in}?"):
            return
        trades.execute(self.lg, self.user, self.lg.teams[abbr], give, get)
        self._clear()
        info(self, "Trade completed", msg)
        self.main.refresh_all()
