// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only

package com.swordcoach;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * The link to the Sword Coach server on this computer (127.0.0.1). JSON lines both ways; all socket
 * work is on background threads so the game thread never waits. If the server is not running the
 * panel says so and the mod keeps retrying every few seconds.
 */
final class Sidecar {
    /** Set from the config before the first tick. */
    int port = 47310;

    final ConcurrentLinkedQueue<JsonObject> inbox = new ConcurrentLinkedQueue<>();
    private final LinkedBlockingQueue<String> outbox = new LinkedBlockingQueue<>(20000);
    private volatile boolean connected, connecting;
    private volatile Socket socket;
    private long nextTry;

    boolean connected() {
        return connected;
    }

    /** Called every client tick: (re)connect in the background when needed. */
    void tick() {
        if (connected || connecting) return;
        long now = System.currentTimeMillis();
        if (now < nextTry) return;
        nextTry = now + 3000;
        connecting = true;
        Thread t = new Thread(this::connect, "swordcoach-connect");
        t.setDaemon(true);
        t.start();
    }

    void send(JsonObject o) {
        if (connected) outbox.offer(o.toString());
    }

    private void connect() {
        try {
            Socket s = new Socket();
            s.connect(new InetSocketAddress("127.0.0.1", port), 300);
            s.setTcpNoDelay(true);
            socket = s;
            outbox.clear();
            connected = true;
            BufferedWriter w = new BufferedWriter(new OutputStreamWriter(s.getOutputStream(), StandardCharsets.UTF_8));
            Thread writer = new Thread(() -> {
                try {
                    while (connected) {
                        String line = outbox.take();
                        w.write(line);
                        w.write('\n');
                        if (outbox.isEmpty()) w.flush();
                    }
                } catch (Exception e) {
                    close();
                }
            }, "swordcoach-writer");
            writer.setDaemon(true);
            writer.start();
            Thread reader = new Thread(() -> {
                try (BufferedReader r = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = r.readLine()) != null) {
                        try {
                            inbox.add(JsonParser.parseString(line).getAsJsonObject());
                        } catch (RuntimeException ignored) {
                            // a malformed line is dropped, not fatal
                        }
                    }
                } catch (Exception ignored) {
                    // connection gone
                }
                close();
            }, "swordcoach-reader");
            reader.setDaemon(true);
            reader.start();
        } catch (Exception e) {
            connected = false;
        } finally {
            connecting = false;
        }
    }

    private void close() {
        connected = false;
        try {
            Socket s = socket;
            if (s != null) s.close();
        } catch (Exception ignored) {
            // already closed
        }
        outbox.offer("");   // wake the writer so it can exit
    }
}
