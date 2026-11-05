---
title: Ankara Esenboğa Havalimanı'nda Sis ve Düşük Görüşün Makine Öğrenmesiyle Kısa Vadeli Tahmini: Yöntemlerin Karşılaştırılması, Açıklanabilirlik ve Gerçek Zamanlı Erken Uyarı
subtitle: TÜBİTAK 2209-A Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı – Araştırma Önerisi Taslağı (2026 Çağrısı)
lines: **Proje yürütücüsü:** Ata Sakik (Yazılım Mühendisliği, 4. sınıf) | **Akademik danışman:** [unvanı, adı ve soyadı – başvurudan önce eklenecek] | **Önerilen süre:** 12 ay | **Talep edilen bütçe:** 12 000 TL
header: TÜBİTAK 2209-A araştırma önerisi taslağı
author: Ata Sakik
lang: tr
---

> **Bu taslak nasıl kullanılır?** Başvuru, TÜBİTAK Yönetim Bilgi Sistemi'nde (TYBS) çevrim içi yapılır; araştırma önerisi, sisteme girilen metinlerden otomatik oluşturulur. Aşağıdaki her başlığın altındaki metni TYBS'deki aynı adlı adıma yapıştırın; tabloları sistemin "Tablo" aracıyla, şekilleri "Resim Yükle" düğmesiyle (.png) ekleyin ve "Proje Önerisini Önizle" ile kontrol edin.
>
> **Süre:** 2026 çağrısında son başvuru ve danışman onayı **11 Kasım 2026, saat 17.30**; kurum yetkilisi e-imzası 16–23 Kasım 2026. Bütçe en fazla 12 000 TL'dir; konferans, yayın ve patent giderleri bütçeye yazılamaz. Çağrının 4.1.8 maddesi gereği metinde hiçbir kurum, firma, ürün veya marka öne çıkarılmamıştır; kaynak ve veri sağlayıcılar yalnızca kaynakçada anılmıştır.

# ÖZET

Sis, havalimanlarında görüşü düşürerek gecikme, yön değiştirme ve iptallere yol açan en önemli hava olaylarından biridir. Başkentin ana hava kapısı olan Ankara Esenboğa Havalimanı'nda sislerin büyük bölümü kış aylarında, gün doğumuna yakın saatlerde oluşmakta ve çoğu en ileri iniş kategorisini gerektirmektedir; buna karşın literatürde havalimanı için makine öğrenmesine dayalı bir sis tahmin modeli bulunmamaktadır. Bu proje, Esenboğa'da sis ve düşük görüşü 1–6 saat önceden tahmin eden, farklı makine öğrenmesi yöntem ailelerini aynı koşullarda ve istatistiksel olarak karşılaştıran, tahminlerini kalibre edilmiş olasılıklar ve anlaşılır gerekçelerle sunan, gerçek zamanlı çalışan açık kaynaklı bir erken uyarı sistemi geliştirmeyi ve bu sistemin başka havalimanlarına genellenebilirliğini sınamayı amaçlamaktadır. Yöntem olarak 2005'ten bu yana yarım saatte bir yayımlanan havalimanı rasatları çözülmekte, kalite kontrolünden geçirilmekte ve 77 öngörücüye dönüştürülmektedir. Lojistik regresyondan analog yönteme, ağaç tabanlı artırma yöntemlerinden açıklanabilir artırma makinesine ve yinelemeli, evrişimli ve dikkat tabanlı sinir ağlarına uzanan on üç teknik ile bunların topluluğu kronolojik olarak eğitilmekte, kalibre edilmekte ve bağımsız kış sezonlarında kalıcılık, tahmincinin pratik kuralı ve resmî kısa vadeli tahminle karşılaştırılmaktadır. Başarı; kritik başarı indeksi, seyrek olaylara uygun beceri skorları, olasılıksal skorlar ve maliyet–kayıp modeline dayalı ekonomik değerle, gün-blok bootstrap ve Holm düzeltmeli anlamlılık testleriyle ölçülmektedir. Ön çalışmada dört bağımsız test sezonunda topluluk tahmini 1, 3 ve 6 saatte kritik başarı indeksini kalıcılığa göre 0,65'ten 0,73'e, 0,32'den 0,46'ya ve 0,13'ten 0,34'e çıkarmış ve 1 saatte resmî tahmini anlamlı biçimde geçmiştir. Proje 12 ay sürecek beş iş paketinden oluşmaktadır: veri güncelleme ve genişletme, yöntem karşılaştırması, kalibrasyon ve açıklanabilirlik, gerçek zamanlı erken uyarı ve canlı doğrulama ile diğer havalimanlarına genelleme ve sayısal hava tahmini öngörücülerinin eklenmesi. Risklere karşı yedek veri kaynakları, yedek zamanlayıcı ve alternatif veri ürünleri planlanmıştır. Projenin çıktıları hakemli bir dergi makalesi, bir kongre bildirisi, açık veri seti ve kıyaslama ölçütü, açık kaynak kod ve herkese açık bir erken uyarı arayüzüdür. Sonuçların sis kaynaklı gecikme ve yön değiştirmelerin önceden öngörülmesine katkı sağlaması, meteoroloji ve hava trafik birimleri için açıklanabilir bir karar destek prototipi oluşturması ve yolculara sade bir dille bilgi vermesi beklenmektedir.

**Anahtar kelimeler:** sis, düşük görüş, havacılık meteorolojisi, makine öğrenmesi, açıklanabilir yapay zekâ, erken uyarı

# 1. ARAŞTIRMA ÖNERİSİNİN BİLİMSEL NİTELİĞİ

## 1.1. Konunun Önemi ve Araştırma Önerisinin Bilimsel Niteliği

Sis, yere yakın yatay görüşü 1000 m'nin altına indiren ve havacılığı en çok aksatan hava olaylarından biridir [@gultepe2007; @haeffelin2010]. Görüş ya da pist görüş mesafesi (RVR), aletli iniş sisteminin (ILS) kullanılabilen kategorisinin alt sınırlarının altına düştüğünde havalimanı düşük görüş prosedürlerine geçer, iniş kapasitesi azalır ya da trafik durur; bu da gecikme, yön değiştirme ve iptal olarak tüm ağa yayılır [@dalmau2025]. Avrupa'da hava trafiği akış yönetimi kaynaklı gecikmenin ağ ortalaması maliyeti dakikada yaklaşık 100 avro olarak verilmektedir [@eurocontrol2025]; sisli tek bir sabahta onlarca uçuşun gecikmesi ya da başka meydana yönlendirilmesi bu nedenle önemli bir ekonomik kayıp ve yolcu mağduriyeti demektir.

Ankara Esenboğa Havalimanı başkentin ana hava kapısıdır; resmî istatistiklere göre yalnızca Ocak 2026'da 1 244 310 yolcuya hizmet vermiş, yolcu sayısı bir önceki yılın aynı ayına göre %14,7 artmıştır [@dhmi2026]. Havalimanı sise karşı özellikle hassastır: sislerin yaklaşık %89'u Ekim–Şubat arasında görülür, çoğu RVR'yi 350 m'nin altına düşürerek en ileri iniş kategorisini (CAT III) gerektirir ve yaklaşık dörtte üçü radyasyon sisidir [@camalan2010]; 2011–2020 döneminde yaklaşık 800 sisli saat kaydedilmiş, Aralık 2019'daki bir olay neredeyse üç gün sürmüştür [@koyuncu2022]. Ön çalışmamızda 2005–2026 rasatlarında 537 sis olayı bulunmuş; olayların medyan süresi 2 saat olsa da %10'u 9 saati aşmıştır. Operasyonel sorun bu nedenle sisin ne zaman başlayıp ne zaman dağılacağını birkaç saat önceden bilebilmektir.

Esenboğa için yayımlanmış çalışmalar iklimsel ve sinoptik niteliktedir; Çamalan vd. [@camalan2010] açıkça sis tahmin modelleri geliştirilmesini önermiş, ancak bildiğimiz kadarıyla havalimanı için bugüne kadar bir makine öğrenmesi tahmin modeli geliştirilmemiştir. Dünyada ise havalimanı rasatları, sayısal tahmin çıktıları ya da uydu verileriyle çalışan istatistiksel ve makine öğrenmesi modelleri kalıcılık tahminine göre açık bir üstünlük göstermiştir [@kneringer2019; @dietz2019a; @dietz2019b; @castillo2022; @kamangir2021]. Güncel derlemeler, bu alandaki çalışmalarda doğrulama uygulamalarının tutarsız olduğunu, resmî havalimanı tahminleriyle aynı bilgi ufkunda karşılaştırmaların nadir yapıldığını, modellerin ne öğrendiğinin çoğunlukla açıklanmadığını ve modellerin başka havalimanlarına aktarılabilirliğinin sınırlı kaldığını vurgulamaktadır [@alves2025; @salcedo2025; @cerda2025]. Tablo verisinde ağaç tabanlı yöntemlerin derin öğrenmeye göre sık üstün geldiği [@grinsztajn2022], yeni temel modellerin ise küçük veri kümelerinde iddialı sonuçlar verdiği [@hollmann2025] bilinmekle birlikte, bu yöntem ailelerinin seyrek ve operasyonel açıdan kritik bir olay olan sis için aynı koşullarda, istatistiksel anlamlılık testleriyle karşılaştırıldığı çalışma çok azdır.

Bu öneri söz konusu boşlukları Esenboğa özelinde kapatmayı amaçlamaktadır. **Araştırma sorusu:** Yalnızca havalimanının kendi rasatlarıyla eğitilen makine öğrenmesi yöntemleri, Esenboğa'da sisi ve ILS kategorisini 1–6 saat önceden kalıcılık tahmininden ve resmî kısa vadeli tahminden daha iyi tahmin edebilir mi; hangi yöntem ailesi hangi öngörü süresinde en iyidir ve bu tahminler operasyonel kullanım için yeterince güvenilir, açıklanabilir ve genellenebilir midir? **Hipotezler:** (H1) en iyi makine öğrenmesi tahmini 1, 3 ve 6 saatte kalıcılığa, 1 saatte resmî TREND tahminine göre anlamlı biçimde daha başarılıdır; (H2) tek bir yöntem ailesi tüm öngörü sürelerinde üstün değildir; (H3) yöntemleri birleştiren bir topluluk tahmini, tek yöntemlerden daha yüksek olasılıksal başarı ve ekonomik değer sağlar; (H4) yapısı gereği açıklanabilir yöntemler en iyi yöntemin başarısının büyük bölümüne ulaşır; (H5) model, kalibrasyon güncellemesiyle başka havalimanlarına sınırlı başarı kaybıyla aktarılabilir ve sayısal hava tahmini öngörücüleri 6 saatlik başarıyı artırır.

**Ön bulgular.** Yürütücünün dönem projesi kapsamında yaptığı ön çalışmada 2005–2026 dönemine ait 385 018 rasat çözülmüş, kalite kontrolünden geçirilmiş ve on üç teknik aynı protokolle karşılaştırılmıştır (Bölüm 2 ve 6). Dört bağımsız test sezonunda (2022/23–2025/26) yöntemleri birleştiren topluluk tahmini genel sıralamada birinci olmuş; 1 saat önceden sislerin %83'ünü önceden yakalamış ve uyarılarının %86'sı doğru çıkmıştır. Kritik başarı indeksi 1, 3 ve 6 saatte 0,73, 0,46 ve 0,34'e ulaşmış (kalıcılık: 0,65, 0,32 ve 0,13); 1 saatte resmî kısa vadeli tahmine göre fark anlamlıdır (ΔCSI = 0,106; %95 güven aralığı 0,073–0,138). Hiçbir yöntem ailesi tüm öngörü sürelerinde üstün olmamış (H2), topluluk en tutarlı sonucu vermiş (H3) ve yapısı gereği açıklanabilir EBM 1 saatte en iyi yöntemle neredeyse aynı başarıya ulaşmıştır (H4). Bu bulgular H1–H4'ü desteklemektedir; proje, bulguları gerçek zamanlı doğrulama, ek havalimanları ve sayısal tahmin verisiyle sınamayı (H5) hedeflemektedir.

Proje, TÜBİTAK öncelikli alanlar listesinde yer alan "yapay zekâ" ve "modelleme ve simülasyon teknolojileri" alanlarıyla doğrudan ilişkilidir [@tubitak2025]: açıklanabilir yapay zekâ yöntemlerini, ulaştırma güvenliği ve verimliliği için gerçek zamanlı çalışan bir karar destek sistemine dönüştürmektedir. İklim değişikliğiyle sis sıklığının değiştiği bir dönemde verinin sürekli güncellenen modellerle izlenmesi, uyum çalışmalarına da katkı sağlar.

## 1.2. Amaç ve Hedefler

Projenin amacı, Ankara Esenboğa Havalimanı'nda sis ve düşük görüşü 1–6 saat önceden tahmin eden; farklı makine öğrenmesi yöntem ailelerini aynı koşullarda ve istatistiksel olarak karşılaştıran; tahminlerini kalibre edilmiş olasılıklarla ve anlaşılır gerekçelerle sunan; gerçek zamanlı çalışarak kendi başarısını sürekli doğrulayan açık kaynaklı bir erken uyarı sistemi geliştirmek ve bu sistemin başka havalimanlarına genellenebilirliğini sınamaktır. Ölçülebilir hedefler şunlardır:

1. **Veri (İP1):** 2005'ten proje sonuna kadar uzanan, kalite kontrolünden geçmiş ve analiz dilimlerinin en az %99'unda gözlem içeren açık bir Esenboğa veri setinin ve en az iki ek havalimanı için aynı biçimde hazırlanmış veri setlerinin yayımlanması.
2. **Karşılaştırma (İP2):** On üç tekniğin aynı öngörücüler, bölümleme, kalibrasyon ve eşik kuralıyla karşılaştırılması; bağımsız test sezonlarında en iyi tekniğin kritik başarı indeksinin (CSI) 1 saatte en az 0,70, 3 saatte en az 0,45 ve 6 saatte en az 0,33 olması ve 1 saatte resmî TREND tahminini gün-blok bootstrap testiyle anlamlı biçimde (p < 0,05) geçmesi.
3. **Güvenilirlik ve açıklanabilirlik (İP3):** Olasılıkların kalibre edilmesi (1 saatte Brier beceri skoru en az 0,5), her tahmin için öngörücü katkılarının raporlanması ve tahminlerin ekonomik değerinin maliyet–kayıp modeliyle farklı kullanıcı türleri için gösterilmesi.
4. **Gerçek zamanlı doğrulama (İP4):** Erken uyarı sisteminin proje süresince yarım saatlik tahmin dilimlerinin en az %95'inde zamanında tahmin üretmesi ve bir kış sezonu boyunca tüm tahminlerin otomatik olarak doğrulanıp raporlanması.
5. **Genelleme (İP5):** Modellerin en az iki ek havalimanına aktarılması ve başarı kaybının ölçülmesi; açık sayısal hava tahmini ve yeniden analiz verisinden türetilen öngörücülerle 6 saatlik CSI'nın en az 0,03 artırılması.

# 2. YÖNTEM

**Araştırma tasarımı.** Çalışma, geçmiş veriyle yapılan geriye dönük bir karşılaştırma ile gerçek zamanlı, ileriye dönük bir doğrulamayı birleştiren nicel ve deneysel bir tasarıma sahiptir. Veri, aynı sis olayının ardışık yarım saatlerinin eğitim ve test kümelerine dağılarak sızıntı oluşturmasını önlemek için kronolojik ve sezonlara hizalı olarak bölünür [@kaufman2012]: eğitim 2005–2019, doğrulama 2019/20–2021/22, test 2022/23–2025/26 sezonları; proje süresindeki kış sezonu ise gerçek zamanlı değerlendirmeye ayrılır. Bütün ayar, kalibrasyon ve eşik kararları yalnızca doğrulama sezonlarında verilir; test sezonları tek kez değerlendirilir.

**Veri ve ön işleme (İP1).** Havalimanında yarım saatte bir yayımlanan rutin METAR ve ani değişimlerde yayımlanan SPECI raporları açık arşivlerden alınır [@iem; @ogimet; @awc]. Uluslararası rapor biçimine [@wmo306] göre yazılmış bir çözücü görüş, her pistin RVR değeri, hadise, bulut, sıcaklık, çiy noktası, basınç ve resmî kısa vadeli tahmin (TREND) gruplarını çıkarır; kalite kontrolü hatalı ve fiziksel olarak imkânsız değerleri ayıklar. Raporlar düzenli 30 dakikalık bir ızgaraya aktarılır; hiçbir değer enterpole edilmez. Aynı işlem hattı ek havalimanlarına da uygulanır; İP5 için açık erişimli küresel sayısal tahmin ve yeniden analiz verisinden [@hersbach2020] sınır tabakası nemi, rüzgâr ve bulutluluk öngörücüleri türetilir.

**Bağımlı ve bağımsız değişkenler.** Bağımlı değişkenler, $t+h$ anında ($h$ = 1–6 saat) görüşün 1000 m'nin altına inmesi (ikili sis olayı) ve en düşük RVR'ye göre tanımlanan sıralı ILS kategorisidir (CAT I ve üstü, CAT II, CAT III) [@icao_annex3; @icao_doc9365]; kategoriler iki ikili modelin sıralı birleşimiyle tahmin edilir [@frank2001]. Bağımsız değişkenler, yalnızca $t$ anında veya öncesinde yayımlanmış raporlardan hesaplanan 77 öngörücüdür: anlık durum (görüş, RVR, sıcaklık, çiy noktası açığı, bağıl nem, rüzgâr, basınç, bulut), hadise, 1–6 saatlik eğilimler, sınır tabakasının belleği (gece soğuması, son 6–72 saatteki sis, yağış ve kar oranları, son sisten beri geçen süre) ile takvim ve Güneş konumu [@alduchov1996; @spencer1971].

**Karşılaştırılan yöntemler (İP2).** Altı aileden on üç teknik aynı protokolle eğitilir: doğrusal (lojistik regresyon [@cox1958]); analog ("geçmişte bugüne en çok benzeyen durumlarda ne oldu?" sorusunu soran k-en yakın komşu yöntemi [@hansen2007; @delle2013]); ağaç toplulukları (rastgele orman [@breiman2001] ve gradyan artırma: XGBoost [@chen2016], LightGBM [@ke2017], CatBoost [@prokhorenkova2018]); yapısı gereği açıklanabilir artırma makinesi (EBM) [@lou2013; @nori2019]; sinir ağları (çok katmanlı algılayıcı ile son 12 saatin dizisini okuyan GRU [@cho2014], LSTM [@hochreiter1997], zamansal evrişim ağı [@bai2018] ve Transformer [@vaswani2017]); ve topluluk (doğrulama başarısını en çok artıran modellerin olasılıklarını birleştiren açgözlü seçim [@caruana2004]). Hiperparametreler doğrulama sezonlarında, hassasiyet–duyarlılık eğrisi altındaki alanı (PR-AUC) en büyükleyecek biçimde ağaç yapılı Parzen kestiricisiyle [@akiba2019] veya küçük ızgaralarla ayarlanır. Sınıf dengesizliği (sis gözlemlerin yaklaşık %1'i) ağırlıklandırmayla ele alınır [@he2009]; olasılıklar Platt ya da izotonik yöntemle kalibre edilir [@platt1999; @zadrozny2002; @niculescu2005] ve uyarı eşiği doğrulama kümesinde CSI'yı en büyükleyecek biçimde seçilir. Karşılaştırma tahminleri; kalıcılık, klimatoloji, sis için tahmincinin pratik kuralı (çiy noktası açığı ve rüzgâr eşikleri) ve resmî TREND ile TAF tahminleridir [@mahringer2008].

**İstatistiksel yöntemler (İP2–İP3).** Başarı; isabet olasılığı (POD), yanlış alarm oranı (FAR), CSI, Heidke beceri skoru (HSS) [@jolliffe2012; @wilks2019], seyrek olaylar için tasarlanmış SEDI [@ferro2011], PR-AUC [@saito2015], Brier skoru ve beceri skoru [@brier1950; @murphy1973] ve ILS kategorileri için sıralı olasılık skoruyla [@epstein1969] ölçülür. Yarım saatlik örnekler güçlü öz ilişki gösterdiğinden güven aralıkları tüm günleri yeniden örnekleyen blok bootstrap ile [@kunsch1989; @wilks1997] hesaplanır; her teknik en iyi teknikle eşleştirilmiş günlerde karşılaştırılır ve çoklu karşılaştırma Holm yöntemiyle düzeltilir [@holm1979]. Tahminlerin pratik yararı maliyet–kayıp modelindeki göreli ekonomik değerle gösterilir [@richardson2000].

**Açıklanabilirlik (İP3).** Ağaç modelleri SHAP değerleriyle [@lundberg2017; @lundberg2020] açıklanır; her tahmin, öngörücü katkılarının toplamına ayrıştırılır ve katkılar nem, rüzgâr, günün saati gibi on sade etken grubunda özetlenir. EBM'nin şekil fonksiyonları ve analog yöntemin bulduğu benzer geçmiş durumlar bağımsız birer çapraz denetim sağlar [@mcgovern2019].

**Gerçek zamanlı sistem (İP4).** Aynı çözme, ızgaralama ve öznitelik kodu, ücretsiz bulut tabanlı otomasyon hizmetinde yarım saatte bir çalışır: son raporları indirir, tahmin üretir, sonuçları kaydeder ve bir web arayüzünde sade bir dille yayımlar. Her tahmin, geçerlilik zamanı geldiğinde gerçekleşen gözlemle otomatik olarak doğrulanır; çalıştırılamayan saatlerin tahminleri sonradan aynı bilgi ufkuyla hesaplanıp ayrı raporlanır. Böylece çevrim dışı ve çevrim içi tahminlerin aynı olduğu da sınanmış olur.

**Genelleme (İP5).** Esenboğa'da eğitilen modeller en az iki ek havalimanına (ör. sis nedeniyle sık aksama yaşanan büyük bir kıyı havalimanı ile iç bölgedeki yüksek rakımlı bir havalimanı) yeniden eğitilmeden, yalnızca yerel kalibrasyonla ve yerel veriyle yeniden eğitilerek uygulanır; başarı farkları aktarılabilirlik literatürüyle [@cerda2025] karşılaştırılır. Sayısal hava tahmini öngörücülerinin katkısı, aynı modellerin bu öngörücülerle ve onlarsız eğitilmesiyle ölçülür.

**Ön çalışma ve fizibilite.** Projenin fizibilitesi bir dönem projesiyle gösterilmiştir: 2005–2026 dönemi için veri seti hazırlanmış (analiz dilimlerinin %99,7'sinde gözlem), on üç teknik eğitilip doğrulanmış, sonuçlar İngilizce ve Türkçe bir makale taslağına dönüştürülmüş ve yarım saatte bir çalışan, kendi tahminlerini otomatik olarak doğrulayan bir erken uyarı prototipi Ekim 2026'dan beri kesintisiz çalışmaktadır. Ön çalışmanın başlıca sonuçları Bölüm 6'daki tablo ve şekillerde özetlenmiştir. Proje bu altyapıyı genişleterek hipotezleri gerçek zamanlı ve çok havalimanlı koşullarda sınayacaktır.

**Çalışma takvimiyle ilişki.** Veri ve kalite kontrolü İP1'de, yöntem karşılaştırması İP2'de, kalibrasyon, açıklanabilirlik ve ekonomik değer İP3'te, gerçek zamanlı sistem ve canlı doğrulama proje boyunca İP4'te, genelleme ve sayısal tahmin öngörücüleri İP5'te ele alınmaktadır (Şekil 1).

# 3. PROJE YÖNETİMİ

## 3.1. Çalışma Takvimi

Table: Çalışma takvimi (başarıya katkı sütununun toplamı 100'dür)
| İP No | İş paketinin adı ve hedefleri | Kim(ler) tarafından | Zaman aralığı (ay) | Başarı ölçütü ve projenin başarısına katkısı |
|---|---|---|---|---|
| 1 | Veri güncelleme, genişletme ve kalite kontrolü: Esenboğa ve en az iki ek havalimanı için rasat arşivlerinin indirilmesi, çözülmesi, kalite kontrolü ve 30 dakikalık ızgaraya aktarılması | Proje yürütücüsü (danışman denetiminde) | 1–2 | Dilimlerin en az %99'unda gözlem; kalite kontrol raporu; veri setlerinin açık erişimle paylaşılması. **Katkı: %15** |
| 2 | Yöntemlerin karşılaştırılması: on üç tekniğin aynı protokolle eğitilmesi, ayarlanması ve test sezonlarında karşılaştırılması | Proje yürütücüsü | 2–6 | CSI en az 0,70 (1 sa), 0,45 (3 sa), 0,33 (6 sa); en iyi tekniğin 1 saatte TREND'i anlamlı biçimde geçmesi (p < 0,05); Holm düzeltmeli karşılaştırma tablosu. **Katkı: %30** |
| 3 | Kalibrasyon, açıklanabilirlik ve ekonomik değer analizi | Proje yürütücüsü, danışman | 5–8 | 1 saatte Brier beceri skoru en az 0,5; her tahmin için katkı raporu; üç kullanıcı türü için ekonomik değer eğrileri. **Katkı: %20** |
| 4 | Gerçek zamanlı erken uyarı sistemi ve canlı doğrulama | Proje yürütücüsü | 1–12 | Yarım saatlik dilimlerin en az %95'inde zamanında tahmin; bir kış sezonunun tüm tahminlerinin otomatik doğrulanması ve aylık başarı raporu. **Katkı: %20** |
| 5 | Diğer havalimanlarına genelleme ve sayısal hava tahmini öngörücüleri | Proje yürütücüsü, danışman | 7–11 | En az iki havalimanında başarı kaybının ölçülmesi; sayısal tahmin öngörücüleriyle 6 saatlik CSI'da en az 0,03 artış. **Katkı: %15** |

![Çalışma takvimi ve kilometre taşları (M1: veri setleri, M2: karşılaştırma raporu, M3: açıklanabilirlik ve değer raporu, M4: canlı doğrulama raporu).](results/figures/tr/gantt.png){width=6.3}

## 3.2. Risk Yönetimi

Table: Risk yönetimi
| İP No | En önemli riskler | Risk yönetimi (B planı) |
|---|---|---|
| 1 | Açık rasat arşivlerinin geçici olarak erişilemez olması veya bazı dönemlerin eksik olması | Üç bağımsız açık kaynak birbirinin yedeği olarak kullanılır; indirilen veri yerel olarak arşivlenir; eksik dönemler raporlanır ve analizde maskelenir. Yöntemde değişiklik gerekmez. |
| 2 | Çok sayıda modelin eğitiminin hesaplama süresini aşması | Bütçedeki bulut tabanlı grafik işlemci hizmeti kullanılır; hiperparametre aramaları daraltılır, derin ağlarda erken durdurma uygulanır. Hedefler değişmez. |
| 2, 3 | İklimsel eğilim nedeniyle sis sıklığının azalması ve test döneminde dağılımın kayması | Kalibrasyon son sezonlarla güncellenir; modeller kayan zaman penceresiyle yeniden eğitilir ve bu değişiklik ayrıca raporlanır. |
| 4 | Ücretsiz bulut zamanlayıcısının çalıştırmaları geciktirmesi veya atlaması | Dış zamanlayıcı ve yedek zamanlayıcı birlikte kullanılır; atlanan saatlerin tahminleri aynı bilgi ufkuyla sonradan hesaplanıp ayrı raporlanır; gerekirse yerel bir bilgisayarda çalıştırılır. |
| 4 | Projenin kışında az sayıda sis olayı görülmesi | Canlı doğrulama, dört bağımsız test sezonu ve ek havalimanlarının sonuçlarıyla birlikte yorumlanır; olay sayısı güven aralıklarıyla raporlanır. |
| 5 | Sayısal tahmin verisine erişimin veya işlenmesinin beklenenden zor olması | Daha düşük çözünürlüklü açık ürünler veya yeniden analiz verisi kullanılır; olmazsa aktarım çalışması yalnızca rasat tabanlı modellerle tamamlanır. |

## 3.3. Araştırma Olanakları

Table: Araştırma olanakları
| Altyapı / ekipman türü ve modeli | Projede kullanım amacı |
|---|---|
| 8 GB bellekli grafik işlemcili dizüstü bilgisayar (yürütücüye ait) | Modellerin eğitimi, ayarlanması ve değerlendirilmesi |
| Ücretsiz bulut tabanlı otomasyon ve statik web barındırma hizmetleri | Gerçek zamanlı tahmin, kayıt, otomatik doğrulama ve sonuçların yayımlanması |
| Açık erişimli rasat arşivleri ve sayısal tahmin/yeniden analiz verileri | Eğitim, test ve gerçek zamanlı veri |
| Üniversitenin kütüphane ve elektronik veri tabanı abonelikleri | Bilimsel kaynaklara erişim |
| Açık kaynak bilimsel yazılım ekosistemi (Python, makine öğrenmesi ve derin öğrenme kütüphaneleri) | Yazılım geliştirme ve analiz |

# 4. ARAŞTIRMA ÖNERİSİNİN YAYGIN ETKİSİ

Table: Öngörülen çıktılar ve etkiler
| Yaygın etki türü | Öngörülen çıktı, sonuç ve etkiler |
|---|---|
| Bilimsel / akademik | En az bir uluslararası hakemli dergiye makale gönderimi; bir ulusal veya uluslararası kongrede bildiri sunumu; Türkiye havalimanları için açık sis veri seti ve yeniden üretilebilir kıyaslama ölçütü (benchmark); açık kaynak kodlar. |
| Ekonomik / sosyal | Sis kaynaklı gecikme, yön değiştirme ve iptallerin daha önceden öngörülmesine katkı (gecikmenin ağ ortalaması maliyeti dakikada yaklaşık 100 avro [@eurocontrol2025]); meteoroloji ve hava trafik birimleri için açıklanabilir bir karar destek prototipi; yolcular için sade dille bilgi veren herkese açık bir web arayüzü; uygulamalı bir çalıştay veya seminer. |
| Araştırmacı yetiştirilmesi ve yeni projeler | Yürütücünün lisansüstü çalışmaya ve araştırmacı kariyerine hazırlanması; çok havalimanlı ve sayısal tahminle birleşik daha kapsamlı bir ulusal proje önerisinin hazırlanması; sanayiye yönelik bir ürünleştirme çalışmasının temeli. |

Proje ayrıca Birleşmiş Milletler Sürdürülebilir Kalkınma Amaçlarından "sanayi, yenilikçilik ve altyapı" (SKA 9), "sürdürülebilir şehirler ve topluluklar" (SKA 11) ve "iklim eylemi" (SKA 13) ile ilişkilidir.

# 5. BÜTÇE TALEP ÇİZELGESİ

Table: Bütçe talebi (tutarlar başvuru sırasında güncel fiyat teklifleriyle doğrulanmalıdır)
| Bütçe türü | Talep edilen tutar (TL) | Talep gerekçesi |
|---|---|---|
| Makine / teçhizat (demirbaş) | 4 500 | 2 TB harici SSD: çok havalimanlı rasat arşivinin, sayısal tahmin verisinin ve model dosyalarının saklanması ve yedeklenmesi |
| Hizmet alımı | 6 500 | Bulut tabanlı grafik işlemci hesaplama hizmeti (yaklaşık 60 GPU-saat): çok havalimanlı deneyler ve sayısal tahmin öngörücüleriyle yapılacak eğitimler |
| Seyahat | 1 000 | Havalimanı meteoroloji birimiyle sonuçların değerlendirileceği toplantılar için şehir içi ulaşım |
| **Toplam** | **12 000** | Konferans, yayın ve patent giderleri çağrı gereği bütçeye dahil edilmemiştir. |

# 6. BELİRTMEK İSTEDİĞİNİZ DİĞER KONULAR

Ön çalışmanın kodları, veri seti ve gerçek zamanlı prototipi açık erişimli olarak yayımlanmıştır. Aşağıdaki tablo ve şekiller ön çalışmanın test sezonlarındaki sonuçlarını özetlemektedir.

Table: Ön çalışmanın 2022/23–2025/26 test sezonlarındaki sonuçları (sis, görüş < 1000 m)
| Tahmin | CSI 1 sa | CSI 3 sa | CSI 6 sa | PR-AUC 1 sa | PR-AUC 6 sa |
|---|---|---|---|---|---|
| Topluluk (genel sıralamada birinci) | **0,729** | 0,458 | **0,341** | **0,899** | 0,516 |
| LightGBM | **0,729** | 0,467 | 0,297 | 0,891 | 0,457 |
| LSTM | 0,703 | **0,472** | 0,340 | 0,885 | 0,509 |
| EBM (yapısı gereği açıklanabilir) | 0,728 | 0,438 | 0,274 | 0,889 | 0,438 |
| Kalıcılık | 0,652 | 0,321 | 0,129 | – | – |
| Tahmincinin pratik kuralı | 0,379 | 0,274 | 0,145 | – | – |
| Resmî kısa vadeli tahmin (TREND) | 0,623 | – | – | – | – |

![On üç tekniğin ve karşılaştırma tahminlerinin test sezonu skorları (koyu renk daha iyidir; her sütunun en iyisi kalın).](results/figures/tr/benchmark.png){width=6.3}

![Sade özet: 100 sisin kaçı önceden bilindi ve 100 uyarının kaçı doğru çıktı?](results/figures/tr/plain_summary.png){width=6.3}

# KAYNAKLAR

{{references}}
