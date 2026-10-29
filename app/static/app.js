"use strict";

const I18N = {
  tr: {
    title: "Esenboğa düşük görüş erken uyarı", issued: "Son rasat",
    heroTitle: "Önümüzdeki 6 saatte sis olasılığı",
    heroHint: "Sütunlar kalibre edilmiş olasılığı gösterir; sis yükseldikçe yaklaşma ışıkları kaybolur. Bir sütuna tıklayınca etkili faktörler görünür.",
    nowTitle: "Şu an Esenboğa'da", ilsTitle: "ILS kategorisi görünümü (RVR)",
    ilsHint: "CAT I: RVR ≥ 550 m · CAT II: 350–550 m · CAT III: RVR < 350 m",
    whyTitle: "Tahmini belirleyen faktörler",
    whyHint: "SHAP katkıları: sağa uzanan çubuklar sis riskini artırır, sola uzananlar azaltır.",
    histTitle: "Son 48 saat: gözlem ve 3 saat önceden verilen tahmin",
    lgVis: "Görüş", lgProb: "3 sa önceki sis olasılığı",
    verTitle: "Gerçek zamanlı doğrulama",
    verHint: "Her tahmin kaydedilir ve geçerlilik saati gelince gözlemle karşılaştırılır. \"Canlı\" uygulamanın çalıştığı dönemi, \"yeniden oynatma\" ilk açılışta son 72 saatin aynı kodla yeniden üretilmesini gösterir.",
    foot: "Araştırma prototipi — operasyonel kullanım için değildir. Resmî tahminler için MGM ve TAF/TREND esas alınmalıdır. Model: kalibre edilmiş LightGBM; eğitim 2005–2019, doğrulama 2019–2022, test 2022–2026 LTAC METAR/SPECI.",
    now: "Şimdi", lead: (h) => `+${h} sa`, observed: "gözlenen görüş", thrLabel: "eşik",
    vis: "Görüş", rvr: "En düşük RVR", temp: "Sıcaklık", dew: "Çiy noktası", spread: "T − Td",
    rh: "Bağıl nem", wind: "Rüzgâr", qnh: "QNH", ceil: "Bulut tavanı", none: "yok",
    calm: "sakin", noRvr: "rapor edilmedi",
    cat1: "CAT I+", cat2: "CAT II", cat3: "CAT III",
    alerts: {
      green: ["Düşük görüş beklenmiyor", "Önümüzdeki 6 saatte sis olasılığı eşiklerin belirgin biçimde altında."],
      yellow: ["Sis riski artıyor", "Olasılık eşiklere yaklaşıyor; gelişmeyi izleyin."],
      orange: ["3–6 saat içinde sis bekleniyor", "Model ileriki saatler için uyarı eşiğini aşıyor; LVP hazırlığını gözden geçirin."],
      red: ["Sis var veya 2 saat içinde bekleniyor", "Düşük görüş prosedürleri (LVP) için hazırlıklı olun."],
    },
    whySel: (h) => `(+${h} sa)`,
    verCols: ["Mod", "Öngörü", "Tahmin", "Olay", "İsabet", "Yanlış alarm", "Kaçırma", "POD", "FAR", "CSI", "Brier"],
    live: "canlı", replay: "yeniden oynatma", noVer: "Henüz doğrulanmış tahmin yok; geçerlilik saatleri doldukça tablo dolacak.",
    loadErr: "Veri alınamadı. Sunucu çalışıyor mu? Ayrıntı: ",
  },
  en: {
    title: "Esenboğa low-visibility early warning", issued: "Latest report",
    heroTitle: "Fog probability over the next 6 hours",
    heroHint: "Columns show the calibrated probability; approach lights fade as the fog rises. Select a column to see what drives it.",
    nowTitle: "Now at Esenboğa", ilsTitle: "ILS category outlook (RVR)",
    ilsHint: "CAT I: RVR ≥ 550 m · CAT II: 350–550 m · CAT III: RVR < 350 m",
    whyTitle: "What drives the forecast",
    whyHint: "SHAP contributions: bars to the right raise the fog risk, bars to the left lower it.",
    histTitle: "Last 48 hours: observations and the forecast issued 3 h earlier",
    lgVis: "Visibility", lgProb: "Fog probability issued 3 h before",
    verTitle: "Real-time verification",
    verHint: "Every forecast is stored and compared with the observation once its valid time has passed. \"Live\" covers the period the app has been running; \"replay\" re-creates the previous 72 h with the same code at first start.",
    foot: "Research prototype — not for operational use. Official forecasts (MGM, TAF/TREND) take precedence. Model: calibrated LightGBM trained on LTAC METAR/SPECI 2005–2019, validated 2019–2022, tested 2022–2026.",
    now: "Now", lead: (h) => `+${h} h`, observed: "observed visibility", thrLabel: "threshold",
    vis: "Visibility", rvr: "Lowest RVR", temp: "Temperature", dew: "Dew point", spread: "T − Td",
    rh: "Relative humidity", wind: "Wind", qnh: "QNH", ceil: "Ceiling", none: "none",
    calm: "calm", noRvr: "not reported",
    cat1: "CAT I+", cat2: "CAT II", cat3: "CAT III",
    alerts: {
      green: ["No low visibility expected", "Fog probability stays well below the warning thresholds for the next 6 h."],
      yellow: ["Fog risk is rising", "Probabilities are approaching the thresholds; keep monitoring."],
      orange: ["Fog expected in 3–6 h", "The model exceeds its warning threshold later in the period; review LVP readiness."],
      red: ["Fog now or expected within 2 h", "Be ready for low-visibility procedures (LVP)."],
    },
    whySel: (h) => `(+${h} h)`,
    verCols: ["Mode", "Lead", "Forecasts", "Events", "Hits", "False alarms", "Misses", "POD", "FAR", "CSI", "Brier"],
    live: "live", replay: "replay", noVer: "No verified forecasts yet; the table fills as valid times pass.",
    loadErr: "Could not load data. Is the server running? Details: ",
  },
};

const URL_LANG = new URLSearchParams(location.search).get("lang");
let LANG = ["tr", "en"].includes(URL_LANG) ? URL_LANG : (localStorageGet("ltac-lang") || "tr");
let DATA = null;
let SELECTED = 3;
let LOG = [];
let VER = [];

function localStorageGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function localStorageSet(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } }
const t = (k) => I18N[LANG][k];
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (ch) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
const fmt = (x, d = 0) => (x === null || x === undefined || Number.isNaN(x) ? "–" : Number(x).toFixed(d));

function visText(v) {
  if (v === null || v === undefined) return "–";
  if (v >= 10000) return "≥10 km";
  return v >= 5000 ? `${(v / 1000).toFixed(0)} km` : `${Math.round(v)} m`;
}

function applyStatic() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const v = I18N[LANG][el.dataset.i18n];
    if (typeof v === "string") el.textContent = v;
  });
  document.querySelectorAll(".lang button").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.lang === LANG)));
  document.title = LANG === "tr" ? "LTAC Sis Erken Uyarı" : "LTAC Fog Early Warning";
}

// ------------------------------------------------------------------ hero
function renderLights() {
  const wrap = $("lights");
  wrap.innerHTML = "";
  const c = DATA.conditions;
  const cols = [{ h: 0 }].concat(Object.keys(DATA.fog).map((h) => ({ h: Number(h), ...DATA.fog[h] })));
  for (const col of cols) {
    const el = document.createElement("button");
    el.type = "button";
    el.setAttribute("role", "listitem");
    const isNow = col.h === 0;
    const p = isNow ? (c.fog_now ? 1 : Math.max(0, Math.min(1, 1 - Math.log10(Math.max(c.vis_m, 100)) / 4 + 0.05))) : col.p;
    el.className = "col" + (isNow ? " now" : "") + (!isNow && col.warn ? " warn" : "");
    el.setAttribute("aria-pressed", String(col.h === SELECTED));
    const lamps = 5;
    const lit = Math.round(lamps * (1 - Math.min(1, p * 1.25)));
    el.innerHTML = `
      <span class="lead">${isNow ? t("now") : t("lead")(col.h)}</span>
      <span class="pct">${isNow ? visText(c.vis_m) : Math.round(col.p * 100) + "%"}</span>
      <span class="tank">
        <span class="fogfill" style="height:${(p * 100).toFixed(1)}%"></span>
        ${isNow ? "" : `<span class="thr" style="bottom:${(col.threshold * 100).toFixed(1)}%"><span>${t("thrLabel")} ${Math.round(col.threshold * 100)}%</span></span>`}
      </span>
      <span class="lamps" aria-hidden="true">${Array.from({ length: lamps }, (_, i) =>
        `<span class="lamp" style="opacity:${i < lit ? 1 : 0.12}"></span>`).join("")}</span>`;
    el.setAttribute("aria-label", isNow ? `${t("now")}: ${t("observed")} ${visText(c.vis_m)}`
      : `${t("lead")(col.h)}: ${Math.round(col.p * 100)}%`);
    if (!isNow) el.addEventListener("click", () => { SELECTED = col.h; renderLights(); renderWhy(); });
    wrap.appendChild(el);
  }
}

// ------------------------------------------------------------------ alert, now, ILS
function renderAlert() {
  const [title, text] = t("alerts")[DATA.alert];
  $("alert").dataset.level = DATA.alert;
  $("alert-title").textContent = title;
  $("alert-text").textContent = text;
}

function renderNow() {
  const c = DATA.conditions;
  const wind = c.wind_speed_kt === null ? "–" : c.wind_speed_kt <= 0.5 ? t("calm")
    : `${c.wind_dir === null ? "VRB" : String(Math.round(c.wind_dir)).padStart(3, "0") + "°"} ${fmt(c.wind_speed_kt)} kt`;
  const items = [
    [t("vis"), visText(c.vis_m)],
    [t("rvr"), c.rvr_min_m === null ? t("noRvr") : `${Math.round(c.rvr_min_m)} m`],
    [t("spread"), `${fmt(c.dpd_c, 0)} °C`],
    [t("temp"), `${fmt(c.temp_c, 0)} °C`],
    [t("dew"), `${fmt(c.dewpt_c, 0)} °C`],
    [t("rh"), `${fmt(c.rh_pct, 0)} %`],
    [t("wind"), wind],
    [t("qnh"), `${fmt(c.qnh_hpa, 0)} hPa`],
    [t("ceil"), c.ceiling_ft === null || c.ceiling_ft > 20000 ? t("none") : `${Math.round(c.ceiling_ft)} ft`],
  ];
  $("now").innerHTML = items.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
  $("raw").textContent = c.raw;
}

function renderIls() {
  const rows = Object.keys(DATA.rvr).map((h) => {
    const r = DATA.rvr[h];
    const seg = (cls, p, name) => `<span class="${cls}" style="width:${(p * 100).toFixed(1)}%" title="${name} ${(p * 100).toFixed(1)}%">${p >= 0.08 ? Math.round(p * 100) + "%" : ""}</span>`;
    return `<div class="row"><b>${t("lead")(h)}</b><div class="bar" role="img" aria-label="${t("cat1")} ${Math.round(r.p_cat1 * 100)}%, ${t("cat2")} ${Math.round(r.p_cat2 * 100)}%, ${t("cat3")} ${Math.round(r.p_cat3 * 100)}%">${seg("c1", r.p_cat1, t("cat1"))}${seg("c2", r.p_cat2, t("cat2"))}${seg("c3", r.p_cat3, t("cat3"))}</div></div>`;
  });
  $("ils").innerHTML = rows.join("") +
    `<div class="key"><span><i style="background:var(--green)"></i>${t("cat1")}</span><span><i style="background:var(--orange)"></i>${t("cat2")}</span><span><i style="background:var(--red)"></i>${t("cat3")}</span></div>`;
}

// ------------------------------------------------------------------ explanation
function featureValue(name, x) {
  if (x === null || x === undefined) return "–";
  if (name.startsWith("wx_") || ["fog_now", "calm", "cavok", "low_cloud", "is_night", "vt_is_night", "vv_reported", "recent_precip"].includes(name))
    return x >= 0.5 ? (LANG === "tr" ? "evet" : "yes") : (LANG === "tr" ? "hayır" : "no");
  if (name === "rvr_eff_m") return x >= 2000 ? "≥2000 m" : `${Math.round(x)} m`;
  if (name.includes("vis") && !name.startsWith("dlog") && name !== "log_vis") return visText(x);
  if (name === "log_vis") return visText(10 ** x);
  if (name.includes("frac")) return `${Math.round(x * 100)}%`;
  if (name.endsWith("_c") || name.startsWith("dT") || name.startsWith("ddpd") || name === "T_minus_max12h") return `${x.toFixed(1)} °C`;
  if (name.includes("rh")) return `${x.toFixed(0)}%`;
  if (name.includes("wind") && !name.endsWith("_u") && !name.endsWith("_v")) return `${x.toFixed(0)} kt`;
  if (name.includes("solar_elev")) return `${x.toFixed(0)}°`;
  if (name.startsWith("h_") || name.startsWith("vt_h_") || name === "night_len_h") return `${x.toFixed(1)} h`;
  return x.toFixed(2);
}

function renderWhy() {
  const list = DATA.shap[SELECTED] || [];
  $("why-h-sel").textContent = t("whySel")(SELECTED);
  const max = Math.max(...list.map((d) => Math.abs(d.value)), 1e-6);
  $("why").innerHTML = list.map((d) => {
    const w = (Math.abs(d.value) / max) * 50;
    const name = esc((DATA.labels[d.feature] || {})[LANG] || d.feature);
    return `<div class="f"><span class="name">${name}</span>
      <span class="axis" role="img" aria-label="${d.value > 0 ? "+" : "−"}${Math.abs(d.value).toFixed(2)}"><span class="b ${d.value > 0 ? "up" : "down"}" style="width:${w.toFixed(1)}%"></span></span>
      <span class="val">${esc(featureValue(d.feature, d.x))}</span></div>`;
  }).join("");
}

// ------------------------------------------------------------------ history chart (SVG)
function renderHistory() {
  const W = 900, H = 260, L = 56, R = 46, T = 12, B = 30;
  const hist = DATA.history.filter((d) => d.vis_m !== null);
  if (!hist.length) { $("hist").innerHTML = ""; return; }
  const t0 = new Date(hist[0].t).getTime(), t1 = new Date(DATA.issue_time).getTime() + 3600e3;
  const x = (ts) => L + ((ts - t0) / (t1 - t0)) * (W - L - R);
  const lv = (v) => Math.log10(Math.max(50, Math.min(10000, v)));
  const y = (v) => T + (1 - (lv(v) - Math.log10(50)) / (4 - Math.log10(50))) * (H - T - B);
  const yp = (p) => H - B - p * (H - T - B) * 0.45;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${t("histTitle")}">`;
  for (const v of [100, 350, 550, 1000, 5000, 10000]) {
    s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#d3dbe2" stroke-width="1"/>`;
    s += `<text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="12" fill="#4a5a70">${v >= 1000 ? v / 1000 + " km" : v + " m"}</text>`;
  }
  s += `<line x1="${L}" x2="${W - R}" y1="${y(1000)}" y2="${y(1000)}" stroke="#c8323f" stroke-dasharray="6 4" stroke-width="1.5"/>`;
  const probs = LOG.filter((d) => new Date(d.valid_time).getTime() >= t0);
  if (probs.length) {
    let area = `M ${x(new Date(probs[0].valid_time).getTime())} ${H - B}`;
    for (const d of probs) area += ` L ${x(new Date(d.valid_time).getTime())} ${yp(d.p)}`;
    area += ` L ${x(new Date(probs[probs.length - 1].valid_time).getTime())} ${H - B} Z`;
    s += `<path d="${area}" fill="rgba(200,50,63,0.28)" stroke="rgba(200,50,63,0.7)" stroke-width="1"/>`;
    s += `<text x="${W - R + 6}" y="${yp(1) + 4}" font-size="12" fill="#c8323f">100%</text>`;
    s += `<text x="${W - R + 6}" y="${H - B}" font-size="12" fill="#c8323f">0%</text>`;
  }
  let path = "";
  hist.forEach((d, i) => { path += `${i ? "L" : "M"} ${x(new Date(d.t).getTime()).toFixed(1)} ${y(d.vis_m).toFixed(1)} `; });
  s += `<path d="${path}" fill="none" stroke="#13233a" stroke-width="2"/>`;
  for (const d of hist) if (d.rvr_m !== null)
    s += `<circle cx="${x(new Date(d.t).getTime())}" cy="${y(d.rvr_m)}" r="3" fill="#e2762b"/>`;
  for (let ts = Math.ceil(t0 / 21600e3) * 21600e3; ts <= t1; ts += 21600e3) {
    const dt = new Date(ts);
    s += `<text x="${x(ts)}" y="${H - 8}" text-anchor="middle" font-size="12" fill="#4a5a70">${String(dt.getUTCDate()).padStart(2, "0")}/${String(dt.getUTCHours()).padStart(2, "0")}Z</text>`;
  }
  s += `<line x1="${x(new Date(DATA.issue_time).getTime())}" x2="${x(new Date(DATA.issue_time).getTime())}" y1="${T}" y2="${H - B}" stroke="#13233a" stroke-width="1" stroke-dasharray="2 3"/>`;
  $("hist").innerHTML = s + "</svg>";
}

// ------------------------------------------------------------------ verification table
function renderVer() {
  const cols = t("verCols");
  if (!VER.length) { $("ver").innerHTML = `<caption class="empty">${t("noVer")}</caption>`; return; }
  const rows = VER.slice().sort((a, b) => a.mode.localeCompare(b.mode) || a.horizon - b.horizon);
  $("ver").innerHTML = `<thead><tr>${cols.map((c) => `<th scope="col">${c}</th>`).join("")}</tr></thead><tbody>` +
    rows.map((r) => `<tr><td>${r.mode === "live" ? t("live") : t("replay")}</td><td>${t("lead")(r.horizon)}</td>
      <td>${r.n}</td><td>${r.events}</td><td>${r.hits}</td><td>${r.false_alarms}</td><td>${r.misses}</td>
      <td>${fmt(r.POD, 2)}</td><td>${fmt(r.FAR, 2)}</td><td>${fmt(r.CSI, 2)}</td><td>${fmt(r.Brier, 4)}</td></tr>`).join("") + "</tbody>";
}

function renderAll() {
  applyStatic();
  if (!DATA) return;
  $("issued").textContent = DATA.issue_time.replace("T", " ").slice(0, 16) + "Z";
  $("issued").dateTime = DATA.issue_time;
  $("source").textContent = DATA.source + (DATA.error ? " · ⚠" : "");
  if (!DATA.fog[SELECTED]) SELECTED = Number(Object.keys(DATA.fog)[0]);
  renderAlert(); renderLights(); renderNow(); renderIls(); renderWhy(); renderHistory(); renderVer();
}

async function load() {
  try {
    const [n, l, v] = await Promise.all([
      fetch("api/nowcast").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      fetch("api/log?hours=72&horizon=3").then((r) => r.json()),
      fetch("api/verification").then((r) => r.json()),
    ]);
    DATA = n; LOG = l; VER = v;
    renderAll();
  } catch (e) {
    applyStatic();
    $("alert-title").textContent = "–";
    $("alert-text").textContent = t("loadErr") + e.message;
  }
}

document.querySelectorAll(".lang button").forEach((b) => b.addEventListener("click", () => {
  LANG = b.dataset.lang; localStorageSet("ltac-lang", LANG); renderAll();
}));
applyStatic();
load();
setInterval(load, 5 * 60 * 1000);
