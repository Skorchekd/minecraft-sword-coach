// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentContents;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.contents.KeybindContents;
import net.minecraft.network.chat.contents.TranslatableContents;

/**
 * Turns text a server sent into the string the game would send back, as a client without this
 * mod would. A server can learn which mods are installed by putting a mod's translation or key
 * binding names into a sign it opens for editing or an item name in an anvil: the client fills
 * them in from its own language files and key bindings and sends the result back. Here, this
 * mod's names come out as a client without it shows them (the name itself, or its fallback);
 * everything else, vanilla included, resolves as normal. Used by the sign editor and anvil hooks.
 */
public final class SafeText {
    private SafeText() {
    }

    static boolean ours(String key) {
        return key != null && key.contains("swordcoach");
    }

    /** What {@code c.getString()} gives on a client without this mod. */
    public static String string(Component c) {
        if (c == null) return "";
        return mentions(c) ? rebuild(c).getString() : c.getString();
    }

    private static boolean mentions(Component c) {
        ComponentContents k = c.getContents();
        if (k instanceof TranslatableContents t) {
            if (ours(t.getKey())) return true;
            for (Object a : t.getArgs()) if (a instanceof Component ac && mentions(ac)) return true;
        }
        if (k instanceof KeybindContents kb && ours(kb.getName())) return true;
        for (Component s : c.getSiblings()) if (mentions(s)) return true;
        return false;
    }

    private static MutableComponent rebuild(Component c) {
        ComponentContents k = c.getContents();
        MutableComponent out;
        if (k instanceof TranslatableContents t && ours(t.getKey())) {
            out = Component.literal(t.getFallback() != null ? t.getFallback() : t.getKey());   // an unknown key shows itself
        } else if (k instanceof TranslatableContents t) {
            Object[] args = t.getArgs().clone();
            for (int i = 0; i < args.length; i++) if (args[i] instanceof Component ac) args[i] = rebuild(ac);
            out = Component.translatableWithFallback(t.getKey(), t.getFallback(), args);
        } else if (k instanceof KeybindContents kb && ours(kb.getName())) {
            out = Component.literal(kb.getName());                                            // an unknown binding shows its name
        } else {
            out = MutableComponent.create(k);
        }
        out.setStyle(c.getStyle());
        for (Component s : c.getSiblings()) out.append(rebuild(s));
        return out;
    }
}
