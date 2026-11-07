// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * What this client drew for both players at the end of every tick of a fight, for the replays.
 * RAW keeps the opponent's network target, which is what the models read but moves in steps (the
 * server sends a player's position every other tick and the client smooths it over three); this
 * keeps the smoothed position you actually saw, head and body yaw, pitch, swing progress, hurt
 * time, crouch, what each of you held and wore, and what the server said about each tick's hits ({@link HitEvents}).
 * Replayed tick for tick it draws the same thing.
 * Frame i belongs to the same tick as RAW tick i, so the server's exchange indices apply to both.
 */
final class ReplayLog {
    static final int X = 0, Y = 1, Z = 2, HEAD = 3, BODY = 4, PITCH = 5, HURT = 6, ANIM = 7, SWING = 8, CROUCH = 9, F = 10;
    static final EquipmentSlot[] SLOTS = {EquipmentSlot.MAINHAND, EquipmentSlot.OFFHAND, EquipmentSlot.HEAD,
            EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};
    /** A jump this far in one tick is a teleport or respawn: the replay cuts instead of sliding. */
    static final double TELEPORT = 4.0;

    /** From this frame on, side `side` has `stack` in `slot`. */
    record Equip(int frame, int side, EquipmentSlot slot, ItemStack stack) {
    }

    final List<double[][]> frames = new ArrayList<>();     // [side 0 you, 1 them][F]
    final List<Boolean> cuts = new ArrayList<>();           // a gap or teleport just before this frame
    final List<Integer> events = new ArrayList<>();         // HitEvents bits of this frame's tick
    final List<Equip> equip = new ArrayList<>();
    /** Both players' health per frame [you, them], from the Sword Coach server: theirs as the server showed it, or worked out from your
     * hits where it hid it (healthEstimated). Empty until the server has sent it. */
    final List<float[]> health = new ArrayList<>();
    boolean healthEstimated;
    private final ItemStack[][] last = new ItemStack[2][SLOTS.length];
    private long lastTick = Long.MIN_VALUE;

    int size() {
        return frames.size();
    }

    void clear() {
        health.clear();
        frames.clear();
        cuts.clear();
        events.clear();
        equip.clear();
        last[0] = new ItemStack[SLOTS.length];
        last[1] = new ItemStack[SLOTS.length];
        lastTick = Long.MIN_VALUE;
    }

    /** One tick; `tick` counts client ticks, so a tick the opponent was missing shows as a gap. */
    void add(long tick, LivingEntity me, LivingEntity opp, int ev) {
        double[][] f = {state(me), state(opp)};
        boolean cut = lastTick != Long.MIN_VALUE && tick != lastTick + 1;
        addFrame(f, cut, ev);
        lastTick = tick;
        LivingEntity[] who = {me, opp};
        int at = frames.size() - 1;
        for (int s = 0; s < 2; s++)
            for (int k = 0; k < SLOTS.length; k++) {
                ItemStack st = who[s].getItemBySlot(SLOTS[k]);
                if (last[s][k] == null || !ItemStack.matches(last[s][k], st)) {
                    last[s][k] = st.copy();
                    equip.add(new Equip(at, s, SLOTS[k], st.copy()));
                }
            }
    }

    /** Appends one frame; a jump bigger than TELEPORT since the last one becomes a cut. */
    void addFrame(double[][] f, boolean cut, int ev) {
        if (!frames.isEmpty()) {
            double[][] p = frames.get(frames.size() - 1);
            for (int s = 0; s < 2; s++)
                if (Math.abs(f[s][X] - p[s][X]) + Math.abs(f[s][Y] - p[s][Y]) + Math.abs(f[s][Z] - p[s][Z]) > TELEPORT) cut = true;
        }
        frames.add(f);
        cuts.add(cut);
        events.add(ev);
    }

    /** The server's per-tick health of a fight, [[yours...], [theirs...]]; null clears it. */
    void setHealth(JsonArray hp, boolean estimated) {
        health.clear();
        healthEstimated = estimated;
        if (hp == null || hp.size() < 2) return;
        JsonArray a = hp.get(0).getAsJsonArray(), b = hp.get(1).getAsJsonArray();
        int n = Math.min(a.size(), b.size());
        for (int i = 0; i < n; i++) health.add(new float[]{a.get(i).getAsFloat(), b.get(i).getAsFloat()});
    }

    static double[] state(LivingEntity p) {
        return new double[]{p.getX(), p.getY(), p.getZ(), p.getYHeadRot(), p.yBodyRot, p.getXRot(), p.hurtTime,
                p.attackAnim, p.swinging ? 1 : 0, p.isCrouching() ? 1 : 0};
    }

    /**
     * A saved fight as the Sword Coach server sends it for a replay: "drawn" [T][20] (this layout, you then them) and
     * "cuts" (frames with a gap before them). Saved fights keep no equipment, so the dummies wear their default kit.
     */
    static ReplayLog fromServer(JsonObject m) {
        ReplayLog log = new ReplayLog();
        Set<Integer> cuts = new HashSet<>();
        if (m.has("cuts")) for (JsonElement c : m.getAsJsonArray("cuts")) cuts.add(c.getAsInt());
        for (JsonElement row : m.getAsJsonArray("drawn")) {
            JsonArray d = row.getAsJsonArray();
            double[][] f = new double[2][F];
            for (int s = 0; s < 2; s++)
                for (int q = 0; q < F; q++) f[s][q] = d.get(F * s + q).getAsDouble();
            log.addFrame(f, cuts.contains(log.size()), 0);
        }
        if (m.has("hp") && m.get("hp").isJsonArray())
            log.setHealth(m.getAsJsonArray("hp"), m.has("hp_estimated") && m.get("hp_estimated").getAsBoolean());
        return log;
    }

    ReplayLog copy() {
        ReplayLog c = new ReplayLog();
        c.frames.addAll(frames);
        c.cuts.addAll(cuts);
        c.events.addAll(events);
        c.equip.addAll(equip);
        c.health.addAll(health);
        c.healthEstimated = healthEstimated;
        return c;
    }
}
