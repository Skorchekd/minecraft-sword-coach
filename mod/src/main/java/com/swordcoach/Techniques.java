// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonArray;

/** The technique list. The server sends its own on connect; this is the same list for when it has not yet. */
final class Techniques {
    static String[] ids = {"sprint_hit", "w_tap", "s_tap", "jump_crit", "jump_reset", "strafe", "space", "bait",
            "retreat", "crit_counter", "sneak_tap", "circle_strafe", "reset_crit", "hit_select", "kb_displace",
            "spam_click", "jump_spam", "stand_trade", "crit_deflection", "punish_crit", "nokb_crit", "double_crit",
            "uppercut", "falling_sprint_hit", "s_crit", "s_hold_deflection", "repositioning", "pick_hit", "sprint_crit",
            "punish_crit_reaction", "nokb_combo", "crouch_dodge", "stun_hit_prediction",
            "falling_sprint_hit_deflection", "single_sweep", "sweep_combo", "followup_sweep", "backaway_sweep",
            "punish_sweep", "back_sweep", "side_sweep", "run_in", "jump_in", "jump_reset_sprint_hit"};
    static String[] labels = {"Sprint hit", "W-tap", "S-tap", "Jump crit", "Jump reset", "Strafe", "Spacing", "Bait",
            "Retreat", "Crit counter", "Sneak-tap", "Circle strafe", "Reset crit", "Hit select", "KB displacement",
            "Spam click", "Jump spam", "Stand and trade", "Crit deflection", "Punish crit", "No-KB crit", "Double crit",
            "Uppercut", "Falling sprint hit", "S-crit", "S-hold deflection", "Repositioning", "Pick hit", "Sprint crit",
            "Punish crit reaction", "No-KB combo", "Crouch dodge", "Stun hit prediction",
            "Falling sprint hit deflection", "Single sweep", "Sweep combo", "Follow-up sweep", "Back-away sweep",
            "Punish sweep", "Back sweep", "Side sweep", "Run in", "Jump in", "Jump reset sprint hit"};

    private Techniques() {
    }

    static void set(JsonArray idList, JsonArray labelList) {
        if (idList == null || labelList == null || idList.size() != labelList.size() || idList.isEmpty()) return;
        String[] i = new String[idList.size()], l = new String[idList.size()];
        for (int k = 0; k < i.length; k++) {
            i[k] = idList.get(k).getAsString();
            l[k] = labelList.get(k).getAsString();
        }
        ids = i;
        labels = l;
    }

    static String label(String id) {
        for (int k = 0; k < ids.length; k++) if (ids[k].equals(id)) return labels[k];
        return id;
    }
}
