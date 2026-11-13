# G4_GITHUB notları

Betik: `sonuclar/hesap_defteri/betikler/g4_github.py` (salt okunur; çıktı `ara/G4_GITHUB_ham.csv`, `_ozet.json`, `_elle_kararlar.csv`).

## 1. Satır sayıları (kaynak ↔ ham)
| kaynak_id | dosya | kaynak | ham |
|---|---|---|---|
| H001 | github_g1_freqtrade.csv | 153 | 153 |
| H002 | github_g2_kripto_bot.csv | 207 | 207 |
| H003 | github_g3_cerceve.csv | 74 | 74 |
| H004 | github_g4_platform.csv | 154 | 154 |
| H005 | github_g5_mt_pine.csv | 166 | 166 |
| H006 | github_g6_liste_notebook.csv | 389 | 389 |
| H007 | github_g7_kutuphane.csv | 55 | 55 |
Toplam 1198 = 1198. H008-H014 (kuyruk, d11f-j, ek ayar) eşleme kaynağıdır; ayrı ham satır üretmez. (wc -l çok satırlı alanlar yüzünden 2 fazla görünür; pandas sayısı doğru.)

## 2. Dağılım
eslesme: KOD 203, AYAR 88, ESDEGER 10, BENZER 280, TEKRAR 8, YOK 609.
on_durum: KOD 301, D_KODLANMADI_NEDENLI 720 (280'i BENZER), G_ML 46, F_YASAK_TIP 25, H_BIZIM_EVRENDE_UYGULANAMAZ 98, TEKRAR 8, **E_KODLANMADI_NEDENSIZ 0**.
D'nin büyük kısmı kaynak durumu `kural_yok` (316 satır; kaynakta kural metni yok) ve kuyruktaki C aileleri.

## 3. Kuyruk: 137 aile
Kuyruk jetonları 295/295 satıra birebir eşlendi (token tam eşleşme; 1 satırda ';'→',' farkı).
- Kodlandı (>=1 satır KOD/AYAR): **105 aile** = d11f-i 71 `kodlandi` + d11j 34 (ayar/mod).
- Kodlanmadı: **32 aile**: 24 C-öncelikli (kural eksik/tek grafiğe uymuyor; d11f-j'de yok, nedeni kuyruk `not`'unda) + 4 çıkış modülü (basamaklı stop, cooldown, kâr-RSI, azalan ROI) + Elder güvenli bölge (6 çıkış modülü; bunlar sonradan `CikisAyarlari` alanı olarak eklendi: cikislar.py:23-45, DURUM.md) + 2 veri_yok (öncü-takipçi korelasyon, günlük yükselenler taraması) + yukarı-boşluk seçici (seans_gap, d11j kurala_dokulemez). 2 aile (`mevcut:cikislar`, `mevcut:swing__mum-coklu-formasyon`) kuyrukta 'mevcut' idi: biri arac_sablon, diğeri BENZER (bit alanı belirsiz).
- Kısmi aileler: kodlandı denen ailelerde bazı kaynak satırları kodlanmamış (sınıf docstring'i söylüyor): ~20 satır D'ye elle çekildi (RSRS rotasyonu, RSI-PHA, AFAOSMD/DHLAOS, saichovsky, r_deadfish/gumbo, Strat, L1-Scalping, EA31337 Retracement, gosterge-egim için GOSTERGELER(21) dışı 8 EA31337 satırı vb.). Liste: `G4_GITHUB_elle_kararlar.csv`.

## 4. d11j modları — koşuldu mu?
- Kanıt (kendim doğruladım): `motor/arastirma/tarama.py::_ayar_listesi` (131-141) = varsayılan + kart + dis + ızgara; `wf_tarama.aday_listesi` bunu çağırır; `wf_portfoy.aday_listesi` (267-278) = BAGLAMA + varsayılan + ızgara. `ayarlar_d11j_ek.json` motor/ ve araclar/ içinde hiçbir yerde okunmuyor; yalnız `testler/test_d11j_modlar.py:253`. Lider ön bulgusu DOĞRU.
- **11 ek ayar (funding-pozitif-short, kombine_07_03, rotasyon bb_uzaklik/triple_rsi, HRP/min_var/mvo, genislik/ftd/dagitim, dunku_getiri) KOŞULMADI.** wf_evren.csv secimler/en_sik_ayar'da 'd11j:' bu ailelerde geçmiyor; ilgili pf sınıflarının ızgarasında (skor, agirlik, rejim_modu, yontem=dunku_getiri) bu mod değerleri yok (pf__kesit_ls izgara: lookback_gun,k,takvim; pf__pairs: yontem eg/johansen/kalman). dis__funding-carry giris_modu='esik' de ızgarada yok (izgara: giris_z, max_tut_saat, atr_k).
- Diğer d11j ayarları (~48 kayıt) `dis_ayarlari/<sınıf>.json` içinde → aday kümesine giriyor ve **koşuldu**: hedef sınıfların hepsi `sonuclar/evren/2017_gelistirme/wf_evren.csv`'de (n_aday 14-70); 'dis:d11j:...' seçimlerde 12 sınıfta geçiyor (ör. min10-dip, sqz-donus, macd-sinyal trix30_sifir, rsi-asiri-donus rsidyn/stc_25_75, renko-sr, mum-yutan-donus, hacim-patlama-kirilimi, supertrend-psar ha_atr_ma).
- Mod değerleri sınıf `parametre_izgarasi`'na girmemiş (bant-donus: onay_osc/bant_tipi; macd-sinyal: gosterge; rsi-asiri-donus: gosterge/esik_modu; supertrend-psar: gosterge chandelier/nrtr/ha_atr; ma-kesisim: ma_tipi wma/hma/cma/mama/itrend; mum-yutan-donus mod=devam; ma-geri-cekilme mod=uclu_hiza; ichimoku mod=skor). Sınıf varsayılanları değişmemiş (kodda mod varsayılanı eski değer). Yani bu modlar YALNIZ ayar kaydıyla koşuldu; kayıtsız modlar (örn. macd-sinyal gosterge=tdld, rsi Oscillator Range, ATR_ADX) hiç koşulmadı çünkü kodlanmadı.

## 5. Bulgular / tutarsızlıklar
1. d11f `elder-guvenli-bolge-stop` "cikislar.py'ye eklenmesi başka işin kapsamı" diyor; sonradan eklendi (elder_guvenli_bolge_k). Kuyruk/d11 notları güncel değil.
2. İlk taramadaki `ayar:yeni__ma-tipli-kesisim` vb. adlar kodlama_2026-11-07_d10a-d dosyalarında `dis__...` olarak çözüldü; DEMA/TEMA satırları dis__ma-tipli-kesisim'de yok (yalnız smma|vwma).
3. 8 makale başlığı (g6) README + paper_meta.json'da iki kez: ikinci satır TEKRAR.
4. dis__funding-carry wf_evren'de n_aday_hata=594 (bu görev kapsamında incelenmedi).
5. Kuyruk "mevcut:..." ve ilk tarama 'ayar:X' satırlarının çoğu (280 BENZER) sınıf açılarak birebir doğrulanamadı: 'fark test edilmedi' listesine girer. Yalnız 10 ma-kesisim satırı periyot çifti ayar kümesinde bulunup ESDEGER sayıldı.
6. KOD (203): 62 satırda sınıf kaynağında ad/dosya adı geçiyor (g1 freqtrade ağırlıklı), 4'ü yalnız ilk tarama 'kodlandi'; kalanı d11f-i eşlemesi. pf__ hedefli ayar:/mevcut: satırları e2 ile KOD sayılmadı (BENZER).
7. Birden çok alt kuralı olan dosyalarda (TrendRiderStrategy / …) tek ayar kaydı alt kuralı ayırmıyor.

## 6. Öz kontrol
Rastgele 10 satır kaynağa geri izlendi (H001:1, H001:69, H002:117, H003:1, H004:141, H005:75, H005:119, H006:287, H007:12, H002:161): ham_id↔CSV satırı tutuyor; H002:117 ve H002:134 önce hatalı AYAR eşleşmişti (jenerik ad), e1 kuralı sıkılaştırılarak düzeltildi (artık BENZER). Kalan zayıf nokta: BENZER satırların `fark` alanı genel (ilk tarama notu + sınıf varsayılanı).
