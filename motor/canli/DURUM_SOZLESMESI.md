# Durum sözleşmesi (motor -> pano)

Motor (backtest besleyici bugün, paper motoru Aşama 4'te) bu dosyaları yazar; pano (`python -m motor.canli.pano`) yalnız okur.
**Pano hesap yapmaz:** gösterilen her sayı dosyada vardır. Kod: `motor/canli/durum.py` (şema doğrulama, atomik yazıcı, okuyucu).
Varsayılan dizin: `durum/` (repoda yok, `.gitignore`). Sürüm: `surum = 1`.

## Genel kurallar
- **Gün kesimi (kullanıcı kararı 2026-11-08):** günlük kâr/zarar ve dönemsel (hafta/ay) gruplama **Türkiye saatine göre** (`Europe/Istanbul`,
  gün 00:00 TSİ'de biter). Zaman damgaları dosyada UTC kalır; yalnız `gun` alanları, `gunluk_kz`, `dusus_serisi`, `ozsermaye_gecmisi.noktalar`,
  `gunluk_kz_ajan`, hafta (ISO, pazartesi başlar) ve ay gruplaması TSİ gününe göredir. Bir mumun kapanışı tam 00:00 TSİ ise o günün özsermayesine yazılır.
  `ozet.gun_kesimi` kesimi söyler: paper `"Europe/Istanbul"`; backtest `"UTC (araştırma ızgarası)"` (yeniden oynatmanın günlük serisi
  `sonuclar/kilit/set.csv` ile birebir olmak zorunda ve gün içi özsermaye tutulmaz; bu yüzden TSİ'ye çevrilemez). Pano gün etiketini bu alandan yazar.
  Değişmeyenler (bilerek UTC): sert günlük kayıp limiti günü (`motor.gun`, risk kodu), beklenti aralığı pencereleri (28/56 gün; backtestle aynı UTC tabanı).
  `ozet.gun_pnl/gun_getiri` TSİ günüdür; `risk.gunluk_kayip` limit günü UTC'dir.
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
  ws_koptu, ws_yeniden_baglandi, ws_24sa_yenileme, binance_hata, veri_yok, baslangic, yeniden_baslatma
  (kalp atışı sonrası: mesajda "(son kalp atışı -> başlangıç)" aralığı ve süre; aşağıdaki "Pano öncelik 4" bölümü).
- **`stratejiler.json` → her strateji**: `performans {islem, kazanma_orani, ort_kar, ort_zarar (negatif), net, pf}`, `ayar`, `sonraki_yenileme`,
  `durum` ("calisiyor" | "veri yok: neden"). `kol_payi` = kolun hesaptaki payı.
- **`icgoruler.json`**: `cumleler[]` kısa Türkçe cümleler (en iyi/en kötü strateji, açıkların kaçı kârda, beklenti alarmına en yakın strateji,
  24 sa maliyet, limit durumu). Sayılar diğer dosyalarla aynı değişkenlerden üretilir.
- **`saglik.json`**: `veri[].bayatlik_dk` = son mum KAPANIŞINDAN beri geçen SEANS dakikası (hisse/emtia için kapalı piyasa sayılmaz,
  `motor/canli/paper_takvim.py`), asla negatif değil; `veri[].seans` (kripto|hisse|emtia). Beklenti alarmları ve ayar yenileme zamanı `uyarilar[]`'a yazılır.

## Genişletme (motor yazıcı paketi, 2026-11-08; sürüm 1 içinde EKLEMELİ)
Hesap `motor/canli/durum_ek.py` içindedir; paper (`paper_durum.py`) ve backtest (`backtest_durum.py`) aynı fonksiyonları çağırır. Pano yalnız biçimler.
Ölçülemeyen değer `null` + neden. Eşik/alarm yoktur: `MIN_ISLEM=30` ve `MIN_GUN=30` yalnız "yeterli örnekle hesaplandı mı" sınırıdır (geçme ölçütü değil;
geçme ölçütleri `sonuclar/evren/ON_KAYIT.md`'dedir).
- **`ozet.json`**
  - `gun_kesimi` (yukarı bakın).
  - `istatistik {islem_sayisi, gun_sayisi, beklenti_islem_basi (para; yalnız set_katki_usd olan işlemlerden), kazanc_kayip_orani (ort. kazanç R / ort. kayıp R),
    sqn (R'den), sharpe, sortino (günlük getiriden, yıllık √365), kelly_ceyrek (0.25 x max(0, W - (1-W)/B); yalnız bilgi), yesil_gun_orani,
    en_uzun_kazanc_serisi, en_uzun_kayip_serisi (çıkış sırasına göre, net K/Z işareti), ort_tutma_saat, en_iyi_gun/en_kotu_gun {gun,pnl}|null, istatistik_neden}`.
    İşlem < 30: `sqn`, `kelly_ceyrek` null; gün < 30: `sharpe`, `sortino` null; nedenleri `istatistik_neden`'de. R'si olmayan satır varsa ya da R'nin
    standart sapması 0 ise `sqn` null + neden (denetim 2026-11-08); Kelly'de W payı R'li işlemler üzerindendir.
  - `cikis_nedenleri[] {neden, islem, pay, net_pnl}` (+ `cikis_nedenleri_not`): net_pnl = set katkısı toplamı; grubun bir işleminde set katkısı yoksa (backtest portföy kolu) null.
  - `gunluk_kz_ajan[] {gun, ajanlar{ajan:{pnl,getiri}}, toplam{pnl,getiri}}` (son 60 gün): ajan getirisi = pnl / başlangıç özsermaye (toplamsal); toplam.getiri = özsermaye getirisi.
  - `haftalik_kz_ajan[]`, `aylik_kz_ajan[] {donem, bas_gun, bit_gun, gun_sayisi, tamamlandi, ajanlar, toplam}` (son 12 dönem; `tamamlandi=false`: dönem bitmedi).
- **`stratejiler.json`** (üst düzey listeler): `ajanlar[] {ajan, strateji_sayisi, ozsermaye_katkisi, katki_getiri, islem_sayisi, kazanma_orani, pf, acik_pozisyon}`,
  `enstrumanlar[] {sembol, strateji_sayisi, ozsermaye_katkisi, katki_getiri, islem_sayisi, kazanma_orani, acik_pozisyon, [katki_neden]}`,
  `strateji_enstruman[] {strateji (ad), sembol, ozsermaye_katkisi, islem_sayisi, acik_pozisyon, [katki_neden]}`. Paper'da Σ katkı = `toplam_pnl`.
  Backtestte portföy kolunun sembol dağılımı ölçülmez: o hücreler (ve onlara dokunan enstrümanlar) `ozsermaye_katkisi: null` + `katki_neden`; `pf` set katkısı olmayan ajanlarda null.
- **`maruziyet.json`**: `bekleyen_emirler[] {kimlik, sembol, tur (giris|hedef_agirlik|cikis|kucultme), yon, sinyal_zamani (karar mumunun kapanışı), emir, stop, hedef}`;
  backtestte `null` (yeniden oynatma emir kuyruğu tutmaz).
- **`islemler.jsonl`**: paper satırlarında `gun` (çıkışın TSİ günü; takvim detayı bunu kullanır); backtest satırlarında `gun` = çıkışın UTC ızgara günü
  (`ozet.gun_kesimi` ile aynı kesim). Pano `gun`'u olmayan satırı hiçbir güne yerleştirmez (UTC tarihine düşürmez) ve sayısını açıkça yazar.
- Eski durum dosyası (TSİ serisi yok) yüklenirse UTC günü serisi devralınır (en çok 3 saat kayma) ve `ozet.notlar`'a yazılır.

## Genişletme (Dersler ve aylık rapor, 2026-11-08; sürüm 1 içinde EKLEMELİ)
Hesap `motor/canli/dersler.py` ve `motor/canli/aylik_rapor.py` içindedir; paper ve backtest aynı fonksiyonları çağırır. Pano yalnız biçimler
(`DERSLER` ve `RAPOR` sekmeleri). Dosya yoksa (eski motor) pano "veri yok" der. Ölçülemeyen değer `null` + neden.
- **`dersler.json`** (`1l3a.durum.dersler`): `min_islem`, `alfa`, `referans_neden` (referans dosyası yoksa metin), `yontem`, `kaynak_not` (backtestte: referans kilitli
  dönemi de içerir, bağımsız sınav değil), `onayli_esikler[] {ad, deger, onay, aciklama}` (asgari işlem 30, alfa 0.05: kullanıcı onaylı 2026-11-08), `tanimsiz_esikler[]` (boş, uyumluluk için), `sayim {icinde, altinda, ustunde, ornek_az, olculmedi}`,
  `stratejiler[] {kimlik, islem, r_olculen, isabet, ort_r, std_r, pf_r (R tabanlı), beklenti {n, isabet, ort_r, std_r, pf_r}|null,
  isabet_testi {test, p_deger, yon, anlamli}|null, ort_r_testi {test, t, df, p_deger, yon, anlamli}|null, test_neden,
  durum ("icinde"|"altinda"|"ustunde"|"ornek_az"|null), durum_etiket, durum_neden, beklenti_penceresi {hafta, net_bant, net_getiri, dusus_bant, max_dusus, alarm}|null,
  aciklamalar[] (kurallı metin şablonları), cikis_nedeni_sapmalari[] {neden, islem, pay, beklenen_pay, p_deger|null, anlamli, gozlenmedi, ust_sinir|null, test_neden|null}}`.
  Backtest payı 0 olan nedende binom testi YAPILMAZ (H0 pay=0 iken tek gözlem p=0 verirdi): `p_deger` null, `gozlenmedi` true, `ust_sinir` ≈ 3/n_ref
  (üçler kuralı, %95), `test_neden` "backtestte gözlenmedi ..."; payı 1 olan (tek neden) için de test yok (`test_neden` yazılı). Denetim O16, 2026-11-08.
  Referans: `sonuclar/final/beklenti_islem_referansi.csv` (üretici `python -m motor.canli.dersler_referans`; `beklenti_araliklari.csv` ile aynı örneklem-dışı işlemler,
  `veri_sonu` çıkışları hariç; araliklar csv'si ortalama R/PF taşımadığı için ayrı dosya). İsabet: kesin iki yönlü binom; ort. R: Welch t; PF test edilmez;
  çıkış nedeni payı: neden başına binom. İşlem < `min_islem` (30) ise testler null + `test_neden`, durum `ornek_az`. Karar: ort. R anlamlıysa onun yönü, değilse isabet,
  değilse "icinde"; 8 hf beklenti alarmı varsa (n yeterliyse) "altinda". **`min_islem` (30) ve `alfa` (0.05) kullanıcı onaylıdır (2026-11-08); "altinda" kabulü bozmaz ama strateji canlıya geçmez, "ornek_az" da canlıya uygun sayılmaz (`aylik_rapor.kabul_listesi.stratejiler`).**
- **`aylik_rapor.json`** (`1l3a.durum.aylik_rapor`): `gun_kesimi`, `aylar[] {ay (TSİ, YYYY-MM), bas_gun, bit_gun, gun_sayisi, tamamlandi, getiri, pnl (ozet.aylik_kz_ajan ile aynı sayı),
  max_dusus (ay içi, günlük getirilerden), yesil_gun_orani, en_iyi_gun, en_kotu_gun, islem_sayisi, kazanan, kazanma_orani, ort_r, en_iyi_strateji/en_kotu_strateji {kimlik, katki},
  ajanlar, limit_olaylari {gunluk_kayip, kill_switch}|null, notlar[]}` (son 12 ay; işlem ayı çıkışın TSİ günündendir), `aylar_not`, `kabul_listesi`, `kabul_listesi_neden`.
  `kabul_listesi` (yalnız paper/canlı; backtestte null + neden) `{kalemler[] {id, ad, olcut, kaynak, durum ("gecti"|"kaldi"|"bekliyor"|"tanimsiz"|"bilgi"), deger, neden}, genel_durum ("kaldi"|"bekliyor"|"tamam"),
  sayim, genel_not, en_erken_degerlendirme (YYYY-MM-DD), kesinti {saat|null, alt_sinir_saat, olculen_olay, olculemeyen_olay, neden|null, limit_saat (24), uzama_saat},
  stratejiler[] {kimlik, dersler_durumu, canliya_uygun (bool), neden}, tanimsiz[] {ad, soru}}`. Kullanıcı kararları 2026-11-08 (DURUM.md lider günlüğü):
  `sure` ≥ 56 gün + 24 saati aşan kesinti kadar (kesinti reddetmez, `en_erken_degerlendirme` kayar; 2027-01-02 kesinti yokken); `set_beklenti` (set 8 hf net getiri/düşüş alarmı yok);
  `sert_limit` (ihlal = motorun KAYITLI olayları: kill switch ya da dolum anı tavan aşımı olayı `dolum_kaldirac_asimi` / `dolum_stop_riski_asimi` [limit_olaylari];
  red/kırpma limitin çalıştığını gösterir, nedende bilgi; günlük kayıp limitinin TETİKLENMESİ ihlal değil — denetim O14 2026-11-08);
  `sert_limit_anlik` (durum "bilgi", kabulü bozmaz: anlık/MTM kaldıraç veya açık stop riski limit üstündeyse `deger` "uyarı: ..."; motor limiti dolumda uygular); `asgari_islem` (set toplamında ≥ 30 kapanan işlem; geçti/kaldı,
  birikimli olduğundan süre dolmadan "bekliyor"); bilgi kalemleri `kesinti_suresi`, `gunluk_limit_olayi`, `strateji_alarmlari`, `dersler_ozeti`.
  `stratejiler[].canliya_uygun`: Dersler "icinde"/"ustunde" true; "altinda" false (neden: beklentinin altında; kabulü bozmaz); "ornek_az" false (ayrı neden: örnek az); ölçülmedi false.
  KESİNTİ ÖLÇÜMÜ (`aylik_rapor.kesinti_olc`): `paper_state.json` olay kayıtlarından (en çok 200 olay): `veri_bosluk` ve `yeniden_baslatma` mesajındaki "(A -> B)" aralığı
  (`veri_bosluk`'ta A/B mum AÇILIŞLARIDIR: "N mum eksik" ile kesinti [A + mum süresi, B) = N mum süresi sayılır; denetim O18)
  (yeniden başlatmada A = son kalp atışı, B = başlangıç; kalp atışından önceki eski olaylarda aralık yoktur) ve `ws_koptu` "WS N sn mesaj vermedi" süresi;
  çakışanlar birleştirilir. Süresi kayıtta olmayan kesinti olayı (aralıksız `yeniden_baslatma`, `binance_hata`, aralıksız `veri_bosluk`, "WS koptu") ya da dolu olay kaydı varsa toplam ÖLÇÜLEMEZ:
  `saat` null + `neden`, `alt_sinir_saat` yalnız ölçülen kısım (uzama yalnız bu kesin kısımdan hesaplanır). `veri_yok` kesinti sayılmaz. Açık kalan tek soru: `tanimsiz` = `strateji_alarmi_kabulu`.
  Eski pano eşikleri (%10 DD, PSR>%95, 30 işlem/60 gün) KULLANILMAZ. "tamam" tanımlı kalemlerin hepsi geçti demektir; kabul kararı kullanıcınındır.

## Genişletme (Pano öncelik 4: veri güveni, bütünlük, sürüm izi, kalp atışı; 2026-11-08; sürüm 1 içinde EKLEMELİ)
Hesap `motor/canli/guven.py`, `giris_izi.py`, `kalp_atisi.py` içindedir; paper ve backtest aynı fonksiyonları çağırır. Pano yalnız biçimler (SAĞLIK sekmesi: "Veri güveni",
"Backtest bütünlüğü", kalp atışı kutuları; İŞLEMLER sekmesi: "İşlem izi"). Dosya yoksa (eski motor) pano "veri yok" der. Ölçülemeyen değer `null` + neden.
- **`veri_guveni.json`** (`1l3a.durum.veri_guveni`): `pencere_gun` (30), `semboller[] {sembol, tf, seans, son_mum_acilis, son_mum_kapanis, bayatlik_dk, esik_dk, bayat (saglik.json ile AYNI sayı; seans takvimi),
  pencere_mum, eksik_mum, bosluk_sayisi, en_uzun_bosluk_mum, eksik_neden, kaynak (binance_perp|dukascopy|yahoo), kaynak_ayrinti, spot_vekil {bas,bit,perp_baslangic}|null, spot_vekil_neden}`,
  `ozet {seri_sayisi, bayat_sayisi, eksik_mum_toplam, bosluk_toplam, olculmeyen_seri, kaynaklar}`, `not`. Eksik mum = son 30 günde KAPANMIŞ mumlar arasında piyasa AÇIKKEN gelmeyen mum yuvası
  (kripto duvar saati; hisse/emtia yalnız seans içi; son mumdan şimdiye süre eksik değil bayatlıktır). Backtest (mum indeksi yok) ve indeksi verilmeyen seri: `eksik_mum: null` + `eksik_neden`.
  Kaynak: canlı paper'da hepsi `binance_perp` (TradFi: Binance TradFi perpetual, geçmiş tohum Dukascopy `kaynak_ayrinti`'nda); tekrar/backtest'te yerel arşiv (DK_ Dukascopy, BIST_ Yahoo).
  `spot_vekil`: `veri/mumlar/<sembol>/kaynak.json` varsa perp öncesi spot vekil aralığı (dosya o makinede yoksa `spot_vekil_neden`).
- **`butunluk.json`** (`1l3a.durum.butunluk`): `kod_surumu {commit|null, kisa, kirli (bool|null), kirli_dosyalar[], kaynak (git|ortam|null), neden}` (git yoksa `commit: null` + neden; `L3A_GIT_COMMIT` ortam değişkeni yedek;
  kirli = motor/stratejiler/araclar/sonuclar/{final,kilit,evren} altında commit edilmemiş değişiklik), `dosyalar[] {id, ad, yol, sha256, kayitli_sha256, kayit_kaynagi, eslesti (bool|null), durum (eslesti|uyusmuyor|kayit_yok|dosya_yok), neden}`
  (final_set.json, beklenti_araliklari.csv, beklenti_islem_referansi.csv, guncel_ayarlar.csv, maliyet_tablosu.csv [kendi `.sha256` mührüyle], kilit set.csv, kilit sonuc.csv), `sanal[]` aynı biçim
  (kod sabitleri: `maliyet_modeli` = paper PortfoyAyarlari maliyet/risk alanları [backtestte `olculmedi` + neden], `sert_limitler` = SERT_LIMITLER değerleri), `genel_durum` (eslesti|uyusmuyor|eksik),
  `sayim`, `kayit_dosyasi`, `kayit_zamani`, `not`. Kayıtlı değer `sonuclar/final/butunluk_kayit.json` (`python -m motor.canli.guven --kaydet`, KULLANICI ONAYIYLA; motor otomatik yazmaz).
  Ayar yenilemesi `guncel_ayarlar.csv`'yi bilerek değiştirir: "uyusmuyor" görünür, yeni özet onayla kaydedilir. Pano uyarısı: `uyusmuyor`.
- **`islemler.jsonl`** (paper; backtestte yalnız `ayar_surumu`): her satırda isteğe bağlı `ayar_surumu {hash (sha256("strateji_adı|ayar_etiketi")[:12]), set_dosyasi, ayar, strateji}` ve
  `giris_gerekcesi {sablon "genel/1", kaynak "genel_sablon", strateji, kimlik, sembol, tf, yon, sinyal_mumu_acilis, sinyal_mumu_kapanis, sinyal_kapanis_fiyati, stop, stop_mesafe_oran, hedef,
  hedef_mesafe_oran, hedef_agirlik, gostergeler {sinyal tablosundaki ek sayısal sütunlar}, cikis_kurallari, metin}`. Gerekçe SİNYAL ANINDA (karar mumunun kapanışı, mumlar <= t) üretilir, pozisyon
  açılırken pozisyona bağlanır (`paper_state.json` motor `karar_meta`/`giris_meta`; yeniden başlatmada korunur), kapanışta işlem satırına yazılır. Stratejiler koşul metni üretmez: genel şablon
  (strateji + yön + sinyal mumu + kapanış + stop/hedef mesafesi + varsa göstergeler). Eski kayıtlarda ve backtestte `giris_gerekcesi` `null`; alanlar `dogrula_islem` zorunlu listesinde DEĞİLDİR.
- **`saglik.json` → `kalp_atisi`** (paper/canlı; tekrar modunda yok): `{son, baslangic, aralik_sn (60), onceki_kalp_atisi, son_kesinti_sn (null: ilk çalışma veya ölçülemedi), son_kesinti_neden}`.
  Kalp atışı `durum/kalp_atisi.json` (`{sema, surum, zaman, baslangic, onceki_kalp_atisi, durdu, aralik_sn}`; en çok 60 sn'de bir, her başarılı turda güncellenir, düzgün kapanışta `durdu: true`) ve
  `paper_state.json` içinde `kalp_atisi` alanı olarak tutulur. Yeniden başlatmada önceki kalp atışı (iki kaynağın yenisi) → başlangıç aralığı `yeniden_baslatma` olayına
  "(A -> B) = N sn" biçiminde yazılır; `kesinti_olc` bunu okur. Kalp atışı yoksa (eski durum dosyası) olay "ölçülemedi" der. Çökmede ölçü en çok 60 sn + tur süresi eksik kalır (alt sınır).
  Uyumluluk: eski `paper_state.json` (kalp_atisi/karar_meta/giris_meta yok) olduğu gibi yüklenir.

## Genişletme (Pano öncelik 5: koni, kıyas, korelasyon, yoğunlaşma; 2026-11-08; sürüm 1 içinde EKLEMELİ)
Hesap `motor/canli/koni.py`, `kiyas.py`, `korelasyon.py`, `yogunlasma.py` içindedir; paper ve backtest aynı fonksiyonları çağırır. Pano yalnız çizer/biçimler (ÖZET: koni + kıyas grafiği; RİSK: korelasyon matrisi + yoğunlaşma tabloları). Dosya yoksa pano "veri yok" der. Ölçülemeyen değer `null` + neden.
- **`koni.json`** (`1l3a.durum.koni`): `baz_gun` (gün 0 = ilk günden önceki gün), `ufuk_gun` (112), `blok_gun` 14, `n_ornek` 10000, `tohum` 42, `yuzdelikler`, `isaretler[] {gun_no, etiket}` (56 = 8 hafta),
  `koni[] {gun_no, gun, p05, p25, p50, p75, p95}` (birikimli net getiri, gün 0 hep 0) | null + `koni_neden`, `gerceklesen[] {gun_no, gun, getiri}` (özsermaye/başlangıç − 1),
  `konum {gun_no, gun, getiri, p05..p95, bant, yuzdelik_sira (simüle yolların bu getiriden kötü payı, orta sıra), not}` (koni ufkundaki son gerçekleşen gün) | null + `konum_neden`,
  `havuz {dosya, sha256, kayitli_sha256, dogrulama (eslesti|uyusmuyor|kayit_yok), tum_gun_sayisi, gun_sayisi, bas, bit, baz_gun_sonrasi_cikarilan}`, `yontem`, `sabitleme`, `notlar[]`.
  KAYNAK/YÖNTEM: final setin örneklem-dışı günlük getirisi (WF OOS + kilitli dönem, kollar 50/50; `beklenti_araliklari.csv` set satırlarıyla AYNI seri) `sonuclar/final/beklenti_koni_havuzu.csv`
  (üretici `python -m motor.canli.koni --havuz-yaz`; parquet'ler sunucuda yok); `beklenti.py` ile aynı hareketli blok bootstrap (14 gün, 10 000 yol, tohum 42), gün gün birikimli yüzdelikler; ad hoc genişletme yok.
  SABİTLEME/LOOKAHEAD: yalnız `baz_gun` DAHİL öncesi havuz günleri kullanılır, gerçekleşen günler havuza girmez, koni gerçekleşenle değişmez; havuz dosyası kodda sabit sha256'ya (`HAVUZ_SHA256`) bağlıdır, uyuşmazsa koni null + neden.
  Backtest: baz gün dönemden önceki gündür, dönemin içindeki günler havuzdan çıkarılır; paper: havuz 2026-10-30'da biter.
- **`kiyas.json`**: `baz_gun`, `gun_kesimi`, `gunler[]` (baz dahil), `seriler[] {kimlik (paper|btc|spx|mevduat), etiket, sembol, kaynak, noktalar[] {gun, getiri|null}, son_getiri, neden}`, `taban_notu`. Hepsi baz günün sonuna normalize birikimli getiri.
  btc = BTCUSDT, spx = DK_SPX (yerel mum arşivi, 1h yoksa 5m); gün değeri = gün sonu kesimine (bitmemiş gün için `simdi`) kadar KAPANMIŞ son mum; son mum kesimden > 5 gün eskiyse o gün null + neden (arşiv güncel değilse seri boş kalır).
  mevduat: `yillik_oran`, `kullanici_girmeli`; oran `stratejiler/kiyas_ayar.json` → `mevduat_yillik_oran` (kesir, bileşik; **0.30 = yıllık %30, kullanıcı kararı 2026-11-08**); null iken seri çizilmez (`noktalar: []`, `kullanici_girmeli: true`).
- **`korelasyon.json`**: `kimlikler[]`, `matris[][]` (Pearson, günlük katkı getirisi: net K/Z ÷ önceki gün özsermaye; işlemsiz gün 0) | null + `neden`, `ortak_gun[][]`, `guven_araligi[][]` (Fisher z %95), `hucre_neden[] {a,b,neden}`,
  `min_ortak_gun` (30; çift başına ortak gün < 30 → hücre null; hiçbir çift 30'a ulaşmazsa tüm matris null), sabit seri → null + neden, `ozet {cift_sayisi, olculemeyen_cift, ort_mutlak, en_yuksek, en_dusuk}`, `esik: null` (korelasyon eşiği tanımlı değil, uyarı yok).
- **`yogunlasma.json`**: `ozsermaye`, `toplam_brut_nominal`, `toplam_stop_riski`, `semboller[]` ve `siniflar[]` (sınıf = `paper_takvim.tur`: kripto|hisse|emtia) her biri `{brut_nominal, net_nominal, brut_oran (kasaya), net_oran, brut_pay (toplam brüt içinde), stop_riski, stop_riski_oran, stop_riski_pay, strateji_sayisi, stratejiler[]}`,
  `en_buyuk_sembol`, `en_buyuk_sinif`, `hhi_brut`, `etkin_sembol_sayisi`, `esikler {sembol_pay: 0.40, sinif_pay: null, neden}`, `uyarilar[]` = `{tur: "sembol_risk_payi", sembol, deger, esik, mesaj}` her sembol için `stop_riski_pay > 0.40` (kesin >; yalnız toplam açık stop riski > 0 iken). Kullanıcı kararı 2026-11-08; **yalnız uyarı**, işlem engellemez, SERT_LIMITLER'e (toplam açık stop riski ≤ %5, kaldıraç ≤ 3x) dokunmaz. Sınıf eşiği kararlaşmadı (null). Pano uyarıları yoğunlaşma kartında gösterir.
  Backtest: `semboller: null` + `olculmedi_neden` (yeniden oynatma pozisyon tutmaz).

## Genişletme (Pano öncelik 6: karne, koç, işlem açıklama çekmecesi; 2026-11-08; sürüm 1 içinde EKLEMELİ)
Hesap `motor/canli/karne.py` ve `koc.py` içindedir; paper ve backtest aynı fonksiyonları çağırır. Pano yalnız çizer/biçimler (DERSLER sekmesi: "Karne (radar)" ve "Koç: kurallı tespitler"; İŞLEMLER sekmesi: satıra tıklayınca açılan çekmece).
Dosya yoksa (eski motor) pano "veri yok" der. Ölçülemeyen değer `null` + neden. **Karne ve koç YALNIZ BİLGİDİR**: strateji seçme/eleme ölçütü değildir, geriye dönük strateji/ayar seçimi önermez.
- **`karne.json`** (`1l3a.durum.karne`): `puan_olcegi`, `genel_puan: null` + `genel_puan_neden` (bilerek tek sayı yok: eksik eksenler ortalamayı şişirir, Goodhart), `min_islem` (30), `alfa` (0.05),
  `eksen_tanimlari[] {id, ad, formul, esik, esik_kaynagi, min_ornek}` (6 eksen, sıra `eksen_sirasi`), `set` ve `stratejiler[]` her biri `{kimlik ("SET" | strateji), tur, ajan, islem, olculen_eksen,
  eksenler[] {id, ad, puan (0-100|null), deger, ozet (kurallı metin), esik_durumu ("gecti"|"kaldi"|"esik_yok"|null), neden (puan null ise zorunlu), ayrinti {...}, [kontroller[] {id, ad, gecti (bool|null), deger, kaynak, neden}]}}`.
  Eşikler eski panonunkiler (%10 düşüş, PSR>%95) DEĞİL; projenin kendi kurallarından (kullanıcı kararı 2026-11-08):
  | eksen | formül | eşik ve kaynağı | asgari örnek |
  |---|---|---|---|
  | `getiri` | 8 hf (yoksa 4 hf) net getirinin backtest beklenti aralığındaki yüzdelik konumu; %5/%25/%50/%75/%95 arası doğrusal, %5 altı bir segmentte 0'a, %95 üstü 100'e iner | 8 hf net getiri alarm eşiği (= %5 yüzdeliği): `beklenti_araliklari.csv`, `sonuclar/final/OZET.md`; 4 hf'de eşik yok (`esik_yok`) | beklenti penceresi dolu (28/56 gün) |
  | `risk` | aynı pencerenin en büyük düşüşünün yüzdeliği TERSİNE: puan = 100 − yüzdelik | 8 hf düşüş alarm eşiği (= %95 yüzdeliği): aynı dosyalar | aynı |
  | `kalite` | PF(R) = Σ(R>0)/−Σ(R<0); puan = clamp(250·(PF−1), 0, 100) (PF 1.0→0, 1.2→50, 1.4→100) | PF ≥ 1.2: `sonuclar/evren/ON_KAYIT.md` Geçme ölçütleri 1 | 30 işlem + en az bir zarar |
  | `isabet` | z = (gözlenen isabet − backtest isabeti)/√(p(1−p)/n); puan = clamp(50 + 50·z/1.96, 0, 100); strateji için Dersler'in kesin binom p'si `ayrinti`'de; set: işlem karışımına göre havuzlanmış beklenti | z > −1.96 (Dersler alfa 0.05, kullanıcı onaylı); `beklenti_islem_referansi.csv` | 30 işlem (R ölçülen) |
  | `uyum` | Dersler'in Welch t'si (set: havuzlanmış beklenti, backtest std'siyle z); puan = clamp(100·(1 − max(0, −t)/1.96), 0, 100) — tek yönlü ceza, beklentinin ÜSTÜ cezalanmaz | t > −1.96 (aynı) | 30 işlem |
  | `saglik` | geçen/ölçülen kontrol × 100. Strateji: çalışıyor mu, veri serisi bayat mı. Set: motor durumu ok, bayat veri yok, bütünlük (sha256 ↔ kayıt) eşleşiyor, toplam kesinti ≤ 24 saat, sert limit ihlali yok | tüm ölçülen kontroller geçer: `saglik.json` bayatlık eşiği, `butunluk.json`, paper kabul kararları (kesinti 24 saat, sert limit; 2026-11-08) | ≥ 1 ölçülen kontrol; backtestte ölçülmez (null + neden) |
  Ölçülemeyen kontrol (ör. kayıtsız bütünlük, ölçülemeyen kesinti) ölçülen sayıya girmez ve nedeni `kontroller[].neden`'dedir. Örnek az ise eksen `puan: null` + `neden` (eksik eksen hiçbir ortalamaya girmez). Backtest kaynağında `kaynak_not` (referans kilitli dönemi içerir).
- **`koc.json`** (`1l3a.durum.koc`): `min_islem` (30), `alfa` (0.05), `min_kova` (5), `min_grup_tutma` (10), `kurallar[] {id, ad, referans ("backtest"|"yok"), kaynak}`, `bulgular[] {id, kural, kapsam ("SET"|strateji), seviye
  ("beklenti_disi"|"incele"|"izle"), seviye_etiket, baslik, metin (kurallı şablon; LLM yok), dayanak {sayılar}, istatistik {test, p_ham|null, test_sayisi, p_duzeltilmis|null, duzeltme, anlamli_ham, anlamli_duzeltilmis, alfa, neden?}, referans, oneri (sabit şablon)}`,
  (`p_ham`/`p_duzeltilmis` null yalnız backtestte HİÇ gözlenmeyen çıkış nedeni/stop ailesi bulgusunda: test yapılmaz, seviye en fazla `izle`, `istatistik.neden` yazılı),
  `atlanan[] {kural, kapsam, neden}` (örnek az: kural ÇALIŞMAZ ve burada nedeniyle yazılır), `sayim`, `yontem`, `uyari`. Sıra: seviye, sonra düzeltilmiş p. Yalnız KAPANMIŞ işlemler (lookahead yok); zaman dilimi TSİ.
  **Koç ASLA** risk artırma, pozisyon büyütme, kayıp sonrası ekleme, Kelly ile büyütme önermez (martingale/DCA yasak); öneri metinleri yalnız `ONERI` şablonlarıdır (incele / izle / beklenti dışı) ve "değişiklik yalnız walk-forward + kullanıcı onayıyla" der.
  Seviye: referans (backtest karşılaştırma tabanı) VAR ise düzeltilmiş p < alfa → `beklenti_disi`, yalnız ham p < alfa → `incele`; referans YOK ise düzeltilmiş p < alfa → `incele`, yalnız ham → `izle` (referanssız kural `beklenti_disi` üretemez).
  Çoklu test: aynı kural ailesi ve kapsam içindeki test sayısı kadar Bonferroni (kapsamlar/kurallar arası düzeltme yok; `test_sayisi` her bulguda). Kurallar (kazanmayan = R ≤ 0):
  `stop_sikligi` ("stop" içeren çıkış nedenlerinin toplam payı backtest payından anlamlı yüksek; kesin binom; strateji), `cikis_nedeni` (diğer nedenlerin payı backtestten saptı; her iki yön; binom + Bonferroni; backtestte hiç görülmeyen neden test edilmez, en fazla izle),
  `kayip_serisi` (en uzun ardışık kazanmayan seri, backtest isabetiyle şansla görülme olasılığı; kesin dinamik program; strateji ve set), `tutma_suresi` (kaybedenler kazananlardan anlamlı uzun tutulmuş; Mann-Whitney; strateji; referans yok),
  `kayip_yogunlugu` (giriş saati TSİ 4 saatlik blok / giriş günü TSİ / sembol kovasında kazanmayan payı kalandan anlamlı yüksek ve kovanın toplam R'si negatif; Fisher; set ve ≥ 30 işlemli strateji; referans yok),
  `beklenti_alti` (Dersler "altında" strateji; set 8 hf beklenti alarmı; Dersler'in onaylı kuralı, ek düzeltme yok). `min_kova`/`min_grup_tutma` koça özgü örnek sınırlarıdır (kullanıcıya sorulur).
- **`islemler.jsonl`** (paper; backtestte alanlar `null`): `mfe_fiyat`, `mae_fiyat` (metin; işlem boyunca en iyi/en kötü fiyat), `mfe_r` (≥ 0), `mae_r` (≤ 0) (R birimi = ortalama giriş − ilk stop mesafesi = `risk_tutar/tepe_miktar`), `mfe_mae_neden` (null değilse alanlar neden null).
  Motor (`paper_motor.uc`) pozisyon AÇIKKEN tamamen kapanmış mumların yüksek/düşük uçlarını ve gerçekleşen dolum fiyatlarını izler; ÇIKIŞ mumunun uçları SAYILMAZ (mum içi sıra bilinmez): değerler gerçek MFE/MAE'nin ALT SINIRIDIR, lookahead yoktur.
  İzleme özellikten önce açılmış pozisyonlarda sonradan başlar (`tam: false`) → null + neden. Muhasebeyi etkilemez; durum dosyasında `uc` alanı (eski dosyada yok: olduğu gibi yüklenir). Alanlar `dogrula_islem` zorunlu listesinde DEĞİLDİR.
- **Çekmece** (İŞLEMLER): satıra tıklayınca açılır; giriş gerekçesi (`giris_gerekcesi.metin` + göstergeler), ayar sürümü (`ayar_surumu`), giriş/çıkış zaman-fiyat-miktar, R, net K/Z, set katkısı, çıkış nedeni (sabit sözlük açıklaması) ve MFE/MAE; alan yoksa "yok" + neden.
  JS yoksa aynı içerik açılır-kapanır liste olarak görünür. Pano hiçbir sayı hesaplamaz.

## Genişletme (TradFi funding ayrımı ve maliyet dahil risk, kullanıcı kararı 2026-11-09; sürüm 1 içinde EKLEMELİ)
- **TradFi funding** (Binance `TRADIFI_PERPETUAL`; projede `DK_` önekli semboller, `paper_veri.tradfi_mi`): paper funding'i ÖDEMEYE devam eder (özsermaye, `net_pnl_yerel`, `r`
  ve `maliyet.funding` DAHİL) ama ayrıca yazılır. Araştırmada (Dukascopy) TradFi funding yoktur; bu yüzden **backtest beklentisiyle kıyaslar TradFi funding HARİÇ** yapılır.
  Kripto perp funding araştırmada da vardır: kıyasa DAHİL kalır.
  - `islemler.jsonl` (paper): `funding_tradfi` (para; o işlemde ödenen TradFi funding, negatif = tahsil; kripto `0.00`), `r_kiyas` (TradFi funding HARİÇ R =
    (net + funding_tradfi) / risk tutarı; kripto işlemde = `r`). Motor işlem kaydında yazılır (`PaperMotor.tradfi_alanlari`); bu alanlardan önce kapanmış kayıtta aynı
    formülle türetilir. Backtest kaynağında alan yoktur (kıyas R'si = `r`; `durum_ek.r_kiyas`). Alanlar `dogrula_islem` zorunlu listesinde değildir.
  - `ozet.json` ve `maliyet.json` → `funding_tradfi {toplam, kapanan, acik, son24s, belirsiz_adet, belirsiz_tutar, not}` (para). `toplam` = kapanan işlemlerin
    `funding_tradfi`'si + açık TradFi pozisyonlarının birikmiş funding'i. `maliyet.toplam/stratejiler.funding` bunu ZATEN içerir (ayrıca toplanmaz).
    `belirsiz_*`: sembolü yazılmamış eski `maliyet_log` satırı, evreni karışık (TradFi + kripto) bir stratejiye aitse sınıflanamaz ve kıyasa DAHİL kalır (açıkça yazılır).
  - Kıyas kullanan yerler: `stratejiler.json` `beklenti` (tek-grafik: `r_kiyas` ile günlük R serisi; portföy: kümülatif katkıya o güne kadarki TradFi funding geri eklenir),
    `set.beklenti` (UTC gün sonu özsermayesine o güne kadarki kümülatif TradFi funding geri eklenir), `dersler.json` (isabet/ort. R), `karne.json` (kalite PF), `koc.json`
    (kazanmayan = `r_kiyas` ≤ 0), iç görülerdeki "beklenti alarmına en yakın". Betimleyici istatistikler (`ozet.istatistik`, aylık rapor, kazanma oranı) gerçek `r`/net ile kalır.
  - `maliyet_log` satırlarına `sembol` eklendi (durum dosyasında; eski satırlarda yok). Pano maliyet kartında TradFi funding ayrı satırdır (pano hesap yapmaz).
  - Paper başlarken exchangeInfo `contractType` ile `tradfi_mi` çelişirse `tradfi_sinif` olayı yazılır.
- **İşlem başı risk maliyet dahil** (`motor/risk/limitler.py`): sinyal kollarında miktar = özsermaye·%1 / (|giriş−stop| + max(giriş, stop)·(stop_kayma + 2·taker)).
  `r` tanımı değişmedi (fiyat riski cinsinden net); tam stop kaybında r ≈ −(1 + maliyet payı/fiyat riski), hesap kaybı ≈ −%1. Beklenti aralıkları (`beklenti_araliklari.csv`)
  eski (yalnız fiyat riski) boyutla üretildiyse set düzeyi beklenti yeniden üretilmelidir (tek-grafik strateji kıyasları R tabanlıdır, etkilenmez).

## Genişletme (Paper v2 seti: 10 strateji, her biri kendi kasasında; 2026-11-10; sürüm 1 içinde EKLEMELİ)
Kod: `motor/canli/paper_v2.py`; set tanımı `stratejiler/paper_v2_seti.json`. Üst düzey `durum/` dosyaları 10 kasanın TOPLAMIDIR (toplamda sert limit
uygulanmaz; her kasanın kendi motoru limitleri ayrı uygular). Eski alanlar değişmedi; eski motor/dosyalarda yeni alanlar yoktur (pano yokluğu tolere eder).
- **`stratejiler.json` → her strateji**: `etiket` ("dogrulandi" = resmi v2 holdout kapısını geçti; "iyi_gorundu" = sonuç sonrası keşif, KANIT DEĞİL; "kapanis_aday" (2026-11-14, EKLEMELİ) = kapanış turu paper adayı — ileri dönem sınavı gerekli, yeterli değil; eski sette `null`),
  `hesap {baslangic, ozsermaye (para), getiri, zirveden_dusus, kill, gunluk_blok, risk_yuzde (işlem başı %), kaldirac, acik_stop_riski}` (stratejinin kendi sanal kasası),
  `kol`: "tek_evren" (aynı strateji evrendeki tüm sembollerde, TEK kasada) | "portfoy"; `kol_payi` v2'de grup payı (pf için s = 0.5, tek_evren için 1).
- **`durum/hesaplar/<klasör>/`** (klasör = kimlik; dosya sistemi için `:`/`#` gibi karakterler `_` olur: `HAM:X005:664#v1` -> `HAM_X005_664_v1`): her kasanın tam dosya seti (ozet, stratejiler, islemler, saglik, ... aynı şema; `ozet.baslangic_ozsermaye` 10000). Yeni satır
  işlendiyse en çok 10 dakikada bir yenilenir.
- **`paper_state.json`**: `{"surum": 2, "set": "paper_v2", "set_imza", "hesaplar": {kimlik: <eski tek-hesap kaydı>}, ...}`; eski 7'li set kaydı (`surum` 1) v2'ye YÜKLENMEZ (açık hata).
- Beklenti aralığı/Dersler referansı yeni stratejiler için YOKTUR (`beklenti` boş, uydurma yok); Dersler/Karne bu alanlar için "ölçülmedi" der.
- Evrenden düşen semboller (Binance TradFi karşılığı yok: `DK_JNJ`, `DK_MA`) SEMBOLE göre TEK satırda görünür: `ozet.notlar`, `saglik.bilgiler` (pano: bilgi düzeyi, sarı uyarı değil; `BİLGİ: ` önekli satırlar `uyarilar`dan buraya ayrılır) ve `olaylar` (`evren_bilgi`, Telegram'a gitmez). Ayrıntı: `saglik.evren_disi` = `[{sembol, neden, beklenen, stratejiler[]}]` (SAĞLIK sekmesi tablosu). Beklenmeyen düşme (başka sembol veya başka neden) `saglik.uyarilar`/`veri_yok` olayı olarak uyarı kalır.
- `butunluk.json` v2'de `profil: "v2"`: izlenenler `paper_v2_seti.json`, `havuz_v2.csv`, `maliyet_tablosu_v2.csv` (kendi `.sha256` mührü); kayıt `stratejiler/butunluk_kayit_v2_16.json` (10'lu setin mühürlü kaydı `sonuclar/final/butunluk_kayit_v2.json` değişmeden durur) (`python -m motor.canli.guven --kaydet`, kullanıcı onayıyla); `maliyet_modeli` = hesap başına PortfoyAyarlari özeti. Eski set: `--set eski`.
