// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonObject;

/**
 * Record mode (U): you declare the technique you are practising ([ and ] to switch). The server saves
 * it with the fight, so the review shows what you meant to do next to what the readers saw.
 */
final class RecordMode {
    boolean on;
    private int index;          // 0 = free play, then the techniques in the server's order

    void toggle(Sidecar link) {
        on = !on;
        send(link);
    }

    void cycle(Sidecar link, int d) {
        int n = Techniques.ids.length + 1;
        index = ((index + d) % n + n) % n;
        send(link);
    }

    /** The declared technique id, or null for free play or when record mode is off. */
    String technique() {
        return on && index > 0 ? Techniques.ids[index - 1] : null;
    }

    String label() {
        return index > 0 ? Techniques.label(Techniques.ids[index - 1]) : "free play";
    }

    /** Tell the server; also called after every reconnect so it never holds a stale choice. */
    void send(Sidecar link) {
        JsonObject o = new JsonObject();
        o.addProperty("t", "intent");
        String t = technique();
        if (t == null) o.add("technique", com.google.gson.JsonNull.INSTANCE);
        else o.addProperty("technique", t);
        link.send(o);
    }
}
