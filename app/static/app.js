"use strict";

// Esenboğa fog forecast dashboard. The same page runs behind the FastAPI server (live endpoints)
// and as the static GitHub Pages copy (JSON files with the same names), so all paths are relative.

const TZ = "Europe/Istanbul";
const LAT = 40.1281, LON = 32.9951;
const HOUR = 3600e3;

const I18N = {
  tr: {
    locale: "tr-TR",
    docTitle: "Esenboğa Sis Tahmini",
    skip: "İçeriğe geç",
    brand: "Esenboğa Sis Tahmini",
    brandSub: "Ankara Esenboğa Havalimanı, önümüzdeki 6 saat",
    loading: "Tahmin yükleniyor…",
    errTitle: "Tahmin şu an gösterilemiyor.",
    errText: "Veriye ulaşılamadı. Birkaç dakika sonra sayfayı yenileyin.",
    sceneAria: "Pistin şu anki görünümünü, ölçülen görüş mesafesine göre canlandıran çizim",
    sceneCap: (v) => `Şu an görüş: ${v}`,
    levels: { green: "Düşük risk", yellow: "Dikkat", orange: "Sis uyarısı", red: "Sis uyarısı", redNow: "Sis var" },
    headline: {
      green: "Önümüzdeki 6 saatte sis beklenmiyor.",
      yellow: "Sis olasılığı artıyor.",
      orange: "Birkaç saat içinde sis bekleniyor.",
      red: "Sis 2 saat içinde bekleniyor.",
      redNow: "Havalimanında şu an sis var.",
    },
    sumGreen: (t, p, thr) => `En yüksek sis olasılığı saat ${t} için ${p}. Bu, o saatin uyarı sınırının (${thr}) altında.`,
    sumYellow: (t, p, thr) => `Saat ${t} için sis olasılığı ${p}, uyarı sınırı ise ${thr}. Henüz uyarı yok ama durum değişebilir.`,
    sumWarn: (t, p, thr) => `Saat ${t} için sis olasılığı ${p} ve uyarı sınırını (${thr}) geçiyor. Uçuşunuz varsa havayolu şirketinizin duyurularını takip edin.`,
    sumNow: (v) => `Şu an görüş mesafesi ${v}. Uçuşlarda gecikmeler olabilir; havayolu şirketinizin duyurularını takip edin.`,
    stamp: (d, t) => `Son ölçüm: ${d}, saat ${t} (Türkiye saati). Sayfa her yarım saatte bir güncellenir.`,
    stale: (h) => `Dikkat: veriler ${h} saattir güncellenmedi, bu tahmin eskimiş olabilir.`,

    hoursTitle: "Saat saat sis olasılığı",
    hoursLead: "Her satır, o saatte havalimanında sis olma olasılığını gösterir. Çubuğun üzerindeki ince dikey çizgi uyarı sınırıdır: olasılık bu çizgiyi geçerse sistem sis uyarısı verir.",
    hoursHint: "Bir satıra dokunduğunuzda, aşağıda o saatin tahmininin nedenleri açıklanır.",
    after: (h) => `${h} saat sonra`,
    risk: { low: "Düşük", mid: "Orta", high: "Yüksek" },
    rowAria: (t, h, p, r) => `Saat ${t}, ${h} saat sonra: sis olasılığı ${p}, ${r}. Nedenlerini göster.`,
    lessThan1: "%1'den az",

    whyTitle: (t) => `Saat ${t} tahmini neden böyle?`,
    whyLead: "Sis nadir görülen bir olaydır (yılın yaklaşık %1'i), bu yüzden model düşük bir başlangıç olasılığından yola çıkar. Sonra nem, rüzgâr, bulutlar ve günün saati gibi 77 ayrı bilgiye bakarak bu olasılığı artırır ya da azaltır. Bu saat için en etkili olanlar aşağıda; çubuk uzadıkça etki güçlenir.",
    whyUp: "Sis olasılığını artıranlar",
    whyDown: "Sis olasılığını azaltanlar",
    whyNone: "Belirgin bir etken yok.",
    strength: ["zayıf etki", "orta etki", "güçlü etki"],
    whyTech: "Teknik ayrıntı: modelin en etkili 8 değişkeni",
    whyTechNote: "Katkılar SHAP yöntemiyle hesaplanmıştır (log-odds birimi). Artı değerler sis olasılığını artırır, eksi değerler azaltır.",
    shapCols: ["Değişken", "Değer", "Katkı"],
    factors: {
      humidity: ["Nem", "Hava neme doydukça su buharı yoğunlaşır ve sis damlacıkları oluşur."],
      visibility: ["Görüş mesafesi", "Görüş azalmaya başladıysa sis daha olasıdır; hava çok açıksa birkaç saat içinde sis oluşması zordur."],
      temperature: ["Sıcaklık", "Hava soğudukça çiy noktasına yaklaşır."],
      wind: ["Rüzgâr", "Sakin havada sis kolay oluşur; rüzgâr havayı karıştırıp sisi dağıtır."],
      clouds: ["Bulutlar", "Açık gecelerde yer hızla soğur; bulutlar bu soğumayı yavaşlatır."],
      precipitation: ["Yağış ve kar", "Yağış havayı nemlendirir; kar örtüsü yerin soğumasını artırır."],
      recent_fog: ["Son günlerdeki sis", "Yakın zamanda sis olduysa koşullar hâlâ sise elverişli olabilir."],
      time_of_day: ["Günün saati", "Sis en çok gece ve gün doğumu civarında oluşur; güneş yükselince dağılır."],
      season: ["Mevsim", "Esenboğa'da sislerin %95'i Ekim–Şubat arasında görülür."],
      pressure: ["Hava basıncı", "Yüksek basınç genellikle sakin ve açık hava getirir; bu da sise uygun bir ortam demektir."],
    },
    ev: {
      humidity: (rh, d) => `Nem ${rh}; sıcaklık çiy noktasının ${d} °C üzerinde.`,
      humiditySat: (rh) => `Nem ${rh}; sıcaklık çiy noktasına eşit, hava neme doymuş.`,
      visibility: (v) => `Görüş şu an ${v}.`,
      visibilityFog: (v) => `Görüş şu an ${v}; havalimanında sis var.`,
      temperature: (t) => `Sıcaklık ${t}.`,
      wind: (w) => `Rüzgâr: ${w}.`,
      clouds: (m) => `Bulut tabanı ${m}.`,
      noClouds: "Yoğun bulut katmanı yok.",
      precip: (w) => `Şu an yağış var: ${w}.`,
      noPrecip: "Şu an yağış yok.",
      recentFog: "Son 48 saat içinde sis görüldü.",
      noRecentFog: "Son 48 saatte sis görülmedi.",
      day: "Gündüz; güneş yüksekte olacak.",
      morning: "Gün doğumundan hemen sonraki saatler.",
      evening: "Gün batımına yakın saatler.",
      dawn: "Gün doğumundan hemen önceki saatler.",
      night: "Gece saatleri.",
      season: (m) => `${m}: sis mevsimi (Ekim–Şubat).`,
      offSeason: (m) => `${m}: sis mevsiminin dışında.`,
      pressure: (q) => `Hava basıncı ${q}.`,
    },

    landTitle: "Uçuşlara olası etkisi",
    landLead: "Sis yoğunlaştıkça pilotun pisti görebildiği mesafe kısalır. Bu mesafe azaldıkça iniş için daha gelişmiş sistemler gerekir ve gecikmeler başlayabilir.",
    landOk: "Önümüzdeki 6 saatte inişlerin normal koşullarda sürmesi bekleniyor.",
    landSome: "Düşük görüş nedeniyle bazı uçuşlarda gecikme olabilir.",
    landSevere: "Çok düşük görüş bekleniyor; gecikmeler ve başka havalimanlarına yönlendirmeler olabilir.",
    landNormal: (p) => `${p} normal`,
    landAria: (a, b, c) => `Normal iniş ${a}, özel prosedürle iniş ${b}, çok düşük görüş ${c}`,
    cats: [
      ["Normal iniş", "Pist görüş mesafesi 550 metre ya da daha fazla."],
      ["Özel prosedürle iniş", "Yaklaşık 350–550 metre. Yalnızca bu koşullar için donatılmış uçaklar ve eğitimli pilotlar (CAT II) inebilir."],
      ["Çok düşük görüş", "350 metrenin altı. Yalnızca en gelişmiş iniş sistemlerine (CAT III) sahip uçaklar inebilir."],
    ],

    nowTitle: "Şu an havalimanında",
    nowLead: (t) => `Havalimanının son hava raporuna göre (saat ${t}).`,
    facts: { vis: "Görüş mesafesi", temp: "Sıcaklık", dew: "Çiy noktası", rh: "Nem", wind: "Rüzgâr", ceil: "Bulut tabanı", qnh: "Hava basıncı", rvr: "Pist görüş mesafesi", wx: "Hava olayı" },
    visMax: "10 km'den fazla",
    noCeil: "Yoğun bulut yok",
    calm: "sakin",
    dirs: ["kuzeyden", "kuzeydoğudan", "doğudan", "güneydoğudan", "güneyden", "güneybatıdan", "batıdan", "kuzeybatıdan"],
    varDir: "değişken yönlerden",
    wind: (dir, v) => `${dir} ${v} km/sa`,
    spread: (d) => `Sıcaklık ile çiy noktası arasında ${d} °C fark var. Bu fark sıfıra yaklaştıkça hava neme doyar ve sis oluşabilir.`,
    rawSummary: "Ham hava raporu (METAR)",
    rawNote: "Bu, havalimanının yayımladığı uluslararası kodlu rapordur. Yukarıdaki değerler bu rapordan çözüldü.",
    wx: {
      int: { "-": "hafif", "+": "kuvvetli" }, vc: (w) => `civarda ${w}`, and: " ve ",
      desc: { MI: "sığ", PR: "kısmi", BC: "yer yer", DR: "alçakta savrulan", BL: "savrulan", SH: "sağanak", TS: "gök gürültülü", FZ: "donan" },
      alone: { SH: "sağanak", TS: "gök gürültülü fırtına" },
      phen: { FG: "sis", BR: "pus", HZ: "kurudumanı", FU: "duman", DZ: "çisenti", RA: "yağmur", SN: "kar", SG: "kar taneleri", PL: "buz taneleri", GR: "dolu", GS: "küçük dolu", DU: "toz", SA: "kum", SQ: "bora", UP: "yağış" },
      special: { MIFG: "yer sisi" },
    },

    histTitle: "Son 48 saat",
    histLead: "Koyu çizgi ölçülen görüş mesafesidir; kırmızı kesikli çizginin (1 km) altına inerse sis var demektir. Alttaki şerit, her saat için 3 saat önceden verilmiş sis olasılığını gösterir.",
    chartAria: "Son 48 saatte ölçülen görüş mesafesi ve 3 saat önceden verilen sis olasılığı",
    fogZone: "sis",
    nowMark: "şimdi",
    limit: "uyarı sınırı",
    lgVis: "Ölçülen görüş mesafesi",
    lgFog: "Sis sınırı (1 km)",
    lgProb: "3 saat önceden verilen sis olasılığı",
    lgRvr: "Pist görüş mesafesi",

    verTitle: "Tahminler tuttu mu?",
    verLead: "Sistem her yarım saatte bir tahmin yapıp kaydeder. Tahmin edilen saat gelince, gerçekleşen havayla karşılaştırır.",
    verNone: "Henüz saati gelmiş bir tahmin yok. İlk karşılaştırmalar birkaç saat içinde burada görünecek.",
    verSince: (d, n) => `${d} tarihinden bu yana ${n} tahmin gerçekleşen havayla karşılaştırıldı.`,
    verQuiet: "Bu sürede havalimanında sis görülmedi; sistem de hiç gereksiz uyarı vermedi.",
    verQuietFA: (f) => `Bu sürede havalimanında sis görülmedi; sistem ${f} tahminde gereksiz uyarı verdi.`,
    verEvents: (e, h, m, f) => `Sis görülen anlar için verilen ${e} tahminin ${h} tanesinde sistem önceden uyarmıştı, ${m} tanesinde uyaramadı. Sis olmayan anlarda ise ${f} tahminde gereksiz uyarı verdi.`,
    verTest: "Model, eğitiminde hiç kullanılmamış dört kışlık veriyle (2022–2026) de sınandı. 1 saat önceden verilen tahminler sisli anların %83'ünü yakaladı ve verilen uyarıların %86'sı doğru çıktı. Süre uzadıkça isabet düşer: 3 saat önceden sisli anların %59'u, 6 saat önceden %52'si yakalandı ve 6 saatlik uyarıların yarıdan fazlası boşa çıktı. Uzak saatlerdeki uyarıları bu yüzden bir “dikkat” işareti olarak okuyun.",
    verTech: "Ayrıntılı doğrulama tablosu",
    verCols: ["Kayıt", "Süre", "Tahmin", "Sis", "İsabet", "Gereksiz uyarı", "Kaçırılan", "POD", "FAR", "CSI", "Brier"],
    live: "Canlı",
    replay: "Geriye dönük",
    lead: (h) => `${h} sa`,
    verTechNote: "Canlı: sistemin gerçek zamanlı kayıtları. Geriye dönük: sistem ilk açıldığında önceki 72 saatin aynı kodla yeniden hesaplanması. POD, sislerin ne kadarının önceden bildirildiğini (isabet oranı); FAR, uyarıların ne kadarının boşa çıktığını (yanlış alarm oranı) gösterir. CSI kritik başarı indeksidir, 1 en iyisidir. Brier skoru olasılık hatasıdır, 0 en iyisidir. Hiç sis görülmediyse POD, FAR ve CSI hesaplanamaz (–).",

    aboutTitle: "Bu site nasıl çalışıyor?",
    step1: "Esenboğa'nın son 5 güne ait hava raporları her yarım saatte bir otomatik olarak indirilir.",
    step2: "2005–2019 yıllarının gözlemleriyle eğitilen bir yapay zekâ modeli (LightGBM), önümüzdeki 1–6 saatin her biri için sis olasılığını hesaplar.",
    step3: "Her tahmin kaydedilir ve saati gelince gerçekleşen havayla karşılaştırılır. Sonuçlar “Tahminler tuttu mu?” bölümünde herkese açıktır.",
    climate: "Esenboğa'da yılda ortalama 90 saat kadar sis görülür. Sislerin %95'i Ekim–Şubat arasında oluşur; en sık sabah 08.00 civarında görülür ve güneş yükseldikçe çoğu dağılır.",
    disclaimer: "Bu site, Ankara Üniversitesi Yazılım Mühendisliği Bölümü öğrencisi Ata Sakik'in YMH453 Makine Öğrenmesi dersi için hazırladığı bir araştırma projesidir; resmî tahmin değildir. Resmî hava bilgisi için Meteoroloji Genel Müdürlüğünü (MGM), uçuşunuzun durumu için havayolu şirketinizi takip edin.",
    linkCode: "Kaynak kodu, verileri ve makaleyi GitHub'da inceleyin",

    termsTitle: "Terimler",
    terms: [
      ["Sis", "Yere yakın havada asılı duran çok küçük su damlacıklarının (çok soğukta buz kristallerinin) görüş mesafesini 1 kilometrenin altına düşürmesi."],
      ["Pus", "Sisin hafif hâli. Hava nemli ve bulanıktır ama görüş 1 ile 5 kilometre arasındadır."],
      ["Görüş mesafesi", "Yatay doğrultuda nesnelerin seçilebildiği en uzak mesafe. Hava raporunda 10 km ve üzeri “9999” diye yazılır."],
      ["Pist görüş mesafesi (RVR)", "Pistteki bir pilotun pist ışıklarını ya da çizgilerini görebildiği mesafe. Pist boyunca cihazlarla ölçülür ve görüş düştüğünde raporlanır."],
      ["Çiy noktası", "Hava bu sıcaklığa kadar soğursa içindeki su buharı yoğunlaşmaya başlar; yoğunlaşma sıcaklığı da denir. Sıcaklık çiy noktasına yaklaştıkça sis olasılığı artar."],
      ["Nem", "Bağıl nem: havadaki su buharının, havanın o sıcaklıkta taşıyabileceği en yüksek miktara oranı. %100'e yaklaştıkça hava neme doyar."],
      ["Sis olasılığı", "Model iyi ayarlanmış (kalibre edilmiş) olasılıklar üretir: %20 sis olasılığı, geçmişte benzer koşulların yaklaşık beşte birinde sis oluştuğu anlamına gelir."],
      ["Uyarı sınırı", "Her tahmin saati için, geçmiş yıllarda en isabetli sonucu veren olasılık değeri. Olasılık bu sınırı geçerse sistem sis uyarısı verir."],
      ["METAR", "Havalimanlarının yarım saatte bir yayımladığı uluslararası kodlu hava raporu. Hava aniden değişirse ara rapor (SPECI) yayımlanır."],
      ["Aletli iniş sistemi (ILS)", "Görüş düşükken uçakları radyo sinyalleriyle piste yönlendiren sistem. Kategorileri (CAT I, II, III), ne kadar düşük görüşte iniş yapılabileceğini belirler."],
    ],
    foot: "Veri kaynakları: NOAA Aviation Weather Center (ABD) ve Iowa Environmental Mesonet. Kod, MIT lisansıyla açık kaynaktır.",
  },

  en: {
    locale: "en-GB",
    docTitle: "Esenboğa Fog Forecast",
    skip: "Skip to content",
    brand: "Esenboğa Fog Forecast",
    brandSub: "Ankara Esenboğa Airport, the next 6 hours",
    loading: "Loading the forecast…",
    errTitle: "The forecast can't be shown right now.",
    errText: "The data could not be reached. Reload the page in a few minutes.",
    sceneAria: "Drawing of the runway as it looks now, based on the measured visibility",
    sceneCap: (v) => `Visibility now: ${v}`,
    levels: { green: "Low risk", yellow: "Watch", orange: "Fog warning", red: "Fog warning", redNow: "Fog now" },
    headline: {
      green: "No fog expected in the next 6 hours.",
      yellow: "The chance of fog is rising.",
      orange: "Fog is expected within a few hours.",
      red: "Fog is expected within 2 hours.",
      redNow: "There is fog at the airport now.",
    },
    sumGreen: (t, p, thr) => `The highest chance of fog is ${p}, for ${t}. That is below the warning level for that hour (${thr}).`,
    sumYellow: (t, p, thr) => `The chance of fog for ${t} is ${p}; the warning level is ${thr}. No warning yet, but this can change.`,
    sumWarn: (t, p, thr) => `The chance of fog for ${t} is ${p}, above the warning level (${thr}). If you are flying, follow your airline's updates.`,
    sumNow: (v) => `Visibility is ${v} right now. Flights may be delayed; follow your airline's updates.`,
    stamp: (d, t) => `Latest observation: ${d}, ${t} (Turkey time). The page updates every half hour.`,
    stale: (h) => `Note: the data has not been updated for ${h} hours, so this forecast may be out of date.`,

    hoursTitle: "Fog chance hour by hour",
    hoursLead: "Each row shows the chance of fog at the airport at that time. The thin vertical line on each bar is the warning level: if the chance crosses it, the system issues a fog warning.",
    hoursHint: "Select a row to see below what drives the forecast for that hour.",
    after: (h) => (h === 1 ? "in 1 hour" : `in ${h} hours`),
    risk: { low: "Low", mid: "Medium", high: "High" },
    rowAria: (t, h, p, r) => `${t}, ${h === 1 ? "in 1 hour" : `in ${h} hours`}: chance of fog ${p}, ${r}. Show the reasons.`,
    lessThan1: "<1%",

    whyTitle: (t) => `Why this forecast for ${t}?`,
    whyLead: "Fog is rare (about 1% of the year), so the model starts from a low baseline chance. It then raises or lowers that chance using 77 pieces of information such as humidity, wind, clouds and the time of day. The most influential ones for this hour are below; the longer the bar, the stronger the effect.",
    whyUp: "Raising the chance of fog",
    whyDown: "Lowering the chance of fog",
    whyNone: "No notable factor.",
    strength: ["weak effect", "moderate effect", "strong effect"],
    whyTech: "Technical detail: the model's 8 most influential variables",
    whyTechNote: "Contributions are SHAP values (log-odds units). Positive values raise the chance of fog, negative values lower it.",
    shapCols: ["Variable", "Value", "Contribution"],
    factors: {
      humidity: ["Humidity", "As the air nears saturation, water vapour condenses into fog droplets."],
      visibility: ["Visibility", "If visibility is already dropping, fog is more likely; in very clear air fog rarely forms within a few hours."],
      temperature: ["Temperature", "As the air cools it gets closer to its dew point."],
      wind: ["Wind", "Fog forms easily in calm air; wind mixes the air and clears it."],
      clouds: ["Clouds", "On clear nights the ground cools quickly; clouds slow that cooling."],
      precipitation: ["Rain and snow", "Rain moistens the air; snow cover makes the ground cool faster."],
      recent_fog: ["Recent fog", "If there was fog recently, conditions may still favour it."],
      time_of_day: ["Time of day", "Fog forms mostly at night and around sunrise, and clears as the sun climbs."],
      season: ["Season", "95% of the fog at Esenboğa occurs between October and February."],
      pressure: ["Air pressure", "High pressure usually brings calm, clear weather, which favours fog."],
    },
    ev: {
      humidity: (rh, d) => `Humidity ${rh}; the temperature is ${d} °C above the dew point.`,
      humiditySat: (rh) => `Humidity ${rh}; the temperature equals the dew point, so the air is saturated.`,
      visibility: (v) => `Visibility is ${v} right now.`,
      visibilityFog: (v) => `Visibility is ${v} right now; there is fog at the airport.`,
      temperature: (t) => `Temperature ${t}.`,
      wind: (w) => `Wind: ${w}.`,
      clouds: (m) => `Cloud base ${m}.`,
      noClouds: "No thick cloud layer.",
      precip: (w) => `Precipitation now: ${w}.`,
      noPrecip: "No precipitation now.",
      recentFog: "There was fog within the last 48 hours.",
      noRecentFog: "No fog in the last 48 hours.",
      day: "Daytime; the sun will be high.",
      morning: "The hours just after sunrise.",
      evening: "Close to sunset.",
      dawn: "The hours just before sunrise.",
      night: "Night time.",
      season: (m) => `${m}: fog season (October–February).`,
      offSeason: (m) => `${m}: outside the fog season.`,
      pressure: (q) => `Air pressure ${q}.`,
    },

    landTitle: "Possible effect on flights",
    landLead: "As fog thickens, the distance a pilot can see along the runway gets shorter. The shorter it is, the more advanced the systems needed to land, and delays can start.",
    landOk: "Landings are expected to continue under normal conditions for the next 6 hours.",
    landSome: "Some flights may be delayed by low visibility.",
    landSevere: "Very low visibility is expected; delays and diversions to other airports are possible.",
    landNormal: (p) => `${p} normal`,
    landAria: (a, b, c) => `Normal landing ${a}, landing with special procedures ${b}, very low visibility ${c}`,
    cats: [
      ["Normal landing", "Runway visual range of 550 metres or more."],
      ["Landing with special procedures", "About 350–550 metres. Only aircraft equipped for these conditions, with trained pilots (CAT II), can land."],
      ["Very low visibility", "Below 350 metres. Only aircraft with the most advanced landing systems (CAT III) can land."],
    ],

    nowTitle: "At the airport now",
    nowLead: (t) => `From the airport's latest weather report (${t}).`,
    facts: { vis: "Visibility", temp: "Temperature", dew: "Dew point", rh: "Humidity", wind: "Wind", ceil: "Cloud base", qnh: "Air pressure", rvr: "Runway visual range", wx: "Weather" },
    visMax: "more than 10 km",
    noCeil: "No thick cloud",
    calm: "calm",
    dirs: ["the north", "the north-east", "the east", "the south-east", "the south", "the south-west", "the west", "the north-west"],
    varDir: "variable directions",
    wind: (dir, v) => `${v} km/h from ${dir}`,
    spread: (d) => `The temperature is ${d} °C above the dew point. As this gap closes, the air becomes saturated and fog can form.`,
    rawSummary: "Raw weather report (METAR)",
    rawNote: "This is the coded international report issued by the airport. The values above are decoded from it.",
    wx: {
      int: { "-": "light", "+": "heavy" }, vc: (w) => `${w} in the vicinity`, and: " and ",
      desc: { MI: "shallow", PR: "partial", BC: "patchy", DR: "drifting", BL: "blowing", SH: "showers of", TS: "thunderstorm with", FZ: "freezing" },
      alone: { SH: "showers", TS: "thunderstorm" },
      phen: { FG: "fog", BR: "mist", HZ: "haze", FU: "smoke", DZ: "drizzle", RA: "rain", SN: "snow", SG: "snow grains", PL: "ice pellets", GR: "hail", GS: "small hail", DU: "dust", SA: "sand", SQ: "squalls", UP: "precipitation" },
      special: {},
    },

    histTitle: "The last 48 hours",
    histLead: "The dark line is the measured visibility; when it drops below the red dashed line (1 km) there is fog. The strip below shows the chance of fog that was forecast 3 hours earlier for each time.",
    chartAria: "Measured visibility over the last 48 hours and the chance of fog forecast 3 hours earlier",
    fogZone: "fog",
    nowMark: "now",
    limit: "warning level",
    lgVis: "Measured visibility",
    lgFog: "Fog limit (1 km)",
    lgProb: "Chance of fog forecast 3 hours earlier",
    lgRvr: "Runway visual range",

    verTitle: "Were the forecasts right?",
    verLead: "Every half hour the system makes and stores a forecast. When the forecast time arrives, it is compared with the actual weather.",
    verNone: "No forecast has reached its time yet. The first comparisons will appear here within a few hours.",
    verSince: (d, n) => `Since ${d}, ${n} forecasts have been compared with the actual weather.`,
    verQuiet: "There has been no fog at the airport in that time, and the system has not issued a single unnecessary warning.",
    verQuietFA: (f) => `There has been no fog at the airport in that time; the system issued an unnecessary warning in ${f} forecasts.`,
    verEvents: (e, h, m, f) => `Of ${e} forecasts for times with fog, the system had warned in ${h} and missed ${m}. For times without fog, it issued an unnecessary warning in ${f} forecasts.`,
    verTest: "The model was also tested on four winters of data it never saw in training (2022–2026). Forecasts made 1 hour ahead caught 83% of foggy times, and 86% of the warnings were correct. Accuracy drops with lead time: 59% of foggy times were caught 3 hours ahead and 52% 6 hours ahead, and more than half of the 6-hour warnings were false alarms. Read warnings for later hours as a heads-up.",
    verTech: "Detailed verification table",
    verCols: ["Record", "Lead", "Forecasts", "Fog", "Hits", "False alarms", "Misses", "POD", "FAR", "CSI", "Brier"],
    live: "Live",
    replay: "Replay",
    lead: (h) => `${h} h`,
    verTechNote: "Live: the system's real-time records. Replay: the 72 hours before the first start, recomputed with the same code. POD is the share of fog that was forecast (hit rate); FAR is the share of warnings that were false alarms. CSI is the critical success index (1 is best). The Brier score is the probability error (0 is best). Without any fog, POD, FAR and CSI cannot be computed (–).",

    aboutTitle: "How this site works",
    step1: "Esenboğa's weather reports for the last 5 days are downloaded automatically every half hour.",
    step2: "A machine-learning model (LightGBM), trained on observations from 2005–2019, computes the chance of fog for each of the next 1 to 6 hours.",
    step3: "Every forecast is stored and compared with the actual weather when its time comes. The results are public under “Were the forecasts right?”.",
    climate: "Esenboğa sees about 90 hours of fog a year. 95% of it forms between October and February, most often around 08:00 in the morning, and most of it clears as the sun climbs.",
    disclaimer: "This site is a research project by Ata Sakik, a Software Engineering student at Ankara University, for the YMH453 Machine Learning course. It is not an official forecast: for official weather information follow the Turkish State Meteorological Service (MGM), and for your flight follow your airline.",
    linkCode: "Source code, data and paper on GitHub",

    termsTitle: "Glossary",
    terms: [
      ["Fog", "Tiny water droplets (ice crystals in severe cold) hanging in the air near the ground that bring visibility below 1 kilometre."],
      ["Mist", "A light form of fog. The air is damp and hazy, but visibility stays between 1 and 5 kilometres."],
      ["Visibility", "The greatest horizontal distance at which objects can be made out. Weather reports write 10 km or more as “9999”."],
      ["Runway visual range (RVR)", "How far a pilot on the runway can see the runway lights or markings. It is measured by instruments along the runway and reported when visibility drops."],
      ["Dew point", "If the air cools to this temperature, its water vapour starts to condense. The closer the temperature is to the dew point, the more likely fog becomes."],
      ["Humidity", "Relative humidity: the water vapour in the air as a share of the most the air can hold at that temperature. Near 100% the air is saturated."],
      ["Chance of fog", "The model produces well-calibrated probabilities: a 20% chance of fog means that fog formed in about one in five similar situations in the past."],
      ["Warning level", "For each forecast hour, the probability that gave the most accurate warnings in past years. If the chance crosses it, the system issues a fog warning."],
      ["METAR", "The coded international weather report that airports issue every half hour. If the weather changes suddenly, an extra report (SPECI) is issued."],
      ["Instrument landing system (ILS)", "A system that guides aircraft to the runway with radio signals when visibility is low. Its categories (CAT I, II, III) set how low the visibility can be for a landing."],
    ],
    foot: "Data: NOAA Aviation Weather Center (USA) and Iowa Environmental Mesonet. The code is open source under the MIT licence.",
  },
};

// ------------------------------------------------------------------ state and helpers
const URL_LANG = new URLSearchParams(location.search).get("lang");
let LANG = ["tr", "en"].includes(URL_LANG) ? URL_LANG : (storeGet("ltac-lang") === "en" ? "en" : "tr");
let DATA = null;        // api/nowcast
let LOG = [];           // api/log: 3-hour forecasts of the last 72 hours
let VER = [];           // api/verification
let PICKED = null;      // forecast hour chosen by the visitor (null: the riskiest hour)
let FAILED = false;

function storeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function storeSet(k, v) { try { localStorage.setItem(k, v); } catch { /* storage blocked */ } }
const T = () => I18N[LANG];
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (ch) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
const isNum = (x) => typeof x === "number" && Number.isFinite(x);
const cap = (s) => (s ? s.charAt(0).toLocaleUpperCase(T().locale) + s.slice(1) : s);
const f1 = (v) => v.toFixed(1);

function num(x, digits = 0) {
  return new Intl.NumberFormat(T().locale, {
    minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: Math.abs(x) >= 10000,
  }).format(x);
}
const pctLabel = (v) => (LANG === "tr" ? `%${num(v)}` : `${num(v)}%`);
const pctInt = (v) => (isNum(v) ? pctLabel(Math.round(v)) : "–");
function pct(p) {
  if (!isNum(p)) return "–";
  return p < 0.01 ? T().lessThan1 : pctLabel(Math.min(99, Math.round(p * 100)));
}

function zoned(ms, opts) { return new Intl.DateTimeFormat(T().locale, { timeZone: TZ, ...opts }).format(ms); }
function timeOf(ms) {
  const s = zoned(ms, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  return LANG === "tr" ? s.replace(":", ".") : s;   // TDK: saat ve dakika noktayla ayrılır
}
const dateOf = (ms, weekday = true) =>
  zoned(ms, { day: "numeric", month: "long", year: "numeric", ...(weekday ? { weekday: "long" } : {}) });
const localPart = (ms, part) => Number(new Intl.DateTimeFormat("en-GB", { timeZone: TZ, [part]: "numeric", hourCycle: "h23" }).format(ms));

function visText(v) {
  if (!isNum(v)) return "–";
  if (v >= 9999) return T().visMax;
  if (v >= 5000) return `${num(Math.round(v / 1000))} km`;
  if (v >= 1000) { const k = Math.round(v / 100) / 10; return `${num(k, k % 1 ? 1 : 0)} km`; }
  return `${num(Math.round(v / 10) * 10)} m`;
}
const degC = (x) => (isNum(x) ? `${num(Math.round(x))} °C` : "–");
const hPa = (x) => (isNum(x) ? `${num(Math.round(x))} hPa` : "–");

function windText(c) {
  if (!isNum(c.wind_speed_kt)) return "–";
  const kmh = Math.round(c.wind_speed_kt * 1.852);
  if (kmh < 2) return T().calm;
  const dir = isNum(c.wind_dir) ? T().dirs[Math.round(c.wind_dir / 45) % 8] : T().varDir;
  return T().wind(dir, num(kmh));
}
function ceilText(c) {
  if (!isNum(c.ceiling_ft) || c.ceiling_ft >= 20000) return null;
  return `${num(Math.max(50, Math.round((c.ceiling_ft * 0.3048) / 50) * 50))} m`;
}

// METAR present-weather groups (e.g. "-SHRA BR") in plain words.
function wxText(tokens) {
  const W = T().wx;
  const words = tokens.map((tok) => {
    if (W.special[tok]) return W.special[tok];
    const m = /^([+-])?(VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?((?:[A-Z]{2})*)$/.exec(tok);
    if (!m) return tok;
    const phen = (m[4].match(/../g) || []).map((p) => W.phen[p] || p);
    const desc = m[3] ? (phen.length ? W.desc[m[3]] : W.alone[m[3]]) : "";
    const w = [m[1] ? W.int[m[1]] : "", desc, phen.join(W.and)].filter(Boolean).join(" ");
    return m[2] ? W.vc(w) : w;
  });
  return words.length ? cap(words.join(", ")) : null;
}
const wxTokens = (wx) => String(wx || "").split(/\s+/).filter(Boolean);
const precipTokens = (wx) => wxTokens(wx).filter((t) => !t.includes("VC") && /DZ|RA|SN|SG|PL|GR|GS|UP|SH/.test(t));

// Solar elevation (degrees) at LTAC; low-precision almanac formulae, good to ~0.1°.
function sunElevation(ms) {
  const rad = Math.PI / 180, d = ms / 86400e3 - 10957.5;   // days since J2000.0
  const g = (357.529 + 0.98560028 * d) * rad;
  const lam = (280.459 + 0.98564736 * d + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * rad;
  const eps = (23.439 - 0.00000036 * d) * rad;
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam));
  const dec = Math.asin(Math.sin(eps) * Math.sin(lam));
  const ha = ((18.697374558 + 24.06570982441908 * d) % 24) * 15 * rad + LON * rad - ra;
  const lat = LAT * rad;
  return Math.asin(Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(ha)) / rad;
}

// ------------------------------------------------------------------ forecast hours
const issueMs = () => Date.parse(DATA.issue_time);
const riskOf = (ratio) => (ratio >= 1 ? "high" : ratio >= 0.5 ? "mid" : "low");
function hours() {
  return Object.keys(DATA.fog).map(Number).sort((a, b) => a - b).map((h) => {
    const f = DATA.fog[h];
    return { h, t: issueMs() + h * HOUR, p: f.p, thr: f.threshold, warn: f.warn,
             ratio: f.p / Math.max(f.threshold, 1e-6) };
  });
}
const riskiest = (list) => list.reduce((a, b) => (b.ratio > a.ratio ? b : a));
function selectedHour() {
  const list = hours();
  return list.find((d) => d.h === PICKED) || riskiest(list);
}

// ------------------------------------------------------------------ scene: the runway in today's visibility
function buildScene() {
  const W = 800, H = 260, HZ = 104, VX = 400;
  const yAt = (z) => HZ + 96 / z;           // z = 1 at the runway threshold, larger = farther
  const half = (z) => 120 / z;               // runway half-width on screen
  const dot = (x, y, r, cls, extra = "") =>
    `<circle cx="${f1(x)}" cy="${f1(y)}" r="${r.toFixed(2)}" class="${cls}"${extra}/>`;
  let lights = "", flash = "", city = "";
  for (let z = 1; z <= 24; z += 0.55) {
    const r = Math.max(0.5, 2.6 / z ** 0.75);
    lights += dot(VX - half(z), yAt(z), r, "l-edge") + dot(VX + half(z), yAt(z), r, "l-edge");
  }
  for (let z = 1.1; z <= 24; z += 0.4) lights += dot(VX, yAt(z), Math.max(0.4, 1.3 / z ** 0.75), "l-centre");
  for (let i = -8; i <= 8; i++) lights += dot(VX + i * 15, yAt(1), 2.6, "l-green");
  for (const i of [-11, -10, -9, 9, 10, 11]) lights += dot(VX + i * 15, yAt(1), 2.4, "l-green");
  for (let i = -3; i <= 3; i++) lights += dot(VX + i * 1.6, yAt(24), 0.7, "l-red");
  const bars = [];
  for (let z = 0.95; z >= 0.6; z -= 0.066) bars.push(z);
  bars.forEach((z, k) => {                    // approach lights; the flashers run towards the runway
    const s = 1 / z;
    for (let j = -2; j <= 2; j++) lights += dot(VX + j * 3.8 * s, yAt(z), 1.5 * Math.sqrt(s), "l-appr");
    flash += dot(VX, yAt(z), 2.8 * Math.sqrt(s), "l-flash", ` style="--i:${bars.length - 1 - k}"`);
  });
  for (let j = -9; j <= 9; j++) if (Math.abs(j) > 2) lights += dot(VX + j * 5.5, yAt(0.818), 1.6, "l-appr");
  let seed = 11;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 70; i++) {
    const x = rnd() * W, y = HZ - 0.6 - rnd() * 2.6, r = 0.45 + rnd() * 0.75, o = 0.3 + rnd() * 0.55;
    if (Math.abs(x - VX) > 26) city += dot(x, y, r, "l-city", ` opacity="${o.toFixed(2)}"`);
  }
  const runway = [[VX - half(1), yAt(1) + 3], [VX + half(1), yAt(1) + 3], [VX + half(24), yAt(24)], [VX - half(24), yAt(24)]]
    .map((p) => p.map(f1).join(",")).join(" ");
  $("scene").innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMax slice" role="img">
<defs>
<linearGradient id="sc-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c1829"/><stop offset=".7" stop-color="#20365a"/><stop offset="1" stop-color="#3d5677"/></linearGradient>
<linearGradient id="sc-earth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#14223a"/><stop offset="1" stop-color="#08111d"/></linearGradient>
<linearGradient id="sc-fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dfe6eb" stop-opacity=".82"/><stop offset=".42" stop-color="#e8edf1" stop-opacity=".97"/><stop offset="1" stop-color="#d3dbe2" stop-opacity=".55"/></linearGradient>
<filter id="sc-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur id="sc-blur" stdDeviation="1.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect width="${W}" height="${HZ}" fill="url(#sc-sky)"/>
<rect y="${HZ}" width="${W}" height="${H - HZ}" fill="url(#sc-earth)"/>
<polygon class="runway" points="${runway}"/>
<g filter="url(#sc-glow)">${city}${lights}</g>
<g filter="url(#sc-glow)">${flash}</g>
<rect id="fog-layer" width="${W}" height="${H}" fill="url(#sc-fog)" style="opacity:0"/>
</svg>`;
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) $("scene").classList.add("intro");
}

function setFog(vis) {
  // 10 km -> clear, 1 km -> half, <= 150 m -> dense
  const d = isNum(vis) ? Math.max(0, Math.min(1, (4 - Math.log10(Math.max(vis, 50))) / (4 - Math.log10(150)))) : 0;
  $("fog-layer").style.opacity = d.toFixed(3);
  $("sc-blur").setAttribute("stdDeviation", (1.5 + 3 * d).toFixed(2));
}

// ------------------------------------------------------------------ sections
function applyStatic() {
  const L = T();
  document.documentElement.lang = LANG;
  document.title = L.docTitle;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const v = L[el.dataset.i18n];
    if (typeof v === "string") el.textContent = v;
  });
  document.querySelectorAll(".lang button").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.lang === LANG)));
  $("scene").querySelector("svg")?.setAttribute("aria-label", L.sceneAria);
  $("cats").innerHTML = L.cats.map(([k, v], i) =>
    `<li><span class="key c${i + 1}" aria-hidden="true"></span><span><b>${esc(k)}.</b> ${esc(v)}</span></li>`).join("");
  $("terms").innerHTML = L.terms.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
}

function renderHero() {
  const L = T();
  if (!DATA) {
    $("hero").dataset.level = FAILED ? "error" : "loading";
    $("level-word").textContent = "";
    $("headline").textContent = FAILED ? L.errTitle : L.loading;
    $("summary").textContent = FAILED ? L.errText : "";
    $("stamp").textContent = "";
    $("scene-cap").textContent = "";
    return;
  }
  const c = DATA.conditions, list = hours();
  const key = DATA.alert === "red" && c.fog_now ? "redNow" : DATA.alert;
  $("hero").dataset.level = DATA.alert;
  $("level-word").textContent = L.levels[key];
  $("headline").textContent = L.headline[key];
  if (key === "redNow") {
    $("summary").textContent = L.sumNow(visText(c.vis_m));
  } else {
    const warned = list.find((d) => d.warn && (key === "red" ? d.h <= 2 : d.h >= 3));
    const d = (key === "red" || key === "orange") && warned ? warned : riskiest(list);
    const say = key === "green" ? L.sumGreen : key === "yellow" ? L.sumYellow : L.sumWarn;
    $("summary").textContent = say(timeOf(d.t), pct(d.p), pct(d.thr));
  }
  const age = (Date.now() - issueMs()) / HOUR;
  $("stamp").innerHTML = esc(L.stamp(dateOf(issueMs()), timeOf(issueMs()))) +
    (age >= 2 ? `<span class="stale">${esc(L.stale(num(Math.floor(age))))}</span>` : "");
  $("scene-cap").textContent = L.sceneCap(visText(c.vis_m));
  setFog(c.vis_m);
}

function renderHours() {
  const L = T(), sel = selectedHour().h;
  $("hours").innerHTML = hours().map((d) => {
    const r = riskOf(d.ratio);
    return `<li><button type="button" class="hour" data-h="${d.h}" aria-pressed="${d.h === sel}" ` +
      `aria-label="${esc(L.rowAria(timeOf(d.t), d.h, pct(d.p), L.risk[r]))}">` +
      `<span class="when"><b>${esc(timeOf(d.t))}</b><small>${esc(L.after(d.h))}</small></span>` +
      `<span class="meter" aria-hidden="true"><span class="fill ${r}" style="width:${f1(Math.min(1, d.p) * 100)}%"></span>` +
      `<span class="limit" style="left:${f1(d.thr * 100)}%"></span></span>` +
      `<span class="pct">${esc(pct(d.p))}</span><span class="risk ${r}">${esc(L.risk[r])}</span></button></li>`;
  }).join("");
}

function evidence(group, d, c) {
  const E = T().ev;
  switch (group) {
    case "humidity":
      return isNum(c.dpd_c) && Math.round(c.dpd_c) <= 0 ? E.humiditySat(pctInt(c.rh_pct))
        : E.humidity(pctInt(c.rh_pct), isNum(c.dpd_c) ? num(Math.round(c.dpd_c)) : "–");
    case "visibility": return (c.fog_now ? E.visibilityFog : E.visibility)(visText(c.vis_m));
    case "temperature": return E.temperature(degC(c.temp_c));
    case "wind": return E.wind(windText(c));
    case "clouds": { const m = ceilText(c); return m ? E.clouds(m) : E.noClouds; }
    case "precipitation": { const w = wxText(precipTokens(c.wx)); return w ? E.precip(w) : E.noPrecip; }
    case "recent_fog":
      return (DATA.history || []).some((x) => isNum(x.vis_m) && x.vis_m < 1000) ? E.recentFog : E.noRecentFog;
    case "time_of_day": {
      const e = sunElevation(d.t), rising = sunElevation(d.t + 30 * 60e3) > e;
      if (e > 12) return E.day;
      if (e > 0) return rising ? E.morning : E.evening;
      return rising && e > -15 ? E.dawn : E.night;
    }
    case "season": {
      const m = localPart(d.t, "month"), name = cap(zoned(d.t, { month: "long" }));
      return ([10, 11, 12, 1, 2].includes(m) ? E.season : E.offSeason)(name);
    }
    case "pressure": return E.pressure(hPa(c.qnh_hpa));
    default: return "";
  }
}

function featureValue(name, x) {
  if (!isNum(x)) return "–";
  if (name.startsWith("wx_") || ["fog_now", "calm", "cavok", "low_cloud", "is_night", "vt_is_night",
    "vv_reported", "recent_precip"].includes(name)) return x >= 0.5 ? (LANG === "tr" ? "evet" : "yes") : (LANG === "tr" ? "hayır" : "no");
  if (name === "rvr_eff_m") return x >= 2000 ? "≥2000 m" : `${num(Math.round(x))} m`;
  if (name === "log_vis") return visText(10 ** x);
  if (name.includes("vis") && !name.startsWith("dlog")) return visText(x);
  if (name.startsWith("log_") && name.endsWith("_ft")) return `${num(Math.round((10 ** x) * 0.3048))} m`;
  if (name.includes("frac")) return pctInt(x * 100);
  if (name.startsWith("drh")) return `${x > 0 ? "+" : ""}${num(x)} ${LANG === "tr" ? "puan" : "pts"}`;
  if (name.includes("rh")) return pctInt(x);
  if (name.endsWith("_c") || name.startsWith("dT") || name.startsWith("ddpd") || ["T_minus_max12h", "dpd_min_6h"].includes(name))
    return `${num(x, 1)} °C`;
  if (name.endsWith("_kt") || (name.includes("wind") && !/_[uv]$/.test(name))) return `${num(x)} kt`;
  if (name.includes("solar_elev")) return `${num(x)}°`;
  if (name.startsWith("h_") || name.startsWith("vt_h_") || name === "night_len_h") return `${num(x, 1)} ${LANG === "tr" ? "sa" : "h"}`;
  if (name === "obs_age_min") return `${num(x)} ${LANG === "tr" ? "dk" : "min"}`;
  if (name.includes("qnh")) return `${num(x, 1)} hPa`;
  return num(x, 2);
}

function renderWhy() {
  const L = T(), d = selectedHour(), c = DATA.conditions;
  $("why-h").textContent = L.whyTitle(timeOf(d.t));
  const list = ((DATA.factors || {})[d.h] || []).filter((f) => L.factors[f.group]);
  const max = Math.max(1e-9, ...list.map((f) => Math.abs(f.value)));
  const item = (f) => {
    const s = Math.abs(f.value) / max;
    return `<li><div class="f-head"><b>${esc(L.factors[f.group][0])}</b>` +
      `<span class="f-bar" role="img" aria-label="${esc(L.strength[s >= 0.66 ? 2 : s >= 0.33 ? 1 : 0])}"><i style="width:${Math.max(6, s * 100).toFixed(0)}%"></i></span></div>` +
      `<p class="f-val">${esc(evidence(f.group, d, c))}</p><p class="f-hint">${esc(L.factors[f.group][1])}</p></li>`;
  };
  const pick = (sign) => list.filter((f) => sign * f.value > 0.05 * max).slice(0, 3);
  const none = `<li class="none">${esc(L.whyNone)}</li>`;
  const up = pick(1), down = pick(-1);
  $("why-up").innerHTML = up.length ? up.map(item).join("") : none;
  $("why-down").innerHTML = down.length ? down.map(item).join("") : none;

  const shap = (DATA.shap || {})[d.h] || [];
  const label = (k) => ((DATA.labels || {})[k] || {})[LANG] || k;
  $("shap-table").innerHTML = `<thead><tr>${L.shapCols.map((x) => `<th scope="col">${esc(x)}</th>`).join("")}</tr></thead><tbody>` +
    shap.map((s) => `<tr><td>${esc(label(s.feature))}</td><td>${esc(featureValue(s.feature, s.x))}</td>` +
      `<td class="${s.value > 0 ? "up" : "down"}">${s.value > 0 ? "+" : "−"}${num(Math.abs(s.value), 2)}</td></tr>`).join("") + "</tbody>";
}

function renderLand() {
  const L = T(), r = DATA.rvr || {};
  const hs = Object.keys(r).map(Number).sort((a, b) => a - b);
  if (!hs.length) { $("land").innerHTML = ""; $("land-summary").textContent = ""; return; }
  const below550 = Math.max(...hs.map((h) => 1 - r[h].p_cat1));
  const below350 = Math.max(...hs.map((h) => r[h].p_cat3));
  $("land-summary").textContent = below350 >= 0.5 ? L.landSevere : below550 >= 0.25 ? L.landSome : L.landOk;
  const seg = (cls, p) => `<i class="${cls}" style="width:${f1(Math.max(0, p) * 100)}%"></i>`;
  $("land").innerHTML = hs.map((h) => {
    const v = r[h], t = issueMs() + h * HOUR;
    return `<div class="land-row"><span class="when"><b>${esc(timeOf(t))}</b><small>${esc(L.after(h))}</small></span>` +
      `<span class="stack" role="img" aria-label="${esc(L.landAria(pct(v.p_cat1), pct(v.p_cat2), pct(v.p_cat3)))}">` +
      `${seg("c1", v.p_cat1)}${seg("c2", v.p_cat2)}${seg("c3", v.p_cat3)}</span>` +
      `<span class="land-p">${esc(L.landNormal(pct(v.p_cat1)))}</span></div>`;
  }).join("");
}

function renderNow() {
  const L = T(), c = DATA.conditions, F = L.facts;
  $("now-lead").textContent = L.nowLead(timeOf(Date.parse(c.obs_time)));
  const wx = wxText(wxTokens(c.wx));
  const items = [
    [F.vis, visText(c.vis_m)],
    isNum(c.rvr_min_m) ? [F.rvr, `${num(Math.round(c.rvr_min_m))} m`] : null,
    wx ? [F.wx, wx] : null,
    [F.temp, degC(c.temp_c)],
    [F.dew, degC(c.dewpt_c)],
    [F.rh, pctInt(c.rh_pct)],
    [F.wind, cap(windText(c))],
    [F.ceil, ceilText(c) || L.noCeil],
    [F.qnh, hPa(c.qnh_hpa)],
  ].filter(Boolean);
  $("facts").innerHTML = items.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
  $("spread-note").textContent = isNum(c.dpd_c) ? L.spread(num(Math.round(c.dpd_c))) : "";
  $("raw").textContent = c.raw || "";
}

function renderChart() {
  const L = T(), box = $("chart");
  const hist = (DATA.history || []).filter((d) => isNum(d.vis_m));
  if (!hist.length) { box.innerHTML = ""; $("legend").innerHTML = ""; return; }
  const W = Math.max(280, Math.round(box.clientWidth || 700)), narrow = W < 520;
  const pl = narrow ? 46 : 54, pr = 8, top = 24, hA = narrow ? 150 : 180, gap = 26, hB = 54, bottom = 28;
  const H = top + hA + gap + hB + bottom;
  const now = issueMs(), t0 = now - 48 * HOUR, t1 = now + 3 * HOUR;
  const x = (ms) => pl + ((ms - t0) / (t1 - t0)) * (W - pl - pr);
  const lo = Math.log10(50);
  const yA = (v) => top + (1 - (Math.log10(Math.min(10000, Math.max(50, v))) - lo) / (4 - lo)) * hA;
  const yB = (p) => top + hA + gap + (1 - p) * hB;
  const hline = (cls, y) => `<line class="${cls}" x1="${pl}" x2="${W - pr}" y1="${f1(y)}" y2="${f1(y)}"/>`;
  const ylabel = (y, text) => `<text x="${pl - 8}" y="${f1(y + 4)}" text-anchor="end">${esc(text)}</text>`;

  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(L.chartAria)}">`;
  s += `<rect class="fogzone" x="${pl}" y="${f1(yA(1000))}" width="${W - pl - pr}" height="${f1(top + hA - yA(1000))}"/>`;
  for (const v of [10000, 3000, 1000, 300, 100]) s += hline("grid", yA(v)) + ylabel(yA(v), v >= 1000 ? `${num(v / 1000)} km` : `${v} m`);
  s += hline("fogline", yA(1000));
  s += `<text class="zone" x="${pl + 6}" y="${f1(top + hA - 8)}">${esc(L.fogZone)}</text>`;
  let path = "", prev = null;
  for (const d of hist) {   // break the line across reporting gaps longer than 2 h
    const ms = Date.parse(d.t);
    path += `${prev !== null && ms - prev <= 2 * HOUR ? "L" : "M"}${f1(x(ms))} ${f1(yA(d.vis_m))} `;
    prev = ms;
  }
  s += `<path class="visline" d="${path}"/>`;
  const rvr = hist.filter((d) => isNum(d.rvr_m));
  for (const d of rvr) s += `<circle class="rvr" cx="${f1(x(Date.parse(d.t)))}" cy="${f1(yA(d.rvr_m))}" r="3"/>`;

  s += hline("grid", yB(0)) + hline("grid", yB(1)) + ylabel(yB(1), pctLabel(100)) + ylabel(yB(0), pctLabel(0));
  const byTime = new Map();   // live records win over replayed ones for the same valid time
  for (const d of LOG) {
    const ms = Date.parse(d.valid_time);
    if (ms >= t0 && ms <= t1 && (!byTime.has(ms) || d.mode === "live")) byTime.set(ms, d);
  }
  const probs = [...byTime.entries()].sort((a, b) => a[0] - b[0]);
  if (probs.length) {
    let a = `M${f1(x(probs[0][0]))} ${f1(yB(0))}`;
    for (const [ms, d] of probs) a += ` L${f1(x(ms))} ${f1(yB(Math.min(1, d.p)))}`;
    a += ` L${f1(x(probs[probs.length - 1][0]))} ${f1(yB(0))} Z`;
    s += `<path class="probarea" d="${a}"/>`;
    const thr = probs[probs.length - 1][1].thr;
    if (isNum(thr)) s += hline("limit", yB(thr)) + `<text x="${W - pr - 4}" y="${f1(yB(thr) - 4)}" text-anchor="end">${esc(L.limit)}</text>`;
  }
  const step = (narrow ? 12 : 6) * HOUR, off = 3 * HOUR;   // Turkey keeps UTC+3 all year
  for (let ms = Math.ceil((t0 + off) / step) * step - off; ms <= t1; ms += step) {
    const lbl = localPart(ms, "hour") === 0 ? zoned(ms, { weekday: "short" }) : timeOf(ms);
    s += `<line class="grid" x1="${f1(x(ms))}" x2="${f1(x(ms))}" y1="${f1(yB(0))}" y2="${f1(yB(0) + 5)}"/>` +
      `<text x="${f1(x(ms))}" y="${H - 6}" text-anchor="middle">${esc(lbl)}</text>`;
  }
  s += `<line class="nowline" x1="${f1(x(now))}" x2="${f1(x(now))}" y1="${top - 4}" y2="${f1(yB(0))}"/>` +
    `<text class="nowlabel" x="${f1(x(now))}" y="${top - 8}" text-anchor="middle">${esc(L.nowMark)}</text>`;
  box.innerHTML = s + "</svg>";
  $("legend").innerHTML = [["sw-vis", L.lgVis], ["sw-fog", L.lgFog], ["sw-prob", L.lgProb], ...(rvr.length ? [["sw-rvr", L.lgRvr]] : [])]
    .map(([k, v]) => `<span><i class="${k}" aria-hidden="true"></i>${esc(v)}</span>`).join("");
}

function renderVer() {
  const L = T(), live = VER.filter((r) => r.mode === "live");
  const sum = (k) => live.reduce((a, r) => a + (r[k] || 0), 0);
  const n = sum("n"), e = sum("events"), h = sum("hits"), m = sum("misses"), f = sum("false_alarms");
  if (!n) {
    $("ver-live").textContent = L.verNone;
  } else {
    const first = Math.min(...live.map((r) => Date.parse(r.first)));
    const tail = e ? L.verEvents(num(e), num(h), num(m), num(f)) : f ? L.verQuietFA(num(f)) : L.verQuiet;
    $("ver-live").textContent = `${L.verSince(dateOf(first, false), num(n))} ${tail}`;
  }
  const rows = VER.slice().sort((a, b) => (a.mode === b.mode ? a.horizon - b.horizon : a.mode === "live" ? -1 : 1));
  const opt = (v, digits) => (isNum(v) ? num(v, digits) : "–");
  $("ver").innerHTML = !rows.length ? "" :
    `<thead><tr>${L.verCols.map((x) => `<th scope="col">${esc(x)}</th>`).join("")}</tr></thead><tbody>` +
    rows.map((r) => `<tr><td>${esc(r.mode === "live" ? L.live : L.replay)}</td><td>${esc(L.lead(r.horizon))}</td>` +
      `<td>${num(r.n)}</td><td>${num(r.events)}</td><td>${num(r.hits)}</td><td>${num(r.false_alarms)}</td><td>${num(r.misses)}</td>` +
      `<td>${opt(r.POD, 2)}</td><td>${opt(r.FAR, 2)}</td><td>${opt(r.CSI, 2)}</td><td>${opt(r.Brier, 4)}</td></tr>`).join("") + "</tbody>";
}

function renderAll() {
  applyStatic();
  renderHero();
  if (!DATA) return;
  renderHours(); renderWhy(); renderLand(); renderNow(); renderChart(); renderVer();
}

// ------------------------------------------------------------------ data
async function getJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}

async function load() {
  const [n, l, v] = await Promise.allSettled([
    getJSON("api/nowcast"), getJSON("api/log?hours=72&horizon=3"), getJSON("api/verification"),
  ]);
  if (n.status === "fulfilled" && n.value && n.value.fog && Object.keys(n.value.fog).length) {
    DATA = n.value;
    FAILED = false;
  }
  else if (!DATA) FAILED = true;
  if (l.status === "fulfilled" && Array.isArray(l.value)) LOG = l.value;
  if (v.status === "fulfilled" && Array.isArray(v.value)) VER = v.value;
  renderAll();
}

$("hours").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-h]");
  if (!b || !DATA) return;
  PICKED = Number(b.dataset.h);
  $("hours").querySelectorAll("button[data-h]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  renderWhy();
});
document.querySelectorAll(".lang button").forEach((b) => b.addEventListener("click", () => {
  LANG = b.dataset.lang;
  storeSet("ltac-lang", LANG);
  renderAll();
}));
let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (DATA) renderChart(); }, 150);
});

buildScene();
renderAll();
load();
setInterval(load, 5 * 60 * 1000);
