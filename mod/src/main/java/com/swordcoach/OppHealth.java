// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.swordcoach.mixin.TextDisplayAccessor;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.network.chat.numbers.StyledFormat;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.scores.DisplaySlot;
import net.minecraft.world.scores.ReadOnlyScoreInfo;

import java.util.ArrayList;
import java.util.List;

/**
 * The opponent's health as this client can honestly know it. Some servers (pvphq.com among
 * them) randomise other players' health attribute and draw the real number over their head
 * instead: a text display, a below-name score or the display name reading "13 ❤".
 *
 * <p>In order: the drawn number when one parses (minus absorption; the attribute instead when it
 * agrees with it); else the attribute, unless the server spoofs it or a drawn number has been
 * seen this fight; else the last value. Only the number and where it came from are kept, never
 * the text, which can carry the player's name.</p>
 */
final class OppHealth {
    static final String TEXT = "text_display", TEXT_BARE = "text_display_bare", BELOW = "below_name",
            NAME = "display_name", VOUCHED = "vouched", ENTITY = "entity", HELD = "held";

    private float health = 20f;
    private boolean tagSeen;
    private int mismatch;
    boolean spoofed;
    String source = HELD;

    /** A new fight: full health until something says otherwise. */
    void reset(boolean spoofedServer) {
        health = 20f;
        tagSeen = false;
        mismatch = 0;
        spoofed = spoofedServer;
        source = HELD;
    }

    float health() {
        return health;
    }

    float update(Minecraft mc, AbstractClientPlayer p) {
        float ent = p.getHealth(), max = p.getMaxHealth() > 0f ? p.getMaxHealth() : 20f;
        String[] src = new String[1];
        double shown = shown(mc, p, src);
        // A drawn bar that keeps disagreeing with the attribute is proof the attribute lies.
        if (Double.isFinite(shown) && Math.abs(shown - ent) > 1.0 && ++mismatch >= 40) spoofed = true;
        if (Double.isFinite(shown)) {
            float raw = (float) shown - Math.max(0f, p.getAbsorptionAmount());
            // Rounded up to a point (a tenth under 3): the true health is in (raw - 1, raw].
            boolean vouched = !spoofed && ent > raw - 1.01f && ent <= raw + 0.11f && ent >= 0f && ent <= max + 1e-3f;
            health = vouched ? ent : Math.max(0f, Math.min(max, raw));
            tagSeen = true;
            source = vouched ? VOUCHED : src[0];
        } else if (!spoofed && !tagSeen && ent >= 0f && ent <= max + 1e-3f) {
            health = ent;
            source = ENTITY;
        } else {
            source = HELD;
        }
        return health;
    }

    /** The health number the server drew for {@code p}, or NaN; {@code src[0]} says where. */
    private static double shown(Minecraft mc, AbstractClientPlayer p, String[] src) {
        List<Entity> near = new ArrayList<>(p.getPassengers());
        for (int i = 0; i < near.size() && i < 16; ++i) near.addAll(near.get(i).getPassengers());
        if (mc.level != null)
            near.addAll(mc.level.getEntitiesOfClass(Display.TextDisplay.class,
                    new AABB(p.getX() - 0.8, p.getY() + 1.0, p.getZ() - 0.8, p.getX() + 0.8, p.getY() + 3.6, p.getZ() + 0.8)));
        List<String> texts = new ArrayList<>();
        for (Entity e : near) {
            if (!(e instanceof Display.TextDisplay display)) continue;
            try {
                var c = ((TextDisplayAccessor) display).swordcoach$getText();
                if (c != null) texts.add(c.getString());
            } catch (RuntimeException unreadable) {
                // next display
            }
        }
        // A heart anywhere beats a bare number anywhere: a rank or a level drawn over the head
        // is also just a number.
        for (String text : texts) {
            double v = HealthText.parse(text, false);
            if (Double.isFinite(v)) {
                src[0] = TEXT;
                return v;
            }
        }
        for (String text : texts) {
            double v = HealthText.parse(text, true);
            if (Double.isFinite(v)) {
                src[0] = TEXT_BARE;
                return v;
            }
        }
        if (mc.level != null) {
            var board = mc.level.getScoreboard();
            var objective = board.getDisplayObjective(DisplaySlot.BELOW_NAME);
            if (objective != null) {
                var info = board.getPlayerScoreInfo(p, objective);
                if (info != null) {
                    String text = ReadOnlyScoreInfo.safeFormatValue(info, objective.numberFormatOrDefault(StyledFormat.NO_STYLE)).getString()
                            + " " + objective.getDisplayName().getString();
                    double v = HealthText.parse(text, false);
                    if (!Double.isFinite(v) && text.contains("❤")) v = info.value();
                    if (Double.isFinite(v)) {
                        src[0] = BELOW;
                        return v;
                    }
                }
            }
        }
        double v = HealthText.parse(p.getDisplayName().getString(), false);
        if (Double.isFinite(v)) src[0] = NAME;
        return v;
    }
}
