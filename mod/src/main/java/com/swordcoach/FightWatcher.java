// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.InterpolationHandler;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Input;
import net.minecraft.world.entity.player.Player;

import java.util.Locale;

/**
 * Finds your opponent (the nearest other player within 6 blocks in a sword kit, see
 * {@link Config#fightKit}), streams one record per game tick to the server while the fight lasts, and
 * ends the fight when someone drops to 0, when the server resets someone's health from a sliver to
 * full (duel servers that never kill the loser end the round this way), when the opponent has been
 * gone for three seconds, or when you leave the world.
 */
final class FightWatcher {
    private static final double START_RANGE = 6.0;
    private static final double LOST_RANGE = 24.0;
    private static final int MIN_TICKS = 40;     // shorter than 2 s: someone walked past, not a fight

    private final Config config;
    final OppHealth oppHealth = new OppHealth();
    AbstractClientPlayer target;
    boolean fighting;
    int ticks, awayTicks;
    String targetName = "";
    /** 1 you won, 0 you lost, -1 unknown; set when a fight ends. */
    int lastResult = -1;
    /** What this client drew, every tick of the fight in progress, and of the last finished one. */
    final ReplayLog replayLog = new ReplayLog();
    ReplayLog lastReplay = new ReplayLog();
    private long clientTick;
    private float prevMyHp = -1, prevOppHp = -1;
    private boolean prevAttackDown;
    private float prevCharge = -1;

    FightWatcher(Config config) {
        this.config = config;
    }

    void tick(Minecraft mc, Sidecar link) {
        clientTick++;
        LocalPlayer me = mc.player;
        if (me == null || mc.level == null) {
            if (fighting) end(link, -1);
            return;
        }
        if (!fighting) {
            AbstractClientPlayer t = nearest(mc, me, config.fightKit);
            if (t == null) return;
            start(mc, link, t);
        }
        boolean gone = target == null || target.isRemoved() || target.level() != me.level()
                || me.distanceTo(target) > LOST_RANGE;
        awayTicks = gone ? awayTicks + 1 : 0;
        float oppHp = gone ? oppHealth.health() : oppHealth.update(mc, target);
        float myHp = me.getHealth();
        if (prevMyHp >= 0 && myHp - prevMyHp > 5 && prevMyHp <= 6 && myHp >= 19.5f) {
            end(link, 0);
            return;
        }
        if (!gone && prevOppHp >= 0 && oppHp - prevOppHp > 5 && prevOppHp <= 6 && oppHp >= 19.5f) {
            end(link, 1);
            return;
        }
        prevMyHp = myHp;
        if (!gone) prevOppHp = oppHp;
        if (myHp <= 0.0f || me.isDeadOrDying()) {
            end(link, 0);
            return;
        }
        if (!gone && (target.isDeadOrDying() || oppHp <= 0.0f)) {
            end(link, 1);
            return;
        }
        if (awayTicks > 60) {
            end(link, -1);
            return;
        }
        if (gone) return;
        float[] r = Raw.of(mc, me, target, oppHp);
        JsonObject o = new JsonObject();
        o.addProperty("t", "raw");
        JsonArray a = new JsonArray();
        for (float v : r) a.add(v);
        o.add("r", a);
        // What the server said about hits this tick (attack sounds, crit particles), for both of you.
        HitEvents.me = me;
        HitEvents.opp = target;
        int ev = HitEvents.take();
        o.addProperty("e", ev);
        // Both players as this client drew them (ReplayLog layout), for the review page's clips.
        replayLog.add(clientTick, me, target, ev);
        double[][] f = replayLog.frames.get(replayLog.size() - 1);
        JsonArray drawn = new JsonArray();
        for (double[] side : f) for (double v : side) drawn.add(Math.round(v * 1000.0) / 1000.0);
        o.add("d", drawn);
        o.addProperty("k", clientTick);
        // Your keys this tick: forward, back, left, right, jump, sneak, sprint, click. A click is the
        // attack key going down, or your attack charge resetting (a swing the key poll missed).
        Input in = me.input.keyPresses;
        boolean attackDown = mc.options.keyAttack.isDown();
        boolean click = (attackDown && !prevAttackDown) || (prevCharge >= 0 && r[11] < prevCharge - 0.5f);
        prevAttackDown = attackDown;
        prevCharge = r[11];
        JsonArray keys = new JsonArray();
        for (boolean b : new boolean[]{in.forward(), in.backward(), in.left(), in.right(), in.jump(), in.shift(), in.sprint(), click})
            keys.add(b ? 1 : 0);
        o.add("i", keys);
        // Their pitch, as the network has it.
        InterpolationHandler interp = target.getInterpolation();
        o.addProperty("op", interp != null && interp.hasActiveInterpolation() ? interp.xRot() : target.getXRot());
        // Velocities the server set this tick (knockback), you then them: x, y, z, packets.
        Knockback.meId = me.getId();
        Knockback.oppId = target.getId();
        JsonArray kb = new JsonArray();
        for (float v : Knockback.take()) kb.add(v);
        o.add("v", kb);
        // Where their health came from this tick (the real value, or a number the server drew over them).
        o.addProperty("hs", oppHealth.source);
        link.send(o);
        ticks++;
    }

    private void start(Minecraft mc, Sidecar link, AbstractClientPlayer t) {
        target = t;
        targetName = t.getName().getString();
        fighting = true;
        ticks = 0;
        awayTicks = 0;
        replayLog.clear();
        Knockback.meId = mc.player.getId();
        Knockback.oppId = t.getId();
        Knockback.take();
        HitEvents.me = mc.player;
        HitEvents.opp = t;
        HitEvents.take();
        prevMyHp = prevOppHp = -1;
        prevAttackDown = mc.options.keyAttack.isDown();
        prevCharge = -1;
        oppHealth.reset(config.healthSpoofed(host(mc)));
        JsonObject o = new JsonObject();
        o.addProperty("t", "reset");
        o.addProperty("server", host(mc));
        // Names go to your own Sword Coach server only, which stores a keyed code instead (never the name),
        // so fights against the same player can be grouped.
        o.addProperty("me", me(mc));
        o.addProperty("opponent", targetName);
        link.send(o);
    }

    private void end(Sidecar link, int result) {
        fighting = false;
        lastResult = result;
        target = null;
        HitEvents.me = HitEvents.opp = null;
        if (ticks < MIN_TICKS) return;
        lastReplay = replayLog.copy();
        JsonObject o = new JsonObject();
        o.addProperty("t", "end");
        o.addProperty("result", result);
        link.send(o);
    }

    private static String me(Minecraft mc) {
        return mc.player != null ? mc.player.getName().getString() : "";
    }

    /** The server's host name (no port), "singleplayer", or "unknown". */
    static String host(Minecraft mc) {
        ServerData sd = mc.getCurrentServer();
        if (sd == null || sd.ip == null) return mc.isLocalServer() ? "singleplayer" : "unknown";
        String h = sd.ip.trim().toLowerCase(Locale.ROOT);
        if (h.startsWith("[")) return h.contains("]") ? h.substring(0, h.indexOf(']') + 1) : h;
        return h.contains(":") ? h.substring(0, h.indexOf(':')) : h;
    }

    private static AbstractClientPlayer nearest(Minecraft mc, LocalPlayer me, String kit) {
        AbstractClientPlayer best = null;
        double bd = START_RANGE;
        if (!"any".equals(kit) && !kitted(me, kit)) return null;
        for (Player p : mc.level.players()) {
            if (p == me || !(p instanceof AbstractClientPlayer ap) || p instanceof Dummy) continue;
            if (p.isSpectator() || !p.isAlive()) continue;
            if (!"any".equals(kit) && !kitted(p, kit)) continue;
            double d = me.distanceTo(p);
            if (d < bd) {
                bd = d;
                best = ap;
            }
        }
        return best;
    }

    /** A sword in the main hand, and (unless "sword_only") at least one piece of armour on. */
    private static boolean kitted(LivingEntity p, String kit) {
        if (!p.getMainHandItem().is(ItemTags.SWORDS)) return false;
        if ("sword_only".equals(kit)) return true;
        for (EquipmentSlot s : new EquipmentSlot[]{EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET})
            if (!p.getItemBySlot(s).isEmpty()) return true;
        return false;
    }
}
