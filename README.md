# Sword Coach

**[Website](https://minecraftcombatai.com/sword-coach.html) · [Discord](https://discord.gg/CqFT4vXD8J) · [Support us: get R1 Local](https://minecraftcombatai.com/r1.html)**

> **Running a server?** We offer the model server side, to analyse your players, auto tier test them, show them how to improve, and more, for sword and other gamemodes too. For that, a commercial licence and a superior model, [contact us on Discord](https://discord.gg/CqFT4vXD8J). Other gamemode inquiries and AI requests are welcome there too.

A Minecraft (26.1.2, Fabric) sword PvP coach that runs entirely on your computer:

- **the mod** watches your sword fights from your own client and streams them to
- **the Sword Coach server** on your PC, which reads which technique each of you used in every exchange (0.6 s),
  saves the fight, and serves a **review page** in your browser: how each fight flowed (with every hit, crit and hit
  sound), the moments that went worse than they usually do, your answers to each of their moves, a skill tree of the 44
  techniques, a matchup grid, and a guide to what every word and technique means.
- Overlapping techniques can both be read and both be labelled ("Also"). Exchanges showing the same technique join into one move, and a move is counted once.

Nothing is sent anywhere. Both the mod and the server only talk to `127.0.0.1` (your own computer), and the review page
works offline. Sharing your fights is a separate, manual step (see below).

Sword Coach is made by **MCA - Minecraft Combat AI**. See what else we have built at
[minecraftcombatai.com](https://minecraftcombatai.com/).

## Setup (Windows)

0. **Get the files**: on GitHub press **Code → Download ZIP** and unzip it anywhere (or
   `git clone https://github.com/Skorchekd/minecraft-sword-coach`).
1. **Launch AI Server.bat**: the first run installs what it needs (Python 3.12 with winget if you have no Python, then
   a private environment in `server\.venv`), then starts the server and opens the review page
   (http://127.0.0.1:47320/). Leave its window open while you play; close it to stop.
2. **Build The Mod.bat**: builds the mod (installs a Java 25 JDK with winget if needed) and puts the `swordcoach-*.jar`
   next to the batch file. Put it in your Minecraft `mods` folder together with [Fabric API](https://modrinth.com/mod/fabric-api).
   Updating: take the old `swordcoach-*.jar` out of `mods` first (two copies stop the game from starting).
3. Start Minecraft. The panel in the top left says **live** once the mod has found the server.

## In game

| Key | What it does |
|---|---|
| J | Show or hide the panel (during a fight it only says it is recording, unless `live_reads` is on) |
| H | Replay your last fight with two dummies (client-only) |
| K | Jump straight to the moments that went worse than expected |
| Y | Your saved fights: pick any of them to replay in game |
| U | Record mode on/off: declare the technique you are practising |
| [ and ] | Record mode: previous / next technique |
| During a replay | ← → previous/next point, `,` `.` one tick, ↑ ↓ speed, B pause, V camera (your view / your eyes / their eyes) |

Replays sound like the fight did: every hit plays its attack sound (crit, knockback, strong, weak, sweep, no damage) at
the attacker and the hurt sound at the one hit, crits throw crit particles, and the player who crit gets a **✦ CRIT**
tag. These come from the sounds and crit particles the server sent during the fight. Fights saved before version 1.1.0
have none recorded, so there they are worked out from how each hit landed and the tag says **CRIT?**. The replay card
also shows each exchange's hits (landed of swings, crits) and your labels. Turn the sounds off with `replay_sounds`.

A fight starts when another player in a sword kit is within 6 blocks and ends when someone dies, when the server resets
the loser's health at the end of a round, or when the opponent is gone for 3 seconds.

## The review page

The bar at the top says whether your game is connected. A new fight appears as soon as it is saved. Hover a dotted word
for what it means, or open the **Guide** tab.

- **Fights**: every saved fight, with a small preview of who was ahead on health. Filter by won, lost or labelled. A fight
  opens with the result, both players' health through the fight (click to jump there) and the flow chart, which shows
  both players' technique family per exchange, so switches show as branches. The square on the middle line says how the
  exchange went compared with what real exchanges from the same spot usually trade (↑ better, = about the same, ↓ worse);
  ✦ marks an exchange where that side landed a crit. Click an exchange to watch it in 3D with both players' health, their
  reach, each swing and each hit, and see both reads and what each of you landed. The ← and → keys step through, Space
  plays or pauses. The clip plays the hit and hurt sounds of your own game (with your resource pack; the mod hands them
  to the server) and pops **CRIT**, **HIT** or **NO DMG** over whoever was hit.
- **Won back**: a lost trade is judged over 1.2 s, so if you came out ahead over the next 6 s, the page and the replay say so: it may have been worth it.
- **Other answers (experimental)**: when one answer usually goes clearly better than yours, the exchange and the in-game replay name it. The **Other answers** tab of an exchange shows how other answers to the opponent's previous technique usually
  went from spots like this one against real players (a small model; hover a row for how common that answer is). It
  was learned mostly from bot-played fights and checked on fights it never saw; the effect is small, so treat it as a
  hint, not a verdict.
- **Label this**: if the reads are right, press **✓ Both reads are right**. If one is wrong, open the **Label this** tab and
  set what really happened; the form shows what counts as the technique you picked. Only label what you are sure of:
  anything you leave is fine and never counted as wrong. For each side you can also say how it was executed
  (**Poor / Decent / Excellent**) and what went wrong (**Missed hit**, **Too close**, **Too far**, **Mistimed**; any number),
  so a botched hit select is "Hit select, poor, missed hit" instead of just "Hit select". Shift-click a second exchange to
  label a range. Your labels are saved separately (`data\labels`) and used everywhere on the page and in game replays.
- **Answers**: first, **your answers by distance**: pick one of their techniques and see how each of your answers in
  the next exchange went at each distance (close, at reach, just out of reach, apart), with how many times; a column
  names a best answer only once one is clearly ahead. Below it, the map of how your engagements go, starting with whoever
  landed the first hit (or swung first if nobody landed one): what they did, how the other answered, what they did next.
- **Skill tree**: starts with **Where you stand**: which techniques are working for you, costing you, making no clear
  difference, or are too new to tell, with a distance filter. Below, the 44 techniques from entry to high level; click
  one for what it is and its numbers at each distance. Dashed techniques are ones the reader cannot name yet: they count
  once you label them. Your style over all your fights is at the bottom.
- **Matchups**: your technique against theirs, across all your fights, at any distance or one distance band.
- **Your data**: how to help the next model, your tier and settings, the unlabelled exchanges the reader was least sure
  about (the most useful ones to label), and your labels per technique so far.
- **Guide**: the first steps, the keys, what the words mean, and what counts as each of the 44 techniques. Label by these
  meanings, so labels from different players mean the same thing.

## Sharing your fights

Run **Bundle Fight Data.bat** (after the server has been set up once). It checks that every fight reads back, then packs
`data\fights`, `data\labels` and a `manifest.json` (versions, your tier if you set it on the Your data tab, an install
id so bundles from the same PC can be put together, totals, labels per technique, anything it had to leave out) into
`fightdata-<date>.zip` next to the batch file. Fights are stored compactly (about 25 KB each) and losslessly.

To help the next model, send the zip to MCA on the [official Discord](https://discord.gg/CqFT4vXD8J). Sending one means
you agree that MCA can keep it and use it to train and test future models. Notes you write on labels go in the bundle too,
so keep names and personal details out of them.

What the data teaches: **labels** teach the technique reader what to name, on you and on your opponents. **Fights** teach
everything else (what usually happens from a position, other answers, the health guess, the copilot), so sending fights
helps even if you label nothing. Execution ratings and "what went wrong" are for your own review; the models do not use
them yet.

## What gets recorded

Per game tick during a fight: your position, look, ground/sprint state, health, attack charge and swing, and your keys
(forward, back, left, right, jump, sneak, sprint, attack click); the opponent as your client sees them (position, look,
ground/sprint/sneak, health, swing); both pings; both players as your client drew them (for the 3D replays); the
velocities the server sets on each of you (knockback), exactly as the packets carry them; and the attack sounds and
crit particles the server sends for your hits and theirs. Names are not saved: each
player gets a code made with a key that only exists on your computer (`server\.install_key`, never shared), so fights
against the same player can be grouped without anyone being able to get the name back. The server name (e.g.
`mcpvp.club`) is saved, unless you joined by a raw IP address, which is saved only as "ip address"; so is where the opponent's health came from (their real value or a number the server drew
over them). A relabel also keeps what the readers said before you corrected them.

## Files

```
Launch AI Server.bat    start the server (installs on first run)
Build The Mod.bat       build the mod jar
Bundle Fight Data.bat   zip your fights to share
server/                 the server (Python), its models and the review page
mod/                    the Fabric mod (Java)
data/                   your saved fights, labels and your game's hit sounds (created on first use; not part of the
                        repository; the sounds are never bundled)
```

The mod's settings are in `config/swordcoach.json` in your Minecraft folder (which players count as a fight, servers
that hide real health, the server port, `live_reads`: off by default, so during a fight the panel only says
"Recording this fight"; turn it on to see the distance and both reads live, and `replay_sounds`: on by default).

## License

Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx, the holders of MCA, together trading as
MCA - Minecraft Combat AI (https://minecraftcombatai.com/).

- **The code** (mod, server, review page, batch files) is free software under the
  [GNU General Public License v3](LICENSE) (`GPL-3.0-only`): you may use, study, change and share it; shared changes
  must stay under the GPL v3 and keep the copyright notices.
- **The model files** in `server/models/` are not covered by the GPL. They are licensed under the
  [MCA Sword Coach Model Licence](server/models/LICENSE): personal, non-commercial use with Sword Coach; no separate
  redistribution, extraction or training of other models from them.

Details and third-party notices: [COPYRIGHT.md](COPYRIGHT.md).

## Fight copilot (experimental)

Press **G** in game to turn it on (it is off by default). It draws in your client only, in purple: where your opponent is looking (a cone on the ground), their reach (a ring around them), and a crosshair ring that fills with your charge, brightens in reach and pulses when you are on them, in reach and charged. It never touches your keys or look and sends nothing to the Minecraft server.

Under the crosshair it shows the move your opponent made ("vs W-tap x3": x3 is the third separate time this fight), then the move you answered it with: **green** when it was the right one, **red** when it was not, followed by `->` and the counter to use instead in **gold**, with a few words on how ("jump as their hit lands"). Each exchange is read 0.6 s after it ends, because the reader also looks at what follows a move: read at once it agreed with the whole-fight read 77% of the time, 0.6 s later 93%, as right as reading the whole fight. Counters name only moves you can make mid-fight (sprint hits, W-taps, S-taps, jump resets, strafing, spacing, baiting, backing off, running or jumping in), only when the answer model has one clearly ahead of what players usually do from where you stood; your answer counts as right when it is that move, one built on it, or about as good. On real fights the model never saw, players who happened to do the named counter came out about 0.2 HP better over the next 1.2 s than with other answers at the same moments; that was one of several settings tried, so it is a trend, not yet a clear result. You can turn counters off on the Your data tab (then it shows the moves only). A quarter of counters stay off the screen at random, and every one is kept with the fight, so your own fights can show whether seeing them helps.

Beside the crosshair it shows the opponent's health as worked out from your hits ("~12.5 ❤", green above 12, gold to 6, red under). It never reads the health the server shows: where a server draws it (a number under the name) you can check the guess against it; where a server hides it from the mod, the guess is all there is. The estimate is saved with every fight, and in reviews and replays (H, K, Y) both players' health shows as bars, yours exact and theirs as the server showed it or, where it hid it, worked out from your hits (marked ~). A small model learned from fights where health does show how much each hit takes off: the hit's kind (crit, sprint hit, sweep...), your charge, whether they were still invulnerable, and what their hits take off you in the same kit. Tested with the health hidden from it, it was off by 0.6 HP on average on your fights it never saw and 1.2 HP on another server and kit (what a hidden server shows, 20, was off by 8 to 9).

The copilot still works out where to go and keeps it with every fight for the review's notes and stats; it is no longer drawn in game.

One copilot fight in five, at random, shows only the cone, ring and crosshair and says "Copilot quiet this fight", so fights with and without its advice can be compared. Every fight keeps what it said, and the review and replays show it with notes on your style. Check a server's rules before using it there: many ban on-screen help during fights.
