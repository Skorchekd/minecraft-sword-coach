# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""About you, kept on this computer: the tier you set on the Your data tab and whether the copilot names counters (data/profile.json), the per-install key
that turns player names into codes (server/.install_key, never shared) and an install id made from it, so bundles
from the same install can be put together without saying who made them."""
import hashlib
import hmac
import json
import os

from .fields import PLAYER_TIERS

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.path.join(SERVER_DIR, ".install_key")


def install_secret():
    try:
        with open(KEY, "rb") as fh:
            k = fh.read()
        if len(k) >= 32:
            return k
    except OSError:
        pass
    k = os.urandom(32)
    with open(KEY, "wb") as fh:
        fh.write(k)
    return k


def install_id(secret):
    """12 hex characters made from the install key: the same on every bundle from this install, and the key cannot be
    got back from it."""
    return hmac.new(secret, b"sword coach install id", hashlib.sha256).hexdigest()[:12]


def load(data_dir):
    try:
        with open(os.path.join(data_dir, "profile.json"), encoding="utf-8") as fh:
            p = json.load(fh)
    except (OSError, ValueError):
        return {"tier": None, "counters": True}
    return {"tier": p.get("tier") if p.get("tier") in PLAYER_TIERS else None, "counters": p.get("counters", True) is True}


def save(data_dir, body):
    cur = load(data_dir)
    if "tier" in body:
        cur["tier"] = body["tier"] if body["tier"] in PLAYER_TIERS else None
    if "counters" in body:
        cur["counters"] = body["counters"] is True
    path = os.path.join(data_dir, "profile.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(cur, fh, indent=1)
    os.replace(path + ".tmp", path)
    return cur


def tier_value(tier):
    """[strength 0..1 (HT1 = 1, LT5 = 0.1), known] for the answer model; [0, 0] when not set."""
    if tier not in PLAYER_TIERS:
        return [0.0, 0.0]
    return [1.0 - PLAYER_TIERS.index(tier) / len(PLAYER_TIERS), 1.0]
