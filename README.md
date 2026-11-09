# 1L3A — 1 Lider, 3 Ajan Algotrading

Üç strateji ajanı (**scalp**, **day trade**, **swing**) kitaplardan seçilmiş, kurala dökülmüş stratejileri
Binance enstrümanlarında takip eder ve kendi bütçeleriyle işlem yapar. Bir **lider ajan** onları denetler,
işlemleri ve stratejileri sorgular, sonuçlardan ders çıkarır ve değişiklik **önerir** (onay insanda).

> Durum ve alınan kararlar: [DURUM.md](DURUM.md)

## Piyasa ve kapsam
- **Borsa:** Binance perpetual — **az enstrüman, derin uzmanlık:** başlangıçta 3–5 (BTC, ETH, XAU + en fazla 1–2)
- **Zaman dilimi:** en az 5 dakika (1 dk yok)
- **Mod:** önce paper trading (canlı fiyat + kendi simülasyon motorumuz), başarılı olursa küçük bütçeyle canlı
- **Çalışma ortamı:** DigitalOcean droplet; dashboard + Telegram bildirimi

## Yol haritası
Ayrıntı ve bitiş ölçütleri: [DURUM.md](DURUM.md) → "Yol haritası".

| Aşama | İş | Durum |
|---|---|---|
| 0 | PDF'lerden strateji kartı, ailelere birleştirme | ✅ |
| 1 | Altyapı + aday stratejilerin kodu (1A motor, 1B veri, 1C adaylar) | ⏳ |
| 2 | Test ve seçim: BTC/ETH walk-forward → eleme → ajan başına ~3 strateji | |
| 3 | Pano (sg-arge örneği; motorun yazdığını gösterir) | |
| 4 | Paper trading (Frankfurt sunucu, canlı veri, ≥ 8 hafta) | |
| 5 | Lider ajan + öğrenme döngüsü (öneri → test → onay) | |
| 6 | Küçük bütçeyle canlı | |

## Klasörler
```
araclar/            Yardımcı scriptler (PDF→metin, kart doğrulama, kart dizini)
stratejiler/        Kart şeması, strateji aileleri, aday raporu, elenenler, çıkış/risk modülleri
veri/kartlar_ham/   PDF başına ham strateji kartları (JSON)
veri/kart_dizini.csv  Tüm kartların kompakt dizini
```
Kaynak PDF'ler ve metin dökümleri **repoda yok** (boyut + telif). Yerelde `scalp/`, `day trade/`, `swing/`
klasörlerinde durur; `python araclar/pdf_metne.py` ile `veri/pdf_metin/` yeniden üretilir.

## Kurulum
```bash
python -m pip install -r requirements.txt
python araclar/kart_dogrula.py
```

## Güvenlik ilkeleri
- API anahtarları yalnızca sunucudaki `.env` dosyasında; repoya asla girmez.
- Sert risk limitleri (günlük max kayıp, kill switch) kodda sabit; hiçbir ajan aşamaz.
- Martingale / kayıptan sonra pozisyon katlama yasak.
- Canlıda kendi kodunu değiştiren ajan yok; değişiklik önerisi → test → insan onayı.
