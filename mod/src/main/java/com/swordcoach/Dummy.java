// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.mojang.authlib.GameProfile;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.RemotePlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.util.UUID;

/**
 * A client-only player model the coach poses for replays: real Minecraft player rendering
 * (skin, diamond kit, sword, walk and swing animation, hurt flash), outlined in its role's
 * colour and labelled. It exists only in this client's world; no packet is ever sent for it. It
 * cannot be targeted (your crosshair passes through it), so clicking during a replay never sends
 * an attack or use for an entity the server does not have.
 */
public final class Dummy extends RemotePlayer {
    private static int nextId = -0x5_0000;

    private final int glow;
    private Component label;
    /** Not drawn: the replay's eye camera is inside it. */
    boolean hidden;

    Dummy(ClientLevel level, GameProfile profile, String label, int glow) {
        super(level, profile);
        this.glow = glow;
        this.label = Component.literal(label);
        setId(nextId--);
        setItemSlot(EquipmentSlot.HEAD, new ItemStack(Items.DIAMOND_HELMET));
        setItemSlot(EquipmentSlot.CHEST, new ItemStack(Items.DIAMOND_CHESTPLATE));
        setItemSlot(EquipmentSlot.LEGS, new ItemStack(Items.DIAMOND_LEGGINGS));
        setItemSlot(EquipmentSlot.FEET, new ItemStack(Items.DIAMOND_BOOTS));
        setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Items.DIAMOND_SWORD));
        noPhysics = true;
    }

    static GameProfile profile(String name) {
        return new GameProfile(UUID.nameUUIDFromBytes(("swordcoach:" + name).getBytes()), name);
    }

    /** One replay tick: move to (x, y, z, yaw), optionally swing and flash hurt. */
    void pose(double x, double y, double z, float yaw, boolean swing, boolean hurt) {
        pose(x, y, z, yaw, 8.0f, swing, hurt);
    }

    /** The same with a pitch: the replay's eye cameras look where this dummy looks. */
    void pose(double x, double y, double z, float yaw, float pitch, boolean swing, boolean hurt) {
        setOldPosAndRot();
        yBodyRotO = yBodyRot;
        yHeadRotO = yHeadRot;
        setPos(x, y, z);
        setYRot(yaw);
        setXRot(pitch);
        setYHeadRot(yaw);
        setYBodyRot(yaw);
        calculateEntityAnimation(false);
        if (swing) swing(InteractionHand.MAIN_HAND);
        updateSwingTime();
        if (hurt) {
            hurtTime = 10;
            hurtDuration = 10;
        } else if (hurtTime > 0) {
            hurtTime--;
        }
        tickCount++;
    }

    @Override
    public void tick() {
        // Posed by the replay; it has no movement of its own.
    }

    @Override
    public void aiStep() {
    }

    @Override
    public boolean isCurrentlyGlowing() {
        return glow != 0;
    }

    @Override
    public int getTeamColor() {
        return glow != 0 ? glow : super.getTeamColor();
    }

    @Override
    public Component getDisplayName() {
        return label;
    }

    @Override
    public boolean shouldShowName() {
        return true;
    }

    /**
     * One replay step from a recorded state: position, head and body yaw, pitch, hurt time, swing
     * progress, crouch. `snap` jumps there (a cut, a seek) instead of moving there over the frame.
     */
    void apply(double x, double y, double z, float head, float body, float pitch, int hurt, float anim, boolean swing,
               boolean crouch, boolean snap) {
        if (!snap) {
            setOldPosAndRot();
            yBodyRotO = yBodyRot;
            yHeadRotO = yHeadRot;
            oAttackAnim = attackAnim;
        }
        setPos(x, y, z);
        setYRot(head);
        setXRot(pitch);
        setYHeadRot(head);
        setYBodyRot(body);
        if (snap) {
            setOldPosAndRot();
            yBodyRotO = yBodyRot;
            yHeadRotO = yHeadRot;
            oAttackAnim = anim;
        }
        attackAnim = anim;
        swinging = swing;
        hurtTime = hurt;
        hurtDuration = 10;
        Pose want = crouch ? Pose.CROUCHING : Pose.STANDING;
        if (getPose() != want) setPose(want);
        calculateEntityAnimation(false);
        tickCount++;
    }

    @Override
    public boolean isPickable() {
        return false;
    }

    @Override
    public boolean isAttackable() {
        return false;
    }

    @Override
    public boolean shouldRender(double x, double y, double z) {
        return !hidden && super.shouldRender(x, y, z);
    }

    void setLabel(String s) {
        label = Component.literal(s);
    }

    void remove() {
        if (level() instanceof ClientLevel cl) cl.removeEntity(getId(), Entity.RemovalReason.DISCARDED);
    }
}
