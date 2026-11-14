/* Who wins digital payments in Bangladesh: dashboard. Reads data/payments.json written by `python -m payments`. */

const CH = { mfs: ["MFS", "#2a78d6"], ib: ["Internet banking", "#eb6834"], card: ["Cards", "#1baf7a"], ab: ["Agent banking", "#eda100"] };
const GROUPS = [
  ["Cash in and cash out", ["cash_in", "cash_out_total"], "#9aa6b8"],
  ["Person to person", ["p2p"], "#2a78d6"],
  ["Payments and inflows", ["merchant", "utility", "salary", "government", "remittance"], "#1baf7a"],
  ["Others", ["others"], "#d5dbe5"],
];
const INK = "#0f1b2d", MUTED = "#7d8aa0", LINE = "#e3e8ef";
const charts = {};
let D;

const lakh = v => (v / 1e5).toFixed(2);
const pct = (v, d = 1) => `${(v * 100).toFixed(d)}%`;
const tk = v => `Tk ${Math.round(v).toLocaleString("en-US")}`;
const mon = m => new Date(m + "-01T00:00:00").toLocaleDateString("en-GB", { month: "short", year: "numeric" });
function chart(id) { if (!charts[id]) charts[id] = echarts.init(document.getElementById(id)); return charts[id]; }
const axis = { axisLine: { lineStyle: { color: LINE } }, axisTick: { show: false }, axisLabel: { color: MUTED, fontSize: 11.5 }, splitLine: { lineStyle: { color: "#eef1f5" } } };
const base = { textStyle: { fontFamily: "Inter, sans-serif" }, grid: { left: 56, right: 120, top: 24, bottom: 30 },
               tooltip: { trigger: "axis", backgroundColor: "#fff", borderColor: LINE, textStyle: { color: INK, fontSize: 12 } } };
const kpi = (l, v, d, f) => `<div class="kpi${f ? " focus" : ""}"><div class="l">${l}</div><div class="v">${v}</div><div class="d">${d}</div></div>`;

function fyChart(id) {
  const fy = D.fy.map(r => r.fy);
  chart(id).setOption({ ...base,
    xAxis: { type: "category", data: fy.map(f => "FY" + f.slice(5)), ...axis },
    yAxis: { type: "value", ...axis },
    tooltip: { ...base.tooltip, valueFormatter: v => `Tk ${(+v).toFixed(2)} lakh crore` },
    series: Object.entries(CH).map(([k, [n, c]]) => ({ name: n, type: "line", showSymbol: false, lineStyle: { width: k === "mfs" || k === "ib" ? 3.2 : 2, color: c }, itemStyle: { color: c },
      endLabel: { show: true, formatter: p => `${n} ${p.value.toFixed(1)}`, color: INK, fontWeight: k === "ib" ? 700 : 500, fontSize: 11.5 },
      labelLayout: { moveOverlap: "shiftY" }, data: D.fy.map(r => r[`${k}_v`] / 1e5) })) }, true);
}

function renderAnswer() {
  const h = D.headline, g = h.growth;
  document.getElementById("answer-text").innerHTML =
    `<b>MFS still owns the mass market, but it is a cash rail, and the growth in payments has moved to bank apps.</b> ` +
    `Internet banking grew ${(h.ib_fy26 / h.ib_fy23).toFixed(1)} times in three years, to Tk ${lakh(h.ib_fy26)} lakh crore in FY2025-26, close to MFS at Tk ${lakh(h.mfs_fy26)} lakh crore. ` +
    `Inside MFS, cash in and cash out rose from ${pct(h.cash_share_first)} to ${pct(h.cash_share_last)} of value. An MFS that wants to keep winning has to turn its cash rail into a payments network before bank apps reach its customers.`;
  document.getElementById("kpis").innerHTML = [
    kpi("MFS value, FY2025-26", `Tk ${lakh(h.mfs_fy26)} lakh cr`, `${(h.mfs_fy26 / h.mfs_fy15).toFixed(0)} times FY2014-15`),
    kpi("Internet banking, FY2025-26", `Tk ${lakh(h.ib_fy26)} lakh cr`, `${(h.ib_fy26 / h.ib_fy23).toFixed(1)} times FY2022-23`, true),
    kpi("Cash in + cash out", pct(h.cash_share_last), `Of MFS value, up from ${pct(h.cash_share_first)}`, true),
    kpi("Merchant payment", pct(h.merchant_share_last), `Of MFS value, +${Math.round(g.merchant * 100)}% in two years`),
  ].join("");
  document.getElementById("bet1").innerHTML = `Merchant payments grew ${Math.round(g.merchant * 100)}% in two years but are still ${pct(h.merchant_share_last)} of MFS value, while cash-out grew ${Math.round(g.cash_out_total * 100)}%. Every taka that is cashed out leaves the network.`;
  document.getElementById("bet2").innerHTML = `Salary disbursement grew ${Math.round(g.salary * 100)}% and inward remittance ${Math.round(g.remittance * 100)}%. Money that arrives in a wallet is cheaper to keep digital than money that has to be cashed in.`;
  document.getElementById("bet3").innerHTML = `Internet banking customers doubled in FY2025-26, from ${(h.ib_customers_fy25 / 1e6).toFixed(1)}m to ${(h.ib_customers_fy26 / 1e6).toFixed(1)}m, and the average transaction fell from ${tk(h.ib_ticket_fy24)} to ${tk(h.ib_ticket_fy26)}. Banks are going retail.`;
  fyChart("c-fy-small");
}

function renderChannels() {
  fyChart("c-fy");
  const m = D.month;
  const gap = m.filter(r => r.nagad_missing).map(r => r.month);
  chart("c-month").setOption({ ...base,
    xAxis: { type: "category", data: m.map(r => r.month), ...axis, axisLabel: { ...axis.axisLabel, formatter: v => new Date(v + "-01T00:00:00").toLocaleDateString("en-GB", { month: "short", year: "2-digit" }) } },
    yAxis: { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: v => `${v}k` } },
    tooltip: { ...base.tooltip, valueFormatter: v => `Tk ${Math.round(+v * 1000).toLocaleString("en-US")} crore` },
    series: ["mfs", "ib", "card"].map((k, i) => ({ name: CH[k][0], type: "line", showSymbol: false, lineStyle: { width: k === "card" ? 2 : 3, color: CH[k][1] }, itemStyle: { color: CH[k][1] },
      endLabel: { show: true, formatter: CH[k][0], color: INK, fontSize: 11.5 }, data: m.map(r => r[`${k}_v`] / 1000),
      markArea: i ? undefined : { silent: true, itemStyle: { color: "rgba(214,69,69,.08)", borderColor: "#d64545", borderType: "dashed", borderWidth: 1 },
        label: { show: true, position: "insideTop", color: "#b23232", formatter: "Nagad missing", fontSize: 11 }, data: [[{ xAxis: gap[0] }, { xAxis: gap[gap.length - 1] }]] } })) }, true);
  const f = Object.fromEntries(D.fy.map(r => [r.fy, r]));
  const a = f["2022-23"], b = f["2025-26"];
  const rows = [["MFS", "mfs_v", "mfs_n"], ["Internet banking", "ib_v", "ib_n"], ["Cards", "card_v", "card_n"], ["Agent banking", "ab_v", "ab_n"]].map(([n, v, c]) =>
    `<tr><td><b>${n}</b></td><td class="n">${lakh(a[v])}</td><td class="n">${lakh(b[v])}</td><td class="n"><span class="chip ${b[v] > a[v] * 1.5 ? "g" : "n"}">${(b[v] / a[v]).toFixed(2)}x</span></td>` +
    `<td class="n">${(a[c] / 1e6).toFixed(0)}m</td><td class="n">${(b[c] / 1e6).toFixed(0)}m</td><td class="n">${(b[c] / a[c]).toFixed(2)}x</td></tr>`).join("");
  document.getElementById("t-growth").innerHTML = `<tr><th>Channel</th><th class="n">Value FY23 (lakh cr)</th><th class="n">Value FY26</th><th class="n">Growth</th><th class="n">Transactions FY23</th><th class="n">FY26</th><th class="n">Growth</th></tr>${rows}`;
}

function renderMfs() {
  const months = [...new Set(D.mix.map(r => r.month))].sort();
  chart("c-mix").setOption({ ...base, grid: { ...base.grid, right: 20, top: 40 },
    legend: { top: 0, left: 0, textStyle: { color: INK, fontSize: 12 }, itemWidth: 12, itemHeight: 10 },
    xAxis: { type: "category", data: months, ...axis, axisLabel: { ...axis.axisLabel, formatter: v => new Date(v + "-01T00:00:00").toLocaleDateString("en-GB", { month: "short", year: "2-digit" }) } },
    yAxis: { type: "value", max: 100, ...axis, axisLabel: { ...axis.axisLabel, formatter: "{value}%" } },
    tooltip: { ...base.tooltip, valueFormatter: v => `${(+v).toFixed(1)}%` },
    series: GROUPS.map(([n, keys, c]) => ({ name: n, type: "line", stack: "s", areaStyle: { color: c, opacity: .9 }, lineStyle: { width: 1, color: "#fff" }, showSymbol: false, itemStyle: { color: c },
      data: months.map(m => D.mix.filter(r => r.month === m && keys.includes(r.product)).reduce((s, r) => s + r.share, 0) * 100) })) }, true);
  const g = D.headline.growth, labels = D.meta.labels;
  const rows = Object.entries(g).filter(([k]) => k !== "others").sort((a, b) => a[1] - b[1]);
  document.getElementById("growth-hint").textContent = `${D.headline.span_first} to ${D.headline.span_last}`;
  const pay = ["merchant", "utility", "salary", "government", "remittance"];
  chart("c-pgrowth").setOption({ ...base, grid: { left: 140, right: 60, top: 10, bottom: 30 },
    xAxis: { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: "{value}%" } },
    yAxis: { type: "category", data: rows.map(([k]) => labels[k]), ...axis, axisLabel: { color: INK, fontSize: 12 } },
    tooltip: { ...base.tooltip, trigger: "item", formatter: p => `${p.name}: +${p.value.toFixed(0)}%` },
    series: [{ type: "bar", barWidth: 16, data: rows.map(([k, v]) => ({ value: v * 100, itemStyle: { color: pay.includes(k) ? "#1baf7a" : k === "p2p" ? "#2a78d6" : "#9aa6b8", borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: "right", color: INK, formatter: p => `+${p.value.toFixed(0)}%` } }] }, true);
  const spans = [...new Set(D.mix_year.map(r => r.span))].sort();
  const get = (s, p) => D.mix_year.find(r => r.span === s && r.product === p);
  const prods = [...D.meta.products].sort((a, b) => get(spans[2], b).amount - get(spans[2], a).amount);
  document.getElementById("t-mix").innerHTML = `<tr><th>Product</th>${spans.map(s => `<th class="n">${s}</th>`).join("")}<th class="n">Share, first</th><th class="n">Share, last</th><th class="n">Growth</th></tr>` +
    prods.map(p => { const a = get(spans[0], p), c = get(spans[2], p); const gr = c.amount / a.amount - 1;
      return `<tr><td>${labels[p]}</td>${spans.map(s => `<td class="n">${Math.round(get(s, p).amount).toLocaleString("en-US")}</td>`).join("")}<td class="n">${pct(a.share)}</td><td class="n"><b>${pct(c.share)}</b></td><td class="n"><span class="chip ${gr > 0.9 ? "g" : "n"}">+${Math.round(gr * 100)}%</span></td></tr>`; }).join("");
}

function renderBanks() {
  const h = D.headline;
  document.getElementById("bank-kpis").innerHTML = [
    kpi("Internet banking customers", `${(h.ib_customers_fy26 / 1e6).toFixed(1)}m`, `From ${(h.ib_customers_fy25 / 1e6).toFixed(1)}m a year earlier`, true),
    kpi("Internet banking transactions", `${(h.ib_n_fy26 / 1e6).toFixed(0)}m`, `FY2025-26; ${(h.ib_n_fy23 / 1e6).toFixed(0)}m in FY2022-23`),
    kpi("Average internet banking payment", tk(h.ib_ticket_fy26), `${tk(h.ib_ticket_fy24)} in FY2023-24`, true),
    kpi("Average MFS transaction", tk(h.mfs_ticket_fy26), "FY2025-26"),
  ].join("");
  const fy = D.fy.map(r => "FY" + r.fy.slice(5));
  chart("c-ibcust").setOption({ ...base, grid: { ...base.grid, right: 30 }, xAxis: { type: "category", data: fy, ...axis }, yAxis: { type: "value", ...axis },
    tooltip: { ...base.tooltip, valueFormatter: v => `${(+v).toFixed(1)}m` },
    series: [{ type: "bar", barWidth: 22, data: D.fy.map(r => r.ib_customers / 1e6), itemStyle: { color: CH.ib[1], borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: "top", color: INK, fontSize: 11, formatter: p => p.value.toFixed(1) } }] }, true);
  chart("c-ticket").setOption({ ...base, grid: { ...base.grid, right: 160 }, xAxis: { type: "category", data: fy, ...axis }, yAxis: { type: "log", ...axis, axisLabel: { ...axis.axisLabel, formatter: v => `Tk ${v >= 1000 ? v / 1000 + "k" : v}` } },
    tooltip: { ...base.tooltip, valueFormatter: v => tk(+v) },
    series: [["Internet banking", "ib", CH.ib[1]], ["Cards", "card", CH.card[1]], ["MFS", "mfs", CH.mfs[1]]].map(([n, k, c]) => ({ name: n, type: "line", showSymbol: false, lineStyle: { width: 3, color: c }, itemStyle: { color: c },
      endLabel: { show: true, formatter: p => `${n} ${tk(p.value)}`, color: INK, fontSize: 11.5 },
      data: D.fy.map(r => r[`${k}_n`] ? r[`${k}_v`] * 1e7 / r[`${k}_n`] : null) })) }, true);
}

function renderMarket() {
  const p = D.providers;
  const total = p.reduce((s, r) => s + r.value_lakh_crore, 0);
  chart("c-prov").setOption({ ...base, grid: { left: 80, right: 80, top: 10, bottom: 30 },
    xAxis: { type: "value", ...axis }, yAxis: { type: "category", inverse: true, data: p.map(r => r.provider), ...axis, axisLabel: { color: INK, fontSize: 12.5 } },
    tooltip: { ...base.tooltip, trigger: "item", formatter: x => `${x.name}: Tk ${x.value.toFixed(2)} lakh crore (${pct(x.value / total)})` },
    series: [{ type: "bar", barWidth: 22, data: p.map(r => ({ value: r.value_lakh_crore, itemStyle: { color: r.basis === "reported" ? CH.mfs[1] : "#9aa6b8", borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: "right", color: INK, formatter: x => pct(x.value / total, 0) } }] }, true);
  document.getElementById("prov-note").innerHTML = `bKash handled <b>${pct(p[0].value_lakh_crore / total, 0)}</b> of MFS value in April to June 2026 and Nagad ${pct(p[1].value_lakh_crore / total, 0)}. The top three handled 99.15%. A market this concentrated is decided by what the leader does next, and by whether banks can win customers it does not serve well.`;
}

const RENDER = { answer: renderAnswer, channels: renderChannels, mfs: renderMfs, banks: renderBanks, market: renderMarket, method: () => {} };
function show(tab) {
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  document.querySelectorAll(".page").forEach(p => p.classList.toggle("on", p.id === `p-${tab}`));
  RENDER[tab]();
  Object.values(charts).forEach(c => c.resize());
  if (location.hash !== `#${tab}`) history.replaceState(null, "", `#${tab}`);
}
fetch("data/payments.json").then(r => r.json()).then(d => {
  D = d;
  document.getElementById("sub").textContent = `MFS, internet banking, cards and agent banking · FY2014-15 to FY2025-26, monthly to ${mon(d.meta.channel_months[1])}`;
  document.getElementById("gen").textContent = `Data built ${d.meta.generated}`;
  document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => show(b.dataset.tab));
  const start = location.hash.slice(1);
  show(RENDER[start] ? start : "answer");
  window.addEventListener("resize", () => Object.values(charts).forEach(c => c.resize()));
});
