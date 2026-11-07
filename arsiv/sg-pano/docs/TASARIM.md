> **Not (2026-10-28, kullanıcı isteği `pano-sade`):** ana panonun sekmeleri **Özet · Trader'lar · Huni · Ayarlar** olarak yeniden düzenlendi; aşağıdaki "Hareketler · Traderlar · Adaylar" menüsü ve sanal kopya / kol toplamı gösterimleri bu isteğe göre geçersizdir. Ayrıntı: `docs/pano_sade/KABUL.md`.

# Pano tasarımı v2 (kullanıcı onayı 2026-10-28) — bağlayıcı

Bu belge ve `docs/tasarim/` resimleri panonun **tek** tasarım kaynağıdır. Burada olmayan özellik eklenmez; değişiklik
kullanıcı onayıyla bu belgeye yazılarak yapılır. Örnek: Hyperdash trader sayfası (`tasarim/ornek_hyperdash_*.png`) —
düzen fikri alınır; marka, logo ve kod kopyalanmaz.

## Genel
- Menü: **Hareketler · Traderlar · Adaylar** (+ sağ üstte Ayarlar ikonu). "CT akış", "CT istatistik", "Keşif" adları kalkar.
- Koyu tema, sık tablolar, sayılar hizalı (`tabular-nums`), kâr yeşil / zarar kırmızı, gereksiz kutu yok.
- Sağ üstte tek tazelik yazısı: "veri 01:21 · 4 dk önce · fiyatlar canlı". 90 dk'dan eski veri kırmızı.
- Saatler **TSİ**; "Bugün 14:32 / Dün 22:05 / 25 Eki 09:10" biçimi.
- Telefon (≤ 700 px): tek sütun; geniş tablolarda öncelikli sütunlar kalır (Varlık, Değer, K/Z), gerisi satıra dokununca açılır.
  Yatay sayfa kaydırması yok. Dokunma alanı ≥ 44 px.
- Kayan şerit, otomatik kaydırma **yok** (kullanıcı vazgeçti).

## 1. Hareketler (açılış ekranı) — `tasarim/A_d.png`, `A_m.png`
- Sol (geniş): **Son hareketler**, son 7 gün, gün başlıklı, en yeni üstte. Satır: saat · trader + tarz · coin · LONG/SHORT ·
  açtı/kapattı/büyüttü/küçülttü · fiyat · sağda durum ("hâlâ açık −%2,4" / "kapandı +%11,7").
  Kaynak: izlenen traderların `userFillsByTime` (son 7 gün) → emir bazında hareket; durum.json olayları da birleşir.
- Sağ (dar): **Traderlar** kısa tablosu (ışık noktası, ad, tarz, açık sayısı, son işlem). Satır → trader sayfası.

## 2. Traderlar — `tasarim/B_d.png` (liste) + `tasarim/C_d.png` (sayfa)
Tablo: ışık · ad · tarz · açık pozisyon · son işlem · hesap değeri · durum notu (ışık nedeni). Satır → trader sayfası.

## 3. Trader sayfası (Hyperdash düzeni) — `tasarim/C_d.png`, `C_m.png`, `ornek_hyperdash_ust.png`
Kaynak: tarayıcıdan Hyperliquid (`clearinghouseState` ana + her HIP-3 dex, `spotClearinghouseState`, `portfolio`,
`frontendOpenOrders`, `userFillsByTime`, `userNonFundingLedgerUpdates`), sayfa açılınca kendiliğinden; "Yenile" düğmesi.

**Sol panel**
- Ad (takma ad), kısa adres + kopyala, tarz, "Hyperdash'te aç ↗".
- Işık kutusu: renk + tüm nedenler.
- **Hesap değeri**; altında **Özkaynak**: Perp'ler (ana + HIP-3) · Spot · toplam.
- **Genel bakış:** gerçekleşmemiş K/Z, hesap kaldıracı, marjin kullanımı, tüm zaman K/Z (portfolio), hacim.
- **Analiz:** işlem tarzı, ortalama ve medyan işlem süresi, en uzun kazanç serisi (gün), 30 gün düşüş ve kazanma oranı.
- **Kapı (seçim):** sonuç, katman, gecikmeli kopya getirisi, kârlı ay, elenme nedeni (varsa) — kapı sonucundan.
- **Bizim sanal kopya:** 1.000 $ → bugün, t0, gecikme dk.

**Üst kartlar (4)**
- **Performans:** dönem seçici (7G/30G/90G/Tümü) K/Z $ + kazanma oranı + işlem sayısı.
- **Kaldıraç:** toplam pozisyon değeri / hesap değeri, çubuk; "nominal · özkaynak".
- **Marjin kullanımı:** kullanılan marjin / hesap değeri, çubuk; serbest marjin.
- **Yön eğilimi:** long % · short % çubuğu ve tutarları.

**Grafik:** K/Z eğrisi (portfolio `pnlHistory`), 7G/30G/90G/Tümü; sıfırın altı kırmızı alan.

**Sekmeler**
1. **Pozisyonlar (n)** — `ornek_hyperdash_pozisyon.png` sütunları: Varlık + kaldıraç rozeti (+ISO) · Miktar · Değer · Giriş ·
   Mark · K/Z $ (% = K/Z / marjin) · Likidasyon (yoksa "YOK") · Marjin · Funding (açılıştan beri) · **Açılış (tarih saat)** ·
   kayma rozeti (intraday %0,5 / swing %1,5). Sütun başlığına tıklayınca sıralanır; varsayılan Değer azalan.
2. **Emirler (n)** — açık limit / TP / SL / tetik emirleri: varlık, tür, yön, fiyat, tetik, miktar, yalnız azaltma, zaman.
3. **İşlem geçmişi** — emir bazında birleşmiş işlemler (açılış→kapanış): açılış · coin · yön · giriş · durum (🟢 Açık / ⚪ Kapandı) ·
   kapanış · süre · sonuç %. En yeni üstte, 20'şer.
4. **Gerçekleşenler** — ham dolumlar (zaman, coin, yön/dir, fiyat, miktar, kapanan K/Z, ücret).
5. **Bakiyeler** — spot bakiyeler (coin, miktar, USD değeri).
6. **Transferler** — yatırma / çekme / alt hesap / vault hareketleri (`userNonFundingLedgerUpdates`), son 90 gün.
   Büyük çekme satırı vurgulu (para çekilmiş hesabı görmek için).
7. **Bizim kopya** — sanal kopya eğrisi ve olay sonuçları (durum.json).
8. **Kararlarım** — bu trader için Açtım/Atladım kayıtları ve sanal sonuçları.

Alınmayan Hyperdash sekmeleri: Tahminler, TWAP (TWAP emirleri Emirler'de görünür), RFQ, sosyal/ortaklık kutuları.

## 4. Adaylar
Keşif'in sade hali: tablo (adres, kaynak, tarz, katman, gecikmeli kopya, kârlı ay, düşüş, elenme nedeni) + filtre (tarz, katman).
Satır → aynı trader sayfası (Kapı bölümü dolu, Bizim kopya / Kararlarım gizli).

## Kabul
- Her sayfanın masaüstü (1440 px) ve telefon (390 px) ekran görüntüsü taslakla yan yana PR'da.
- 8bae ve 3f96 için Pozisyonlar ve Emirler sekmesi Hyperdash'le aynı (ekran görüntüsü).
- İşlem birleştirme ve K/Z % için altın örnek (`docs/tasarim_kabul.md`).
- `node --check`; tarayıcı konsolunda hata yok; Hyperliquid erişilemezse sayfa bozulmaz, "canlı veri alınamadı" yazar.
