# Copyright and licences

Sword Coach
Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx, the holders of MCA, together trading as
MCA - Minecraft Combat AI (https://minecraftcombatai.com/).

## The code: GNU GPL v3

The mod (`mod/`), the server (`server/swordcoach/`), the review page (`server/web/`) and the batch files are free
software: you can redistribute them and/or modify them under the terms of the GNU General Public License, version 3,
as published by the Free Software Foundation (`LICENSE`, SPDX `GPL-3.0-only`).

They are distributed in the hope that they will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

If you share a modified version, keep the copyright notices, say that you changed it, and license your changes under
the GPL v3 as well.

## The model files: not covered by the GPL

The trained model files in `server/models/` (`technique_reader.onnx`, `key_reader.onnx`, `answer_model.onnx`,
`guide_model.onnx`, `spot_value.npz`, `hp_model.npz`) are
**not** part of the GPL-licensed code. They are licensed separately under the MCA Sword Coach Model Licence in
`server/models/LICENSE`: personal, non-commercial use with Sword Coach; no separate redistribution, extraction,
conversion or training of other models from them.

## Third-party parts

- `mod/gradlew`, `mod/gradlew.bat` and `mod/gradle/wrapper/` are the Gradle Wrapper, Copyright the original authors,
  licensed under the Apache License 2.0 (see the headers in those files).
- `server/web/three.module.js` and `server/web/three.core.js` are three.js, Copyright 2010-2026 three.js authors, under the
  MIT licence (`server/web/three.LICENSE.txt`). The pixel lettering on the page is MCA's own.
- The hit sounds the replays and the review page play are the player's own game's sound files (Mojang's, or their
  resource pack's), read from the running game on their computer. None are included in this repository, the mod jar
  or a fight bundle.
- Minecraft is a trademark of Mojang Studios. Sword Coach is not an official Minecraft product and is not approved by
  or associated with Mojang Studios or Microsoft. Fabric API is licensed under the Apache License 2.0 and is not
  included.
