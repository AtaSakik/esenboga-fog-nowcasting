---
title: Ankara Esenboğa Havalimanı'nda Sis ve Düşük Görüş Koşullarının Açıklanabilir Makine Öğrenmesiyle Kısa Vadeli Tahmini
authors: Ata Sakik
abstract: Sis, Ankara Esenboğa Uluslararası Havalimanı'nda (LTAC) gecikme, yönlendirme ve iptallerin başlıca meteorolojik nedenidir ve havalimanındaki sis gözlemlerinin yarısından fazlası CAT II/III yaklaşma prosedürleri gerektirmektedir. Bu çalışmada LTAC için ilk makine öğrenmesi tabanlı düşük görüş kısa vadeli tahmin (nowcasting) sistemi sunulmaktadır. Kalite kontrolünden geçirilmiş 21,8 yıllık (2005–2026) METAR/SPECI rasatları kullanılarak sis (hâkim görüş mesafesi 1000 m'nin altında) ve ILS kategorilerine karşılık gelen pist görüş mesafesi (RVR) sınıfları; anlık durumu, eğilimleri, sınır tabaka belleğini ve Güneş döngüsünü tanımlayan 77 öznitelikle 1, 3 ve 6 saat önceden tahmin edilmiştir. Lojistik regresyon, rastgele orman, XGBoost, LightGBM ve çok görevli GRU/LSTM ağları kronolojik olarak eğitilmiş, kalibre edilmiş ve dört bağımsız sis sezonunda (2022–2026) kalıcılık, klimatoloji ve resmî METAR TREND tahminiyle karşılaştırmalı olarak doğrulanmıştır. Tüm modeller her öngörü süresinde kalıcılık tahmininden anlamlı biçimde daha başarılıdır: en iyi kritik başarı indeksi 1, 3 ve 6 saat için sırasıyla 0,73, 0,47 ve 0,34 olup kalıcılıkta bu değerler 0,65, 0,32 ve 0,13'tür; 1 saatte LightGBM, TREND tahminini 0,105 (%95 güven aralığı 0,075–0,140) farkla geçmektedir. Gradyan artırma yöntemleri 1 saatte, yinelemeli ağlar ise 3–6 saatte en yüksek olasılıksal beceriyi sağlamaktadır. SHAP analizi, belirleyici etkenlerin 1 saatte anlık nem ve görüş durumundan 6 saatte sınır tabakanın nem belleğine ve gün doğumuna kalan süreye fiziksel olarak tutarlı biçimde kaydığını göstermektedir. Kalibre edilmiş modeller; kademeli uyarı üreten, her tahmini açıklayan ve kendini gerçek zamanlı doğrulayan açık kaynaklı bir web uygulamasında hizmete sunulmuştur.
keywords: Açıklanabilir yapay zekâ, düşük görüş prosedürleri, gradyan artırma, havacılık meteorolojisi, kısa vadeli tahmin, pist görüş mesafesi, sis, yinelemeli sinir ağları.
footnote: Bu çalışma, Ankara Üniversitesi Yazılım Mühendisliği Bölümü YMH453 Makine Öğrenmesi dersinin 2026–2027 güz dönemi projesi olarak hazırlanmıştır. Veri seti, kaynak kodlar, eğitilmiş modeller ve web uygulaması https://github.com/AtaSakik/esenboga-fog-nowcasting adresinde açık olarak paylaşılmaktadır.
 A. Sakik, Ankara Üniversitesi Yazılım Mühendisliği Bölümü 4. sınıf öğrencisidir, Ankara, Türkiye (öğrenci no. 25290085; e-posta: atasakik0077@hotmail.com).
header: YMH453 MAKİNE ÖĞRENMESİ — DÖNEM PROJESİ, ANKARA ÜNİVERSİTESİ, 2026
bio: Ata Sakik|Ankara Üniversitesi Yazılım Mühendisliği Bölümü'nde 4. sınıf lisans öğrencisidir. Araştırma ilgi alanları makine öğrenmesi, açıklanabilir yapay zekâ ve bunların havacılık meteorolojisi ile operasyonel tahmin sistemlerine uygulanmasıdır.
---
# Giriş

Sis, yer seviyesindeki yatay görüş mesafesini 1000 m'nin altına düşüren ve havacılık için en fazla aksaklığa yol açan meteorolojik olaylardan biridir [@gultepe2007; @haeffelin2010]. Görüş mesafesi veya pist görüş mesafesi (RVR), mevcut aletli iniş sistemi (ILS) kategorisinin minimumlarının altına indiğinde havalimanı düşük görüş prosedürlerini (LVP) uygulamak, geliş kapasitesini düşürmek ya da trafiğe kapanmak zorunda kalır; bu da ağ genelinde gecikme, yönlendirme ve iptallere neden olur [@dalmau2025]. Başkentin ana kapısı olan Ankara Esenboğa Uluslararası Havalimanı (LTAC) bu açıdan özellikle hassastır: sislerin yaklaşık %89'u Ekim–Şubat döneminde görülmekte, büyük bölümü RVR'yi 350 m'nin altına düşürmekte ve yaklaşık dörtte üçü radyasyon sisidir [@camalan2010]; 2011–2020 döneminde yaklaşık 800 saat sis kaydedilmiş, Aralık 2019'daki tek bir olay ise yaklaşık üç gün sürmüştür [@koyuncu2022].

Bu operasyonel önemine karşın Esenboğa üzerine yayımlanmış çalışmalar klimatolojik ve sinoptik niteliktedir. Çamalan vd. [@camalan2010] 2000–2009 gözlemlerini incelemiş ve sis tahmin modellerinin geliştirilmesini açıkça önermiş; Koyuncu vd. [@koyuncu2022] on yıllık bir analizi sinoptik bir olay incelemesiyle birleştirmiştir. Bildiğimiz kadarıyla LTAC için makine öğrenmesi (ML) tabanlı bir sis veya düşük görüş tahmini geliştirilmemiştir. Uluslararası ölçekte istatistiksel ve ML tabanlı sis ve düşük görüş prosedürü tahminleri, Viyana gibi havalimanlarında [@kneringer2019; @dietz2019a; @dietz2019b] ve pek çok başka konumda [@alves2025; @salcedo2025] kalıcılık tahminine göre açık bir üstünlük göstermiştir; ancak veriye dayalı tahminleri resmî meydan tahminleriyle aynı bilgi ufkunda karşılaştıran ve modellerin öğrendiklerini fiziksel olarak açıklayan çalışma sayısı azdır.

Bu çalışma söz konusu boşlukları LTAC için kapatmaktadır. Katkılar şunlardır:

1) Sis istatistikleri havalimanının yayımlanmış klimatolojisini yeniden üreten, 21,8 yıllık (2005–2026) ve kalite kontrolünden geçirilmiş bir METAR/SPECI veri seti; veri seti tüm kaynak kodlarla birlikte açık olarak paylaşılmaktadır.

2) Altı model ailesinin—lojistik regresyon, rastgele orman, XGBoost, LightGBM, GRU ve LSTM—1, 3 ve 6 saatlik sis ve ILS kategorisi tahminleri için olasılık kalibrasyonu, sınıf dengesizliği deneyi ve gün-blok bootstrap anlamlılık testleriyle kalıcılık, klimatoloji ve resmî METAR TREND (operasyonel pencerede ayrıca TAF) tahminlerine karşı karşılaştırılması.

3) RVR/ILS kategorisi tahmininin sıralı (ordinal) bir problem olarak kurgulanması ve operasyonlar için en kritik olaylar olan sis başlangıç ve dağılmalarının ayrıca incelenmesi.

4) Öğrenilen ilişkileri sis fiziğiyle ilişkilendiren ve belirleyici etkenlerin öngörü süresine göre nasıl değiştiğini gösteren SHAP tabanlı bir açıklanabilirlik analizi.

5) Aynı işlem hattını canlı METAR'larla çalıştıran, açıklamalı kademeli uyarılar üreten ve kendi tahminlerini gerçek zamanlı doğrulayan açık kaynaklı web tabanlı bir erken uyarı uygulaması.

Makalenin geri kalanı şöyle düzenlenmiştir: Bölüm II ilgili çalışmaları, Bölüm III havalimanını ve veriyi, Bölüm IV yöntemi, Bölüm V bulguları sunmakta; Bölüm VI sonuçların anlamını ve sınırlılıkları tartışmakta, Bölüm VII ise çalışmayı sonuçlandırmaktadır.

# İlgili Çalışmalar

## Sis Fiziği ve Esenboğa

Sis, yere yakın hava ışınımsal soğuma, nemli hava adveksiyonu ya da buharlaşmayla nemlenme sonucu doygunluğa ulaştığında oluşur; Güneş ısıtması, karışım veya kuruma ile dağılır [@gultepe2007]. ParisFog gibi saha çalışmaları, radyasyon sisinin yaşam döngüsünün ışınımsal soğuma, türbülans, aerosoller ve yüzey nemi arasındaki hassas bir dengeyle denetlendiğini göstermiştir [@haeffelin2010]; sayısal hava tahmin modellerinin sisi tahmin etmekte hâlâ zorlanmasının nedeni de budur [@gultepe2007; @herman2016]. Esenboğa'da Çamalan vd. [@camalan2010], 2000–2009 dönemindeki sisli günlerin %75'inin radyasyon sisi olduğunu ve sis gözlemlerinin çoğunun CAT III aralığına (RVR < 350 m) düştüğünü bulmuş; Koyuncu vd. [@koyuncu2022] ise Aralık 2019'daki uzun süreli bir olayı kalıcı bir antisiklon ve güçlü bir alçak seviye inversiyonuyla ilişkilendirmiştir.

## Havalimanlarında İstatistiksel ve Makine Öğrenmesi Tabanlı Kısa Vadeli Tahmin

İlk veriye dayalı yaklaşımlar Canberra'da sis için [@fabbian2007], ABD havalimanlarında bulut tavanı ve görüş için [@marzban2007] ve olasılıksal görüş tahmini için [@bremnes2007] yapay sinir ağlarını kullanmıştır. Herman ve Schumacher [@herman2016] havacılık için sis ve görüş kılavuzunu iyileştirmek amacıyla yeniden tahminleri (reforecast) son işlemden geçirmiştir. Viyana Uluslararası Havalimanı için Kneringer vd. [@kneringer2019] sıralı düşük görüş prosedürü durumlarını sıralı lojistik regresyonla 2 saate kadar tahmin etmiş; Dietz vd. ağaç tabanlı modellerin [@dietz2019a] ve artırma (boosting) yöntemlerinin [@dietz2019b] farklı planlama ufuklarında bu tahminleri iyileştirdiğini göstermiştir. Guijo-Rubio vd. [@guijo2018] sise bağlı düşük görüşü sıralı bir sınıflandırma problemi olarak ele almış, Castillo-Botón vd. [@castillo2022] ise çok sayıda ML yönteminin regresyon ve sınıflandırma formülasyonlarını karşılaştırmıştır. Derin öğrenme yaklaşımları havalimanı görüşü için derin ağlardan [@zhu2017] ve klimatolojik veriyle görüş tahmininden [@ortega2023] üç boyutlu evrişimli FogNet modeline [@kamangir2021] kadar uzanmaktadır. Güncel derleme çalışmaları [@alves2025; @salcedo2025] bu yöntemlerin potansiyelini doğrulamakla birlikte tutarsız doğrulama uygulamalarına, resmî tahminlerle nadiren yapılan karşılaştırmalara ve modellerin konumlar arasında sınırlı aktarılabilirliğine [@cerda2025] dikkat çekmektedir.

## Açıklanabilir Yapay Zekâ ve Tahmin Doğrulama

Açıklanabilirlik, ML tahminlerinin tahminciler tarafından benimsenmesi için temel bir koşuldur [@mcgovern2019]. SHAP değerleri [@lundberg2017], ağaç topluluklarında tam olarak hesaplanabilen [@lundberg2020], toplamsal ve yerel olarak doğru katkı değerleri sağlar. Meydan tahminleri olasılık tablosundan türetilen kategorik skorlarla doğrulanır [@jolliffe2012; @wilks2019]; TAF ve TREND değişim grupları içerdiğinden en doğru biçimde bir tahmin koşulları aralığı olarak yorumlanır [@mahringer2008]. Bu çalışma; kalibre edilmiş ML'yi, sıralı ILS kategorilerini, resmî tahminlerle doğrudan karşılaştırmayı ve SHAP açıklamalarını, daha önce veriye dayalı bir sis tahmini bulunmayan bir havalimanı için operasyonel olarak çalışan tek bir sistemde birleştirmektedir.

# Çalışma Alanı ve Veri

## Esenboğa Havalimanı ve Sis İklimi

Ankara Esenboğa Uluslararası Havalimanı (40,13° K, 32,99° D), şehir merkezinin yaklaşık 28 km kuzeydoğusunda, 953 m yükseklikte bir plato üzerinde yer almaktadır. Karasal iklimi; uzun kış gecelerini, sık görülen antisiklonik durgunluğu, kar örtüsünü ve cephesel yağışlar sonrasında nemli sınır tabakaları bir araya getirir—bunlar ışınımsal soğumayı ve sisi destekleyen koşullardır [@camalan2010; @koyuncu2022]. Şekil @fig:clim, kullanılan veri setindeki sis iklimini özetlemektedir. Sis neredeyse yalnızca soğuk sezona özgüdür: hâkim görüşün 1000 m'nin altında olduğu yarım saatlik gözlemlerin %94,6'sı Ekim–Şubat aylarındadır; sıklık Aralık'ta %4,3, Ocak'ta %3,7'dir ve Haziran–Eylül döneminde pratikte sis görülmez. Gün içinde sis en sık gün doğumu civarında (yerel saatle 08, %2,8), en seyrek ise 15'te görülmektedir. 2011–2020 için hesapladığımız 819,5 saatlik sis süresi, Koyuncu vd. [@koyuncu2022] tarafından aynı on yıl için bildirilen yaklaşık 800 saatle çok iyi örtüşmektedir; RVR ≤ 350 m olan sis gözlemlerinin payı (%55,5) da Çamalan vd.'nin [@camalan2010] sislerin çoğunun CAT III operasyonu gerektirdiği bulgusunu doğrulamaktadır. 537 sis olayı kısa sürelidir—medyan 2 saat—ancak 90. yüzdelik 9 saate ulaşmakta ve en uzun olay 35,5 saat sürmektedir; dolayısıyla operasyonel sorun büyük ölçüde sisin başlangıç ve dağılma zamanlamasıdır. Yıllık sisli saat sayısı belirgin biçimde azalmıştır: 2005–2012'de yılda yaklaşık 130 saatten 2020–2025'te yılda yaklaşık 50 saate.

![page](climatology.png){#fig:clim} LTAC'nin sis iklimi, 2005–2026 (hâkim görüş < 1000 m). (a) Yıllık sisli saat sayısı; gölgeli 2011–2020 dönemi Koyuncu vd. tarafından incelenen dönemdir. (b) Yarım saatlik gözlemlerde sisin aylık sıklığı. (c) Ay ve yerel saate (UTC+3) göre sıklık.

## Gözlemler ve Resmî Tahminler

Çalışmada Ocak 2005–Ekim 2026 dönemine ait yarım saatlik rutin METAR'lar (HH:20 ve HH:50 UTC) ve özel SPECI rasatları kullanılmıştır. Orijinal rasat metinleri Iowa Environmental Mesonet (IEM) arşivinden alınmıştır [@iem]. Eski IEM kayıtları, NCEI Integrated Surface Database'den yeniden oluşturulmuş rasatlar da içermektedir; bunlar RVR ve TREND gruplarından yoksun olduğu ve görüşü statü mil adımlarıyla verdiği için çıkarılmış, oluşan boşluklar Ogimet arşivinden alınan orijinal metinlerle doldurulmuştur [@ogimet]. Her METAR, tahmincinin resmî çok kısa vadeli tahmini olan 2 saatlik TREND tahminini (NOSIG, BECMG veya TEMPO grupları) içermektedir. Meydan tahminleri (TAF; 24 saat geçerli, günde dört kez yayımlanan) yalnızca son 30 gün için NOAA Aviation Weather Center veri servisinden [@awc] elde edilebilmiştir; tarihsel TAF arşivine güvenilir biçimde erişilemediğinden TAF karşılaştırması operasyonel dönemde yapılmıştır.

Tüm rasatlar, hâkim ve minimum görüşü, her pistin RVR değerini, mevcut ve yakın geçmiş hadiseleri, bulut katmanlarını ve dikey görüşü, sıcaklığı, çiy noktasını, QNH'yi ve TREND/TAF değişim gruplarını çözümleyen, bu çalışma için geliştirilmiş bir WMO FM 15/FM 51 çözücüsüyle [@wmo306] işlenmiştir; çözücü sık görülen yazım hatalarını da (ör. "NO SIG", "Q1 015") düzeltmektedir. Kalite kontrolü kapsamında NIL ve bozuk rasatlar çıkarılmış, fiziksel aralık denetimleri ve çiy noktası tutarlılık denetimi uygulanmış, sıcaklık, çiy noktası ve basınçtaki tekil sıçramalar giderilmiştir. Elde edilen veri seti Tablo @tab:data'de özetlenmiştir.

{{table:data_summary|col}}{#tab:data}

## Analiz Izgarası ve Tahmin Edilen Değişkenler

Rasatlar, rutin gözlem saatleriyle hizalı düzenli 30 dakikalık bir ızgaraya aktarılmıştır. Izgara zamanı $t$'deki durum, $(t-29\,\mathrm{dk},\,t]$ aralığında yayımlanan son rasattır; böylece rutin saatler arasındaki SPECI'ler hesaba katılır, ancak hiçbir değer enterpole edilmez veya ileri taşınmaz. 382 607 ızgara diliminin %99,7'sinde gözlem bulunmaktadır.

Öngörü süreleri $h \in \{1, 3, 6\}$ saat için geçerlilik zamanı $t+h$'de iki hedef değişken tanımlanmıştır. İkili sis olayı, ICAO/WMO sis eşiği olan 1000 m'nin altındaki hâkim görüştür [@icao_annex3]. ILS kategorisi, tüm pistlerde raporlanan en düşük RVR'ye dayanan sıralı bir değişkendir: RVR ≥ 550 m için sınıf 0 (CAT I veya daha iyi), 350 ≤ RVR < 550 m için sınıf 1 (CAT II) ve RVR < 350 m için sınıf 2 (CAT III). Bu sınırlar Çamalan vd.'nin [@camalan2010] LTAC için kullandığı kategorileri ve ICAO'nun her hava koşulunda operasyon ile RVR raporlamasına ilişkin kılavuzlarını [@icao_doc9365; @icao_doc9328] izlemektedir; güncel CAT II minimumları 300 m'ye kadar RVR'ye izin verdiğinden 350 m sınırı bir miktar ihtiyatlıdır. RVR yalnızca görüş veya RVR 1500 m'nin altındayken raporlandığından, RVR grubu bulunmayan ve görüşü ≥ 1500 m olan dilimler sınıf 0 kabul edilmiş; RVR'nin eksik olduğu düşük görüşlü dilimlerin %0,06'sında ise ihtiyatlı bir yaklaşık değer olarak hâkim görüş kullanılmıştır.

# Yöntem

Şekil @fig:arch, arşivlerden doğrulanmış tahminlere ve operasyonel uygulamaya uzanan veri akışını göstermektedir.

![page](architecture.png){#fig:arch} Çalışmanın ve operasyonel erken uyarı uygulamasının veri akışı. Web uygulaması, çevrimdışı çalışmanın çözücüsünü, kalite kontrolünü, öznitelik işlem hattını ve kalibre edilmiş modellerini yeniden kullandığından çevrimdışı ve çevrimiçi tahminler birebir aynıdır.

## Problem Tanımı

Gözlem bulunan her ızgara zamanı $t$ için bir $f_h$ modeli

$$ p_{h}(t)=P\left(y(t+h)=1\mid \mathbf{x}(t)\right) $$ {#eq:prob}

olasılığını tahmin eder; burada $\mathbf{x}(t)$ yalnızca $t$ anında veya öncesinde yayımlanan rasatlardan hesaplanan öznitelik vektörüdür. $p_{h}(t)$ bir $\tau_{h}$ eşiğini aştığında uyarı verilir. ILS kategorisi Frank ve Hall'un [@frank2001] sıralı ayrıştırmasıyla tahmin edilmektedir: iki ikili model $P_{550}=P(\mathrm{RVR}<550\,\mathrm{m})$ ve $P_{350}=P(\mathrm{RVR}<350\,\mathrm{m})$ olasılıklarını kestirir; sınıf olasılıkları $1-P_{550}$, $P_{550}-P_{350}$ ve $P_{350}$ olarak elde edilir ve $P_{350}\le P_{550}$ koşulu zorunlu kılınır.

## Öznitelik Mühendisliği

77 öznitelik gruplar hâlinde Tablo @tab:feat'de özetlenmiştir. Öznitelikler şunları tanımlar: (i) anlık durum—görüş, RVR, sıcaklık $T$, çiy noktası $T_{d}$, çiy noktası farkı $T-T_{d}$, Magnus formülüyle hesaplanan bağıl nem [@alduchov1996], rüzgâr bileşenleri, sakin rüzgâr göstergesi, QNH, bulut tavanı, bulut tabanı ve kapalılığı; (ii) mevcut hadise (sis, sığ veya yamalı sis, pus, kurudumanı, çisenti, yağmur, kar); (iii) özellikle gece soğuması ile yüzey tabakasının kuruması veya nemlenmesini yansıtan 1, 3 ve 6 saatlik eğilimler; (iv) 12 saatlik maksimumdan bu yana soğuma, önceki 6–72 saatteki sis, pus, yağış ve kar oranları ve son sisten bu yana geçen süre gibi bellek terimleri; (v) NOAA Güneş konumu denklemleriyle [@spencer1971] hem tahmin hem geçerlilik zamanında hesaplanan Güneş yükseklik açısı ve gün doğumuna kalan süre dahil takvim ve astronomik terimler. Geçerlilik zamanına ait astronomik terimler deterministik olduğundan önceden bilinmeleri meşrudur.

{{table:features|col}}{#tab:feat}

## Modeller

Standartlaştırılmış ve medyanla doldurulmuş girdilerle lojistik regresyon (LR) [@cox1958] istatistiksel temel modeldir. Rastgele ormanlar (RF) [@breiman2001] ile gradyan artırma kütüphaneleri XGBoost [@chen2016] ve LightGBM [@ke2017] ağaç topluluklarını temsil etmektedir; her iki artırma kütüphanesi eksik değerleri doğrudan işleyebilmekte olup hiperparametreleri Optuna'daki [@akiba2019] ağaç yapılı Parzen kestiricisiyle 30 denemede, erken durdurma kullanılarak ve doğrulama PR-AUC değeri en büyüklenecek biçimde ayarlanmıştır. RF ve LR için küçük doğrulama ızgaraları kullanılmıştır. Zamansal örüntüler uzun kısa süreli bellek (LSTM) [@hochreiter1997] ve kapılı yinelemeli birim (GRU) [@cho2014] ağlarıyla öğrenilmektedir. Tek bir çok görevli ağ, 22 standartlaştırılmış durum değişkeninin ve bir gözlem maskesinin son 12 saatini (24 ızgara adımı) okur, son gizli durumunu bellek ve geçerlilik zamanı öznitelikleriyle birleştirir ve iki katmanlı bir çıkış bloğuyla dokuz görevin (üç hedef × üç öngörü süresi) tamamını tahmin eder. Maskelenmiş ve pozitif sınıf ağırlıklı ikili çapraz entropi, AdamW [@loshchilov2019] ile ve ortalama doğrulama PR-AUC değerine göre erken durdurmayla en küçüklenmiş; altı mimari doğrulama sezonlarında karşılaştırılmıştır. Tüm modeller scikit-learn [@pedregosa2011] ve PyTorch [@paszke2019] ile gerçekleştirilmiştir; seçilen ayarlar Ek'te listelenmiştir.

## Sınıf Dengesizliği ve Kalibrasyon

Sis, gözlemlerin yalnızca %1,0'ını, RVR < 350 m ise yalnızca %0,6'sını oluşturmaktadır. LR ve LightGBM için dört strateji karşılaştırılmıştır [@he2009]: düzeltme yapmamak, sınıf ağırlıklandırma, SMOTE ile aşırı örnekleme [@chawla2002] ve rastgele alt örnekleme. Yeniden ağırlıklandırma ve örnekleme tahmin olasılıklarını bozduğundan her model; eşleme yapılmadan, Platt ölçeklemesiyle [@platt1999] veya izotonik regresyonla [@zadrozny2002] yeniden kalibre edilmektedir; yöntem, doğrulama sezonlarında Brier skorunun bir-sezon-dışarıda çapraz doğrulamasıyla seçilmekte [@niculescu2005] ve ardından tüm doğrulama kümesinde yeniden uydurulmaktadır. Uyarı eşiği $\tau_{h}$, doğrulama kümesinde kritik başarı indeksini (CSI) en büyükleyen değerdir; $F_{1}=2\,\mathrm{CSI}/(1+\mathrm{CSI})$ olduğundan aynı eşik $F_{1}$'i de en büyükler.

## Eğitim Protokolü ve Veri Sızıntısının Önlenmesi

Veri, sezonlarla hizalı biçimde kronolojik olarak bölünmüştür (Tablo @tab:split): eğitim 01/2005–06/2019, doğrulama 07/2019–06/2022 (üç sis sezonu) ve test 07/2022–06/2026 (dört sis sezonu); Temmuz 2026 sonrası operasyonel değerlendirmeye ayrılmıştır. Rastgele bir bölme, bir sis olayının ardışık yarım saatlik örnekleri neredeyse aynı olduğundan bilgi sızıntısına yol açardı [@kaufman2012]. Tüm ayarlama, kalibrasyon ve eşik kararlarında yalnızca doğrulama sezonları kullanılmış, test sezonları yalnızca bir kez değerlendirilmiştir. Otomatik testler, $t$ anındaki her özniteliğin $t$ sonrasındaki tüm rasatlar silindiğinde değişmediğini ve hedef değişkenin hiçbir zaman $t$ anındaki gözlemi yeniden kullanmadığını doğrulamaktadır.

{{table:splits|col}}{#tab:split}

## Karşılaştırma Tahminleri

Kalıcılık (persistence) tahmini, $t+h$ için o anda gözlenen durumu tahmin eder. Klimatoloji, eğitim dönemindeki geçerlilik zamanının takvim ayı ve UTC saatine koşullu olay sıklığıdır ve Brier beceri skorunun referansıdır. $t$ anında yayımlanan METAR'a eklenen TREND $h \le 2$ saat için değerlendirilmekte; $t+h$ için TAF tahmini ise $t$ anında veya öncesinde yayımlanan son TAF'tan alınmaktadır; böylece tahmincinin bilgi ufku modellerinkine eşitlenmektedir. TREND ve TAF değişim grupları içerdiğinden geçerlilik zamanında bir görüş aralığına dönüştürülmektedir [@mahringer2008]: hâkim okuma temel tahmini, FM gruplarını ve tamamlanmış BECMG değişimlerini; en kötü durum okuması ise ek olarak BECMG geçişlerinin ve TEMPO ile PROB30/40 gruplarının alt sınırını kullanmaktadır. Okuma 1000 m'nin altındaysa sis tahmini verilmiş sayılır.

## Doğrulama

$a$ isabet, $b$ yanlış alarm, $c$ kaçırma ve $d$ doğru ret sayısı olmak üzere kategorik skorlar şöyledir [@jolliffe2012; @wilks2019]:

$$ \mathrm{POD}=\frac{a}{a+c},\quad \mathrm{FAR}=\frac{b}{a+b},\quad \mathrm{CSI}=\frac{a}{a+b+c} $$ {#eq:pod}

$$ \mathrm{HSS}=\frac{2(ad-bc)}{(a+c)(c+d)+(a+b)(b+d)} $$ {#eq:hss}

Burada Heidke beceri skoru (HSS), doğruluğu rastlantısal tahmine göre ölçmektedir [@heidke1926; @doswell1990]. Olasılıksal tahminler, nadir olaylar için bilgilendirici olan kesinlik–duyarlılık eğrisi altındaki alan (PR-AUC) [@saito2015; @davis2006], ROC eğrisi altındaki alan ve Brier skoru ile beceri skoru [@brier1950; @murphy1973] ile değerlendirilmektedir:

$$ \mathrm{BS}=\frac{1}{N}\sum_{i=1}^{N}(p_{i}-o_{i})^{2},\qquad \mathrm{BSS}=1-\frac{\mathrm{BS}}{\mathrm{BS}_{\mathrm{klim}}} $$ {#eq:bs}

ILS kategorileri için sıralı olasılık skoru [@epstein1969]

$$ \mathrm{RPS}=\frac{1}{K-1}\sum_{k=1}^{K}\left(F_{k}-O_{k}\right)^{2} $$ {#eq:rps}

birikimli tahmin ve gözlem dağılımları $F_{k}$ ve $O_{k}$ ($K=3$) ile test kümesinde ortalaması alınarak ay–saat sınıf klimatolojisine göre bir beceri skoru (RPSS) olarak ifade edilmektedir. Yarım saatlik örnekler güçlü öz ilişki gösterdiğinden %95 güven aralıkları tüm günleri yeniden örnekleyen bir blok bootstrap ile elde edilmekte [@kunsch1989; @wilks1997], tahminler arasındaki farklar ise aynı günlerin eşleştirilmiş yeniden örneklemeleriyle (kategorik skorlar için 2000, PR-AUC ve BSS için 300 yineleme) sınanmaktadır.

## Açıklanabilirlik

LightGBM modelleri, ağaçlar için TreeSHAP [@lundberg2020] ile tam olarak hesaplanan SHAP değerleriyle [@lundberg2017] açıklanmaktadır. Log-odds çıktısı $g(\mathbf{x})$ olan bir tahmin için katkılar $\phi_{j}$ yerel doğruluk özelliğini sağlar:

$$ g(\mathbf{x})=\phi_{0}+\sum_{j=1}^{M}\phi_{j} $$ {#eq:shap}

Burada $\phi_{0}$ beklenen model çıktısı, $\phi_{j}$ ise $j$ özniteliğinin Shapley değeridir [@shapley1953]. Küresel önem, tüm sis durumlarını ve rastgele seçilmiş 6000 sissiz durumu içeren bir test örneğinde ortalama mutlak SHAP değeriyle özetlenmekte; bağımlılık grafikleri ise katkıları sisin fiziksel etkenleriyle ilişkilendirmektedir [@mcgovern2019].

## Erken Uyarı Uygulaması

Operasyonel sistem bir FastAPI web uygulamasıdır (Şekil @fig:app). Uygulama her on dakikada bir son 120 saatin METAR'larını NOAA Aviation Weather Center'dan (yedek kaynak IEM) indirir; çevrimdışı çalışmayla tamamen aynı çözme, kalite kontrolü, ızgaralama ve öznitelik kodunu çalıştırır ve 1–6 saat için kalibre edilmiş sis olasılıklarını, 1, 3 ve 6 saat için ILS kategorisi görünümünü, bir uyarı seviyesini ve öne çıkan SHAP katkılarını yayımlar. Sis gözleniyorsa veya 1–2 saatlik olasılık eşiğini aşıyorsa uyarı kırmızı, yalnızca 3–6 saatlik tahminler eşiklerini aşıyorsa turuncu, herhangi bir olasılık eşiğinin yarısını aşıyorsa sarıdır (izleme). Her tahmin kaydedilmekte ve geçerlilik zamanı geldiğinde otomatik olarak doğrulanmaktadır; böylece gerçek anlamda gerçek zamanlı bir doğrulama kaydı oluşmaktadır.

# Bulgular

## Genel Başarım

Tablo @tab:main, dört test sezonundaki tüm tahminlerin skorlarını vermektedir. 1 saatte tüm ML modelleri kalıcılık tahmininden açıkça daha başarılıdır; LightGBM en iyi CSI (0,729) ve HSS (0,842) değerlerine ve 0,739'luk bir Brier beceri skoruna ulaşırken kalıcılığın CSI değeri 0,652'dir. Fark öngörü süresiyle büyümektedir: 3 saatte en iyi CSI 0,472 (LSTM) iken kalıcılıkta 0,321, 6 saatte ise 0,340 (LSTM) iken 0,129'dur. Kalıcılık 3 ve 6 saatte klimatolojiden bile kötüleşirken (negatif BSS) tüm ML modelleri 6 saatte 0,26 ile 0,32 arasında BSS değerlerini korumaktadır. Çok sayıdaki kolay sissiz durum nedeniyle ROC alanları her modelde 0,98'in üzerindedir; bu yüzden Şekil @fig:pr'deki PR eğrileri daha bilgilendiricidir: 1 saatte altı model neredeyse ayırt edilemezken 3 ve 6 saatte yinelemeli ağlar eğrinin büyük bölümüne hâkimdir ve en yüksek PR-AUC değerlerine ulaşır (GRU: 0,685 ve 0,517).

{{table:main_results|page}}{#tab:main}

![page](pr_curves.png){#fig:pr} Test sezonlarında sis tahminlerinin kesinlik–duyarlılık eğrileri (parantez içinde PR-AUC). İşaretler deterministik karşılaştırma tahminlerini göstermektedir.

Gün-blok bootstrap (Tablo @tab:ci), iyileşmelerin sağlam olduğunu doğrulamaktadır: altı modelin her biri ile kalıcılık arasındaki eşleştirilmiş CSI ve HSS farkları üç öngörü süresinin tamamında anlamlı biçimde pozitiftir—örneğin LightGBM için ΔCSI 1 saatte 0,077 [0,052; 0,104], 3 saatte 0,146 [0,105; 0,188] ve 6 saatte 0,168 [0,099; 0,234]'tür. Beceri öngörü süresiyle düzgün biçimde azalmakta (Şekil @fig:lead), LightGBM'nin kalıcılığa göre göreli CSI kazancı 1 saatte %12'den 3 saatte %45'e ve 6 saatte %130'a yükselmektedir. İyileşme elverişli tek bir yıla da bağlı değildir: her model, dört test sezonunun her birinde ve her öngörü süresinde kalıcılıktan daha başarılıdır (Tablo @tab:season).

{{table:bootstrap_ci|col}}{#tab:ci}

{{table:per_season|col}}{#tab:season}

![col](leadtime.png){#fig:lead} Test sezonlarında LightGBM ve kalıcılık tahminlerinin öngörü süresine göre CSI ve HSS değerleri ile 1 saatte METAR TREND tahmini. Gölgelendirme: 1, 3 ve 6 saatte hesaplanan %95 gün-blok bootstrap aralıkları (aradaki değerler enterpole edilmiştir).

## Resmî TREND ve TAF Tahminleriyle Karşılaştırma

TREND tahmini her test METAR'ında mevcuttur. Aynı durumlar üzerinde (Tablo @tab:trend) TREND'in hâkim okuması 1 saatte CSI 0,623 ve HSS 0,767, en kötü durum okuması ise 0,622 ve 0,765 değerlerine ulaşmakta; bu değerler kalıcılığın (0,652 ve 0,788) biraz altındadır. Başka bir deyişle resmî 2 saatlik tahmin mevcut gözlemin ötesinde nadiren bilgi eklemektedir: TREND grupları çoğunlukla iyileşmeleri bildirmekte, yeni sis oluşumu ise nadiren öngörülmektedir. LightGBM TREND'i ΔCSI = 0,105 [0,075; 0,140] ve ΔHSS = 0,076 [0,053; 0,103] farkla geçmektedir; her iki fark da anlamlıdır. Çalışmanın yazıldığı sırada erişilebilen 30 günlük TAF penceresinde (29 Eylül–30 Ekim 2026; öngörü süresi başına yaklaşık 1 420 tahmin) sis gözlenmemiştir; ne TAF—her iki okumada da—ne de LightGBM sis tahmini vermiş, dolayısıyla ikisi de yanlış alarm üretmemiştir; en kötü durum TAF okuması ise durumların yaklaşık %8'inde 5 km'nin altında pus bildirmiştir. Sis sezonunu kapsayan bir TAF karşılaştırması bu nedenle canlı doğrulamaya bırakılmıştır.

{{table:trend|col}}{#tab:trend}

## Sis Başlangıçları ve Dağılmaları

Başlangıç ve dağılmalar, kalıcılık tahmini ikisini de öngöremediği için kısa vadeli tahminin operasyonel değer yarattığı anlardır. Şekil @fig:onset, test sezonlarındaki 48 sis başlangıcının (en az 2 saat sissiz geçen sürenin ardından sis) ve 44 dağılmanın doğru tahmin edilme oranını göstermektedir. Dağılmalar iyi yakalanmaktadır: 1 saatte XGBoost dağılmaların %45'ini doğru tahmin etmekte (kalıcılık: %0), 6 saatte GRU %86'ya ulaşmaktadır (kalıcılık: %68). Başlangıçlar ise en zor problem olmaya devam etmektedir: CSI'yı en büyükleyen eşiklerde modeller başlangıçların %2–21'ini yakalarken kalıcılıkta bu oran %0–4'tür. Kademeli uyarı tasarımı bu sınırlılığı hafifletmektedir: izleme seviyesinde ($\tau_{h}/2$) LightGBM, başlangıçların 1, 3 ve 6 saat önceden sırasıyla %25, %21 ve %38'ini işaretlerken CSI yalnızca 0,729'dan 0,692'ye, 0,467'den 0,435'e ve 0,297'den 0,271'e düşmektedir.

![col](onset_dissipation.png){#fig:onset} CSI'yı en büyükleyen eşiklerde test sezonlarındaki sis başlangıçlarının (solda) ve dağılmalarının (sağda) doğru tahmin edilme oranı.

## ILS Kategorisi Tahminleri

Tablo @tab:rvr ve Şekil @fig:rvr sıralı RVR tahminlerini özetlemektedir. Tüm ML modelleri her öngörü süresinde pozitif bir sıralı olasılık beceri skoruna ulaşmaktadır—1 saatte 0,636 (LightGBM), 3 saatte 0,407 (XGBoost) ve 6 saatte 0,281 (LSTM)—buna karşılık kalıcılık 0,427'den −0,166'ya ve −0,695'e düşmektedir. CAT III koşulları (RVR < 350 m) için LightGBM 1 saatte CSI 0,578'e, GRU ise 3 saatte 0,371'e ulaşmaktadır (kalıcılık: 0,521 ve 0,225). Karışıklık matrisleri CAT III'ün iyi tanındığını (1 saatte durumların %76'sı), ara sınıf olan CAT II'nin ise komşu sınıflarla sık karıştırılan en zor sınıf olduğunu göstermektedir; bu, RVR'nin dar bir geçiş bandı için beklenen bir durumdur.

{{table:rvr|col}}{#tab:rvr}

![page](rvr_confusion.png){#fig:rvr} Test sezonlarında LightGBM ILS kategorisi tahminlerinin karışıklık matrisleri (sayılar ve satır bazında normalleştirilmiş oranlar).

## Sınıf Dengesizliği ve Kalibrasyon

Dengesizlik deneyi (Tablo @tab:imb), sınıf ağırlıklandırma, SMOTE ve alt örneklemenin sıralama kalitesini güvenilir biçimde iyileştirmediğini—LR'de doğrulama PR-AUC değerini 0,759'dan 0,720–0,747'ye düşürdüğünü—ancak ham olasılıkları ciddi biçimde bozduğunu göstermektedir: sınıf ağırlıklandırma LR'nin doğrulama Brier skorunu on kat artırmaktadır (0,0026'dan 0,0261'e). Yeniden kalibrasyon bu bozulmanın büyük bölümünü gidermekle birlikte en basit seçenek olan örnekleme yapmadan kalibrasyon, alternatifleri kadar veya onlardan daha iyidir; bu nedenle tüm nihai modellerde bu seçenek kullanılmıştır. Kalibre edilmiş tahminlerin güvenilirlik eğrileri tüm öngörü sürelerinde köşegeni yakından izlemektedir (Şekil @fig:rel). Bu sonuç önemsiz değildir: test sezonlarındaki sis sıklığı (%0,64) eğitim döneminin (%1,24) yalnızca yarısıdır ve en güncel sezonlarda yapılan kalibrasyon olasılıkları bu değişime uyarlamıştır.

{{table:imbalance|col}}{#tab:imb}

![col](reliability.png){#fig:rel} Test sezonlarında kalibre edilmiş LightGBM (düz çizgi) ve GRU (kesikli çizgi) sis tahminlerinin güvenilirlik diyagramı; 15'ten az tahmin içeren aralıklar gösterilmemiştir.

## Açıklanabilirlik

SHAP analizi fiziksel olarak tutarlı bir tablo ortaya koymaktadır. 1 saatte tahmin anlık duruma—bağıl nem, minimum ve hâkim görüş ile çiy noktası farkı (Şekil @fig:shapbar)—hâkimdir ve bu grup toplam katkının %78'ini taşımaktadır (Şekil @fig:groups). Öngörü süresi arttıkça anlık durumun payı 6 saatte %41'e düşerken astronomik ve takvim terimlerinin payı %6'dan %28'e, sınır tabaka belleğinin payı ise %6'dan %21'e yükselmektedir.

![page](shap_bar.png){#fig:shapbar} 1, 3 ve 6 saatlik LightGBM sis modellerinde en önemli on beş özniteliğin ortalama mutlak SHAP değerleri.

![col](shap_groups.png){#fig:groups} Öznitelik grubu ve öngörü süresine göre toplam ortalama mutlak SHAP değerinin payı.

6 saatte sıralamanın başında 6 saatlik maksimum bağıl nem, bağıl nem, çiy noktası farkı ve sıcaklık yer almakta; bunları geçerlilik zamanında gün doğumundan bu yana geçen süre, gece uzunluğu ve gün doğumuna kalan süre izlemektedir (Şekil @fig:bee): yüksek nem, küçük çiy noktası farkı, düşük sıcaklık ve uzun geceler tahmini sise doğru iterken gün doğumundan sonraki geçerlilik zamanları tahmini sisten uzaklaştırmaktadır—bu, radyasyon sisinin tipik imzasıdır.

![col](shap_beeswarm_6h.png){#fig:bee} 6 saatlik modelde en önemli on iki özniteliğin SHAP değerleri; renk, öznitelik değerinin yüzdelik sırasını göstermektedir.

Bağımlılık grafikleri (Şekil @fig:dep) ders kitabı düzeyindeki sis fiziğini yeniden üretmektedir: 2 °C veya daha küçük çiy noktası farkları log-odds değerini +1,4'e kadar artırırken 4 °C ve üzerindeki farklar azaltmaktadır; sakin ve hafif rüzgârlar (≤ 3 kt) sisi desteklerken 4–10 kt'lık rüzgârlar mekanik karışımla sisi bastırmaktadır; yaklaşık %93'ün üzerindeki 6 saatlik maksimum bağıl nem sisi güçlü biçimde desteklemektedir; geçerlilik zamanında Güneş ufkun yaklaşık 15° üzerine çıktığında ise katkı negatife dönmekte ve Güneş ısıtmasıyla dağılmayı yansıtmaktadır.

![page](shap_dependence.png){#fig:dep} 3 saatlik sis modelinin çiy noktası farkı, rüzgâr hızı, geçerlilik zamanındaki Güneş yükseklik açısı ve 6 saatlik maksimum bağıl neme göre SHAP bağımlılığı; renk etkileşen bir değişkeni göstermektedir.

## Olay İncelemesi: 17–18 Aralık 2022

Şekil @fig:case, test döneminden iki aşamalı bir olayı göstermektedir. Sis 17 Aralık'ta yaklaşık 10 UTC'ye kadar sürmüş, öğleden sonra açılmış ve 16:50 UTC'de yeniden oluşarak RVR çoğunlukla 200–400 m arasında kalmak üzere 18 Aralık 03:50 UTC'ye kadar devam etmiştir. Görüşün henüz 1200 m olduğu 16:20 UTC'de 3 saatlik model 0,82 sis olasılığı (eşik 0,33), yani yeniden oluşum için doğru bir uyarı vermiştir. Bu tahminin SHAP açıklaması (Şekil @fig:local) tahmini düşen minimum görüşe (+1,74), 650 m'lik RVR'ye (+0,96), 1 °C'lik çiy noktası farkına (+0,88) ve %93'lük bağıl neme (+0,88) dayandırmaktadır—deneyimli bir tahmincinin kullanacağı ipuçlarının tam olarak aynısı. 1 saatlik tahminler olayı yakından izlemekte, 3 ve 6 saatlik tahminler akşam saatlerinde olasılığı yükseltip sisin gece boyunca süreceğini öngörmektedir; gün doğumundan sonra tüm öngörü süreleri dağılmayı doğru tahmin etmekte, uzun öngörü süreleri ise daha geç tepki vermektedir.

![page](case_study.png){#fig:case} 17–18 Aralık 2022'de LTAC'de gözlenen görüş ve RVR ile her geçerlilik zamanından 1, 3 ve 6 saat önce verilen LightGBM sis olasılıkları.

![col](shap_waterfall.png){#fig:local} 17 Aralık 2022 16:20 UTC'de verilen 3 saatlik tahminin SHAP açıklaması (görüş 1200 m; sis 30 dakika sonra oluştu).

## Operasyonel Başarım

Hizmete alınan uygulama (Şekil @fig:app) iki yolla doğrulanmıştır. İlk olarak test kümesi sonrasındaki operasyonel dönem (Temmuz–Ekim 2026) web uygulamasının koduyla yeniden oynatılmış ve öngörü süresi başına 5 727–5 737 tahmin elde edilmiştir (Tablo @tab:live); bu sıcak sezon döneminde sis oluşmamış ve sistem hiçbir öngörü süresinde sis uyarısı vermemiştir, yani hiç yanlış alarm üretmemiştir. İkinci olarak, canlı sistemin yaptığı gibi öznitelikleri yalnızca önceki 120 saatin rasatlarından 40 rastgele zamanda yeniden hesaplayan bir eşdeğerlik testi, toplu (batch) olasılıkları makine hassasiyetinde yeniden üretmiştir (240 karşılaştırmada en büyük fark 0,0). Canlı kayıt 29 Ekim 2026'da, 2026/27 sis sezonunun başında başlamıştır ve otomatik olarak doğrulanan kayıt dönem boyunca sürekli güncellenmektedir.

![col](app_screenshot.png){#fig:app} Web tabanlı erken uyarı uygulaması: uyarı bandı, önümüzdeki 6 saat için kalibre edilmiş sis olasılıkları, anlık koşullar, ILS kategorisi görünümü ve SHAP tabanlı etkili faktörler.

{{table:live|col}}{#tab:live}

# Tartışma

Bulgular, yalnızca gözleme dayalı bir kısa vadeli tahminin Esenboğa'da hem kalıcılık tahminine hem de resmî TREND tahminine önemli ölçüde beceri katabildiğini göstermektedir. Üç nokta özellikle vurgulanmalıdır. Birincisi, en iyi model öngörü süresine bağlıdır: 1 saatte anlık durumdaki keskin eşiklerden yararlanan ağaç toplulukları en iyiyken 3–6 saatte yinelemeli ağlar 12 saatlik geçmişten daha fazla bilgi çıkarmakta ve en iyi olasılıksal skorlara ulaşmaktadır. Operasyonel bir sistem bu nedenle en kısa sürelerde artırma yöntemlerini, 2 saatin ötesinde yinelemeli ağları birleştirebilir. İkincisi, SHAP analizi modellerin rastlantısal ilişkiler yerine radyasyon sisinin fiziğini—doygunluk, zayıf karışım ve günlük ışınım döngüsü—öğrendiğini doğrulamaktadır; bu, tahmincilerin güvenini desteklemekte [@mcgovern2019] ve LTAC'de radyasyon sisinin baskınlığıyla uyumludur [@camalan2010]. Üçüncüsü, TREND ile karşılaştırma resmî 2 saatlik tahminin esasen kalıcılık olduğunu, dolayısıyla mütevazı bir veriye dayalı kılavuzun bile çok kısa vadeli hizmeti iyileştirebileceğini göstermektedir.

Çalışmanın sınırlılıkları da bulunmaktadır. Yalnızca nokta gözlemleri kullanılmıştır; tek bir METAR'da görülemeyen sınır tabaka süreçlerine ve adveksiyona bağlı olan sis başlangıçlarını tahmin etmek zor olmaya devam etmektedir ve sayısal hava tahmini, uydu veya tavan ölçer (seilometre) verileri bu konuda büyük olasılıkla iyileşme sağlayacaktır [@herman2016; @kamangir2021]. Test sezonları için tarihsel TAF arşivine erişilemediğinden TAF karşılaştırması kısa ve sissiz bir pencereyle sınırlı kalmıştır; bu karşılaştırma canlı doğrulamayla tamamlanacaktır. Yalnızca tek bir havalimanı incelendiğinden aktarılabilirlik değerlendirilmemiştir [@cerda2025]. Son olarak sis sıklığının 21 yıl boyunca azalması durağan olmayan bir süreci işaret etmektedir; sezonlarla hizalı doğrulama ve güncel sezonlarda kalibrasyon bu etkiyi azaltmış olsa da modellerin dönemsel olarak yeniden eğitilmesi gerekecektir.

# Sonuç

Bu makalede Ankara Esenboğa Havalimanı'nda sis ve düşük görüş için ilk makine öğrenmesi tabanlı kısa vadeli tahmin sistemi sunulmuştur. Kalite kontrolünden geçirilmiş 21,8 yıllık METAR/SPECI rasatlarına dayanan ve dört bağımsız sis sezonunda doğrulanan tüm modeller kalıcılık tahmininden anlamlı biçimde daha başarılı olmuş, LightGBM ise 1 saatte resmî METAR TREND tahminini CSI'da 0,105 farkla geçmiştir. Kalibre edilmiş olasılıklar, ILS kategorisi tahminleri ve SHAP açıklamaları tahminleri operasyonel olarak yorumlanabilir kılmakta; açık kaynaklı web uygulaması ise bunları sürekli öz doğrulamayla gerçek zamanlı olarak sunmaktadır. Gelecek çalışmalarda başlangıç tespitini iyileştirmek için sayısal model ve uydu öznitelikleri eklenecek, TAF karşılaştırması tam sis sezonlarına genişletilecek ve yaklaşım diğer Türk havalimanlarına aktarılacaktır.

# Ek {-}

Doğrulama sezonlarında seçilen hiperparametreler Tablo @tab:hp'de listelenmiştir. Veri setinin tamamı, çözücü, eğitim ve değerlendirme betikleri, eğitilmiş modeller, İngilizce ve Türkçe şekiller ve web uygulaması https://github.com/AtaSakik/esenboga-fog-nowcasting adresindedir; tek bir betik bu makaledeki tüm sayıları yeniden üretmektedir.

{{table:hyperparams|col}}{#tab:hp}

# Teşekkür {-}

Yazar, meteorolojik arşivlerini açık erişime sunan Iowa Environmental Mesonet, Ogimet ve NOAA Aviation Weather Center'a ve proje süresince verdiği rehberlik için YMH453 Makine Öğrenmesi dersinin öğretim üyesine teşekkür eder.

# Kaynaklar {-}
