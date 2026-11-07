# Durum sözleşmesi (motor -> pano)

Motor (backtest besleyici bugün, paper motoru Aşama 4'te) bu dosyaları yazar; pano (`python -m motor.canli.pano`) yalnız okur.
**Pano hesap yapmaz:** gösterilen her sayı dosyada vardır. Kod: `motor/canli/durum.py` (şema doğrulama, atomik yazıcı, okuyucu).
Varsayılan dizin: `durum/` (repoda yok, `.gitignore`). Sürüm: `surum = 1`.

## Genel kurallar
- Zaman: UTC, `YYYY-MM-DDTHH:MM:SSZ`. Para: **metin**, 2 hane (`"10721.40"`, Decimal). Oran: JSON sayısı (`0.072` = %7.2); kayıp/düşüş **pozitif** oran.
- Ölçülmeyen değer `null` (pano `—` gösterir). `NaN`/`Infinity` yasak.
- Atomik yazma: aynı dizinde geçici dosya + `fsync` + `os.replace`. Yazım sırası: `islemler`, `ozsermaye_gecmisi`, `stratejiler`, `saglik`, **`ozet` en son**.
- Her JSON dosyasında zarf: `sema` (`1l3a.durum.<ad>`), `surum`, `zaman` (durumun "şimdi"si; backtestte dönem sonu), `kaynak` (`backtest|paper|canli`).
- Okuma hatası (yok/bozuk/şema uyumsuz) açık hatadır; pano kırmızı uyarı gösterir, değer uydurmaz.

## `ozet.json`
`yazim_zamani`, `donem {bas,bit}|null`, `baslangic_ozsermaye`, `ozsermaye`, `toplam_pnl`, `toplam_getiri`, `gun_pnl`, `gun_getiri`,
`zirve_ozsermaye`, `zirveden_dusus`, `max_dusus`, `notlar[]`,
`risk`: `gunluk_kayip{deger,limit,kullanim,tetiklendi}`, `kaldirac{deger,limit,kullanim,not}`,
`kill_switch{dusus,limit,mesafe,tetiklendi}`, `acik_stop_riski{deger,limit,kullanim}` (kullanım = değer/limit; limitler `SERT_LIMITLER`'den),
`sayaclar{acik_pozisyon,kapanan_islem,reddedilen_giris,kirpilan_giris,gunluk_limit_olayi,kill_olayi}`.

## `stratejiler.json`
`beklenti_penceresi_hafta` (`[4,8]`), `stratejiler[]`: `kimlik, ajan, kol, kol_payi, ozsermaye_katkisi (para), katki_getiri (set başlangıcına oran, toplamsal),
acik_pozisyonlar[] (nesne listesi), son_islem (islemler.jsonl satırı|null), islem_sayisi, kazanma_orani, beklenti`.
`beklenti["4"|"8"]{net_getiri,max_dusus}` her biri `{deger,p05,p25,p50,p75,p95,bant,alarm}`; `bant` = `p05_alti|p05_p25|p25_p50|p50_p75|p75_p95|p95_ustu`;
`alarm` yalnız 8 hafta için `true/false` (net < alarm eşiği veya düşüş > %95 eşiği; `sonuclar/final/beklenti_araliklari.csv`), 4 haftada `null`.
`set.beklenti` aynı biçim (set serisi). Konum **motor tarafında** son 28/56 günden hesaplanır.
Katkı toplamları: Σ `ozsermaye_katkisi` = `ozet.toplam_pnl` (backtestte birebir).

## `islemler.jsonl` (satır başına bir kapanan işlem)
`zaman` (çıkış), `kimlik, sembol, yon (long|short), giris_zamani, giris_fiyati, cikis_zamani, cikis_fiyati, miktar` (fiyat/miktar metin),
`r`, `net_pnl_yerel` (stratejinin kendi hesabındaki net PnL, para), `set_katki_usd` (tek-grafik: set özsermayesine katkı; portföy kolu: `null`), `cikis_nedeni`.
Paper'da tek satır eklemek için `durum.islem_ekle`.

## `saglik.json`
`son_calisma`, `durum (ok|…)`, `bayat_denetimi` (bool; backtestte false), `dosya_esik_dk` (paper/canlıda dosya yaşı eşiği; pano bunu `zaman` ile karşılaştırır),
`veri[] {sembol,tf,son_mum_zamani,bayatlik_dk,esik_dk,bayat}` (eşik = 2 x mum süresi + 10 dk, `durum.bayat_esigi_dk`),
`servis {calisiyor (true|false|null),surum,not}`, `uyarilar[]`.
Pano kırmızı uyarı: `bayat=true`, dosya yaşı > `dosya_esik_dk` (paper/canlı), `durum != ok`, kill/günlük limit tetiklendi, beklenti alarmı.

## `ozsermaye_gecmisi.json`
`noktalar[] {gun, ozsermaye (para)}` (günlük, eğri çizimi için).
