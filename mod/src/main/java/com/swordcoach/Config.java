// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * config/swordcoach.json, written with defaults on first start.
 *
 * <ul>
 * <li>{@code fight_kit}: what makes a nearby player a fight. "sword" (both hold a sword and wear some
 * armour; the default, so a lobby is not a fight), "sword_only", or "any".</li>
 * <li>{@code spoofed_health_servers}: servers that hide other players' real health; there only the
 * number drawn over their head is trusted.</li>
 * <li>{@code server_port}: where the Sword Coach server listens on this computer.</li>
 * <li>{@code live_reads}: show the distance and both players' technique reads on screen during a fight.
 * Off by default: during a fight the panel only says it is recording, so nothing on screen helps you
 * mid-fight (what a server's rules care about); everything is in the review afterwards.</li>
 * <li>{@code copilot}: the fight copilot (G in game): guides on the ground and a crosshair, drawn in this client only. Off by default.</li>
 * <li>{@code replay_sounds}: replays play the fight's hit sounds (attack and hurt sounds, client-only). On by
 * default.</li>
 * </ul>
 */
final class Config {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting()
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES).create();

    String fightKit = "sword";
    List<String> spoofedHealthServers = new ArrayList<>(List.of("pvphq.com"));
    int serverPort = 47310;
    boolean liveReads = false;
    boolean replaySounds = true;
    boolean copilot = false;

    static Config load(Path gameDir) {
        Path file = gameDir.resolve("config").resolve("swordcoach.json");
        Config c = null;
        try {
            if (Files.exists(file)) c = GSON.fromJson(Files.readString(file, StandardCharsets.UTF_8), Config.class);
        } catch (Exception e) {
            SwordCoach.LOG.warn("could not read {}, using defaults: {}", file, e.toString());
        }
        boolean fresh = c == null;
        if (fresh) c = new Config();
        if (c.fightKit == null || !List.of("sword", "sword_only", "any").contains(c.fightKit)) c.fightKit = "sword";
        if (c.spoofedHealthServers == null) c.spoofedHealthServers = new ArrayList<>(List.of("pvphq.com"));
        c.spoofedHealthServers.removeIf(Objects::isNull);
        if (c.serverPort <= 0 || c.serverPort > 65535) c.serverPort = 47310;
        if (fresh) {
            try {
                Files.createDirectories(file.getParent());
                Files.writeString(file, GSON.toJson(c), StandardCharsets.UTF_8);
            } catch (Exception e) {
                SwordCoach.LOG.warn("could not write {}: {}", file, e.toString());
            }
        }
        return c;
    }

    void save(Path gameDir) {
        Path file = gameDir.resolve("config").resolve("swordcoach.json");
        try {
            Files.createDirectories(file.getParent());
            Files.writeString(file, GSON.toJson(this), StandardCharsets.UTF_8);
        } catch (Exception e) {
            SwordCoach.LOG.warn("could not write {}: {}", file, e.toString());
        }
    }

    boolean healthSpoofed(String host) {
        String h = host == null ? "" : host.toLowerCase(Locale.ROOT);
        for (String s : spoofedHealthServers)
            if (!s.isBlank() && h.contains(s.toLowerCase(Locale.ROOT))) return true;
        return false;
    }
}
