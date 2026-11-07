# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""Fight files: one file per fight, lossless and small.

Layout: b"SCF2", a 4-byte little-endian header length, the header (JSON: fight info and the array list), then one
LZMA stream with every array's bytes, byte-planed (all first bytes, then all second bytes, ...) column by column,
which is what makes slowly changing numbers compress well. Before that, whole-number columns are stored as
tick-to-tick differences and float columns XOR'd with the previous tick's bits (both undone exactly on read).
Arrays keep exactly what the mod sent:
  raw     float32 [T, 25]  the per-tick record (the mod's own floats)
  keys    uint8   [T]      your 8 keys as bits (forward, back, left, right, jump, sneak, sprint, click)
  opitch  float32 [T]      their pitch
  drawn   int32   [T, 20]  both players as your client drew them, in thousandths (the mod rounds to 0.001)
  ticks   int32   [T]      client tick numbers
  kb      float32 [T, 8]   velocities the server set that tick (knockback): you x, y, z, packets, then them the same
  ev      int32   [T]      hit events that tick as the server sent them: attack sounds and crit particles (bits in
                           fields.py, SOUND_KINDS / EV_CRIT_ON)
  ohp_est float32 [T]      their health as worked out from your hits, tick by tick from the past only (hpguess.py), saved with every
                           fight from server 1.8.2 on: where the server hides their health this is all there is (info "opp_health_est")
"""
import json
import lzma
import os
import struct

import numpy as np

MAGIC = b"SCF2"


def _encode(a):
    a = np.ascontiguousarray(a)
    if a.dtype.kind == "i":
        return np.concatenate([a[:1], np.diff(a, axis=0)]).astype(a.dtype)
    if a.dtype == np.float32:
        u = a.view(np.uint32)
        return np.concatenate([u[:1], u[1:] ^ u[:-1]]).view(np.float32)
    return a


def _decode(a):
    if a.dtype.kind == "i":
        return np.cumsum(a, axis=0, dtype=a.dtype)
    if a.dtype == np.float32:
        return np.bitwise_xor.accumulate(a.view(np.uint32), axis=0).view(np.float32)
    return a


def _planes(a):
    a = np.ascontiguousarray(a)
    cols = a.reshape(len(a), -1).T if a.ndim > 1 else a[None]
    b = np.ascontiguousarray(cols).view(np.uint8).reshape(cols.shape[0], cols.shape[1], a.dtype.itemsize)
    return np.ascontiguousarray(b.transpose(0, 2, 1)).tobytes()


def _unplanes(buf, dtype, shape):
    dtype = np.dtype(dtype)
    n = shape[0]
    ncol = int(np.prod(shape[1:])) if len(shape) > 1 else 1
    b = np.frombuffer(buf, np.uint8).reshape(ncol, dtype.itemsize, n).transpose(0, 2, 1)
    cols = np.ascontiguousarray(b).view(dtype).reshape(ncol, n)
    return (cols.T if len(shape) > 1 else cols[0]).reshape(shape).copy()


def pack_keys(keys):
    k = (np.asarray(keys)[:, :8] > 0.5).astype(np.uint8)
    return (k * (1 << np.arange(8, dtype=np.uint8))).sum(1).astype(np.uint8)


def unpack_keys(b):
    return ((np.asarray(b, np.uint8)[:, None] >> np.arange(8, dtype=np.uint8)) & 1).astype(np.float32)


def write(path, info, raw, keys=None, opitch=None, drawn=None, ticks=None, kb=None, ev=None, ohp_est=None):
    arrays = {"raw": np.asarray(raw, np.float32)}
    T = len(arrays["raw"])
    if keys is not None:
        arrays["keys"] = pack_keys(keys)
    if opitch is not None:
        arrays["opitch"] = np.asarray(opitch, np.float32)
    if drawn is not None and len(drawn) == T:
        arrays["drawn"] = np.round(np.asarray(drawn, np.float64) * 1000.0).astype(np.int32)
    if ticks is not None and len(ticks) == T:
        arrays["ticks"] = np.asarray(ticks, np.int32)
    if kb is not None and len(kb) == T:
        arrays["kb"] = np.asarray(kb, np.float32)
    if ev is not None and len(ev) == T:
        arrays["ev"] = np.asarray(ev, np.int32)
    if ohp_est is not None and len(ohp_est) == T:
        arrays["ohp_est"] = np.asarray(ohp_est, np.float32)
    meta, body = [], []
    for name, a in arrays.items():
        buf = _planes(_encode(a))
        meta.append({"name": name, "dtype": a.dtype.str, "shape": list(a.shape), "bytes": len(buf)})
        body.append(buf)
    header = json.dumps({"info": info, "arrays": meta}, separators=(",", ":")).encode()
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(MAGIC + struct.pack("<I", len(header)) + header)
        fh.write(lzma.compress(b"".join(body), preset=9 | lzma.PRESET_EXTREME))
    os.replace(tmp, path)


def read_info(path):
    with open(path, "rb") as fh:
        if fh.read(4) != MAGIC:
            raise ValueError("not a fight file")
        n = struct.unpack("<I", fh.read(4))[0]
        return json.loads(fh.read(n))["info"]


def read(path):
    """(info, arrays) with keys unpacked to [T, 8] floats and drawn back in blocks."""
    with open(path, "rb") as fh:
        if fh.read(4) != MAGIC:
            raise ValueError("not a fight file")
        n = struct.unpack("<I", fh.read(4))[0]
        header = json.loads(fh.read(n))
        body = lzma.decompress(fh.read())
    out, pos = {}, 0
    for m in header["arrays"]:
        a = _decode(_unplanes(body[pos:pos + m["bytes"]], m["dtype"], tuple(m["shape"])))
        pos += m["bytes"]
        if m["name"] == "keys":
            a = unpack_keys(a)
        elif m["name"] == "drawn":
            a = a.astype(np.float64) / 1000.0
        out[m["name"]] = a
    return header["info"], out
