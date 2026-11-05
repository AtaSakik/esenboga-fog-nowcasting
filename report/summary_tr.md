---
title: Esenboğa'da Sisi Saatler Önceden Görmek
subtitle: Yapay zekâ, sisi en iyi hangi yöntemle tahmin ediyor? – Herkes için özet
lines: Ata Sakik, Ankara Üniversitesi Yazılım Mühendisliği, YMH453 Makine Öğrenmesi dönem projesi | Canlı sistem: https://atasakik.github.io/esenboga-fog-nowcasting/
header: Herkes için özet
lang: tr
---

> **Kısaca**
>
> • Esenboğa'nın 21 yıllık hava raporlarıyla 13 farklı yapay zekâ yöntemini sis tahmininde yarıştırdık.
>
> • En iyisi, yöntemleri birleştiren “topluluk” oldu: 1 saat önceden 100 sisin 83'ünü bildi, 100 uyarısının 86'sı doğru çıktı.
>
> • 6 saat önceden 100 sisin 54'ünü yakaladı; “şimdi ne varsa sonra da o” demek yalnızca 23'ünü yakalayabiliyor.
>
> • Yöntemler sisin fiziğini öğreniyor ve her tahmini gerekçesiyle gösteren canlı bir web sitesinde çalışıyor.

# Sis neden bu kadar önemli?

Sis, aslında yere inmiş bir buluttur: havadaki su buharı yoğunlaşıp küçük damlacıklar oluşturur ve görüş 1 kilometrenin altına düşer. Kara yolunda yavaşlamak yeterlidir; havalimanında ise pilotun pisti görebilmesi gerekir. Görüş belirli sınırların altına indiğinde uçaklar ancak özel donanım ve yetkiyle inebilir, aksi hâlde beklemek, başka bir havalimanına gitmek ya da sefer iptal etmek gerekir.

Ankara Esenboğa Havalimanı bu konuda özellikle hassastır. Ankara'nın yüksek ve soğuk platosunda, uzun ve açık kış gecelerinde yer hızla soğur; sabaha karşı yoğun "radyasyon sisi" oluşur. Esenboğa'daki sislerin büyük çoğunluğu Ekim–Şubat aylarında, özellikle gün doğumu saatlerinde görülür ve çoğu, en ileri iniş sistemini gerektirecek kadar yoğundur. Havalimanı yalnızca Ocak 2026'da 1,2 milyondan fazla yolcuya hizmet verdi; bu yüzden sisin birkaç saat önceden bilinmesi binlerce yolcunun planını doğrudan etkiler.

# Ne yaptık?

Havalimanlarında yarım saatte bir, pilotlar için kısa ve kodlu bir hava raporu yayımlanır (METAR). Bu çalışmada Esenboğa'nın 2005'ten 2026'ya kadar yayımlanmış yaklaşık 385 bin raporunu topladık, hatalı olanları ayıkladık ve her yarım saat için havanın "fotoğrafını" çıkardık. Her fotoğraftan 77 ipucu türettik: o anki görüş, nem, sıcaklık ile çiy noktası arasındaki fark, rüzgâr, bulut, son saatlerde havanın nasıl değiştiği, en son ne zaman sis olduğu ve Güneş'in ne zaman doğacağı gibi.

Sonra bilgisayara şu soruyu sorduk: "Bu ipuçlarına bakarak 1, 3 ve 6 saat sonra sis olur mu?" Bilgisayar 2005–2019 yıllarından öğrendi, 2019–2022 kışlarında ayarlandı ve hiç görmediği 2022–2026 kışlarında sınandı. Böylece sonuçlar "ezber" değil, gerçek bir öngörü başarısını gösteriyor.

# Yarışan 13 yöntem

Aynı ipuçlarını ve aynı kuralları kullanarak 13 farklı makine öğrenmesi yöntemini yarıştırdık. Hepsini, tahmincilerin bugün kullandığı yöntemlerle de karşılaştırdık: "şimdi sis varsa sonra da olacak" demek (kalıcılık), tahmincinin pratik kuralı ve havalimanının resmî kısa vadeli tahmini (TREND).

Table: Yöntemler, tek cümlelik benzetmelerle
| Yöntem | Nasıl çalışır? (benzetme) | Kararını açıklayabilir mi? |
|---|---|---|
| Lojistik regresyon | Her ipucuna bir puan verip toplayan bir puan kartı | Evet, puanlar görünür |
| Analog (k-en yakın komşu) | "Geçmişte bugüne en çok benzeyen durumlarda ne olmuştu?" diye bakan deneyimli bir tahminci | Evet, benzer günleri gösterir |
| Rastgele orman | Yüzlerce "evet/hayır" sorusu soran karar ağacından oluşan bir kurul; çoğunluk ne derse o | Kısmen, sonradan çözümlenir |
| XGBoost, LightGBM, CatBoost | Ağaçları sırayla kuran, her yeni ağacın öncekilerin hatasını düzelttiği "hatalarından öğrenen ekip" | Kısmen, sonradan çözümlenir |
| Açıklanabilir artırma (EBM) | Gücünü korurken her ipucunun etkisini ayrı bir eğriyle gösteren "camdan kutu" | Evet, yapısı gereği |
| Çok katmanlı sinir ağı (MLP) | Beyindeki sinir hücrelerinden esinlenen, katman katman hesap yapan ağ | Zor |
| GRU ve LSTM | Son 12 saatin raporlarını sırayla okuyup "hikâyeyi" hatırlayan hafızalı ağlar | Zor |
| TCN | Son 12 saate farklı genişlikte pencerelerden bakan ağ | Zor |
| Transformer | Sohbet robotlarının temelindeki "dikkat" yöntemiyle 12 saatin hangi anlarının önemli olduğuna kendi karar veren ağ | Zor |
| Topluluk | En iyi yöntemlerin tahminlerini birleştiren "uzmanlar kurulu" | Üyeleri üzerinden |

# Sonuçlar: hangi yöntem kazandı?

![Üç yaklaşımın karşılaştırması: 100 sisin kaçı önceden bilindi ve 100 uyarının kaçı doğru çıktı?](results/figures/tr/plain_summary.png){width=6.3}

Grafik üç yaklaşımı yan yana koyuyor. Bir saat önceden yapay zekâ (topluluk) 100 sisin 83'ünü önceden bildi ve verdiği her 100 uyarının 86'sı doğru çıktı. “Şimdi sis varsa sonra da var” demek 79 sisi bildi ama her 100 uyarıdan 21'i boşa çıktı. Tahmincinin pratik kuralı daha çok sisi yakaladı (85), ancak uyarılarının yarısından fazlası boşa çıktı. Öngörü süresi uzadıkça fark büyüyor: 6 saat önceden yapay zekâ 100 sisin 54'ünü yakalarken “şimdi ne varsa” yaklaşımı yalnızca 23'ünü yakalayabiliyor.

13 yöntemin neredeyse tamamı en basit yaklaşımı her kışta geride bıraktı (tek istisna, bir kışta analog yöntem). En iyi yöntemler arasındaki farklar ise küçük; çoğu istatistiksel olarak “berabere” sayılır. Öne çıkanlar şunlar:

- **Bir saat sonrası için** karar ağacı toplulukları (ör. LightGBM) ve açıklanabilir artırma (EBM) en iyiler arasında. “Camdan kutu” EBM'nin en iyi yöntemle neredeyse aynı başarıyı göstermesi, bu sürede şeffaflığın neredeyse bedava olduğunu gösteriyor.
- **3–6 saat sonrası için** son 12 saati hafızasında tutan ağlar (GRU, LSTM) öne çıkıyor; sisin gece boyunca nasıl “olgunlaştığını” daha iyi okuyorlar.
- **Topluluk** her öngörü süresinde en tutarlı sonucu veriyor, çünkü farklı ailelerden yöntemlerin güçlü yanlarını birleştiriyor.
- **Analog yöntem** anlaşılır olsa da en zayıf kaldı: geçmişte “benzer” görünen geceler her zaman aynı sonu getirmiyor.
- **Hesaplama maliyeti** küçük: en hızlı yöntem birkaç saniyede eğitiliyor, tahmin etmek ise saniyenin çok küçük bir kesrini alıyor.

Bu sonuçlar ne işe yarar? Bir havayolu şirketi için uçağın kalkışını biraz ertelemek, sis yüzünden başka bir şehre inmekten çok daha ucuzdur. Böyle kullanıcılar için yapay zekâ tahmininin “ekonomik değeri”, kusursuz bir tahminin sağlayacağı kazancın 1 saatte yaklaşık %89'una, 6 saatte %70'ine ulaşıyor; “şimdi ne varsa” yaklaşımında bu oran %78'den %19'a düşüyor.

# Yapay zekâ neden "sis olacak" dedi?

Bir tahminin güvenilir olması için yalnızca doğru çıkması yetmez; neden öyle dediğini de görebilmeliyiz. Bu yüzden her tahmini, ipuçlarının katkısına ayırdık (SHAP yöntemi). Sonuç, meteorologların bildikleriyle örtüşüyor: hava neme doymuşa yakınsa (sıcaklık ile çiy noktası arasındaki fark 2 °C'nin altındaysa), rüzgâr sakinse (yaklaşık 3 knotun altında) ve gece uzunsa sis olasılığı artıyor; Güneş doğup yükseldikçe sis dağılıyor. Kısa vadede "şu an ne görüyorum" bilgisi, birkaç saat sonrası için ise gecenin uzunluğu, son saatlerdeki nem birikimi ve gün doğumuna kalan süre öne çıkıyor. Yani yöntemler ezber yapmıyor, sisin fiziğini öğreniyor.

# Canlı sistem

Yöntemleri yalnızca kâğıt üzerinde bırakmadık. Herkesin açabileceği bir web sayfası, yarım saatte bir son raporları indiriyor, önümüzdeki 6 saat için sis olasılığını sade bir dille gösteriyor, tahminin nedenini anlatıyor ve her tahmini, zamanı gelince gerçekleşen havayla karşılaştırarak kendi başarısını sürekli kaydediyor: https://atasakik.github.io/esenboga-fog-nowcasting/

# Sınırlar

- Yalnızca havalimanının kendi raporlarını kullanıyoruz; sisin aniden başladığı anları önceden yakalamak hâlâ en zor kısım. Hava tahmin modellerinin ve uydu görüntülerinin eklenmesi bunu iyileştirebilir.
- Şimdilik tek bir havalimanı inceledik; yöntemin başka havalimanlarında ne kadar işe yarayacağı ayrıca sınanmalı.
- Esenboğa'da sis yıllar içinde azaldı (yılda yaklaşık 130 saatten 50 saate); iklim değiştikçe modellerin düzenli olarak yeniden eğitilmesi gerekir.
- Bu bir araştırma prototipidir; resmî tahminlerin ve uçuş kararlarının yerine geçmez.

# Küçük sözlük

- **METAR:** Havalimanlarında yarım saatte bir yayımlanan kodlu hava raporu.
- **Görüş / RVR:** Yatay görüş mesafesi / pist boyunca görülebilen mesafe.
- **Kalıcılık:** "Şimdi ne varsa birkaç saat sonra da o olur" diyen en basit tahmin.
- **CSI (kritik başarı indeksi):** Sis uyarılarının ve gerçek sislerin ne kadar örtüştüğünü 0 ile 1 arasında ölçer; kaçırılan sisleri de boşa verilen alarmları da cezalandırır.
- **Olasılık kalibrasyonu:** "%30 sis" denen günlerin gerçekten yaklaşık %30'unda sis olması.
- **Makine öğrenmesi:** Bilgisayarın kuralları bizden almak yerine geçmiş örneklerden kendisinin çıkarması.
