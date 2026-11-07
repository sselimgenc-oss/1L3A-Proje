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

## Genişletme (Aşama 4, sürüm 1 içinde EKLEMELİ; eski alanlar değişmedi)
Pano bunları yalnız okur; her sayıyı motor yazar. Dosya yoksa (eski motor) pano eski görünümle çalışır (`durum.ek_oku` → `None`).
Ölçülemeyen değer `null` + yanında `*_neden` / `olculmedi_neden` metni (backtest kaynağı). Para metin, oran sayı.

- **Her JSON dosyasında `yazildi_zaman`** (UTC ISO): dosyanın diske yazıldığı an (`yaz_hepsi` damgalar, aynı turda hepsinde aynı).
  Pano tarayıcıda "şimdi − yazildi_zaman" ile dosya bayatlığını gösterir. (`zaman` = durumun "şimdi"si, ayrı kavram.)
- **`ozet.json`**: `baslangictan_pnl` (= `toplam_pnl`), `hafta_pnl` (7 gün dolmadıysa `null` + `hafta_pnl_neden`), `gun_pnl`, `zirve_ozsermaye`
  (zaten vardı), `gunluk_kz[] {gun, pnl, getiri}` (son 60 gün), `dusus_serisi[] {gun, dusus}` (zirveden düşüş, aynı günler).
- **`maruziyet.json`** (`1l3a.durum.maruziyet`): `semboller[] {sembol, net_nominal, brut_nominal, net_oran, brut_oran}` (oran = kasaya),
  `toplam_brut_nominal`, `toplam_net_nominal`, `kaldirac`, `kullanilan_teminat` (= brüt / 3x sert tavan; borsa teminatı değildir, `teminat_notu`),
  `acik_stop_riski {deger (para), oran, limit}`, `pozisyonlar[] {kimlik, sembol, yon, miktar, giris_fiyati, mark_fiyat, giris_zamani, stop, kz, kz_oran,
  nominal, kasaya_orani, stop_riski}` (kz = mark fiyatla anlık K/Z). Aynı pozisyon nesneleri `stratejiler.json` → `acik_pozisyonlar`'da da bulunur.
- **`maliyet.json`**: `toplam {son24s, tum}` ve `stratejiler{kimlik: {son24s, tum}}`; her blok `{ucret, kayma, funding, toplam}` (para; pozitif = maliyet,
  funding ödenen). ücret = taker komisyonu; kayma = dolum fiyatı − referans (açılış / stop seviyesi) farkı x miktar.
- **`reddedilen.json`**: `son24s` ve `tum`: `{"reddedildi:<neden>" | "kirpildi:<neden>": sayı}`, `son[]` (son 20: `zaman, tur, neden, kimlik, sembol`).
  Nedenler: gunluk_kayip_limiti, kill_switch, toplam_risk_tavani, kaldirac_tavani, min_qty, min_notional, gecersiz_stop, portfoy_risk, risk,
  kaldirac_orantili, toplam_risk, kaldirac, zarar_buyutme...
- **`olaylar.jsonl`**: zaman damgalı SON 50 olay `{zaman, tur, mesaj}`; tür: gunluk_limit, kill_switch, veri_bosluk, veri_uyusmazlik, ws_baglandi,
  ws_koptu, ws_yeniden_baglandi, ws_24sa_yenileme, binance_hata, veri_yok, baslangic, yeniden_baslatma.
- **`stratejiler.json` → her strateji**: `performans {islem, kazanma_orani, ort_kar, ort_zarar (negatif), net, pf}`, `ayar`, `sonraki_yenileme`,
  `durum` ("calisiyor" | "veri yok: neden"). `kol_payi` = kolun hesaptaki payı.
- **`icgoruler.json`**: `cumleler[]` kısa Türkçe cümleler (en iyi/en kötü strateji, açıkların kaçı kârda, beklenti alarmına en yakın strateji,
  24 sa maliyet, limit durumu). Sayılar diğer dosyalarla aynı değişkenlerden üretilir.
- **`saglik.json`**: `veri[].bayatlik_dk` = son mum KAPANIŞINDAN beri geçen SEANS dakikası (hisse/emtia için kapalı piyasa sayılmaz,
  `motor/canli/paper_takvim.py`), asla negatif değil; `veri[].seans` (kripto|hisse|emtia). Beklenti alarmları ve ayar yenileme zamanı `uyarilar[]`'a yazılır.
