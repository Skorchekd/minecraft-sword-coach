# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""One fight's review: both players' techniques per exchange (the readers), what really happened (hits, crits,
swings), what an exchange from the same spot usually trades in real fights, your relabels and declared techniques,
and your timing."""
import numpy as np

from .fields import EV_CRIT_ON, FAMILY, LABELS, R, REQUIRES, SEG, SHORT, SOUND_KINDS, TECHNIQUES, TIER, TIER_NAMES
from .spot import spot_features

CRIT, KNOCKBACK, STRONG, WEAK, SWEEP = (SOUND_KINDS.index(k) for k in ("crit", "knockback", "strong", "weak", "sweep"))


def _rise(x):
    return np.r_[False, (x[1:] > 0.5) & (x[:-1] < 0.5)]


def _up(x):
    return np.r_[False, np.diff(x) > 0] & (np.asarray(x) >= 8)


def tech(t, p=None):
    name = TECHNIQUES[t]
    out = {"t": int(t), "id": name, "name": LABELS[name], "short": SHORT[name], "tier": TIER_NAMES[TIER[name]],
           "family": FAMILY[name]}
    if p is not None:
        out["p"] = round(float(p), 3)
    return out


ALSO_AT = 0.5    # how likely a second technique has to be on its own to be named next to the first


def _builds_on(t, seen=None):
    """Everything technique t builds on (fields.REQUIRES, all the way down)."""
    seen = set() if seen is None else seen
    for r in REQUIRES[t]:
        if r not in seen:
            seen.add(r)
            _builds_on(r, seen)
    return seen


def read_choice(P, M=None):
    """What the reader says about one side of an exchange. With M (each technique on its own), every technique likely
    enough is named: a hit select made while sprinting is both, and the more specific one goes first."""
    o = np.argsort(-P)
    if M is None:
        return dict(tech(o[0], P[o[0]]), alt=[tech(k, P[k]) for k in o[1:3] if P[k] >= 0.1], also=[])
    sure = [int(k) for k in np.argsort(-M) if M[k] >= ALSO_AT]
    first = int(o[0])
    for k in sure:
        if TECHNIQUES[first] in _builds_on(TECHNIQUES[k]):
            first = k
    p = float(M[first]) if M[first] >= ALSO_AT else float(P[first])
    also = [tech(k, M[k]) for k in sure if k != first][:3]
    return dict(tech(first, p), alt=[tech(k, P[k]) for k in o[:3] if k != first and P[k] >= 0.1 and k not in sure][:2], also=also)


def trade(raw, a, n):
    e = min(len(raw), a + n)
    if e <= a:
        return 0.0, 0.0
    dealt = max(0.0, raw[a - 1, R["ohp"]] - raw[a:e, R["ohp"]].min())
    taken = max(0.0, raw[a - 1, R["shp"]] - raw[a:e, R["shp"]].min())
    return float(dealt), float(taken)


def _swings(raw, keys, side):
    """Ticks where a side swung: your attack clicks (or swing starts without key data), their swing starts."""
    if side == 0:
        return (keys[:, 7] > 0.5) if keys is not None else _rise(raw[:, R["sswing"]])
    return _rise(raw[:, R["oswing"]])


def _inferred_kinds(raw, keys, h, by):
    """The attack sounds a hit at tick h most likely played, from how the attacker was moving when they swung (older
    fights, which have no recorded sounds). The server's rules: a charged hit while sprinting knocks back, a charged
    hit while falling and not sprinting crits, a charged hit standing still on the ground sweeps; otherwise it is a
    strong or weak hit by charge. Your charge is known; theirs is taken as full."""
    g = lambda n: raw[:, R[n]]
    p = "s" if by == 0 else "o"
    lo = max(1, h - 8)
    sw = np.nonzero(_swings(raw, keys, by)[lo:h + 1])[0]
    c = max(2, lo + int(sw[-1])) if len(sw) else max(2, h - 1)
    full = g("scharge")[c - 1] > 0.9 if by == 0 else True
    sprint, ground = g(p + "sprint")[c] > 0.5, g(p + "ground")[c] > 0.5
    falling = not ground and g(p + "y")[c] < g(p + "y")[c - 1]
    speed = float(np.hypot(g(p + "x")[c] - g(p + "x")[c - 1], g(p + "z")[c] - g(p + "z")[c - 1]))
    if not full:
        return [WEAK], False
    if sprint:
        return [KNOCKBACK, STRONG], False
    if falling:
        return [CRIT], True
    if ground and speed < 0.25:
        return [SWEEP], False
    return [STRONG], False


def hit_events(raw, ev=None, keys=None):
    """The fight's attack sounds and crits per tick, for the clips and replays.

    sounds: [tick, at (0 you, 1 them: who attacked), kind (SOUND_KINDS index), recorded (1) or worked out (0)]
    crits:  [tick, on (0 you, 1 them: who was crit), recorded (1) or worked out (0)]
    Recorded ones are what the server itself sent (fights from mod 1.1.0 on). A hit (their hurt going up) with no
    attack sound recorded near it gets the sounds it most likely played, so older fights and servers that send no
    attack sounds still sound right; those are marked as worked out."""
    g = lambda n: raw[:, R[n]]
    sounds, crits = [], []
    if ev is not None:
        ev = np.asarray(ev, np.int64)
        for t in np.nonzero(ev)[0]:
            b = int(ev[t])
            for at in (0, 1):
                for k in range(len(SOUND_KINDS)):
                    if b >> (6 * at + k) & 1:
                        sounds.append([int(t), at, k, 1])
            for on in (0, 1):
                if b >> (EV_CRIT_ON + on) & 1:
                    crits.append([int(t), on, 1])
    for on, hurt in ((0, "shurt"), (1, "ohurt")):
        by = 1 - on
        for h in np.nonzero(_up(g(hurt)))[0]:
            if h < 3 or any(x[1] == by and h - 3 <= x[0] <= h + 1 for x in sounds):
                continue
            kinds, crit = _inferred_kinds(raw, keys, int(h), by)
            if any(x[1] == on and h - 3 <= x[0] <= h + 1 for x in crits):
                kinds, crit = [CRIT], False      # the crit itself was recorded
            elif ev is not None and crit:
                kinds, crit = [STRONG], False    # recorded, and the server sent no crit for it
            sounds += [[int(h), by, k, 0] for k in kinds]
            if crit:
                crits.append([int(h), on, 0])
    sounds.sort()
    crits.sort()
    return {"sounds": sounds, "crits": crits, "recorded": ev is not None}


SUGGEST_GAP = 0.5      # a card names a better answer only when the answer used sits this far under the top one
LATER_BLOCKS = 5       # how far a "won it back" line looks, in blocks of 1.2 s


def later_net(raw, a):
    """Dealt minus taken from this exchange on, over about 6 s or to the fight's end."""
    return sum(d - t for d, t in (trade(raw, a + 2 * SEG * i, 2 * SEG) for i in range(LATER_BLOCKS)))


def suggestion(e):
    """The answer to name for this exchange, or None: no card, a run of crits on you (no shown edge there), your answer too rare to compare, or no clear gap."""
    A = e.get("answers")
    if not A or A.get("farmed"):
        return None
    mine = chosen(e, "you")
    me = next((o for o in A["options"] if o["id"] == mine), None)
    top = A["options"][0]
    if me is None or top["id"] == mine or top["value"] - me["value"] < SUGGEST_GAP:
        return None
    return {"id": top["id"], "name": top["name"]}


def exchange_hits(raw, keys, starts, crits):
    """Per exchange and side: swings, hits landed, crits landed (ticks a .. a + 12), and the tick of the first swing and hit in it (None if none)."""
    sw = [_swings(raw, keys, 0), _swings(raw, keys, 1)]
    landed = [_up(raw[:, R["ohurt"]]), _up(raw[:, R["shurt"]])]
    first = lambda on: next((int(t) for t in np.nonzero(on)[0]), None)
    out = []
    for a in starts:
        b = a + SEG
        out.append({name: {"swings": int(sw[side][a:b].sum()), "landed": int(landed[side][a:b].sum()),
                           "crits": sum(1 for c in crits if c[1] == 1 - side and a <= c[0] < b),
                           "first_swing": first(sw[side][a:b]), "first_hit": first(landed[side][a:b])}
                    for side, name in ((0, "you"), (1, "them"))})
    return out


def timing(raw, keys, crits=None):
    """Your own measurements this fight (no comparison data: compare fights on the page)."""
    g = lambda n: raw[:, R[n]]
    T = len(raw)
    dist = np.hypot(g("ox") - g("sx"), g("oz") - g("sz"))
    clicks = (keys[:, 7] > 0.5) if keys is not None else _rise(g("sswing"))
    out = {}
    ready = (g("scharge") >= 0.95) & (dist < 3.0)
    delays, t = [], 1
    while t < T:
        if ready[t] and not ready[t - 1]:
            u = t
            while u < min(T, t + 30) and not clicks[u]:
                u += 1
            if u < min(T, t + 30):
                delays.append(u - t)
            t = u + 1
        else:
            t += 1
    if len(delays) >= 3:
        out["swing_delay"] = dict(median=float(np.median(delays)), n=len(delays),
                                  text="ticks from charged and in reach to your click")
    landed = _up(g("ohurt"))
    sw = np.nonzero(clicks & (dist < 3.6))[0]
    if len(sw) >= 3:
        hit = [bool(landed[s:s + 4].any()) for s in sw]
        out["hits_per_swing"] = dict(value=round(float(np.mean(hit)), 3), n=len(sw), text="your swings within 3.6 blocks that landed")
        hd = [dist[s] for s, h in zip(sw, hit) if h]
        if hd:
            out["hit_distance"] = dict(median=round(float(np.median(hd)), 2), n=len(hd), text="blocks between you when your hits landed")
    if keys is not None:
        B, F, J = keys[:, 1] > 0.5, keys[:, 0] > 0.5, keys[:, 4] > 0.5
        holds, rel = [], []
        for c in np.nonzero(clicks)[0]:
            s0 = next((u for u in range(c, min(T, c + 7)) if B[u]), None)
            if s0 is not None:
                n = 0
                while s0 + n < T and B[s0 + n] and n < 12:
                    n += 1
                holds.append(n)
            r0 = next((u for u in range(c, min(T, c + 7)) if not F[u]), None)
            if r0 is not None and F[max(0, c - 1)]:
                n = 0
                while r0 + n < T and not F[r0 + n] and n < 12:
                    n += 1
                if n <= 8:
                    rel.append(n)
        if len(holds) >= 3:
            out["s_hold"] = dict(median=float(np.median(holds)), n=len(holds), text="ticks you held S after a click")
        if len(rel) >= 3:
            out["w_release"] = dict(median=float(np.median(rel)), n=len(rel), text="ticks you let go of W after a click")
        presses = np.nonzero(J & ~np.r_[False, J[:-1]])[0]
        offs = []
        for h in np.nonzero(_up(g("shurt")))[0]:
            near = [p - h for p in presses if -2 <= p - h <= 4]
            if near:
                offs.append(min(near, key=abs))
        if len(offs) >= 3:
            out["reset_timing"] = dict(on_tick=round(float(np.mean([o in (-1, 0) for o in offs])), 3), n=len(offs),
                                       median=float(np.median(offs)),
                                       text="jump presses near their hits: share on the tick the hit landed (or one before)")
    if crits is not None:
        crit_hits = [c for c in crits if c[1] == 1]
    else:
        crit_hits = [h for h in np.nonzero(landed)[0] if h >= 2 and g("sground")[h - 1] < 0.5 and g("sy")[h - 1] < g("sy")[h - 2]
                     and g("ssprint")[h - 1] < 0.5]
    nl = int(landed.sum())
    if nl >= 3:
        out["crit_share"] = dict(value=round(len(crit_hits) / nl, 3), n=nl, text="your hits that landed falling and unsprinted (crits)")
    return out


def build(info, arrays, readers, labels=None, tier=None):
    # On a server that hides the other player's health, it is worked out from the hits you landed: dealt damage would otherwise read as nothing.
    # Where the server hid their health: the estimate saved with the fight (or worked out now for older fights), from the hidden-health model.
    from . import hpguess
    raw0 = np.asarray(arrays["raw"], np.float64)
    est = arrays.get("ohp_est")
    if est is None and readers.hp is not None:
        est = readers.hp.track(raw0, arrays.get("ev"), arrays.get("keys"))
    raw, health_estimated = hpguess.fill(raw0, est)
    keys = arrays.get("keys")
    T = len(raw)
    if T < 2 * SEG:
        return None
    starts, you, them, _, m_you, m_them = readers.read_saved(info.get("id"), raw, arrays.get("opitch"), keys)
    ok = starts + 2 * SEG <= T
    exp = np.full(len(starts), np.nan)
    if ok.any():
        exp[ok] = readers.expected(raw, starts[ok])
    sd = readers.spot.sd
    labels = labels or {}
    fixes = labels.get("exchanges", {})
    intents = sorted(info.get("intent", []), key=lambda x: x[0])
    hev = hit_events(raw, arrays.get("ev"), keys)
    hits = exchange_hits(raw, keys, starts, hev["crits"])
    ex = []
    for k, a in enumerate(starts):
        d1, t1 = trade(raw, a, SEG)
        d2, t2 = trade(raw, a, 2 * SEG)
        dist = float(np.hypot(raw[a - 1, R["ox"]] - raw[a - 1, R["sx"]], raw[a - 1, R["oz"]] - raw[a - 1, R["sz"]]))
        e = {"ex": k, "t0": int(a), "dist": round(dist, 2), "you": read_choice(you[k], None if m_you is None else m_you[k]), "them": read_choice(them[k], None if m_them is None else m_them[k]),
             "real": {"dealt": round(d1, 2), "taken": round(t1, 2), "trade2": round(d2 - t2, 2)},
             "hp": {"you": round(float(raw[a - 1, R["shp"]]), 1), "them": round(float(raw[a - 1, R["ohp"]]), 1)},
             "hits": hits[k]}
        if not np.isnan(exp[k]):
            e["expected"] = round(float(exp[k]), 2)
            e["vs"] = round(float(d2 - t2 - exp[k]), 2)
            e["call"] = "worse" if e["vs"] <= -sd else "better" if e["vs"] >= sd else "as_expected"
            e["later"] = round(later_net(raw, int(a)), 1)
        dec = [x for x in intents if x[0] <= a]
        if dec and dec[-1][1]:
            e["declared"] = dec[-1][1]
        f = fixes.get(str(k))
        if f:
            e["fix"] = f
        ex.append(e)
    if readers.answers is not None and len(ex) > 1:
        ks = list(range(1, len(ex)))
        last = [chosen(ex[k - 1], "them") for k in ks]
        sure = [bool((ex[k - 1].get("fix") or {}).get("them")) or ex[k - 1]["them"]["p"] >= 0.6 for k in ks]
        for k, l, ans in zip(ks, last, readers.answers.lookup(spot_features(raw, starts[ks]), last, tier, sure)):
            if ans:
                ex[k]["answers"] = dict(ans, after=LABELS[l], farmed=sum(ex[j]["hits"]["them"]["crits"] for j in range(max(0, k - 3), k)) >= 2 and ex[k]["dist"] < 2.5)
                ex[k]["suggest"] = suggestion(ex[k])
    # What the copilot's counter said during the fight (server 1.6.0 on). From 1.7.0 a step judges your answer (the exchange that ended WAIT ticks
    # before) to their move in the exchange before it, and goes on that exchange; 1.6.0 rows (six fields) read their move only, on its own exchange.
    from .counter import HOW, WAIT
    for c in (info.get("copilot") or {}).get("counters") or []:
        judged = len(c) > 7
        k = (int(c[0]) - WAIT - SEG) // SEG
        if 0 <= k < len(ex) and c[1] in LABELS:
            shown = c[5] if len(c) > 5 else True
            ex[k]["counter"] = {"them": LABELS[c[1]], "p": c[2], "counter": LABELS.get(c[3]) if shown else None, "how": HOW.get(c[3]) if shown else None,
                                "kept_off": bool(c[3]) and shown is False, "you": LABELS.get(c[6]) if judged else None,
                                "verdict": c[7] if judged and shown else None, "after": judged}
    copilot = None
    if readers.guide is not None and keys is not None:
        # What the copilot said, or would have said, through this fight, and how your play compared. Style notes from the fight's own numbers.
        from . import guide as gd
        kk = np.asarray(keys, np.float64)
        track = gd.track(readers.guide, raw, kk)
        logged = info.get("copilot") or {}
        by_t = {h[0]: h for h in track}
        said = strafed = wanted = followed = 0
        for e in ex:
            h = by_t.get(int(e["t0"])) or by_t.get(int(e["t0"]) + 1) or by_t.get(int(e["t0"]) + 2)
            if not h:
                continue
            did = gd.steered(raw, kk, h[0])
            e["copilot"] = {"move": h[1], "click": h[2], "cue": h[3], "did": did}
            said += 1
            followed += did == h[1]
            wanted += h[1] in ("left", "right")
            strafed += did in ("left", "right")
        style = gd.style_features(raw, kk, np.array([T - 1]))[0]
        copilot = {"track": track, "style": [round(float(x), 4) for x in style], "notes": gd.notes(style, readers.guide.norms), "on": bool(logged.get("on")), "held_back": bool(logged.get("held_back")),
                   "said": said, "followed": followed, "wanted_strafe": wanted, "strafed": strafed, "opponent": info.get("opponent")}
    moves = assign_moves(ex)
    worse = sorted([e for e in ex if e.get("call") == "worse"], key=lambda e: e["vs"])[:6]
    vs = [e["vs"] for e in ex if "vs" in e]
    return {"id": info["id"], "info": info, "exchanges": ex, "moves": moves, "copilot": copilot, "health_estimated": health_estimated, "techniques": [tech(t) for t in range(len(TECHNIQUES))],
            "timing": timing(raw, keys, hev["crits"]), "worse": [e["ex"] for e in worse], "residual_sd": round(sd, 2),
            "events_recorded": hev["recorded"],
            "summary": {"exchanges": len(ex), "vs_expected": round(float(np.sum(vs)), 2) if vs else None,
                        "crits_you": sum(1 for c in hev["crits"] if c[1] == 1),
                        "crits_them": sum(1 for c in hev["crits"] if c[1] == 0),
                        "per_exchange": round(float(np.mean(vs)), 3) if vs else None,
                        "worse": sum(1 for e in ex if e.get("call") == "worse"),
                        "better": sum(1 for e in ex if e.get("call") == "better")}}


MOVE_MAX = 5     # exchanges: a move is about 2 seconds, and nothing that keeps going for over 3 is still one move
COMBOS = {"double_crit", "sweep_combo", "nokb_combo"}


def assign_moves(ex):
    """Exchanges are 0.6 s; a technique usually takes about 2 s. Per side, runs of exchanges showing the same technique (or one the other also shows) are one move; a span the player labelled always is, and a
    labelled exchange with a different technique always ends one. Each exchange gets its move's index, and each move what the pages count: its technique (a label wins, else what most of it read as), how long, how
    far apart it started, and how it went: exchanges overlap (each looks 1.2 s ahead), so every second one is added up."""
    out = {}
    for side in ("you", "them"):
        moves, cur = [], None
        for k, e in enumerate(ex):
            fix = e.get("fix") or {}
            t = chosen(e, side)
            hits = ((e.get("hits") or {}).get(side) or {}).get("landed", 0)
            also = {a["id"] for a in e[side].get("also", [])}
            if fix.get(side + "2"):
                also.add(fix[side + "2"])
            span = tuple(fix["span"]) if fix.get("span") and fix.get(side) else None
            join = False
            if cur is not None:
                if span or cur["span"]:
                    # the span was saved for both sides of the form: a side only stays one move if it really has the one technique across it
                    join = span == cur["span"] and fix.get(side) == cur["label"]
                else:
                    last = cur["seen"][-1]
                    # "Also" only links two exchanges when neither move builds on the other: a sprint hit is under nearly every W-tap, and letting that join them would swallow the W-taps into one long sprint hit.
                    linked = (t in cur["also"] or last in also) and t not in _builds_on(last) and last not in _builds_on(t)
                    # A second hit is a second move: three W-taps in a row are three W-taps. Only a technique that is several hits by name stays one.
                    again = hits and cur["hits"] and t not in COMBOS
                    join = (k - cur["first"] < MOVE_MAX) and (t == last or linked) and not again and not (fix.get(side) and cur["label"] and fix[side] != cur["label"])
            if not join:
                cur = {"first": k, "seen": [], "also": set(), "span": span, "label": None, "hits": 0}
                moves.append(cur)
            cur["last"] = k
            cur["hits"] += hits
            cur["seen"].append(t)
            cur["also"] |= also
            if fix.get(side):
                cur["label"] = fix[side]
            e.setdefault("move", {})[side] = len(moves) - 1
        done = []
        for m in moves:
            seen = m["seen"]
            tech = m["label"] or max(dict.fromkeys(seen), key=seen.count)
            vs = [ex[k]["vs"] for k in range(m["first"], m["last"] + 1, 2) if "vs" in ex[k]]
            done.append({"first": m["first"], "last": m["last"], "tech": tech, "name": LABELS[tech], "also": sorted(a for a in m["also"] | set(seen) if a != tech),
                         "seconds": round((m["last"] - m["first"] + 1) * SEG / 20.0, 1), "dist": ex[m["first"]]["dist"], "vs": round(float(sum(vs)), 2) if vs else None,
                         "labelled": m["label"] is not None})
        out[side] = done
    return out


def chosen(e, side):
    """The technique to count for a side: your relabel if you made one, else the reader's."""
    f = e.get("fix") or {}
    return f.get(side) or e[side]["id"]
