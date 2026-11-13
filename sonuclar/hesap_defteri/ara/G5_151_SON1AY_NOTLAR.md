# G5_151_SON1AY notlari

Betik: `sonuclar/hesap_defteri/betikler/g5_151_son1ay.py` (kendi dosyalarimi yazar). Ciktilar: `ara/G5_151_SON1AY_ham.csv` (189), `ara/G5_151_SON1AY_elle_kararlar.csv` (elle karar verilen 37 satir).

## Satir sayilari
| Kaynak | Kaynak satiri | Ham satir |
|---|---|---|
| Q001 kakushadze_151.csv | 173 | 173 |
| Q004 son1ay_2026-11.csv | 16 | 16 |
| Q002 kodlama_151_d12b.csv (8) ve Q003 ayarlar_d12b_ek.json (7) | esleme/karar dosyasi | ham satir uretmez; eslemeler `kanit`/`ayar_id` alaninda |
| Q005 son1ay_2026-11.md | karar metni | ham satir yok; `kanit` ve nedenlerde kullanildi |
Toplam 189 = 173 + 16, tutuyor.

## 173 neden 151 degil
Kitap "151" der ama CSV alt varyantlari ayri satir sayiyor (3.9.1, 4.1.1, 4.1.2, 5.8.1, 6.3.1, 7.3.1, 8.2.1, 10.1.1, 10.1.2, 10.3.1, 13.2.1, 15.2.1-3, 15.3.1, 16.3.1-3 ...) ve opsiyon bolumunde 56 payoff. Kaynak: kakushadze_151_OZET.md ("173 = numarali strateji ve alt varyantlar"). Sayi sapmasi kayip degil, sayim farki.

## Dagilim (betikle sayildi)
on_durum: H_BIZIM_EVRENDE_UYGULANAMAZ 117, D_KODLANMADI_NEDENLI 51, KOD 15, G_ML 5, F_YASAK_TIP 1, E 0, BELIRSIZ 0.
eslesme: YOK 155, BENZER 19, AYAR 6, KOD 6, ESDEGER 3, TEKRAR 0.
KOD on_durumlu 15 = AYAR 6 + KOD (hp-filtre-ma, fomc-gunu-long, son1ay 4) 6 + ESDEGER 3.

Kakushadze kendi durumu -> benim durumum: veri_yok 91 (56 opsiyon + VIX/opsiyon/HFT -> H; temel/FX faiz/COT/makro/vade yapisi -> D veri_yok), kapsam_disi 48 -> H kapsam_disi (tahvil, CDO, gayrimenkul, nakit, altyapi, vergi, kaldiracli ETF ...), ml 4 -> G, yasak 1 -> F (17.2 kara para aklama, neden_kodu=yasa_disi), mevcut/ayar/yeni (29) -> KOD/AYAR/ESDEGER/BENZER/D.
Ayrim ilkesi: opsiyon/VIX/HFT/orderbook ve evrende hic bulunmayan varlik sinifi = H; ayni sinifta veri eksigi (bilanco, faiz/forward, COT, vade yapisi, makro) = D veri_yok.

## ONEMLI KONTROL: ayarlar_d12b_ek.json arastirma hattinda okunuyor mu? HAYIR
- `motor/arastirma/tarama.py::_ayar_listesi` (satir 131-141) yalniz varsayilan + `kayit.kart_ayarlari` + `dis_ayarlari` (stratejiler/dis_ayarlari/<ad>.json) + sinifin `parametre_izgarasi`.
- Portfoy hatti `motor/arastirma/wf_portfoy.py::aday_listesi` (satir 267-278) yalniz varsayilan + `parametre_izgarasi`.
- Dosya adi (`ayarlar_d12b_ek`) `motor/` ve `araclar/` icinde gecmiyor; depo disinda yalniz `testler/test_d12b_151.py:22` (ve benzeri d11j icin `testler/test_d11j_modlar.py:253`) okuyor. Testin kapsami: ayar kurulur, nedensel, dolar-notr; getiri/WF kosusu degil.
- `parametre_izgarasi`: pf__kesit_ls = lookback_gun/k/takvim, pf__rotasyon = lookback_gun/k/takvim; `skor="ibs"|"dusuk_vol"|"r2_alfa"`, `agirlik="orantili"|"getiri_vol"` izgarada YOK. Yani d12b ile eklenen 7 ayar (ibs_k3_gunluk, dusuk_vol_90, donus_orantili, getiri_orantili, btc_faktor_90, evren_faktor_90, getiri_vol_k3) arastirma/WF koşusuna HIC girmedi. `sonuclar/wf_portfoy/*.csv` ve `sonuclar/*/*.csv` icinde `d12b:` gecen dosya bulunamadi (grep -l, maxdepth 2). Kodlama_151_d12b.csv notlari da "izgarada yok" diyor (satir 2, 3).
- Etki: 6 AYAR satiri (3.4, 3.9, 4.3, 4.4, 4.6, 10.3) kodda/ayar dosyasinda var ve test-edilebilir, ama bir kez bile kosulmadi (liderin "kodlandi ama test edilmedi" listesine girmeli). Her satirin `not` alanina yazildi. Ayni sekilde `dis__hp-filtre-ma` ve `dis__fomc-gunu-long` tek-grafik siniflari kayit uzerinden varsayilan+izgara ile taranabilir (D3Taban), onlar bu sorunun disinda.
- portfoy_adaylari.csv ve kodlama_2026-11-07_pf.csv icinde 151/d12b kaynakli satir YOK (grep "151|d12b" bos). stratejiler/dis_ayarlari/ icinde hp/fomc/kesit ayari yok (yalniz dis__son1ay-* iki dosya).

## 151 satirlari: bulgular
- Kodlama kaydi (kodlama_151_d12b.csv) 8 satir: 7 madde kodlandi (4.4, 3.4, 3.9/10.3, 4.6, 4.3 vekil, 8.1, 19.5; "3.9 / 10.3" iki CSV satirina bolundu), 3.9.1 KODLANMADI (evren: grup basina 1-3 sembol). Eslesen sinif kod_kaydi.csv'de var: pf__kesit_ls, pf__rotasyon, dis__hp-filtre-ma (satir 200), dis__fomc-gunu-long (134).
- Tutarsizlik 1: CSV `durum` 'mevcut/ayar' etiketli 4.4 (IBS), 3.4, 3.9, 10.3, 4.3, 4.6 satirlari kodlanmadan once yazilmis (yeni/ayar) — sonra d12b kodladi; CSV'nin `benzer_1l3a` ve `durum` sutunlari bu yeni kodu yansitmiyor (ör. 4.4 satirinda hala 'pf__ibs_donus ... kesitsel degil; skor ibs eklenebilir').
- Tutarsizlik 2: 3.4 "ayar:pf__rotasyon" (long-only) idi; d12b L/S dolar-notr kesit_ls ayari ekledi (pf__rotasyon skor=dusuk_vol izgarada yok).
- Tutarsizlik 3: 8.1 FX HP-MA 'yeni'; FX evreni yok ama sinif tek-grafik genel kural (kripto/hisse/emtia) olarak kodlandi; KOD kabul edildi.
- BENZER 19 satir (D_KODLANMADI_NEDENLI, benzer_var): 3.1, 3.6, 3.7, 3.8, 3.10, 3.12, 3.13, 3.14, 3.15, 3.18, 4.1, 4.1.1, 4.1.2, 4.2, 6.5, 9.3, 9.4 (+ son1ay 5 ve 7). Hepsinde sinif/docstring acildi; farklar `fark` sutununda. ESDEGER 3: 3.11 -> dis__sma200-ls (izgara sma_n 150-250), 9.5 -> pf__kesit_ls skor carpiklik (portfoy_adaylari.csv:58 ayni ayar), 10.4 -> pf__cta sinyal=tsmom (olcekleme farki).
- benzer_1l3a dolu olup BENZER/ESDEGER OLMAYAN satirlar: 6.2, 8.2, 9.1 (hedef dis__funding-carry) — sinif acildi: z-skor yonlu kripto fonlama girisi, arbitraj degil / karsilik degil; D veri_yok. 3.17/3.20/18.2/18.3 G_ML.
- Ham fark listesi: "pf__kesit_ls skor=getiri atla=30 lookback=365" (3.1), "mod=ters lookback~1260" (9.4), "agirlik=sabit" (9.3), "trend_sma>0" (4.1.1) siniflarda var ama ayar kaydi/izgara yok: ayar yazilsa ESDEGER olurdu.
- Q004 'okunmadi' satiri 16 tek ham satir ama 6 depo iceriyor (kaynak CSV de tek satir).

## son1ay (Q004)
Kullanici onayli 4 aday KODLANDI: #1 delta-paper-bot -> dis__son1ay-donchian-adx (+ dis ayar son1ay:delta-strategy.py-varsayilan), #2 schrodingers-quant -> dis__son1ay-kanal-20-10 (+ 2 dis ayar), #3 TrendRider -> pf__son1ay_trendrider, #4 E014 -> pf__son1ay_e014 (kod_kaydi.csv satir 314, 315, 512, 511; DURUM.md:338-341 "4 aday test edildi, hicbiri final havuza girmedi"). Akibet G0'da.
Diger 12 satir alinmama nedenleri (son1ay_2026-11.md'de yaziyor, hepsi): #5 EMA30/90 'izle' (al-tut altinda; BENZER swing__ma-kesisim), #6 CacheCarti ders kaynagi/kod incelenmedi, #7 BAB sonuc yok (BENZER pf__kesit_ls skor beta), #8 H-009 sonuc yok/kilitli, #9 scalp kural tam degil, #10 2304 konfig coklu test, #11 helloword kapali kaynak, #12 huhcat2 ML Ridge, #13 balbin570 kural yok, #14 Cince yazi sermaye belirsiz, #15 Freqtrade surumu (arac), #16 okunmayan 6 depo. Hepsinin nedeni md'de yazili -> E yok.
Test sonuc dosyalari (wf/saglamlik/wf_portfoy son1ay_*, son1ay_kilit_bilgi.json, son1ay_yazar_karsilastirma.csv) yalniz basliklarla yoklandi; akibet G0'in isi. Ham satir: dis__son1ay-donchian-adx (ETH/BTC 4h) ve kanal-20-10 BTC 4h; pf__son1ay_trendrider kripto, pf__son1ay_e014 makro.

## Envanter disi / dikkat
Envanter disi kaynak yok. `son1ay_2026-11.csv` 16 satirinin altisi '-' sira numarasi, 10 numarali; Q003 (ayar JSON) satir sayisi 7 ama ham satir uretmiyor.

## Oz kontrol
Rastgele 10 Q001 satiri (3, seed) kaynak CSV satirina geri izlendi (kanit `kakushadze_151.csv:L` = veri satiri+1, baslik 1. satir): 10/10 ad ve bolum uydu. Ek: AYAR/KOD 15 satirin hedef sinifi kod_kaydi.csv'de ve docstring'inde dogrulandi; 3.4 ve 19.5 acik kontrol edildi. Emin olmadiklarim: ESDEGER 3 kararinin kitap metni olmadan (PDF repoda yok) yalniz CSV kural_ozeti ile verilmesi; H/D ayrimi (FX/vade/makro D veri_yok, opsiyon/VIX/HFT/evren disi H) benim ilkem, lider degistirebilir.
