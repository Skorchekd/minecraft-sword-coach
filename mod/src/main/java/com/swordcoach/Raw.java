// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.world.entity.InterpolationHandler;
import net.minecraft.world.phys.Vec3;

/**
 * One tick of what this client sees, in the layout the server's fields.py RAW_FIELDS lists:
 * you exactly, the opponent at the position the server last sent (the interpolation target, not
 * the smoothed body we draw), their health as {@link OppHealth} reads it (the name tag where the
 * server hides the real number), and both pings from the tab list.
 */
final class Raw {
    static final String[] FIELDS = {"sx", "sy", "sz", "syaw", "spitch", "sground", "ssprint", "sfall", "shurt", "sinv",
            "shp", "scharge", "sswing",
            "ox", "oy", "oz", "oyaw", "oground", "osprint", "osneak", "ohurt", "ohp", "oswing",
            "ping_s", "ping_o"};
    static final int N = FIELDS.length;

    private Raw() {
    }

    static float[] of(Minecraft mc, LocalPlayer me, AbstractClientPlayer opp, float oppHealth) {
        float[] r = new float[N];
        r[0] = (float) me.getX();
        r[1] = (float) me.getY();
        r[2] = (float) me.getZ();
        r[3] = me.getYRot();
        r[4] = me.getXRot();
        r[5] = me.onGround() ? 1 : 0;
        r[6] = me.isSprinting() ? 1 : 0;
        r[7] = (float) me.fallDistance;
        r[8] = me.hurtTime;
        r[9] = me.invulnerableTime;
        r[10] = me.getHealth();
        r[11] = me.getAttackStrengthScale(0.5f);
        r[12] = me.swinging ? 1 : 0;
        InterpolationHandler interp = opp.getInterpolation();
        boolean moving = interp != null && interp.hasActiveInterpolation();
        Vec3 t = moving ? interp.position() : opp.position();
        r[13] = (float) t.x;
        r[14] = (float) t.y;
        r[15] = (float) t.z;
        r[16] = moving ? interp.yRot() : opp.getYRot();
        r[17] = opp.onGround() ? 1 : 0;
        r[18] = opp.isSprinting() ? 1 : 0;
        r[19] = opp.isCrouching() ? 1 : 0;
        r[20] = opp.hurtTime;
        r[21] = oppHealth;
        r[22] = opp.swinging ? 1 : 0;
        r[23] = ping(mc, me);
        r[24] = ping(mc, opp);
        return r;
    }

    private static float ping(Minecraft mc, AbstractClientPlayer p) {
        if (mc.getConnection() == null) return 0;
        PlayerInfo info = mc.getConnection().getPlayerInfo(p.getUUID());
        return info == null ? 0 : info.getLatency();
    }
}
