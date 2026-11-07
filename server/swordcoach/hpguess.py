# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""Their health on servers that hide it, worked out live from nothing but the past.

Each hit you land takes off what a hit like it takes in this kit. A small tree model (models/hp_model.npz, the spot model's plain-array
format) says how much, from the hit's kind (crit, knockback, sweep, strong or weak: the attack sounds the server sent, or worked out from
how you moved), your charge, whether they were still invulnerable from the last hit, and what their hits have been taking off you this
fight (you wear the same kit, so that measures the armour). Without the model file the same is done by rule (health.py's figures). Their
health also comes back at the rate yours does when nobody is hit (some servers regenerate, most PvP ones do not).

`hidden(raw)` says when to use it: HIDDEN_AFTER hits landed and their health never moved (on servers that show it, a whole-number
display took up to 3 hits before it first moved, in 536 recorded fights)."""
import os

import numpy as np

from . import health
from .fields import R, SOUND_KINDS
from .review import hit_events
from .spot import TreeEnsemble

FULL = 20.0
KINDS = ["crit", "knockback", "sweep", "strong", "weak"]
FEATURES = ["crit", "knockback", "sweep", "strong", "weak", "kind_unknown", "kind_recorded", "your_charge", "their_hurt_before",
            "ticks_since_their_last_hurt", "you_falling", "you_sprinting", "taken_median", "taken_crit_median", "taken_plain_median",
            "taken_count"]
WINDOW = (-3, 1)        # ticks around their hurt where your attack sound belongs to this hit
HIDDEN_AFTER = 5        # hits landed with their health never moving before it counts as hidden


def _rises(x):
    return np.nonzero(np.r_[False, np.diff(x) > 0])[0]


def hidden(raw):
    """Their health never moved though HIDDEN_AFTER of your hits landed: the server hides it."""
    raw = np.asarray(raw, np.float64)
    landed = np.r_[False, np.diff(raw[:, R["ohurt"]]) > 0] & (raw[:, R["ohurt"]] >= 8)
    return bool(landed.sum() >= HIDDEN_AFTER and np.ptp(raw[:, R["ohp"]]) < 1e-3)


def taken(raw, before):
    """What their hits took off you before tick `before`: [(tick, HP lost, crit?)]."""
    hp = raw[:, R["shp"]]
    out = []
    for h in _rises(raw[:, R["shurt"]]):
        if h < 1 or h + 3 >= before:
            continue
        lost = float(hp[h - 1] - hp[h:h + 3].min())
        if lost > 0:
            out.append((int(h), lost, health._crit(raw, health._swing_before(raw, h, "oswing"), "o")))
    return out


def hit_rows(raw, ev=None, keys=None):
    """Every hit you landed: its tick and the features of FEATURES, from ticks up to it (and the two after, where its sound lands)."""
    raw = np.asarray(raw, np.float64)
    T = len(raw)
    sounds = hit_events(raw, ev, keys)["sounds"]
    by_tick = {}
    for t, at, k, rec in sounds:
        if at == 0:
            by_tick.setdefault(t, []).append((SOUND_KINDS[k], rec))
    hurt = raw[:, R["ohurt"]]
    hits = [h for h in _rises(hurt) if hurt[h] >= 8 and h >= 1]
    rows, last = [], -100
    for h in hits:
        found = [kr for t in range(h + WINDOW[0], min(T, h + WINDOW[1] + 1)) for kr in by_tick.get(t, [])]
        kinds = {k for k, _ in found}
        s = health._swing_before(raw, h, "sswing")
        tk = taken(raw, h)
        lost = [x[1] for x in tk]
        crit_l = [x[1] for x in tk if x[2]]
        plain_l = [x[1] for x in tk if not x[2]]
        med = lambda v: float(np.median(v)) if v else np.nan
        rows.append([float(k in kinds) for k in KINDS] + [float(not kinds), float(any(r for _, r in found)),
                     float(raw[max(0, s - 1), R["scharge"]]), float(hurt[h - 1]), float(min(100, h - last)),
                     float(raw[s, R["sground"]] < 0.5 and raw[s, R["sy"]] < raw[max(0, s - 1), R["sy"]]), float(raw[s, R["ssprint"]] > 0.5),
                     med(lost), med(crit_l), med(plain_l), float(len(lost))])
        last = h
    return np.array(hits, np.int64), np.array(rows, np.float64).reshape(-1, len(FEATURES))


def regen_rates(raw):
    """[T] your health coming back per tick when nobody was hit, averaged over the fight so far (0 where it never has): their health is taken
    to come back at the same rate (same server rules)."""
    hp = raw[:, R["shp"]]
    T = len(hp)
    d = np.r_[0.0, np.diff(hp)]
    quiet = np.ones(T, bool)
    for h in _rises(raw[:, R["shurt"]]):
        quiet[max(0, h - 1):h + 10] = False
    up = np.where(quiet & (d > 0) & (d < 2.5), d, 0.0)      # a jump bigger than that is food or a potion, not regeneration
    return np.cumsum(up) / np.maximum(1, np.cumsum(quiet))


class HpGuess:
    def __init__(self, models_dir):
        p = os.path.join(models_dir, "hp_model.npz")
        self.trees = TreeEnsemble(p) if os.path.exists(p) else None

    def damage(self, X):
        """HP each hit took off them."""
        if not len(X):
            return np.zeros(0)
        if self.trees is not None:
            return np.clip(self.trees.predict(X), 0.0, FULL)
        return rule_damage(X)

    def track(self, raw, ev=None, keys=None):
        """[T] their health worked out tick by tick from the past only: every hit you landed takes off what the model says from its own
        tick, and it comes back at the rate yours has, never past full."""
        raw = np.asarray(raw, np.float64)
        T = len(raw)
        hits, X = hit_rows(raw, ev, keys)
        d = np.zeros(T)
        d[hits] = self.damage(X)
        rate = regen_rates(raw)
        hp = np.empty(T)
        cur = FULL
        for t in range(T):
            cur = min(FULL, max(0.0, cur - d[t]) + rate[t])
            hp[t] = cur
        return hp


def fill(raw, est):
    """raw with their health from `est` where the server hid it (health.is_hidden), and whether it did. The estimate is used as it was
    worked out during the fight: stretching it to end at nothing after a win made it worse (.90 HP off vs .72 over 197 won fights: the
    record ends before their health shows 0, a median 1.0)."""
    raw = np.asarray(raw, np.float64)
    if est is None or len(est) != len(raw) or not health.is_hidden(raw):
        return raw, False
    e = np.asarray(est, np.float64)
    out = raw.copy()
    out[:, R["ohp"]] = np.clip(e, 0.0, FULL)
    return out, True


def rule_damage(X):
    """health.py's rule, causal: a crit takes what their crits took off you so far, other hits what their plain hits did (the usual figures
    until there are some), scaled by your charge as the game scales it."""
    F = {n: i for i, n in enumerate(FEATURES)}
    plain = np.where(np.isnan(X[:, F["taken_plain_median"]]), health.PLAIN, X[:, F["taken_plain_median"]])
    crit = np.where(np.isnan(X[:, F["taken_crit_median"]]), np.maximum(health.CRIT, plain * health.CRIT / health.PLAIN), X[:, F["taken_crit_median"]])
    base = np.where(X[:, F["crit"]] > 0.5, crit, plain)
    ch = np.clip(X[:, F["your_charge"]], 0.0, 1.0)
    return base * (0.2 + 0.8 * ch ** 2)
