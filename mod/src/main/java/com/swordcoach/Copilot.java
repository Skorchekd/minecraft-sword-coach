// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderContext;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;

/**
 * The fight copilot, drawn in the world and on the crosshair, in this client only. It reads what the game already shows you and
 * never touches your keys or look. Facts it draws: where the opponent is looking (a cone on the ground), their reach (a ring around
 * them), whether you are in reach and charged (the crosshair). Under the crosshair, from the server: the move they made, the move you
 * answered it with, green when it was the right one and red when it was not, and the counter to use instead, in gold so it catches
 * the eye mid-fight. On servers that hide health, right of the crosshair: their health as worked out from your hits ("~12.5 ❤").
 * (The server still works out the copilot's movement hints and keeps them with the fight; they are not drawn.)
 */
final class Copilot {
    private static final int DEEP = 0x6D28D9, VIOLET = 0xA855F7, LILAC = 0xD8B4FE, WHITE = 0xF5EEFF;
    /** Right, wrong and the counter: colours that stand out from the purple guides and from the game. */
    static final int RIGHT = 0x4ADE80, WRONG = 0xFF5C5C, COUNTER = 0xFFD23F;
    private static final double THEIR_REACH = 3.0, CONE_HALF = 28.0, CONE_LEN = 4.5;

    boolean on;
    /** This fight shows no advice, at random, so fights with and without it can be compared. */
    boolean heldBack;
    private double leadX, leadZ;
    private static final double LEAD_TICKS = 6.0;
    private double groundY = Double.NaN, yawShown = Double.NaN;
    private long lastDraw;
    /** Their move, the move you answered it with, the verdict ("right", "wrong" or null), the counter (null when none is clearly ahead) and
     * how to do it, and when it arrived, in ms. */
    private String counterThem, counterYou, counterVerdict, counterName, counterHow;
    private int counterTimes;
    private long counterAt;
    private static final long COUNTER_MS = 1800, COUNTER_FADE = 400, COUNTER_FLASH = 600;
    /** Their health as the server works it out where it is hidden (NaN: not a hidden-health fight), and when it arrived, in ms. */
    private float hpGuess = Float.NaN;
    private long hpAt;
    private static final long HP_MS = 2500;

    void hp(JsonObject m) {
        hpGuess = m.has("hp") && !m.get("hp").isJsonNull() ? m.get("hp").getAsFloat() : Float.NaN;
        hpAt = System.currentTimeMillis();
    }

    void counter(JsonObject m) {
        counterThem = str(m, "them");
        counterYou = str(m, "you");
        counterVerdict = str(m, "verdict");
        counterName = str(m, "counter");
        counterHow = str(m, "how");
        counterTimes = m.has("times") ? m.get("times").getAsInt() : 1;
        counterAt = System.currentTimeMillis();
    }

    private static String str(JsonObject m, String k) {
        return m.has(k) && !m.get(k).isJsonNull() ? m.get(k).getAsString() : null;
    }

    /** The counters it showed through a fight, for replays: [[tick, their move, counter, how, your move, verdict], ...] (null where none). */
    private JsonArray counters;
    private int countersAt;

    void setCounters(JsonArray c) {
        counters = c;
        countersAt = 0;
    }

    private boolean counterFresh() {
        return counterThem != null && System.currentTimeMillis() - counterAt < COUNTER_MS;
    }

    /** During a replay, what the copilot showed at that frame, as one line for the replay card (null if nothing). */
    String counterLine() {
        if (!counterFresh()) return null;
        StringBuilder s = new StringBuilder("Copilot: after their ").append(counterThem);
        if (counterYou != null) s.append(", you ").append(counterYou).append("right".equals(counterVerdict) ? " (right)" : "wrong".equals(counterVerdict) ? " (wrong)" : "");
        if (counterName != null && !"right".equals(counterVerdict)) {
            s.append("  ->  ").append(counterName);
            if (counterHow != null && !counterHow.isEmpty()) s.append(" (").append(counterHow).append(")");
        }
        return s.toString();
    }

    /** The colour of that line: green, red, or the copilot's own. */
    int counterLineColor(int fallback) {
        return 0xFF000000 | ("right".equals(counterVerdict) ? RIGHT : "wrong".equals(counterVerdict) ? WRONG : fallback & 0xFFFFFF);
    }

    /** During a replay, the counter of that frame. */
    void atFrame(int frame) {
        if (counters == null || counters.isEmpty()) return;
        if (countersAt >= counters.size() || counters.get(countersAt).getAsJsonArray().get(0).getAsInt() > frame) countersAt = 0;
        while (countersAt + 1 < counters.size() && counters.get(countersAt + 1).getAsJsonArray().get(0).getAsInt() <= frame) countersAt++;
        JsonArray c = counters.get(countersAt).getAsJsonArray();
        int at = c.get(0).getAsInt();
        if (at > frame || frame - at > 24) {
            counterThem = null;
            return;
        }
        counterThem = c.get(1).getAsString();
        counterName = at(c, 2);
        counterHow = at(c, 3);
        counterYou = at(c, 4);
        counterVerdict = at(c, 5);
        counterTimes = 1;
        counterAt = System.currentTimeMillis();
    }

    private static String at(JsonArray c, int i) {
        return i < c.size() && !c.get(i).isJsonNull() ? c.get(i).getAsString() : null;
    }

    void clear() {
        counterThem = counterYou = counterVerdict = counterName = counterHow = null;
        hpGuess = Float.NaN;
        groundY = yawShown = Double.NaN;
    }

    /** World guides, flat on the ground around the opponent, where you are already looking, so they stay in view at any FOV. */
    void drawWorld(LevelRenderContext ctx, Vec3 me, Vec3 themNow, Vec3 theirStep, float theirYaw) {
        Minecraft mc = Minecraft.getInstance();
        Vec3 cam = mc.gameRenderer.getMainCamera().position();
        long now = System.currentTimeMillis();
        double dt = Math.min(0.1, (now - lastDraw) / 1000.0);
        lastDraw = now;
        // Where they are heading, not where they were: a third of a second ahead on their momentum, eased so a packet cannot make it jump.
        double ease = Math.min(1.0, dt * 8.0);
        leadX += (theirStep.x * LEAD_TICKS - leadX) * ease;
        leadZ += (theirStep.z * LEAD_TICKS - leadZ) * ease;
        Vec3 them = new Vec3(themNow.x + leadX, themNow.y, themNow.z + leadZ);
        // Steady ground: nobody's jump moves the guides, and their look eases rather than snapping with each packet.
        double ground = Math.min(me.y, them.y);
        groundY = Double.isNaN(groundY) || ground < groundY ? ground : groundY + (ground - groundY) * Math.min(1.0, dt * 2.0);
        yawShown = Double.isNaN(yawShown) ? theirYaw : yawShown + wrap(theirYaw - yawShown) * Math.min(1.0, dt * 18.0);
        PoseStack ps = ctx.poseStack();
        ps.pushPose();
        ps.translate(-cam.x, -cam.y, -cam.z);
        Matrix4f m = ps.last().pose();
        MultiBufferSource.BufferSource src = ctx.bufferSource();
        RenderType type = RenderTypes.debugQuads();
        VertexConsumer vc = src.getBuffer(type);
        double y = groundY + 0.06;
        double t = now / 1000.0;
        double dx = me.x - them.x, dz = me.z - them.z, dist = Math.hypot(dx, dz);
        // In their cone and inside their reach is the place to get out of: it says so by glowing.
        double offLine = Math.abs(wrap(Math.toDegrees(Math.atan2(-dx, dz)) - yawShown));
        boolean seen = offLine < CONE_HALF;
        boolean danger = seen && dist < THEIR_REACH + 0.6;
        double pulse = 0.5 + 0.5 * Math.sin(t * 7.0);
        cone(vc, m, themNow, y, (float) yawShown, danger ? 0.34 + 0.16 * pulse : seen ? 0.26 : 0.16);
        ring(vc, m, themNow, y + 0.03, THEIR_REACH, 0.05, VIOLET, danger ? 0.85 : 0.5);
        ring(vc, m, themNow, y + 0.015, THEIR_REACH, 0.34, VIOLET, danger ? 0.2 : 0.09);
        src.endBatch(type);
        ps.popPose();
    }

    private static void cone(VertexConsumer vc, Matrix4f m, Vec3 at, double y, float yaw, double alpha) {
        int n = 14, bands = 5;
        for (int b = 0; b < bands; b++) {
            double r0 = CONE_LEN * b / bands, r1 = CONE_LEN * (b + 1) / bands;
            double a0 = alpha * (1.0 - (double) b / bands), a1 = alpha * (1.0 - (double) (b + 1) / bands);
            for (int i = 0; i < n; i++) {
                double u0 = yaw - CONE_HALF + 2 * CONE_HALF * i / n, u1 = yaw - CONE_HALF + 2 * CONE_HALF * (i + 1) / n;
                quad(vc, m, y, at.x + r0 * fx(u0), at.z + r0 * fz(u0), a0, at.x + r1 * fx(u0), at.z + r1 * fz(u0), a1,
                        at.x + r1 * fx(u1), at.z + r1 * fz(u1), a1, at.x + r0 * fx(u1), at.z + r0 * fz(u1), a0, DEEP);
            }
        }
    }

    private static void ring(VertexConsumer vc, Matrix4f m, Vec3 c, double y, double r, double w, int color, double alpha) {
        int n = 64;
        for (int i = 0; i < n; i++) {
            double a0 = 2 * Math.PI * i / n, a1 = 2 * Math.PI * (i + 1) / n;
            double i0 = r - w / 2, o0 = r + w / 2;
            quad(vc, m, y, c.x + i0 * Math.cos(a0), c.z + i0 * Math.sin(a0), alpha, c.x + o0 * Math.cos(a0), c.z + o0 * Math.sin(a0), alpha,
                    c.x + o0 * Math.cos(a1), c.z + o0 * Math.sin(a1), alpha, c.x + i0 * Math.cos(a1), c.z + i0 * Math.sin(a1), alpha, color);
        }
    }

    private static void quad(VertexConsumer vc, Matrix4f m, double y, double ax, double az, double aa, double bx, double bz, double ba,
                             double cx, double cz, double ca, double dx, double dz, double da, int color) {
        v(vc, m, ax, y, az, color, aa);
        v(vc, m, bx, y, bz, color, ba);
        v(vc, m, cx, y, cz, color, ca);
        v(vc, m, dx, y, dz, color, da);
    }

    private static void v(VertexConsumer vc, Matrix4f m, double x, double y, double z, int color, double alpha) {
        int a = (int) Math.max(0, Math.min(255, Math.round(alpha * 255)));
        vc.addVertex(m, (float) x, (float) y, (float) z).setColor((color >> 16) & 255, (color >> 8) & 255, color & 255, a);
    }

    private static double fx(double yawDeg) {
        return -Math.sin(Math.toRadians(yawDeg));
    }

    private static double fz(double yawDeg) {
        return Math.cos(Math.toRadians(yawDeg));
    }

    private static double wrap(double a) {
        a = (a + 180.0) % 360.0;
        if (a < 0) a += 360.0;
        return a - 180.0;
    }

    /**
     * The crosshair: a ring that fills as your charge builds, brightens when you are in reach, and pulses white when you are on them, in reach
     * and charged. Under it, their move, your answer and the counter.
     */
    void drawCrosshair(GuiGraphicsExtractor g, Font f, AbstractClientPlayer me, Entity target) {
        Minecraft mc = Minecraft.getInstance();
        int cx = mc.getWindow().getGuiScaledWidth() / 2, cy = mc.getWindow().getGuiScaledHeight() / 2;
        float charge = me.getAttackStrengthScale(0.5f);
        Vec3 eye = me.getEyePosition();
        double box = target.getBoundingBox().distanceToSqr(eye);
        boolean inReach = box <= me.entityInteractionRange() * me.entityInteractionRange();
        boolean onThem = mc.hitResult instanceof EntityHitResult e && e.getEntity() == target;
        boolean ready = inReach && onThem && charge >= 0.95f;
        double t = System.currentTimeMillis() / 1000.0;
        double pulse = 0.5 + 0.5 * Math.sin(t * 12.0);
        int base = ready ? mix(LILAC, WHITE, pulse) : inReach ? VIOLET : DEEP;
        int alpha = ready ? 255 : inReach ? 230 : 130;
        int r = ready ? 9 : 8, n = 32;
        for (int i = 0; i < n; i++) {
            double a = -Math.PI / 2 + 2 * Math.PI * i / n;
            boolean lit = i / (double) n <= charge;
            int x = cx + (int) Math.round(r * Math.cos(a)), y = cy + (int) Math.round(r * Math.sin(a));
            g.fill(x, y, x + 1, y + 1, argb(lit ? alpha : 60, lit ? base : DEEP));
        }
        drawHealth(g, f, cx + 13, cy - 4);
        if (heldBack) {
            String s = "Copilot quiet this fight";
            g.text(f, s, cx - f.width(s) / 2, cy + 40, argb(170, LILAC), true);
            return;
        }
        drawCounter(g, f, cx, cy + 40);
    }

    /**
     * Their move; then your answer, green when it was the right one, red when it was not, followed by the counter in gold (pulsing as it
     * arrives) and how to do it. Fades out if no new read comes.
     */
    private void drawCounter(GuiGraphicsExtractor g, Font f, int cx, int y) {
        long age = System.currentTimeMillis() - counterAt;
        if (!counterFresh()) return;
        double fade = age < COUNTER_MS - COUNTER_FADE ? 1.0 : (COUNTER_MS - age) / (double) COUNTER_FADE;
        String them = "vs " + counterThem + (counterTimes >= 2 ? "  x" + counterTimes : "");
        g.text(f, them, cx - f.width(them) / 2, y, argb((int) (190 * fade), LILAC), true);
        boolean suggest = counterName != null && !"right".equals(counterVerdict);
        String you = counterYou == null ? null : counterYou;
        String arrow = suggest ? (you != null ? "  ->  " : "->  ") : null;
        int w = (you != null ? f.width(you) : 0) + (suggest ? f.width(arrow) + f.width(counterName) : 0);
        if (w == 0) return;
        int x = cx - w / 2, line = y + 11;
        if (you != null) {
            int c = "right".equals(counterVerdict) ? RIGHT : "wrong".equals(counterVerdict) ? WRONG : WHITE;
            g.text(f, you, x, line, argb((int) (255 * fade), c), true);
            x += f.width(you);
        }
        if (suggest) {
            // The counter catches the eye: bright gold, flashing for a moment when it arrives.
            double flash = age < COUNTER_FLASH ? 0.65 + 0.35 * Math.abs(Math.sin(age / 1000.0 * Math.PI * 5)) : 1.0;
            g.text(f, arrow, x, line, argb((int) (230 * fade), WHITE), true);
            x += f.width(arrow);
            g.text(f, counterName, x, line, argb((int) (255 * fade * flash), COUNTER), true);
            if (counterHow != null && !counterHow.isEmpty())
                g.text(f, counterHow, cx - f.width(counterHow) / 2, line + 11, argb((int) (215 * fade), COUNTER), true);
        }
    }

    /** Their worked-out health beside the crosshair, coloured by how low it is: green above 12, gold to 6, red under. */
    private void drawHealth(GuiGraphicsExtractor g, Font f, int x, int y) {
        if (Float.isNaN(hpGuess) || System.currentTimeMillis() - hpAt >= HP_MS) return;
        String num = String.format(java.util.Locale.ROOT, "~%.1f", hpGuess);
        int c = hpGuess > 12f ? RIGHT : hpGuess >= 6f ? COUNTER : WRONG;
        g.text(f, num, x, y, argb(240, c), true);
        g.text(f, " \u2764", x + f.width(num), y, argb(240, WRONG), true);
    }

    private static int argb(int a, int rgb) {
        return (Math.max(0, Math.min(255, a)) << 24) | (rgb & 0xFFFFFF);
    }

    private static int mix(int a, int b, double t) {
        int r = (int) (((a >> 16) & 255) * (1 - t) + ((b >> 16) & 255) * t);
        int gn = (int) (((a >> 8) & 255) * (1 - t) + ((b >> 8) & 255) * t);
        int bl = (int) ((a & 255) * (1 - t) + (b & 255) * t);
        return (r << 16) | (gn << 8) | bl;
    }
}
