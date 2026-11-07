# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""The two technique readers (ONNX) and the spot model, run on a whole fight."""
import hashlib
import json
import os

import numpy as np
import onnxruntime as ort

from . import features as fx
from .fields import DIST_BANDS, FAMILIES, FAMILY, LABELS, REQUIRES, SEG, TECHNIQUES, band_of
from .profile import tier_value
from .spot import TreeEnsemble, spot_features

BANDS = [k for k, _, _, _ in DIST_BANDS]

YOU_WITH_KEYS, THEM, YOU_NO_KEYS = 0, 1, 2


def fold_matrix(reads, n):
    """[n, n]: each read technique keeps its probability; one the reader does not read hands its probability to the
    nearest read techniques it builds on (fields.REQUIRES), so a not-yet-read P-crit counts as a jump crit instead of
    being spread over everything."""
    def up(t):
        out = set()
        for r in REQUIRES[t]:
            out |= {r} if r in reads else up(r)
        return out
    F = np.zeros((n, n), np.float32)
    for j, t in enumerate(TECHNIQUES[:n]):
        to = [j] if t in reads else [TECHNIQUES.index(a) for a in up(t) if TECHNIQUES.index(a) < n]
        for a in to:
            F[j, a] = 1.0 / len(to)
    return F


def known_index(t, n):
    """t's place in fields.TECHNIQUES if it is one of the first n, else that of the first technique it builds on that
    is (fields.REQUIRES), else None."""
    i = TECHNIQUES.index(t)
    if i < n:
        return i
    for r in REQUIRES[t]:
        k = known_index(r, n)
        if k is not None:
            return k
    return None


class AnswerModel:
    """Experimental: how each answer usually goes from this spot after the other player's last technique, in recorded
    exchanges against real players (HP over 1.2 s vs what the spot usually trades, players' own levels taken out), and
    how often each answer is used there. A small network (models/answer_model.onnx).

    Its inputs are named in the model's metadata (`inputs`, comma-separated, in order):
      spot     the 32 spot features (spot.spot_features): distance, health, momentum, ...
      familyK  the other player's previous technique family, one-hot over the first K of fields.FAMILIES
      prev     the other player's previous technique, one-hot over the techniques it was trained with (the first of
               fields.TECHNIQUES)
      band     the distance band this exchange starts in, one-hot over fields.DIST_BANDS
      tier     your tier as profile.tier_value: [strength, known]
    A model without the entry is the first one: spot + the first 5 families."""
    MIN_SHARE = 0.03
    ENGAGED = 6.0
    # Where each distance band is looked at for "the same moment at other distances".
    BAND_AT = {"close": 1.8, "reach": 3.0, "edge": 4.0, "apart": 5.0}

    def __init__(self, session):
        self.s = session
        meta = session.get_modelmeta().custom_metadata_map.get("inputs")
        width = session.get_inputs()[0].shape[1]
        self.inputs = meta.split(",") if meta else ["spot", f"family{width - 32}"]
        fam = [x for x in self.inputs if x.startswith("family")]
        self.families = int(fam[0][6:]) if fam else len(FAMILIES)
        # How many techniques "prev" covers: the list the model was trained with. Labels added since go in as what they build on.
        other = {"spot": 32, "band": len(DIST_BANDS), "tier": 2}
        self.n_prev = width - sum(self.families if x.startswith("family") else other.get(x, 0) for x in self.inputs if x != "prev")
        # How often each technique shows at each distance in recorded fights played by people (per 100 exchanges), from a model that carries it.
        usage = session.get_modelmeta().custom_metadata_map.get("usage")
        self.usage = json.loads(usage) if usage else None
        self.tiers = session.get_modelmeta().custom_metadata_map.get("tiers") == "learned"

    def features(self, X, their_last, tier=None, sure=None):
        """sure [n]: whether their move is known well enough to name; where it is not, only its family goes in, as in training."""
        X = np.asarray(X, np.float32)
        parts = []
        for name in self.inputs:
            if name == "spot":
                parts.append(X)
            elif name.startswith("family"):
                f = np.array([FAMILY[t] for t in their_last])
                parts.append(np.eye(len(FAMILIES), dtype=np.float32)[f][:, :self.families])
            elif name == "prev":
                prev = np.zeros((len(their_last), self.n_prev), np.float32)
                for i, t in enumerate(their_last):
                    k = known_index(t, self.n_prev)
                    if k is not None:
                        prev[i, k] = 1.0
                parts.append(prev if sure is None else prev * np.asarray(sure, np.float32)[:, None])
            elif name == "band":
                parts.append(np.eye(len(DIST_BANDS), dtype=np.float32)[[BANDS.index(band_of(d)) for d in X[:, 3] * 6.0]])
            elif name == "tier":
                # Only a model that says it learned from tiers gets one: to the others it is an input they never saw vary.
                parts.append(np.tile(np.asarray(tier_value(tier if self.tiers else None), np.float32), (len(X), 1)))
            else:
                raise ValueError(f"answer model input {name!r} is not known to this version")
        return np.concatenate(parts, 1)

    def _options(self, value, share, i):
        return [{"id": t, "name": LABELS[t], "value": round(float(value[i, k]), 2), "share": round(float(share[i, k]), 3)}
                for k, t in enumerate(TECHNIQUES[:share.shape[1]]) if share[i, k] >= self.MIN_SHARE]

    def lookup(self, X, their_last, tier=None, sure=None):
        """X [n, 32] spot features, their_last [n] technique ids -> per exchange the answers used often enough there,
        best first, and the best few at each other distance with everything else the same (None where the players
        were not engaged, or after a family it was not trained with)."""
        if not len(X):
            return []
        X = np.asarray(X, np.float32)
        f = np.array([FAMILY[t] for t in their_last])
        value, share = self.s.run(None, {"x": self.features(X, their_last, tier, sure)})
        sweep = {}
        for k, d in self.BAND_AT.items():
            Xd = X.copy()
            Xd[:, 3] = d / 6.0
            sweep[k] = self.s.run(None, {"x": self.features(Xd, their_last, tier, sure)})
        out = []
        for i in range(len(X)):
            if X[i, 3] * 6.0 >= self.ENGAGED or f[i] >= self.families:
                out.append(None)
                continue
            opts = sorted(self._options(value, share, i), key=lambda o: -o["value"])
            if not opts:
                out.append(None)
                continue
            by_band = {k: sorted(self._options(v, s_, i), key=lambda o: -o["value"])[:3] for k, (v, s_) in sweep.items()}
            out.append({"options": opts, "by_band": by_band})
        return out


class Readers:
    def __init__(self, models_dir):
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        opts.log_severity_level = 3
        load = lambda n: ort.InferenceSession(os.path.join(models_dir, n), opts, providers=["CPUExecutionProvider"])
        self.technique = load("technique_reader.onnx")
        self.keys = load("key_reader.onnx")
        meta = lambda s: s.get_modelmeta().custom_metadata_map.get("model_version")
        self.versions = {"technique_reader": meta(self.technique), "key_reader": meta(self.keys)}
        # The techniques the reader reads: its metadata `reads` (comma-separated ids) when it has one, else the first
        # ones of fields.TECHNIQUES, one per output. The rest can only be labelled; the reader never names them.
        n_out = self.technique.get_outputs()[0].shape[1]
        listed = self.technique.get_modelmeta().custom_metadata_map.get("reads")
        self.reads = [t for t in (listed.split(",") if listed else TECHNIQUES[:n_out]) if t in TECHNIQUES[:n_out]]
        self.fold = fold_matrix(self.reads, n_out)
        # A reader may look further back than the first one (metadata `pre`), and may also say how likely each technique
        # is on its own (a second output), so that two overlapping techniques can both be true.
        rmeta = self.technique.get_modelmeta().custom_metadata_map
        self.pre, self.post = int(rmeta.get("pre") or fx.PRE), int(rmeta.get("post") or 0)
        # Read from key patterns but not yet confirmed by players' labels: the pages say so.
        self.unconfirmed = [t for t in (rmeta.get("unconfirmed") or "").split(",") if t]
        self.multi = len(self.technique.get_outputs()) > 1
        # Reading the other player from how they moved is harder than reading your own keys: a reader may name fewer on them.
        them = [t for t in (rmeta.get("reads_them") or "").split(",") if t]
        self.reads_them = them or self.reads
        self.spot = TreeEnsemble(os.path.join(models_dir, "spot_value.npz"))
        self.reads_dir = None     # set by the server: where saved fights' reads are kept
        self.reads_tag = hashlib.sha256(open(os.path.join(models_dir, "technique_reader.onnx"), "rb").read() + open(os.path.join(models_dir, "key_reader.onnx"), "rb").read()).hexdigest()[:12]
        a = os.path.join(models_dir, "answer_model.onnx")
        self.answers = AnswerModel(load("answer_model.onnx")) if os.path.exists(a) else None
        if self.answers is not None:
            self.versions["answer_model"] = meta(self.answers.s)
        from .hpguess import HpGuess
        self.hp = HpGuess(models_dir)       # their health where the server hides it (rule figures without models/hp_model.npz)
        if self.hp.trees is not None:
            self.versions["hp_model"] = str(np.load(os.path.join(models_dir, "hp_model.npz"))["model_version"])
        self.guide = None
        if os.path.exists(os.path.join(models_dir, "guide_model.onnx")):
            from .guide import GuideModel
            self.guide = GuideModel(load("guide_model.onnx"))
            self.versions["guide_model"] = meta(self.guide.s)

    def their_keys(self, raw, opitch):
        """[T, 8] probabilities of the other player's keys, read from how they moved."""
        w = fx.key_windows(fx.key_frames(raw, opitch))
        return self.keys.run(None, {"x": w})[0] if len(w) else np.zeros((0, 8), np.float32)

    def techniques(self, F, starts, view):
        return self._run(F, starts, view)[0]

    def _run(self, F, starts, view):
        """One call per exchange (sums to 1) and, from a reader that has it, each technique on its own (else None)."""
        X = fx.exchange_windows(F, starts, self.pre, self.post)
        if not len(X):
            return np.zeros((0, len(TECHNIQUES)), np.float32), None
        out = self.technique.run(None, {"x": X, "view": np.full(len(X), view, np.int64)})
        P = out[0] @ self.fold
        P = P / np.maximum(P.sum(1, keepdims=True), 1e-9)
        if not self.multi:
            return P, None
        read = np.isin(np.arange(out[1].shape[1]), [TECHNIQUES.index(t) for t in (self.reads_them if view == THEM else self.reads)])
        return P, out[1] * read

    def read(self, raw, opitch, keys=None):
        """Every exchange of a fight: start ticks, your technique and theirs (probabilities), their keys per tick."""
        return self.read_multi(raw, opitch, keys)[:4]

    def read_saved(self, fid, raw, opitch, keys=None):
        """read_multi for a saved fight, kept on disk per reader version: a saved fight never changes, and with hundreds of them the pages would otherwise read every one again after each restart."""
        path = None
        if self.reads_dir and fid:
            os.makedirs(self.reads_dir, exist_ok=True)
            path = os.path.join(self.reads_dir, f"{fid}-{self.reads_tag}.npz")
            try:
                with np.load(path) as d:
                    if len(d["you"]) == len(np.arange(1, len(raw) - SEG + 1, SEG)):
                        m = (d["m_you"], d["m_them"]) if "m_you" in d else (None, None)
                        return d["starts"], d["you"], d["them"], None, m[0], m[1]
            except (OSError, ValueError, KeyError):
                pass
        out = self.read_multi(raw, opitch, keys)
        if path:
            arrays = dict(starts=out[0], you=out[1].astype(np.float32), them=out[2].astype(np.float32))
            if out[4] is not None:
                arrays.update(m_you=out[4].astype(np.float32), m_them=out[5].astype(np.float32))
            tmp = path + ".tmp.npz"
            np.savez_compressed(tmp, **arrays)
            os.replace(tmp, path)
        return out

    def read_multi(self, raw, opitch, keys=None):
        """read() plus each technique on its own, for you and for them (None from a one-call reader)."""
        raw = np.asarray(raw, np.float64)
        opitch = np.zeros(len(raw)) if opitch is None else np.asarray(opitch, np.float64)
        starts = np.arange(1, len(raw) - SEG + 1, SEG)
        tk = self.their_keys(raw, opitch)
        mine = fx.own_keys(keys) if keys is not None else np.zeros((len(raw), 8))
        you, m_you = self._run(fx.view(raw, opitch, mine, True), starts, YOU_WITH_KEYS if keys is not None else YOU_NO_KEYS)
        them, m_them = self._run(fx.view(raw, opitch, tk, False), starts, THEM)
        return starts, you, them, tk, m_you, m_them

    def read_latest(self, raw, opitch, keys=None):
        """The last exchange that has ended, with whatever ticks after it there are, reading only the ticks it needs: (its index, you, them). The in-fight tip must not cost more as a fight goes on, and a whole-fight read would."""
        raw = np.asarray(raw, np.float64)
        opitch = np.zeros(len(raw)) if opitch is None else np.asarray(opitch, np.float64)
        T = len(raw)
        starts = np.arange(1, T - SEG + 1, SEG)
        if not len(starts):
            return None
        s = int(starts[-1])
        a = max(0, s - self.pre - fx.KEY_PAST - fx.KEY_FUT - 2)
        at = np.array([s - a])
        r, op = raw[a:], opitch[a:]
        tk = self.their_keys(r, op)
        mine = fx.own_keys(np.asarray(keys)[a:]) if keys is not None else np.zeros((len(r), 8))
        you = self.techniques(fx.view(r, op, mine, True), at, YOU_WITH_KEYS if keys is not None else YOU_NO_KEYS)
        them = self.techniques(fx.view(r, op, tk, False), at, THEM)
        return len(starts) - 1, you[0], them[0]

    def expected(self, raw, starts):
        """What an exchange from each start usually trades over 1.2 s (HP dealt minus taken), from real fights."""
        if not len(starts):
            return np.zeros(0)
        return self.spot.predict(spot_features(raw, starts))
