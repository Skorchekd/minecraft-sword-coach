# Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
# SPDX-License-Identifier: GPL-3.0-only
"""The per-tick record the mod streams (one row per client tick) and the technique list."""

# One row per client tick, as the mod sends it ("r"): you exactly, them as your client receives them.
RAW_FIELDS = ["sx", "sy", "sz", "syaw", "spitch", "sground", "ssprint", "sfall", "shurt", "sinv",
              "shp", "scharge", "sswing",
              "ox", "oy", "oz", "oyaw", "oground", "osprint", "osneak", "ohurt", "ohp", "oswing",
              "ping_s", "ping_o"]
R = {n: i for i, n in enumerate(RAW_FIELDS)}
RAW_N = len(RAW_FIELDS)

# Your keys per tick ("i"): forward, back, left, right, jump, sneak, sprint, attack click.
KEY_NAMES = ["forward", "back", "left", "right", "jump", "sneak", "sprint", "click"]

# The readers output the first 18, in this order. The ones after them can be labelled (relabels, record mode) but are
# not read yet.
TECHNIQUES = ["sprint_hit", "w_tap", "s_tap", "jump_crit", "jump_reset", "strafe", "space", "bait", "retreat",
              "crit_counter", "sneak_tap", "circle_strafe", "reset_crit", "hit_select", "kb_displace", "spam_click",
              "jump_spam", "stand_trade",
              "crit_deflection", "punish_crit", "nokb_crit", "double_crit", "uppercut", "falling_sprint_hit", "s_crit",
              "s_hold_deflection", "repositioning", "pick_hit", "sprint_crit", "punish_crit_reaction", "nokb_combo",
              "crouch_dodge", "stun_hit_prediction", "falling_sprint_hit_deflection", "single_sweep", "sweep_combo",
              "followup_sweep", "backaway_sweep", "punish_sweep", "back_sweep", "side_sweep", "run_in", "jump_in",
              "jump_reset_sprint_hit"]
LABELS = {
    "sprint_hit": "Sprint hit", "w_tap": "W-tap", "s_tap": "S-tap", "jump_crit": "Jump crit", "jump_reset": "Jump reset",
    "strafe": "Strafe", "space": "Spacing", "bait": "Bait", "retreat": "Retreat", "crit_counter": "Crit counter",
    "sneak_tap": "Sneak-tap", "circle_strafe": "Circle strafe", "reset_crit": "Reset crit", "hit_select": "Hit select",
    "kb_displace": "KB displacement", "spam_click": "Spam click", "jump_spam": "Jump spam", "stand_trade": "Stand and trade",
    "crit_deflection": "Crit deflection", "punish_crit": "Punish crit", "nokb_crit": "No-KB crit",
    "double_crit": "Double crit", "uppercut": "Uppercut", "falling_sprint_hit": "Falling sprint hit", "s_crit": "S-crit",
    "s_hold_deflection": "S-hold deflection", "repositioning": "Repositioning", "pick_hit": "Pick hit",
    "sprint_crit": "Sprint crit", "punish_crit_reaction": "Punish crit reaction", "nokb_combo": "No-KB combo",
    "crouch_dodge": "Crouch dodge", "stun_hit_prediction": "Stun hit prediction",
    "falling_sprint_hit_deflection": "Falling sprint hit deflection", "single_sweep": "Single sweep",
    "sweep_combo": "Sweep combo", "followup_sweep": "Follow-up sweep", "backaway_sweep": "Back-away sweep",
    "punish_sweep": "Punish sweep", "back_sweep": "Back sweep", "side_sweep": "Side sweep", "run_in": "Run in",
    "jump_in": "Jump in", "jump_reset_sprint_hit": "Jump reset sprint hit",
}
# 0 entry, 1 mid, 2 high
TIER = {"sprint_hit": 1, "w_tap": 1, "s_tap": 1, "jump_crit": 2, "jump_reset": 2, "strafe": 1, "space": 2, "bait": 2,
        "retreat": 1, "crit_counter": 2, "sneak_tap": 1, "circle_strafe": 1, "reset_crit": 2, "hit_select": 2,
        "kb_displace": 2, "spam_click": 0, "jump_spam": 0, "stand_trade": 0,
        "crit_deflection": 1, "punish_crit": 1, "nokb_crit": 1, "double_crit": 1, "uppercut": 2, "falling_sprint_hit": 2,
        "s_crit": 2, "s_hold_deflection": 2, "repositioning": 2, "pick_hit": 2, "sprint_crit": 2,
        "punish_crit_reaction": 2, "nokb_combo": 2, "crouch_dodge": 2, "stun_hit_prediction": 2,
        "falling_sprint_hit_deflection": 2, "single_sweep": 2, "sweep_combo": 2, "followup_sweep": 2,
        "backaway_sweep": 2, "punish_sweep": 2, "back_sweep": 2, "side_sweep": 2, "run_in": 0, "jump_in": 1,
        "jump_reset_sprint_hit": 2}
TIER_NAMES = ["entry", "mid", "high"]
# Skill tree: what each technique builds on.
REQUIRES = {
    "sprint_hit": ["stand_trade"], "jump_spam": ["spam_click"],
    "w_tap": ["sprint_hit"], "s_tap": ["sprint_hit"], "sneak_tap": ["sprint_hit"], "strafe": ["sprint_hit"],
    "retreat": ["sprint_hit"], "circle_strafe": ["strafe"],
    "jump_crit": ["jump_spam"], "jump_reset": ["jump_spam"], "reset_crit": ["jump_reset", "jump_crit"],
    "crit_counter": ["jump_crit"], "space": ["retreat", "strafe"], "bait": ["space"], "hit_select": ["bait"],
    "kb_displace": ["w_tap"], "spam_click": [], "stand_trade": [],
    "crit_deflection": ["jump_crit"], "punish_crit": ["jump_crit"], "nokb_crit": ["jump_crit"],
    "double_crit": ["jump_crit"], "uppercut": ["sprint_hit"], "falling_sprint_hit": ["sprint_hit"],
    "s_crit": ["s_tap", "jump_crit"], "s_hold_deflection": ["s_tap"], "repositioning": ["strafe"],
    "pick_hit": ["sprint_hit"], "sprint_crit": ["sprint_hit", "jump_crit"], "punish_crit_reaction": ["punish_crit"],
    "nokb_combo": ["nokb_crit"], "crouch_dodge": ["sneak_tap"], "stun_hit_prediction": ["crouch_dodge"],
    "falling_sprint_hit_deflection": ["falling_sprint_hit"], "single_sweep": ["stand_trade"],
    "sweep_combo": ["single_sweep"], "followup_sweep": ["single_sweep"], "backaway_sweep": ["single_sweep"],
    "punish_sweep": ["single_sweep"], "back_sweep": ["single_sweep"], "side_sweep": ["single_sweep"],
    "run_in": [], "jump_in": ["run_in", "jump_spam"], "jump_reset_sprint_hit": ["jump_reset", "sprint_hit"],
}
# What each technique means, as the page shows it next to the picker. One meaning per name is what keeps labels from
# different players comparable, so these say what counts, not how good the move is.
DEFINITIONS = {
    "sprint_hit": "A fully charged hit landed while sprinting. It names the hit itself, nothing around it.",
    "w_tap": "Let go of W and press it again right after a sprint hit. How long you let go does not matter.",
    "s_tap": "Tap S right after a sprint hit. It ends when S is released; running back in is a separate move.",
    "jump_crit": "Jump and land a fully charged hit on the way down, not sprinting.",
    "jump_reset": "Jump on the tick their hit lands, with W and sprint held. Holding them is what cuts the knockback.",
    "strafe": "Switching A and D while running in, so you are harder to aim at.",
    "space": "General positioning: holding the distance you want. Backing off after a hit is Retreat instead.",
    "bait": "Getting them to commit to something you can punish. It comes in many forms, such as an S-tap bait or a run-in bait.",
    "retreat": "Backing away after a hit.",
    "crit_counter": "Riding their knockback into a falling crit of your own.",
    "sneak_tap": "Tapping sneak as your hit goes in.",
    "circle_strafe": "Holding one strafe direction while running in, so you circle them.",
    "reset_crit": "A jump reset followed by a crit from that same jump.",
    "hit_select": "Waiting in reach, charged, and choosing when to hit. There is no fixed wait: the closer you are, the longer it usually is, aiming for a hit they cannot answer.",
    "kb_displace": "Flicking your aim off them just before a sprint hit, so the knockback sends them where you choose.",
    "spam_click": "Hitting as early as you can, often at part charge. Constantly running at them and hitting early for a full hit is also called 3 block spam.",
    "jump_spam": "Jumping again right after you land, to deny them momentum.",
    "stand_trade": "Standing in range and trading hits with almost no movement.",
    "crit_deflection": "Only off someone critting you: wait until they land, and sprint hit them the exact moment they touch the ground, so they take a lot of knockback.",
    "punish_crit": "A crit made off the knockback from their hit. It does not count when they whiff.",
    "nokb_crit": "After you crit, hold W and wait for them to hit you, which reduces your knockback. Only after they hit you go for your second hit.",
    "double_crit": "Two crits in a row, close together.",
    "uppercut": "A sprint hit on the way up from a jump. S afterwards is situational, usually in mid air for spacing.",
    "falling_sprint_hit": "A sprint hit landed while falling, usually from more distance.",
    "s_crit": "A crit with S held from the moment you crit.",
    "s_hold_deflection": "A normal crit deflection, then S right after your own sprint hit: tap it from long range, hold it from mid range.",
    "repositioning": "Changing your position to the best range for a hit they cannot answer, usually with S. It often means letting them crit you, holding S, then waiting a long time before you hit.",
    "pick_hit": "A long-range hit picked off right at the edge of reach.",
    "sprint_crit": "A crit where you were sprinting until just before the hit.",
    "punish_crit_reaction": "A punish crit made by reacting to their move as it happens, not by planning ahead.",
    "nokb_combo": "A run of No-KB crits chained together.",
    "crouch_dodge": "Sneaking around their swing so that it misses.",
    "stun_hit_prediction": "Reading when a hit will land without them being able to hit back, and timing yours for that moment.",
    "falling_sprint_hit_deflection": "A falling sprint hit used around their swing or hit, the falling version of a deflection.",
    "single_sweep": "One fully charged sweep on the ground, not sprinting.",
    "sweep_combo": "Two or more sweeps close together.",
    "followup_sweep": "A sweep right after one of your own hits landed.",
    "backaway_sweep": "A sweep while backing away from them.",
    "punish_sweep": "A sweep that punishes their whiff.",
    "back_sweep": "A sweep with S held.",
    "side_sweep": "A sweep while strafing, without W.",
    "run_in": "Sprinting straight at them from range to close the distance.",
    "jump_in": "Jumping in from range. Only the jumping in counts; the hit after it is a separate move.",
    "jump_reset_sprint_hit": "A sprint hit landed during the jump of a jump reset.",
}
SEG = 12          # ticks per exchange

# How far apart you are when an exchange starts (blocks between your feet, flat), for the pages' distance views.
DIST_BANDS = [("close", "Close", 0.0, 2.5), ("reach", "At reach", 2.5, 3.5), ("edge", "Just out of reach", 3.5, 4.5),
              ("apart", "Apart", 4.5, float("inf"))]


def band_of(dist):
    return next(k for k, _, lo, hi in DIST_BANDS if lo <= dist < hi)


# Player tiers you can set for yourself (Your data tab); a bundle carries yours so fights from players of different
# levels can be told apart. Best first.
PLAYER_TIERS = ["HT1", "LT1", "HT2", "LT2", "HT3", "LT3", "HT4", "LT4", "HT5", "LT5"]

# Families, for the fight flow chart's rows. The answer model knows the first 5.
FAMILIES = [("Sprint resets", ["sprint_hit", "w_tap", "s_tap", "sneak_tap", "kb_displace", "uppercut",
                               "falling_sprint_hit", "pick_hit", "falling_sprint_hit_deflection"]),
            ("Jumps and crits", ["jump_crit", "jump_reset", "reset_crit", "jump_spam", "crit_counter", "crit_deflection",
                                 "punish_crit", "nokb_crit", "double_crit", "s_crit", "sprint_crit",
                                 "punish_crit_reaction", "nokb_combo", "jump_reset_sprint_hit"]),
            ("Strafing", ["strafe", "circle_strafe", "crouch_dodge"]),
            ("Range play", ["space", "bait", "retreat", "hit_select", "s_hold_deflection", "repositioning",
                            "stun_hit_prediction"]),
            ("Entry", ["spam_click", "stand_trade"]),
            ("Sweeps", ["single_sweep", "sweep_combo", "followup_sweep", "backaway_sweep", "punish_sweep", "back_sweep",
                        "side_sweep"]),
            ("Approaches", ["run_in", "jump_in"])]
FAMILY = {t: i for i, (_, ts) in enumerate(FAMILIES) for t in ts}
SHORT = {"sprint_hit": "SH", "w_tap": "WT", "s_tap": "ST", "jump_crit": "JC", "jump_reset": "JR", "strafe": "SF",
         "space": "SP", "bait": "BT", "retreat": "RT", "crit_counter": "CC", "sneak_tap": "NT", "circle_strafe": "CS",
         "reset_crit": "RC", "hit_select": "HS", "kb_displace": "KD", "spam_click": "SC", "jump_spam": "JS",
         "stand_trade": "TR", "crit_deflection": "CD", "punish_crit": "PC", "nokb_crit": "NC", "double_crit": "DC",
         "uppercut": "UC", "falling_sprint_hit": "FS", "s_crit": "S-C", "s_hold_deflection": "SHD", "repositioning": "RP",
         "pick_hit": "PH", "sprint_crit": "SPC", "punish_crit_reaction": "PCR", "nokb_combo": "NKC", "crouch_dodge": "DG",
         "stun_hit_prediction": "SHP", "falling_sprint_hit_deflection": "FSD", "single_sweep": "SW", "sweep_combo": "SWC",
         "followup_sweep": "FUS", "backaway_sweep": "BAS", "punish_sweep": "PSW", "back_sweep": "BSW", "side_sweep": "SSW",
         "run_in": "RI", "jump_in": "JI", "jump_reset_sprint_hit": "JRS"}

# Labels: how well each side executed its technique in an exchange, and what went wrong (any number of these).
EXECUTION = ["poor", "decent", "excellent"]
EXECUTION_LABELS = {"poor": "Poor", "decent": "Decent", "excellent": "Excellent"}
FAILS = ["missed_hit", "too_close", "too_far", "mistimed"]
FAIL_LABELS = {"missed_hit": "Missed hit", "too_close": "Too close", "too_far": "Too far", "mistimed": "Mistimed"}

# Hit events per tick ("e"), a bit mask the mod builds from the server's own packets: the attack sound the server
# played at a player (that player attacked; bits 0-5 you, 6-11 them, in SOUND_KINDS order), and the crit /
# enchanted-hit particles the server put on a player (that player was hit; 12 crit on you, 13 crit on them, 14 and
# 15 the enchanted-hit sparks).
SOUND_KINDS = ["crit", "knockback", "strong", "weak", "sweep", "nodamage"]
SOUND_EVENTS = {"crit": "entity.player.attack.crit", "knockback": "entity.player.attack.knockback",
                "strong": "entity.player.attack.strong", "weak": "entity.player.attack.weak",
                "sweep": "entity.player.attack.sweep", "nodamage": "entity.player.attack.nodamage",
                "hurt": "entity.player.hurt"}
EV_CRIT_ON = 12
EV_MAGIC_ON = 14
