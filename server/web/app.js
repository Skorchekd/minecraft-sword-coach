// Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
// SPDX-License-Identifier: GPL-3.0-only
// Sword Coach review page. Everything here comes from your own fights on this computer: the technique reads,
// what really happened, and what an exchange from the same spot usually trades in real fights.
import * as THREE from "./three.module.js";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const NS = "http://www.w3.org/2000/svg";
const sv = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs || {}) e.setAttribute(k, attrs[k]); return e; };
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const hp = (v) => v == null ? "–" : (v > 0 ? "+" : "") + v.toFixed(1);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const api = async (path, opts) => { const r = await fetch(path, opts); if (!r.ok) throw new Error(path + ": " + r.status); return r.json(); };
const postJson = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const S = { status: null, fights: [], fight: null, frames: null, sel: 0, range: null, stats: null, tab: "", band: "all", after: null, pane: "read", filter: "all", load: 0, live: { mod: false, fights: 0 }, thumbs: {} };
try { S.band = localStorage.getItem("swordcoach-band") || "all"; } catch (err) { /* private window: not remembered */ }
const SITE = "https://minecraftcombatai.com/", DISCORD = "https://discord.gg/CqFT4vXD8J";
const CALL = {
  worse: { ic: "↓", word: "Lost this trade", color: "--bad" },
  better: { ic: "↑", word: "Won this trade", color: "--good" },
  as_expected: { ic: "=", word: "About what usually happens", color: "--close" },
};

// The mod's 5x7 display face, one hex byte per row, as on minecraftcombatai.com.
const GLYPHS = { A: "0e11111f111111", B: "1e11111e11111e", C: "0e11101010110e", D: "1e11111111111e", E: "1f10101e10101f", F: "1f10101e101010", G: "0e11101711110e", H: "1111111f111111", I: "0e04040404040e", J: "0702020202120c", K: "11121418141211", L: "1010101010101f", M: "111b1511111111", N: "11191513111111", O: "0e11111111110e", P: "1e11111e101010", Q: "0e11111115120d", R: "1e11111e141211", S: "0f10100e01011e", T: "1f040404040404", U: "1111111111110e", V: "11111111110a04", W: "11111111151b11", X: "11110a040a1111", Y: "11110a04040404", Z: "1f01020408101f", 0: "0e11131519110e", 1: "040c040404040e", 2: "0e11010204081f", 3: "1e01010e01011e", 4: "02060a121f0202", 5: "1f101e0101110e", 6: "0608101e11110e", 7: "1f010204080808", 8: "0e11110e11110e", 9: "0e11110f01020c", "-": "0000000e000000", ".": "00000000000c0c", ":": "000c0c000c0c00", "/": "01010204081010", "!": "04040404040004", "?": "0e110106040004", "+": "0004041f040400" };
function pixelText(text, scale = 2, color = "currentColor") {
  const up = String(text).toUpperCase(), w = Math.max(1, up.length * 6 - 1);
  const svg = sv("svg", { viewBox: `0 0 ${w} 7`, width: w * scale, height: 7 * scale, fill: color, "shape-rendering": "crispEdges", role: "img", "aria-label": text });
  let d = "";
  [...up].forEach((ch, i) => {
    const g = GLYPHS[ch]; if (!g) return;
    for (let y = 0; y < 7; y++) {
      const row = parseInt(g.substr(y * 2, 2), 16);
      for (let x = 0; x < 5; x++) if (row & (16 >> x)) d += `M${i * 6 + x} ${y}h1v1h-1z`;
    }
  });
  svg.append(sv("path", { d }));
  return svg;
}

// The words the page uses, in one place: hover one on the page, or read them all on the Guide tab.
const TERMS = {
  exchange: ["Exchange", "A 0.6 second slice of a fight. Reads and results are worked out for each one."],
  move: ["Move", "One technique from start to finish. Moves run about 2 seconds, so a move can cover several exchanges."],
  trade: ["Trade", "HP you dealt minus HP you took over the next 1.2 seconds."],
  usual: ["Usual", "What exchanges from the same position usually trade in real fights. +0.20 means you came out 0.2 HP better than that."],
  read: ["Read", "What the technique reader thinks a player did, with how sure it is. Reads can be wrong."],
  label: ["Label", "What you say really happened. Your label always beats the read, here and in replays."],
  answer: ["Answer", "The move you make right after theirs."],
  engagement: ["Engagement", "One stretch of fighting. A new one starts when you are more than 4.5 blocks apart."],
};
function term(key, shown) { const s = el("span", "term", shown || TERMS[key][0].toLowerCase()); s.title = TERMS[key][1]; s.tabIndex = 0; return s; }
// "Won {trade|this trade}": text with hoverable words.
function rich(tag, cls, text) {
  const p = el(tag, cls);
  text.split(/(\{[a-z]+\|[^}]*\})/).forEach(part => { const m = part.match(/^\{([a-z]+)\|(.*)\}$/); p.append(m ? term(m[1], m[2]) : part); });
  return p;
}
function how(summary, ...paras) {
  const d = el("details", "how"); d.append(el("summary", null, summary));
  for (const x of paras) d.append(typeof x === "string" ? rich("p", null, x) : x);
  return d;
}
function fold(summary, cls) { const d = el("details", "fold " + (cls || "")), body = el("div", "in"); d.append(el("summary", null, summary), body); return [d, body]; }
function pageHead(title, sub, right) {
  const h = el("div", "pagehead"), t = el("div", "t");
  t.append(pixelText(title, 3)); if (sub) t.append(rich("p", "sub", sub));
  h.append(t); if (right) h.append(right);
  return h;
}

function toast(msg, action) {
  for (const old of document.querySelectorAll(".toast")) old.remove();
  const t = el("div", "toast", msg);
  if (action) { const b = el("button", null, action[0]); b.addEventListener("click", () => { t.remove(); action[1](); }); t.append(b); }
  document.body.append(t); setTimeout(() => t.remove(), action ? 8000 : 2600);
}
const techOf = (id) => S.status && S.status.techniques.find(x => x.id === id);
function techName(id) { const t = techOf(id); return t ? t.name : id; }
function techShort(id) { const t = techOf(id); return t ? t.short : "?"; }
function techDef(id) { const t = techOf(id); return t ? t.definition : ""; }
function chosen(e, side) { return (e.fix && e.fix[side]) || e[side].id; }
// A technique usually takes about 2 s, an exchange 0.6: the move an exchange belongs to, on one side.
function moveOf(e, side) { return S.fight && S.fight.moves && e.move ? S.fight.moves[side][e.move[side]] : null; }
function moveTech(e, side) { const m = moveOf(e, side); return m ? m.tech : chosen(e, side); }
function execOf(e, side) { return (e.fix && e.fix.exec && e.fix.exec[side]) || null; }
function failsOf(e, side) { return (e.fix && e.fix.fail && e.fix.fail[side]) || []; }
function execName(id) { const x = S.status && S.status.execution.find(q => q.id === id); return x ? x.name : id; }
function failName(id) { const x = S.status && S.status.fails.find(q => q.id === id); return x ? x.name : id; }
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
// "1 hit from 3 swings · 1 crit": what the data says each side did in an exchange.
function hitsText(h) {
  if (!h) return "";
  const crit = h.crits ? ` · ${plural(h.crits, "crit")}${S.fight && !S.fight.events_recorded ? "?" : ""}` : "";
  if (!h.landed) return h.swings ? `No hit from ${plural(h.swings, "swing")}` : "No swings";
  return `${plural(h.landed, "hit")} landed${h.swings >= h.landed ? ` from ${plural(h.swings, "swing")}` : ""}${crit}`;
}
function labelText(e, side) {
  const x = execOf(e, side), f = failsOf(e, side);
  return [x ? "executed " + execName(x).toLowerCase() : null, f.length ? f.map(failName).join(", ") : null].filter(Boolean).join(" · ");
}
function fmtDay(s) { const d = new Date(s); return d.toLocaleDateString(undefined, { day: "numeric", month: "short" }); }
function fmtClock(s) { const d = new Date(s); return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }); }
function fmtTime(s) { return s ? fmtDay(s) + ", " + fmtClock(s) : "?"; }

// ---- routing ----------------------------------------------------------------------------------
const TITLES = { fights: "Fights", branches: "Answers", skills: "Skill tree", matchups: "Matchups", data: "Your data", guide: "Guide" };
async function route() {
  const [tab, a, b] = (location.hash.replace(/^#/, "") || "fights").split("/");
  const before = S.tab, token = ++S.load;
  S.tab = TITLES[tab] ? tab : "fights";
  document.title = "Sword Coach · " + TITLES[S.tab];
  for (const x of document.querySelectorAll(".tabs a")) { if (x.dataset.tab === S.tab) x.setAttribute("aria-current", "page"); else x.removeAttribute("aria-current"); }
  const v = $("view");
  if (S.tab === "fights") { if (before !== "fights") v.innerHTML = ""; return showFights(a, b != null ? Number(b) : null, token); }
  v.innerHTML = "";
  if (S.tab === "guide") return showGuide();
  if (!(await loadStats(token)) || token !== S.load) return;
  if (S.tab !== "data" && !S.stats.fights) { const p = el("section", "panel empty"); p.append(el("h2", null, "Nothing to show yet"), el("p", "note", "This page fills up from your fights. Three steps to your first one:"), startList()); v.append(p); return; }
  if (S.tab === "branches") return showBranches();
  if (S.tab === "skills") return showSkills();
  if (S.tab === "matchups") return showMatchups();
  return showData();
}
let statsCall = null;     // one read at a time, however many tabs are clicked while it runs
async function loadStats(token) {
  if (S.stats) return true;
  const v = $("view"), box = el("div", "panel empty"), p = el("div", "progress"), t = el("div", null, "Reading your fights…"), m = el("div", "meter"), f = el("span");
  f.style.width = "0"; m.append(f); p.append(t, m, el("div", "small", "New fights take a moment the first time. After that they are remembered."));
  box.append(p); v.append(box);
  const timer = setInterval(async () => {
    try { const l = await api("/api/live"); if (l.reading.total) { t.textContent = `Reading your fights: ${l.reading.done} of ${l.reading.total}`; f.style.width = (l.reading.done / l.reading.total * 100) + "%"; } } catch (err) { /* the main request reports it */ }
  }, 400);
  try {
    statsCall = statsCall || api("/api/stats").finally(() => { statsCall = null; });
    const got = await statsCall; S.stats = got;
    if (token === S.load) v.innerHTML = "";
    return true;
  }
  catch (e) { if (token === S.load) { v.innerHTML = ""; v.append(el("div", "panel empty", "Could not read your fights: " + e.message)); } return false; }
  finally { clearInterval(timer); }
}

// ---- getting started --------------------------------------------------------------------------
function startList() {
  const ol = el("ol", "startlist");
  const step = (done, n, title, text) => { const li = el("li", done ? "done" : null), b = el("div"); b.append(el("b", null, title), el("span", null, text)); li.append(el("span", "st", done ? "✓" : n), b); ol.append(li); };
  step(true, "1", "The server is running", "This page comes from it. Leave its window open while you play.");
  step(S.live.mod, "2", S.live.mod ? "Minecraft is connected" : "Start Minecraft with the mod", S.live.mod ? "The mod has found the server." : "Build it with Build The Mod.bat, then put it in your mods folder with Fabric API.");
  step(S.status && S.status.fights > 0, "3", "Fight someone with a sword", "A fight starts when another player in a sword kit is within 6 blocks. It shows up here when it ends.");
  return ol;
}

// ---- fights -----------------------------------------------------------------------------------
function resultTag(r) { return r === 1 ? ["w", "W"] : r === 0 ? ["l", "L"] : ["u", "–"]; }
const sparkSeen = new IntersectionObserver((list) => {
  for (const x of list) if (x.isIntersecting) { sparkSeen.unobserve(x.target); loadSpark(x.target); }
}, { rootMargin: "160px" });
async function loadSpark(box) {
  const id = box.dataset.id;
  try { S.thumbs[id] = S.thumbs[id] || await api(`/api/fight/${id}/thumb`); box.append(sparkSvg(S.thumbs[id])); } catch (err) { /* a preview is never worth an error */ }
}
// Who was ahead on health through the fight: bars above the line you, below it them.
function sparkSvg(t) {
  const n = t.you.length, W = 82, H = 28, mid = H / 2, bw = W / n, most = Math.max(5, ...t.you.map((y, i) => Math.abs(y - t.them[i]))), k = (H / 2 - 1) / most;
  const svg = sv("svg", { class: "spark", viewBox: `0 0 ${W} ${H}`, "aria-hidden": "true", "shape-rendering": "crispEdges" });
  svg.append(sv("rect", { x: 0, y: mid - 0.5, width: W, height: 1, fill: css("--line") }));
  t.you.forEach((y, i) => {
    const lead = y - t.them[i], h = Math.max(1, Math.abs(lead) * k);
    svg.append(sv("rect", { x: i * bw, y: lead >= 0 ? mid - h : mid, width: Math.max(1, bw - 1), height: h, fill: css(lead >= 0 ? "--good" : "--bad"), opacity: 0.85 }));
  });
  return svg;
}
function renderRail() {
  const rail = $("rail"), F = S.fights; rail.innerHTML = "";
  const wins = F.filter(f => f.result === 1).length, losses = F.filter(f => f.result === 0).length;
  const top = el("div", "rail-top"), rec = el("div", "record");
  const nums = el("b"); nums.append(el("span", "w", wins + "W"), " ", el("span", "l", losses + "L"));
  rec.append(el("span", "small", plural(F.length, "fight")), nums); top.append(rec);
  const seg = el("div", "seg"); seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Show");
  for (const [id, name] of [["all", "All"], ["won", "Won"], ["lost", "Lost"], ["labelled", "Labelled"]]) {
    const b = el("button", null, name); b.type = "button"; b.setAttribute("aria-pressed", String(S.filter === id));
    b.addEventListener("click", () => { S.filter = id; renderRail(); markCurrent(); }); seg.append(b);
  }
  top.append(seg); rail.append(top);
  const list = el("div", "flist");
  const keep = F.filter(f => S.filter === "all" || (S.filter === "won" && f.result === 1) || (S.filter === "lost" && f.result === 0) || (S.filter === "labelled" && f.relabels));
  for (const f of keep) {
    const b = el("button", "fight"); b.type = "button"; b.dataset.id = f.id;
    const [c, tx] = resultTag(f.result), r = el("span", "res " + c, tx), mid = el("span", "tx");
    r.title = f.result === 1 ? "Won" : f.result === 0 ? "Lost" : "No result";
    mid.append(el("div", "d", fmtTime(f.time)), el("div", "m", `${f.seconds || "?"} s · ${f.server || "?"}${f.relabels ? " · ✎" + f.relabels : ""}`));
    const sp = el("span"); sp.dataset.id = f.id; sp.style.minHeight = "28px"; b.title = "Bars above the line: you were ahead on health. Below: they were.";
    b.append(r, mid, sp);
    b.addEventListener("click", () => { location.hash = "#fights/" + f.id; });
    list.append(b); sparkSeen.observe(sp);
  }
  if (!keep.length) list.append(el("div", "empty small", "None of these yet."));
  rail.append(list);
}
function markCurrent() { const id = S.fight && S.fight.id; for (const b of document.querySelectorAll(".fight")) b.setAttribute("aria-current", String(b.dataset.id === id)); }
async function showFights(id, ex, token) {
  const got = await api("/api/fights"); if (token !== S.load) return;
  const more = got.length !== S.fights.length; S.fights = got;
  const v = $("view");
  if (!S.fights.length) {
    v.innerHTML = ""; const p = el("section", "panel empty"); p.append(pixelText("Welcome", 4), el("p", "note", "Sword Coach reads your sword fights and shows you how they went. Three steps and your first fight lands here."), startList()); v.append(p); return;
  }
  if (!$("rail")) { v.innerHTML = ""; const lay = el("div", "layout"), rail = el("aside", "panel rail"), main = el("div", "main"); rail.id = "rail"; main.id = "main"; lay.append(rail, main); v.append(lay); renderRail(); }
  else if (more) renderRail();
  const fid = id && S.fights.find(f => f.id === id) ? id : S.fights[0].id;
  if (S.fight && S.fight.id === fid && S.frames) { if (ex != null && ex !== S.sel) select(ex); return; }
  for (const b of document.querySelectorAll(".fight")) b.setAttribute("aria-current", String(b.dataset.id === fid));
  $("main").innerHTML = ""; $("main").append(el("div", "panel empty", "Reading the fight…"));
  const [r, fr] = await Promise.all([api("/api/fight/" + fid), api("/api/fight/" + fid + "/frames")]);
  if (token !== S.load) return;
  S.fight = r; S.frames = fr; S.range = null;
  if (r) S.sel = ex != null && ex < r.exchanges.length ? ex : (r.worse.length ? r.worse[0] : 0);
  renderFight();
}

function statTile(n, k, cls, hint) { const t = el("div", "tile " + (cls || "")); t.append(el("div", "n", n), el("div", "k", k)); if (hint) t.title = hint; return t; }
function renderFight() {
  const r = S.fight, main = $("main"); main.innerHTML = "";
  if (!r) { main.append(el("div", "panel empty", "This fight is too short to read.")); return; }
  const s = r.summary, won = r.info.result === 1, lost = r.info.result === 0;
  const top = el("section", "panel hero " + (won ? "won" : lost ? "lost" : ""));
  const head = el("div", "title");
  head.append(pixelText(won ? "You won" : lost ? "You lost" : "Fight", 4, css(won ? "--good" : lost ? "--bad" : "--ink")));
  head.append(el("div", "meta", [fmtTime(r.info.time), r.info.server || "unknown server", `${r.info.seconds || "?"} s`, plural(s.exchanges, "exchange"), r.info.keys ? null : "your keys not recorded", r.health_estimated ? "their health worked out from your hits" : null].filter(Boolean).join(" · ")));
  head.append(rich("p", "say", s.vs_expected == null ? "Too short to compare with real fights."
    : `You clearly won ${s.better} {trade|trades} and clearly lost ${s.worse}. Added up, this fight went ${hp(s.vs_expected)} HP against what is {usual|usual} from the same positions. A move that pays off later can still show as a lost trade.`));
  const tiles = el("div", "tiles");
  tiles.append(statTile(String(s.better), "trades won", "good"), statTile(String(s.worse), "trades lost", "bad"));
  tiles.append(statTile(s.vs_expected == null ? "–" : hp(s.vs_expected), "HP vs usual", s.vs_expected == null ? "" : s.vs_expected >= 0 ? "good" : "bad"));
  top.append(head, tiles);
  const hb = el("div", "healthbox"), key = el("div", "hkey"), l = el("span"), rr = el("span");
  const swatch = (c, t) => { const x = el("span"), i = el("i"); i.style.background = `var(${c})`; x.append(i, t); return x; };
  l.append(swatch("--you", "Your health  "), swatch("--them", r.health_estimated ? "Their health (worked out)" : "Their health")); rr.textContent = "Click to jump there";
  key.append(l, rr); hb.append(key, healthChart()); top.append(hb);
  main.append(top);

  const tree = el("section", "panel");
  const th = el("div", "head"); th.append(el("h2", null, "How the fight flowed"));
  const lg = el("div", "legend");
  const li = (v, t) => { const s2 = el("span"); const i = el("i"); i.style.background = `var(${v})`; s2.append(i, t); lg.append(s2); };
  li("--them", "them"); li("--you", "you"); li("--good", "↑ won the trade"); li("--close", "= about usual"); li("--bad", "↓ lost the trade");
  lg.append(el("span", null, "✦ crit"));
  th.append(lg); tree.append(th);
  const box = el("div", "scroll"); box.id = "treebox"; box.append(drawFlow()); tree.append(box);
  tree.append(how("How to read this", "Each column is one {exchange|exchange} (0.6 s). A bar across several columns is one {move|move}. Their technique family is on top, yours below, and the lines show each of you switching. The dot in the middle says how that {trade|trade} went.", "Click a column to watch it. Shift-click a second column to pick a range to label. The ← and → keys step through, and Space plays or pauses."));
  main.append(tree);

  const mom = el("section", "panel"); mom.id = "moment"; main.append(mom);
  renderMoment();

  if (r.worse.length) {
    const w = el("section", "panel"); w.append(el("h2", null, "Worth rewatching"));
    w.append(el("p", "note", "The trades you clearly lost. If you came out ahead over the next 6 seconds, the exchange says so, and it may have been worth it."));
    const grid = el("div", "worselist");
    for (const k of r.worse) {
      const e = r.exchanges[k], b = el("button"); b.type = "button";
      b.append(el("div", "small", `Exchange ${k + 1} · ${e.dist.toFixed(1)} blocks`));
      b.append(el("div", null, `${techName(chosen(e, "you"))} vs their ${techName(chosen(e, "them"))}`));
      b.append(el("div", "small", `Usually ${hp(e.expected)} HP, you traded ${hp(e.real.trade2)}`));
      b.addEventListener("click", () => { select(k); $("moment").scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" }); });
      grid.append(b);
    }
    w.append(grid); main.append(w);
  }
  const tm = r.timing || {};
  if (Object.keys(tm).length) {
    const p = el("section", "panel"); p.append(el("h2", null, "Your timing this fight"));
    const grid = el("div", "cards");
    const card = (title, val, txt) => { const c2 = el("div", "card stat"); c2.append(el("div", "k", title), el("div", "n", val), el("div", "small", txt)); grid.append(c2); };
    if (tm.swing_delay) card("Swing delay", tm.swing_delay.median + " ticks", tm.swing_delay.text + ` (${tm.swing_delay.n})`);
    if (tm.hits_per_swing) card("Hits per swing", Math.round(tm.hits_per_swing.value * 100) + "%", tm.hits_per_swing.text + ` (${tm.hits_per_swing.n})`);
    if (tm.hit_distance) card("Hit distance", tm.hit_distance.median + " blocks", tm.hit_distance.text);
    if (tm.crit_share) card("Crits", Math.round(tm.crit_share.value * 100) + "%", tm.crit_share.text);
    if (tm.reset_timing) card("Jump resets on time", Math.round(tm.reset_timing.on_tick * 100) + "%", tm.reset_timing.text + ` (${tm.reset_timing.n})`);
    if (tm.s_hold) card("S held", tm.s_hold.median + " ticks", tm.s_hold.text);
    if (tm.w_release) card("W released", tm.w_release.median + " ticks", tm.w_release.text);
    p.append(grid); main.append(p);
  }
  if (r.copilot) main.append(copilotPanel(r.copilot));
  markCurrent();
}

// Both players' health through the fight. One SVG unit is one tick, stretched to the panel, so the lines stay sharp at any width.
function healthChart() {
  const F = S.frames, T = F.hp[0].length, H = 100, m = 5, top = Math.max(20, ...F.hp[0], ...F.hp[1]);
  const y = (v) => m + (1 - Math.max(0, v) / top) * (H - 2 * m), step = Math.max(1, Math.floor(T / 900));
  const svg = sv("svg", { class: "healthchart", id: "healthchart", viewBox: `0 0 ${Math.max(1, T - 1)} ${H}`, preserveAspectRatio: "none", role: "img", "aria-label": "Both players' health through the fight" });
  const E = S.fight.exchanges, lo = S.range ? Math.min(...S.range) : S.sel, hi = S.range ? Math.max(...S.range) : S.sel, a = E[lo].t0, b = E[hi].t0 + 12;
  svg.append(sv("rect", { x: a, y: 0, width: Math.max(1, b - a), height: H, fill: css("--chip-hot") }));
  svg.append(sv("line", { x1: 0, x2: T - 1, y1: y(10), y2: y(10), stroke: css("--hair"), "vector-effect": "non-scaling-stroke", "stroke-dasharray": "3 4" }));
  for (const [side, col] of [[1, "--them"], [0, "--you"]]) {
    let pts = ""; for (let i = 0; i < T; i += step) pts += `${i},${y(F.hp[side][i]).toFixed(1)} `;
    svg.append(sv("polyline", { points: pts + `${T - 1},${y(F.hp[side][T - 1]).toFixed(1)}`, fill: "none", stroke: css(col), "stroke-width": 2, "vector-effect": "non-scaling-stroke", "stroke-linejoin": "round" }));
  }
  svg.addEventListener("click", (ev) => {
    const R = svg.getBoundingClientRect(), tick = (ev.clientX - R.left) / R.width * T;
    let k = E.findIndex(x => tick < x.t0 + 12); if (k < 0) k = E.length - 1;
    select(k);
  });
  return svg;
}
function drawFlow() {
  const E = S.fight.exchanges, fam = S.status.families, gap = 34, L = 132, R0 = 18;
  const rowH = 18, topY = 26, midY = topY + fam.length * rowH + 20, botY = midY + 30;
  const W = Math.max(700, L + R0 + gap * Math.max(1, E.length - 1)), H = botY + fam.length * rowH + 26;
  const svg = sv("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "group", "aria-label": "How the fight flowed" });
  const x = (i) => L + i * gap;
  const yThem = (f) => topY + f * rowH, yYou = (f) => botY + f * rowH;
  fam.forEach((n, f) => {
    for (const [y, col] of [[yThem(f), "--them"], [yYou(f), "--you"]]) {
      svg.append(sv("line", { x1: L - 8, y1: y, x2: W - 8, y2: y, stroke: css("--hair") }));
      const t = sv("text", { x: 10, y: y + 4, fill: css(col), "font-size": 11 }); t.textContent = n; svg.append(t);
    }
  });
  const famOf = (e, side) => { const t = S.fight.techniques.find(q => q.id === moveTech(e, side)); return t ? t.family : 0; };
  for (const [side, yf, col] of [["them", yThem, "--them"], ["you", yYou, "--you"]]) {
    let d = "";
    E.forEach((e, i) => { const y = yf(famOf(e, side)); if (i === 0) d = `M${x(i)},${y}`; else { const px2 = x(i - 1), py = yf(famOf(E[i - 1], side)); d += ` C${px2 + gap / 2},${py} ${x(i) - gap / 2},${y} ${x(i)},${y}`; } });
    svg.append(sv("path", { d, fill: "none", stroke: css(col), "stroke-width": 2, opacity: 0.5 }));
  }
  svg.append(sv("line", { x1: L, y1: midY, x2: x(E.length - 1), y2: midY, stroke: css("--line"), "stroke-width": 2 }));
  const lo = S.range ? Math.min(...S.range) : S.sel, hi = S.range ? Math.max(...S.range) : S.sel;
  // One move across several exchanges is drawn as one bar.
  for (const [side, yf, col] of [["them", yThem, "--them"], ["you", yYou, "--you"]]) {
    for (const m of (S.fight.moves ? S.fight.moves[side] : [])) {
      if (m.last > m.first) svg.append(sv("rect", { x: x(m.first) - 13, y: yf(famOf(E[m.first], side)) - 7, width: x(m.last) - x(m.first) + 26, height: 14, fill: css(col) }));
    }
  }
  E.forEach((e, i) => {
    const g = sv("g", { tabindex: 0, role: "button", style: "cursor:pointer", "aria-label": `Exchange ${i + 1}: you ${techName(chosen(e, "you"))}, they ${techName(chosen(e, "them"))}` });
    const lt = (side) => { const t = labelText(e, side); return t ? ` (${t})` : ""; };
    const tt = sv("title"); tt.textContent = `#${i + 1}  you ${techName(chosen(e, "you"))}${lt("you")} · they ${techName(chosen(e, "them"))}${lt("them")} · ${e.vs == null ? "no estimate" : hp(e.vs) + " HP vs usual"}${e.fix ? " · labelled" : ""}`; g.append(tt);
    if (i >= lo && i <= hi) g.append(sv("rect", { x: x(i) - gap / 2 + 1, y: 4, width: gap - 2, height: H - 8, fill: css("--chip-hot") }));
    else g.append(sv("rect", { x: x(i) - gap / 2 + 1, y: 4, width: gap - 2, height: H - 8, fill: "transparent" }));
    for (const [side, yf, col] of [["them", yThem, "--them"], ["you", yYou, "--you"]]) {
      const y = yf(famOf(e, side));
      g.append(sv("rect", { x: x(i) - 13, y: y - 7, width: 26, height: 14, fill: css(col) }));
      const t = sv("text", { x: x(i), y: y + 3.5, "text-anchor": "middle", fill: css("--on-accent"), "font-size": 9.5, "font-weight": 700 }); const mm = moveOf(e, side); t.textContent = !mm || i === mm.first ? techShort(moveTech(e, side)) : ""; g.append(t);
      if (e.hits && e.hits[side].crits) { const st = sv("text", { x: x(i) + 13, y: y - 2, "text-anchor": "middle", fill: css("--close"), stroke: css("--well"), "stroke-width": 3, "paint-order": "stroke", "font-size": 14, "font-weight": 700 }); st.textContent = "✦"; g.append(st); }
    }
    const c = e.call ? css(CALL[e.call].color) : css("--unsure"), sz = e.call ? 9 : 4;
    g.append(sv("rect", { x: x(i) - sz, y: midY - sz, width: 2 * sz, height: 2 * sz, fill: c }));
    if (e.call) { const ic = sv("text", { x: x(i), y: midY + 4, "text-anchor": "middle", fill: css("--on-accent"), "font-size": 12, "font-weight": 700 }); ic.textContent = CALL[e.call].ic; g.append(ic); }
    if (e.fix) { const p = sv("text", { x: x(i) + 9, y: midY - 10, fill: css("--ink"), "font-size": 10 }); p.textContent = "✎"; g.append(p); }
    if (e.declared) g.append(sv("rect", { x: x(i) - 2, y: midY + 13, width: 4, height: 4, fill: css("--ink") }));
    if (i === S.sel) g.append(sv("rect", { x: x(i) - 12, y: midY - 12, width: 24, height: 24, fill: "none", stroke: css("--ink"), "stroke-width": 1.5 }));
    const n = sv("text", { x: x(i), y: H - 6, "text-anchor": "middle", fill: css("--dim"), "font-size": 9.5 }); n.textContent = String(i + 1); g.append(n);
    g.addEventListener("click", (ev) => { if (ev.shiftKey) { S.range = [S.sel, i]; S.pane = "label"; redrawTree(); renderMoment(); } else select(i); });
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter") select(i); });
    svg.append(g);
  });
  return svg;
}
function redrawTree() {
  const b = $("treebox"); if (b) { const sl = b.scrollLeft; b.innerHTML = ""; b.append(drawFlow()); b.scrollLeft = sl; }
  const h = $("healthchart"); if (h) h.replaceWith(healthChart());
}
function select(i) {
  S.sel = Math.max(0, Math.min(S.fight.exchanges.length - 1, i)); S.range = null;
  history.replaceState(null, "", `#fights/${S.fight.id}/${S.sel}`);
  redrawTree(); renderMoment();
  const b = $("treebox"); if (b) b.scrollLeft = Math.max(0, 132 + S.sel * 34 - b.clientWidth / 2);
}

function renderMoment() {
  const r = S.fight, e = r.exchanges[S.sel], box = $("moment"); if (!box) return; box.innerHTML = "";
  const h = el("div", "momenthead"), t = el("div");
  t.append(el("h2", null, S.range ? `Exchanges ${Math.min(...S.range) + 1} to ${Math.max(...S.range) + 1}` : `Exchange ${e.ex + 1} of ${r.exchanges.length}`));
  t.append(el("div", "small", `${e.dist.toFixed(2)} blocks apart · health ${e.hp.you} vs ${r.health_estimated ? "about " : ""}${e.hp.them}`));
  const st = el("div", "stepper"), prev = el("button", "btn", "←"), next = el("button", "btn", "→");
  prev.type = next.type = "button"; prev.title = "Previous exchange"; next.title = "Next exchange"; prev.setAttribute("aria-label", prev.title); next.setAttribute("aria-label", next.title);
  prev.disabled = S.sel === 0; next.disabled = S.sel === r.exchanges.length - 1;
  prev.addEventListener("click", () => select(S.sel - 1)); next.addEventListener("click", () => select(S.sel + 1));
  st.append(prev, next); h.append(t, st); box.append(h);
  const cols = el("div", "cols"), left = el("div", "clipcol"), right = el("div", "sidecol");
  left.append(Clip.mount());
  const tabs = el("div", "panes"); tabs.setAttribute("role", "tablist");
  if (S.pane === "answers" && !e.answers) S.pane = "read";
  const body = el("div", "sidecol"); body.id = "sidepane";
  const panes = [["read", "What happened"], ...(e.answers ? [["answers", "Other answers"]] : []), ["label", "Label this"]];
  for (const [id, name] of panes) {
    const b = el("button", null, name); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(S.pane === id));
    if (id === "label" && e.fix) { const d = el("span", "dot"); d.title = "You labelled this one"; b.append(d); }
    b.addEventListener("click", () => { S.pane = id; for (const x of tabs.children) x.setAttribute("aria-selected", String(x === b)); fillPane(e, body); });
    tabs.append(b);
  }
  right.append(tabs, body); cols.append(left, right); box.append(cols);
  fillPane(e, body);
  Clip.show(e);
}
function fillPane(e, body) {
  body.innerHTML = "";
  if (S.pane === "answers") return body.append(answersCard(e));
  if (S.pane === "label") return body.append(relabelForm(e));
  const who = el("div", "who");
  for (const [side, cls, k] of [["you", "card y", "You"], ["them", "card o", "Them"]]) {
    const c = el("div", cls), rd = e[side], fx = e.fix && e.fix[side], mv = moveOf(e, side);
    const unconfirmed = id => (S.status.unconfirmed || []).includes(id);
    c.append(el("div", "k", k + (fx ? (fx === rd.id ? " · checked by you" : " · your label") : (moveTech(e, side) === rd.id ? ` · ${Math.round(rd.p * 100)}% sure` : " · over the whole move"))));
    const v = el("div", "v", techName(moveTech(e, side))); v.title = techDef(moveTech(e, side)); c.append(v);
    if (!fx && unconfirmed(moveTech(e, side))) c.append(el("div", "small", "Not confirmed by players' labels yet"));
    if (mv && mv.last > mv.first) c.append(el("div", "small", `One move, ${mv.seconds} s: exchanges ${mv.first + 1} to ${mv.last + 1}`));
    if (fx && fx !== rd.id) c.append(el("div", "small", `Read as ${rd.name} (${Math.round(rd.p * 100)}%)`));
    else if (rd.alt.length) c.append(el("div", "small", "Or " + rd.alt.map(a => `${a.name} ${Math.round(a.p * 100)}%`).join(", ")));
    // What else this exchange shows, never the move's own name again; if the move goes by another name than this exchange's read, that read is listed too.
    const shownId = moveTech(e, side);
    const also = fx ? (e.fix[side + "2"] && e.fix[side + "2"] !== shownId ? [techName(e.fix[side + "2"])] : []) : [rd, ...(rd.also || [])].filter(a => a.id !== shownId).map(a => `${a.name} ${Math.round(a.p * 100)}%` + (unconfirmed(a.id) ? " (unconfirmed)" : ""));
    if (also.length) c.append(el("div", "small also", "Also " + also.join(", ")));
    if (e.hits) c.append(el("div", "small hits", hitsText(e.hits[side])));
    const lt = labelText(e, side); if (lt) c.append(el("div", "small lab", lt[0].toUpperCase() + lt.slice(1)));
    if (side === "you" && e.declared) c.append(el("div", "small", "Declared in record mode: " + techName(e.declared)));
    who.append(c);
  }
  body.append(who);
  const oc = el("div", "outcome " + (e.call || ""));
  oc.append(el("div", "ic", e.call ? CALL[e.call].ic : "·"));
  const ot = el("div");
  ot.append(el("div", "big", e.call ? CALL[e.call].word : "No estimate (too close to the end)"));
  ot.append(el("div", "small", `Over the next 1.2 s you came out ${hp(e.real.trade2)} HP.` + (e.expected != null ? ` From this position it is usually ${hp(e.expected)}.` : "")));
  if (e.call === "worse" && e.later > 0) ot.append(el("div", "small", `But you came out ${hp(e.later)} HP over the next 6 s, so it may have been worth it.`));
  oc.append(ot); body.append(oc);
  if (e.suggest) { const c = el("div", "card answers"); c.append(el("div", "k", "Usually went better here"), el("div", "v", e.suggest.name)); body.append(c); }
  if (e.copilot) body.append(copilotCard(e.copilot));
  if (e.counter) body.append(counterCard(e.counter));
  if (!e.fix && !S.range) {
    const q = el("div", "quick"), go = el("div", "controls"), yes = el("button", "btn", "✓ Both reads are right"), no = el("button", "btn ghost", "Fix a read");
    yes.type = no.type = "button"; yes.title = "Saves a label for both sides. A quick check like this helps the next reader.";
    yes.addEventListener("click", () => saveLabels({ [S.sel]: { you: e.you.id, them: e.them.id } }));
    no.addEventListener("click", () => { S.pane = "label"; renderMoment(); });
    go.append(yes, no); q.append(el("span", "small", "Do these reads look right?"), go); body.append(q);
  }
}

const MOVE_WORDS = { toward: "Go in", away: "Back off", left: "Strafe left", right: "Strafe right", hold: "Stop moving forward" };

// What the copilot said at this moment, and what you did a moment later.
function copilotCard(h) {
  const c = el("div", "card copilot");
  c.append(el("div", "k", "Copilot · experimental"));
  c.append(el("div", "copilot-say", MOVE_WORDS[h.move] + (h.click ? " · click" : "") + (h.cue && h.cue !== "Too close" && h.cue !== "Wait for them" ? " · " + h.cue : "")));
  if (h.did) c.append(el("div", "small", h.did === h.move ? "You did this." : `You: ${MOVE_WORDS[h.did].toLowerCase()}.`));
  return c;
}

// What the copilot showed during the fight for this exchange: their move before it, your answer in it marked right or wrong, and the counter.
// (Fights from server 1.6.0 have their move only, read on its own exchange.)
function counterCard(h) {
  const c = el("div", "card copilot");
  c.append(el("div", "k", "Copilot, live · experimental"));
  if (!h.after) {
    c.append(el("div", "copilot-say", `Read during the fight: ${h.them}` + (h.p != null ? ` · ${Math.round(h.p * 100)}% sure` : "")));
    if (h.counter) c.append(el("div", "small", `Counter it showed next: ${h.counter}` + (h.how ? ` (${h.how})` : "")));
    else if (h.kept_off) c.append(el("div", "small", "A counter was worked out and kept off the screen, at random, so shown and not shown can be compared."));
    return c;
  }
  c.append(el("div", "small", `After their ${h.them}` + (h.p != null ? ` (${Math.round(h.p * 100)}% sure)` : "")));
  const say = el("div", "copilot-say");
  if (h.you) say.append(el("span", h.verdict === "right" ? "verdict-right" : h.verdict === "wrong" ? "verdict-wrong" : null, `You: ${h.you}`));
  if (h.counter && h.verdict !== "right") say.append(el("span", "verdict-counter", ` → ${h.counter}`));
  c.append(say);
  if (h.counter && h.verdict !== "right" && h.how) c.append(el("div", "small", h.how));
  if (h.kept_off) c.append(el("div", "small", "Kept off the screen at random, so shown and not shown can be compared."));
  return c;
}

function noteCards(list, into) { for (const n of list) { const c = el("div", "card note-row"); c.append(el("div", null, n.text), el("div", "small", n.value)); into.append(c); } }
function copilotPanel(cp) {
  const [d, p] = fold("Copilot notes", "copilot");
  if (cp.held_back) p.append(el("p", "note", "This was one of the fights where the copilot stayed quiet, at random, so fights with and without it can be compared. These notes are what it would have said."));
  else if (cp.on) p.append(el("p", "note", "The copilot was on for this fight."));
  if (cp.said) p.append(el("p", "note", `It wanted you strafing in ${cp.wanted_strafe} of ${cp.said} exchanges; you strafed in ${cp.strafed}. You went the way it said in ${cp.followed}.`));
  noteCards(cp.notes, p);
  if (!cp.notes.length) p.append(el("p", "note", "Nothing stood out from how most players fight."));
  p.append(el("p", "note", "One fight is a rough read. The Skill tree page has your style over all your fights."));
  return d;
}
function stylePanel(st) {
  const [d, p] = fold("Your style", "copilot");
  if (!st.enough) { p.append(el("p", "note", `Needs at least 5 fights with key data; you have ${st.fights}. Your habits only settle over several fights.`)); return d; }
  noteCards(st.you, p);
  if (!st.you.length) p.append(el("p", "note", "Your clicks, strafing and aim sit in the usual range for players."));
  if (st.play) p.append(el("p", "note", `Over ${st.fights} fights the copilot wanted you strafing in ${st.play.wanted_strafe} of ${st.play.exchanges} exchanges; you strafed in ${st.play.strafed}.`));
  for (const o of st.opponents) { p.append(el("h3", null, `Opponent ${o.code} · ${plural(o.fights, "fight")}`)); noteCards(o.notes, p); }
  return d;
}

// Experimental: how other answers usually go from this spot (models/answer_model.onnx).
function answersCard(e) {
  const A = e.answers, mine = chosen(e, "you"), c = el("div", "card answers");
  c.append(el("div", "k", "Other answers · experimental"));
  if (e.suggest) c.append(el("div", "v", `Usually went better: ${e.suggest.name}`));
  c.append(el("div", "small", `After their ${A.after} at ${e.dist.toFixed(1)} blocks, how each answer usually goes from a position like this, against real players:`));
  const top = Math.max(0.05, ...A.options.map(o => Math.abs(o.value)));
  const list = el("div", "alist");
  const shown = A.options.slice(0, 5);
  const me = A.options.find(o => o.id === mine);
  if (me && !shown.includes(me)) shown.push(me);
  for (const o of shown) {
    const row = el("div", "arow" + (o.id === mine ? " mine" : ""));
    row.append(el("span", "an", o.name + (o.id === mine ? " (yours)" : "")));
    const bar = el("span", "abar"), fill = el("span", "afill " + (o.value >= 0 ? "pos" : "neg"));
    fill.style.width = (Math.abs(o.value) / top * 50) + "%"; bar.append(fill); row.append(bar);
    row.append(el("span", "av", (o.value > 0 ? "+" : "") + o.value.toFixed(2) + " HP"));
    row.title = `Used in ${Math.round(o.share * 100)}% of spots like this`;
    list.append(row);
  }
  c.append(list);
  if (!me) c.append(el("div", "small", `Your ${techName(mine)}: too rare from spots like this to compare.`));
  if (A.by_band) {
    // The same moment with only the distance changed: which answers the model rates best at each distance.
    const here = S.status.bands.find(b => e.dist >= b.lo && (b.hi == null || e.dist < b.hi));
    const d = el("details", "more"); d.append(el("summary", null, "The same moment at other distances"));
    const bl = el("div", "blist");
    for (const b of S.status.bands) {
      const opts = A.by_band[b.id] || [], row = el("div", "brow" + (here && here.id === b.id ? " here" : ""));
      row.append(el("span", "bn", b.name + (here && here.id === b.id ? " (here)" : "")));
      row.append(el("span", null, opts.length ? opts.map(o => `${o.name} ${(o.value > 0 ? "+" : "") + o.value.toFixed(2)}`).join(" · ") : "–"));
      bl.append(row);
    }
    d.append(bl); c.append(d);
  }
  if (A.farmed) c.append(el("div", "small", "After a run of crits on you this close, these rankings showed no clear edge for human players in testing."));
  c.append(el("div", "small", "A hint from averages, not a verdict on this moment: it cannot know what would have happened here, and the real gain is small."));
  return c;
}

async function saveLabels(body) {
  try {
    await postJson(`/api/fight/${S.fight.id}/labels`, { exchanges: body });
    S.fight = await api("/api/fight/" + S.fight.id); S.stats = null;
    const f = S.fights.find(x => x.id === S.fight.id);
    if (f) { const before = f.relabels; f.relabels = Object.values(S.fight.exchanges).filter(x => x.fix).length; if (f.relabels !== before) renderRail(); markCurrent(); }
    redrawTree(); renderMoment(); toast("Saved");
  } catch (err) { toast("Could not save: " + err.message); }
}
function techSelect(first) {
  const s = el("select"); for (const o of first) s.append(o);
  S.status.families.forEach((n, f) => {
    const g = el("optgroup"); g.label = n;
    for (const t of S.status.techniques) if (t.family === f) g.append(new Option(t.name, t.id));
    s.append(g);
  });
  return s;
}
function relabelForm(e) {
  const f = el("div", "card");
  const lo = S.range ? Math.min(...S.range) : S.sel, hi = S.range ? Math.max(...S.range) : S.sel;
  f.append(el("div", "k", S.range ? `Label exchanges ${lo + 1} to ${hi + 1}` : "Label this exchange"));
  f.append(rich("div", "small", "Say what really happened. Only label what you are sure of; anything you leave is fine and never counts as wrong. Shift-click another column in the chart to label a range."));
  const sides = {};
  const mk = (side, readId, readName) => {
    const s = techSelect(S.range ? [new Option("(not labelled)", ""), new Option("✓ Each read is right", "=read")] : [new Option("(not labelled)", ""), new Option(`✓ The read is right: ${readName}`, "=read")]);
    const fx = e.fix && e.fix[side];
    s.value = fx ? (fx === readId ? "=read" : fx) : ""; s.setAttribute("aria-label", side === "you" ? "Your technique" : "Their technique"); return s;
  };
  const mk2 = (side) => {
    const s = techSelect([new Option("(nothing else)", "")]);
    s.value = (e.fix && e.fix[side + "2"]) || ""; s.setAttribute("aria-label", (side === "you" ? "Your" : "Their") + " second technique"); return s;
  };
  for (const [side, name] of [["you", "You"], ["them", "Them"]]) {
    const box = el("div", "lside " + (side === "you" ? "y" : "o")), sel = mk(side, e[side].id, e[side].name), sel2 = mk2(side), hd = el("h3", null, name);
    if (!S.range) hd.append(el("small", null, `read as ${e[side].name}, ${Math.round(e[side].p * 100)}% sure`));
    box.append(hd);
    const row = el("div", "relabel"), def = el("div", "def");
    const showDef = () => { const id = sel.value === "=read" ? e[side].id : sel.value; def.textContent = id ? techDef(id) : ""; };
    sel.addEventListener("change", showDef); showDef();
    row.append(el("span", "small", "It was"), sel, el("span", "small", "Also"), sel2);
    box.append(row, def);
    let exec = execOf(e, side); const fails = new Set(failsOf(e, side));
    const more = el("details", "more"); more.open = !!exec || fails.size > 0; more.append(el("summary", null, "How it was executed (optional)"));
    const ex = el("div", "seg"); ex.setAttribute("role", "group"); ex.setAttribute("aria-label", name + ": execution");
    for (const x of S.status.execution) {
      const b = el("button", null, x.name); b.type = "button"; b.setAttribute("aria-pressed", String(exec === x.id));
      b.addEventListener("click", () => { exec = exec === x.id ? null : x.id; for (const c of ex.children) c.setAttribute("aria-pressed", String(c === b && exec !== null)); });
      ex.append(b);
    }
    const er = el("div", "lrow"); er.append(ex); more.append(er);
    const fl = el("div", "chipset"); fl.setAttribute("role", "group"); fl.setAttribute("aria-label", name + ": what went wrong");
    for (const x of S.status.fails) {
      const b = el("button", "tog", x.name); b.type = "button"; b.setAttribute("aria-pressed", String(fails.has(x.id)));
      b.addEventListener("click", () => { fails.has(x.id) ? fails.delete(x.id) : fails.add(x.id); b.setAttribute("aria-pressed", String(fails.has(x.id))); });
      fl.append(b);
    }
    const fr = el("div", "lrow"); fr.append(el("span", "small", "What went wrong"), fl); more.append(fr);
    box.append(more);
    if (!S.range && e.hits) box.append(el("div", "small", "The recording shows: " + hitsText(e.hits[side]).toLowerCase()));
    f.append(box);
    sides[side] = { sel, sel2, exec: () => exec, fails: () => S.status.fails.map(x => x.id).filter(id => fails.has(id)) };
  }
  f.append(el("div", "small", "When two moves overlap, name both, one under “Also”. A sprint hit that turned into a hit select is Hit select, also Sprint hit. The order does not matter."));
  const note = el("textarea"); note.placeholder = "Note (optional): what was really going on. It goes into your bundle, so no names or personal details.";
  note.value = (e.fix && e.fix.note) || ""; note.setAttribute("aria-label", "Note"); f.append(note);
  if (!S.range) {
    // A long move is one thing: label it once, across its exchanges.
    const whole = el("div", "controls");
    for (const [side, name] of [["you", "your"], ["them", "their"]]) {
      const m = moveOf(e, side);
      if (m && m.last > m.first) {
        const b = el("button", "btn ghost", `Label ${name} whole move (${m.first + 1} to ${m.last + 1})`); b.type = "button";
        b.addEventListener("click", () => { S.range = [m.first, m.last]; redrawTree(); renderMoment(); });
        whole.append(b);
      }
    }
    if (whole.children.length) f.append(whole);
  }
  const row = el("div", "controls"), save = el("button", "btn primary", "Save label"), clear = el("button", "btn ghost", "Clear");
  save.type = clear.type = "button";
  save.addEventListener("click", () => {
    const b = {};
    const pick = (side, k) => { const x = sides[side].sel.value; return x === "=read" ? S.fight.exchanges[k][side].id : x || null; };
    for (let k = lo; k <= hi; k++) b[k] = { you: pick("you", k), them: pick("them", k), you2: sides.you.sel2.value || null, them2: sides.them.sel2.value || null, span: S.range && hi > lo ? [lo, hi] : undefined, note: note.value,
      exec: { you: sides.you.exec(), them: sides.them.exec() }, fail: { you: sides.you.fails(), them: sides.them.fails() } };
    saveLabels(b);
  });
  clear.addEventListener("click", () => { const b = {}; for (let k = lo; k <= hi; k++) b[k] = {}; saveLabels(b); });
  row.append(save, clear); f.append(row);
  return f;
}

// ---- hit sounds -------------------------------------------------------------------------------
// The attack and hurt sounds of your own game (with your resource pack): the mod hands them to the server on this
// computer, which keeps them in data/sounds. Browsers only start audio after a click, so the first click unlocks it.
const Sfx = (() => {
  let index = null, ctx = null, muted = false;
  const buffers = {};
  try { muted = localStorage.getItem("swordcoach-muted") === "1"; } catch (err) { /* private window: not remembered */ }
  async function load() { if (index) return index; try { index = await api("/api/sounds"); } catch (err) { index = {}; } return index; }
  function audio() {
    if (!ctx && window.AudioContext) { ctx = new AudioContext(); for (const k in index || {}) for (const u of index[k]) buffer(u); }
    if (ctx && ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  function buffer(url) {
    if (!(url in buffers)) buffers[url] = fetch(url).then(r => r.arrayBuffer()).then(b => ctx.decodeAudioData(b)).catch(() => null);
    return buffers[url];
  }
  function play(kind) {
    const list = index && index[kind]; if (muted || !list || !list.length) return;
    const c = audio(); if (!c) return;
    buffer(list[Math.floor(Math.random() * list.length)]).then(buf => {
      if (!buf) return; const src = c.createBufferSource(), g = c.createGain(); g.gain.value = 0.7; src.buffer = buf; src.connect(g).connect(c.destination); src.start();
    });
  }
  document.addEventListener("pointerdown", () => { if (index && Object.keys(index).length) audio(); }, { capture: true });
  return { load, play, has: () => !!index && Object.keys(index).length > 0, muted: () => muted,
    setMuted(v) { muted = v; try { localStorage.setItem("swordcoach-muted", v ? "1" : "0"); } catch (err) { /* not remembered */ } } };
})();

// ---- 3D clip ----------------------------------------------------------------------------------
const KINDS = ["crit", "knockback", "strong", "weak", "sweep", "nodamage"];
const YOU_COL = 0x56c8f5, THEM_COL = 0xb79bff, NIGHT = 0x10151e;
const Clip = (() => {
  let root, stage, canvas, hud, trEl, scrubEl, marksEl, playEl, sndEl, noteEl, renderer, scene, camera, sun, link, P = [], rings = [], tags = [], pops = [], bars = [], sparks = [], ok = true;
  let clip = null, t = 0, playing = false, speed = 0.5, cam = "side", raf = 0, last = 0, side = null, cur = null, heard = -1, far = 7;
  function mount() { if (!root) build(); return root; }
  // Small canvases drawn pixel by pixel: nothing here comes from the game.
  function pixels(size, paint, repeat) {
    const c = document.createElement("canvas"); c.width = c.height = size; paint(c.getContext("2d"));
    const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; tx.magFilter = THREE.NearestFilter; tx.minFilter = THREE.LinearMipmapLinearFilter;
    tx.anisotropy = renderer.capabilities.getMaxAnisotropy();
    if (repeat) { tx.wrapS = tx.wrapT = THREE.RepeatWrapping; tx.repeat.set(repeat, repeat); }
    return tx;
  }
  const rand = (seed) => () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  function floorTex(x) {
    const r = rand(7), shades = ["#1b2330", "#1e2736", "#192130", "#202a3a"];
    for (let bx = 0; bx < 4; bx++) for (let bz = 0; bz < 4; bz++) {
      const ox = bx * 16, oz = bz * 16;
      x.fillStyle = shades[Math.floor(r() * 4)]; x.fillRect(ox, oz, 16, 16);
      for (let i = 0; i < 26; i++) { x.fillStyle = r() < 0.5 ? "#26313f" : "#161c28"; x.fillRect(ox + Math.floor(r() * 16), oz + Math.floor(r() * 16), 1, 1); }
      x.fillStyle = "#2c3748"; x.fillRect(ox, oz, 16, 1); x.fillRect(ox, oz, 1, 16);
      x.fillStyle = "#121824"; x.fillRect(ox, oz + 15, 16, 1); x.fillRect(ox + 15, oz, 1, 16);
    }
  }
  function speckle(x) {
    const r = rand(11);
    x.fillStyle = "#fff"; x.fillRect(0, 0, 16, 16);
    for (let i = 0; i < 90; i++) { const v = 196 + Math.floor(r() * 59); x.fillStyle = `rgb(${v},${v},${v})`; x.fillRect(Math.floor(r() * 16), Math.floor(r() * 16), 1, 1); }
  }
  function build() {
    root = el("div"); root.style.display = "flex"; root.style.flexDirection = "column"; root.style.gap = "8px";
    stage = el("div", "stage"); canvas = el("canvas"); hud = el("div", "hud"); stage.append(canvas, hud); root.append(stage);
    const hb = el("div", "hbars");
    for (const [s, name] of [[0, "You"], [1, "Them"]]) {
      const b = el("div", "hbar " + (s ? "o" : "y")), lab = el("span", "lab", name), track = el("span", "track"), fill = el("span", "fill");
      track.append(fill); b.append(lab, track); bars.push({ b, lab, fill, name });
    }
    trEl = el("div", "tr"); hb.append(bars[0].b, trEl, bars[1].b); hud.append(hb, el("div", "mca", "minecraftcombatai.com"));
    const c2 = el("div", "controls");
    const play = playEl = el("button", "btn", "▶"); play.type = "button"; play.setAttribute("aria-label", "Play"); play.addEventListener("click", toggle);
    const line = el("div", "scrubline"); marksEl = el("div", "marks");
    const scrub = scrubEl = el("input"); scrub.type = "range"; scrub.min = 0; scrub.step = "0.01"; scrub.setAttribute("aria-label", "Time in this clip");
    scrub.addEventListener("input", (ev) => { t = Number(ev.target.value); heard = Math.floor(t); draw(); });
    line.append(marksEl, scrub);
    const segOf = (list, val, name, on) => { const g = el("div", "seg"); g.setAttribute("role", "group"); g.setAttribute("aria-label", name); for (const [v, n] of list) { const b = el("button", null, n); b.type = "button"; b.setAttribute("aria-pressed", String(v === val)); b.addEventListener("click", () => { on(v); for (const x of g.children) x.setAttribute("aria-pressed", String(x === b)); }); g.append(b); } return g; };
    const sp = segOf([[0.25, "¼×"], [0.5, "½×"], [1, "1×"]], speed, "Speed", (v) => { speed = v; });
    const cams = segOf([["side", "Side"], ["you", "Your eyes"], ["them", "Their eyes"], ["top", "Above"]], cam, "Camera", (v) => { cam = v; draw(); });
    const snd = sndEl = el("button", "btn", "Sound"); snd.type = "button"; snd.setAttribute("aria-label", "Hit sounds");
    snd.addEventListener("click", () => { Sfx.setMuted(!Sfx.muted()); soundButton(); });
    c2.append(play, line); const c3 = el("div", "controls"); c3.append(sp, cams, snd); root.append(c2, c3);
    noteEl = el("div", "small"); noteEl.hidden = true; root.append(noteEl);
    Sfx.load().then(soundButton);
    try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true }); } catch (err) { ok = false; }
    if (!ok) { hud.append(el("div", "msg", "3D clips need WebGL, which is switched off in this browser.")); return; }
    renderer.setPixelRatio(Math.min(2, devicePixelRatio || 1));
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    scene = new THREE.Scene(); scene.background = new THREE.Color(NIGHT); scene.fog = new THREE.Fog(NIGHT, 15, 58);
    camera = new THREE.PerspectiveCamera(50, 1.6, 0.05, 300);
    scene.add(new THREE.HemisphereLight(0xd5e2ff, 0x1a2230, 2.3));
    sun = new THREE.DirectionalLight(0xfff0dc, 2.8); sun.castShadow = true; sun.shadow.mapSize.set(1536, 1536); sun.shadow.bias = -0.0006; sun.shadow.radius = 3;
    Object.assign(sun.shadow.camera, { left: -11, right: 11, top: 11, bottom: -11, near: 1, far: 40 }); scene.add(sun, sun.target);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), new THREE.MeshStandardMaterial({ map: pixels(64, floorTex, 150), roughness: 0.92, metalness: 0.05 }));
    ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
    // A few stars above the fog.
    const r = rand(23), pos = [];
    for (let i = 0; i < 420; i++) { const a = r() * Math.PI * 2, e = 0.12 + r() * 1.2; pos.push(Math.cos(a) * Math.cos(e) * 150, Math.sin(e) * 150, Math.sin(a) * Math.cos(e) * 150); }
    const sg = new THREE.BufferGeometry(); sg.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    scene.add(new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xaab8cc, size: 1.1, sizeAttenuation: false, fog: false })));
    const speck = pixels(16, speckle);
    P = [figure(speck, YOU_COL), figure(speck, THEM_COL)]; P.forEach(p => scene.add(p.g));
    rings = [YOU_COL, THEM_COL].map(c => reachRing(c)); rings.forEach(x => scene.add(x));
    const lg = new THREE.BufferGeometry(); lg.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 0, 0, 0], 3));
    link = new THREE.Line(lg, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.45 })); scene.add(link);
    const sparkGeo = new THREE.BoxGeometry(0.08, 0.08, 0.08);
    for (let i = 0; i < 60; i++) { const m = new THREE.Mesh(sparkGeo, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true })); m.visible = false; scene.add(m); sparks.push(m); }
    for (let s = 0; s < 2; s++) { const tg = el("div", "tag " + (s ? "o" : "y")); hud.append(tg); tags.push(tg); const pp = el("div", "pop"); pp.hidden = true; hud.append(pp); pops.push({ el: pp, tick: -9, until: -1 }); }
    new ResizeObserver(resize).observe(stage);
  }
  function soundButton() {
    if (!sndEl) return;
    sndEl.textContent = Sfx.muted() ? "Sound off" : "Sound on"; sndEl.setAttribute("aria-pressed", String(!Sfx.muted()));
    sndEl.disabled = !Sfx.has(); sndEl.title = Sfx.has() ? "Hit sounds from your game" : "No hit sounds yet: start Minecraft with the mod while the server runs";
    note();
  }
  function note() {
    if (!noteEl) return;
    const msg = [];
    if (!Sfx.has()) msg.push("No hit sounds yet: they come from your own game, so start Minecraft with the mod while the server runs.");
    if (S.frames && !S.frames.events_recorded) msg.push("This fight is from before hits were recorded: its crits and hit sounds are worked out from how each hit landed (CRIT?).");
    noteEl.textContent = msg.join(" "); noteEl.hidden = !msg.length;
  }
  function reachRing(color) {
    const g = new THREE.Group(), mat = (o) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity: o, depthWrite: false });
    const ring = new THREE.Mesh(new THREE.RingGeometry(2.96, 3, 96), mat(0.5)), disc = new THREE.Mesh(new THREE.CircleGeometry(0.5, 32), mat(0.28));
    ring.rotation.x = disc.rotation.x = -Math.PI / 2; g.add(ring, disc); g.position.y = 0.015;
    return g;
  }
  function figure(speck, color) {
    const px = 1 / 16, g = new THREE.Group(), body = new THREE.Group(); g.add(body);
    const base = new THREE.Color(color), red = new THREE.Color(0xff2a1c), dark = base.clone().multiplyScalar(0.42);
    const armor = new THREE.MeshStandardMaterial({ map: speck, color: base, roughness: 0.55, metalness: 0.12, emissive: base, emissiveIntensity: 0.14 });
    const trim = new THREE.MeshStandardMaterial({ map: speck, color: dark, roughness: 0.7, metalness: 0.1 });
    const visor = new THREE.MeshStandardMaterial({ color: 0x0a0c11, emissive: base, emissiveIntensity: 0.9, roughness: 0.3 });
    const blade = new THREE.MeshStandardMaterial({ color: 0xdfe9f2, emissive: 0x90b6c8, emissiveIntensity: 0.35, roughness: 0.28, metalness: 0.55 });
    const hilt = new THREE.MeshStandardMaterial({ color: 0x4a3322, roughness: 0.8 }), guard = new THREE.MeshStandardMaterial({ color: 0xffc15e, emissive: 0x6e4c10, emissiveIntensity: 0.4, roughness: 0.4, metalness: 0.4 });
    const box = (w, h, d, m) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w * px, h * px, d * px), m); b.castShadow = true; return b; };
    const pivot = (x, y, mesh, oy) => { const p = new THREE.Group(); p.position.set(x * px, y * px, 0); mesh.position.y = oy * px; p.add(mesh); body.add(p); return p; };
    const legL = pivot(2, 12, box(3.9, 12, 3.9, trim), -6), legR = pivot(-2, 12, box(3.9, 12, 3.9, trim), -6);
    for (const leg of [legL, legR]) { const boot = box(4.3, 3, 4.3, armor); boot.position.y = -10.6 * px; leg.add(boot); }
    const torso = box(8, 12, 4, armor); torso.position.y = 18 * px; body.add(torso);
    const belt = box(8.3, 1.6, 4.3, trim); belt.position.y = 12.8 * px; body.add(belt);
    const chest = box(5, 4, 4.5, trim); chest.position.y = 20 * px; body.add(chest);
    const armL = pivot(6, 22, box(3.9, 12, 3.9, armor), -4), armR = pivot(-6, 22, box(3.9, 12, 3.9, armor), -4);
    const head = new THREE.Group(); head.position.y = 24 * px; body.add(head);
    const skull = box(8, 8, 8, armor); skull.position.y = 4 * px; head.add(skull);
    const eyes = box(7, 1.8, 1, visor); eyes.position.set(0, 4.4 * px, 3.9 * px); eyes.castShadow = false; head.add(eyes);
    const sword = new THREE.Group(); sword.position.set(0, -9 * px, 1 * px); armR.add(sword);
    sword.add(box(1.2, 1.2, 4, hilt)); const gd = box(5, 1.4, 1.2, guard); gd.position.z = 2 * px; sword.add(gd); const bl = box(1.4, 0.8, 12, blade); bl.position.z = 8.5 * px; sword.add(bl);
    // The swing: a flat arc in front of them that fades as the arm comes back.
    const arc = new THREE.Mesh(new THREE.RingGeometry(0.75, 1.4, 28, 1, -Math.PI / 2 - 0.8, 1.6), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
    arc.rotation.x = -Math.PI / 2; arc.position.y = 1.32; arc.visible = false; g.add(arc);
    g.scale.setScalar(0.9375);
    return { g, body, legL, legR, armL, armR, head, arc,
      hurt(k) { armor.color.copy(base).lerp(red, 0.7 * k); armor.emissive.copy(base).lerp(red, 0.9 * k); armor.emissiveIntensity = 0.14 + 0.5 * k; trim.color.copy(dark).lerp(red, 0.5 * k); } };
  }
  function resize() { if (!ok || !stage.isConnected) return; const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / Math.max(1, h); camera.updateProjectionMatrix(); draw(); }
  // The floor is the lowest either player gets in the clip, so nobody who lands later sinks into it.
  function show(e) {
    cur = e; const F = S.frames; if (!F || !ok) return;
    const D = F.drawn, lo = S.range ? Math.min(...S.range) : S.sel, hi = S.range ? Math.max(...S.range) : S.sel;
    const a = Math.max(0, S.fight.exchanges[lo].t0 - 1), b = Math.min(D.length - 1, S.fight.exchanges[hi].t0 + 24);
    let floor = Infinity; for (let i = a; i <= b; i++) floor = Math.min(floor, D[i][1], D[i][11]);
    const o = [(D[a][0] + D[a][10]) / 2, floor, (D[a][2] + D[a][12]) / 2];
    const frames = [], hits = [];
    for (let i = a; i <= b; i++) { const d = D[i]; frames.push([0, 1].map(s => { const q = s * 10; return [d[q] - o[0], d[q + 1] - o[1], d[q + 2] - o[2], d[q + 3], d[q + 4], d[q + 5], d[q + 6], d[q + 7], d[q + 8], d[q + 9]]; })); hits.push([F.hurt[0][i], F.hurt[1][i]]); }
    // Per clip tick: the sounds to play, and what pops over each player (HIT, CRIT, NO DMG).
    const sounds = frames.map(() => []), popAt = frames.map(() => [null, null]), bursts = [];
    for (const [tk, at, kind] of F.sounds || []) if (tk >= a && tk <= b) {
      sounds[tk - a].push(KINDS[kind]);
      if (KINDS[kind] === "nodamage") popAt[tk - a][1 - at] = popAt[tk - a][1 - at] || "NO DMG";
    }
    hits.forEach((h, i) => h.forEach((v, s2) => {
      if (!v) return; sounds[i].push("hurt");
      const c = (F.crits || []).find(([tk, on]) => on === s2 && tk - a >= i - 3 && tk - a <= i + 1);
      popAt[i][s2] = c ? (c[2] ? "CRIT" : "CRIT?") : "HIT";
      bursts.push({ tick: i, s: s2, crit: !!c });
    }));
    clip = { frames, hits, sounds, popAt, bursts, a }; heard = -1; note();
    scrubEl.max = String(Math.max(1, frames.length - 1));
    marksEl.innerHTML = "";
    for (const x of bursts) { const m = el("i", (x.s ? "" : "o") + (x.crit ? " crit" : "")); m.style.left = (x.tick / Math.max(1, frames.length - 1) * 100) + "%"; marksEl.append(m); }
    const f0 = frames[0]; let ax = f0[1][0] - f0[0][0], az = f0[1][2] - f0[0][2]; const L = Math.hypot(ax, az) || 1;
    side = { ax: ax / L, az: az / L, cx: (f0[0][0] + f0[1][0]) / 2, cz: (f0[0][2] + f0[1][2]) / 2 }; far = Math.max(5.5, Math.min(13, 3.2 + L * 1.15));
    t = 0; playing = !reduceMotion; setPlay(); resize(); draw(); if (playing) loop();
  }
  const la = (a, b, k) => { const d = ((b - a) % 360 + 540) % 360 - 180; return a + d * k; };
  function at(tt) {
    const F = clip.frames, i = Math.max(0, Math.min(F.length - 1, Math.floor(tt))), j = Math.min(F.length - 1, i + 1), k = tt - i;
    return [0, 1].map(s => { const a = F[i][s], b = F[j][s]; return { x: a[0] + (b[0] - a[0]) * k, y: a[1] + (b[1] - a[1]) * k, z: a[2] + (b[2] - a[2]) * k,
      head: la(a[3], b[3], k), body: la(a[4], b[4], k), pitch: a[5], hurt: a[6], anim: b[7] >= a[7] ? a[7] + (b[7] - a[7]) * k : a[7], crouch: a[9] > 0.5, spd: Math.hypot(b[0] - a[0], b[2] - a[2]) }; });
  }
  function drawSparks(fr) {
    let n = 0;
    for (const x of clip.bursts) {
      const age = t - x.tick; if (age < 0 || age > 11) continue;
      const f = fr[x.s], r = rand(x.tick * 97 + x.s * 13 + 5), count = x.crit ? 14 : 8;
      for (let i = 0; i < count && n < sparks.length; i++, n++) {
        const a = r() * Math.PI * 2, up = 0.03 + r() * 0.06, sp = 0.035 + r() * 0.05, m = sparks[n];
        m.visible = true; m.position.set(f.x + Math.cos(a) * sp * age, f.y + 1.15 + r() * 0.4 + up * age - 0.0028 * age * age, f.z + Math.sin(a) * sp * age);
        m.material.color.setHex(x.crit ? 0xffc15e : 0xff6a5e); m.material.opacity = 1 - age / 11; m.scale.setScalar(x.crit ? 1.2 : 0.9);
      }
    }
    for (; n < sparks.length; n++) sparks[n].visible = false;
  }
  function draw() {
    if (!clip || !ok || !stage.isConnected) return;
    const fr = at(t), tick = Math.floor(t), apart = Math.hypot(fr[1].x - fr[0].x, fr[1].z - fr[0].z);
    trEl.textContent = `${apart.toFixed(2)} blocks · ${(t / 20).toFixed(2)} s`;
    scrubEl.value = String(t);
    const HP = S.frames.hp, at0 = Math.min(clip.a + tick, HP[0].length - 1);
    bars.forEach((b, s) => { const v = HP[s][at0]; b.fill.style.width = Math.max(0, Math.min(100, v * 5)) + "%"; b.lab.textContent = `${b.name} ${s && S.frames.hp_estimated ? "~" : ""}${v.toFixed(1)}`; });
    fr.forEach((f, s) => {
      const p = P[s]; p.g.position.set(f.x, f.y, f.z); p.g.rotation.y = -f.body * Math.PI / 180; p.head.rotation.y = -(f.head - f.body) * Math.PI / 180;
      let pitch = f.pitch; if (pitch == null || isNaN(pitch)) { const o = fr[1 - s]; pitch = -Math.atan2(o.y + 1.2 - (f.y + 1.62), Math.max(0.3, Math.hypot(o.x - f.x, o.z - f.z))) * 180 / Math.PI; }
      f.pitchUsed = pitch; p.head.rotation.x = pitch * Math.PI / 180;
      const walk = Math.min(1, f.spd / 0.22), leg = Math.sin(t * 1.3) * 0.7 * walk;
      p.legL.rotation.x = leg; p.legR.rotation.x = -leg; p.armL.rotation.x = -leg * 0.8;
      const sw = Math.sin(Math.PI * Math.max(0, Math.min(1, f.anim))); p.armR.rotation.x = -0.45 - 1.35 * sw; p.armR.rotation.z = 0.25 * sw;
      p.body.position.y = f.crouch ? -0.12 : 0; p.body.rotation.x = f.crouch ? 0.35 : 0;
      p.hurt(f.hurt > 0 ? Math.min(1, f.hurt / 10 + 0.2) : 0);
      p.arc.visible = f.anim > 0.02 && f.anim < 0.8; p.arc.material.opacity = 0.42 * (1 - f.anim / 0.8);
      p.g.visible = !((cam === "you" && s === 0) || (cam === "them" && s === 1));
      rings[s].position.x = f.x; rings[s].position.z = f.z;
    });
    const lp = link.geometry.attributes.position; lp.setXYZ(0, fr[0].x, 0.03, fr[0].z); lp.setXYZ(1, fr[1].x, 0.03, fr[1].z); lp.needsUpdate = true;
    link.material.color.setHex(apart <= 3.3 ? 0xff8a7a : 0x8da0b8);
    drawSparks(fr);
    placeCamera(fr); renderer.render(scene, camera);
    const ei = Math.min(S.fight.exchanges.length - 1, (S.range ? Math.min(...S.range) : S.sel) + Math.floor(t / 12)), e = S.fight.exchanges[ei];
    fr.forEach((f, s) => {
      const v = new THREE.Vector3(f.x, f.y + 2.2, f.z).project(camera), vis = v.z < 1 && P[s].g.visible, tg = tags[s];
      tg.hidden = !vis;
      if (vis) { tg.style.left = ((v.x + 1) / 2 * stage.clientWidth) + "px"; tg.style.top = Math.max(58, (1 - v.y) / 2 * stage.clientHeight) + "px"; tg.textContent = techName(chosen(e, s ? "them" : "you")); }
      const pop = pops[s], lab = clip.popAt[tick] ? clip.popAt[tick][s] : null;
      if (lab && pop.tick !== tick) { pop.tick = tick; pop.until = t + (lab.startsWith("CRIT") ? 14 : 9); pop.el.textContent = lab; pop.el.className = "pop" + (lab.startsWith("CRIT") ? " crit" : lab === "NO DMG" ? " nod" : ""); }
      const on = pop.until > t && t >= pop.tick; pop.el.hidden = !on || !vis;
      if (on && vis) { const age = (t - pop.tick) / 9, w = new THREE.Vector3(f.x, f.y + 2.6 + age * 0.4, f.z).project(camera);
        pop.el.style.left = ((w.x + 1) / 2 * stage.clientWidth) + "px"; pop.el.style.top = ((1 - w.y) / 2 * stage.clientHeight) + "px"; pop.el.style.opacity = String(1 - age * 0.7); }
    });
  }
  function placeCamera(fr) {
    const mx = (fr[0].x + fr[1].x) / 2, mz = (fr[0].z + fr[1].z) / 2;
    if (cam === "side" || cam === "top") {
      const want = Math.max(5.5, Math.min(13, 3.2 + Math.hypot(fr[1].x - fr[0].x, fr[1].z - fr[0].z) * 1.15));
      side.cx += (mx - side.cx) * 0.2; side.cz += (mz - side.cz) * 0.2; far += (want - far) * 0.06; const fx = side.az, fz = -side.ax;
      if (cam === "side") { camera.fov = 44; camera.position.set(side.cx - fx * far, 2.1 + far * 0.1, side.cz - fz * far); camera.lookAt(side.cx, 1.0, side.cz); }
      else { camera.fov = 45; camera.position.set(side.cx - fx * 3.2, 7 + far * 0.8, side.cz - fz * 3.2); camera.lookAt(side.cx, 0.4, side.cz); }
    } else {
      const me = cam === "you" ? fr[0] : fr[1], r = me.head * Math.PI / 180, ey = me.y + (me.crouch ? 1.27 : 1.62) * 0.9375, p = (me.pitchUsed || 0) * Math.PI / 180;
      camera.fov = 70; camera.position.set(me.x, ey, me.z); camera.lookAt(me.x - Math.sin(r) * Math.cos(p), ey - Math.sin(p), me.z + Math.cos(r) * Math.cos(p));
    }
    camera.updateProjectionMatrix();
    sun.position.set(side.cx + 6, 13, side.cz + 5); sun.target.position.set(side.cx, 0, side.cz);
  }
  function loop() {
    cancelAnimationFrame(raf); last = performance.now();
    const step = (now) => { const dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (!stage.isConnected) { playing = false; return; }
      if (playing && clip) { const end = clip.frames.length - 1; t = Math.min(end, t + dt * 20 * speed); if (t >= end) { playing = false; setPlay(); }
        for (const tk = Math.floor(t); heard < tk; ) { heard++; for (const k of clip.sounds[heard] || []) Sfx.play(k); } }
      draw(); if (playing) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
  }
  function setPlay() { const b = playEl; if (b) { b.textContent = playing ? "❚❚" : "▶"; b.setAttribute("aria-label", playing ? "Pause" : "Play"); } }
  function toggle() { if (!clip) return; if (t >= clip.frames.length - 1) { t = 0; heard = -1; } playing = !playing; setPlay(); if (playing) loop(); }
  return { mount, show, toggle };
})();

// ---- shared: verdicts and distance ------------------------------------------------------------
// How a technique (or an answer) went for you, as the server works it out: clear only when the 95% range of the
// average is clear of zero.
const LEVEL = {
  working: { color: "--good", soft: "--good-soft", word: "Working for you" },
  costly: { color: "--bad", soft: "--bad-soft", word: "Costing you" },
  even: { color: "--close", soft: "--close-soft", word: "No clear difference" },
  learning: { color: "--unsure", soft: null, word: "Too few to tell yet" },
  "not seen": { color: "--unsure", soft: null, word: "Not seen yet" },
};
const hp2 = (v) => v == null ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(2);
const pm = (se) => se == null ? "" : ` (± ${(2 * se).toFixed(2)})`;
const isRead = (id) => S.status.reads.includes(id);
function bandInfo(id) { return S.status.bands.find(b => b.id === id); }
function bandRange(b) { return b.hi == null ? `${b.lo}+ blocks` : `${b.lo}–${b.hi} blocks`; }
function bandName(id) { if (id === "all") return "All distances"; const b = bandInfo(id); return b ? b.name : id; }
function bandPicker(onChange) {
  const seg = el("div", "seg"); seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Distance when the exchange started");
  for (const b of [{ id: "all", name: "All distances" }, ...S.status.bands]) {
    const x = el("button", null, b.name); x.type = "button";
    x.title = b.id === "all" ? "Every exchange" : `Exchanges that started ${bandRange(b)} apart`;
    x.setAttribute("aria-pressed", String(S.band === b.id));
    x.addEventListener("click", () => { S.band = b.id; try { localStorage.setItem("swordcoach-band", b.id); } catch (err) { /* not remembered */ } onChange(); });
    seg.append(x);
  }
  return seg;
}
function legendRow(items) {
  const lg = el("div", "legend");
  for (const [c, t, dashed] of items) { const s = el("span"); const i = el("i"); i.style.background = dashed ? "transparent" : `var(${c})`; if (dashed) i.style.border = `1.5px dashed var(${c})`; s.append(i, t); lg.append(s); }
  return lg;
}
function watchButtons(list) {
  const row = el("div", "controls");
  for (const x of list) { const b = el("button", "btn", `${x.fight.slice(4, 6)}/${x.fight.slice(6, 8)} ${x.fight.slice(9, 11)}:${x.fight.slice(11, 13)} #${x.ex + 1}`); b.type = "button"; b.addEventListener("click", () => { location.hash = `#fights/${x.fight}/${x.ex}`; }); row.append(b); }
  return row;
}

// ---- answers (branches) -----------------------------------------------------------------------
function showBranches() {
  const v = $("view"); v.innerHTML = "";
  v.append(pageHead("Answers", "What you do after each of their moves, and how it goes for you. It counts your own fights only."));
  const A = S.stats.answers, p = el("section", "panel");
  p.append(el("h2", null, "Your answers, by distance"));
  if (!A.after.length) { p.append(el("p", "note", "Not enough fights yet: play some more with the server running.")); v.append(p); }
  else {
    if (!S.after || !A.after.find(a => a.them === S.after)) S.after = A.after[0].them;
    const row = el("div", "controls"), sel = el("select");
    for (const a of A.after) sel.append(new Option(`${techName(a.them)} (${a.n} times)`, a.them));
    sel.value = S.after; sel.setAttribute("aria-label", "Their technique");
    sel.addEventListener("change", () => { S.after = sel.value; showBranches(); });
    row.append(el("span", null, "After they used"), sel);
    p.append(row);
    p.append(answerGrid(A.after.find(a => a.them === S.after), A.bands));
    p.append(how("How to read this", "Columns are how far apart you were when you answered, and each cell says how that {answer|answer} went compared with what is {usual|usual} from the same position, and how many times you did it.", "A cell is green or red only when the numbers make it clear. A column names a best answer only when one is clearly ahead of the next."));
    const det = el("div", "card detail"); det.id = "adetail"; det.append(el("div", "small", "Click a cell to see the numbers and watch those exchanges.")); p.append(det);
    v.append(p);
  }
  const B = S.stats.branches, q = el("section", "panel");
  q.append(el("h2", null, "How your engagements go"));
  q.append(rich("p", "note", `${B.n} {engagement|engagements} from ${plural(S.stats.fights, "fight")}, read left to right from whoever started it. This is what happened, not advice.`));
  q.append(legendRow([["--them", "their technique"], ["--good", "your move: working for you"], ["--close", "no clear difference"], ["--bad", "costing you"], ["--unsure", "too few to tell"]]));
  const box = el("div", "scroll"); box.append(drawBranches(B)); q.append(box);
  q.append(how("How to read this", "Each engagement starts with the first hit landed, or the first swing if nobody landed one. Each step is 0.6 s, so two boxes side by side happened together; only the first box says who went first. The number is how many engagements went that way."));
  const det = el("div", "card detail"); det.id = "bdetail"; det.append(el("div", "small", "Click a box for its numbers and examples.")); q.append(det);
  v.append(q);
}
function answerGrid(a, bands) {
  const all = a.bands.all.rows.filter(r => r.n >= 5).slice(0, 10);
  const wrap = el("div", "scroll"), t = el("table", "agrid");
  const hr = el("tr"); hr.append(el("th", "rowh", "Your answer"));
  for (const b of bands) { const th = el("th"); th.append(el("div", null, bandName(b)), el("div", "small", b === "all" ? `${a.bands.all.n} answers` : `${bandRange(bandInfo(b))} · ${(a.bands[b] || { n: 0 }).n}`)); hr.append(th); }
  const br = el("tr"); br.append(el("th", "rowh small", "Best here"));
  for (const b of bands) { const c = a.bands[b], best = c && c.best; br.append(el("td", "best" + (best ? " has" : ""), best ? techName(best) : "not clear yet")); }
  const head = el("thead"); head.append(hr, br); t.append(head);
  const body = el("tbody");
  for (const r of all) {
    const tr = el("tr"); tr.append(el("th", "rowh", techName(r.you)));
    for (const b of bands) {
      const c = a.bands[b] && a.bands[b].rows.find(x => x.you === r.you), td = el("td");
      if (!c) { td.append(el("span", "small", "–")); tr.append(td); continue; }
      const btn = el("button", "acell " + c.level.replace(" ", "_")); btn.type = "button";
      const L = LEVEL[c.level];
      if (L.soft && c.level !== "learning") { btn.style.background = `var(${L.soft})`; btn.style.borderColor = `var(${L.color})`; }
      btn.append(el("span", "av", c.n >= 5 ? hp2(c.vs_expected) : "few"), el("span", "an", `${c.n}×`));
      btn.title = `${techName(r.you)} after their ${techName(a.them)}, ${bandName(b).toLowerCase()}: ${c.n} times, ${hp2(c.vs_expected)} HP vs usual. ${L.word}.`;
      btn.addEventListener("click", () => answerDetail(a, b, c));
      td.append(btn); tr.append(td);
    }
    body.append(tr);
  }
  t.append(body); wrap.append(t);
  return wrap;
}
function answerDetail(a, b, c) {
  const d = $("adetail"); d.innerHTML = "";
  d.append(el("div", "k", `After their ${techName(a.them)} · ${bandName(b)}${b === "all" ? "" : " (" + bandRange(bandInfo(b)) + ")"}`));
  d.append(el("div", "v", techName(c.you)));
  d.append(el("div", "small", `${c.n} times. Those exchanges went ${hp2(c.vs_expected)} HP for you compared with what is usual from the same positions${pm(c.se)}. ${LEVEL[c.level].word}${c.level === "learning" ? " (needs 8 or more)" : ""}.`));
  if (c.examples.length) d.append(el("div", "small", "Watch them:"), watchButtons(c.examples));
}
function drawBranches(root) {
  const colW = 190, boxW = 160, rowH = 30, padX = 12, padY = 14;
  let leaves = 0; const place = (n, d) => { n.d = d; if (!n.children.length) { n.y = leaves++; return n.y; } const ys = n.children.map(c => place(c, d + 1)); n.y = (Math.min(...ys) + Math.max(...ys)) / 2; return n.y; };
  place(root, 0);
  let maxD = 0; const walk = (n, f) => { f(n); n.children.forEach(c => walk(c, f)); }; walk(root, n => { maxD = Math.max(maxD, n.d); });
  const W = padX * 2 + (maxD + 1) * colW, H = padY * 2 + Math.max(1, leaves) * rowH;
  const svg = sv("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "group", "aria-label": "Branch map" });
  const X = (n) => padX + n.d * colW, Y = (n) => padY + n.y * rowH + rowH / 2;
  walk(root, n => n.children.forEach(c => svg.append(sv("path", { d: `M${X(n) + boxW},${Y(n)} C${X(n) + boxW + 15},${Y(n)} ${X(c) - 15},${Y(c)} ${X(c)},${Y(c)}`, fill: "none", stroke: css("--line"), "stroke-width": Math.max(1, Math.min(8, Math.sqrt(c.n))) }))));
  walk(root, n => {
    const g = sv("g", { tabindex: 0, role: "button", style: "cursor:pointer" });
    let fill = css("--chip"), stroke = css("--line"), txt = css("--ink");
    if (n.side === "them") { fill = css("--them-soft"); stroke = css("--them"); }
    else if (n.side === "you") { stroke = css(LEVEL[n.level || "learning"].color); fill = css("--shell"); }
    g.append(sv("rect", { x: X(n), y: Y(n) - 11, width: boxW, height: 22, fill, stroke, "stroke-width": n.side === "you" ? 2 : 1 }));
    const pre = n.side === "them" ? "They: " : n.side === "you" ? "You: " : "";
    const label = pre + n.label, t = sv("text", { x: X(n) + 7, y: Y(n) + 4, fill: txt, "font-size": 11 }); t.textContent = label.length > 20 ? label.slice(0, 19) + "…" : label; g.append(t);
    const c = sv("text", { x: X(n) + boxW - 7, y: Y(n) + 4, fill: txt, "font-size": 10, "text-anchor": "end", opacity: 0.85 }); c.textContent = String(n.n); g.append(c);
    const tt = sv("title"); tt.textContent = `${pre}${n.label}: ${n.n}${n.vs_expected != null ? ` · ${hp2(n.vs_expected)} HP vs usual` : ""}`; g.append(tt);
    g.addEventListener("click", () => branchDetail(n));
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter") branchDetail(n); });
    svg.append(g);
  });
  return svg;
}
function branchDetail(n) {
  const d = $("bdetail"); d.innerHTML = "";
  d.append(el("div", "k", n.side === "them" ? "They" : n.side === "you" ? "You" : "All engagements"));
  d.append(el("div", "v", n.label));
  d.append(el("div", "small", `${n.n} times${n.vs_expected != null ? ` · those exchanges went ${hp2(n.vs_expected)} HP for you vs what is usual from the same positions${pm(n.se)}` : ""}${n.side === "you" && n.level ? ` · ${LEVEL[n.level].word.toLowerCase()}` : ""}.`));
  if (n.examples && n.examples.length) d.append(el("div", "small", "Watch it:"), watchButtons(n.examples));
}

// ---- skill tree -------------------------------------------------------------------------------
const SKILL_LAYOUT = {
  stand_trade: [0, 6], run_in: [0, 13], spam_click: [0, 20],
  single_sweep: [1, 2.5], sprint_hit: [1, 10], jump_spam: [1, 20],
  sweep_combo: [2, 0], followup_sweep: [2, 1], punish_sweep: [2, 2], back_sweep: [2, 3], backaway_sweep: [2, 4], side_sweep: [2, 5],
  uppercut: [2, 6], pick_hit: [2, 7], w_tap: [2, 8], falling_sprint_hit: [2, 9], sneak_tap: [2, 10], s_tap: [2, 11], strafe: [2, 12],
  retreat: [2, 14], jump_in: [2, 16], jump_crit: [2, 18.5], jump_reset: [2, 22],
  kb_displace: [3, 8], falling_sprint_hit_deflection: [3, 9], crouch_dodge: [3, 10], s_hold_deflection: [3, 11],
  circle_strafe: [3, 12], repositioning: [3, 13], space: [3, 14], s_crit: [3, 15], sprint_crit: [3, 16], crit_counter: [3, 17],
  crit_deflection: [3, 18], punish_crit: [3, 19], nokb_crit: [3, 20], double_crit: [3, 21], reset_crit: [3, 22], jump_reset_sprint_hit: [3, 23],
  stun_hit_prediction: [4, 10], bait: [4, 14], punish_crit_reaction: [4, 19], nokb_combo: [4, 20],
  hit_select: [5, 14],
};
function showSkills() {
  const v = $("view"); v.innerHTML = "";
  const T = S.stats.skill_tree[S.band] || S.stats.skill_tree.all;
  v.append(pageHead("Skill tree", "Which techniques are working for you, and what to learn next.", bandPicker(showSkills)));
  const top = el("section", "panel");
  top.append(el("h2", null, "Where you stand"));
  const where = S.band === "all" ? "" : `Only moves that started ${bandName(S.band).toLowerCase()} (${bandRange(bandInfo(S.band))}). `;
  top.append(rich("p", "note", `${where}From ${plural(T.moves, "move")} in ${plural(S.stats.fights, "fight")}. Numbers are HP against what is {usual|usual} from the same positions.`));
  const grid = el("div", "stand");
  for (const lv of ["working", "costly", "even", "learning"]) {
    const ns = T.nodes.filter(n => n.level === lv).sort((a, b) => lv === "working" ? b.vs_expected - a.vs_expected : lv === "costly" ? a.vs_expected - b.vs_expected : b.uses - a.uses);
    const c = el("div", "card standcard"); c.style.borderTopColor = `var(${LEVEL[lv].color})`;
    const hd = el("div", "shead"); hd.append(el("div", "k", LEVEL[lv].word), el("div", "n", String(ns.length))); c.append(hd);
    const list = el("div", "slist");
    for (const n of ns.slice(0, 6)) {
      const b = el("button", "srow"); b.type = "button";
      b.append(el("span", null, n.name), el("span", "sv", lv === "learning" ? `${n.uses} uses` : hp2(n.vs_expected)));
      b.addEventListener("click", () => { skillDetail(n); $("sdetail").scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" }); });
      list.append(b);
    }
    if (ns.length > 6) list.append(el("div", "small", `and ${ns.length - 6} more in the tree below`));
    if (!ns.length) list.append(el("div", "small", lv === "working" ? "None clear yet." : "None."));
    c.append(list); grid.append(c);
  }
  top.append(grid);
  const unseen = T.nodes.filter(n => n.level === "not seen"), labelOnly = unseen.filter(n => !isRead(n.id));
  top.append(how("How this is worked out", "A technique counts as working or costing you only when the numbers make it clear, from 15 uses. +0.20 means you came out 0.2 HP better than {usual|usual} each time, −0.20 means 0.2 HP worse.", `${unseen.length} techniques are not seen yet (under 5 uses).` + (labelOnly.length ? ` ${labelOnly.length} of them the reader cannot name yet: they only count once you {label|label} exchanges as them (dashed in the tree).` : "")));
  v.append(top);
  const p = el("section", "panel");
  p.append(el("h2", null, `The ${T.nodes.length} techniques, from entry to high level`));
  p.append(legendRow([["--good", "working for you"], ["--bad", "costing you"], ["--close", "no clear difference"], ["--unsure", "too few to tell"], ["--unsure", "only counted when you label it", true]]));
  const line = el("div", "treeline");
  const box = el("div", "scroll"); box.append(drawSkills(T));
  const det = el("div", "card detail"); det.id = "sdetail"; det.append(el("div", "small", "Click a technique for what it is and your numbers at each distance."));
  line.append(box, det); p.append(line);
  v.append(p);
  if (S.stats.style) v.append(stylePanel(S.stats.style));
}
function drawSkills(T) {
  const rows = Object.values(SKILL_LAYOUT).map(p => p[1]), r0 = Math.min(...rows), r1 = Math.max(...rows);
  const colW = 175, rowH = 54, W = 6 * colW + 30, H = 100 + (r1 - r0) * rowH, nx = (c) => 20 + c * colW, ny = (r) => 52 + (r - r0) * rowH;
  const svg = sv("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "group", "aria-label": "Skill tree" });
  [["Entry", 0, 1], ["Mid", 1.5, 3], ["High", 3.5, 6]].forEach(([n, a]) => { const t = sv("text", { x: nx(a) + 4, y: 20, fill: css("--dim"), "font-size": 11 }); t.textContent = n.toUpperCase(); svg.append(t); });
  for (const n of T.nodes) for (const req of n.requires) { const a = SKILL_LAYOUT[req], b = SKILL_LAYOUT[n.id]; if (!a || !b) continue;
    svg.append(sv("path", { d: `M${nx(a[0]) + 150},${ny(a[1])} C${nx(a[0]) + 165},${ny(a[1])} ${nx(b[0]) - 15},${ny(b[1])} ${nx(b[0])},${ny(b[1])}`, fill: "none", stroke: css("--line"), "stroke-width": 1.5 })); }
  for (const n of T.nodes) {
    const [c, r] = SKILL_LAYOUT[n.id], x = nx(c), y = ny(r), g = sv("g", { tabindex: 0, role: "button", style: "cursor:pointer" });
    const L = LEVEL[n.level], read = isRead(n.id);
    g.append(sv("rect", { x, y: y - 22, width: 150, height: 44, fill: css("--shell"), stroke: css(L.color), "stroke-width": 2, "stroke-dasharray": read ? "none" : "5 3", opacity: n.level === "not seen" ? 0.75 : 1 }));
    const t1 = sv("text", { x: x + 9, y: y - 4, fill: css("--ink"), "font-size": n.name.length > 18 ? 10.5 : 12, "font-weight": 600 }); t1.textContent = n.name; g.append(t1);
    if (n.name.length > 24) { t1.setAttribute("textLength", 132); t1.setAttribute("lengthAdjust", "spacingAndGlyphs"); }
    const line2 = n.uses >= 5 && n.vs_expected != null ? `${n.uses} uses · ${hp2(n.vs_expected)}` : !read ? (n.labelled ? `${n.labelled} labelled` : "label it to count it") : `${n.uses} uses`;
    const t2 = sv("text", { x: x + 9, y: y + 12, fill: css("--muted"), "font-size": 10.5 }); t2.textContent = line2; g.append(t2);
    const share = Math.min(1, n.share * 4); g.append(sv("rect", { x: x + 9, y: y + 16, width: 132 * share, height: 3, fill: css(L.color) }));
    const tt = sv("title"); tt.textContent = `${n.name}: ${L.word.toLowerCase()}${read ? "" : " · the reader cannot name it yet"}`; g.append(tt);
    g.addEventListener("click", () => skillDetail(n));
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter") skillDetail(n); });
    svg.append(g);
  }
  return svg;
}
function skillDetail(n) {
  const d = $("sdetail"); d.innerHTML = "";
  const byId = Object.fromEntries((S.stats.skill_tree[S.band] || S.stats.skill_tree.all).nodes.map(x => [x.id, x]));
  d.append(el("div", "k", `${n.tier} level · ${LEVEL[n.level].word}${S.band === "all" ? "" : " · " + bandName(S.band).toLowerCase()}`), el("div", "v", n.name));
  d.append(el("div", "def", techDef(n.id)));
  if (!isRead(n.id)) d.append(el("div", "small lab", `The reader cannot name ${n.name} yet, so it only counts where you labelled it (${n.labelled} so far${S.band === "all" ? "" : " at this distance"}). Sure labels of it are what can teach the next model.`));
  d.append(el("div", "small", `You used it ${n.uses} times (${Math.round(n.share * 100)}% of your moves) across ${plural(n.fights, "fight")}` + (n.vs_expected != null ? `; they went ${hp2(n.vs_expected)} HP for you vs usual${pm(n.se)}.` : ".")));
  d.append(el("div", "small", `Opponents used it against you ${n.faced} times` + (n.faced_vs_expected != null ? `; those exchanges went ${hp2(n.faced_vs_expected)} HP for you vs usual.` : ".")));
  const bd = S.stats.by_distance[n.id];
  if (bd) {
    const t = el("table", "dtable"), hr = el("tr");
    const usage = S.status.usage && S.status.usage.per_100[n.id];
    for (const x of ["Distance", "Uses", "vs usual", ...(usage ? ["Others"] : [])]) hr.append(el("th", null, x));
    t.append(hr);
    for (const b of S.status.bands) {
      const c = bd[b.id], tr = el("tr");
      tr.append(el("td", null, b.name), el("td", null, String(c.n)));
      const w = el("td", null, c.n ? hp2(c.vs_expected) + pm(c.se) : "–"); w.style.color = `var(${c.level === "learning" || c.level === "not seen" ? "--muted" : LEVEL[c.level].color})`; w.title = LEVEL[c.level].word; tr.append(w);
      if (usage) { const td = el("td", null, usage[S.status.bands.indexOf(b)] + " in 100"); td.title = "How often recorded players use it in exchanges that start at this distance"; tr.append(td); }
      t.append(tr);
    }
    d.append(t);
  }
  const xs = S.status.execution.filter(x => n.execution && n.execution[x.id]);
  if (xs.length) d.append(el("div", "small", "How you rated your execution: " + xs.map(x => `${x.name.toLowerCase()} ${n.execution[x.id]}`).join(" · ")));
  const fs = S.status.fails.filter(x => n.fails && n.fails[x.id]);
  if (fs.length) d.append(el("div", "small", "What went wrong: " + fs.map(x => `${x.name.toLowerCase()} ${n.fails[x.id]}`).join(" · ")));
  if (n.requires.length) d.append(el("div", "small", "Builds on: " + n.requires.map(r => byId[r] ? byId[r].name : r).join(", ")));
}

// ---- matchups ---------------------------------------------------------------------------------
function showMatchups() {
  const v = $("view"); v.innerHTML = "";
  const M = S.stats.matchups[S.band] || S.stats.matchups.all, p = el("section", "panel");
  v.append(pageHead("Matchups", "Your technique against theirs, across all your fights.", bandPicker(showMatchups)));
  p.append(legendRow([["--good", "went better than usual"], ["--close", "about usual"], ["--bad", "went worse than usual"], ["--chip", "not seen"]]));
  const T = M.techniques, cell = {}; for (const c of M.cells) cell[c.you + "|" + c.them] = c;
  const longest = Math.max(...T.map(t => M.labels[t].length));
  const cw = 30, left = 24 + longest * 6.6, topH = 30 + longest * 5.2, W = left + T.length * cw + 12, H = topH + T.length * cw + 12;
  const svg = sv("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "group", "aria-label": "Matchup grid" });
  const det = el("div", "card detail"); det.append(el("div", "small", "Point at a square for its numbers. Rows are your technique, columns theirs. Faint squares have fewer than 8 exchanges."));
  const say = (y, t, c) => { det.innerHTML = ""; det.append(el("div", "k", `You ${M.labels[y]} · they ${M.labels[t]}`), el("div", "v", c ? `${hp2(c.vs_expected)} HP vs usual` : "Not seen"), el("div", "small", c ? plural(c.n, "move") + (c.n < 8 ? ", too few to read much into" : "") : "You have not met this pairing yet.")); };
  T.forEach((t, j) => { const tx = sv("text", { x: left + j * cw + cw / 2, y: topH - 6, fill: css("--them"), "font-size": 10.5, transform: `rotate(-50 ${left + j * cw + cw / 2} ${topH - 6})` }); tx.textContent = M.labels[t]; svg.append(tx); });
  T.forEach((y, i) => {
    const tx = sv("text", { x: left - 6, y: topH + i * cw + cw / 2 + 4, fill: css("--you"), "font-size": 10.5, "text-anchor": "end" }); tx.textContent = M.labels[y]; svg.append(tx);
    T.forEach((t, j) => {
      const c = cell[y + "|" + t], x = left + j * cw, yy = topH + i * cw;
      let fill = css("--chip"), op = 1;
      if (c && c.vs_expected != null) { fill = css(c.vs_expected > 0.1 ? "--good" : c.vs_expected < -0.1 ? "--bad" : "--close"); op = c.n >= 8 ? Math.min(1, 0.4 + Math.abs(c.vs_expected)) : 0.25; }
      const g = sv("g", { tabindex: 0 }), r = sv("rect", { x: x + 1, y: yy + 1, width: cw - 2, height: cw - 2, fill, opacity: op });
      const tt = sv("title"); tt.textContent = c ? `You ${M.labels[y]} vs their ${M.labels[t]}: ${c.n} moves, ${hp2(c.vs_expected)} HP vs usual` : `You ${M.labels[y]} vs their ${M.labels[t]}: none`; r.append(tt);
      g.append(r);
      if (c && c.n >= 8) { const n = sv("text", { x: x + cw / 2, y: yy + cw / 2 + 4, "text-anchor": "middle", fill: css("--on-accent"), "font-size": 9.5, "font-weight": 700 }); n.textContent = c.n; g.append(n); }
      g.addEventListener("mouseenter", () => say(y, t, c)); g.addEventListener("focus", () => say(y, t, c));
      svg.append(g);
    });
  });
  const box = el("div", "scroll"); box.append(svg); p.append(box, det); v.append(p);
}

// ---- your data --------------------------------------------------------------------------------
function showData() {
  const st = S.status, v = $("view"); v.innerHTML = "";
  const L = S.stats.labels;
  v.append(pageHead("Your data", "Everything stays on this computer until you choose to share it."));
  const tiles = el("div", "tiles"); tiles.style.gridTemplateColumns = "repeat(auto-fit, minmax(150px, 1fr))";
  tiles.append(statTile(String(st.fights), "fights saved"), statTile(String(L.exchanges), "exchanges labelled", L.exchanges ? "good" : ""), statTile(String(L.fights), "fights with labels"), statTile(st.profile.tier || "–", "your tier"));
  v.append(tiles);

  const two = el("div", "twoup");
  const how1 = el("section", "panel");
  how1.append(el("h2", null, "Help the next model"));
  const ol = el("ol", "steps");
  const step = (b, t) => { const li = el("li"); li.append(el("b", null, b + " "), t); ol.append(li); };
  step("Play.", "Every fight is saved here on its own. Nothing is sent anywhere.");
  step("Check reads.", "On the Fights tab, pick an exchange you remember. If the read is right, press “✓ Both reads are right”. If not, open Label this and pick what really happened.");
  step("Only label what you are sure of.", "Anything you leave is fine and never counts as wrong. A few sure labels help more than many guesses, and the Guide tab says what counts as each technique.");
  step("Or use record mode.", "In game press U, then [ and ], to declare the technique you are practising before you do it.");
  step("Send it.", "Run Bundle Fight Data.bat and send the zip to MCA. You can keep playing; the next bundle simply has everything up to then.");
  how1.append(ol);
  const links = el("p", "note"); const dis = el("a", null, "the official Discord"); dis.href = DISCORD; dis.target = "_blank"; dis.rel = "noopener";
  links.append("Send bundles on ", dis, ". Sending one means you agree MCA can use it to train and test future models.");
  how1.append(links);
  how1.append(how("What your data teaches", "{label|Labels} teach the technique reader: what it names, on you and on your opponents. That is the part that improves most from players labelling.", "The fights themselves teach everything else: what is {usual|usual} from a position, other answers, the health guess and the copilot. So sending fights helps even if you label nothing.", "Execution ratings and what went wrong are for your own review. The models do not use them yet."));
  two.append(how1);

  const set = el("section", "panel");
  set.append(el("h2", null, "Settings"));
  const pick = el("div", "pick");
  pick.append(el("h3", null, "Your tier"), el("p", "small", "It goes into your bundles and nowhere else, so fights from players of different levels can be kept apart."));
  const seg = el("div", "chipset"); seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Your tier");
  const setProfile = async (body, msg) => { try { st.profile = await postJson("/api/profile", body); S.fight = null; toast(msg); showData(); } catch (err) { toast("Could not save: " + err.message); } };
  for (const t of [...st.tiers, null]) {
    const b = el("button", "tog tier", t || "Not set"); b.type = "button"; b.setAttribute("aria-pressed", String((st.profile.tier || null) === t));
    b.addEventListener("click", () => setProfile({ tier: t }, t ? "Tier set to " + t : "Tier cleared"));
    seg.append(b);
  }
  pick.append(seg); set.append(pick);
  const co = el("div", "pick");
  co.append(el("h3", null, "Copilot counters (experimental)"), el("p", "small", "With the copilot on (G), it names their move under your crosshair. With this on, it also marks your answer green or red and names a counter."));
  co.append(how("What the evidence says", "On fights it never saw, players who happened to do the named counter came out about 0.2 HP better over 1.2 s than with other answers. That was one of several settings tried, so it is a trend, not a clear result yet. A quarter of counters stay off the screen at random and every one is kept with the fight, so your own fights can show whether seeing them helps."));
  const cs = el("div", "chipset"); cs.setAttribute("role", "group"); cs.setAttribute("aria-label", "Copilot counters");
  for (const [on, word] of [[false, "Off"], [true, "On"]]) {
    const b = el("button", "tog tier", word); b.type = "button"; b.setAttribute("aria-pressed", String(!!st.profile.counters === on));
    b.addEventListener("click", () => setProfile({ counters: on }, on ? "Counters on" : "Counters off"));
    cs.append(b);
  }
  co.append(cs); set.append(co); two.append(set); v.append(two);

  if (L.next.length) {
    const nx = el("section", "panel");
    nx.append(el("h2", null, "Worth labelling next"));
    nx.append(el("p", "note", "The unlabelled exchanges the reader was least sure about. If you remember one, labelling it teaches the most."));
    const grid = el("div", "worselist");
    for (const x of L.next) {
      const b = el("button", "next"); b.type = "button";
      b.append(el("div", "small", `${fmtTime(x.fight.slice(0, 4) + "-" + x.fight.slice(4, 6) + "-" + x.fight.slice(6, 8) + "T" + x.fight.slice(9, 11) + ":" + x.fight.slice(11, 13))} · exchange ${x.ex + 1}`));
      b.append(el("div", null, `Read as ${techName(x.you)} vs their ${techName(x.them)}`));
      b.append(el("div", "small", `${Math.round(x.p * 100)}% sure`));
      b.addEventListener("click", () => { S.pane = "label"; location.hash = `#fights/${x.fight}/${x.ex}`; });
      grid.append(b);
    }
    nx.append(grid); v.append(nx);
  }

  const [d, prog] = fold("Your labels per technique");
  prog.append(rich("p", "note", "“Checked” means you said the read was right, “corrected” that you changed it. The reader cannot name the dashed ones yet."));
  const t = el("table", "ltable"), hr = el("tr");
  for (const x of ["Technique", "You", "Them", "Checked", "Corrected", ""]) hr.append(el("th", null, x));
  t.append(hr);
  const top = Math.max(1, ...Object.values(L.techniques).map(x => x.you + x.them));
  st.families.forEach((fname, f) => {
    const fr = el("tr", "fam"); fr.append(el("td", null, fname)); for (let i = 0; i < 5; i++) fr.append(el("td")); t.append(fr);
    for (const tq of st.techniques.filter(q => q.family === f)) {
      const c = L.techniques[tq.id], tr = el("tr");
      const nm = el("td", isRead(tq.id) ? null : "unread", tq.name); nm.title = tq.definition; tr.append(nm);
      for (const k of ["you", "them", "checked", "corrected"]) tr.append(el("td", "num", c[k] ? String(c[k]) : "·"));
      const bar = el("td"); const bf = el("span", "lbar"); bf.style.width = Math.round((c.you + c.them) / top * 100) + "%"; bar.append(bf); tr.append(bar);
      t.append(tr);
    }
  });
  const box = el("div", "scroll"); box.append(t); prog.append(box);
  v.append(d);

  const [d2, p] = fold("Where your files are");
  const ul = el("ul", "steps");
  const li = (x) => ul.append(el("li", null, x));
  li(`${plural(st.fights, "fight")} saved in ${st.data} (fights/, and your labels in labels/). Nothing leaves this computer on its own.`);
  li("A bundle holds your fights, labels, tier and an install id. Player names are never saved: each player gets a code made with a key that stays on this computer.");
  li("Hit sounds: the clips play the attack and hurt sounds of your own game (with your resource pack). The mod hands them to this server, which keeps them in sounds/. They are never put in a bundle.");
  p.append(ul);
  v.append(d2);
}

// ---- guide ------------------------------------------------------------------------------------
function showGuide() {
  const v = $("view"), st = S.status; v.innerHTML = "";
  v.append(pageHead("Guide", "How Sword Coach works, what the words mean, and what counts as each technique."));
  const two = el("div", "twoup");
  const start = el("section", "panel"); start.append(el("h2", null, "Start here"), startList()); two.append(start);
  const keys = el("section", "panel"); keys.append(el("h2", null, "Keys in game"));
  const kl = el("div", "keys");
  for (const [k, t] of [["H", "Replay your last fight"], ["K", "Jump to the moments that went worse"], ["Y", "Your saved fights"], ["J", "Show or hide the panel"], ["U", "Record mode on or off"], ["[ ]", "Record mode: pick the technique"], ["G", "Fight copilot (experimental)"]]) { const r = el("div"); r.append(el("kbd", null, k), el("span", null, t)); kl.append(r); }
  keys.append(kl, el("p", "note", "During a replay: ← → previous or next point, , . one tick, ↑ ↓ speed, B pause, V camera."));
  keys.append(el("p", "note", "Check a server's rules before using the copilot there: many ban on-screen help during fights."));
  two.append(keys); v.append(two);

  const words = el("section", "panel"); words.append(el("h2", null, "The words on these pages"));
  const dl = el("dl", "gloss"); dl.style.margin = 0;
  for (const k in TERMS) { const d = el("div"); d.append(el("dt", null, TERMS[k][0]), el("dd", null, TERMS[k][1])); dl.append(d); }
  words.append(dl); v.append(words);

  const tp = el("section", "panel");
  const h = el("div", "head"); h.append(el("h2", null, `The ${st.techniques.length} techniques`));
  const find = el("input"); find.type = "search"; find.placeholder = "Find a technique"; find.setAttribute("aria-label", "Find a technique"); h.append(find); tp.append(h);
  tp.append(el("p", "note", "Label by these meanings, so labels from different players mean the same thing. If a name means something else to you, tell us on Discord rather than labelling it your way."));
  const body = el("div"); body.style.display = "flex"; body.style.flexDirection = "column"; body.style.gap = "12px";
  const paint = () => {
    body.innerHTML = ""; const q = find.value.trim().toLowerCase();
    st.families.forEach((fname, f) => {
      const list = st.techniques.filter(t => t.family === f && (!q || t.name.toLowerCase().includes(q) || t.definition.toLowerCase().includes(q)));
      if (!list.length) return;
      body.append(el("h3", null, fname));
      const grid = el("div", "techs");
      for (const t of list) {
        const c = el("div", "techcard"), n = el("div", "nm");
        n.append(el("span", null, t.name), el("span", "tg", `${t.tier}${isRead(t.id) ? "" : " · label only"}`)); c.append(n, el("p", null, t.definition)); grid.append(c);
      }
      body.append(grid);
    });
    if (!body.children.length) body.append(el("p", "note", "No technique matches that."));
  };
  find.addEventListener("input", paint); paint(); tp.append(body); v.append(tp);

  const ab = el("section", "panel"); ab.append(el("h2", null, "About"));
  const pa = el("p", "note"), a = el("a", null, "minecraftcombatai.com"); a.href = SITE; a.target = "_blank"; a.rel = "noopener";
  pa.append("Sword Coach is made by MCA - Minecraft Combat AI: Skorchekd, ApocalypseGamer1, Crazyon and centerx. See what else we have built at ", a, ".");
  ab.append(pa, el("p", "small mono", `Sword Coach ${st.version} · ${Object.entries(st.models || {}).filter(([, x]) => x).map(([k, x]) => `${k.replace(/_/g, " ")} ${x}`).join(" · ")}`));
  ab.append(el("p", "small", "Sword Coach is not an official Minecraft product and is not approved by or associated with Mojang Studios or Microsoft."));
  v.append(ab);
}

// ---- live status ------------------------------------------------------------------------------
async function poll() {
  try {
    const l = await api("/api/live"), box = $("live"), had = S.live.fights;
    S.live = l; box.className = "live " + (l.mod ? "on" : "off");
    box.lastElementChild.textContent = l.mod ? "Game connected" : "Waiting for the game";
    if (S.status) S.status.fights = l.fights;
    if (had && l.fights > had) {
      S.stats = null;
      toast("New fight saved", ["Open it", () => { S.fight = null; location.hash = "#fights"; if (S.tab === "fights") route(); }]);
      if (S.tab === "fights" && $("rail")) { S.fights = await api("/api/fights"); renderRail(); markCurrent(); }
    }
  } catch (err) { const box = $("live"); box.className = "live"; box.lastElementChild.textContent = "Server stopped"; }
}

// ---- start ------------------------------------------------------------------------------------
window.addEventListener("keydown", (e) => {
  if (S.tab !== "fights" || !S.fight || ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "SUMMARY"].includes(e.target.tagName)) return;
  if (e.key === "ArrowRight") { select(S.sel + 1); e.preventDefault(); } else if (e.key === "ArrowLeft") { select(S.sel - 1); e.preventDefault(); }
  else if (e.key === " ") { Clip.toggle(); e.preventDefault(); }
});
window.addEventListener("hashchange", () => route());
(async () => {
  $("wordmark").append(pixelText("Sword Coach", 3));
  $("footmark").append(pixelText("MCA", 3));
  try { S.status = await api("/api/status"); } catch (e) { $("view").append(el("div", "panel empty", "The Sword Coach server is not answering. Start it with Launch AI Server.bat.")); return; }
  await poll();
  setInterval(poll, 4000);
  route();
})();
