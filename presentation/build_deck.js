// Builds the project presentation (Turkish and English) with pptxgenjs.
// Usage: NODE_PATH=<dir with node_modules> node presentation/build_deck.js [tr|en]
"use strict";
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const LANG = process.argv[2] || "tr";
const FIG = (name) => path.join(ROOT, "results", "figures", LANG, name);
const K = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "tables", "key_numbers.json"), "utf8"));
const APPLY_THEME = process.env.APPLY_THEME_JS;

const THEME = {
  name: "LTAC Fog",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "13233A", lt1: "FFFFFF", dk2: "2B3E5A", lt2: "E6EBEF",
    accent1: "F2C200", accent2: "1F77B4", accent3: "C8323F", accent4: "1F9D5B",
    accent5: "E2762B", accent6: "7F8C9A", hlink: "1F77B4", folHlink: "2B3E5A",
  },
};
const HEX = THEME.colors;

// ------------------------------------------------------------------ text (TR / EN)
const tr = LANG === "tr";
const num = (x, d) => (tr ? x.toFixed(d).replace(".", ",") : x.toFixed(d));
const pct = (x, d) => (tr ? `%${num(x, d)}` : `${x.toFixed(d)}%`);
const T = {
  title: tr ? "Esenboğa'da Sis ve Düşük Görüşün Açıklanabilir Makine Öğrenmesiyle Kısa Vadeli Tahmini"
            : "Explainable Machine-Learning Nowcasting of Fog and Low Visibility at Esenboğa",
  sub: tr ? "Açıklanabilir bir erken uyarı sistemi" : "An explainable early-warning system",
  who: tr ? "Ata Sakik (25290085)\nYMH453 Makine Öğrenmesi, Ankara Üniversitesi Yazılım Mühendisliği, 2026"
          : "Ata Sakik (25290085)\nYMH453 Machine Learning, Ankara University Software Engineering, 2026",
  footer: tr ? "YMH453 Makine Öğrenmesi — Ankara Üniversitesi" : "YMH453 Machine Learning — Ankara University",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 in
pres.author = "Ata Sakik";
pres.title = T.title;
pres.subject = "YMH453 term project";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
const sign = (x, y) => [
  { rect: { x, y, w: 1.05, h: 0.46, fill: { color: "000000" }, line: { color: HEX.accent1, width: 1.5 } } },
  { text: { text: "LTAC", options: { x, y, w: 1.05, h: 0.46, align: "center", valign: "middle",
    fontFace: "Calibri", bold: true, fontSize: 18, color: HEX.accent1, margin: 0 } } },
];
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: HEX.dk1 },
  objects: [
    ...sign(0.7, 0.6),
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.55, w: 6.9, h: 2.7,
      fontFace: "Cambria", fontSize: 36, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.45, w: 6.9, h: 0.6,
      fontFace: "Calibri", fontSize: 20, color: C.accent1, align: "left", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    ...sign(11.65, 0.42),
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 10.8, h: 0.75,
      fontFace: "Cambria", fontSize: 30, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: T.footer, options: { x: 0.6, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: HEX.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.35, fontSize: 10, color: HEX.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: HEX.dk1 },
  objects: [
    ...sign(11.65, 0.42),
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 10.8, h: 0.75,
      fontFace: "Cambria", fontSize: 30, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.35, fontSize: 10, color: HEX.accent6, align: "right" },
});

// ------------------------------------------------------------------ helpers
let section = "";
function slide(master, title, notes) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  return s;
}
function newSection(name) { section = name; pres.addSection({ title: name }); }
function stat(s, x, y, w, big, label, opts = {}) {
  s.addText(big, { x, y, w, h: 0.85, fontFace: "Cambria", fontSize: opts.size || 40, bold: true,
    color: opts.color || C.text1, margin: 0, isTextBox: true, objectName: "stat-" + label.slice(0, 12) });
  s.addText(label, { x, y: y + 0.85, w, h: opts.lh || 0.6, fontSize: 14, color: C.text2, margin: 0,
    valign: "top", isTextBox: true });
}
function bullets(s, items, x, y, w, h, size = 16) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
    { x, y, w, h, fontSize: size, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0.05, isTextBox: true });
}
function card(s, x, y, w, h, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || HEX.lt2 },
    line: { color: fill || HEX.lt2 } });
}
function image(s, file, x, y, w, h) {
  s.addImage({ path: FIG(file), x, y, w, h });
}
const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt",
  dataLabelFontFace: "+mn-lt", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, legendFontSize: 12,
  dataLabelFontSize: 11, catAxisLabelColor: HEX.dk2, valAxisLabelColor: HEX.accent6, dataLabelColor: HEX.dk1 };

// =========================================================================== slides
newSection(tr ? "Giriş" : "Introduction");
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: section });
  s.addText(T.title, { placeholder: "title" });
  s.addText(T.sub, { placeholder: "body" });
  s.addText(T.who, { x: 0.7, y: 5.75, w: 7.2, h: 0.9, fontSize: 14, color: HEX.lt2, margin: 0, isTextBox: true });
  // approach lights fading into fog (the visual motif of the web application) and the app itself
  for (let i = 0; i < 5; i++) {
    s.addShape(pres.shapes.OVAL, { x: 0.75 + i * 0.5, y: 5.15, w: 0.26, h: 0.26,
      fill: { color: HEX.accent1, transparency: i * 18 }, line: { color: HEX.accent1, transparency: i * 18 },
      objectName: "approach-light-" + i });
  }
  s.addImage({ path: FIG("app_screenshot.png"), x: 8.1, y: 1.0, w: 4.6, h: 4.47, objectName: "app-preview" });
  s.addNotes(tr
    ? "Merhaba. Bu projede Ankara Esenboğa Havalimanı'nda sis ve düşük görüşü 1, 3 ve 6 saat önceden tahmin eden, kararlarını açıklayabilen ve canlı çalışan bir erken uyarı sistemi geliştirdim. Sunumda önce problemi, ardından veri ve yöntemi, sonra bulguları ve uygulamayı anlatacağım."
    : "Hello. In this project I built an early-warning system that nowcasts fog and low visibility at Ankara Esenboğa Airport 1, 3 and 6 hours ahead, explains its decisions and runs live. I will cover the problem, data and method, results and the application.");
}
{
  const s = slide("CONTENT", tr ? "Sis Esenboğa'nın en önemli operasyonel riski" : "Fog is Esenboğa's key operational weather risk",
    tr ? `Sis Esenboğa'da gecikme, yönlendirme ve iptallerin başlıca nedeni. Kendi veri setimiz yayımlanmış klimatolojiyi doğruluyor: sislerin %${num(K.share_oct_feb, 1)}'i Ekim–Şubat'ta; 2011–2020'de ${num(K.fog_hours_2011_2020, 1)} saat sis var, Koyuncu ve arkadaşlarının yaklaşık 800 saatlik değeriyle örtüşüyor; sis gözlemlerinin %${num(K.fog_rvr_le350_pct, 1)}'inde RVR 350 metrenin altında, yani CAT III gerekiyor. Isı haritası sisin gün doğumu civarında yoğunlaştığını gösteriyor.`
       : `Fog is the main cause of delays and diversions. Our data set reproduces the published climatology: ${K.share_oct_feb}% of fog in Oct–Feb, ${K.fog_hours_2011_2020} fog hours in 2011–2020 (≈800 h reported), and RVR ≤ 350 m in ${K.fog_rvr_le350_pct}% of fog observations.`);
  stat(s, 0.6, 1.35, 3.6, pct(K.share_oct_feb, 1),
    tr ? "sislerin Ekim–Şubat'ta görülme payı" : "of fog occurs October–February");
  stat(s, 4.75, 1.35, 3.6, tr ? `${num(K.fog_hours_2011_2020, 1)} sa` : `${K.fog_hours_2011_2020.toFixed(1)} h`,
    tr ? "2011–2020 sis süresi (literatür ≈800 sa)" : "fog hours 2011–2020 (literature ≈800 h)");
  stat(s, 8.9, 1.35, 3.8, pct(K.fog_rvr_le350_pct, 1),
    tr ? "sis gözlemlerinde RVR ≤ 350 m (CAT III)" : "of fog observations with RVR ≤ 350 m (CAT III)", { color: C.accent3 });
  image(s, "climatology.png", 0.6, 3.25, 12.1, 3.4);
}
{
  const s = slide("CONTENT", tr ? "Boşluk ve katkılar" : "Gap and contributions",
    tr ? "Esenboğa üzerine yapılan çalışmalar klimatolojik ve sinoptik; Çamalan ve arkadaşları 2010'da tahmin modeli geliştirilmesini açıkça öneriyor. Literatür taramamızda Esenboğa için makine öğrenmesi tabanlı bir tahmin modeli bulunamadı. Uluslararası çalışmalarda ise resmî TAF/TREND ile aynı bilgi ufkunda karşılaştırma ve fiziksel açıklama nadir. Beş katkıyı sağdaki listede görüyorsunuz."
       : "Existing Esenboğa studies are climatological; no ML forecast exists. Internationally, matched comparisons with the official forecasts and physical explanations are rare. Our five contributions are listed on the right.");
  card(s, 0.6, 1.4, 4.6, 5.2, HEX.lt2);
  s.addText(tr ? "Mevcut durum" : "State of the art", { x: 0.85, y: 1.6, w: 4.1, h: 0.45, fontFace: "Cambria",
    fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true });
  bullets(s, tr ? ["Esenboğa: klimatolojik ve sinoptik analizler (2010, 2022)",
                   "Makine öğrenmesi tabanlı tahmin modeli yok",
                   "Resmî TAF/TREND ile adil karşılaştırma nadir",
                   "Modellerin öğrendiği fizik çoğu zaman açıklanmıyor"]
                : ["Esenboğa: climatological and synoptic analyses (2010, 2022)", "No machine-learning forecast model",
                   "Fair comparison with official TAF/TREND is rare", "What models learn is rarely explained"],
    0.85, 2.2, 4.15, 4.2, 16);
  const items = tr ? [["21,8 yıllık açık veri seti", "kalite kontrollü METAR/SPECI, klimatolojiyi yeniden üretiyor"],
                      ["6 model ailesinin karşılaştırması", "kalibrasyon, dengesizlik deneyi, bootstrap anlamlılık testleri"],
                      ["ILS/RVR kategorisi tahmini", "sıralı (ordinal) formülasyon, başlangıç/dağılma analizi"],
                      ["SHAP ile açıklanabilirlik", "öğrenilen ilişkiler sis fiziğiyle tutarlı"],
                      ["Canlı erken uyarı uygulaması", "aynı işlem hattı, kademeli uyarı, gerçek zamanlı doğrulama"]]
                   : [["21.8-year open data set", "quality-controlled METAR/SPECI reproducing the climatology"],
                      ["Benchmark of 6 model families", "calibration, imbalance ablation, bootstrap significance"],
                      ["ILS/RVR category forecasts", "ordinal formulation, onset/dissipation analysis"],
                      ["Explainability with SHAP", "learnt relationships consistent with fog physics"],
                      ["Live early-warning application", "same pipeline, tiered alerts, real-time verification"]];
  items.forEach(([h, d], i) => {
    const y = 1.45 + i * 1.04;
    s.addShape(pres.shapes.OVAL, { x: 5.65, y: y + 0.08, w: 0.55, h: 0.55, fill: { color: HEX.accent1 }, line: { color: HEX.accent1 } });
    s.addText(String(i + 1), { x: 5.65, y: y + 0.08, w: 0.55, h: 0.55, align: "center", valign: "middle",
      fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText([{ text: h, options: { bold: true, fontSize: 17, breakLine: true } },
               { text: d, options: { fontSize: 14, color: HEX.dk2 } }],
      { x: 6.4, y, w: 6.3, h: 0.85, valign: "middle", margin: 0, color: C.text1, isTextBox: true });
  });
}

newSection(tr ? "Veri ve yöntem" : "Data and method");
{
  const s = slide("CONTENT", tr ? "Veri: 21,8 yıllık METAR/SPECI arşivi" : "Data: 21.8 years of METAR/SPECI",
    tr ? "Veri Iowa Environmental Mesonet arşivinden geliyor. Önemli bir tespit: eski kayıtların bir kısmı gerçek METAR değil, NCEI veritabanından yeniden üretilmiş sentetik kayıtlar; bunlarda RVR ve TREND yok. Bu kayıtları çıkarıp boşlukları Ogimet'teki orijinal metinlerle doldurdum. Kendi yazdığım çözücü görüş, her pistin RVR'si, hadise, bulut, sıcaklık, nem ve TREND gruplarını çözüyor; kalite kontrolü aralık ve sıçrama denetimleri içeriyor."
       : "Data come from the IEM archive; synthetic ISD-derived records without RVR/TREND were removed and gaps filled from Ogimet. A purpose-built decoder parses visibility, RVR of every runway, weather, clouds and TREND groups; QC applies range and spike checks.");
  const st = tr ? [["385 018", "METAR/SPECI rasatı (KK sonrası)"], ["%99,7", "30 dk ızgarada gözlem kapsaması"],
                   ["537", "sis olayı; medyan süre 2 sa"], ["%1,02", "sis dilimi oranı (görüş < 1000 m)"],
                   ["%99,9", "görüş < 1500 m iken RVR raporu"], ["109 / 47", "çıkarılan rasat / düzeltilen değer"]]
                : [["385,018", "METAR/SPECI reports after QC"], ["99.7%", "coverage of the 30-min grid"],
                   ["537", "fog episodes; median duration 2 h"], ["1.02%", "fog slots (VIS < 1000 m)"],
                   ["99.9%", "RVR reported when VIS < 1500 m"], ["109 / 47", "reports removed / values corrected"]];
  st.forEach(([b, l], i) => {
    const x = 0.6 + (i % 3) * 4.15, y = 1.45 + Math.floor(i / 3) * 1.85;
    card(s, x, y, 3.85, 1.6, HEX.lt2);
    stat(s, x + 0.25, y + 0.12, 3.4, b, l, { size: 34, lh: 0.55 });
  });
  s.addText(tr ? "Kaynaklar: Iowa Environmental Mesonet (orijinal METAR), Ogimet (2005–2012 boşluk dolgusu), NOAA AWC (canlı veri ve son 30 günün TAF'ları). Sentetik ISD kayıtları (RVR/TREND yok) çıkarıldı."
                : "Sources: Iowa Environmental Mesonet (original METARs), Ogimet (gap filling 2005–2012), NOAA AWC (live data, last 30 days of TAFs). Synthetic ISD records (no RVR/TREND) were removed.",
    { x: 0.6, y: 5.35, w: 12.1, h: 0.9, fontSize: 14, color: C.text2, margin: 0, valign: "top", isTextBox: true });
}
{
  const s = slide("CONTENT", tr ? "Yöntem akışı" : "Method overview",
    tr ? "Akış: arşivler, çözücü ve kalite kontrolü, 30 dakikalık ızgara ve 77 öznitelik, modeller ve kalibrasyon, doğrulama. Web uygulaması aynı kodu kullandığı için çevrimdışı ve canlı tahminler birebir aynı; bunu bir eşdeğerlik testiyle de kanıtladım."
       : "Pipeline: archives, decoder and QC, 30-min grid with 77 features, models and calibration, verification. The web app reuses the same code, so offline and live forecasts are identical (proven by a parity test).");
  image(s, "architecture.png", 0.75, 1.75, 11.8, 4.15);
}
{
  const s = slide("CONTENT", tr ? "Hedefler ve öznitelikler" : "Targets and predictors",
    tr ? "İki hedef var: görüşün 1000 metrenin altına inmesi ve ILS kategorileri. ILS sınıfları Çamalan ve arkadaşlarının Esenboğa için kullandığı 550 ve 350 metrelik sınırlarla tanımlı. 77 öznitelik beş gruba ayrılıyor: anlık durum, hadise, eğilimler, sınır tabaka belleği ve Güneş/takvim. Geçerlilik zamanındaki Güneş yüksekliği önceden bilinen deterministik bir bilgi olduğu için meşru bir öznitelik."
       : "Two targets: visibility below 1000 m and ILS categories (550/350 m, as used for Esenboğa). The 77 predictors form five groups; valid-time solar terms are deterministic and known in advance.");
  s.addText(tr ? "Tahmin edilen değişkenler (1, 3, 6 sa sonra)" : "Predictands (1, 3, 6 h ahead)",
    { x: 0.6, y: 1.35, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true });
  const cats = [[tr ? "Sis: hâkim görüş < 1000 m" : "Fog: prevailing visibility < 1000 m", HEX.dk2],
                [tr ? "CAT I+: RVR ≥ 550 m" : "CAT I+: RVR ≥ 550 m", HEX.accent4],
                [tr ? "CAT II: 350 ≤ RVR < 550 m" : "CAT II: 350 ≤ RVR < 550 m", HEX.accent5],
                [tr ? "CAT III: RVR < 350 m" : "CAT III: RVR < 350 m", HEX.accent3]];
  cats.forEach(([t, col], i) => {
    const y = 2.0 + i * 0.85;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 5.6, h: 0.65, rectRadius: 0.08, fill: { color: col }, line: { color: col } });
    s.addText(t, { x: 0.8, y, w: 5.3, h: 0.65, fontSize: 17, bold: true, color: C.background1, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText(tr ? "Sınırlar: Çamalan vd. (2010) ve ICAO Doc 9365." : "Boundaries: Çamalan et al. (2010), ICAO Doc 9365.",
    { x: 0.6, y: 5.5, w: 5.6, h: 0.4, fontSize: 12, color: C.text2, margin: 0, isTextBox: true });
  const groups = tr ? [["Anlık durum", "21", "görüş, RVR, T, Td, T−Td, nem, rüzgâr, QNH, bulut"],
                       ["Hadise", "11", "FG, BCFG/MIFG, BR, HZ, DZ, RA, SN"],
                       ["Eğilimler", "19", "1/3/6 sa soğuma, kuruma/nemlenme, görüş eğilimi"],
                       ["Bellek", "13", "12 sa max'tan soğuma, son sisten beri süre, kar oranı"],
                       ["Güneş ve takvim", "13", "Güneş yüksekliği, gün doğumuna kalan süre"]]
                    : [["Current state", "21", "visibility, RVR, T, Td, T−Td, RH, wind, QNH, cloud"],
                       ["Present weather", "11", "FG, BCFG/MIFG, BR, HZ, DZ, RA, SN"],
                       ["Tendencies", "19", "1/3/6-h cooling, drying/moistening, visibility trend"],
                       ["Memory", "13", "cooling since 12-h max, hours since fog, snow fraction"],
                       ["Sun and calendar", "13", "solar elevation, time to sunrise"]];
  const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk1 } } });
  s.addTable([[hdr(tr ? "Grup" : "Group"), hdr("n"), hdr(tr ? "Örnekler" : "Examples")],
              ...groups.map((g) => g.map((c) => ({ text: c })))],
    { x: 6.7, y: 1.4, w: 6.0, colW: [1.6, 0.5, 3.9], fontSize: 14, color: HEX.dk1, border: { type: "solid", color: "D3DBE2", pt: 0.75 },
      fill: { color: "FFFFFF" }, rowH: 0.62, valign: "middle", margin: 0.06, autoPage: false });
}
{
  const s = slide("CONTENT", tr ? "Modeller ve sızıntısız doğrulama" : "Models and leakage-free validation",
    tr ? "Veriyi rastgele değil kronolojik ve sezonlarla hizalı böldüm; aksi hâlde aynı sis olayının ardışık örnekleri eğitim ve teste dağılırdı. Altı model ailesi: lojistik regresyon, rastgele orman, XGBoost, LightGBM ve çok görevli GRU/LSTM. Hiperparametreler Optuna ile doğrulama sezonlarında ayarlandı. SMOTE ve sınıf ağırlığı olasılıkları bozduğu için nihai modellerde yeniden örnekleme yapmadım; kalibrasyonu bir-sezon-dışarıda çapraz doğrulamayla seçtim."
       : "Chronological, season-aligned split; six model families; Optuna tuning on validation seasons; no resampling in the final models because SMOTE and class weights distort probabilities; calibration chosen by leave-one-season-out CV.");
  const segs = [[tr ? "Eğitim" : "Training", "2005–2019", 14.5, HEX.dk2], [tr ? "Doğrulama" : "Validation", "2019–2022", 3, HEX.accent2],
                [tr ? "Test" : "Test", "2022–2026", 4, HEX.accent4], [tr ? "Canlı" : "Live", "2026–", 1, HEX.accent1]];
  let x = 0.6;
  const total = 22.5, W = 12.1;
  segs.forEach(([n, p, yrs, col]) => {
    const w = (yrs / total) * W;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.5, w, h: 0.75, fill: { color: col }, line: { color: "FFFFFF", width: 1 } });
    s.addText([{ text: n, options: { bold: true, breakLine: true } }, { text: p, options: { fontSize: 12 } }],
      { x: x + 0.08, y: 1.5, w: Math.max(w - 0.1, 0.9), h: 0.75, fontSize: 15, color: col === HEX.accent1 ? HEX.dk1 : HEX.lt1,
        valign: "middle", margin: 0, isTextBox: true });
    x += w;
  });
  const cols = tr ? [["Modeller", ["Lojistik regresyon (temel)", "Rastgele orman", "XGBoost ve LightGBM (Optuna, 30 deneme)", "Çok görevli GRU ve LSTM (12 sa dizi, GPU)"]],
                     ["Dengesizlik ve kalibrasyon", ["Sis örneklerin yalnızca %1'i", "SMOTE/ağırlık: olasılıkları bozuyor", "Kalibrasyon: yok/Platt/izotonik", "Eşik: doğrulamada en yüksek CSI"]],
                     ["Sızıntı kontrolü", ["Öznitelik yalnızca t'ye kadarki veriden", "Hedef t+h'deki yeni rasat", "Otomatik sızıntı testi (17 test)", "Test sezonları tek kez kullanıldı"]]]
                  : [["Models", ["Logistic regression (baseline)", "Random forest", "XGBoost and LightGBM (Optuna, 30 trials)", "Multi-task GRU and LSTM (12-h sequence, GPU)"]],
                     ["Imbalance and calibration", ["Fog is only 1% of samples", "SMOTE/weights distort probabilities", "Calibration: none/Platt/isotonic", "Threshold: max CSI on validation"]],
                     ["Leakage control", ["Features use data up to t only", "Target is a new report at t+h", "Automated leakage tests (17 tests)", "Test seasons evaluated once"]]];
  cols.forEach(([h, items], i) => {
    const cx = 0.6 + i * 4.15;
    card(s, cx, 2.7, 3.85, 3.95, HEX.lt2);
    s.addText(h, { x: cx + 0.2, y: 2.85, w: 3.5, h: 0.5, fontFace: "Cambria", fontSize: 19, bold: true, color: C.text1, margin: 0, isTextBox: true });
    bullets(s, items, cx + 0.2, 3.45, 3.5, 3.0, 15);
  });
}

newSection(tr ? "Bulgular" : "Results");
{
  const s = slide("CONTENT", tr ? "Tüm modeller kalıcılığı anlamlı biçimde geçiyor" : "All models significantly beat persistence",
    tr ? "Dört bağımsız test sezonunda en iyi kritik başarı indeksi 1, 3 ve 6 saat için 0,73, 0,47 ve 0,34; kalıcılık ise 0,65, 0,32 ve 0,13. Göreli kazanç öngörü süresiyle büyüyor: yüzde 12, 45 ve 130. Gün-blok bootstrap ile eşleştirilmiş testlerde altı modelin tamamı her öngörü süresinde kalıcılıktan anlamlı biçimde iyi. İlginç bir bulgu: 1 saatte ağaç tabanlı LightGBM, 3–6 saatte yinelemeli ağlar en iyi."
       : "On four independent test seasons the best CSI is 0.73/0.47/0.34 vs 0.65/0.32/0.13 for persistence (+12/45/130%). All six models are significantly better at every lead time (paired day-block bootstrap). Boosting wins at 1 h, recurrent nets at 3–6 h.");
  s.addChart(pres.charts.BAR, [
    { name: tr ? "En iyi ML" : "Best ML", labels: ["1 h", "3 h", "6 h"].map((l) => (tr ? l.replace("h", "sa") : l)), values: [0.729, 0.472, 0.340] },
    { name: tr ? "Kalıcılık" : "Persistence", labels: ["1 h", "3 h", "6 h"].map((l) => (tr ? l.replace("h", "sa") : l)), values: [0.652, 0.321, 0.129] },
  ], { x: 0.6, y: 1.35, w: 7.4, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent2, HEX.dk1],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", valAxisMaxVal: 0.9, valAxisMinVal: 0,
    valAxisLabelFormatCode: "0.0", showLegend: true, legendPos: "t", showTitle: true, title: tr ? "Kritik başarı indeksi (CSI), test 2022–2026" : "Critical success index (CSI), test 2022–2026",
    titleFontFace: "+mj-lt", titleFontSize: 16, titleColor: HEX.dk1, valGridLine: { color: "E1E7EC", size: 0.5 }, catGridLine: { style: "none" },
    ...chartText });
  stat(s, 8.5, 1.5, 4.2, tr ? "+%12  +%45  +%130" : "+12%  +45%  +130%", tr ? "1/3/6 sa CSI göreli kazancı (LightGBM)" : "relative CSI gain at 1/3/6 h (LightGBM)", { size: 30, color: C.accent2 });
  stat(s, 8.5, 3.05, 4.2, "6 / 6", tr ? "model, her sürede anlamlı (bootstrap, p < 0,05)" : "models significant at every lead (bootstrap, p < 0.05)", { size: 34 });
  stat(s, 8.5, 4.6, 4.2, tr ? "1 sa: LightGBM" : "1 h: LightGBM", tr ? "3–6 sa: GRU/LSTM en iyi olasılıksal beceri" : "3–6 h: GRU/LSTM best probabilistic skill", { size: 28 });
}
{
  const s = slide("CONTENT", tr ? "Resmî TREND tahminini de geçiyor" : "It also beats the official TREND forecast",
    tr ? "METAR'a eklenen TREND, tahmincinin 2 saatlik resmî tahmini. Aynı test durumlarında TREND'in CSI değeri 0,62; kalıcılık 0,65; LightGBM ise 0,73. Fark 0,105 ve %95 güven aralığı 0,075 ile 0,140 arasında, yani anlamlı. Sağdaki grafik becerinin öngörü süresiyle düzgün azaldığını ve kalıcılıkla arasındaki farkın açıldığını gösteriyor. TAF için yalnızca son 30 günlük arşive erişebildim; o dönemde sis olmadığı için ne TAF ne de model yanlış alarm verdi."
       : "TREND (the forecaster's official 2-h forecast) reaches CSI 0.62, persistence 0.65 and LightGBM 0.73 on identical cases: ΔCSI = 0.105 [0.075, 0.140]. Skill decays smoothly with lead time while the gap to persistence widens. In the 30-day TAF window no fog occurred and neither TAF nor the model raised a false alarm.");
  const L = tr ? ["1 sa", "2 sa", "3 sa", "4 sa", "5 sa", "6 sa"] : ["1 h", "2 h", "3 h", "4 h", "5 h", "6 h"];
  s.addChart(pres.charts.LINE, [
    { name: "LightGBM", labels: L, values: [0.729, 0.544, 0.467, 0.384, 0.346, 0.297] },
    { name: tr ? "Kalıcılık" : "Persistence", labels: L, values: [0.652, 0.458, 0.321, 0.230, 0.168, 0.129] },
  ], { x: 5.3, y: 1.35, w: 7.4, h: 5.3, chartColors: [HEX.accent2, HEX.dk1], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8,
    showValue: true, dataLabelPosition: "t", dataLabelFormatCode: "0.00", valAxisMinVal: 0, valAxisMaxVal: 0.9, valAxisLabelFormatCode: "0.0",
    showLegend: true, legendPos: "t", showTitle: true, title: tr ? "CSI ve öngörü süresi" : "CSI versus lead time", titleFontFace: "+mj-lt",
    titleFontSize: 16, titleColor: HEX.dk1, valGridLine: { color: "E1E7EC", size: 0.5 }, catGridLine: { style: "none" }, ...chartText });
  const rows = tr ? [["LightGBM", "0,73"], ["Kalıcılık", "0,65"], ["TREND (resmî)", "0,62"]] : [["LightGBM", "0.73"], ["Persistence", "0.65"], ["TREND (official)", "0.62"]];
  s.addText(tr ? "1 saatte CSI" : "CSI at 1 h", { x: 0.6, y: 1.45, w: 4.3, h: 0.45, fontFace: "Cambria", fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true });
  rows.forEach(([n, v], i) => {
    const y = 2.05 + i * 0.8;
    card(s, 0.6, y, 4.3, 0.65, i === 0 ? HEX.accent2 : HEX.lt2);
    s.addText(n, { x: 0.8, y, w: 2.8, h: 0.65, fontSize: 17, bold: i === 0, color: i === 0 ? HEX.lt1 : HEX.dk1, valign: "middle", margin: 0, isTextBox: true });
    s.addText(v, { x: 3.4, y, w: 1.3, h: 0.65, fontSize: 22, bold: true, align: "right", color: i === 0 ? HEX.lt1 : HEX.dk1, valign: "middle", margin: 0, isTextBox: true });
  });
  stat(s, 0.6, 4.6, 4.4, tr ? "ΔCSI = +0,105" : "ΔCSI = +0.105", tr ? "LightGBM − TREND, %95 GA [0,075; 0,140]" : "LightGBM − TREND, 95% CI [0.075, 0.140]", { size: 32, color: C.accent2 });
}
{
  const s = slide("CONTENT", tr ? "Zor kısım: sis başlangıçları" : "The hard part: fog onsets",
    tr ? "Kalıcılık sis başlangıcını ve dağılmasını tanımı gereği hiç öngöremez; asıl operasyonel değer burada. Dağılmaları modeller iyi yakalıyor: 6 saatte GRU yüzde 86. Başlangıçlar ise zor; en yüksek CSI eşiğinde yalnızca yüzde 6 ile 21 arası yakalanıyor. Bunu dürüstçe raporladım ve uygulamaya kademeli bir uyarı ekledim: eşiğin yarısında 'izleme' seviyesi, başlangıçların 1, 3 ve 6 saat önceden yüzde 25, 21 ve 38'ini işaretliyor; CSI ise çok az düşüyor."
       : "Persistence cannot predict onsets or dissipations. Dissipations are captured well (GRU 86% at 6 h); onsets are hard (6–21% at the max-CSI thresholds). The tiered alert design helps: the watch level (half the threshold) flags 25/21/38% of onsets 1/3/6 h ahead at a small CSI cost.");
  const L = tr ? ["1 sa", "3 sa", "6 sa"] : ["1 h", "3 h", "6 h"];
  s.addChart(pres.charts.BAR, [
    { name: tr ? "Uyarı (τ)" : "Warning (τ)", labels: L, values: [12.5, 6.3, 20.8] },
    { name: tr ? "İzleme (τ/2)" : "Watch (τ/2)", labels: L, values: [25.0, 20.8, 37.5] },
    { name: tr ? "Kalıcılık" : "Persistence", labels: L, values: [0, 2.1, 4.2] },
  ], { x: 0.6, y: 1.35, w: 7.6, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent2, HEX.accent1, HEX.dk1],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", valAxisMinVal: 0, valAxisMaxVal: 45, showLegend: true, legendPos: "t",
    showTitle: true, title: tr ? "Önceden işaretlenen sis başlangıçları (%) — LightGBM" : "Fog onsets flagged in advance (%) — LightGBM",
    titleFontFace: "+mj-lt", titleFontSize: 16, titleColor: HEX.dk1, valGridLine: { color: "E1E7EC", size: 0.5 }, catGridLine: { style: "none" }, ...chartText });
  stat(s, 8.7, 1.5, 4.0, tr ? "%86" : "86%", tr ? "6 sa önceden doğru tahmin edilen dağılmalar (GRU; kalıcılık %68)" : "dissipations forecast 6 h ahead (GRU; persistence 68%)", { size: 40, color: C.accent4, lh: 0.8 });
  stat(s, 8.7, 3.35, 4.0, tr ? "%2–21" : "2–21%", tr ? "en yüksek CSI eşiğinde yakalanan başlangıçlar" : "onsets captured at the max-CSI thresholds", { size: 40, color: C.accent3, lh: 0.8 });
  stat(s, 8.7, 5.2, 4.0, tr ? "×2–3" : "×2–3", tr ? "izleme seviyesiyle başlangıç tespiti artışı" : "more onsets flagged at the watch level", { size: 40, lh: 0.8 });
}
{
  const s = slide("CONTENT", tr ? "ILS kategorisi tahminleri" : "ILS-category forecasts",
    tr ? "ILS kategorilerini sıralı bir problem olarak, iki ikili modelle tahmin ettim: RVR 550'nin altında mı ve 350'nin altında mı. Sıralı olasılık beceri skoru 1, 3 ve 6 saatte 0,64, 0,41 ve 0,28; kalıcılık ise 6 saatte -0,70. CAT III durumları yüzde 76 doğrulukla tanınıyor; en zor sınıf, dar bir geçiş bandı olan CAT II."
       : "ILS categories are forecast as an ordinal problem with two binary models (RVR < 550 m, < 350 m). RPSS reaches 0.64/0.41/0.28 at 1/3/6 h (persistence −0.70 at 6 h). CAT III is recognised in 76% of cases; CAT II, a narrow transitional band, is hardest.");
  image(s, "rvr_confusion.png", 0.6, 1.4, 8.3, 3.15);
  const r = tr ? [["0,64", "RPSS 1 sa"], ["0,41", "RPSS 3 sa"], ["0,28", "RPSS 6 sa"]] : [["0.64", "RPSS 1 h"], ["0.41", "RPSS 3 h"], ["0.28", "RPSS 6 h"]];
  r.forEach(([b, l], i) => stat(s, 9.4, 1.45 + i * 1.6, 3.3, b, l, { size: 38, color: C.accent2 }));
  bullets(s, tr ? ["CAT III (RVR < 350 m): 1 saatte durumların %76'sı doğru", "CAT II: dar geçiş bandı, komşu sınıflarla karışıyor", "Kalıcılık RPSS: 0,43 → −0,17 → −0,70"]
                : ["CAT III (RVR < 350 m): 76% correct at 1 h", "CAT II: narrow transitional band, often confused", "Persistence RPSS: 0.43 → −0.17 → −0.70"],
    0.6, 4.85, 8.3, 1.8, 16);
}
{
  const s = slide("CONTENT", tr ? "Açıklanabilirlik: model sis fiziğini öğrenmiş" : "Explainability: the model learnt fog physics",
    tr ? "SHAP analizi en güçlü kanıt: 1 saatte tahmini anlık nem ve görüş belirliyor, katkının yüzde 78'i. 6 saatte bu pay yüzde 41'e iniyor; Güneş/takvim terimleri yüzde 28'e, sınır tabaka belleği yüzde 21'e çıkıyor. Bağımlılık grafikleri ders kitabı fiziği: çiy noktası farkı 2 derecenin altındaysa sis riski artıyor, rüzgâr 3 knotun üzerindeyse karışım sisi bastırıyor, Güneş yükseldiğinde sis dağılıyor."
       : "SHAP shows the current state dominates at 1 h (78%), while at 6 h sun/calendar (28%) and boundary-layer memory (21%) rise. Dependence plots reproduce textbook physics: T−Td ≤ 2 °C raises the risk, winds > 3 kt suppress fog, sunrise dissipates it.");
  image(s, "shap_groups.png", 0.6, 1.35, 4.6, 2.75);
  bullets(s, tr ? ["1 sa: anlık nem ve görüş (%78)", "6 sa: Güneş/takvim %28, bellek %21", "T−Td ≤ 2 °C ve rüzgâr ≤ 3 kt → sis", "Gün doğumundan sonra → dağılma"]
                : ["1 h: current humidity and visibility (78%)", "6 h: sun/calendar 28%, memory 21%", "T−Td ≤ 2 °C and wind ≤ 3 kt → fog", "After sunrise → dissipation"],
    5.6, 1.5, 7.1, 2.6, 17);
  image(s, "shap_dependence.png", 0.6, 4.35, 12.1, 2.65);
}
{
  const s = slide("CONTENT", tr ? "Olay incelemesi: 17–18 Aralık 2022" : "Case study: 17–18 December 2022",
    tr ? "Test döneminden iki aşamalı bir olay. Sis öğleden sonra açılıyor, 16:50 UTC'de yeniden oluşuyor. 16:20'de görüş henüz 1200 metreyken 3 saatlik model yüzde 82 olasılıkla doğru uyarı veriyor. Sağdaki SHAP açıklaması bu kararın nedenlerini gösteriyor: düşen minimum görüş, 650 metrelik RVR, 1 derecelik çiy noktası farkı ve yüzde 93 nem; yani deneyimli bir tahmincinin bakacağı ipuçları."
       : "A two-stage episode: fog cleared in the afternoon and re-formed at 16:50 UTC. At 16:20, with visibility still 1200 m, the 3-h model warned with p = 0.82. The SHAP explanation shows the reasons: falling minimum visibility, RVR 650 m, T−Td 1 °C and RH 93%.");
  image(s, "case_study.png", 0.6, 1.4, 8.15, 2.5);
  image(s, "shap_waterfall.png", 8.95, 1.35, 3.75, 3.45);
  stat(s, 0.6, 4.35, 3.8, tr ? "p = 0,82" : "p = 0.82", tr ? "16:20 UTC'de 3 sa sonrası için sis olasılığı (eşik 0,33)" : "fog probability for +3 h issued at 16:20 UTC (threshold 0.33)", { size: 38, color: C.accent3, lh: 0.8 });
  stat(s, 4.6, 4.35, 4.1, tr ? "30 dk" : "30 min", tr ? "sonra sis oluştu (16:50 UTC)" : "later, fog formed (16:50 UTC)", { size: 38, lh: 0.8 });
}

newSection(tr ? "Uygulama ve sonuç" : "Application and conclusion");
{
  const s = slide("CONTENT", tr ? "Canlı erken uyarı uygulaması" : "Live early-warning application",
    tr ? "Uygulama her on dakikada son METAR'ları çekiyor, aynı işlem hattından geçiriyor ve 1–6 saat için olasılık, ILS görünümü, uyarı seviyesi ve SHAP açıklamaları gösteriyor. Her tahmin veritabanına kaydedilip geçerlilik saati gelince otomatik doğrulanıyor. Eşdeğerlik testinde 240 karşılaştırmada fark sıfır. Temmuz–Ekim 2026 yeniden oynatmasında sis yoktu ve sistem tek bir yanlış alarm vermedi; canlı kayıt dönem boyunca sürüyor."
       : "Every 10 minutes the app fetches the latest METARs, runs the same pipeline and shows 1–6 h probabilities, the ILS outlook, an alert level and SHAP explanations. Every forecast is logged and verified automatically. Parity test: zero difference in 240 comparisons. July–October 2026 replay: no fog and not a single false alarm.");
  image(s, "app_screenshot.png", 0.6, 1.3, 5.75, 5.58);
  bullets(s, tr ? ["Her 10 dakikada canlı METAR (NOAA AWC, yedek IEM)", "Eğitimle birebir aynı işlem hattı: eşdeğerlik testinde fark 0,0",
                   "Kademeli uyarı: yeşil / sarı (izleme) / turuncu / kırmızı", "Her tahmin için SHAP tabanlı etkili faktörler",
                   "SQLite kaydı ve otomatik gerçek zamanlı doğrulama", "Temmuz–Ekim 2026: 5 700+ tahmin, 0 yanlış alarm", "Açık kaynak: FastAPI + saf HTML/CSS/JS"]
                : ["Live METARs every 10 min (NOAA AWC, IEM fallback)", "Identical pipeline to training: parity difference 0.0",
                   "Tiered alerts: green / yellow (watch) / orange / red", "SHAP-based driving factors for every forecast",
                   "SQLite log with automatic real-time verification", "July–October 2026: 5,700+ forecasts, 0 false alarms", "Open source: FastAPI + plain HTML/CSS/JS"],
    6.75, 1.45, 5.95, 5.3, 17);
}
{
  const s = slide("CLOSING_DARK", tr ? "Sonuç" : "Conclusion",
    tr ? "Özetle: Esenboğa için ilk makine öğrenmesi tabanlı sis tahmin sistemini geliştirdim; tüm modeller kalıcılığı ve resmî TREND tahminini anlamlı biçimde geçiyor, modeller sis fiziğiyle tutarlı ve sistem canlı çalışıyor. Gelecekte sayısal model ve uydu verisiyle başlangıç tespitini iyileştirmeyi, TAF karşılaştırmasını tam sezona genişletmeyi ve diğer havalimanlarına aktarmayı planlıyorum. Veri, kod ve uygulama GitHub'da açık. Teşekkürler; sorularınızı alabilirim."
       : "In summary: the first ML fog nowcast for Esenboğa; all models beat persistence and the official TREND; the models are physically consistent and run live. Future work: NWP and satellite predictors, full-season TAF comparison, transfer to other airports. Thank you — questions are welcome.");
  const pts = tr ? [["0,73 / 0,47 / 0,34", "en iyi CSI (1/3/6 sa); kalıcılık 0,65 / 0,32 / 0,13"],
                    ["+0,105 CSI", "1 saatte resmî METAR TREND tahminine göre (anlamlı)"],
                    ["Fiziksel tutarlılık", "SHAP: doygunluk, zayıf karışım, ışınım döngüsü"]]
                 : [["0.73 / 0.47 / 0.34", "best CSI at 1/3/6 h; persistence 0.65 / 0.32 / 0.13"],
                    ["+0.105 CSI", "over the official METAR TREND at 1 h (significant)"],
                    ["Physically consistent", "SHAP: saturation, weak mixing, radiative cycle"]];
  pts.forEach(([b, l], i) => {
    const x = 0.6 + i * 4.15;
    s.addText(b, { x, y: 1.55, w: 3.9, h: 0.8, fontFace: "Cambria", fontSize: 28, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    s.addText(l, { x, y: 2.35, w: 3.8, h: 0.9, fontSize: 15, color: HEX.lt2, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText(tr ? "Gelecek çalışmalar" : "Future work", { x: 0.6, y: 3.65, w: 6, h: 0.5, fontFace: "Cambria", fontSize: 20, bold: true, color: C.background1, margin: 0, isTextBox: true });
  s.addText((tr ? ["Sayısal hava tahmini, uydu ve seilometre öznitelikleri ile başlangıç tespiti", "Tam sis sezonlarında TAF karşılaştırması (canlı kayıt)", "Diğer Türk havalimanlarına aktarım"]
                : ["NWP, satellite and ceilometer predictors for onset detection", "Full-season TAF comparison (live log)", "Transfer to other Turkish airports"])
              .map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })),
    { x: 0.6, y: 4.2, w: 7.6, h: 1.6, fontSize: 16, color: HEX.lt2, paraSpaceAfter: 6, margin: 0.05, valign: "top", isTextBox: true });
  s.addText("github.com/AtaSakik/esenboga-fog-nowcasting", { x: 0.6, y: 6.25, w: 8, h: 0.45, fontSize: 16, color: C.accent1, margin: 0, isTextBox: true,
    hyperlink: { url: "https://github.com/AtaSakik/esenboga-fog-nowcasting" } });
  s.addText(tr ? "Teşekkürler" : "Thank you", { x: 8.9, y: 5.7, w: 3.8, h: 0.9, fontFace: "Cambria", fontSize: 36, bold: true, color: C.background1, align: "right", margin: 0, isTextBox: true });
}

// ------------------------------------------------------------------ write + theme
const out = path.join(__dirname, tr ? "Esenboga_Sunum_TR.pptx" : "Esenboga_Presentation_EN.pptx");
pres.writeFile({ fileName: out }).then(async () => {
  if (APPLY_THEME) {
    const { applyTheme } = require(APPLY_THEME);
    await applyTheme(out, THEME);
  }
  console.log("wrote", out);
});
