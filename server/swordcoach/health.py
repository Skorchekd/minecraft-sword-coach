# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""The other player's health on servers that hide it: worked out from the hits you landed.

A server that hides health leaves one number standing all fight. Starting from full, each hit on them takes off what a hit like it took off you in this same fight (you are in the same kit: a crit and a
plain hit each have their own figure), scaled by how charged your swing was, as the game scales it. If you won, they ended at nothing, so the hits are scaled to say so. It is an estimate: the pages say so.
"""
import numpy as np

from .fields import R

FULL = 20.0
# When a fight has too few hits on you to measure: what plain and crit hits usually take off (recorded fights).
PLAIN, CRIT = 0.8, 1.4
MIN_HITS = 3


def _rises(x):
    return np.r_[False, np.diff(x) > 0]


def is_hidden(raw):
    """The number never moved, though they were hit: nothing to read."""
    o = raw[:, R["ohp"]]
    return bool(_rises(raw[:, R["ohurt"]]).sum() >= MIN_HITS and np.ptp(o) < 1e-3)


def _crit(raw, c, p):
    """A hit crits if the swing came falling, not sprinting and fully charged: the game's own rule."""
    g = lambda n: raw[:, R[n]]
    if p == "s":
        full = g("scharge")[max(0, c - 1)] > 0.9
    else:
        full = True
    return bool(full and g(p + "ground")[c] < 0.5 and g(p + "sprint")[c] < 0.5 and g(p + "y")[c] < g(p + "y")[max(0, c - 1)])


def _swing_before(raw, h, name):
    s = raw[:, R[name]]
    for t in range(h, max(0, h - 7), -1):
        if s[t] > 0.5 and s[t - 1] < 0.5:
            return t
    return h


def damage_rates(raw):
    """What a plain hit and a crit took off you in this fight."""
    hurt = np.nonzero(_rises(raw[:, R["shurt"]]))[0]
    plain, crit = [], []
    hp = raw[:, R["shp"]]
    for h in hurt:
        lost = float(hp[max(0, h - 1)] - hp[h:h + 3].min())
        if lost <= 0:
            continue
        (crit if _crit(raw, _swing_before(raw, h, "oswing"), "o") else plain).append(lost)
    p = float(np.median(plain)) if len(plain) >= 2 else None
    c = float(np.median(crit)) if len(crit) >= 2 else None
    if p is None and c is None:
        return PLAIN, CRIT
    if p is None:
        return c * PLAIN / CRIT, c
    if c is None:
        return p, p * CRIT / PLAIN
    return p, max(c, p)


def estimate(raw, won=None):
    """[T] their health, from the hits you landed. won: the fight's result if known; a win ends them at nothing."""
    raw = np.asarray(raw, np.float64)
    T = len(raw)
    p, c = damage_rates(raw)
    hits = np.nonzero(_rises(raw[:, R["ohurt"]]))[0]
    dmg = np.zeros(T)
    for h in hits:
        s = _swing_before(raw, h, "sswing")
        ch = float(raw[max(0, s - 1), R["scharge"]])
        dmg[h] = (c if _crit(raw, s, "s") else p) * (0.2 + 0.8 * min(1.0, ch) ** 2) / 1.0
    total = dmg.sum()
    if won and total > 0:
        dmg *= FULL / total
    return np.maximum(0.0, FULL - np.cumsum(dmg))


def apply(raw, won=None):
    """raw with their health filled in where the server hides it, and whether it did."""
    raw = np.asarray(raw, np.float64)
    if not is_hidden(raw):
        return raw, False
    out = raw.copy()
    out[:, R["ohp"]] = estimate(raw, won)
    return out, True
