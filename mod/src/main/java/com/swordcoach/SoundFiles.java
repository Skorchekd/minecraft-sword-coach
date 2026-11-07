// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.Sound;
import net.minecraft.client.sounds.SoundManager;
import net.minecraft.client.sounds.WeighedSoundEvents;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.util.RandomSource;

import java.io.InputStream;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.Optional;
import java.util.Set;

/**
 * Hands the hit sounds of your own game (the attack and hurt sounds, as your resource packs have them) to the Sword
 * Coach server on this computer once per connection, so the review page's clips sound like your game. The files are
 * read from the game's loaded resources; they stay on this computer (the server keeps them in data/sounds, which a
 * fight bundle never includes).
 */
final class SoundFiles {
    private static final SoundEvent[] EVENTS = {SoundEvents.PLAYER_ATTACK_CRIT, SoundEvents.PLAYER_ATTACK_KNOCKBACK,
            SoundEvents.PLAYER_ATTACK_STRONG, SoundEvents.PLAYER_ATTACK_WEAK, SoundEvents.PLAYER_ATTACK_SWEEP,
            SoundEvents.PLAYER_ATTACK_NODAMAGE, SoundEvents.PLAYER_HURT};
    private static final int MAX_FILES = 16, MAX_BYTES = 1_000_000;

    private SoundFiles() {
    }

    /** True when the files were sent; false when the game has none loaded yet (try again later). */
    static boolean send(Minecraft mc, Sidecar link) {
        try {
            JsonArray files = new JsonArray();
            for (SoundEvent ev : EVENTS) {
                WeighedSoundEvents w = mc.getSoundManager().getSoundEvent(ev.location());
                if (w == null) continue;
                // Every variant the game can pick for this sound (the list itself is private, so draw from it).
                Set<Identifier> paths = new LinkedHashSet<>();
                RandomSource r = RandomSource.create(20261029L);
                for (int k = 0; k < 64 && paths.size() < MAX_FILES; k++) {
                    Sound s = w.getSound(r);
                    if (s == null || s.getLocation().equals(SoundManager.EMPTY_SOUND_LOCATION)
                            || s.getLocation().equals(SoundManager.INTENTIONALLY_EMPTY_SOUND_LOCATION)) continue;
                    paths.add(s.getPath());
                }
                for (Identifier p : paths) {
                    Optional<Resource> res = mc.getResourceManager().getResource(p);
                    if (res.isEmpty()) continue;
                    byte[] b;
                    try (InputStream in = res.get().open()) {
                        b = in.readNBytes(MAX_BYTES + 1);
                    }
                    if (b.length > MAX_BYTES) continue;
                    JsonObject f = new JsonObject();
                    f.addProperty("event", ev.location().getPath());
                    f.addProperty("data", Base64.getEncoder().encodeToString(b));
                    files.add(f);
                }
            }
            if (files.isEmpty()) return false;
            JsonObject o = new JsonObject();
            o.addProperty("t", "sounds");
            o.add("files", files);
            link.send(o);
            return true;
        } catch (Exception e) {
            SwordCoach.LOG.warn("could not read the hit sounds for the review page: {}", e.toString());
            return false;
        }
    }
}
