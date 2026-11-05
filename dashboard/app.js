// Dashboard for near-thesis-data. Every figure comes from ../data/ (numbers.json and the
// data files); nothing is written by hand. Charts are inline SVG drawn below. The five
// "Check live" buttons make read-only RPC calls (query / call_function) from the browser.
"use strict";

const RPC = "https://rpc.mainnet.fastnear.com";
const DATA = "../data/";
const THOUSAND = 10 ** 3;
const MILLION = 10 ** 6;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Every numbers.json key this script reads (data-n keys in index.html are listed there).
const KEYS = [
  "n2.fees_usd_per_day", "n1.new_near_per_day", "iv.fees_conversion_price_usd",
  "iv.wallets_share_of_fees_with_front_end", "n2.hsp029_max_coverage", "n2.hsp029_equilibrium_price_usd",
  "iv.hsp029_fees_multiple", "n2.equilibrium_price_usd", "n1.coverage_with_front_end",
  "c.front_end_transfer", "c.front_end_rules", "c.intents_fee_change", "c.buybacks_confirmations",
  "c.issuance_upgrade_stake_threshold", "c.issuance_validators_to_pass_upgrade", "iv.issuance_rate_per_year",
  "f6.change1.utc", "f8.quorum_required_venear", "f8.fewest_voters_reaching_quorum",
  "f8.top8_share_of_votes_cast", "n1.coverage_buybacks", "n3.largest_share",
  "n2.max_coverage", "n3.stakers_active",
  // the 2031 section (chartTo2031)
  "n1.buybacks_near_per_day", "n1.front_end_near_per_day", "lr.issuance_per_day.A.2028",
  "lr.issuance_per_day.A.2029", "lr.issuance_per_day.A.2031", "lr.issuance_per_day.B.2028",
  "lr.issuance_per_day.B.2029", "lr.issuance_per_day.B.2031", "lr.required_growth.buybacks.A.2028",
  "lr.required_growth.buybacks.A.2029", "lr.required_growth.buybacks.A.2031", "lr.required_growth.buybacks.B.2028",
  "lr.required_growth.buybacks.B.2029", "lr.required_growth.buybacks.B.2031",
  "lr.required_growth.buybacks.B_late.2028", "lr.required_growth.buybacks.B_late.2029",
  "lr.required_growth.buybacks.B_late.2031", "lr.required_growth.with_front_end.A.2028",
  "lr.required_growth.with_front_end.A.2029", "lr.required_growth.with_front_end.A.2031",
  "lr.required_growth.with_front_end.B.2028", "lr.required_growth.with_front_end.B.2029",
  "lr.required_growth.with_front_end.B.2031", "lr.required_growth.with_front_end.B_late.2028",
  "lr.required_growth.with_front_end.B_late.2029", "lr.required_growth.with_front_end.B_late.2031",
  "lr.required_growth.all_fees.A.2028", "lr.required_growth.all_fees.A.2029", "lr.required_growth.all_fees.A.2031",
  "lr.required_growth.all_fees.B.2028", "lr.required_growth.all_fees.B.2029", "lr.required_growth.all_fees.B.2031",
  "lr.required_growth.all_fees.B_late.2028", "lr.required_growth.all_fees.B_late.2029",
  "lr.required_growth.all_fees.B_late.2031", "lr.required_multiple.buybacks.A.2028",
  "lr.required_multiple.buybacks.A.2029", "lr.required_multiple.buybacks.A.2031",
  "lr.required_multiple.buybacks.B.2028", "lr.required_multiple.buybacks.B.2029",
  "lr.required_multiple.buybacks.B.2031", "lr.required_multiple.buybacks.B_late.2028",
  "lr.required_multiple.buybacks.B_late.2029", "lr.required_multiple.buybacks.B_late.2031",
  "lr.required_multiple.with_front_end.A.2028", "lr.required_multiple.with_front_end.A.2029",
  "lr.required_multiple.with_front_end.A.2031", "lr.required_multiple.with_front_end.B.2028",
  "lr.required_multiple.with_front_end.B.2029", "lr.required_multiple.with_front_end.B.2031",
  "lr.required_multiple.with_front_end.B_late.2028", "lr.required_multiple.with_front_end.B_late.2029",
  "lr.required_multiple.with_front_end.B_late.2031", "lr.required_multiple.all_fees.A.2028",
  "lr.required_multiple.all_fees.A.2029", "lr.required_multiple.all_fees.A.2031",
  "lr.required_multiple.all_fees.B.2028", "lr.required_multiple.all_fees.B.2029",
  "lr.required_multiple.all_fees.B.2031", "lr.required_multiple.all_fees.B_late.2028",
  "lr.required_multiple.all_fees.B_late.2029", "lr.required_multiple.all_fees.B_late.2031",
];

const QUERIES = {
  p1: { sentence: "Each link's value, signatures and history, read at the locked end block.",
    query: "python scripts/control_map.py --verify\npython scripts/control_history.py --verify\n" +
      "RPC at the end block: view_account and view_access_key_list of each account; call_function " +
      "get_policy (Sputnik DAOs), get_num_confirmations (multisigs), fee and acl_get_grantees " +
      "(intents.near), get_reward_fee_fraction (nearai.pool.near), EXPERIMENTAL_protocol_config, validators",
    files: "data/control_map.json · data/control_history.json · data/raw/control/" },
  p2: { sentence: "The bars are what the wallets keep; the dashed marks are what is issued.",
    query: "python scripts/coverage.py --verify\nRPC at the first block of each month (00:00 UTC): " +
      "block → header total_supply; view_account of buybacks.multisignature.near, " +
      "1csfundsadmin.sputnik-dao.near and fefundsadmin.sputnik-dao.near",
    files: "data/coverage_monthly.json · numbers.json keys f1.coverage_buybacks.*" },
  p3: { sentence: "Even all fees, converted to NEAR at each day's price, stay below issuance.",
    query: "python scripts/fees.py --verify data/fees_2026-10-02_2026-11-01.json\n" +
      "DefiLlama: NEAR Intents daily fees and revenue; coins.llama.fi: daily NEAR price. " +
      "Issuance and wallets as in the chart above.",
    files: "numbers.json keys f2.fees_near_per_day.*, f2.wallets_kept_near_per_day.*, f2.take_rate.*" },
  p3b: { sentence: "Each step uses only figures already in numbers.json; the calculator re-runs the same formula in your browser.",
    query: "python scripts/build_numbers.py --verify\nKeys: n1.coverage_buybacks, n1.coverage_with_front_end, " +
      "n2.max_coverage, n2.hsp029_max_coverage, iv.hsp029_fees_multiple, n2.hsp029_equilibrium_price_usd; " +
      "calculator inputs n2.fees_usd_per_day, n1.new_near_per_day, iv.fees_conversion_price_usd, " +
      "iv.wallets_share_of_fees_with_front_end. HSP-029's target rate is issuance × 16/25.",
    files: "data/numbers.json" },
  p3c: { sentence: "Issuance follows protocol rules step by step; the bars do not depend on any price.",
    query: "python scripts/build_numbers.py --verify   # runs scripts/longrun.py\n" +
      "Rules: today at most 1/40 of supply a year; HSP-029 cap(t) = 2.5% - 0.9% x min(t, 24) / 24, t in months from " +
      "activation, every epoch. Held at the window's level: actual / maximum issuance (lr.k), epoch length " +
      "(lr.epoch_days), NEAR kept a day. Cross-check with the proposal: lr.not_issued_B_vs_proposal.*",
    files: "data/numbers.json keys lr.* · scripts/longrun.py · docs/DETAILS.md#issuance-to-2031" },
  p4: { sentence: "More accounts joined, but one account still holds most of the farm.",
    query: "python scripts/stakers.py --verify\nNearBlocks: receipts of stake to stake.dao (the list of " +
      "accounts); RPC call_function stake.dao get_farm_position for every account at each date's first block",
    files: "data/stakers/ · numbers.json keys f5.*" },
  p5: { sentence: "Two falls, in April and May; otherwise the balance only grows by its reward.",
    query: "python scripts/treasury_spend.py --verify\npython scripts/treasury_exits.py --verify\n" +
      "RPC view_account treasury.near at every epoch start; block → header total_supply",
    files: "data/treasury_spend.json · data/treasury_exits.json" },
  p6: { sentence: "Validators decide when a passed vote becomes a rule; a few voters held enough veNEAR to reach the quorum.",
    query: "python scripts/upgrade_watch.py --verify\npython scripts/hsp029_voters.py --verify\n" +
      "RPC block (latest_protocol_version of sampled blocks), validators, EXPERIMENTAL_protocol_config; " +
      "vote.dao get_proposal and the vote events of proposal 29",
    files: "data/upgrade_watch.csv · data/hsp029_voters.json" },
  p7: { sentence: "Each prediction's rule was fixed and anchored before its judging date.",
    query: "python scripts/check_prereg.py --verify\nRPC call_function social.near get " +
      "{\"keys\":[\"samerice7976.near/thesis/prereg/1/**\"]}; tx; block",
    files: "PREREG.md · PREREG-2.md · data/prereg.json" },
};

const PREDICTIONS = [
  { n: "1", text: "The largest account keeps at least 70% of the NEAR AI farm", rule: "share ≥ 0.70",
    base: "n3.largest_share", when: "judged 16 November" },
  { n: "2", text: "Net inflows to the buybacks wallet, 1–15 November, stay below a quarter of new supply",
    rule: "ratio < 0.25", base: "n1.coverage_buybacks", when: "judged 16 November" },
  { n: "3", text: "Fewer than 150 accounts are active in the NEAR AI farm", rule: "count < 150",
    base: "n3.stakers_active", when: "judged 16 November" },
  { n: "4", text: "Protocol version 87 (HSP-027) is in effect on NEAR mainnet", rule: "protocol_version ≥ 87",
    prob: "0.85", when: "judged 6 November" },
  { n: "5", text: "Protocol version 88 is in effect on NEAR mainnet", rule: "protocol_version ≥ 88",
    prob: "0.75", when: "judged 8 November" },
];

const COMMANDS = [
  "python -m unittest discover -s tests",
  "python scripts/build_numbers.py --verify",
  "python scripts/build_numbers.py --check README.md",
  "python scripts/check_prereg.py --file",
];

// ---------------------------------------------------------------- helpers
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const NS = "http://www.w3.org/2000/svg";
let N = {};

function txt(key) {
  const it = N[key];
  return it && it.text != null ? it.text : "—";
}
function val(key) {
  const it = N[key];
  return it && it.value != null ? Number(it.value) : NaN;
}
function fmtInt(v) { return Math.round(v).toLocaleString("en-US"); }
function fmtAxis(v) {
  if (Math.abs(v) >= MILLION) return (v / MILLION).toLocaleString("en-US", { maximumFractionDigits: 1 }) + "M";
  if (Math.abs(v) >= THOUSAND) return (v / THOUSAND).toLocaleString("en-US", { maximumFractionDigits: 0 }) + "K";
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
}
function fmtPct(v, d = 0) { return (v * 100).toFixed(d) + "%"; }
function monthLabel(ym) { const [y, m] = ym.split("-"); return MONTHS[Number(m) - 1]; }
function dayLabel(ymd) { const [y, m, d] = ymd.split("-"); return Number(d) + " " + MONTHS[Number(m) - 1]; }
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function svgText(parent, x, y, s, attrs = {}) { const t = el("text", { x, y, ...attrs }, parent); t.textContent = s; return t; }
function niceMax(v) {
  const p = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}
function tip(node, html) { node.dataset.tip = html; }
// Draw at the host's own width, so text in the SVG keeps its CSS size on every screen.
function width(host) { return Math.round(Math.max(300, Math.min(host.clientWidth || 640, 900))); }

async function getJSON(p) { const r = await fetch(DATA + p); if (!r.ok) throw new Error(p); return r.json(); }
async function getText(p) { const r = await fetch(p); if (!r.ok) throw new Error(p); return r.text(); }
function parseCSV(s) {
  const [head, ...rows] = s.trim().split(/\r?\n/);
  const cols = head.split(",");
  return rows.filter(Boolean).map(r => Object.fromEntries(r.split(",").map((v, i) => [cols[i], v])));
}
function bytesToText(arr) { return new TextDecoder().decode(new Uint8Array(arr)); }

// ---------------------------------------------------------------- chart primitives
// Vertical bars: cats = labels; stacks = [{name, cls, values}] drawn bottom-up; marks = optional
// reference value per category (dashed tick); labels = optional text above each stack.
function barChart(host, { title, cats, stacks, marks, markName, labels, unit, tips, grouped }) {
  const W = width(host), H = 260, L = 52, R = 10, T = 22, B = 30;
  const totals = cats.map((_, i) => grouped ? Math.max(...stacks.map(s => s.values[i])) :
    stacks.reduce((a, s) => a + s.values[i], 0));
  const top = niceMax(Math.max(...totals, ...(marks || [0])) * 1.08);
  const y = v => T + (H - T - B) * (1 - v / top);
  if (title) { const p = document.createElement("p"); p.className = "ttl"; p.textContent = title; host.appendChild(p); }
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": title || "" }, host);
  for (let k = 0; k <= 4; k++) {
    const v = top * k / 4, yy = y(v);
    el("line", { x1: L, x2: W - R, y1: yy, y2: yy, class: k ? "gridl" : "axis" }, svg);
    svgText(svg, L - 6, yy + 4, fmtAxis(v), { "text-anchor": "end" });
  }
  const band = (W - L - R) / cats.length, bw = Math.min(46, band * (grouped ? 0.34 : 0.56));
  cats.forEach((c, i) => {
    const cx = L + band * (i + 0.5);
    svgText(svg, cx, H - 10, c, { "text-anchor": "middle" });
    let acc = 0;
    stacks.forEach((s, j) => {
      const v = s.values[i];
      let x0 = cx - bw / 2, base = acc;
      if (grouped) { x0 = cx - bw + j * bw + (j ? 1 : -1); base = 0; }
      const y1 = y(base + v), y0 = y(base) - (grouped || j === 0 ? 0 : 2);
      const h = Math.max(0, y0 - y1);
      if (h <= 0) { if (!grouped) acc += v; return; }
      const r = Math.min(4, h / 2);
      const isTop = grouped || j === stacks.length - 1;
      const path = isTop
        ? `M${x0},${y0}V${y1 + r}Q${x0},${y1} ${x0 + r},${y1}H${x0 + bw - r}Q${x0 + bw},${y1} ${x0 + bw},${y1 + r}V${y0}Z`
        : `M${x0},${y0}V${y1}H${x0 + bw}V${y0}Z`;
      el("path", { d: path, class: s.cls }, svg);
      if (!grouped) acc += v;
    });
    if (marks) {
      const my = y(marks[i]);
      el("line", { x1: cx - band * 0.42, x2: cx + band * 0.42, y1: my, y2: my, class: "ref" }, svg);
    }
    if (labels) svgText(svg, cx, y(totals[i]) - 6, labels[i], { "text-anchor": "middle", class: "val" });
    const hit = el("rect", { x: cx - band / 2, y: T, width: band, height: H - T - B, class: "hit" }, svg);
    tip(hit, tips[i]);
  });
  const lg = document.createElement("div"); lg.className = "legend";
  lg.innerHTML = stacks.map(s => `<span><i class="sw-${s.cls}"></i>${s.name}</span>`).join("") +
    (marks ? `<span><i class="line"></i>${markName}</span>` : "") + (unit ? `<span>${unit}</span>` : "");
  host.appendChild(lg);
  $$(".legend i[class^='sw-']", host).forEach(i => { i.style.background = `var(--series-${i.className.slice(-1)})`; });
}

// Line with dots: xs labels, ys values, y range [0, top]; refs = [{v, name}].
function lineChart(host, { title, xs, ys, top, refs, fmt, tips, unit, height, last }) {
  const W = width(host), H = height || 220, L = 46, R = 16, T = 18, B = 30;
  const y = v => T + (H - T - B) * (1 - v / top);
  const x = i => xs.length === 1 ? (L + W - R) / 2 : L + (W - L - R) * i / (xs.length - 1);
  if (title) { const p = document.createElement("p"); p.className = "ttl"; p.textContent = title; host.appendChild(p); }
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": title || "" }, host);
  for (let k = 0; k <= 4; k++) {
    const v = top * k / 4, yy = y(v);
    el("line", { x1: L, x2: W - R, y1: yy, y2: yy, class: k ? "gridl" : "axis" }, svg);
    svgText(svg, L - 6, yy + 4, fmt(v), { "text-anchor": "end" });
  }
  (refs || []).forEach(r => {
    el("line", { x1: L, x2: W - R, y1: y(r.v), y2: y(r.v), class: "ref" }, svg);
    svgText(svg, W - R, y(r.v) - 5, r.name, { "text-anchor": "end" });
  });
  const step = Math.ceil(xs.length / 8);
  xs.forEach((s, i) => { if (i % step === 0 || i === xs.length - 1) svgText(svg, x(i), H - 10, s, { "text-anchor": "middle" }); });
  if (ys.length > 1) el("path", { d: ys.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(""), class: "l1" }, svg);
  ys.forEach((v, i) => {
    el("circle", { cx: x(i), cy: y(v), r: 4, class: "d1" }, svg);
    const hit = el("rect", { x: x(i) - 14, y: T, width: 28, height: H - T - B, class: "hit" }, svg);
    tip(hit, tips[i]);
  });
  svgText(svg, x(ys.length - 1), y(ys[ys.length - 1]) - 9, (last || fmt)(ys[ys.length - 1]), { "text-anchor": "end", class: "val" });
  if (unit) { const lg = document.createElement("div"); lg.className = "legend"; lg.textContent = unit; host.appendChild(lg); }
}

function tableView(host, head, rows) {
  const d = document.createElement("details");
  d.innerHTML = `<summary>Table</summary><div class="tablewrap"><table><thead><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  host.appendChild(d);
}

// ---------------------------------------------------------------- sections
function fillNumbers() {
  $$("[data-n]").forEach(e => { e.textContent = txt(e.dataset.n); });
}

function fillMeta() {
  $$("[data-meta]").forEach(host => {
    const q = QUERIES[host.dataset.meta];
    if (!q) return;
    const d = document.createElement("details");
    d.innerHTML = `<summary>Query</summary><pre></pre>`;
    $("pre", d).textContent = q.query;
    const s = document.createElement("p"); s.className = "src";
    s.textContent = q.sentence + " Source: " + q.files + ".";
    host.prepend(d); host.prepend(s);
  });
  $("#cmds").textContent = COMMANDS.join("\n");
}

function status(doc) {
  const w = doc.window;
  const prov = (doc.provisional_or_pending || []).length;
  $("#status").textContent = `Window ${w.start} → ${w.end} (00:00 UTC), blocks ${fmtInt(w.start_block)} → ` +
    `${fmtInt(w.end_block)}. ` + (prov ? `DefiLlama-based figures are provisional (${prov} keys).` : "Every on-chain and DefiLlama figure is final for this window.");
}

function chartCoverage(cov) {
  const rows = cov.rows;
  const cats = rows.map(r => monthLabel(r.month));
  const bb = rows.map(r => Number(r.buybacks_per_day)), fe = rows.map(r => Number(r.fefunds_per_day));
  const iss = rows.map(r => Number(r.new_supply_per_day));
  const host = $("#c2");
  barChart(host, {
    cats, marks: iss, markName: "NEAR issued per day",
    stacks: [{ name: "Buybacks wallets", cls: "s1", values: bb }, { name: "Front-end fund", cls: "s2", values: fe }],
    labels: rows.map(r => txt("f1.coverage_buybacks." + r.month)), unit: "NEAR per day · label: coverage by the buybacks wallets",
    tips: rows.map((r, i) => `<b>${cats[i]}</b><br>Buybacks wallets ${fmtInt(bb[i])} NEAR/day<br>Front-end fund ${fmtInt(fe[i])}<br>Issued ${fmtInt(iss[i])}<br>Coverage ${txt("f1.coverage_buybacks." + r.month)} · with the fund ${txt("f1.coverage_with_front_end." + r.month)}`),
  });
  tableView(host, ["Month", "Buybacks wallets", "Front-end fund", "Issued", "Coverage", "With the fund"],
    rows.map((r, i) => [r.month, fmtInt(bb[i]), fmtInt(fe[i]), fmtInt(iss[i]), txt("f1.coverage_buybacks." + r.month), txt("f1.coverage_with_front_end." + r.month)]));
}

function chartHistory(hist) {
  const host = $("#c2");
  const d = document.createElement("div"); d.className = "chart"; d.style.marginTop = "18px"; host.appendChild(d);
  const xs = hist.map(r => dayLabel(r.date)), ys = hist.map(r => Number(r.coverage_buybacks));
  lineChart(d, {
    title: "Rolling 30 days, one point a day (updated every day by the daily workflow)", xs, ys,
    top: niceMax(Math.max(...ys) * 1.6), fmt: v => fmtPct(v, 0), last: v => fmtPct(v, 1), height: 180,
    tips: hist.map(r => `<b>${r.window_start} → ${r.date}</b><br>Coverage ${fmtPct(Number(r.coverage_buybacks), 1)}<br>With the fund ${fmtPct(Number(r.coverage_with_fe), 1)}`),
  });
}

function chartCeiling(cov) {
  const months = cov.rows.map(r => r.month).filter(m => N["f2.fees_near_per_day." + m] && N["f2.wallets_kept_near_per_day." + m]);
  const iss = Object.fromEntries(cov.rows.map(r => [r.month, Number(r.new_supply_per_day)]));
  const fees = months.map(m => val("f2.fees_near_per_day." + m)), kept = months.map(m => val("f2.wallets_kept_near_per_day." + m));
  const host = $("#c3");
  barChart(host, {
    cats: months.map(monthLabel), grouped: true, marks: months.map(m => iss[m]), markName: "NEAR issued per day",
    stacks: [{ name: "All fees, in NEAR", cls: "s3", values: fees }, { name: "Kept by the wallets", cls: "s1", values: kept }],
    unit: "NEAR per day",
    tips: months.map((m, i) => `<b>${monthLabel(m)}</b><br>All fees ${fmtInt(fees[i])} NEAR/day<br>Kept by the wallets ${fmtInt(kept[i])}<br>Issued ${fmtInt(iss[m])}<br>Take rate ${txt("f2.take_rate." + m)} · mean price ${txt("f2.mean_price_usd." + m)}`),
  });
  tableView(host, ["Month", "All fees (NEAR/day)", "Kept by the wallets", "Issued", "Take rate", "Mean price"],
    months.map((m, i) => [m, fmtInt(fees[i]), fmtInt(kept[i]), fmtInt(iss[m]), txt("f2.take_rate." + m), txt("f2.mean_price_usd." + m)]));
}

function chartFarm() {
  const dates = Object.keys(N).filter(k => k.startsWith("f5.stakers_active.")).map(k => k.split(".").pop()).sort();
  const act = dates.map(d => val("f5.stakers_active." + d)), share = dates.map(d => val("f5.largest_share." + d));
  barChart($("#c4a"), {
    title: "Active accounts", cats: dates.map(dayLabel), stacks: [{ name: "Active accounts", cls: "s1", values: act }],
    labels: dates.map(d => txt("f5.stakers_active." + d)),
    tips: dates.map((d, i) => `<b>${d}</b><br>${fmtInt(act[i])} active accounts`),
  });
  lineChart($("#c4b"), {
    title: "Largest account's share of the farm", xs: dates.map(dayLabel), ys: share, top: 1,
    refs: [{ v: 0.5, name: "half: condition (c)" }], fmt: v => fmtPct(v, 0), last: v => fmtPct(v, 1), height: 260,
    tips: dates.map((d, i) => `<b>${d}</b><br>Largest account ${txt("f5.largest_share." + d)}` +
      (d > "2026-09-15" && d <= "2026-10-01" ? `<br>Credits rate ${txt("f6.change1.ratio")} on ${txt("f6.change1.utc")}` : "")),
  });
  tableView($("#c4b"), ["Date", "Active accounts", "Largest share", "Units per NEAR a year"],
    dates.map((d, i) => [d, fmtInt(act[i]), txt("f5.largest_share." + d), txt("f6.units_per_near_year." + d)]));
}

function chartTreasury(ts) {
  const m = ts.results.months;
  const bal = m.map(r => Number(r.balance_end_near));
  const host = $("#c5");
  barChart(host, {
    cats: m.map(r => monthLabel(r.start.slice(0, 7))), stacks: [{ name: "Balance at month end", cls: "s1", values: bal }],
    unit: "NEAR",
    tips: m.map((r, i) => `<b>${monthLabel(r.start.slice(0, 7))}</b><br>Balance ${fmtInt(bal[i])} NEAR<br>Reward received ${fmtInt(Number(r.treasury_in_near))}<br>Other change ${fmtInt(Number(r.other_net_near))}`),
  });
  tableView(host, ["Month", "Reward received", "Other change", "Balance at end"],
    m.map((r, i) => [r.start.slice(0, 7), fmtInt(Number(r.treasury_in_near)), fmtInt(Number(r.other_net_near)), fmtInt(bal[i])]));
}

function chartUpgrade(rows) {
  const host = $("#c6a");
  const thr = rows.length ? rows[rows.length - 1].threshold.split("/").map(Number) : [4, 5];
  const target = rows.length ? rows[rows.length - 1].target_version : "";
  lineChart(host, {
    title: `Stake signalling protocol version ${target} (HSP-027)`, xs: rows.map(r => dayLabel(r.date)),
    ys: rows.map(r => Number(r.signaling_share)), top: 1, refs: [{ v: thr[0] / thr[1], name: "threshold " + thr.join("/") }],
    fmt: v => fmtPct(v, 0), last: v => fmtPct(v, 1), height: 260,
    tips: rows.map(r => `<b>${r.utc.slice(0, 16).replace("T", " ")} UTC</b><br>Signalling ${fmtPct(Number(r.signaling_share), 1)}<br>Version in effect ${r.protocol_version}<br>Producers seen ${fmtPct(Number(r.seen_share), 1)} of stake`),
  });
  tableView(host, ["Date", "In effect", "Signalling", "Producers seen"],
    rows.map(r => [r.date, r.protocol_version, fmtPct(Number(r.signaling_share), 1), fmtPct(Number(r.seen_share), 1)]));
}

function chartVoters(vd) {
  const host = $("#c6b");
  const vs = vd.voters.map(v => Number(v.venear)).sort((a, b) => b - a);
  const total = vs.reduce((a, b) => a + b, 0);
  const k = val("f8.fewest_voters_reaching_quorum");
  const q = val("f8.quorum_required_venear");
  const W = width(host), H = 150, L = 8, R = 8, T = 40, BH = 44;
  const p = document.createElement("p"); p.className = "ttl"; p.textContent = "veNEAR of each HSP-029 voter, largest first"; host.appendChild(p);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": p.textContent }, host);
  const sx = v => L + (W - L - R) * v / total;
  let acc = 0;
  vs.forEach((v, i) => {
    const x0 = sx(acc), w = Math.max(0.5, sx(acc + v) - x0 - (i < vs.length - 1 ? 2 : 0));
    const r = el("rect", { x: x0, y: T, width: w, height: BH, rx: i === 0 || i === vs.length - 1 ? 4 : 0, class: i < k ? "s1" : "sn" }, svg);
    tip(r, `<b>Voter ${i + 1} of ${vs.length}</b><br>${fmtInt(v)} veNEAR · ${fmtPct(v / total, 1)} of votes cast`);
    acc += v;
  });
  if (q <= total) {
    const qx = sx(q);
    el("line", { x1: qx, x2: qx, y1: T - 12, y2: T + BH + 12, class: "ref" }, svg);
    svgText(svg, qx, T - 18, "quorum", { "text-anchor": "middle" });
  }
  svgText(svg, L, T + BH + 30, `${txt("f8.fewest_voters_reaching_quorum")} voters reach the quorum; the largest 8 cast ${txt("f8.top8_share_of_votes_cast")}`, {});
  const lg = document.createElement("div"); lg.className = "legend";
  lg.innerHTML = `<span><i style="background:var(--series-1)"></i>Voters that reach the quorum</span><span><i style="background:var(--neutral-mark)"></i>Other voters</span><span><i class="line"></i>Quorum</span>`;
  host.appendChild(lg);
}

// ---------------------------------------------------------------- lever model
const HSP029_FACTOR = 16 / 25;

function ladder() {
  const steps = [
    { name: "Today: the buybacks wallets", key: "n1.coverage_buybacks",
      who: `multisig ${txt("c.buybacks_confirmations")} holds it; nothing is burned · a choice` },
    { name: "+ the front-end fund", key: "n1.coverage_with_front_end",
      who: `its DAO: transfers ${txt("c.front_end_transfer")}, rules ${txt("c.front_end_rules")} · a choice` },
    { name: "+ every fee kept by NEAR", key: "n2.max_coverage",
      who: `the distribution channels, off-chain; or the protocol fee, DAO ${txt("c.intents_fee_change")} · a choice` },
    { name: "+ HSP-029 at the end of its ramp", key: "n2.hsp029_max_coverage", rule: true,
      who: `validators with ${txt("c.issuance_upgrade_stake_threshold")} of stake, at least ${txt("c.issuance_validators_to_pass_upgrade")} of them · a rule once they run it` },
  ];
  const host = $("#ladder");
  host.innerHTML = steps.map(s => {
    const v = Math.min(1, val(s.key));
    return `<div class="step"><span class="nm">${s.name}</span>` +
      `<div class="track" data-tip="<b>${s.name}</b><br>coverage ${txt(s.key)}"><div class="fill ${s.rule ? "rule" : "choice"}" style="width:${(v * 100).toFixed(2)}%"></div>` +
      `<span class="v" style="left:calc(${(v * 100).toFixed(2)}% + 8px)">${txt(s.key)}</span><span class="full"></span></div>` +
      `<span class="who">${s.who}</span></div>`;
  }).join("") +
    `<p class="end">Dashed line: full coverage. After the last step, fees must still grow ${txt("iv.hsp029_fees_multiple")}, ` +
    `or the NEAR price be at or below ${txt("n2.hsp029_equilibrium_price_usd")}. HSP-029 reaches its target rate after a ` +
    `24-month ramp; year by year to 2031 in the next section.</p>`;
}

function chartTo2031() {
  const years = ["2028", "2029", "2031"];
  const isA = years.map(y => val("lr.issuance_per_day.A." + y)), isB = years.map(y => val("lr.issuance_per_day.B." + y));
  const kept = val("n1.buybacks_near_per_day");
  const host = $("#c3c");
  barChart(host, {
    cats: years, grouped: true, marks: years.map(() => kept), markName: "kept by the buybacks wallets a day today",
    stacks: [{ name: "Issued a day, today's rule", cls: "s3", values: isA }, { name: "Issued a day, HSP-029", cls: "s1", values: isB }],
    unit: "NEAR per day, on the first day of each year",
    tips: years.map((y, i) => `<b>${y}</b><br>Issued a day: ${txt("lr.issuance_per_day.A." + y)} (today's rule), ` +
      `${txt("lr.issuance_per_day.B." + y)} (HSP-029)<br>What the buybacks wallets keep must grow ${txt("lr.required_growth.buybacks.B." + y)} ` +
      `a year (HSP-029), ${txt("lr.required_growth.buybacks.A." + y)} (today's rule); with the front-end fund ` +
      `${txt("lr.required_growth.with_front_end.B." + y)} / ${txt("lr.required_growth.with_front_end.A." + y)}`),
  });
  const g = (c, p, y) => `${txt(`lr.required_growth.${c}.${p}.${y}`)} (${txt(`lr.required_multiple.${c}.${p}.${y}`)})`;
  tableView(host, ["First day of", "Issued a day: today's rule / HSP-029", "Buybacks wallets must grow a year: today / HSP-029",
    "With the front-end fund", "All fees in NEAR", "HSP-029 six months late, with the fund"],
    years.map(y => [y, `${txt("lr.issuance_per_day.A." + y)} / ${txt("lr.issuance_per_day.B." + y)}`,
      `${g("buybacks", "A", y)} / ${g("buybacks", "B", y)}`, `${g("with_front_end", "A", y)} / ${g("with_front_end", "B", y)}`,
      `${g("all_fees", "A", y)} / ${g("all_fees", "B", y)}`, g("with_front_end", "B_late", y)]));
}

function calculator() {
  const feesUsd = val("n2.fees_usd_per_day"), issued = val("n1.new_near_per_day");
  const p0 = val("iv.fees_conversion_price_usd"), k0 = val("iv.wallets_share_of_fees_with_front_end");
  const coverage = (g, k, p, f) => feesUsd * g * k / p / (issued * f);
  const breakEven = (g, k, f) => feesUsd * g * k / (issued * f);
  const host = $("#calc");
  host.innerHTML = `
    <label>Share of all fees kept by NEAR's wallets <b id="kv"></b><input id="k" type="range" min="0" max="1" step="any"></label>
    <label>Growth of fees (in dollars) <b id="gv"></b><input id="g" type="range" min="0.5" max="10" step="0.1"></label>
    <label>NEAR price <b id="pv"></b><input id="p" type="range" min="0.5" max="15" step="any"></label>
    <label>Issuance <b id="fv"></b><select id="f"><option value="1">today's rate</option><option value="hsp">HSP-029 target (× 16/25)</option></select></label>
    <div class="out"><div class="big" id="cv"></div><div class="row" id="cx"></div><div class="chk" id="ck"></div></div>
    <button type="button" class="reset" id="reset">Back to today's values</button>`;
  const k = $("#k"), g = $("#g"), p = $("#p"), f = $("#f");
  const reset = () => { k.value = k0; g.value = 1; p.value = p0; f.value = "1"; draw(); };
  const draw = () => {
    const kk = Number(k.value), gg = Number(g.value), pp = Number(p.value), ff = f.value === "hsp" ? HSP029_FACTOR : 1;
    $("#kv").textContent = fmtPct(kk, 1) + (Math.abs(kk - k0) < 0.005 ? ` (today, with the front-end fund: ${txt("iv.wallets_share_of_fees_with_front_end")})` : "");
    $("#gv").textContent = "×" + gg.toFixed(1);
    $("#pv").textContent = "$" + pp.toFixed(2) + (Math.abs(pp - p0) < 0.005 ? ` (each day's fees at that day's price: ${txt("iv.fees_conversion_price_usd")})` : "");
    $("#fv").textContent = ff === 1 ? txt("iv.issuance_rate_per_year") + " a year" : "× 16/25";
    const c = coverage(gg, kk, pp, ff);
    $("#cv").textContent = "Coverage " + fmtPct(c, 1);
    $("#cx").innerHTML = `<span>${c >= 1 ? "✓ covers issuance" : "needs ×" + (1 / c).toFixed(1) + " more to cover issuance"}</span>` +
      `<span>covers issuance at a NEAR price of $${breakEven(gg, kk, ff).toFixed(2)} or less</span>`;
  };
  [k, g, p, f].forEach(x => x.addEventListener("input", draw));
  $("#reset").addEventListener("click", reset);
  reset();
  // Self-check: the formula at today's values reproduces numbers.json.
  const checks = [
    [fmtPct(coverage(1, 1, p0, 1), 1), txt("n2.max_coverage")],
    [fmtPct(coverage(1, 1, p0, HSP029_FACTOR), 1), txt("n2.hsp029_max_coverage")],
    ["$" + breakEven(1, 1, 1).toFixed(2), txt("n2.equilibrium_price_usd")],
    ["$" + breakEven(1, 1, HSP029_FACTOR).toFixed(2), txt("n2.hsp029_equilibrium_price_usd")],
    [fmtPct(coverage(1, k0, p0, 1), 1), txt("n1.coverage_with_front_end")],
  ];
  const ok = checks.every(([a, b]) => a === b);
  $("#ck").textContent = (ok ? "✓ " : "✗ ") + "At today's values the formula gives " + checks.map(c => c[0]).join(", ") +
    (ok ? ": the same as numbers.json." : "; numbers.json says " + checks.map(c => c[1]).join(", ") + ".");
}

function predictions() {
  $("#preds").innerHTML = PREDICTIONS.map(p => `<div class="pred"><span class="k">Prediction ${p.n} · ${p.when}</span>` +
    `<div>${p.text}</div><div class="st">Holds if ${p.rule}` +
    (p.base ? ` · baseline ${txt(p.base)}` : "") + (p.prob ? ` · probability stated ${p.prob}` : "") + `</div></div>`).join("");
}

// ---------------------------------------------------------------- live checks
async function rpcView(account, method, args) {
  const body = { jsonrpc: "2.0", id: "dashboard", method: "query",
    params: { request_type: "call_function", finality: "final", account_id: account, method_name: method,
      args_base64: btoa(JSON.stringify(args || {})) } };
  const r = await fetch(RPC, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!j.result || !j.result.result) throw new Error("no result");
  return { text: bytesToText(j.result.result), height: j.result.block_height };
}
async function saved(path) {
  const j = await getJSON(path);
  return { text: bytesToText(j.result.result), height: j.result.block_height };
}

let FARM_PRICE = "", PREREG = null;
const LIVE = {
  fee: { label: "protocol fee", run: () => rpcView("intents.near", "fee"), saved: () => saved("raw/control/intents.near_fee.json") },
  buybacks: { label: "signatures needed", run: () => rpcView("buybacks.multisignature.near", "get_num_confirmations"),
    saved: () => saved("raw/control/buybacks.multisignature.near_get_num_confirmations.json") },
  pool: { label: "share of rewards kept", run: () => rpcView("nearai.pool.near", "get_reward_fee_fraction"),
    saved: () => saved("raw/control/nearai.pool.near_get_reward_fee_fraction.json"),
    show: t => { const f = JSON.parse(t); return `${f.numerator}/${f.denominator}`; } },
  farm: { label: "farm reward rate", run: () => rpcView("stake.dao", "get_farm_pool", { price_id: FARM_PRICE }),
    saved: () => saved(`raw/stakedao/${N.__end_block}/farm_pool.json`),
    show: t => JSON.parse(t).reward_rate },
  prereg: { label: "record contains the anchored SHA-256",
    run: () => rpcView("social.near", "get", { keys: [PREREG.key + "/**"] }),
    saved: async () => ({ text: PREREG.anchored_sha256, height: PREREG.stored_record_read_at_block }),
    compare: (live, at) => live.includes(at), show: t => t.length > 24 ? t.slice(0, 12) + "…" : t },
};

function liveButtons() {
  $$("[data-live]").forEach(card => {
    const c = LIVE[card.dataset.live];
    const box = document.createElement("div"); box.className = "live";
    box.innerHTML = `<button type="button">Check live</button><span class="res"></span>`;
    card.appendChild(box);
    $("button", box).addEventListener("click", async () => {
      const res = $(".res", box);
      res.textContent = "asking the RPC…";
      try {
        const [lv, sv] = await Promise.all([c.run(), c.saved()]);
        const show = c.show || (t => t);
        const same = c.compare ? c.compare(lv.text, sv.text) : show(lv.text) === show(sv.text);
        res.innerHTML = c.compare
          ? `live at block ${fmtInt(lv.height)}: <span class="badge ${same ? "same" : "changed"}">${same ? "✓ contains" : "✗ missing"}</span> ${show(sv.text)}`
          : `live ${c.label}: <b>${show(lv.text)}</b> · at block ${fmtInt(sv.height)}: ${show(sv.text)} · <span class="badge ${same ? "same" : "changed"}">${same ? "✓ same" : "≠ changed"}</span>`;
      } catch (e) {
        res.textContent = "could not reach the RPC from this browser";
      }
    });
  });
}

// ---------------------------------------------------------------- tooltip
function tooltips() {
  const t = $("#tip");
  document.addEventListener("pointermove", e => {
    const node = e.target.closest ? e.target.closest("[data-tip]") : null;
    if (!node) { t.hidden = true; return; }
    t.innerHTML = node.dataset.tip; t.hidden = false;
    const pad = 14, w = t.offsetWidth, h = t.offsetHeight;
    let x = e.clientX + pad, y = e.clientY + pad;
    if (x + w > innerWidth - 8) x = e.clientX - w - pad;
    if (y + h > innerHeight - 8) y = e.clientY - h - pad;
    t.style.left = x + "px"; t.style.top = y + "px";
  });
  document.addEventListener("pointerleave", () => { t.hidden = true; });
}

// ---------------------------------------------------------------- main
async function main() {
  const doc = await getJSON("numbers.json");
  N = doc.numbers;
  N.__end_block = doc.window.end_block;
  fillNumbers();
  fillMeta();
  status(doc);
  predictions();
  tooltips();
  const [cov, histTxt, upTxt, ts, vd, fp, pr] = await Promise.all([
    getJSON("coverage_monthly.json"), getText(DATA + "history.csv"), getText(DATA + "upgrade_watch.csv"),
    getJSON("treasury_spend.json"), getJSON("hsp029_voters.json"),
    getJSON(`raw/stakedao/${doc.window.end_block}/farm_pool.json`), getJSON("prereg.json")]);
  FARM_PRICE = JSON.parse(bytesToText(fp.result.result)).price_id;
  PREREG = pr;
  chartCoverage(cov);
  chartHistory(parseCSV(histTxt));
  chartCeiling(cov);
  ladder();
  calculator();
  chartTo2031();
  chartFarm();
  chartTreasury(ts);
  chartUpgrade(parseCSV(upTxt));
  chartVoters(vd);
  liveButtons();
}

main().catch(err => {
  const s = $("#status");
  s.textContent = "Could not load the data files (" + err.message + "). Serve the repository root over HTTP: " +
    "python -m http.server, then open /dashboard/.";
});
