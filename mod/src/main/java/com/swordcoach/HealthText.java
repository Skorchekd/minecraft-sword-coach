// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import java.util.regex.Pattern;

/**
 * Reads a health number off text a server drew: "20 ❤", "❤ 15.1", a resource-pack heart.
 * Pure (no Minecraft).
 */
final class HealthText {
    private HealthText() {
    }

    private static final Pattern HEART = Pattern.compile(
            "(\\d+(?:[.,]\\d+)?)\\s*[❤♥♡]|[❤♥♡]\\s*(\\d+(?:[.,]\\d+)?)");

    /** A line that is only a number and symbols: a heart drawn with a resource-pack glyph. */
    private static final Pattern BARE = Pattern.compile(
            "^[^\\p{L}\\d]*(\\d{1,3}(?:[.,]\\d+)?)[^\\p{L}\\d]*$");

    /**
     * The first health number in {@code text}, or NaN.
     *
     * @param allowBare also take a line that is just a number (a heart glyph from a resource
     *                  pack); a rank or a level drawn over a head looks the same
     */
    static double parse(String text, boolean allowBare) {
        if (text == null || text.isEmpty()) return Double.NaN;
        for (String line : text.split("\\R")) {
            var m = HEART.matcher(line);
            String n = null;
            if (m.find()) n = m.group(1) != null ? m.group(1) : m.group(2);
            else if (allowBare) {
                var b = BARE.matcher(line.trim());
                if (b.find()) n = b.group(1);
            }
            if (n == null) continue;
            try {
                double v = Double.parseDouble(n.replace(',', '.'));
                if (v >= 0.0 && v <= 2048.0) return v;
            } catch (NumberFormatException bad) {
                // next line
            }
        }
        return Double.NaN;
    }
}
