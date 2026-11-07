// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;

import java.util.Locale;

/**
 * Your saved fights (Y), newest first, as the Sword Coach server on this computer lists them. Click one to replay
 * it in your world, the same way H replays the last one. The list and the fight both come from the local server;
 * nothing here talks to the Minecraft server, and the screen does not pause the game.
 */
final class FightsScreen extends Screen {
    private static final int ROW = 24, TOP = 44;
    private final SwordCoach coach;
    private JsonArray fights;            // null until the server answers
    private int page;
    private String waiting, message;

    FightsScreen(SwordCoach coach) {
        super(Component.literal("Your saved fights"));
        this.coach = coach;
        if (coach.link.connected()) {
            JsonObject o = new JsonObject();
            o.addProperty("t", "list");
            coach.link.send(o);
        } else {
            message = "Sword Coach server not running: start Launch AI Server.bat";
        }
    }

    /** The server's list arrived. */
    void setFights(JsonArray list) {
        fights = list;
        rebuildWidgets();
    }

    /** True while this screen waits for that fight. */
    boolean waitingFor(String id) {
        return id != null && id.equals(waiting);
    }

    void failed(String why) {
        waiting = null;
        message = why;
        rebuildWidgets();
    }

    private int rows() {
        return Math.max(3, (height - TOP - 40) / ROW);
    }

    @Override
    protected void init() {
        int w = Math.min(340, width - 40), x = (width - w) / 2, y = TOP, rows = rows();
        int n = fights == null ? 0 : fights.size();
        page = Math.max(0, Math.min(page, (n - 1) / rows));
        for (int i = page * rows; i < Math.min(n, (page + 1) * rows); i++) {
            JsonObject f = fights.get(i).getAsJsonObject();
            String id = f.get("id").getAsString();
            Button b = addRenderableWidget(Button.builder(label(f), btn -> open(id)).bounds(x, y, w, 20).build());
            b.active = waiting == null;
            y += ROW;
        }
        int by = height - 28;
        Button newer = addRenderableWidget(Button.builder(Component.literal("< Newer"), b -> {
            page--;
            rebuildWidgets();
        }).bounds(x, by, 70, 20).build());
        Button older = addRenderableWidget(Button.builder(Component.literal("Older >"), b -> {
            page++;
            rebuildWidgets();
        }).bounds(x + w - 70, by, 70, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Close"), b -> onClose()).bounds(width / 2 - 40, by, 80, 20).build());
        newer.active = page > 0;
        older.active = (page + 1) * rows < n;
    }

    private void open(String id) {
        if (!coach.link.connected()) {
            message = "Sword Coach server not running: start Launch AI Server.bat";
            return;
        }
        waiting = id;
        message = null;
        JsonObject o = new JsonObject();
        o.addProperty("t", "replay");
        o.addProperty("id", id);
        coach.link.send(o);
        rebuildWidgets();
    }

    /** "29 Oct 03:19 · mcpvp.club · LOST · 42 s · ✎3" */
    private static Component label(JsonObject f) {
        int result = f.has("result") && !f.get("result").isJsonNull() ? f.get("result").getAsInt() : -1;
        MutableComponent c = Component.literal(str(f, "when") + " · " + str(f, "server") + " · ");
        c.append(result == 1 ? Component.literal("WON").withStyle(ChatFormatting.GREEN)
                : result == 0 ? Component.literal("LOST").withStyle(ChatFormatting.RED) : Component.literal("—").withStyle(ChatFormatting.GRAY));
        if (f.has("seconds") && !f.get("seconds").isJsonNull())
            c.append(String.format(Locale.ROOT, " · %.0f s", f.get("seconds").getAsDouble()));
        int relabels = f.has("relabels") ? f.get("relabels").getAsInt() : 0;
        if (relabels > 0) c.append(" · ✎" + relabels);
        return c;
    }

    private static String str(JsonObject f, String k) {
        return f.has(k) && !f.get(k).isJsonNull() ? f.get(k).getAsString() : "?";
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor g, int mouseX, int mouseY, float a) {
        super.extractRenderState(g, mouseX, mouseY, a);
        g.centeredText(font, title.getString(), width / 2, 14, 0xFFFFFFFF);
        int n = fights == null ? 0 : fights.size(), rows = rows();
        String sub = message != null ? message
                : waiting != null ? "Loading the fight..."
                : fights == null ? "Reading your fights..."
                : n == 0 ? "No saved fights yet: fight someone with a sword first"
                : String.format(Locale.ROOT, "Click one to replay it here · page %d of %d", page + 1, (n - 1) / rows + 1);
        g.centeredText(font, sub, width / 2, 28, 0xFF93A0AC);
    }

    @Override
    public void extractBackground(GuiGraphicsExtractor g, int mouseX, int mouseY, float a) {
        extractTransparentBackground(g);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
