// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach.mixin;

import com.swordcoach.Dummy;
import com.swordcoach.ReplayCamera;
import net.minecraft.client.Camera;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Render-only: during a replay's eye camera, the view is drawn from the dummy's eyes. */
@Mixin(Camera.class)
public abstract class CameraMixin {
    @Shadow
    private boolean detached;

    @Shadow
    protected abstract void setRotation(float yRot, float xRot);

    @Shadow
    protected abstract void setPosition(Vec3 pos);

    @Shadow
    protected abstract void move(float forwards, float up, float left);

    @Inject(method = "alignWithEntity", at = @At("TAIL"))
    private void swordcoach$replayEyes(float partialTick, CallbackInfo ci) {
        Dummy e = ReplayCamera.eye;
        if (e == null || e.isRemoved()) return;
        setRotation(e.getViewYRot(partialTick), e.getViewXRot(partialTick));
        setPosition(e.getEyePosition(partialTick));
        if (detached) move(-4.0f, 0.0f, 0.0f);       // F5: over the dummy's shoulder
    }
}
