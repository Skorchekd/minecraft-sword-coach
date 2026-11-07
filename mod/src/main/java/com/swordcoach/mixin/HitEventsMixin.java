// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach.mixin;

import com.swordcoach.HitEvents;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.ClientboundAnimatePacket;
import net.minecraft.network.protocol.game.ClientboundSoundPacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Read-only: notes the attack sounds and crit particles the server sends, so a replay can play them back. Both
 * handlers first hop from the network thread to the game thread, so TAIL only runs on the game thread, after the game
 * has played the sound / spawned the particles as normal.
 */
@Mixin(ClientPacketListener.class)
public abstract class HitEventsMixin {
    @Inject(method = "handleAnimate", at = @At("TAIL"))
    private void swordcoach$animate(ClientboundAnimatePacket packet, CallbackInfo ci) {
        HitEvents.animate(packet.getId(), packet.getAction());
    }

    @Inject(method = "handleSoundEvent", at = @At("TAIL"))
    private void swordcoach$sound(ClientboundSoundPacket packet, CallbackInfo ci) {
        HitEvents.sound(packet.getSound(), packet.getX(), packet.getY(), packet.getZ());
    }
}
