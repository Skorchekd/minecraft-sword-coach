// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach.mixin;

import com.swordcoach.SafeText;
import net.minecraft.client.gui.screens.inventory.AnvilScreen;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * The anvil fills its rename box from the item's name and sends the name back. Read the name as a
 * client without this mod would (SafeText), so a server cannot read this mod's names.
 */
@Mixin(AnvilScreen.class)
public abstract class AnvilNameMixin {
    @Redirect(method = {"slotChanged", "onNameChanged"},
            at = @At(value = "INVOKE", target = "Lnet/minecraft/network/chat/Component;getString()Ljava/lang/String;"))
    private String swordcoach$plainName(Component name) {
        return SafeText.string(name);
    }
}
