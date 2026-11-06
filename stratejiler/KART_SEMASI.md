# Strateji Kartı Şeması (Aşama 0)

Her PDF'ten çıkarılan her **somut, işlem yapılabilir** strateji bir karttır.
Genel tavsiyeler ("disiplinli olun", "planınıza sadık kalın") kart DEĞİLDİR.
Aynı kitapta aynı stratejinin varyantları varsa tek kart + `varyantlar` alanı kullanılır.

Ham kartlar: `veri/kartlar_ham/<stil>/<pdf_kisa_adi>.json` — bir JSON dizisi (array).

```json
{
  "kart_id": "scalp__ema14-50__waqar",          // <stil>__<kısa-strateji-adı>__<yazar-soyadı>, küçük harf, tire
  "ad": "EMA14/EMA50 Kesişim Scalp",
  "stil": "scalp | daytrade | swing",
  "kaynak": {"pdf": "dosya adı.pdf", "sayfalar": [12, 13, 14]},
  "ozet": "1-3 cümle: ne zaman, neden işlem açılır",
  "kategori": "trend_takip | ortalamaya_donus | kirilim | momentum | formasyon | destek_direnc | diger",
  "piyasa_rejimi": "trend | yatay | volatil | herhangi",
  "orijinal_piyasa": "forex | hisse | vadeli | kripto | emtia | genel",
  "zaman_dilimi": {"islem": "5m", "ust_filtre": "1h veya null"},
  "gostergeler": [{"ad": "EMA", "parametreler": {"periyot": 14}}],
  "long_giris": ["Kesin, ölçülebilir koşul 1", "Koşul 2"],
  "short_giris": ["..."],
  "stop_loss": "Kural (ör. son swing dibinin 1 ATR altı) veya null",
  "kar_al": "Kural (ör. 1.5R, karşı bant, sabit pip) veya null",
  "iz_suren_stop": "Kural veya null",
  "zaman_cikisi": "Kural (ör. 10 mum sonra kapat) veya null",
  "filtreler": ["Seans, hacim, volatilite, haber, trend filtresi vb."],
  "pozisyon_risk": "Kitabın önerdiği risk/boyut kuralı veya null",
  "iddia_edilen_performans": "Kitapta geçen kazanma oranı / R:R / getiri iddiası (aynen) veya null",
  "kodlanabilirlik": {
    "puan": 0,                                    // 0-3, aşağıya bak
    "gerekce": "Neden bu puan"
  },
  "belirsizlikler": ["Kitapta tanımlanmamış ya da yoruma açık kısımlar"],
  "uyumluluk_notu": "1L3A için: ≥5m'ye uyarlanabilir mi? Forex'e özgü mü (pip, seans)? Hacim verisi gerekiyor mu? Kripto/ABD hisse/emtia perpetual'larda çalışır mı?",
  "varyantlar": ["Kitaptaki küçük varyasyonlar"],
  "anahtar_kelimeler": ["ema-kesisim", "rsi", "bollinger", "..."]   // birleştirmede tekrar bulmak için, standart Türkçe-küçük harf
}
```

## Kodlanabilirlik puanı
- **3** — Tamamen mekanik: tüm giriş/çıkış kuralları gösterge/fiyat ile ölçülebilir.
- **2** — Küçük yorum boşlukları var ama makul varsayımla kurala dökülebilir (varsayım `belirsizlikler`'e yazılır).
- **1** — Ağırlıklı yorum (formasyon "görme", "güçlü mum" vb.); ancak kaba bir yaklaşıkla kodlanır.
- **0** — Kodlanamaz / tamamen sezgisel / bilgi yetersiz.

## Kurallar
- Uydurma yok: kitapta yazmayan parametreyi doldurma; `null` bırak veya `belirsizlikler`'e "kitapta yok" yaz.
- Kart alanları Türkçe yazılır; gösterge adları standart (EMA, SMA, RSI, MACD, Bollinger, ATR, Stokastik, VWAP, ADX, Pivot, Fibonacci, Heikin Ashi, Hacim...).
- Çift dilli (Türkçe+İngilizce) PDF'lerde içerik bir kez çıkarılır.
