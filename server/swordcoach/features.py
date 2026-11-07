# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""Model inputs computed from a fight's per-tick record (vectorised over the whole fight)."""
import numpy as np

from .fields import R, SEG

KEYN = 8
PRE = 4                        # ticks before an exchange the technique reader also sees
WIN = PRE + SEG
KEY_PAST, KEY_FUT = 4, 16      # key reader window around each tick


def wrap(a):
    return (np.asarray(a) + 180.0) % 360.0 - 180.0


def _diff(x):
    return np.r_[0.0, np.diff(x)] if len(x) else x


def _rise(x, thr=0.5):
    return np.r_[False, (x[1:] > thr) & (x[:-1] < thr)] if len(x) else np.zeros(0, bool)


def movement(raw, you):
    """[T, 10]: one player's movement relative to the other (you, or them as your client sees them)."""
    g = lambda n: raw[:, R[n]]
    dx, dz = g("ox") - g("sx"), g("oz") - g("sz")
    dist = np.maximum(1e-6, np.hypot(dx, dz))
    ux, uz = dx / dist, dz / dist
    p = "s" if you else "o"
    vx, vy, vz = _diff(g(p + "x")), _diff(g(p + "y")), _diff(g(p + "z"))
    sign = 1.0 if you else -1.0
    got, landed = np.r_[False, np.diff(g("shurt")) > 0], np.r_[False, np.diff(g("ohurt")) > 0]
    ground = g(p + "ground")
    jump = np.r_[False, (ground[:-1] > 0.5) & (ground[1:] < 0.5)] & (vy > 0)
    return np.stack([sign * (vx * ux + vz * uz) / 0.3, np.abs(-vx * uz + vz * ux) / 0.3, vy / 0.4, ground,
                     g(p + "sprint"), _rise(g(p + "swing")), got if you else landed,
                     landed if you else got, dist / 6.0, jump], 1)


def look(raw, opitch, you):
    """[T, 5]: sin/cos of the yaw off the other player, pitch / 90, yaw and pitch turn / 30."""
    g = lambda n: raw[:, R[n]]
    dx, dz = g("ox") - g("sx"), g("oz") - g("sz")
    if you:
        bearing = np.degrees(np.arctan2(dz, dx)) - 90.0
        yaw, pitch = g("syaw"), g("spitch")
    else:
        bearing = np.degrees(np.arctan2(-dz, -dx)) - 90.0
        yaw, pitch = g("oyaw"), np.asarray(opitch, np.float64).reshape(-1)
    off = np.radians(wrap(yaw - bearing))
    return np.stack([np.sin(off), np.cos(off), pitch / 90.0, wrap(_diff(yaw)) / 30.0, _diff(pitch) / 30.0], 1)


def own_keys(keys):
    """Your keys [T, >=8] -> [T, 8] with the jump as a press."""
    k = (np.asarray(keys)[:, :8] > 0.5).astype(np.float64)
    k[:, 4] = np.r_[k[:1, 4], (k[1:, 4] > 0.5) & (k[:-1, 4] < 0.5)]
    return k


def key_frames(raw, opitch):
    """Key reader inputs per tick: how the other player moved in their own facing, turns, flags, ping, hurt."""
    g = lambda n: raw[:, R[n]]
    yaw = np.radians(g("oyaw"))
    dx, dy, dz = _diff(g("ox")), _diff(g("oy")), _diff(g("oz"))
    fwd = -dx * np.sin(yaw) + dz * np.cos(yaw)
    left = dx * np.cos(yaw) + dz * np.sin(yaw)
    moved = (np.abs(dx) + np.abs(dy) + np.abs(dz) > 1e-7).astype(np.float64)
    oh = g("ohurt")
    cols = [fwd * 4, left * 4, dy * 2, wrap(_diff(g("oyaw"))) / 30.0, _diff(np.asarray(opitch, np.float64).reshape(-1)) / 30.0,
            g("oground"), g("osprint"), g("osneak"), moved, g("ping_o") / 200.0, oh / 10.0,
            np.r_[0.0, np.diff(oh) > 0], _rise(g("sswing")).astype(np.float64), _rise(g("oswing")).astype(np.float64),
            np.hypot(g("ox") - g("sx"), g("oz") - g("sz")) / 6.0]
    return np.stack(cols, 1)


def key_windows(frames):
    T = len(frames)
    pad = np.vstack([np.repeat(frames[:1], KEY_PAST, 0), frames, np.repeat(frames[-1:], KEY_FUT, 0)])
    idx = np.arange(T)[:, None] + np.arange(KEY_PAST + KEY_FUT + 1)[None, :]
    return pad[idx].reshape(T, -1).astype(np.float32)


def view(raw, opitch, keys8, you):
    """[T, 23] for one player: movement, look, keys (exact for you, read for them)."""
    return np.concatenate([movement(raw, you), look(raw, opitch, you), keys8], 1).astype(np.float32)


def exchange_windows(F, starts, pre=PRE, post=0):
    """[len(starts), pre + 12 + post, 23]: the ticks before each exchange, its 12 ticks and the ticks after (how far each way depends on the reader; a W-tap's second press can land after the exchange)."""
    T = len(F)
    pad = np.vstack([np.zeros((pre, F.shape[1]), np.float32), F, np.zeros((SEG + post, F.shape[1]), np.float32)])
    idx = np.asarray(starts)[:, None] + np.arange(pre + SEG + post)[None, :]
    X = pad[np.clip(idx, 0, T + pre + SEG + post - 1)]
    return np.nan_to_num(X).clip(-10, 10).astype(np.float32)
