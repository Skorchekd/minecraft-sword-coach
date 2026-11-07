// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import static com.swordcoach.ReplayLog.ANIM;
import static com.swordcoach.ReplayLog.BODY;
import static com.swordcoach.ReplayLog.CROUCH;
import static com.swordcoach.ReplayLog.HEAD;
import static com.swordcoach.ReplayLog.HURT;
import static com.swordcoach.ReplayLog.PITCH;
import static com.swordcoach.ReplayLog.SWING;
import static com.swordcoach.ReplayLog.X;
import static com.swordcoach.ReplayLog.Y;
import static com.swordcoach.ReplayLog.Z;

/**
 * Plays your last fight back in your world with two client-only dummies, exactly as your client drew
 * it ({@link ReplayLog}): position, head and body yaw, pitch, swing, hurt, crouch and equipment,
 * blended between ticks so slow motion stays smooth, and cut (never slid) across gaps and teleports.
 *
 * <p>The fight is split into its 12-tick exchanges, each with the technique each of you used and how
 * it went against what real exchanges from the same spot usually trade (from the server). Points on the
 * timeline: the start, every exchange that went clearly worse, and every switch of technique.</p>
 *
 * <p>It sounds like the fight did: the attack sound of every hit (crit, knockback, strong, weak, sweep, no damage) at
 * the attacker, the hurt sound at the one hit, and crit particles plus a CRIT tag when a hit crit. Those come from
 * what the server sent during the fight ({@link HitEvents}); for older saved fights the server works them out from
 * how each hit landed, and the tag then says CRIT?.</p>
 *
 * <p>Controls: left/right previous or next point, comma/period one tick, up/down speed, B pause,
 * V camera (your view, your eyes, their eyes). The eye camera only moves the rendered view
 * ({@link ReplayCamera}). If you have left the place of the fight, it is staged five blocks in front
 * of you.</p>
 */
final class Replay {
    static final int YOU = 0x3CC9BF, THEM = 0xE66AC0, WORSE = 0xEF6B5E, BETTER = 0x4CC27A;
    static final double[] SPEEDS = {0.25, 1 / 3.0, 0.5, 1.0};
    static final String[] SPEED_NAMES = {"1/4", "1/3", "1/2", "1"};

    enum Cam {
        OWN("your view"), YOU("your eyes"), THEM("their eyes");
        final String label;

        Cam(String label) {
            this.label = label;
        }
    }

    /** One exchange. */
    static final class Seg {
        int start, end;
        String you, them, call;      // call: "worse", "better", "as_expected" or null (no estimate)
        double vs;
        Double later;                // dealt minus taken over about the next 6 s
        String suggest;              // an answer that usually went clearly better here, or null
        boolean point, relabelled;
        int[][] hits;                // you, them: hits landed, swings, crits
        String marks = "";           // your labels: how each side executed it, what went wrong
    }

    double[][][] st;                 // [tick][side][ReplayLog.F]
    boolean[] cut;                   // a gap or teleport just before this tick
    List<ReplayLog.Equip> equip;
    Seg[] segs;
    int[] points;                    // timeline points, as tick indices
    final String[] lines = new String[6];
    /** Both players' health per tick [you, them] when the server sent it (null if not), and whether theirs is worked out from your hits. */
    float[][] hp;
    boolean hpEstimated;
    String title = "", name = "Last fight";
    boolean active, paused, sounds = true;
    Cam cam = Cam.OWN;
    int speedIdx = 1;
    private int frame, equipAt = -1, trailAt;
    private double pos, offX, offY, offZ;
    private boolean snapNext;
    private Dummy you, opp;

    Dummy you() {
        return you;
    }

    Dummy opp() {
        return opp;
    }
    private CameraType savedType;
    private final Map<Integer, List<int[]>> sfx = new HashMap<>();     // frame -> [at (0 you, 1 them), sound kind]
    private final Map<Integer, List<int[]>> critAt = new HashMap<>();  // frame -> [on (who was crit), recorded 1/0]
    private int playedTo;
    private final int[] critUntil = {-1, -1};
    private final boolean[] critSure = new boolean[2];

    /**
     * A fight as drawn, with the server's reading of each exchange ({@code exchanges}: ex, you, them, call, vs,
     * hits, labels) when it has sent one, and its attack sounds and crits ({@code sounds}: [tick, at, kind, recorded],
     * {@code crits}: [tick, on, recorded]; when null, the ones recorded in the log). Exchange k covers ticks
     * 12k .. 12k + 12.
     */
    boolean load(ReplayLog log, JsonArray exchanges, JsonArray sounds, JsonArray crits, String name) {
        int n = log.size();
        if (n < 2) return false;
        st = new double[n][][];
        cut = new boolean[n];
        for (int i = 0; i < n; i++) {
            double[][] f = log.frames.get(i);
            st[i] = new double[][]{f[0].clone(), f[1].clone()};
            cut[i] = i > 0 && log.cuts.get(i);
        }
        equip = new ArrayList<>(log.equip);
        hp = log.health.isEmpty() ? null : log.health.toArray(new float[0][]);
        hpEstimated = log.healthEstimated;
        this.name = name;
        sfx.clear();
        critAt.clear();
        if (sounds != null && crits != null) {
            for (JsonElement e : sounds) {
                JsonArray a = e.getAsJsonArray();
                int kind = a.get(2).getAsInt();
                if (kind >= 0 && kind < HitEvents.KINDS.length)
                    sfx.computeIfAbsent(a.get(0).getAsInt(), k -> new ArrayList<>()).add(new int[]{a.get(1).getAsInt() & 1, kind});
            }
            for (JsonElement e : crits) {
                JsonArray a = e.getAsJsonArray();
                critAt.computeIfAbsent(a.get(0).getAsInt(), k -> new ArrayList<>()).add(new int[]{a.get(1).getAsInt() & 1, a.get(2).getAsInt()});
            }
        } else {
            for (int i = 0; i < log.events.size(); i++) {
                int b = log.events.get(i);
                for (int at = 0; at < 2; at++)
                    for (int kind = 0; kind < HitEvents.KINDS.length; kind++)
                        if ((b >> (6 * at + kind) & 1) != 0) sfx.computeIfAbsent(i, k -> new ArrayList<>()).add(new int[]{at, kind});
                for (int on = 0; on < 2; on++)
                    if ((b >> (HitEvents.CRIT_ON + on) & 1) != 0) critAt.computeIfAbsent(i, k -> new ArrayList<>()).add(new int[]{on, 1});
            }
        }
        Map<Integer, JsonObject> byEx = new HashMap<>();
        if (exchanges != null)
            for (JsonElement e : exchanges) byEx.put(e.getAsJsonObject().get("ex").getAsInt(), e.getAsJsonObject());
        List<Seg> list = new ArrayList<>();
        for (int k = 0; 12 * k < n - 1; k++) {
            Seg g = new Seg();
            g.start = 12 * k;
            g.end = Math.min(n - 1, 12 * k + 12);
            JsonObject e = byEx.get(k);
            if (e != null) {
                g.you = e.get("you").getAsString();
                g.them = e.get("them").getAsString();
                g.call = e.has("call") && !e.get("call").isJsonNull() ? e.get("call").getAsString() : null;
                g.vs = e.has("vs") && !e.get("vs").isJsonNull() ? e.get("vs").getAsDouble() : 0;
                g.later = e.has("later") && !e.get("later").isJsonNull() ? e.get("later").getAsDouble() : null;
                g.suggest = e.has("suggest") && !e.get("suggest").isJsonNull() ? e.get("suggest").getAsString() : null;
                g.relabelled = e.has("relabelled") && e.get("relabelled").getAsBoolean();
                if (e.has("hits")) {
                    JsonArray h = e.getAsJsonArray("hits");
                    g.hits = new int[2][3];
                    for (int s = 0; s < 2; s++)
                        for (int q = 0; q < 3; q++) g.hits[s][q] = h.get(s).getAsJsonArray().get(q).getAsInt();
                }
                g.marks = marks(e);
            }
            list.add(g);
        }
        List<Integer> pts = new ArrayList<>();
        for (int k = 0; k < list.size(); k++) {
            Seg g = list.get(k), p = k > 0 ? list.get(k - 1) : null;
            boolean sw = p != null && g.you != null && p.you != null && (!g.you.equals(p.you) || !g.them.equals(p.them));
            g.point = k == 0 || "worse".equals(g.call) || sw;
            if (g.point) pts.add(g.start);
        }
        segs = list.toArray(new Seg[0]);
        points = pts.stream().mapToInt(Integer::intValue).toArray();
        return true;
    }

    /** "You: poor, missed hit · Them: too close" from your labels, or "". */
    private static String marks(JsonObject e) {
        List<String> out = new ArrayList<>();
        for (String[] side : new String[][]{{"you", "You"}, {"them", "Them"}}) {
            List<String> parts = new ArrayList<>();
            if (e.has("exec") && e.getAsJsonObject("exec").has(side[0]))
                parts.add("executed " + e.getAsJsonObject("exec").get(side[0]).getAsString().toLowerCase(Locale.ROOT));
            if (e.has("fail") && e.getAsJsonObject("fail").has(side[0]))
                for (JsonElement f : e.getAsJsonObject("fail").getAsJsonArray(side[0])) parts.add(f.getAsString().toLowerCase(Locale.ROOT));
            if (!parts.isEmpty()) out.add(side[1] + ": " + String.join(", ", parts));
        }
        return String.join(" · ", out);
    }

    /** The exchanges that went clearly worse than expected, as tick indices. */
    int[] worse() {
        return java.util.Arrays.stream(segs).filter(g -> "worse".equals(g.call)).mapToInt(g -> g.start).toArray();
    }

    // ---- playback ---------------------------------------------------------------------------
    void start(Minecraft mc, int atTick) {
        if (st == null || mc.level == null || mc.player == null) return;
        active = true;
        paused = false;
        frame = 0;
        pos = Math.max(0, Math.min(st.length - 1, atTick));
        equipAt = -1;
        trailAt = (int) pos;
        playedTo = (int) pos - 1;
        critUntil[0] = critUntil[1] = -1;
        anchor(mc);
        you = new Dummy(mc.level, Dummy.profile("You"), "You", YOU);
        opp = new Dummy(mc.level, Dummy.profile("Opponent"), "Them", THEM);
        snapNext = true;
        render();
        mc.level.addEntity(you);
        mc.level.addEntity(opp);
        applyCam(mc);
        updateLines();
    }

    void stop() {
        Minecraft mc = Minecraft.getInstance();
        active = false;
        ReplayCamera.eye = null;
        if (savedType != null) {
            mc.options.setCameraType(savedType);
            savedType = null;
        }
        cam = Cam.OWN;
        if (you != null) you.remove();
        if (opp != null) opp.remove();
        you = opp = null;
    }

    /** Where the fight happened if you are still there, else five blocks in front of you. */
    private void anchor(Minecraft mc) {
        offX = offY = offZ = 0;
        LocalPlayer p = mc.player;
        double[][] f = st[0];
        double mx = (f[0][X] + f[1][X]) / 2, mz = (f[0][Z] + f[1][Z]) / 2, my = Math.min(f[0][Y], f[1][Y]);
        if (Math.hypot(p.getX() - mx, p.getZ() - mz) < 48 && Math.abs(p.getY() - my) < 16) return;
        double r = Math.toRadians(p.getYRot());
        offX = p.getX() - Math.sin(r) * 5 - mx;
        offZ = p.getZ() + Math.cos(r) * 5 - mz;
        offY = p.getY() - my;
    }

    /** Pose both dummies at the playhead: blended between the two ticks around it, never across a cut. */
    private void render() {
        int n = st.length;
        int i = Math.max(0, Math.min(n - 1, (int) Math.floor(pos))), j = Math.min(n - 1, i + 1);
        double k = pos - i;
        if (j == i || cut[j]) k = 0;
        boolean snap = snapNext;
        for (int c = frame + 1; c <= i && !snap; c++) if (cut[c]) snap = true;
        snapNext = false;
        double[][] a = st[i], b = st[j];
        double[][] at = new double[2][3];
        for (int s = 0; s < 2; s++)
            for (int q = 0; q < 3; q++) at[s][q] = a[s][q] + (b[s][q] - a[s][q]) * k;
        Dummy[] d = {you, opp};
        for (int s = 0; s < 2; s++) {
            double[] p = a[s], q = b[s];
            float head = lerpAngle(p[HEAD], q[HEAD], k), body = lerpAngle(p[BODY], q[BODY], k);
            float pitch = Double.isNaN(p[PITCH]) ? pitchTo(at[s], at[1 - s]) : (float) (p[PITCH] + (q[PITCH] - p[PITCH]) * k);
            float anim = (float) (q[ANIM] >= p[ANIM] ? p[ANIM] + (q[ANIM] - p[ANIM]) * k : k < 0.5 ? p[ANIM] : q[ANIM]);
            d[s].apply(at[s][0] + offX, at[s][1] + offY, at[s][2] + offZ, head, body, pitch, (int) p[HURT], anim,
                    p[SWING] > 0.5, p[CROUCH] > 0.5, snap);
        }
        frame = i;
        if (equipAt != i) applyEquip(i);
    }

    private void applyEquip(int f) {
        Dummy[] d = {you, opp};
        Map<String, ItemStack> now = new HashMap<>();
        for (ReplayLog.Equip e : equip) if (e.frame() <= f) now.put(e.side() + ":" + e.slot().name(), e.stack());
        for (int s = 0; s < 2; s++)
            for (EquipmentSlot slot : ReplayLog.SLOTS) {
                ItemStack stack = now.get(s + ":" + slot.name());
                if (stack != null) d[s].setItemSlot(slot, stack.copy());
            }
        equipAt = f;
    }

    private static float lerpAngle(double a, double b, double k) {
        double d = ((b - a) % 360 + 540) % 360 - 180;
        return (float) (a + d * k);
    }

    /** Pitch (Minecraft's: positive looks down) from a's eyes to b's chest. */
    private static float pitchTo(double[] a, double[] b) {
        double d = Math.max(0.3, Math.hypot(b[0] - a[0], b[2] - a[2]));
        return (float) -Math.toDegrees(Math.atan2(b[1] + 1.2 - (a[1] + 1.62), d));
    }

    void tick(Minecraft mc) {
        if (!active) return;
        if (mc.level == null || mc.player == null) {
            stop();
            return;
        }
        if (!paused && pos < st.length - 1) pos = Math.min(st.length - 1, pos + SPEEDS[speedIdx]);
        render();
        for (; playedTo < frame; playedTo++) fire(mc, playedTo + 1);
        for (; trailAt < frame; trailAt++) {
            double[][] f = st[trailAt + 1];
            trail(mc, f[0], YOU);
            trail(mc, f[1], THEM);
        }
        updateLines();
    }

    // ---- controls ---------------------------------------------------------------------------
    void togglePause() {
        paused = !paused;
    }

    void speed(int d) {
        speedIdx = Math.max(0, Math.min(SPEEDS.length - 1, speedIdx + d));
    }

    /** Left/right: the previous or next timeline point. */
    void step(int d) {
        if (!active) return;
        int target = frame;
        if (d > 0) {
            for (int p : points)
                if (p > frame) {
                    target = p;
                    break;
                }
        } else {
            target = 0;
            for (int p : points) if (p < frame - 2) target = p;     // from just after a point, the one before it
        }
        seek(target);
    }

    /** Comma/period: one tick back or forward, paused. */
    void tickStep(int d) {
        if (!active) return;
        paused = true;
        if (d < 0) snapNext = true;
        pos = Math.max(0, Math.min(st.length - 1, frame + d));
        render();
        if (d > 0 && frame > playedTo) fire(Minecraft.getInstance(), frame);
        playedTo = frame;
        trailAt = Math.min(trailAt, frame);
        updateLines();
    }

    void seek(int f) {
        pos = f;
        snapNext = true;
        render();
        playedTo = frame;
        trailAt = frame;
        updateLines();
    }

    void cycleCam(Minecraft mc) {
        cam = Cam.values()[(cam.ordinal() + 1) % Cam.values().length];
        applyCam(mc);
    }

    /** Your eyes or theirs: the view is drawn from that dummy in first person (F5 still works). */
    private void applyCam(Minecraft mc) {
        if (you != null) you.hidden = cam == Cam.YOU;
        if (opp != null) opp.hidden = cam == Cam.THEM;
        ReplayCamera.eye = cam == Cam.YOU ? you : cam == Cam.THEM ? opp : null;
        if (cam != Cam.OWN && savedType == null) {
            savedType = mc.options.getCameraType();
            mc.options.setCameraType(CameraType.FIRST_PERSON);
        } else if (cam == Cam.OWN && savedType != null) {
            mc.options.setCameraType(savedType);
            savedType = null;
        }
    }

    /**
     * What the fight sounded like at frame f: the hurt sound at whoever was hit, the attack sounds at the attacker,
     * crit particles on whoever was crit (and a CRIT tag on the one who crit them). Client-only, like the dummies.
     */
    private void fire(Minecraft mc, int f) {
        if (mc.level == null || f <= 0 || f >= st.length) return;
        Dummy[] d = {you, opp};
        if (sounds)
            for (int s = 0; s < 2; s++)
                if (!cut[f] && st[f][s][HURT] > st[f - 1][s][HURT])
                    mc.level.playLocalSound(d[s], SoundEvents.PLAYER_HURT, SoundSource.PLAYERS, 1.0f, 1.0f);
        if (sounds)
            for (int[] x : sfx.getOrDefault(f, List.of()))
                mc.level.playLocalSound(d[x[0]], HitEvents.KINDS[x[1]], SoundSource.PLAYERS, 1.0f, 1.0f);
        for (int[] c : critAt.getOrDefault(f, List.of())) {
            mc.particleEngine.createTrackingEmitter(d[c[0]], ParticleTypes.CRIT);
            critUntil[1 - c[0]] = f + 15;
            critSure[1 - c[0]] = c[1] == 1;
        }
    }

    private String critTag(int s) {
        return frame <= critUntil[s] ? (critSure[s] ? "  ✦ CRIT" : "  ✦ CRIT?") : "";
    }

    private static String hitsText(int[] h) {
        if (h[0] == 0) return h[1] == 0 ? "no swings" : "none of " + h[1] + " swing" + (h[1] == 1 ? "" : "s");
        return h[0] + (h[1] >= h[0] ? " of " + h[1] : "") + " landed" + (h[2] > 0 ? ", " + h[2] + " crit" + (h[2] == 1 ? "" : "s") : "");
    }

    // ---- what the card shows ----------------------------------------------------------------
    int segAt(int f) {
        for (int k = segs.length - 1; k >= 0; k--) if (f >= segs[k].start) return k;
        return 0;
    }

    int frame() {
        return frame;
    }

    /** [your health, theirs] at this frame, or null when the server sent none. */
    float[] healthNow() {
        if (hp == null || hp.length == 0) return null;
        return hp[Math.max(0, Math.min(hp.length - 1, frame))];
    }

    double distance() {
        double[][] f = st[frame];
        return Math.hypot(f[1][X] - f[0][X], f[1][Z] - f[0][Z]);
    }

    private void updateLines() {
        int k = segAt(frame);
        Seg g = segs[k];
        boolean end = frame >= st.length - 1;
        title = String.format(Locale.ROOT, "%s: exchange %d of %d%s", name, k + 1, segs.length, end ? " (end)" : "");
        if (g.you != null) {
            lines[0] = "You: " + g.you + "   Them: " + g.them + (g.relabelled ? "   (your labels)" : "");
            lines[1] = g.call == null ? "No estimate for this exchange"
                    : "worse".equals(g.call) ? String.format(Locale.ROOT, "Lost this trade: %+.1f HP against what usually happens here", g.vs)
                    : "better".equals(g.call) ? String.format(Locale.ROOT, "Won this trade: %+.1f HP against what usually happens here", g.vs)
                    : String.format(Locale.ROOT, "About what usually happens here (%+.1f HP)", g.vs);
            you.setLabel("You: " + g.you + critTag(0));
            opp.setLabel("Them: " + g.them + critTag(1));
        } else {
            lines[0] = "Not read yet (is the Sword Coach server running?)";
            lines[1] = "";
            you.setLabel("You" + critTag(0));
            opp.setLabel("Them" + critTag(1));
        }
        lines[2] = hint(g);
        lines[3] = g.hits == null ? "" : "Hits: you " + hitsText(g.hits[0]) + " · them " + hitsText(g.hits[1]);
        Seg p = k > 0 ? segs[k - 1] : null;
        String why = "";
        if (p != null && g.you != null && p.you != null) {
            if (!g.them.equals(p.them)) why = "They switched " + p.them + " to " + g.them;
            if (!g.you.equals(p.you)) why += (why.isEmpty() ? "" : ". ") + "You switched " + p.you + " to " + g.you;
        }
        lines[4] = g.marks.isEmpty() ? why : why.isEmpty() ? g.marks : why + ". " + g.marks;
        lines[5] = String.format(Locale.ROOT, "Distance %.2f blocks", distance());
    }

    /** A lost trade you won back says so first: it may have been worth it. Otherwise an answer that usually went clearly better, if there is one. */
    private static String hint(Seg g) {
        if ("worse".equals(g.call) && g.later != null && g.later > 0)
            return String.format(Locale.ROOT, "But you came out %+.1f HP over the next 6 s: maybe worth it", g.later);
        return g.suggest == null ? "" : "Usually went better here: " + g.suggest + " (about +0.3 HP)";
    }

    String controls() {
        return String.format(Locale.ROOT, "←→ point   ,. tick   ↑↓ %sx   B %s   V camera: %s   H close",
                SPEED_NAMES[speedIdx], paused ? "play" : "pause", cam.label);
    }

    /** The playhead as a fraction of the fight, for the timeline. */
    double progress() {
        return st == null || st.length < 2 ? 0 : frame / (double) (st.length - 1);
    }

    private void trail(Minecraft mc, double[] p, int color) {
        mc.level.addParticle(new DustParticleOptions(color, 1.1f), p[X] + offX, p[Y] + offY + 0.15, p[Z] + offZ, 0, 0, 0);
    }
}
