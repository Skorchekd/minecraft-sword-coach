// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

/**
 * The replay's eye camera. While set, the camera mixin draws the view from this dummy's eyes
 * instead of yours. It only moves the rendered view: the game's camera entity stays you, so your
 * client keeps sending its movement exactly as normal (vanilla stops them while the camera entity
 * is anything else, which a server would see as a gap).
 */
public final class ReplayCamera {
    public static volatile Dummy eye;

    private ReplayCamera() {
    }
}
