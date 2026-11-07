# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""What an exchange usually trades from where it starts, learned from real recorded fights: a gradient-boosted
tree ensemble stored as plain arrays (models/spot_value.npz), evaluated here with numpy."""
import numpy as np

from .fields import R

FEATURES = ["your_hp", "their_hp", "hp_lead", "distance", "height_diff", "closing_speed", "your_approach",
            "your_sideways", "their_approach", "their_sideways", "your_charge", "their_charge", "your_hurt",
            "their_hurt", "your_immunity", "your_ground", "their_ground", "your_sprint", "their_sprint", "their_sneak",
            "your_vertical", "their_vertical", "your_aim_off", "their_aim_off", "your_ping", "their_ping",
            "landed_recent", "taken_recent", "dealt_recent", "lost_recent", "your_swings_recent", "their_swings_recent"]
HISTORY = 24


def _rise(x):
    return np.r_[False, (x[1:] > 0.5) & (x[:-1] < 0.5)]


def _up(x):
    return np.r_[False, np.diff(x) > 0]


def spot_features(raw, starts):
    """[len(starts), 32] describing the tick before each exchange starts, and the second before it."""
    raw = np.asarray(raw, np.float64)
    T = len(raw)
    g = lambda n: raw[:, R[n]]
    i = np.clip(np.asarray(starts) - 1, 1, T - 1)
    dx, dz = g("ox") - g("sx"), g("oz") - g("sz")
    dist = np.hypot(dx, dz)
    ux, uz = dx / np.maximum(dist, 1e-6), dz / np.maximum(dist, 1e-6)
    v = lambda p: (np.r_[0.0, np.diff(g(p + "x"))], np.r_[0.0, np.diff(g(p + "y"))], np.r_[0.0, np.diff(g(p + "z"))])
    svx, svy, svz = v("s")
    ovx, ovy, ovz = v("o")
    osw = _rise(g("oswing"))
    since = np.zeros(T)
    c = 30.0
    for t in range(T):
        c = 0.0 if osw[t] else min(30.0, c + 1.0)
        since[t] = c
    bearing = np.degrees(np.arctan2(dz, dx)) - 90.0
    wrap = lambda a: (a + 180.0) % 360.0 - 180.0
    landed, taken = _up(g("ohurt")) & (g("ohurt") >= 8), _up(g("shurt")) & (g("shurt") >= 8)
    sswing = _rise(g("sswing"))
    cum = lambda x: np.r_[0.0, np.cumsum(x)]
    cl, ct, cs, co = cum(landed), cum(taken), cum(sswing), cum(osw)
    dealt = np.maximum(0.0, -np.r_[0.0, np.diff(g("ohp"))])
    lost = np.maximum(0.0, -np.r_[0.0, np.diff(g("shp"))])
    cd, cls = cum(dealt), cum(lost)
    j = np.maximum(0, i - HISTORY)
    win = lambda cc: cc[i + 1] - cc[j + 1]
    F = np.stack([
        g("shp")[i] / 20, g("ohp")[i] / 20, (g("shp")[i] - g("ohp")[i]) / 20, dist[i] / 6, g("oy")[i] - g("sy")[i],
        (dist[np.maximum(0, i - 2)] - dist[i]) / 2,
        svx[i] * ux[i] + svz[i] * uz[i], np.abs(-svx[i] * uz[i] + svz[i] * ux[i]),
        -(ovx[i] * ux[i] + ovz[i] * uz[i]), np.abs(-ovx[i] * uz[i] + ovz[i] * ux[i]),
        g("scharge")[i], np.minimum(1.2, since[i] / 12.5), g("shurt")[i] / 10, g("ohurt")[i] / 10, g("sinv")[i] / 20,
        g("sground")[i], g("oground")[i], g("ssprint")[i], g("osprint")[i], g("osneak")[i], svy[i], ovy[i],
        np.abs(wrap(g("syaw")[i] - bearing[i])) / 180, np.abs(wrap(g("oyaw")[i] - (bearing[i] + 180))) / 180,
        g("ping_s")[i] / 200, g("ping_o")[i] / 200,
        win(cl), win(ct), win(cd) / 20, win(cls) / 20, win(cs), win(co)], 1)
    return np.nan_to_num(F).astype(np.float64)


class TreeEnsemble:
    """Sum of regression trees: per node feature, threshold, left, right, value, leaf flag, missing-goes-left."""

    def __init__(self, path):
        z = np.load(path)
        self.base = float(z["base"])
        self.feat, self.thr = z["feature"], z["threshold"]
        self.left, self.right = z["left"], z["right"]
        self.value, self.leaf, self.miss_left = z["value"], z["leaf"].astype(bool), z["missing_left"].astype(bool)
        self.roots = z["roots"]
        self.sd = float(z["residual_sd"])

    def predict(self, X):
        X = np.asarray(X, np.float64)
        out = np.full(len(X), self.base)
        for r in self.roots:
            node = np.full(len(X), r)
            active = ~self.leaf[node]
            while active.any():
                n = node[active]
                x = X[active, self.feat[n]]
                go_left = np.where(np.isnan(x), self.miss_left[n], x <= self.thr[n])
                node[active] = np.where(go_left, self.left[n], self.right[n])
                active = ~self.leaf[node]
            out += self.value[node]
        return out
