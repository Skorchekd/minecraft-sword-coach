# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""The copilot's counter: the move the other player made, the move you answered it with, and whether your answer was the right one; if
not, the answer that has gone best after their move from where you stood (shown as: your move in red -> that answer).

Each exchange is read WAIT ticks after it ends, because the reader also looks at what comes after a move (a W-tap's second press can land
after the exchange): read the moment an exchange ends, the call matched the whole-fight read 77% of the time, 12 ticks later 93%, as right
as the whole-fight read (two real clients, fights it never saw). So at each step their move is the exchange before your answer's, and your
answer is the exchange that ended WAIT ticks ago: what the answer model scores (their last move, then your answer from that spot).

The answers come from the answer model (models/answer_model.onnx): how each answer has gone after their move from this spot in recorded
fights against real players, HP over 1.2 s. A counter is named only among moves you can make mid-fight that show in your keys (ANSWERS),
only when one sits GAP ahead of what players usually do from there, and never after a run of crits on you up close, where no answer has
shown an edge. Your answer is right when it is that counter (or a move built on it), or within GAP of it; wrong when it sits GAP or more
under it; not judged when there is no clear counter or the model has no value for your move there. On real fights the model never saw,
players who happened to do the named counter came out about 0.2 HP better over 1.2 s than with other answers at the same moments (95% range
0.05 to 0.36; a random answer: 0.06), one of several settings tried: a trend, not yet a pass."""
import numpy as np

from . import features as fx
from .fields import LABELS, R, SEG, TECHNIQUES
from .review import _builds_on, hit_events, read_choice
from .spot import spot_features

WAIT = 12          # ticks after an exchange before it is read
SURE = 0.5         # their move is named only when the reader is this sure of it
GAP = 0.2          # HP over 1.2 s: the counter must be this far ahead of the usual answer from here
# Answers a counter can name: moves made mid-fight that show in the keys (crit and sweep timings do not, and spam clicking is no advice).
ANSWERS = {"sprint_hit", "w_tap", "s_tap", "jump_reset", "strafe", "space", "bait", "retreat", "circle_strafe", "run_in", "jump_in"}
ENGAGED = 6.0      # blocks: further apart there is no exchange to answer

# What to do, in a few words, for each answer the model can name.
HOW = {
    "sprint_hit": "sprint in and hit",
    "w_tap": "after your hit, let go of W",
    "s_tap": "after your hit, tap S",
    "jump_crit": "jump, crit on the way down",
    "jump_reset": "jump as their hit lands",
    "strafe": "switch A/D going in",
    "space": "hold range at their reach",
    "bait": "hover just outside reach",
    "retreat": "back off after your hit",
    "crit_counter": "crit off their knockback",
    "sneak_tap": "after your hit, tap sneak",
    "circle_strafe": "circle them one way",
    "reset_crit": "jump reset, then crit",
    "hit_select": "wait for their swing, then hit",
    "kb_displace": "flick off them, then sprint hit",
    "spam_click": "hit early and often",
    "jump_spam": "jump again as you land",
    "stand_trade": "stand and trade",
    "crit_deflection": "sprint hit them as they land",
    "punish_crit": "crit off their hit's knockback",
    "nokb_crit": "after your crit hold W, hit after them",
    "double_crit": "crit, then crit again",
    "uppercut": "sprint hit on the way up",
    "falling_sprint_hit": "sprint hit as you fall",
    "s_crit": "hold S as you crit",
    "s_hold_deflection": "deflect, then tap S",
    "repositioning": "after their crit, S to stun range",
    "pick_hit": "hit from the edge of reach",
    "sprint_crit": "drop sprint just before a crit",
    "nokb_combo": "chain no-knockback crits",
    "crouch_dodge": "sneak as they swing",
    "falling_sprint_hit_deflection": "falling sprint hit right after theirs",
    "single_sweep": "full hit standing still",
    "sweep_combo": "sweep, then sweep again",
    "followup_sweep": "sweep right after your hit",
    "backaway_sweep": "back away, then sweep",
    "punish_sweep": "sweep after they miss",
    "back_sweep": "sweep holding S",
    "side_sweep": "sweep moving sideways",
    "run_in": "run straight in",
    "jump_in": "jump in",
    "jump_reset_sprint_hit": "sprint hit in your jump reset",
}


def due(n):
    """True when a step is due with n ticks in: WAIT ticks after an exchange ended (exchanges start at tick 1, 13, 25, ...)."""
    return n >= 1 + 2 * SEG + WAIT and (n - 1 - WAIT) % SEG == 0


def read_at(readers, raw, opitch, keys, starts, n, view):
    """One side of the exchanges starting at `starts`, from ticks before n only, cut the way the server's read_latest cuts it: [(P, M or None)].
    view 1 = them (keys read from how they moved), 0 = you (your own keys)."""
    a = max(0, int(min(starts)) - readers.pre - fx.KEY_PAST - fx.KEY_FUT - 2)
    r = np.asarray(raw[a:n], np.float64)
    op = np.zeros(len(r)) if opitch is None else np.asarray(opitch[a:n], np.float64)
    if view == 1:
        F = fx.view(r, op, readers.their_keys(r, op), False)
    else:
        F = fx.view(r, op, fx.own_keys(np.asarray(keys[a:n], np.float64)), True)
    P, M = readers._run(F, np.asarray(starts) - a, view)
    return [(P[i], None if M is None else M[i]) for i in range(len(starts))]


def farmed(raw, keys, s):
    """Two or more crits on you in the three exchanges before s, up close at s: the review's rule for when no answer has shown an edge."""
    crits = hit_events(raw, None, keys)["crits"]
    n = sum(1 for t, on, _ in crits if on == 0 and s - 3 * SEG <= t < s)
    d = float(np.hypot(raw[s - 1, R["ox"]] - raw[s - 1, R["sx"]], raw[s - 1, R["oz"]] - raw[s - 1, R["sz"]]))
    return n >= 2 and d < 2.5


class Counter:
    """One fight's counters, from nothing but the past. The same code scores old fights and drives the screen."""

    def __init__(self, readers, tier=None, sure=SURE, gap=GAP):
        self.r, self.tier, self.sure, self.gap = readers, tier, sure, gap
        self.times = {}         # how many separate times each of their moves was read this fight (a move runs over several exchanges)
        self.last = None

    def step(self, raw, opitch, keys, n):
        """At n ticks in, WAIT ticks after an exchange ended: {"t": tick, "them": {...} or None, "you": {...} or None, "counter": {...} or None,
        "verdict": "right" / "wrong" / None, "why": ...}."""
        raw = np.asarray(raw[:n], np.float64)
        s = n - WAIT - SEG          # your answer: the exchange that ended WAIT ticks ago
        sp = s - SEG                # their move: the exchange before it
        out = {"t": n - 1, "ex": (s - 1) // SEG, "them": None, "you": None, "counter": None, "verdict": None, "why": None}
        if sp < 1:
            out["why"] = "too early"
            return out
        if np.hypot(raw[s - 1, R["ox"]] - raw[s - 1, R["sx"]], raw[s - 1, R["oz"]] - raw[s - 1, R["sz"]]) >= ENGAGED:
            out["why"] = "apart"
            self.last = None
            return out
        (Pt, Mt), = read_at(self.r, raw, opitch, None, [sp], n, 1)
        c = read_choice(Pt, Mt)
        if c["p"] < self.sure:
            out["why"] = "unsure"
            self.last = None
            return out
        tid = c["id"]
        if tid != self.last:
            self.times[tid] = self.times.get(tid, 0) + 1
        self.last = tid
        out["them"] = {"id": tid, "name": LABELS[tid], "p": round(float(c["p"]), 2), "times": self.times[tid]}
        if keys is not None:
            (Py, My), = read_at(self.r, raw, opitch, keys, [s], n, 0)
            y = read_choice(Py, My)
            out["you"] = {"id": y["id"], "name": LABELS[y["id"]], "p": round(float(y["p"]), 2)}
        if self.r.answers is None:
            out["why"] = "no answer model"
            return out
        if farmed(raw, None if keys is None else np.asarray(keys[:n], np.float64), s):
            out["why"] = "farmed"
            return out
        got = self.r.answers.lookup(spot_features(raw, np.array([s])), [tid], self.tier, [c["p"] >= 0.6])[0]
        opts = [o for o in (got or {}).get("options", []) if o["id"] in ANSWERS]
        if not opts:
            out["why"] = "no answers known after it"
            return out
        usual = sum(o["value"] * o["share"] for o in opts) / max(1e-9, sum(o["share"] for o in opts))
        top = max(opts, key=lambda o: o["value"])
        out["gap"] = round(top["value"] - usual, 2)
        out["top"] = top["id"]
        out["options"] = [(o["id"], o["value"], o["share"]) for o in got["options"]]
        if top["value"] - usual < self.gap:
            out["why"] = "no clear counter"
            return out
        out["counter"] = {"id": top["id"], "name": top["name"], "how": HOW.get(top["id"], ""), "gap": out["gap"]}
        if out["you"] is not None:
            out["verdict"] = judge(out["you"]["id"], top, got["options"], self.gap)
        return out


def judge(you, top, options, gap=GAP):
    """right: your answer is the counter, a move built on it, or within gap of it; wrong: gap or more under it; None: no value for it here."""
    if you == top["id"] or top["id"] in _builds_on(you):
        return "right"
    v = next((o["value"] for o in options if o["id"] == you), None)
    if v is None:
        return None
    return "right" if top["value"] - v < gap else "wrong"


def track(readers, raw, opitch, keys, tier=None):
    """What it would have said all through a fight: [[tick, their move, counter or None, how or None, your move or None, verdict or None], ...]."""
    raw = np.asarray(raw, np.float64)
    c = Counter(readers, tier)
    out = []
    for n in range(1, len(raw) + 1):
        if not due(n):
            continue
        h = c.step(raw, opitch, keys, n)
        if h["them"] is not None:
            k, y = h["counter"], h["you"]
            out.append([h["t"], h["them"]["name"], k["name"] if k else None, k["how"] if k else None, y["name"] if y else None, h["verdict"]])
    return out


assert set(HOW) <= set(TECHNIQUES)
