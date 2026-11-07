# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""The fight copilot: what to do next, redrawn every few ticks from what you and the opponent really do. A small model (models/guide_model.onnx)
says when a click should pay and which way to strafe, and reach decides the plan: go in when far or charged at the edge of reach, strafe at reach, let go of W when they come down on you or after a hit, meet a rush if you are charged. Advice starts a few ticks ahead, so there is time to act on it.

It also reads the style of both players so far in a fight (style_features), for the replay notes."""
import json

import numpy as np

from .fields import R
from .review import _up
from .spot import spot_features

MOVES = ["toward", "away", "left", "right", "hold"]
N_ACT = len(MOVES) * 2
EVERY = 3                # ticks between new advice
HOLD_SIDE = 12           # a strafe side stays up at least this long
HOLD_CLICK = 6
PRESS_HOLD, PRESS_AGAIN = 6, 18   # ticks: how long to let go of W, and how soon it can come up again
HOLD_PLAN = 15           # going in, or backing off, stays up at least this long
SMOOTH = 0.3
STYLE = ["their_aim", "their_aim_me_left", "their_aim_me_right", "their_swing_rate", "their_hit_rate", "their_jump", "their_sprint", "their_left", "their_right",
         "my_aim", "my_aim_them_left", "my_aim_them_right", "my_click_charge", "my_early_click", "my_hit_rate", "my_left", "my_right"]
SIGNED = ["my_yaw_err", "their_yaw_err", "my_side", "their_side", "my_turn", "their_turn"]
SPOT_N = 32
SWAP = [(SPOT_N + STYLE.index(a), SPOT_N + STYLE.index(b)) for a, b in (("their_aim_me_left", "their_aim_me_right"), ("their_left", "their_right"), ("my_aim_them_left", "my_aim_them_right"), ("my_left", "my_right"))]
NEGATE = list(range(SPOT_N + len(STYLE), SPOT_N + len(STYLE) + len(SIGNED)))
ACT_SWAP = np.arange(N_ACT)
for _c in (0, 1):
    ACT_SWAP[2 * 2 + _c], ACT_SWAP[3 * 2 + _c] = 3 * 2 + _c, 2 * 2 + _c


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def motion(raw):
    """Per tick: distance, both aim errors, each player's sideways motion across the line between them (+ their own right)."""
    g = lambda n: raw[:, R[n]]
    dx, dz = g("ox") - g("sx"), g("oz") - g("sz")
    d = np.maximum(np.hypot(dx, dz), 1e-3)
    my_err = np.abs(wrap(np.degrees(np.arctan2(-dx, dz)) - g("syaw")))
    their_err = np.abs(wrap(np.degrees(np.arctan2(dx, -dz)) - g("oyaw")))
    rx, rz = dz / d, -dx / d
    my_side = np.r_[0.0, np.diff(g("sx")) * -rx[1:] + np.diff(g("sz")) * -rz[1:]]
    their_side = np.r_[0.0, np.diff(g("ox")) * rx[1:] + np.diff(g("oz")) * rz[1:]]
    return d, my_err, their_err, my_side, their_side


def style_features(raw, keys, ts):
    """The two players as read so far this fight, nothing after t, pulled toward a neutral value until there is evidence."""
    g = lambda n: raw[:, R[n]]
    d, my_err, their_err, my_side, their_side = motion(raw)
    near = d < 5.0
    moving = 0.05
    sw_o = np.r_[False, (g("oswing")[1:] > 0.5) & (g("oswing")[:-1] < 0.5)]
    hit_o, hit_s = _up(g("shurt")), _up(g("ohurt"))
    click = keys[:, 7] > 0.5
    charge = np.r_[1.0, g("scharge")[:-1]]
    jump_o = np.r_[False, (g("oground")[1:] < 0.5) & (g("oground")[:-1] > 0.5)]
    cum = lambda x: np.r_[0.0, np.cumsum(x, dtype=np.float64)]
    mean = lambda v, m, prior, k=40.0: (cum(v * m) + prior * k) / (cum(m) + k)
    S = np.stack([
        mean(their_err, near, 15.0), mean(their_err, near & (my_side < -moving), 15.0), mean(their_err, near & (my_side > moving), 15.0),
        (cum(sw_o) + 1.5) / (cum(near) / 20.0 + 1.0), (cum(hit_o) + 1.0) / (cum(sw_o) + 2.0), mean(jump_o.astype(float), near, 0.04), mean(g("osprint"), near, 0.6),
        mean(their_side < -moving, near, 0.15), mean(their_side > moving, near, 0.15),
        mean(my_err, near, 15.0), mean(my_err, near & (their_side < -moving), 15.0), mean(my_err, near & (their_side > moving), 15.0),
        (cum(charge * click) + 1.8) / (cum(click) + 2.0), (cum((charge < 0.9) & click) + 0.2) / (cum(click) + 2.0), (cum(hit_s) + 1.0) / (cum(click) + 2.0),
        mean(my_side < -moving, near, 0.15), mean(my_side > moving, near, 0.15)], 1)
    return S[np.asarray(ts)].astype(np.float32)


def signed_features(raw, ts):
    """Which way everything is leaning at this moment: the side of the crosshair each player has the other on, how each moves across the line, how each is turning."""
    g = lambda n: raw[:, R[n]]
    dx, dz = g("ox") - g("sx"), g("oz") - g("sz")
    me = wrap(np.degrees(np.arctan2(-dx, dz)) - g("syaw"))
    them = wrap(np.degrees(np.arctan2(dx, -dz)) - g("oyaw"))
    _, _, _, ms, os_ = motion(raw)
    smooth = lambda v: np.convolve(v, np.ones(5) / 5, "full")[:len(v)]
    turn = lambda n: smooth(np.r_[0.0, wrap(np.diff(g(n)))])
    S = np.stack([me / 90, them / 90, smooth(ms) / 0.3, smooth(os_) / 0.3, turn("syaw") / 10, turn("oyaw") / 10], 1)
    return np.clip(S[np.asarray(ts)], -3, 3).astype(np.float32)


def mirror(X):
    """The same moment seen in a mirror: the game has no left or right, so the advice must not either."""
    Z = X.copy()
    for a, b in SWAP:
        Z[:, a], Z[:, b] = X[:, b], X[:, a]
    Z[:, NEGATE] = -X[:, NEGATE]
    return Z


def features(raw, keys, ts):
    return np.concatenate([spot_features(raw, ts), style_features(raw, keys, ts), signed_features(raw, ts)], 1).astype(np.float32)


class GuideModel:
    def __init__(self, session):
        self.s = session
        meta = session.get_modelmeta().custom_metadata_map
        self.click_bar = float(meta.get("click_bar", 0.0))
        self.norms = json.loads(meta["norms"]) if meta.get("norms") else None

    def values(self, X):
        """Per net of the ensemble, seen and mirrored: trade [n_nets, n, N_ACT], their aim, hits taken; how often each action is used [n, N_ACT]."""
        X = np.asarray(X, np.float32)
        q, a, h, p = self.s.run(None, {"x": X})
        qm, am, hm, pm = self.s.run(None, {"x": mirror(X)})
        Q = (q + qm[..., ACT_SWAP]) / 2
        A = (a + am[..., ACT_SWAP]) / 2
        H = (h + hm[..., ACT_SWAP]) / 2
        P = (p + pm[..., ACT_SWAP]) / 2
        return Q, A, H, P.mean(0)


class Live:
    """One fight's advice, moment by moment, from nothing but the past. The same code scores it on old fights and drives the screen."""

    def __init__(self, model):
        self.model = model
        self.q = None
        self.side, self.since = None, 0
        self.move, self.move_since = None, 0
        self.press_at = -999
        self.click_sm = None
        self.click_until = -1
        self.last_t = None

    def step(self, t, x, vals=None):
        """t a tick, x the moment's features, vals its model values if already run. {"move", "click", "cue", "side"}"""
        Q, A, H, P = self.model.values(x[None]) if vals is None else vals
        P_ = P[0]
        pm = P_[0::2] + P_[1::2]
        marg = lambda v: (P_[0::2] * v[..., 0::2] + P_[1::2] * v[..., 1::2]) / np.maximum(pm, 1e-6)
        E = marg(A[:, 0]) - marg(H[:, 0])
        lcb = E.mean(0) - E.std(0)
        fresh = self.last_t is None or t - self.last_t != EVERY
        self.last_t = t
        self.q = lcb.copy() if fresh or self.q is None else SMOOTH * lcb + (1 - SMOOTH) * self.q
        sides = {2: self.q[2], 3: self.q[3]}
        best = max(sides, key=sides.get)
        if self.side is None or fresh:
            self.side, self.since = best, t
        elif best != self.side and t - self.since >= HOLD_SIDE and sides[best] - sides[self.side] >= 0.05:
            self.side, self.since = best, t
        # Reach decides the plan; the model picks the side. Strafing is the default: it is what makes you hard to hit. Measured on real fights: when they are coming down on you, have
        # just hit you or are farming you, backing off gives away HP and letting go of W pays; when they rush you, meet them if you are charged and wait if you are not.
        dist, charge = float(x[3]) * 6.0, float(x[10])
        hit = float(x[13]) >= 0.7        # you hit them in the last few ticks
        rush, hurt, airborne, falling, hits_on_you = float(x[8]), float(x[12]), float(x[16]) < 0.5, float(x[21]) < -0.05, float(x[27])
        pressed = hurt >= 0.7 or (airborne and falling and dist < 4.0) or (hits_on_you >= 2 and dist < 3.5)
        rushed = rush > 0.2 and dist < 6.0
        cue = None
        urgent = True
        # A quick release, then get moving: when they come at you it is the first few ticks that are the trade, and strafing after it is what makes them miss.
        if pressed and t - self.press_at >= PRESS_AGAIN:
            self.press_at = t
        if pressed and t - self.press_at < PRESS_HOLD:
            want, cue = 4, "Let go of W"
        elif pressed:
            want = self.side
        elif rushed:
            want, cue = (0, None) if charge >= 0.8 else (4, "Wait for them")
        elif dist < 1.4:
            want, cue = 1, "Too close"
        else:
            urgent = False
            want = 0 if dist >= 4.5 or (dist >= 3.6 and charge >= 0.8) else self.side
        # A plan stays up long enough to read, unless the fight has just changed.
        if self.move is None or fresh or urgent or (want == self.side and self.move in (2, 3)) or t - self.move_since >= HOLD_PLAN:
            if want != self.move:
                self.move_since = t
            self.move = want
        elif self.move == 4 and cue is None:
            cue = "Let go of W"
        move = self.move
        if hit and dist < 4.0:
            cue = "W-tap"
        # When a click should pay: only what the click part of the model says, smoothed and held long enough to see.
        Qm, Qs = Q[:, 0].mean(0), Q[:, 0].std(0)
        pc = np.array([P_[0::2].sum(), P_[1::2].sum()])
        qc = np.array([(P_[0::2] * Qm[0::2]).sum() / max(pc[0], 1e-6), (P_[1::2] * Qm[1::2]).sum() / max(pc[1], 1e-6)])
        adv = qc[1] - qc[0] - Qs[1::2].mean()
        self.click_sm = adv if fresh or self.click_sm is None else SMOOTH * adv + (1 - SMOOTH) * self.click_sm
        if self.click_sm >= self.model.click_bar:
            self.click_until = t + HOLD_CLICK
        return {"move": MOVES[move], "click": bool(t < self.click_until), "cue": cue, "side": MOVES[self.side]}


def track(model, raw, keys):
    """What the copilot would have said all through a fight, for the replays: [[tick, move, click, cue], ...]."""
    raw, keys = np.asarray(raw, np.float64), np.asarray(keys, np.float64)
    d = motion(raw)[0]
    ts = np.array([t for t in range(20, len(raw), EVERY) if d[t] < 8.0])
    if not len(ts):
        return []
    X, live, out = features(raw, keys, ts), Live(model), []
    Q, A, H, P = model.values(X)
    for i, (t, x) in enumerate(zip(ts, X)):
        h = live.step(int(t), x, (Q[:, i:i + 1], A[:, i:i + 1], H[:, i:i + 1], P[i:i + 1]))
        out.append([int(t), h["move"], h["click"], h["cue"]])
    return out


def steered(raw, keys, t, lead=5, n=8):
    """Which way the player steered just after t, from the keys, relative to the opponent."""
    a, b = t + lead, min(len(raw), t + lead + n)
    if b <= a:
        return None
    yaw = np.radians(raw[a:b, R["syaw"]])
    fwd, side = keys[a:b, 0] - keys[a:b, 1], keys[a:b, 3] - keys[a:b, 2]
    vx, vz = fwd * -np.sin(yaw) + side * -np.cos(yaw), fwd * np.cos(yaw) + side * -np.sin(yaw)
    dx, dz = raw[a:b, R["ox"]] - raw[a:b, R["sx"]], raw[a:b, R["oz"]] - raw[a:b, R["sz"]]
    dn = np.maximum(np.hypot(dx, dz), 1e-3)
    along, across = float(np.mean((vx * dx + vz * dz) / dn)), float(np.mean((vx * dz - vz * dx) / dn))
    if max(abs(along), abs(across)) < 0.3:
        return "hold"
    if abs(along) >= abs(across):
        return "toward" if along > 0 else "away"
    return "right" if across > 0 else "left"


def _band(v, q):
    return "low" if v <= q[0] else "high" if v >= q[2] else "mid"


def notes(style, norms):
    """A fight's or a player's style, in words, against where people's numbers usually sit. Only what a person can act on, and each number beside the note."""
    if norms is None:
        return []
    s = dict(zip(STYLE, map(float, style)))
    out = []
    def note(kind, text, value):
        out.append({"kind": kind, "text": text, "value": value})
    if _band(s["my_early_click"], norms["my_early_click"]) == "high":
        note("clicks", "You click before your sword is charged more than most players. Wait for the crosshair ring to fill.", f'{s["my_early_click"] * 100:.0f}% of clicks early')
    elif _band(s["my_click_charge"], norms["my_click_charge"]) == "low":
        note("clicks", "Your clicks land at lower charge than most players'.", f'{s["my_click_charge"] * 100:.0f}% charge')
    if _band(s["my_hit_rate"], norms["my_hit_rate"]) == "low":
        note("clicks", "Fewer of your swings connect than most players'. Swing when you are in reach and on them.", f'{s["my_hit_rate"] * 100:.0f}% of swings hit')
    strafe, usual = s["my_left"] + s["my_right"], norms["my_left"][1] + norms["my_right"][1]
    if strafe < usual * 0.7:
        note("strafe", "You strafe less than most players, which makes you easy to track. Strafing moved opponents' aim off you in the recorded fights.", f'{strafe * 100:.0f}% of the time, most players {usual * 100:.0f}%')
    if strafe > 0.05 and max(s["my_left"], s["my_right"]) > 2.5 * min(s["my_left"], s["my_right"]):
        side = "right" if s["my_right"] > s["my_left"] else "left"
        note("strafe", f"You mostly strafe {side}. Mixing sides makes you harder to read.", f'left {s["my_left"] * 100:.0f}%, right {s["my_right"] * 100:.0f}%')
    if _band(s["my_aim"], norms["my_aim"]) == "high":
        note("aim", "Your crosshair sits further off them than most players'.", f'{s["my_aim"]:.0f} degrees off on average')
    return out


def opponent_notes(style, norms):
    """What to expect from someone, read over several fights against them."""
    if norms is None:
        return []
    s = dict(zip(STYLE, map(float, style)))
    out = []
    if _band(s["their_jump"], norms["their_jump"]) == "high":
        out.append({"kind": "them", "text": "They jump more than most players.", "value": f'{s["their_jump"] * 100:.0f}% of ticks up close start a jump'})
    if strafe_side := ("right" if s["their_right"] > 2 * s["their_left"] else "left" if s["their_left"] > 2 * s["their_right"] else None):
        out.append({"kind": "them", "text": f"They mostly strafe {strafe_side}.", "value": f'left {s["their_left"] * 100:.0f}%, right {s["their_right"] * 100:.0f}%'})
    if _band(s["their_aim"], norms["their_aim"]) == "high":
        out.append({"kind": "them", "text": "Their aim stays further off you than most players'. Moving keeps it that way.", "value": f'{s["their_aim"]:.0f} degrees off on average'})
    return out
