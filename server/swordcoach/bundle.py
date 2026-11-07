# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""Pack your saved fights and labels into one zip to share, after checking every file reads back.

The zip holds data/fights/*.scf (already compressed, stored as is), data/labels/*.json and a manifest.json (app and
model versions, your tier if you set one on the Your data tab, this install's id, what each fight carries, totals and
labels per technique). Broken files are left out and listed. Nothing is uploaded.

    python -m swordcoach.bundle [--data DIR] [--out DIR]
"""
import argparse
import json
import os
import time
import zipfile

import numpy as np

from . import __version__, profile, store
from .fields import TECHNIQUES
from .readers import Readers

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(os.path.dirname(SERVER_DIR), "data"))
    ap.add_argument("--out", default=os.path.dirname(SERVER_DIR))
    args = ap.parse_args()
    fdir, ldir = os.path.join(args.data, "fights"), os.path.join(args.data, "labels")
    names = sorted(f for f in os.listdir(fdir) if f.endswith(".scf")) if os.path.isdir(fdir) else []
    if not names:
        print("No fights saved yet. Play with the mod and the server running first.")
        return 1
    fights, broken, ticks = [], [], 0
    for n in names:
        try:
            info, a = store.read(os.path.join(fdir, n))
            T = len(a["raw"])
            if not np.isfinite(a["raw"]).all():
                raise ValueError("non-finite numbers in the record")
            ticks += T
            fights.append({"file": n, "ticks": T, "server": info.get("server"), "result": info.get("result"),
                           "has": sorted(k for k in a if k != "raw"), "intents": len(info.get("intent") or []),
                           "opponent": info.get("opponent"), "app": info.get("app")})
        except Exception as e:
            broken.append({"file": n, "error": repr(e)})
    labels, relabels = [], 0
    per_tech = {}
    for n in (sorted(os.listdir(ldir)) if os.path.isdir(ldir) else []):
        if not n.endswith(".json"):
            continue
        try:
            with open(os.path.join(ldir, n), encoding="utf-8") as fh:
                ex = json.load(fh).get("exchanges", {})
            relabels += len(ex)
            for v in ex.values():
                for side in ("you", "them"):
                    for t in (v.get(side), v.get(side + "2")):
                        if t in TECHNIQUES:
                            per_tech.setdefault(t, {"you": 0, "them": 0})[side] += 1
            labels.append(n)
        except Exception as e:
            broken.append({"file": "labels/" + n, "error": repr(e)})
    me = profile.load(args.data)
    manifest = {"made": time.strftime("%Y-%m-%dT%H:%M:%S"), "app": __version__,
                "models": Readers(os.path.join(SERVER_DIR, "models")).versions,
                "tier": me["tier"], "install": profile.install_id(profile.install_secret()),
                "labels_per_technique": per_tech,
                "fights": len(fights), "ticks": ticks, "hours": round(ticks / 20 / 3600, 2), "relabels": relabels,
                "fights_with_intent": sum(1 for f in fights if f["intents"]),
                "opponents": len({f["opponent"] for f in fights if f["opponent"]}),
                "broken": broken, "fight_list": fights}
    path = os.path.join(args.out, "fightdata-" + time.strftime("%Y%m%d-%H%M") + ".zip")
    with zipfile.ZipFile(path + ".tmp", "w") as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=1), zipfile.ZIP_DEFLATED)
        for f in fights:
            z.write(os.path.join(fdir, f["file"]), "fights/" + f["file"], zipfile.ZIP_STORED)
        for n in labels:
            z.write(os.path.join(ldir, n), "labels/" + n, zipfile.ZIP_DEFLATED)
    os.replace(path + ".tmp", path)
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
    if bad:
        print(f"The zip did not check out ({bad}); try again.")
        return 1
    mb = os.path.getsize(path) / 1e6
    print(f"Made {os.path.basename(path)}: {len(fights)} fights ({manifest['hours']} h), {relabels} relabelled exchanges, "
          f"{mb:.1f} MB.")
    if not me["tier"]:
        print("  Your tier is not set: set it on the review page's Your data tab and bundle again, so your fights can be"
              " put with players of your level.")
    for b in broken:
        print(f"  left out {b['file']}: {b['error']}")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
