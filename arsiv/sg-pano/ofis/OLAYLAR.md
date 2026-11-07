# Olay → animasyon eşlemesi (sürüm 2)

**İlke:** ofisteki her hareket bir olaydan doğar; boşta "çalışıyormuş gibi" sahte hareket yoktur. Olay akışı örnekte
`ornek_durum.json` → `olaylar[]` içinde simüle edilir (şema: `SEMA.md`). Her olay ayrıca **Gözcü kaydına** (`zaman · oda · olay`) yazılır
ve olayın odası ~3 sn **vurgulanır** (sarı çerçeve + yumuşak parıltı). Sol dikey menüdeki oda düğmesi ve Gözcü kaydı satırı aynı odaya götürür. Animasyon süreleri `office.js` içindedir.

| Olay (`tur`) | Tetikleyen durum | Ofiste ne olur | Panelde ne değişir |
|---|---|---|---|
| `yeni_adres` | Haftalık tarama yeni adres buldu | Yeni figür binanın önünden girişe yürür, Kapı'da turnike arasında bekler. Tarama odası vurgulanır, balonda büyüteç, Tarama duvar ekranında tarama çizgisi gezer | Gözcü kaydı |
| `kapi_gecti` | Ön eleme geçti | Figür Kapı'dan çıkıp avlunun taş yolundan Lab'ın boş masasına yürüyüp oturur. Kapı + Lab vurgulanır, balonda onay | Havuz sayısı +1 (Özet, Huni) |
| `kapi_elendi` | Ön eleme kaldı (neden olayda) | Figür geldiği yoldan çıkışa yürür, kapıdan çıkınca kaybolur. Kapı vurgulanır, kırmızı uyarı balonu | Gözcü kaydı (neden) |
| `havuzdan_cikar` | Havuz kuralı: adres düştü | Lab'daki figür kalkar, Kapı'dan çıkıp kaybolur; masa boş sandalye kalır | Havuz −1 |
| `terfi` | Kat geçiş kuralı sağlandı (Lab → Aday → Oda) | Figür masasından kalkıp hedef katın boş masasına yürür (avlunun taş yolları ve kapılardan). İki oda vurgulanır, hedefte yukarı-ok balonu | Kat sayıları, Oda doluluğu |
| `kat_dusur` | Histerezis / zarar kesme: kat düştü | Aynı yürüyüş, ters yönde; aşağı-ok balonu (kırmızı) | Kat sayıları |
| `islem_acildi` | Yeni gölge işlem (yeni sinyal) | İlgili masanın **monitörü parlar** (4 sn), sonra işlem sürdükçe mum grafiği yanık kalır (yeşil kâr / kırmızı zarar). Masanın odası vurgulanır | Açık işlem tablosuna satır; Özet: açık işlem, "bugün açıldı" |
| `islem_kapandi` | İşlem kapandı (trader kapattı / zarar kesme / süre) | Masanın ekranı söner (başka işlem yoksa). **Finans**: kasadan para parıltısı yükselir, duvar eğrisi yanıp söner, oda vurgulanır | Tablo → Son kapananlar (neden, süre, K/Z); kasa ve "bugün K/Z" |
| `bildirim` | Telegram bildirimi gitti | **Postacı masasından kalkıp zarfla posta kutusuna yürür**, zarfı bırakır; zarf sağ üste süzülüp kaybolur; Haberleşme duvar ekranı mavi parlar | Telegram kartı: bugün n, son bildirimler |
| `risk_tavan` | Bir risk tavanı doldu (≥ %100) | Risk odasında **alarm lambası** yanıp söner (kırmızı ışık), duvardaki çubuk ekranın çerçevesi kırmızı yanıp söner; oda vurgulanır | Risk kartı: çubuk kırmızı, "TAVAN DOLU" |
| `risk_normal` | Tavan altına indi | Alarm lambası söner; onay balonu | Risk çubuğu normale döner |
| `veri_bayat` | Oda verisi eşikten eski (`yas_dk`) | Oda **renksizleşir** (gri), plakaya "veri eski" (taralı şerit) eklenir, odanın sıcak iç ışığı söner, odadaki ekranlar söner; saat balonu | Veri kalitesi satırı sarı "bayat" |
| `veri_taze` | Bayat veri yenilendi | Oda rengine ve iç ışığına döner, plaka normalleşir | Satır tekrar "tamam" |
| `denetim` | Denetçi sağlama / kalite kontrolü | Sunucu dolabı LED'leri yeşil (tamam) ya da amber (uyarı) olur; Denetim vurgulanır, onay/göz balonu | "Sağlama" satırı |
| `arsiv_yazildi` | Arşive yeni satırlar yazıldı | Arşiv rafı yanındaki yığına **yeni koli** konur (yığın 5'e çıkınca 3'e döner), parıltı | Arşiv satır sayısı |
| `kasa_guncelle` | Kasa değişti (funding vb.) | Finans'ta para parıltısı + duvar eğrisi parlar | Gölge kasası değeri |
| `kural_kitabi` | Kural kitabı / ön kayıt kaydedildi | Sekreterlik'te belge balonu, oda vurgusu | Gözcü kaydı |
| `kullanici_karari` | Kullanıcı kararı işlendi | Makam'da onay balonu, oda vurgusu | Gözcü kaydı |
| `veri_yenile` | Saatlik veri yenilemesi | Finans + Oda vurgulanır | Açık işlemlerde K/Z, lik. uzaklığı güncellenir |
| `kirmizi_bayrak` | Denetim bir trader için kırmızı bayrak koydu (ör. vault oranı eşiği aştı) | **Denetçi masasından kalkıp** trader'ın masasına yürür, **kırmızı bayrak notu** bırakır ve masasına döner. Not, bayrak kalkana kadar masada durur; Denetim + trader odası vurgulanır | Trader bilgi kutusunda "Kırmızı bayrak" satırı; Denetçi satırında açık bayrak sayısı |
| `bayrak_kalkti` | Bayrak nedeni ortadan kalktı | Denetçi yine masaya yürüyüp notu alır; not masadan kalkar | Bayrak satırı kaybolur |
| `sistem` | Örnek akış başa sardı | — (yalnız örnek akışta) | Gözcü kaydı; sayılar ilk veriye döner |

## İletişim işaretleri (olay → zarf / not / ok)
Her işaret **bir olaydan** doğar ve `olay_id` taşır; işarete tıklayınca bilgi kutusu olay_id, zaman ve kuralı gösterir. Olay yoksa işaret yoktur.
Renk anlamı: **aqua = bilgi, kayısı = uyarı**; hiçbir renk kâr/zarar ya da performans anlamı taşımaz. İşaretler ~3,6 sn görünür; aynı anda en fazla 8 işaret çizilir.

| Olay | İşaret (kimden → kime) |
|---|---|
| `yeni_adres` | **zarf** Tarama → Kapı (uçar) + ok |
| `kapi_gecti` | **ok** Kapı → Lab |
| `kapi_elendi` | **not** (uyarı) Kapı → çıkış |
| `havuzdan_cikar` | **ok** Lab → Kapı |
| `terfi` | **ok** eski kat → yeni kat + **not** trader'ın yeni masasına |
| `kat_dusur` | **ok** (uyarı) eski kat → yeni kat + **not** (uyarı) trader'a |
| `islem_acildi` | **not** trader'ın odası → Finans |
| `islem_kapandi` | **zarf** trader'ın odası → Finans |
| `bildirim` | **zarf taşıyan figür** (Postacı → posta kutusu) + **zarf** posta kutusu → dışarı |
| `risk_tavan` | **ok** + **not** (uyarı) Risk → Oda |
| `risk_normal` | **ok** Risk → Oda |
| `veri_bayat` | **not** (uyarı) Denetim → bayat oda |
| `veri_taze` | **ok** Denetim → oda |
| `denetim` | **not** Denetim → Makam (uyarıda kayısı) |
| `arsiv_yazildi` | **ok** Denetim → Arşiv (koli yığını zaten çizilir) |
| `kasa_guncelle` | **ok** Finans → Makam (değer gösterilmez, ön kayıt) |
| `kural_kitabi` | **zarf** Sekreterlik → Makam |
| `kullanici_karari` | **not** Makam → Sekreterlik |
| `veri_yenile` | **ok** Finans → Oda |
| `kirmizi_bayrak` | **not taşıyan figür** (Denetçi → trader masası) + kalıcı **kırmızı bayrak notu** masada |
| `bayrak_kalkti` | Denetçi notu alır (figür yürür) + **ok** trader → Denetim |

## Olay kuyruğu (hızlı gelen olaylar)
Durum her olayda **anında** güncellenir (sayılar, koltuklar, bayraklar, bayat odalar); animasyon yalnız bunu göstermenin yoludur.
- Aynı anda 4'ten fazla figür yürüyorsa yürüyüş 2×, 8'den fazlaysa 3× hızlanır.
- Bir güncellemede 3 ya da daha fazla olay birden gelirse (sekme uykudan döndü, hız yüksek) sonraki 4 sn boyunca figürler yürümez, **hedef yerine doğrudan geçer**; taşıyıcı figürler (zarf/not) atlanır; işaret sayısı 8 ile sınırlıdır.
- Hiçbir durumda eski bir animasyon yüzünden pano yanlış durum göstermez: bilgi kutusu, paneller ve masa ekranları her olayda yeniden çizilir.
- **Olay yokken çizim döngüsü durur** (kare çizilmez, zamanlayıcı sıradaki örnek olaya kadar uyur; yalnız risk alarmı yanıyorsa ~5 kare/sn yavaş döngü çalışır). Pencere yeniden görünür olunca ya da etkileşimde döngü uyanır.

## Tıklama etkileşimi (olay değil, kullanıcı eylemi)
- **Odaya giriş:** oda plakasına/zeminine ya da sol menüdeki oda düğmesine tıklamak aynı tuvalde kamerayı odaya yaklaştırır (~0,5 sn); diğer odalar soluklaşır, seçili odanın tam yükseklikli duvarları (ör. Arşiv, Denetim, Makam) kalkar. Adres `#oda/<id>`;
  Esc, **← Bina** düğmesi ve tarayıcı geri tuşu binaya döndürür. Dokunmada ≥ 44 px hedef; hareket azaltma açıksa geçiş anlıktır.
- **Bilgi kutusu:** kişiye, nesneye, iletişim işaretine ya da "Oda bilgisi" düğmesine tıklayınca açılır (masaüstü: sağda panel, telefon: alttan çekmece). Kimlik · Gerçek veri · Replik; hover'a bağlı işlev yoktur (fare ipucu yalnız ek kolaylıktır).
- **Tepki animasyonu:** tıklanan figür ~0,65 sn küçük bir sıçrama yapar ve üstünde gülümseme balonu çıkar. Yalnız tıklamayla olur; veri değiştirmez, kalıcı değildir; hareket azaltmada yalnız balon görünür.
- **Replikler:** olay repliği (`replikler.json` `veri`, olaydan ve sayılarla) ile **ofis esprisi** (`suz`, ayrı çerçeveli ve etiketli kutu, sayı/adres/oran içermez) birlikte gösterilir. Olay yoksa olay repliği gösterilmez.

## Ekran ve ışık durumları (olaydan değil, durumdan)
- **Masa monitörleri:** işlemi olan trader'ın ekranı grafik gösterir (mavi/mor ton; kâra ya da zarara göre renk **yok**), olmayanınki kapalıdır. Bayat odada tüm ekranlar kapalıdır.
- **Boş koltuk:** boş sandalye olarak çizilir (Oda 14/20 → 6 boş koltuk).
- **Gün ışığı (gerçek saate göre):** sabah turuncu, gündüz açık, akşam alacakaranlık, gece mavi. Kenarlara doğru hafif kararan **ortam ışığı** katmanı ve
  her odada **sıcak iç ışık** (gündüz hafif, akşam/gece belirgin) bu saatten türer. Bayat odada iç ışık yanmaz. Gece park/avlu lambaları, pencereler
  ve avlu havuzunun su altı ışığı yanar. Sol menü altındaki "ışık saati" yalnız bu saati gösterir. `?saat=SS:DD` ile denenir.
- **Sunucu ışıkları (Denetim):** sunucu dolabı LED'leri ve zemine vuran parıltı `denetim` durumudur: yeşil = tamam, amber = uyarı. Gündüz de hafif görünür; durum değişmedikçe sabittir.
- **Zemin ve küçük nesneler (süs, veri taşımaz, hareketsiz):** Makam parke, Denetim metal ızgara, Çay ocağı fayans; Çay ocağında semaver, Sekreterlik ve Haberleşme'de koliler;
  avluda havuz, şezlong, şemsiye, bank, lamba. Bunlar hiç hareket etmez ve bir sayıyı temsil etmez.

## Süs hareketi yok
Bu sürümde olaydan doğmayan **hiçbir** hareket yoktur: çaycı yürüyüşü ve ağaç sallanması kaldırıldı; su ve şemsiye durağandır. Masadakiler olay olmadıkça kıpırdamaz.
Performansı oyunlaştıran öğe de yoktur: işlem K/Z'si yalnız işaretli sayı olarak yazılır (renk, rozet, parıltı yok).

## `prefers-reduced-motion: reduce`
Çizim döngüsü durur (yaklaşık 0,7 sn'de bir yenilenir): yürüme yerine figür hedefine **hemen** geçer, vurgu ve alarm yanıp sönmez
(sabit yanık kalır), zarf/para/koli efektleri sabit çizilir, kamera geçişleri anlıktır. Olaylar yine işlenir
(Gözcü kaydı ve paneller güncellenir). `?hareket=0` aynı davranışı zorlar.

## Sürüm 2b: çekmece, bayatlık, özet, ses
- **Olay çekmecesi** (`cekmece.js`; rayda "Olaylar", Gözcü kaydında "Tümü · filtre"): oturumun olay günlüğü + `gecmis_olaylar`; oda, trader ve olay türü filtresi. Olaya tıklayınca kamera o odaya gider
  (`Off.spot`: oda ve ilgili figür halkayla vurgulanır, birkaç saniye sonra söner). Masaüstünde soldan panel, telefonda alttan çekmece; `Esc` kapatır.
- **Bayatlık** veriden türetilir, olay bayrağından değil: her veri kaynağının `esik_dk` alanı vardır (kodda sabit eşik yok); yaş = benzetim saati − kaynağın `zaman`ı. Ekran ve oda köşesinde "X dk önce";
  eşik aşılırsa oda sislenir, plakada ve köşede "VERİ ESKİ" yazar, panelde satır işaretlenir. `veri_bayat` kaynağın zamanını eskiye çeker, `veri_taze` yeniler; sis kendiliğinden kalkar.
- **Günlük özet** yalnız olay günlüğünden ("dün: 3 terfi, 1 çıkış, 2 bildirim"; boş günde "değişiklik yok"). Gruplar `kadro.json` `ozet_gruplari`nda.
- **Ses**: varsayılan kapalı (Ayarlar → "Olay sesi"), olay başına tek kısa ton (WebAudio, frekans `kadro.json` `olay_turleri[tur].ton`), dosya yok; olay yağmurunda en çok birkaç ton; tercih `sgofis.ses.v1`.
- **Kural metni** her yerde olaydaki `kural` alanından gelir (terfi: "gölgede ≥ 3 hafta ve ≥ 10 kapanmış işlem", ön kayıtla aynı); kodda veya replikte sabit sayı yoktur (test denetler).
- **Oda ayrıntıları:** Risk alarm paneli (tavan doluluğu, alarmda yanar), Haberleşme büyük ekran + zarf rafı (bugünkü bildirim sayısı, en çok 12 zarf), Sekreterlik ön kayıt kasası (sürüm, commit, dondurma tarihi), Oda trader masaları; her odanın bilgi kutusunda "Bu birim ne yapar / ne yapmaz" kartı.

## Ofis paneli (sol menü → açılan panel)
Masaüstünde kart sütunu gizlidir; sol menü öğesi odaya gider ve eşlenen kartları ofisin üstünde panel olarak açar (`PANEL_ESLE`): Finans → Gölge kasası · Risk → Risk tavanları · Oda → Açık gölge işlemleri + Son kapananlar · Arşiv → Veri kalitesi · Haberleşme → Telegram · Kontrol → Kohort ↔ Kontrol (kilitli) · Tarama/Kapı/Lab/Aday → Özet + Huni · diğerleri → oda bilgisi kartı. Kapatma: ×, Esc (önce panel, sonra oda), boş alan, aynı menüye ikinci tıklama, "Tüm ofis". Olay çekmecesi açılınca panel kapanır. Performans körlüğü kartların içeriğinde aynen geçerlidir.
