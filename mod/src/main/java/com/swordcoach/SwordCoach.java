// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.hud.VanillaHudElements;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderContext;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.resources.Identifier;
import net.minecraft.world.phys.Vec3;
import org.lwjgl.glfw.GLFW;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Sword Coach. Watches your sword fights from your own client and streams them to the Sword Coach
 * server running on this computer, which reads both players' techniques and saves the fight for the
 * review page. In game: a small panel (J) with the latest read, H to replay your last fight with
 * dummies, K to jump to the moments worth rewatching, Y to pick any saved fight to replay, U for record mode.
 *
 * <p>Observe only: the mod sends nothing to the Minecraft server, never presses keys or moves you,
 * and its replay dummies exist only in your client.</p>
 */
public final class SwordCoach implements ClientModInitializer {
    public static final Logger LOG = LoggerFactory.getLogger("swordcoach");
    private static final String NS = "swordcoach";

    final Config config = Config.load(FabricLoader.getInstance().getGameDir());
    final Sidecar link = new Sidecar();
    final FightWatcher watcher = new FightWatcher(config);
    final RecordMode record = new RecordMode();
    final Replay replay = new Replay();
    final Copilot copilot = new Copilot();
    JsonObject lastTip, summary;
    JsonArray exchanges;                 // the server's reading of the last fight, per exchange
    JsonArray lastSounds, lastCrits;     // its attack sounds and crits, per tick
    boolean hudVisible = true;
    private boolean wasConnected, helloSeen, soundsSent;
    private int soundsRetry;
    private KeyMapping hudKey, wholeKey, worseKey, fightsKey, recordKey, prevKey, nextKey, copilotKey;
    private KeyMapping camKey, pauseKey, backKey, fwdKey, fasterKey, slowerKey, tickBackKey, tickFwdKey;

    @Override
    public void onInitializeClient() {
        link.port = config.serverPort;
        replay.sounds = config.replaySounds;
        KeyMapping.Category cat = KeyMapping.Category.register(Identifier.fromNamespaceAndPath(NS, "main"));
        hudKey = key("hud", GLFW.GLFW_KEY_J, cat);
        wholeKey = key("whole", GLFW.GLFW_KEY_H, cat);
        worseKey = key("worse", GLFW.GLFW_KEY_K, cat);
        fightsKey = key("fights", GLFW.GLFW_KEY_Y, cat);
        recordKey = key("record", GLFW.GLFW_KEY_U, cat);
        prevKey = key("prev", GLFW.GLFW_KEY_LEFT_BRACKET, cat);
        nextKey = key("next", GLFW.GLFW_KEY_RIGHT_BRACKET, cat);
        camKey = key("camera", GLFW.GLFW_KEY_V, cat);
        pauseKey = key("pause", GLFW.GLFW_KEY_B, cat);
        backKey = key("back", GLFW.GLFW_KEY_LEFT, cat);
        fwdKey = key("forward", GLFW.GLFW_KEY_RIGHT, cat);
        fasterKey = key("faster", GLFW.GLFW_KEY_UP, cat);
        slowerKey = key("slower", GLFW.GLFW_KEY_DOWN, cat);
        tickBackKey = key("tick_back", GLFW.GLFW_KEY_COMMA, cat);
        tickFwdKey = key("tick_forward", GLFW.GLFW_KEY_PERIOD, cat);
        copilotKey = key("copilot", GLFW.GLFW_KEY_G, cat);
        copilot.on = config.copilot;
        ClientTickEvents.END_CLIENT_TICK.register(this::tick);
        HudElementRegistry.addLast(Identifier.fromNamespaceAndPath(NS, "panel"), this::hud);
        HudElementRegistry.attachElementAfter(VanillaHudElements.CROSSHAIR, Identifier.fromNamespaceAndPath(NS, "copilot_crosshair"), this::copilotCrosshair);
        LevelRenderEvents.AFTER_TRANSLUCENT_FEATURES.register(this::copilotWorld);
        LOG.info("Sword Coach ready; server expected on 127.0.0.1:{}", link.port);
    }

    private static KeyMapping key(String name, int glfw, KeyMapping.Category cat) {
        return KeyMappingHelper.registerKeyMapping(new KeyMapping("key." + NS + "." + name, InputConstants.Type.KEYSYM, glfw, cat));
    }

    private void tick(Minecraft mc) {
        link.tick();
        boolean connected = link.connected();
        if (connected && !wasConnected) {
            record.send(link);       // a fresh server must know the declared technique
            sendCopilot();
            helloSeen = soundsSent = false;      // and gets this game's hit sounds after its hello
        }
        wasConnected = connected;
        for (JsonObject m; (m = link.inbox.poll()) != null; ) handle(mc, m);
        // The sounds can only be read once the game has loaded its resources (no loading overlay); until then the
        // sound list is empty, so try again every 10 s until they are sent.
        if (connected && helloSeen && !soundsSent && mc.getOverlay() == null && --soundsRetry <= 0) {
            soundsSent = SoundFiles.send(mc, link);
            soundsRetry = 200;
        }
        while (hudKey.consumeClick()) hudVisible = !hudVisible;
        while (copilotKey.consumeClick()) {
            copilot.on = !copilot.on;
            config.copilot = copilot.on;
            config.save(FabricLoader.getInstance().getGameDir());
            if (!copilot.on) copilot.clear();
            sendCopilot();
        }
        while (recordKey.consumeClick()) record.toggle(link);
        while (prevKey.consumeClick()) if (record.on) record.cycle(link, -1);
        while (nextKey.consumeClick()) if (record.on) record.cycle(link, 1);
        // Replays start only between fights; while one plays, fights are not watched.
        while (wholeKey.consumeClick()) {
            if (replay.active) replay.stop();
            else if (!watcher.fighting && replay.load(watcher.lastReplay, exchanges, lastSounds, lastCrits, "Last fight")) replay.start(mc, 0);
        }
        while (worseKey.consumeClick()) {
            if (replay.active) replay.stop();
            else if (!watcher.fighting && replay.load(watcher.lastReplay, exchanges, lastSounds, lastCrits, "Last fight")) {
                int[] w = replay.worse();
                replay.start(mc, w.length > 0 ? w[0] : 0);
            }
        }
        // Your saved fights, to pick one to replay (between fights only).
        while (fightsKey.consumeClick()) {
            if (watcher.fighting) continue;
            if (replay.active) replay.stop();
            mc.setScreen(new FightsScreen(this));
        }
        // Replay controls do nothing outside a replay (their presses are still used up).
        while (camKey.consumeClick()) if (replay.active) replay.cycleCam(mc);
        while (pauseKey.consumeClick()) if (replay.active) replay.togglePause();
        while (backKey.consumeClick()) if (replay.active) replay.step(-1);
        while (fwdKey.consumeClick()) if (replay.active) replay.step(1);
        while (fasterKey.consumeClick()) if (replay.active) replay.speed(1);
        while (slowerKey.consumeClick()) if (replay.active) replay.speed(-1);
        while (tickBackKey.consumeClick()) if (replay.active) replay.tickStep(-1);
        while (tickFwdKey.consumeClick()) if (replay.active) replay.tickStep(1);
        if (!replay.active) {
            boolean was = watcher.fighting;
            watcher.tick(mc, link);
            if (!was && watcher.fighting) {          // a new fight: forget the last one's reads
                lastTip = null;
                summary = null;
                exchanges = null;
                lastSounds = lastCrits = null;
                copilot.heldBack = false;
            }
        }
        replay.tick(mc);
        if (replay.active && copilot.on) copilot.atFrame(replay.frame());
    }

    private void handle(Minecraft mc, JsonObject m) {
        String t = m.has("t") ? m.get("t").getAsString() : "";
        switch (t) {
            case "hello" -> {
                Techniques.set(m.getAsJsonArray("techniques"), m.getAsJsonArray("labels"));
                helloSeen = true;
            }
            case "tip" -> lastTip = m;
            case "counter" -> copilot.counter(m);
            case "hp" -> copilot.hp(m);
            case "copilot_fight" -> {
                copilot.clear();
                copilot.heldBack = m.has("held_back") && m.get("held_back").getAsBoolean();
            }
            case "summary" -> summary = m;
            case "exchanges" -> {
                exchanges = m.getAsJsonArray("exchanges");
                lastSounds = m.has("sounds") ? m.getAsJsonArray("sounds") : null;
                copilot.setCounters(m.has("counters") && m.get("counters").isJsonArray() ? m.getAsJsonArray("counters") : null);
                watcher.lastReplay.setHealth(m.has("hp") && m.get("hp").isJsonArray() ? m.getAsJsonArray("hp") : null,
                        m.has("hp_estimated") && m.get("hp_estimated").getAsBoolean());
                lastCrits = m.has("crits") ? m.getAsJsonArray("crits") : null;
            }
            case "list" -> {
                if (mc.screen instanceof FightsScreen fs) fs.setFights(m.getAsJsonArray("fights"));
            }
            case "replay" -> {
                String id = m.has("id") ? m.get("id").getAsString() : null;
                if (!(mc.screen instanceof FightsScreen fs) || !fs.waitingFor(id)) return;
                if (watcher.fighting) {
                    fs.failed("A fight is on: replays wait until it ends");
                    return;
                }
                boolean ok = false;
                try {
                    ok = !m.has("failed")
                            && replay.load(ReplayLog.fromServer(m), m.getAsJsonArray("exchanges"), m.getAsJsonArray("sounds"),
                            m.getAsJsonArray("crits"), m.has("title") ? m.get("title").getAsString() : "Fight");
                } catch (RuntimeException e) {
                    LOG.warn("could not load fight {}: {}", id, e.toString());
                }
                if (!ok) {
                    fs.failed("That fight could not be read");
                    return;
                }
                copilot.setCounters(m.has("counters") && m.get("counters").isJsonArray() ? m.getAsJsonArray("counters") : null);
                mc.setScreen(null);
                replay.start(mc, 0);
            }
            default -> {
            }
        }
    }

    private void sendCopilot() {
        JsonObject o = new JsonObject();
        o.addProperty("t", "copilot");
        o.addProperty("on", copilot.on);
        link.send(o);
    }

    private void copilotWorld(LevelRenderContext ctx) {
        Minecraft mc = Minecraft.getInstance();
        if (!copilot.on || mc.player == null) return;
        float pt = mc.getDeltaTracker().getGameTimeDeltaPartialTick(true);
        if (replay.active) {         // the same guides, on the replay's two players
            if (replay.you() != null && replay.opp() != null) copilot.drawWorld(ctx, replay.you().getPosition(pt), replay.opp().getPosition(pt), step(replay.opp()), replay.opp().getViewYRot(pt));
            return;
        }
        if (!watcher.fighting || watcher.target == null) return;
        Vec3 me = mc.player.getPosition(pt), them = watcher.target.getPosition(pt);
        copilot.drawWorld(ctx, me, them, step(watcher.target), watcher.target.getViewYRot(pt));
    }

    /** How far someone moved in the last tick. */
    private static Vec3 step(net.minecraft.world.entity.Entity e) {
        return new Vec3(e.getX() - e.xo, 0.0, e.getZ() - e.zo);
    }

    private void copilotCrosshair(GuiGraphicsExtractor g, DeltaTracker delta) {
        Minecraft mc = Minecraft.getInstance();
        if (!copilot.on || replay.active || !watcher.fighting || watcher.target == null || mc.player == null || mc.options.hideGui) return;
        copilot.drawCrosshair(g, mc.font, mc.player, watcher.target);
    }

    // ---- HUD --------------------------------------------------------------------------------
    private static final int BG = 0xD0101418, LINE = 0xFF2B343E, TEXT = 0xFFE5EAEE, FAINT = 0xFF93A0AC;
    private static final int YOU = 0xFF000000 | Replay.YOU, THEM = 0xFF000000 | Replay.THEM;
    private static final int WORSE = 0xFF000000 | Replay.WORSE, BETTER = 0xFF000000 | Replay.BETTER, REC = 0xFFE5484D, COPILOT = 0xFFA855F7;

    private void hud(GuiGraphicsExtractor g, DeltaTracker delta) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.options.hideGui || mc.player == null) return;
        Font f = mc.font;
        if (replay.active) {
            card(g, f, mc);
            return;
        }
        int bottom = hudVisible ? panel(g, f) : 2;
        if (record.on) recordStrip(g, f, 6, bottom + 4, 236);
    }

    /** The panel: offline notice, the latest read during a fight, the last fight's summary after it. */
    private int panel(GuiGraphicsExtractor g, Font f) {
        int x = 6, y = 6, w = 236;
        List<String[]> rows = new ArrayList<>();          // text, colour
        if (!link.connected()) {
            rows.add(row("Sword Coach server not running", FAINT));
            rows.add(row("start Launch AI Server.bat", FAINT));
        } else if (watcher.fighting && !config.liveReads) {
            rows.add(row(copilot.on ? "Recording this fight, copilot on (G)" : "Recording this fight", FAINT));
        } else if (watcher.fighting) {
            double d = watcher.target != null && Minecraft.getInstance().player != null
                    ? Math.hypot(watcher.target.getX() - Minecraft.getInstance().player.getX(), watcher.target.getZ() - Minecraft.getInstance().player.getZ()) : 0;
            rows.add(row(String.format(Locale.ROOT, "vs %s   %.1f blocks", watcher.targetName, d), FAINT));
            if (lastTip != null) {
                rows.add(row("They: " + read(lastTip.getAsJsonObject("them")), THEM));
                rows.add(row("You: " + read(lastTip.getAsJsonObject("you")), YOU));
            } else {
                rows.add(row("reading the first exchange...", FAINT));
            }
        } else if (watcher.lastReplay.size() > 1) {
            if (summary == null) rows.add(row("Last fight: reading it...", FAINT));
            else if (summary.has("failed")) rows.add(row("Last fight: could not be read", FAINT));
            else {
                int worse = summary.get("worse").getAsInt(), better = summary.get("better").getAsInt();
                rows.add(row(String.format(Locale.ROOT, "Last fight: %d exchanges", summary.get("exchanges").getAsInt()), TEXT));
                rows.add(row(String.format(Locale.ROOT, "%d went worse, %d better than expected", worse, better), worse > better ? WORSE : BETTER));
                if (worse > 0) rows.add(row("K rewatch the worse moments", TEXT));
            }
            rows.add(row("H replay the whole fight", YOU));
            rows.add(row("Y your saved fights", YOU));
            rows.add(row("Review page: 127.0.0.1:47320", FAINT));
        } else {
            rows.add(row("Waiting for a fight (someone within 6 blocks)", FAINT));
            rows.add(row(copilot.on ? "Copilot on (G)" : "Copilot off (G)", copilot.on ? COPILOT : FAINT));
            rows.add(row("Y your saved fights", YOU));
        }
        int h = 20 + rows.size() * 11;
        g.fill(x, y, x + w, y + h, BG);
        g.fill(x, y, x + w, y + 1, LINE);
        g.text(f, "SWORD COACH", x + 6, y + 6, YOU, false);
        String state = link.connected() ? "live" : "offline";
        g.text(f, state, x + w - 6 - f.width(state), y + 6, link.connected() ? YOU : FAINT, false);
        int yy = y + 19;
        for (String[] r : rows) {
            g.text(f, fit(f, r[0], w - 12), x + 6, yy, Integer.parseInt(r[1]), false);
            yy += 11;
        }
        return y + h;
    }

    private static String[] row(String text, int color) {
        return new String[]{text, Integer.toString(color)};
    }

    /** "Jump reset" or "Jump reset?" when the reader is unsure. */
    private static String read(JsonObject r) {
        return r.get("name").getAsString() + (r.get("p").getAsDouble() < 0.45 ? "?" : "");
    }

    private void recordStrip(GuiGraphicsExtractor g, Font f, int x, int y, int w) {
        int h = 30;
        g.fill(x, y, x + w, y + h, BG);
        g.fill(x, y, x + 3, y + h, REC);
        g.text(f, "● REC", x + 9, y + 6, REC, false);
        g.text(f, fit(f, record.label(), w - 60), x + 48, y + 6, TEXT, false);
        g.text(f, fit(f, "[ ] technique   U stop", w - 15), x + 9, y + 18, FAINT, false);
    }

    private void card(GuiGraphicsExtractor g, Font f, Minecraft mc) {
        int sw = mc.getWindow().getGuiScaledWidth();
        int w = Math.min(sw - 20, 470);
        int x = (sw - w) / 2, y = 8;
        String counter = copilot.on ? copilot.counterLine() : null;
        float[] hp = replay.healthNow();
        int h = 18 + 11 * replay.lines.length + (counter != null ? 11 : 0) + (hp != null ? 14 : 0) + 14 + 22;
        g.fill(x, y, x + w, y + h, BG);
        g.fill(x, y, x + 3, y + h, YOU);
        g.text(f, fit(f, replay.title, w - 14), x + 9, y + 6, TEXT, false);
        int yy = y + 19;
        for (String line : replay.lines) {
            g.text(f, fit(f, line == null ? "" : line, w - 14), x + 9, yy, TEXT, false);
            yy += 11;
        }
        if (counter != null) {
            g.text(f, fit(f, counter, w - 14), x + 9, yy, copilot.counterLineColor(COPILOT), false);
            yy += 11;
        }
        if (hp != null) {
            int half = (w - 18) / 2;
            healthBar(g, f, x + 9, yy + 2, half - 6, "You", hp[0], false, YOU);
            healthBar(g, f, x + 9 + half, yy + 2, half - 6, "Them", hp[1], replay.hpEstimated, THEM);
            yy += 14;
        }
        // The fight as a strip: one cell per exchange, coloured by how it went; points marked below.
        int tx = x + 9, tw = w - 18, n = replay.segs.length, cur = replay.segAt(replay.frame());
        for (int k = 0; k < n; k++) {
            int a = tx + tw * k / n, b = tx + tw * (k + 1) / n - (n < 60 ? 1 : 0);
            Replay.Seg sg = replay.segs[k];
            int c = sg.call == null ? 0xFF3A444E : "worse".equals(sg.call) ? WORSE : "better".equals(sg.call) ? BETTER : 0xFF7A6A3A;
            g.fill(a, yy + 3, Math.max(a + 1, b), yy + 9, c);
            if (sg.point) g.fill(a, yy + 9, a + 1, yy + 12, FAINT);
            if (k == cur) g.fill(a, yy + 1, Math.max(a + 1, b), yy + 2, TEXT);
        }
        int px = tx + (int) Math.round(tw * replay.progress());
        g.fill(px, yy + 1, px + 1, yy + 11, TEXT);
        yy += 14;
        g.text(f, fit(f, "■ You    ■ Them", w - 14), x + 9, yy + 2, FAINT, false);
        g.text(f, fit(f, replay.controls(), w - 14), x + 9, yy + 13, FAINT, false);
    }

    /** One player's health on the replay card: name, a bar filling with it (red under a third), and the number (~ where it is worked out
     * from your hits because the server hid it). */
    private static void healthBar(GuiGraphicsExtractor g, Font f, int x, int y, int w, String who, float hp, boolean estimated, int color) {
        String num = String.format(Locale.ROOT, "%s%.1f \u2764", estimated ? "~" : "", hp);
        int lw = f.width(who) + 4, nw = f.width(num) + 4, bw = Math.max(10, w - lw - nw);
        g.text(f, who, x, y, color, false);
        int bx = x + lw;
        g.fill(bx, y + 1, bx + bw, y + 8, 0xFF2A323B);
        float frac = Math.max(0f, Math.min(1f, hp / 20f));
        int fillColor = hp < 6.5f ? 0xFFFF5C5C : hp < 12.5f ? 0xFFFFD23F : 0xFF4ADE80;
        g.fill(bx, y + 1, bx + Math.round(bw * frac), y + 8, fillColor);
        for (int k = 1; k < 10; k++) g.fill(bx + bw * k / 10, y + 1, bx + bw * k / 10 + 1, y + 8, 0x66101418);
        g.text(f, num, bx + bw + 4, y, estimated ? 0xFFFFD23F : TEXT, false);
    }

    static String fit(Font f, String s, int w) {
        if (f.width(s) <= w) return s;
        while (s.length() > 1 && f.width(s + "...") > w) s = s.substring(0, s.length() - 1);
        return s + "...";
    }
}
