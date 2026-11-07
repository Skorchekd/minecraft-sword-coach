# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""Across all your fights: the skill tree, technique matchups, the branch map of how engagements go, how your answers
to each of their techniques went at each distance, and how far your labelling has got."""
import math
from collections import defaultdict

import numpy as np

from .fields import DIST_BANDS, LABELS, REQUIRES, TECHNIQUES, TIER, TIER_NAMES, band_of
from .review import chosen

MIN_SOLID, MIN_LEARNING = 15, 5
MIN_ANSWER = 5


def _mean_se(v):
    v = np.asarray(v, np.float64)
    if not len(v):
        return None, None
    return round(float(v.mean()), 3), round(float(v.std(ddof=1) / math.sqrt(len(v))), 3) if len(v) > 1 else None


def verdict(n, m, se, enough=MIN_SOLID):
    """working / costly when the 95% range of how it went is clear of zero, even when it is not, learning / not seen
    when there are too few to tell."""
    if n < MIN_LEARNING or m is None:
        return "not seen" if n < MIN_LEARNING else "learning"
    if n < enough:
        return "learning"
    if se is None:
        return "even"
    return "working" if m - 2 * se > 0 else "costly" if m + 2 * se < 0 else "even"


def in_band(e, band):
    return band is None or band_of(e["dist"]) == band


def _their_move_at(r, k):
    return r["moves"]["them"][r["exchanges"][k]["move"]["them"]]


def skill_tree(reviews, band=None):
    """Counted in moves, not exchanges: a 2-second technique used once is one use."""
    used, faced = defaultdict(list), defaultdict(list)
    count, fights, labelled, faced_n = defaultdict(int), defaultdict(set), defaultdict(int), defaultdict(int)
    execution, fails = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    total = 0
    for r in reviews:
        for m in r["moves"]["you"]:
            if band is not None and band_of(m["dist"]) != band:
                continue
            y = m["tech"]
            total += 1
            count[y] += 1
            fights[y].add(r["id"])
            if m["labelled"]:
                labelled[y] += 1
            x_seen, f_seen = set(), set()
            for k in range(m["first"], m["last"] + 1):
                fix = r["exchanges"][k].get("fix") or {}
                x = (fix.get("exec") or {}).get("you")
                if x and x not in x_seen:
                    x_seen.add(x)
                    execution[y][x] += 1
                for f in (fix.get("fail") or {}).get("you", []):
                    if f not in f_seen:
                        f_seen.add(f)
                        fails[y][f] += 1
            if m["vs"] is not None:
                used[y].append(m["vs"])
        for m in r["moves"]["them"]:
            if band is not None and band_of(m["dist"]) != band:
                continue
            faced_n[m["tech"]] += 1
            if m["vs"] is not None:
                faced[m["tech"]].append(m["vs"])
    nodes = []
    for name in TECHNIQUES:
        m, se = _mean_se(used[name])
        fm, fse = _mean_se(faced[name])
        n = count[name]
        nodes.append({"id": name, "name": LABELS[name], "tier": TIER_NAMES[TIER[name]], "requires": REQUIRES[name],
                      "uses": n, "share": round(n / total, 3) if total else 0.0, "fights": len(fights[name]),
                      "labelled": labelled[name], "vs_expected": m, "se": se, "faced": faced_n[name],
                      "faced_vs_expected": fm, "faced_se": fse, "level": verdict(n, m, se),
                      "execution": dict(execution[name]), "fails": dict(fails[name])})
    return {"nodes": nodes, "moves": total, "exchanges": total}


def by_distance(reviews):
    """Per technique and distance band: how often you used it and how it went (the skill tree's detail)."""
    cell = defaultdict(list)
    for r in reviews:
        for m in r["moves"]["you"]:
            if m["vs"] is not None:
                cell[(m["tech"], band_of(m["dist"]))].append(m["vs"])
    out = {}
    for name in TECHNIQUES:
        row = {}
        for k, _, _, _ in DIST_BANDS:
            v = cell.get((name, k), [])
            m, se = _mean_se(v)
            row[k] = {"n": len(v), "vs_expected": m, "se": se, "level": verdict(len(v), m, se, enough=8)}
        out[name] = row
    return out


def matchups(reviews, band=None):
    cell = defaultdict(list)
    for r in reviews:
        for m in r["moves"]["you"]:
            if m["vs"] is not None and (band is None or band_of(m["dist"]) == band):
                cell[(m["tech"], _their_move_at(r, m["first"])["tech"])].append(m["vs"])
    out = []
    for (y, t), v in cell.items():
        m, se = _mean_se(v)
        out.append({"you": y, "them": t, "n": len(v), "vs_expected": m, "se": se})
    return {"cells": sorted(out, key=lambda c: -c["n"]), "techniques": TECHNIQUES, "labels": LABELS}


def answers(reviews):
    """After they used a technique, how each of your answers in the next exchange went, at each distance you were at
    when you answered. A cell is clear only when its 95% range is clear of zero; the best answer at a distance is
    named only when it is clearly ahead of the next one."""
    cell = defaultdict(list)
    seen = defaultdict(int)
    examples = defaultdict(list)
    for r in reviews:
        # Your move, against the move of theirs that was going on just before it started, from how far apart you were when it started.
        for m in r["moves"]["you"]:
            if m["first"] < 1 or m["vs"] is None:
                continue
            prev, mine, b = _their_move_at(r, m["first"] - 1)["tech"], m["tech"], band_of(m["dist"])
            seen[prev] += 1
            for bb in (b, "all"):
                cell[(prev, bb, mine)].append(m["vs"])
                if len(examples[(prev, bb, mine)]) < 6:
                    examples[(prev, bb, mine)].append({"fight": r["id"], "ex": m["first"]})
    bands = ["all"] + [k for k, _, _, _ in DIST_BANDS]
    out = []
    for prev in sorted(seen, key=lambda t: -seen[t]):
        if seen[prev] < MIN_ANSWER:
            continue
        cols = {}
        for b in bands:
            rows = []
            for mine in TECHNIQUES:
                v = cell.get((prev, b, mine))
                if not v:
                    continue
                m, se = _mean_se(v)
                rows.append({"you": mine, "n": len(v), "vs_expected": m, "se": se,
                             "level": verdict(len(v), m, se, enough=8), "examples": examples[(prev, b, mine)]})
            rows.sort(key=lambda x: (x["n"] < MIN_ANSWER, -(x["vs_expected"] or 0)))
            ok = [x for x in rows if x["n"] >= MIN_ANSWER and x["se"] is not None]
            best = None
            if len(ok) >= 2:
                a, c = ok[0], ok[1]
                if a["vs_expected"] - c["vs_expected"] > 2 * math.hypot(a["se"], c["se"]) and a["level"] == "working":
                    best = a["you"]
            elif len(ok) == 1 and ok[0]["level"] == "working":
                best = ok[0]["you"]
            cols[b] = {"n": sum(x["n"] for x in rows), "rows": rows, "best": best}
        out.append({"them": prev, "n": seen[prev], "bands": cols})
    return {"after": out, "bands": bands}


def labels(reviews):
    """How far your labelling has got: per technique, the exchanges you labelled (corrected the read, or said the
    read was right) for you and for them, and which unlabelled exchanges the readers were least sure about."""
    per = {t: {"you": 0, "them": 0, "checked": 0, "corrected": 0} for t in TECHNIQUES}
    fights_labelled, exchanges_labelled, unsure = 0, 0, []
    for r in reviews:
        any_label = False
        spans = set()
        for e in r["exchanges"]:
            fix = e.get("fix") or {}
            if fix.get("you") or fix.get("them"):
                exchanges_labelled += 1
                any_label = True
            for side in ("you", "them"):
                t = fix.get(side)
                if t and fix.get("span"):     # one move labelled across several exchanges is one label
                    key = (side, t, tuple(fix["span"]))
                    if key in spans:
                        continue
                    spans.add(key)
                if t:
                    per[t][side] += 1
                    per[t]["checked" if t == e[side]["id"] else "corrected"] += 1
                t2 = fix.get(side + "2")
                if t2 and fix.get("span"):
                    key = (side, t2, tuple(fix["span"]), 2)
                    if key in spans:
                        continue
                    spans.add(key)
                if t2:
                    per[t2][side] += 1
            if not fix:
                p = min(e["you"].get("p", 1.0), e["them"].get("p", 1.0))
                unsure.append((p, r["id"], e["ex"], e["you"]["id"], e["them"]["id"]))
        fights_labelled += any_label
    unsure.sort()
    nxt = [{"fight": f, "ex": k, "p": round(p, 2), "you": y, "them": t} for p, f, k, y, t in unsure[:12]]
    return {"techniques": per, "fights": fights_labelled, "exchanges": exchanges_labelled, "next": nxt}


def engagements(r, gap=4.5):
    """Runs of exchanges between separations: a new run starts when you are more than `gap` blocks apart."""
    runs, cur = [], []
    for e in r["exchanges"]:
        if e["dist"] > gap and cur:
            runs.append(cur)
            cur = []
        if e["dist"] <= gap or cur:
            cur.append(e)
    if cur:
        runs.append(cur)
    return [x for x in runs if len(x) >= 2]


def engaged_first(run):
    """Who started an engagement: the first hit landed in it, or the first swing if nobody landed one. None if it cannot be told (same tick, or neither did)."""
    for key in ("first_hit", "first_swing"):
        for e in run:
            you, them = e["hits"]["you"][key], e["hits"]["them"][key]
            if you is None and them is None:
                continue
            if you == them:
                break
            return "them" if you is None or (them is not None and them < you) else "you"
    return None


def branches(reviews, depth=3, keep=4):
    """How engagements go: whoever started it -> the other's answer -> the first's next ... Each node counts the
    engagements that went that way and how those exchanges went against expectation (real data)."""
    root = {"id": "root", "label": "Engagements", "n": 0, "vs": [], "children": {}, "examples": []}
    for r in reviews:
        for run in engagements(r):
            root["n"] += 1
            node = root
            order = ("you", "them") if engaged_first(run) == "you" else ("them", "you")
            for e in run[:depth]:
                for side in order:
                    key = f"{side}:{chosen(e, side)}"
                    ch = node["children"].setdefault(key, {"id": key, "side": side, "tech": chosen(e, side),
                                                         "label": LABELS[chosen(e, side)], "n": 0, "vs": [],
                                                         "children": {}, "examples": []})
                    ch["n"] += 1
                    if "vs" in e:
                        ch["vs"].append(e["vs"])
                    if len(ch["examples"]) < 6:
                        ch["examples"].append({"fight": r["id"], "ex": e["ex"]})
                    node = ch

    def finish(node):
        out = {k: node[k] for k in ("id", "label", "n", "examples") if k in node}
        out.update({k: node[k] for k in ("side", "tech") if k in node})
        vs = node["vs"]
        m, se = _mean_se(vs)
        out["vs_expected"], out["se"] = m, se
        out["level"] = verdict(len(vs), m, se, enough=8) if node.get("side") == "you" else None
        out["children"] = []
        for side in ("them", "you"):      # the first column holds both sides, so each keeps its own top moves
            kids = sorted((c for c in node["children"].values() if c["side"] == side), key=lambda c: -c["n"])
            out["children"] += [finish(c) for c in kids[:keep]]
            rest = kids[keep:]
            if rest:
                out["children"].append({"id": f"{node['id']}/{side}/other", "label": f"{len(rest)} other", "n": sum(c["n"] for c in rest),
                                        "side": side, "children": [], "examples": [], "vs_expected": None, "se": None})
        return out

    return finish(root)


def style_profile(reviews, norms):
    """Your style across fights, and each opponent's once there are several fights against them. One fight is too short to read a habit: these numbers only settle over several."""
    from .guide import notes, opponent_notes
    rows = [r["copilot"] for r in reviews if r.get("copilot")]
    out = {"fights": len(rows), "you": [], "opponents": [], "enough": len(rows) >= 5}
    if out["enough"]:
        out["you"] = notes(np.median([c["style"] for c in rows], 0), norms)
        said, followed = sum(c["said"] for c in rows), sum(c["followed"] for c in rows)
        wanted, strafed = sum(c["wanted_strafe"] for c in rows), sum(c["strafed"] for c in rows)
        out["play"] = {"exchanges": said, "followed": followed, "wanted_strafe": wanted, "strafed": strafed}
    by = {}
    for c in rows:
        if c.get("opponent"):
            by.setdefault(c["opponent"], []).append(c["style"])
    for code, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if len(v) >= 4:
            n = opponent_notes(np.median(v, 0), norms)
            if n:
                out["opponents"].append({"code": code[:6], "fights": len(v), "notes": n})
    out["opponents"] = out["opponents"][:6]
    return out


def everything(reviews, norms=None):
    bands = [None] + [k for k, _, _, _ in DIST_BANDS]
    return {"skill_tree": {b or "all": skill_tree(reviews, b) for b in bands},
            "matchups": {b or "all": matchups(reviews, b) for b in bands},
            "by_distance": by_distance(reviews), "answers": answers(reviews), "labels": labels(reviews),
            "branches": branches(reviews), "fights": len(reviews), "style": style_profile(reviews, norms)}
