// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach.mixin;

import com.swordcoach.SafeText;
import net.minecraft.client.gui.screens.inventory.AbstractSignEditScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.entity.SignText;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * The sign editor fills its lines from the sign's text and sends them back when it closes. Refill
 * them as a client without this mod would (SafeText), so a server cannot read this mod's names.
 */
@Mixin(AbstractSignEditScreen.class)
public abstract class SignEditMixin {
    @Shadow
    private SignText text;

    @Shadow
    @Final
    private String[] messages;

    @Inject(method = "<init>(Lnet/minecraft/world/level/block/entity/SignBlockEntity;ZZLnet/minecraft/network/chat/Component;)V", at = @At("TAIL"))
    private void swordcoach$plainLines(SignBlockEntity sign, boolean front, boolean filtered, Component title, CallbackInfo ci) {
        for (int i = 0; i < messages.length; i++) messages[i] = SafeText.string(text.getMessage(i, filtered));
    }
}
