// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import net.minecraft.world.phys.Vec3;

/**
 * Velocities the server set this tick (knockback and other pushes) for you and your opponent, exactly as
 * the packets carried them. Filled by the motion mixin, read and cleared once per tick by FightWatcher.
 */
public final class Knockback {
    static int meId = -1, oppId = -1;
    private static final float[] tick = new float[8];   // you x y z count, them x y z count

    private Knockback() {
    }

    public static void seen(int entityId, Vec3 v) {
        int base = entityId == meId ? 0 : entityId == oppId ? 4 : -1;
        if (base < 0) return;
        tick[base] = (float) v.x;
        tick[base + 1] = (float) v.y;
        tick[base + 2] = (float) v.z;
        tick[base + 3] += 1;
    }

    /** This tick's values, then cleared for the next. */
    static float[] take() {
        float[] out = tick.clone();
        java.util.Arrays.fill(tick, 0f);
        return out;
    }
}
