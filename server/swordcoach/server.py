# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""Sword Coach local server.

  127.0.0.1:47310  the mod connects here and streams your fights (newline-delimited JSON)
  127.0.0.1:47320  the review page in your browser

Both listen on this computer only. Fights are saved under data/fights, your relabels under data/labels, and the hit
sounds of your own game (which the mod hands over, so the page's clips sound like your game) under data/sounds.
Nothing is sent anywhere: sharing fights is a separate, manual step (Bundle Fight Data), which never includes sounds.

    python -m swordcoach.server [--data DIR] [--mod-port 47310] [--web-port 47320] [--models DIR]
"""
import argparse
import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import socketserver
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

from . import __version__, counter, guide, hpguess, profile, review, stats, store
from .fields import (DEFINITIONS, DIST_BANDS, EXECUTION, EXECUTION_LABELS, FAIL_LABELS, FAILS, FAMILIES, FAMILY, LABELS,
                     PLAYER_TIERS, R, REQUIRES, SEG, SHORT, SOUND_EVENTS, TECHNIQUES, TIER, TIER_NAMES)
from .readers import Readers

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(HERE)
WEB = os.path.join(SERVER_DIR, "web")
MODELS = os.path.join(SERVER_DIR, "models")
ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}(-[0-9]+)?$")
IP_RE = re.compile(r"[0-9a-fA-F.:\[\]]+")
SOUND_RE = re.compile(r"^/sound/(" + "|".join(SOUND_EVENTS) + r")/([0-9]{1,2})\.ogg$")


class App:
    def __init__(self, data_dir, models_dir=MODELS):
        self.data = data_dir
        self.fights_dir = os.path.join(data_dir, "fights")
        self.labels_dir = os.path.join(data_dir, "labels")
        self.sounds_dir = os.path.join(data_dir, "sounds")
        os.makedirs(self.fights_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)
        self.readers = Readers(models_dir)
        self.readers.reads_dir = os.path.join(data_dir, "reads")
        self.secret = profile.install_secret()
        self.me = profile.load(data_dir)
        self.lock = threading.Lock()
        self.cache = {}
        self.thumbs = {}
        self.reading = {"done": 0, "total": 0}     # how far the page's "reading your fights" has got
        self.mods = 0                              # game clients connected right now

    # ---- storage ---------------------------------------------------------------------------------
    def fight_path(self, fid):
        return os.path.join(self.fights_dir, fid + ".scf")

    def labels_path(self, fid):
        return os.path.join(self.labels_dir, fid + ".json")

    def fight_ids(self):
        return sorted((f[:-4] for f in os.listdir(self.fights_dir) if f.endswith(".scf")), reverse=True)

    def labels(self, fid):
        try:
            with open(self.labels_path(fid), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def save_labels(self, fid, body):
        cur = self.labels(fid)
        ex = cur.setdefault("exchanges", {})
        try:
            reads = {e["ex"]: e for e in self.review(fid)["exchanges"]}
        except Exception:
            reads = {}
        for k, v in (body.get("exchanges") or {}).items():
            if not str(k).isdigit():
                continue
            clean = {s: v[s] for s in ("you", "them") if isinstance(v, dict) and v.get(s) in TECHNIQUES}
            # A second technique on the same side, when two overlap (a hit select that is also a sprint hit).
            for s in ("you", "them"):
                if s in clean and v.get(s + "2") in TECHNIQUES and v[s + "2"] != clean[s]:
                    clean[s + "2"] = v[s + "2"]
            # Labelled as one move across several exchanges.
            sp = v.get("span") if isinstance(v, dict) else None
            if clean and isinstance(sp, list) and len(sp) == 2 and all(isinstance(x, int) for x in sp) and sp[0] <= int(k) <= sp[1] and sp[1] - sp[0] < 12:
                clean["span"] = sp
            if isinstance(v, dict) and isinstance(v.get("note"), str) and v["note"].strip():
                clean["note"] = v["note"].strip()[:500]
            # How each side executed it, and what went wrong.
            exe = v.get("exec") if isinstance(v, dict) and isinstance(v.get("exec"), dict) else {}
            exe = {s: exe[s] for s in ("you", "them") if exe.get(s) in EXECUTION}
            if exe:
                clean["exec"] = exe
            fail = v.get("fail") if isinstance(v, dict) and isinstance(v.get("fail"), dict) else {}
            fail = {s: [f for f in FAILS if isinstance(fail.get(s), list) and f in fail[s]] for s in ("you", "them")}
            fail = {s: fs for s, fs in fail.items() if fs}
            if fail:
                clean["fail"] = fail
            if clean:
                # What the readers said when you corrected them, and the exchange's first tick, so the label
                # stands on its own in a bundle.
                r = reads.get(int(k))
                if r:
                    clean["read"] = {"you": r["you"]["id"], "them": r["them"]["id"],
                                     "p": {"you": r["you"]["p"], "them": r["them"]["p"]}}
                    clean["t0"] = r["t0"]
                ex[str(k)] = dict(clean, at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            else:
                ex.pop(str(k), None)
        if isinstance(body.get("note"), str):
            cur["note"] = body["note"].strip()[:2000]
        cur["models"] = self.readers.versions
        cur["app"] = __version__
        tmp = self.labels_path(fid) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=1)
        os.replace(tmp, self.labels_path(fid))
        self.cache.pop(fid, None)
        return cur

    def review(self, fid):
        p = self.fight_path(fid)
        stamp = (os.path.getmtime(p), os.path.getmtime(self.labels_path(fid)) if os.path.exists(self.labels_path(fid)) else 0)
        hit = self.cache.get(fid)
        if hit and hit[0] == stamp:
            return hit[1]
        info, arrays = store.read(p)
        with self.lock:
            r = review.build(info, arrays, self.readers, self.labels(fid), tier=self.me["tier"])
        self.cache[fid] = (stamp, r)
        return r

    def frames(self, fid):
        """Both players as drawn per tick, hits, health, the attack sounds and crits, and where the recording has a gap
        (a cut: the replay jumps there instead of sliding)."""
        info, a = store.read(self.fight_path(fid))
        raw = a["raw"]
        hp, hp_estimated = self.health(info, a)
        up = lambda c: np.r_[False, np.diff(raw[:, R[c]]) > 0].astype(int).tolist()
        drawn = a.get("drawn")
        if drawn is None:          # no drawn frames: positions from the record (you exact, them as received)
            z = np.zeros((len(raw), 20))
            for s, p in ((0, "s"), (1, "o")):
                z[:, 10 * s:10 * s + 3] = raw[:, [R[p + "x"], R[p + "y"], R[p + "z"]]]
                z[:, 10 * s + 3] = z[:, 10 * s + 4] = raw[:, R[p + "yaw"]]
                z[:, 10 * s + 8] = raw[:, R[p + "swing"]]
            drawn = z
        ticks = a.get("ticks")
        cuts = (np.nonzero(np.diff(ticks) != 1)[0] + 1).tolist() if ticks is not None and len(ticks) > 1 else []
        ev = review.hit_events(np.asarray(raw, np.float64), a.get("ev"), a.get("keys"))
        return {"id": fid, "drawn": np.round(drawn, 3).tolist(), "hurt": [up("shurt"), up("ohurt")],
                "hp": hp, "hp_estimated": hp_estimated, "cuts": cuts,
                "sounds": ev["sounds"], "crits": ev["crits"], "events_recorded": ev["recorded"]}

    def health(self, info, a):
        """Both players' health per tick for the page and replays: [yours, theirs] (theirs as the server showed it, or the hidden-health model's
        estimate where it hid it), and whether theirs is estimated."""
        raw = np.asarray(a["raw"], np.float64)
        est = a.get("ohp_est")
        if est is None:
            est = self.readers.hp.track(raw, a.get("ev"), a.get("keys"))
        filled, estimated = hpguess.fill(raw, est)
        return [filled[:, R["shp"]].round(1).tolist(), filled[:, R["ohp"]].round(1).tolist()], estimated

    def replay(self, fid):
        """A saved fight for the mod's in-game replay: what the client drew, gaps, sounds and crits, and each exchange."""
        r = self.review(fid)
        if not r:
            return {"t": "replay", "id": fid, "failed": True}
        fr = self.frames(fid)
        return {"t": "replay", "id": fid, "title": "Fight " + when(r["info"].get("time")), "drawn": fr["drawn"],
                "cuts": fr["cuts"], "sounds": fr["sounds"], "crits": fr["crits"], "exchanges": mod_exchanges(r), "copilot": (r.get("copilot") or {}).get("track"),
                "counters": counters_shown(r["info"]), "hp": fr["hp"], "hp_estimated": fr["hp_estimated"]}

    def all_reviews(self):
        out = []
        ids = self.fight_ids()
        self.reading = {"done": 0, "total": len(ids)}
        for fid in ids:
            try:
                r = self.review(fid)
            except Exception as e:      # a broken file must not take the page down
                print(f"skipped {fid}: {e!r}", flush=True)
                r = None
            self.reading["done"] += 1
            if r:
                out.append(r)
        return out

    def thumb(self, fid):
        """The fight list's small preview: both players' health at evenly spaced points through the fight."""
        p = self.fight_path(fid)
        stamp = os.path.getmtime(p)
        hit = self.thumbs.get(fid)
        if hit and hit[0] == stamp:
            return hit[1]
        info, a = store.read(p)
        hp, estimated = self.health(info, a)
        at = np.linspace(0, len(hp[0]) - 1, 28).round().astype(int).tolist()
        out = {"you": [hp[0][i] for i in at], "them": [hp[1][i] for i in at], "estimated": bool(estimated)}
        self.thumbs[fid] = (stamp, out)
        return out

    def fight_list(self):
        out = []
        for fid in self.fight_ids():
            try:
                info = store.read_info(self.fight_path(fid))
            except Exception:
                continue
            item = {"id": fid, "time": info.get("time"), "server": info.get("server"), "result": info.get("result"),
                    "seconds": info.get("seconds"), "relabels": len(self.labels(fid).get("exchanges", {}))}
            hit = self.cache.get(fid)
            if hit and hit[1]:
                item["summary"] = hit[1]["summary"]
            out.append(item)
        return out

    def save_fight(self, f):
        raw = np.asarray(f.raws, np.float32)
        n = len(raw)
        keys = np.asarray(f.keys[:n], np.float32) if f.keys and all(k is not None for k in f.keys[:n]) else None
        drawn = f.drawn[:n] if f.drawn and all(d is not None for d in f.drawn[:n]) else None
        kb = np.asarray(f.kb[:n], np.float32) if f.kb and all(v is not None for v in f.kb[:n]) else None
        ev = np.asarray(f.ev[:n], np.int32) if f.ev and all(v is not None for v in f.ev[:n]) else None
        fid = time.strftime("%Y%m%d-%H%M%S")
        k = 1
        while os.path.exists(self.fight_path(fid)):
            fid = time.strftime("%Y%m%d-%H%M%S") + f"-{k}"
            k += 1
        info = {"id": fid, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "server": f.server, "result": f.result,
                "result_why": f.why, "ticks": n, "seconds": round(n / 20.0, 1), "keys": keys is not None,
                "intent": f.intent, "me": self.code(f.me), "opponent": self.code(f.opponent),
                "opp_health_source": f.health_source,
                "app": __version__, "models": self.readers.versions}
        if f.copilot_on:
            info["copilot"] = {"on": True, "held_back": f.held_back, "hints": [h for h in f.hints if h[0] < n], "counters": [c for c in f.counters if c[0] < n]}
        # Their health as worked out from your hits, saved with every fight: where the server hides it, this is what the review and replays show.
        est = None
        try:
            est = self.readers.hp.track(raw, ev, keys)
            info["opp_health_est"] = {"model": self.readers.versions.get("hp_model", "rule"), "hidden": hpguess.hidden(raw)}
        except Exception as e:
            print(f"health estimate not saved: {e!r}", flush=True)
        store.write(self.fight_path(fid), info, raw, keys, f.opitch[:n], drawn, f.ticks[:n], kb, ev, est)
        return fid

    # ---- hit sounds --------------------------------------------------------------------------------------------
    def save_sounds(self, files):
        """The hit sounds of the player's own game (with their resource pack), as the mod read them: kept under
        data/sounds for the page's clips. Each file is overwritten in place; index.json says which are current."""
        kinds = {ev: k for k, ev in SOUND_EVENTS.items()}
        got, total = {}, 0
        for f in files if isinstance(files, list) else []:
            k = kinds.get(f.get("event")) if isinstance(f, dict) else None
            if k is None or not isinstance(f.get("data"), str) or len(got.get(k, [])) >= 16:
                continue
            try:
                b = base64.b64decode(f["data"], validate=True)
            except ValueError:
                continue
            total += len(b)
            if not b.startswith(b"OggS") or len(b) > 1_000_000 or total > 8_000_000:
                continue
            got.setdefault(k, []).append(b)
        if not got:
            return 0
        for k, blobs in got.items():
            os.makedirs(os.path.join(self.sounds_dir, k), exist_ok=True)
            for i, b in enumerate(blobs):
                p = os.path.join(self.sounds_dir, k, f"{i}.ogg")
                with open(p + ".tmp", "wb") as fh:
                    fh.write(b)
                os.replace(p + ".tmp", p)
        index = {k: len(v) for k, v in got.items()}
        with open(os.path.join(self.sounds_dir, "index.json.tmp"), "w", encoding="utf-8") as fh:
            json.dump(index, fh)
        os.replace(os.path.join(self.sounds_dir, "index.json.tmp"), os.path.join(self.sounds_dir, "index.json"))
        return sum(index.values())

    def sound_index(self):
        try:
            with open(os.path.join(self.sounds_dir, "index.json"), encoding="utf-8") as fh:
                index = json.load(fh)
        except (OSError, ValueError):
            return {}
        return {k: [f"/sound/{k}/{i}.ogg" for i in range(min(16, int(n)))] for k, n in index.items() if k in SOUND_EVENTS}


    def save_profile(self, body):
        old = self.me["tier"]
        self.me = profile.save(self.data, body)
        if self.me["tier"] != old:
            self.cache.clear()          # the answers depend on your tier
        return self.me

    def code(self, name):
        """A player's name as a keyed code: the same player always gets the same code on this computer, and
        the name cannot be got back from it without the key in server/.install_key (which never leaves it)."""
        if not isinstance(name, str) or not name.strip():
            return None
        return hmac.new(self.secret, name.strip().lower().encode(), hashlib.sha256).hexdigest()[:16]


def when(iso):
    """"29 Oct 03:19" from the saved time."""
    try:
        return datetime.datetime.fromisoformat(iso).strftime("%d %b %H:%M").lstrip("0")
    except (TypeError, ValueError):
        return "?"


def counters_shown(info):
    """The counters the copilot showed in a fight, for the replay: [[tick, their move, counter or None, how or None, your move or None,
    verdict or None], ...] (fights from server 1.6.0 on). One kept off the screen at random stays off in the replay too."""
    out = []
    for c in (info.get("copilot") or {}).get("counters") or []:
        t, them, _, k = c[:4]
        shown = c[5] if len(c) > 5 else True
        you, verdict = (c[6], c[7]) if len(c) > 7 else (None, None)
        if not shown:
            k, verdict = None, None
        if them in LABELS:
            out.append([int(t), LABELS[them], LABELS.get(k), counter.HOW.get(k), LABELS.get(you), verdict])
    return out


def mod_exchanges(r):
    """Each exchange as the mod's replay card shows it: the techniques (your relabels win), how it went, the hits."""
    out = []
    for e in r["exchanges"]:
        fix = e.get("fix") or {}
        h = e.get("hits") or {}
        out.append({"ex": e["ex"], "t0": e["t0"], "you": LABELS[review.chosen(e, "you")], "them": LABELS[review.chosen(e, "them")],
                    "relabelled": bool(fix.get("you") or fix.get("them")), "call": e.get("call"), "vs": e.get("vs"), "later": e.get("later"),
                    "suggest": (e.get("suggest") or {}).get("name"),
                    "hits": [[h[s]["landed"], h[s]["swings"], h[s]["crits"]] if s in h else [0, 0, 0] for s in ("you", "them")],
                    "exec": {s: EXECUTION_LABELS[x] for s, x in (fix.get("exec") or {}).items()},
                    "fail": {s: [FAIL_LABELS[x] for x in xs] for s, xs in (fix.get("fail") or {}).items()}})
    return out


HOLD_BACK = 0.2    # share of copilot fights that show no advice
COUNTER_HOLD = 0.25    # share of counters kept off the screen at random (and logged), so shown and not shown can be compared on your own fights
HP_EVERY = 10      # ticks between health guesses on servers that hide it
TIP_WAIT = 6       # ticks after an exchange before the in-fight tip reads it


class Fight:
    def __init__(self, server=None, intent=None, me=None, opponent=None):
        self.server = "ip address" if server and IP_RE.fullmatch(server) else server     # a private server's address stays out of the record
        self.me, self.opponent = me, opponent
        self.raws, self.keys, self.opitch, self.drawn, self.ticks, self.kb, self.ev = [], [], [], [], [], [], []
        self.health_source = {}
        self.intent = [[0, intent]] if intent else []
        self.result, self.why = -1, None
        self.copilot_on, self.live, self.held_back, self.hints, self.guide_busy = False, None, False, [], False
        self.counter, self.counters, self.counter_busy = None, [], False
        self.hp_busy, self.hp_shown = False, False

    def add(self, m):
        self.raws.append(m["r"])
        self.keys.append(m.get("i"))
        self.opitch.append(float(m.get("op") or 0.0))
        self.drawn.append(m.get("d"))
        self.ticks.append(int(m.get("k") or 0))
        v = m.get("v")
        self.kb.append(v if isinstance(v, list) and len(v) == 8 else None)
        e = m.get("e")
        self.ev.append(int(e) if isinstance(e, int) and 0 <= e < 1 << 16 else None)
        hs = m.get("hs")
        if isinstance(hs, str) and len(hs) <= 24:
            self.health_source[hs] = self.health_source.get(hs, 0) + 1

    def trim(self, result):
        """Some servers end a round by resetting the loser's health instead of a death: cut there."""
        raw = np.asarray(self.raws, np.float32)
        self.result = result
        for t in range(1, len(raw)):
            for me, other, res in ((R["shp"], R["ohp"], 0), (R["ohp"], R["shp"], 1)):
                if raw[t, me] - raw[t - 1, me] > 5.0 and raw[t - 1, me] <= 4.0:
                    for lst in (self.raws, self.keys, self.opitch, self.drawn, self.ticks, self.kb, self.ev):
                        del lst[t:]
                    if self.result not in (0, 1):
                        self.result, self.why = res, "health reset at round end"
                    return


class ModHandler(socketserver.StreamRequestHandler):
    app = None

    def setup(self):
        super().setup()
        self.app.mods += 1

    def finish(self):
        self.app.mods -= 1
        super().finish()

    def handle(self):
        lock = threading.Lock()
        fight, intent = None, None
        copilot_on = False

        def send(o):
            with lock:
                try:
                    self.wfile.write((json.dumps(o, separators=(",", ":")) + "\n").encode())
                    self.wfile.flush()
                except OSError:
                    pass

        send({"t": "hello", "version": __version__, "techniques": TECHNIQUES, "labels": [LABELS[t] for t in TECHNIQUES]})
        for line in self.rfile:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            t = m.get("t")
            if t == "reset":
                fight = Fight(m.get("server"), intent, m.get("me"), m.get("opponent"))
                if copilot_on and self.app.readers.guide is not None:
                    # One fight in five shows nothing beyond the plain facts, at random, so on and off can really be compared later.
                    fight.copilot_on, fight.live, fight.held_back = True, guide.Live(self.app.readers.guide), random.random() < HOLD_BACK
                    fight.counter = counter.Counter(self.app.readers, self.app.me["tier"])
                    send({"t": "copilot_fight", "held_back": fight.held_back})
            elif t == "copilot":
                copilot_on = bool(m.get("on"))
            elif t == "intent":
                intent = m.get("technique") if m.get("technique") in TECHNIQUES else None
                if fight is not None:
                    fight.intent.append([len(fight.raws), intent])
            elif t == "raw" and fight is not None and isinstance(m.get("r"), list) and len(m["r"]) == len(R):
                fight.add(m)
                n = len(fight.raws)
                if n > SEG + TIP_WAIT and (n - 1 - TIP_WAIT) % SEG == 0:
                    threading.Thread(target=self.tip, args=(fight, n, send), daemon=True).start()
                if fight.live is not None and n > 20 and (n - 20) % guide.EVERY == 0 and not fight.guide_busy:
                    fight.guide_busy = True
                    threading.Thread(target=self.guide_tick, args=(fight, n, send), daemon=True).start()
                if fight.counter is not None and counter.due(n) and not fight.counter_busy:
                    fight.counter_busy = True
                    threading.Thread(target=self.counter_tick, args=(fight, n, send), daemon=True).start()
                if fight.copilot_on and n >= HP_EVERY and n % HP_EVERY == 0 and not fight.hp_busy:
                    fight.hp_busy = True
                    threading.Thread(target=self.hp_tick, args=(fight, n, send), daemon=True).start()
            elif t == "end" and fight is not None:
                f, fight = fight, None
                threading.Thread(target=self.finish_fight, args=(f, m.get("result", -1), send), daemon=True).start()
            elif t == "list":
                threading.Thread(target=self.fight_list, args=(send,), daemon=True).start()
            elif t == "replay" and isinstance(m.get("id"), str) and ID_RE.match(m["id"]):
                threading.Thread(target=self.replay, args=(m["id"], send), daemon=True).start()
            elif t == "sounds":
                try:
                    n = self.app.save_sounds(m.get("files"))
                    if n:
                        print(f"hit sounds from your game: {n} files", flush=True)
                except OSError as e:
                    print(f"could not keep the hit sounds: {e!r}", flush=True)

    def fight_list(self, send):
        """Your saved fights, newest first, for the mod's fight list (Y)."""
        out = []
        for item in self.app.fight_list()[:200]:
            out.append({"id": item["id"], "when": when(item.get("time")), "server": item.get("server") or "?",
                        "result": item.get("result"), "seconds": item.get("seconds"), "relabels": item.get("relabels", 0)})
        send({"t": "list", "fights": out})

    def replay(self, fid, send):
        if not os.path.exists(self.app.fight_path(fid)):
            return send({"t": "replay", "id": fid, "failed": True})
        try:
            send(self.app.replay(fid))
        except Exception as e:
            print(f"replay failed for {fid}: {e!r}", flush=True)
            send({"t": "replay", "id": fid, "failed": True})

    def guide_tick(self, fight, n, send):
        """The next piece of advice for the screen, logged with the fight whether it was shown or held back."""
        try:
            raw = np.asarray(fight.raws[:n], np.float64)
            keys = fight.keys[:n]
            if not all(k is not None for k in keys):
                return
            keys = np.asarray(keys, np.float64)[:, :8]
            t = n - 1
            if guide.motion(raw[-2:])[0][-1] >= 8.0:
                fight.live.last_t = None
                if not fight.held_back:
                    send({"t": "guide", "move": None, "click": False, "cue": None})
                return
            h = fight.live.step(t, guide.features(raw, keys, np.array([t]))[0])
            fight.hints.append([t, h["move"], h["click"], h["cue"]])
            if not fight.held_back:
                send({"t": "guide", "move": h["move"], "click": h["click"], "cue": h["cue"]})
        except Exception as e:
            print(f"copilot failed: {e!r}", flush=True)
        finally:
            fight.guide_busy = False

    def counter_tick(self, fight, n, send):
        """Their last move as the reader reads it and the counter to it, for the screen, logged with the fight whether it was shown or held back."""
        try:
            keys = fight.keys[:n]
            keys = np.asarray(keys, np.float64)[:, :8] if all(k is not None for k in keys) else None
            with self.app.lock:
                h = fight.counter.step(fight.raws, fight.opitch, keys, n)
            if h["them"] is None:
                return
            c, y = h["counter"], h["you"]
            # Counters (and whether your answer was the right one) show unless you turned them off on the Your data tab. A quarter are kept off the
            # screen at random, so shown and not shown can be compared on your own fights. Logged as shown (True), kept off at random (False)
            # or not in the test (None: counters off, or a quiet fight).
            shown = None if fight.held_back or not self.app.me.get("counters") else (c is None or random.random() >= COUNTER_HOLD)
            fight.counters.append([h["t"], h["them"]["id"], h["them"]["p"], c["id"] if c else None, h.get("gap"), shown,
                                   y["id"] if y else None, h["verdict"]])
            if not fight.held_back:
                send({"t": "counter", "them": h["them"]["name"], "p": h["them"]["p"], "times": h["them"]["times"],
                      "you": y["name"] if y else None, "verdict": h["verdict"] if shown else None,
                      "counter": c["name"] if c and shown else None, "how": c["how"] if c and shown else None})
        except Exception as e:
            print(f"counter failed: {e!r}", flush=True)
        finally:
            fight.counter_busy = False

    def hp_tick(self, fight, n, send):
        """Their health worked out from your hits, for the crosshair, in every copilot fight: where the server shows it you can check the guess
        against it; where it hides it (hidden: five hits landed and it never moved) the guess is all there is. It never reads their shown health."""
        try:
            raw = np.asarray(fight.raws[:n], np.float64)
            keys = fight.keys[:n]
            keys = np.asarray(keys, np.float64)[:, :8] if all(k is not None for k in keys) else None
            ev = np.asarray([e or 0 for e in fight.ev[:n]], np.int64) if any(e is not None for e in fight.ev[:n]) else None
            hp = float(self.app.readers.hp.track(raw, ev, keys)[-1])
            fight.hp_shown = True
            send({"t": "hp", "hp": round(hp, 1), "hidden": hpguess.hidden(raw)})
        except Exception as e:
            print(f"health guess failed: {e!r}", flush=True)
        finally:
            fight.hp_busy = False

    def tip(self, fight, n, send):
        """The exchange that ended TIP_WAIT ticks ago, as the readers see it (live)."""
        try:
            raw = np.asarray(fight.raws[:n], np.float64)
            keys = fight.keys[:n]
            keys = np.asarray(keys, np.float32) if all(k is not None for k in keys) else None
            with self.app.lock:
                got = self.app.readers.read_latest(raw, fight.opitch[:n], keys)
            if got is None:
                return
            k, you, them = got
            send({"t": "tip", "ex": k, "you": review.read_choice(you), "them": review.read_choice(them)})
        except Exception as e:
            print(f"live read failed: {e!r}", flush=True)

    def finish_fight(self, f, result, send):
        f.trim(result)
        if len(f.raws) < 2 * SEG:
            return
        try:
            fid = self.app.save_fight(f)
        except Exception as e:
            print(f"save failed: {e!r}", flush=True)
            return
        send({"t": "saved", "id": fid})
        try:
            r = self.app.review(fid)
        except Exception as e:
            print(f"review failed for {fid}: {e!r}", flush=True)
            send({"t": "summary", "id": fid, "failed": True})
            return
        if not r:
            return
        send(dict(t="summary", id=fid, result=f.result, **r["summary"]))
        fr = self.app.frames(fid)
        send({"t": "exchanges", "id": fid, "exchanges": mod_exchanges(r), "worse": r["worse"],
              "sounds": fr["sounds"], "crits": fr["crits"], "copilot": (r.get("copilot") or {}).get("track"), "counters": counters_shown(r["info"]),
              "hp": fr["hp"], "hp_estimated": fr["hp_estimated"]})


class ModServer(socketserver.ThreadingTCPServer):
    # On Windows SO_REUSEADDR lets a second server take the same port silently.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


class WebServer(ThreadingHTTPServer):
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


class Web(BaseHTTPRequestHandler):
    app = None
    TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
             ".svg": "image/svg+xml", ".png": "image/png", ".ogg": "audio/ogg"}

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def from_this_computer(self):
        """The page and its API answer only pages served from here. A website open in the same browser can otherwise reach 127.0.0.1: through a host
        name that points here (the Host check) or by posting to it (the Origin check)."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].lower()
        origin = self.headers.get("Origin")
        return host in ("127.0.0.1", "localhost", "[::1]") and (not origin or origin.split("//")[-1].rsplit(":", 1)[0].lower() in ("127.0.0.1", "localhost", "[::1]"))

    def do_GET(self):
        path = self.path.split("?")[0]
        if not self.from_this_computer():
            return self._send(403, {"error": "forbidden"})
        try:
            if path == "/":
                path = "/index.html"
            if path.startswith("/api/"):
                return self.api_get(path)
            m = SOUND_RE.match(path)
            if m:
                full = os.path.join(self.app.sounds_dir, m.group(1), m.group(2) + ".ogg")
                if os.path.isfile(full):
                    with open(full, "rb") as fh:
                        return self._send(200, fh.read(), self.TYPES[".ogg"])
                return self._send(404, {"error": "not found"})
            name = os.path.basename(path)
            full = os.path.join(WEB, name)
            if os.path.splitext(name)[1] in self.TYPES and os.path.isfile(full):
                with open(full, "rb") as fh:
                    return self._send(200, fh.read(), self.TYPES[os.path.splitext(name)[1]])
            self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": repr(e)})

    def api_get(self, path):
        parts = path.strip("/").split("/")
        if parts == ["api", "status"]:
            return self._send(200, {"version": __version__, "fights": len(self.app.fight_ids()), "data": self.app.data,
                                    "techniques": [{"id": t, "name": LABELS[t], "short": SHORT[t], "family": FAMILY[t], "tier": TIER_NAMES[TIER[t]],
                                                     "requires": REQUIRES[t], "definition": DEFINITIONS[t]} for t in TECHNIQUES],
                                    "families": [n for n, _ in FAMILIES],
                                    "execution": [{"id": x, "name": EXECUTION_LABELS[x]} for x in EXECUTION],
                                    "fails": [{"id": x, "name": FAIL_LABELS[x]} for x in FAILS],
                                    "reads": self.app.readers.reads, "unconfirmed": self.app.readers.unconfirmed, "usage": self.app.readers.answers.usage if self.app.readers.answers else None, "models": self.app.readers.versions,
                                    "bands": [{"id": k, "name": n, "lo": lo, "hi": None if hi == float("inf") else hi}
                                              for k, n, lo, hi in DIST_BANDS],
                                    "tiers": PLAYER_TIERS, "profile": self.app.me})
        if parts == ["api", "live"]:
            return self._send(200, {"mod": self.app.mods > 0, "fights": len(self.app.fight_ids()), "reading": self.app.reading})
        if parts == ["api", "sounds"]:
            return self._send(200, self.app.sound_index())
        if parts == ["api", "fights"]:
            return self._send(200, self.app.fight_list())
        if parts == ["api", "stats"]:
            return self._send(200, stats.everything(self.app.all_reviews(), self.app.readers.guide.norms if self.app.readers.guide is not None else None))
        if len(parts) >= 3 and parts[1] == "fight" and ID_RE.match(parts[2]) and os.path.exists(self.app.fight_path(parts[2])):
            if len(parts) == 3:
                return self._send(200, self.app.review(parts[2]))
            if parts[3:] == ["frames"]:
                return self._send(200, self.app.frames(parts[2]))
            if parts[3:] == ["thumb"]:
                return self._send(200, self.app.thumb(parts[2]))
        self._send(404, {"error": "not found"})

    def do_POST(self):
        parts = self.path.split("?")[0].strip("/").split("/")
        if not self.from_this_computer():
            return self._send(403, {"error": "forbidden"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 1_000_000:
                return self._send(413, {"error": "too large"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if len(parts) == 4 and parts[1] == "fight" and parts[3] == "labels" and ID_RE.match(parts[2]) \
                    and os.path.exists(self.app.fight_path(parts[2])):
                return self._send(200, self.app.save_labels(parts[2], body))
            if parts == ["api", "profile"]:
                return self._send(200, self.app.save_profile(body))
            self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(400, {"error": repr(e)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(os.path.dirname(SERVER_DIR), "data"))
    ap.add_argument("--mod-port", type=int, default=47310)
    ap.add_argument("--web-port", type=int, default=47320)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--models", default=MODELS, help="the models folder (default: server/models)")
    args = ap.parse_args()
    app = App(os.path.abspath(args.data), os.path.abspath(args.models))
    ModHandler.app = Web.app = app
    web = WebServer(("127.0.0.1", args.web_port), Web)
    threading.Thread(target=web.serve_forever, daemon=True).start()
    mod = ModServer(("127.0.0.1", args.mod_port), ModHandler)
    url = f"http://127.0.0.1:{args.web_port}/"
    print(f"Sword Coach {__version__}: review page {url}  (mod port {args.mod_port}, data {app.data})", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        mod.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
