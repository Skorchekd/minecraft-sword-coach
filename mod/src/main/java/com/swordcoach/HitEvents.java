// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import net.minecraft.core.Holder;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.Entity;

/**
 * What the server said about each hit this tick, for both of you: the attack sound it played at a player (crit,
 * knockback, strong, weak, sweep, no damage; that player attacked) and the crit / enchanted-hit particles it put on a
 * player (that player was hit). Filled by the hit events mixin from the server's own packets, read and cleared once
 * per tick by FightWatcher. Bit layout: server/swordcoach/fields.py (SOUND_KINDS, EV_CRIT_ON).
 */
public final class HitEvents {
    /** The attack sounds, in the bit order of SOUND_KINDS: you 0-5, them 6-11. */
    static final SoundEvent[] KINDS = {SoundEvents.PLAYER_ATTACK_CRIT, SoundEvents.PLAYER_ATTACK_KNOCKBACK,
            SoundEvents.PLAYER_ATTACK_STRONG, SoundEvents.PLAYER_ATTACK_WEAK, SoundEvents.PLAYER_ATTACK_SWEEP,
            SoundEvents.PLAYER_ATTACK_NODAMAGE};
    static final int CRIT_ON = 12, MAGIC_ON = 14;
    /** An attack sound further than this from both of you belongs to someone else. */
    private static final double NEAR = 2.5;

    static Entity me, opp;
    private static int bits;

    private HitEvents() {
    }

    /** A sound the server played at (x, y, z): an attack sound is played where the attacker stands. */
    public static void sound(Holder<SoundEvent> sound, double x, double y, double z) {
        Entity a = me, b = opp;
        if (a == null || b == null || sound == null) return;
        int k = -1;
        for (int i = 0; i < KINDS.length; i++) if (KINDS[i].location().equals(sound.value().location())) k = i;
        if (k < 0) return;
        double da = a.distanceToSqr(x, y, z), db = b.distanceToSqr(x, y, z);
        if (Math.min(da, db) > NEAR * NEAR) return;
        bits |= 1 << (6 * (da <= db ? 0 : 1) + k);
    }

    /** An entity animation the server sent: 4 crit particles, 5 enchanted-hit particles, on the player who was hit. */
    public static void animate(int entityId, int action) {
        if (action != 4 && action != 5) return;
        int on = me != null && entityId == me.getId() ? 0 : opp != null && entityId == opp.getId() ? 1 : -1;
        if (on < 0) return;
        bits |= 1 << ((action == 4 ? CRIT_ON : MAGIC_ON) + on);
    }

    /** This tick's events, then cleared for the next. */
    static int take() {
        int b = bits;
        bits = 0;
        return b;
    }
}
