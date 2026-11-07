// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach.mixin;

import com.swordcoach.Knockback;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Read-only: notes the velocity the server sets on an entity (knockback). The handler first hops from
 * the network thread to the game thread, so TAIL only runs on the game thread.
 */
@Mixin(ClientPacketListener.class)
public abstract class MotionMixin {
    @Inject(method = "handleSetEntityMotion", at = @At("TAIL"))
    private void swordcoach$motion(ClientboundSetEntityMotionPacket packet, CallbackInfo ci) {
        Knockback.seen(packet.id(), packet.movement());
    }
}
