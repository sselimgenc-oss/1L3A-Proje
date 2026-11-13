"""G5_151_SON1AY ham satir uretici (hesap defteri). Kaynak: kakushadze_151.csv (173) + son1ay_2026-11.csv (16).
Calistirma: python3 sonuclar/hesap_defteri/betikler/g5_151_son1ay.py  (depo kokunden)
Yazar: ara/G5_151_SON1AY_ham.csv ve ara/G5_151_SON1AY_elle_kararlar.csv. Baska dosyaya dokunmaz."""
import csv
import collections
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
ARA = KOK / "sonuclar" / "hesap_defteri" / "ara"
KK = "stratejiler/ek_kaynaklar/kakushadze_151.csv"
OZ = "stratejiler/ek_kaynaklar/kakushadze_151_OZET.md"
KD = "stratejiler/kodlama_151_d12b.csv"
AJ = "stratejiler/ayarlar_d12b_ek.json"
S1 = "stratejiler/ek_kaynaklar/son1ay_2026-11.csv"
S1MD = "stratejiler/ek_kaynaklar/son1ay_2026-11.md"
KR = "sonuclar/hesap_defteri/ara/kod_kaydi.csv"

kod_satir = {}
for n, s in enumerate((ARA / "kod_kaydi.csv").read_text(encoding="utf-8").splitlines(), 1):
    kod_satir[s.split(",")[0]] = n


def kr(ad):
    return f"{KR}:{kod_satir[ad]}"


AYAR_NOT = ("ayarlar_d12b_ek.json arastirma hattinda OKUNMUYOR: motor/arastirma/tarama.py::_ayar_listesi (varsayilan+kart+dis+izgara) ve "
            "motor/arastirma/wf_portfoy.py::aday_listesi (varsayilan+izgara) bu dosyayi acmaz; motor/ ve araclar/ icinde adi gecmez, yalniz "
            "testler/test_d12b_151.py okur. Ayrica skor/agirlik modu pf__kesit_ls/pf__rotasyon parametre_izgarasi'nda yok -> test kosusuna girmedi.")

EVREN = "evren: kripto 13 + ABD hisse + emtia (perp), karar 27"

# (idx, eslesme, hedef, ayar_id, ayar_dosyasi, fark, on_durum, neden_kodu, neden_metni, kanit_ek, aile, kisa_mantik, not)
E = {}


def put(i, **k):
    E[i] = k


# --- KOD / AYAR (d12b kodlamasi)
def ayar(i, ayar_id, hedef, kd_satir, kisa, fark_not, aile="MR"):
    put(i, eslesme="AYAR", hedef=hedef, ayar_id=ayar_id, ayar_dosyasi=AJ, fark="", on_durum="KOD", neden_kodu="", neden_metni="",
        kanit=f"{KD}:{kd_satir} ; {AJ}#{ayar_id.split(' ; ')[0]}", aile=aile, kisa_mantik=kisa, **{"not": fark_not + " | " + AYAR_NOT})


ayar(83, "d12b:kesit-ibs:ibs_k3_gunluk", "pf__kesit_ls", 2, "Onceki gun IBS'ye gore kesit sirala: dusuk IBS long, yuksek IBS short, dolar-notr, gunluk.",
     "Kitap decil; 13 sembolde k=3. Sinif: motor/portfoy/stratejiler/kesit.py skor='ibs' (ac_kod: -IBS satirlari 113-118). pf__ibs_donus ayri (sembol basina long-only).")
ayar(60, "d12b:kesit-dusuk-vol-ls:dusuk_vol_90", "pf__kesit_ls", 3, "Dusuk volatilite long, yuksek volatilite short, dolar-notr (kesit).",
      "Kitap 126-252 gun sigma, burada 90 gun (varsayim); kesit.py skor='dusuk_vol'. Long-only kol pf__rotasyon skor=dusuk_vol (izgarada yok).")
ayar(65, "d12b:kesit-orantili-agirlik:donus_orantili", "pf__kesit_ls", 4, "Ortalama getiriden sapmayla orantili dolar pozisyon, dolar-notr (kisa vadeli donus).",
      "kesit.py agirlik='orantili' (k yok sayilir); getiri_orantili varyanti da dosyada.")
ayar(129, "d12b:kesit-orantili-agirlik:donus_orantili", "pf__kesit_ls", 4, "Haftalik getirinin piyasa ortalamasindan sapmasiyla orantili agirlik, dolar-notr.",
      "3.9 ile ayni ayar; ayrica d12b:kesit-orantili-agirlik:getiri_orantili (90g momentum sapmasi) dosyada. Kitap 1/sigma bastirma ve haftalik dengeleme: ayarda takvim ayri.")
ayar(82, "d12b:r2-secicilik-alfa:evren_faktor_90 ; d12b:r2-secicilik-alfa:btc_faktor_90", "pf__kesit_ls", 6,
     "Tek faktorlu alfa ve R2: dusuk R2 + yuksek alfa long, tersi short.",
     "Kodlama 'kodlandi (vekil)': 5x5 kantil yerine surekli skor z(alfa)+z(1-R2), faktor=BTC ya da evren ortalamasi; kitap 4 faktor.", aile="diger")
ayar(85, "d12b:rotasyon-getiri-vol-agirlik:getiri_vol_k3", "pf__rotasyon", 5 + 0, "R>0 olan varliklari R/sigma agirlikli tut, long-only.",
     "Kodlama satiri 4.6 (kodlama_151_d12b.csv:5). Fark: kitaptaki negatif R/sigma short ve MA filtresi opsiyonu yok; agirlik='getiri_vol' izgarada yok.", aile="trend")
E[85]["kanit"] = f"{KD}:5 ; {AJ}#d12b:rotasyon-getiri-vol-agirlik:getiri_vol_k3"
E[85]["fark"] = "kitap negatif R/sigma short bacagi ve sigma^2 secenegi kodlanmadi (yalniz R>0, long-only)"
E[85]["eslesme"] = "AYAR"

put(113, eslesme="KOD", hedef="dis__hp-filtre-ma", ayar_id="", ayar_dosyasi="", fark="", on_durum="KOD", neden_kodu="", neden_metni="",
    kanit=f"{KD}:7 ; {kr('dis__hp-filtre-ma')} ; motor/strateji/dis/d12b_151.py (HpFiltreMa docstring)", aile="trend",
    kisa_mantik="Nedensel (tek tarafli) HP trendi uzerinde hizli/yavas SMA kesisimi: long/short.",
    **{"not": "Sapma: iki tarafli HP yerine kayan pencere sonu noktasi; lambda/pencere/MA varsayim. FX evreni yok ama kural tek-grafik (kripto/hisse/emtia) olarak kodlu; sinif izgarasi (lambda,hizli,yavas) arastirma hattinda kosar (D3Taban, kayit)."})
put(172, eslesme="KOD", hedef="dis__fomc-gunu-long", ayar_id="", ayar_dosyasi="", fark="", on_durum="KOD", neden_kodu="", neden_metni="",
    kanit=f"{KD}:8 ; {kr('dis__fomc-gunu-long')} ; motor/strateji/dis/d12b_151.py (FOMC_GUNLERI)", aile="diger",
    kisa_mantik="FOMC karar gunu ABD hisse/endeksinde long, gun sonu cikis; diger gunler nakit.",
    **{"not": "FOMC_GUNLERI 2020-2026 hafizadan (teyit onerilir), acil toplantilar yok; yalniz DK_SPX/ABD hisseleri, gun ici mum sart. Ilgili ama ayri: v3__pre-fomc-surunme (kod_kaydi.csv:" + str(kod_satir['v3__pre-fomc-surunme']) + ")."})

# --- D: kodlanmadi (kodlama_151_d12b)
put(66, eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="evren_yetersiz",
    neden_metni="Evrende grup (sektor) basina 1-3 sembol: Mag7 tek teknoloji kumesi, kripto 3, emtia 3; grup-notr sapma anlamsiz.",
    kanit=f"{KD}:9 ; {KK}:67", aile="MR",
    kisa_mantik="Her sektor grubunda ayri ortalamaya donus (grup-notr), gruplar esit sermayeli.",
    **{"not": "Evren genisleyince yeniden degerlendirilir (kodlama_151_d12b.csv satir 9). pf__kesit_ls'te grup-notr secenek yok."})

# --- BENZER / ESDEGER (sinif acilarak)
KS = "motor/portfoy/stratejiler/kesit.py"
RS = "motor/portfoy/stratejiler/rotasyon.py"


def benz(i, hedef, fark, kisa, aile, kanit_ek="", not_=""):
    put(i, eslesme="BENZER", hedef=hedef, ayar_id="", ayar_dosyasi="", fark=fark, on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var",
        neden_metni="Kaynak CSV benzer sinifi gosteriyor; kural acildi, farklar var (fark sutunu).",
        kanit=f"{KK}:{i+1} ; {kr(hedef)}" + (f" ; {kanit_ek}" if kanit_ek else ""), aile=aile, kisa_mantik=kisa, **{"not": not_})


def esd(i, hedef, kisa, aile, kanit_ek="", not_=""):
    put(i, eslesme="ESDEGER", hedef=hedef, ayar_id="", ayar_dosyasi="", fark="yok", on_durum="KOD", neden_kodu="",
        neden_metni="", kanit=f"{KK}:{i+1} ; {kr(hedef)}" + (f" ; {kanit_ek}" if kanit_ek else ""), aile=aile, kisa_mantik=kisa, **{"not": not_})


benz(57, "pf__kesit_ls", "Sinif skor='getiri' atla=30/lookback=365 destekler ama bu ayar izgarada ve ayar dosyalarinda yok; kitap decil (~%10), burada k<=3/13; hisse evreni 13 sembole iner",
     "Hisse 12-1 ay momentum: en iyi decil long, en kotu short, aylik tut.", "trend", KS + " (skor getiri)")
benz(62, "pf__kesit_ls", "Kitap value+momentum rank-ortalamasi (value verisi yok); sinif skor='kombine' = z(risk_ayarli)+z(-3g getiri), yalniz fiyat faktorleri",
     "Birden fazla faktorun siralamasini ortalayip kesit L/S kurmak.", "diger", KS + " (kombine)")
benz(63, "pf__kesit_ls", "Kitap 36 ay FF3 regresyonu, 12 ay kalinti ort/sigma; sinif tek referansla (BTC/evren) 90g kayan beta kalintisi",
     "Faktor regresyonu kalintisinin 12 aylik ort/sigma'sina gore kesit sirala.", "trend", KS + " (artik)")
benz(64, "pf__pairs", "Kitap: iki hissenin donem getirisinin ortalamadan sapmasi, dolar-notr; sinif mesafe yontemi SSD/z-skor ile cift secimi ve esik/stop kullanir, getiri sapmasi birebir degil",
     "Iki yuksek korelasyonlu varlikta pahali olani short, ucuzu long (dolar-notr).", "MR", "motor/portfoy/stratejiler/pairs.py (docstring)")
benz(67, "pf__pca_statarb", "Kitap: sektor+sektor disi faktor yuk matrisine agirlikli (1/sigma^2) regresyon; sinif PCA ozportfoy yukleri + OU s-skoru, 18 hisse evreni ve esik giris/cikis",
     "Getiriyi faktor yuklerine regres edip kalintinin tersiyle dolar-notr konumlan.", "MR", "motor/portfoy/stratejiler/ek2.py (PcaStatArb)")
benz(70, "dis__ma-dizilim-5-10-30", "Kitap periyotlari 3/10/21; sinif izgarasi hizli {3,5,8} orta {10,13,20} yavas {30,50}: yavas=21 izgara disi; kitap cikis MA3<=MA10, sinif dizilim bozulunca cikar",
     "SMA3>SMA10>SMA21 dizilimiyle long, ters dizilimde short.", "trend", "motor/strateji/dis/d9_atlanan_b.py (MaDizilim51030)")
benz(71, "swing__pivot-seviye", "Kitap: pivot merkez ustunde long, R'de kapat; sinif tepki/kirilim modlari, EMA trend filtresi, ATR tamponlu stop, hedef sonraki seviye/R: basit merkez-ustu-long kurali birebir yok",
     "Onceki gun pivotuna gore: merkez ustu long (hedef R), alti short (hedef S).", "trend", "motor/strateji/swing/pivot_seviye.py")
benz(72, "swing__donchian-kirilim", "Kitap hem sinir donusu (tabana degince long) hem kirilim kolu; donchian-kirilim yalniz kirilim kolu (donus kolu swing__aralik-ticareti'nde, ayri sinif); T kitapta sabit degil",
     "Kanal tavan/tabaninda donus ya da kirilim izleme.", "trend", "motor/strateji/swing/donchian_kirilim.py ; kod_kaydi'nda swing__aralik-ticareti ayri sinif")
benz(75, "pf__sabit_sepet", "Kitap w ~ C^-1 E (ortalama-varyans) ve dolar-notr Lagrange; sinif agirlik='mvo' yalniz long-only, L/S Sigma^-1 E yok; kendi sinyali yok (cerceve)",
     "Beklenen getiri sinyaliyle ortalama-varyans agirliklandirma (istatistiksel arbitraj).", "diger", RS + " (SabitSepet agirlik mvo)")
benz(78, "pf__rotasyon", "Kitap decil, 6-12 ay getiri, 1-3 ay tut; sinif mutlak=True varsayilan (izgarada hep acik) ve long-only, lookback 30/90/180 takvim W/M/Q; 365g ve mutlak=False izgarada yok",
     "ETF/sektor 6-12 aylik getiriye gore en iyi decili long (ya da L/S), 1-3 ay tut.", "trend", RS + " (Rotasyon skor getiri)")
benz(79, "pf__rotasyon", "trend_sma filtresi sinifta var ama izgarada 0 (kapali); kitap alt decil short + MA alti sarti yok (long-only sinif)",
     "Rotasyonda yalniz fiyat>MA(100-200) olan ustteki ETF'ler long.", "trend", RS + " (trend_sma)")
benz(80, "pf__gem", "Kitap piyasa endeksi MA altinda ise nakit/korelasyonsuz varliga gecis; Gem mutlak momentum (skor<=0) + savunma kolu DK_XAU/nakit, MA esigi yok",
     "Goreli momentum sec, piyasa zayifsa savunma varligina ya da nakde gec.", "trend", RS + " (Gem)")
benz(81, "pf__kesit_ls", "Kitap FF3 regresyonu kesisim alfasi; sinif 'artik' skoru beta-ayarli kalinti getiri ort/sigma (tek referans)",
     "ETF getirisini faktorlere regres edip kesisim alfasina gore siralamak.", "diger", KS + " (artik)")
benz(105, "dis__voltarget-trend", "Kitap saf vol hedefleme (w=sigma*/sigma, rejim yok, esik yeniden dengeleme); sinif SMA200 rejim + haftalik giris + ATR stop + tek pozisyon, saf surum degil (not: 'rejim filtresiz saf surum = ayar' ayar olarak yazilmamis)",
     "Hedef/gerceklesen volatilite oraniyla risk agirligi, kalan risksiz.", "diger", "motor/strateji/dis/d2_trend.py (VoltargetTrend)")
benz(121, "pf__sabit_sepet", "Pasif kol (sabit pay, donemsel dengele) SabitSepet'te var ama agirlik='sabit' izgarada yok (esit/ters_vol); aktif kol Fed iskonto verisi gerektirir, yok",
     "Portfoye sabit emtia payi ayir, donemsel dengele (pasif) ya da faize gore ayarla (aktif).", "diger", RS + " (SabitSepet)")
benz(122, "pf__kesit_ls", "Sinif skor='getiri' mod='ters' lookback~1260 destekler (kodlanmadi ayar), izgara 14/30/90; kitap tercil + aylik, evren yalniz 5 emtia ve 2020 oncesi veri gerekir; ayar dosyasinda yok",
     "5 yil onceki fiyat/simdiki fiyat (value): ust tercil long, alt tercil short, aylik.", "MR", KS + " (getiri mod=ters)")
esd(123, "pf__kesit_ls", "Gecmis getiri carpikligi en dusuk long, en yuksek short (kesit).", "diger", KS + " (skor carpiklik/asimetri) ; stratejiler/portfoy_adaylari.csv:58 (carpiklik 5/5 ayari)",
    "Kitap kuintil, evren 13 sembol k kisiliyor; lookback izgarada. Kural ayni (-carpiklik).")
esd(131, "pf__cta", "Her varlikta getiri isaretiyle long/short, 1/sigma olceginde.", "trend", "motor/portfoy/stratejiler/cta.py (sinyal=tsmom, birlesim=bagimsiz) ; dis__tsmom, dis__ewmac-carver",
    "Kural ayni (sign(R)/sigma); olcek sum|w|=1 yerine hedef vol (sadece olcekleme, motor 3x tavan). Dolar-notr varyanti yok.")
esd(68, "dis__sma200-ls", "Fiyat SMA(T) ustunde long, altinda short; long-only/short-only secenegi yonler parametresinde.", "trend", "motor/strateji/dis/d3_kural.py (Sma200Ls: sma_n 150-250, yonler)",
    "ATR stop motor eklentisi (kitapta stop yok); EMA secenegi dis__ema-esik-trend/dis__kapanis-ma5 gibi ayri siniflarda.")
put(69, eslesme="BENZER", hedef="swing__ma-kesisim", ayar_id="", ayar_dosyasi="",
    fark="Kitap MA(10)>MA(30) durumuyla long/short (opsiyonel %2 geri cekilme stopu); sinif kesisimde giris, ATR stop; hizli {5,9,14} yavas {21,34,50}: 10/30 izgara disi",
    on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var", neden_metni="Kaynak CSV benzer sinifi gosteriyor; kural acildi, farklar var (fark sutunu).",
    kanit=f"{KK}:70 ; {kr('swing__ma-kesisim')} ; motor/strateji/ma_kesisim.py", aile="trend",
    kisa_mantik="Hizli MA yavas MA'nin ustundeyse long, altindaysa short.", **{"not": "dis__ma-cift-cross, dis__ma-kesisim-dinamik de var ama acilmadi."})

# --- veri/arac evren: acik karar satirlari
YASAK = 162
put(YASAK, eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="F_YASAK_TIP", neden_kodu="yasa_disi",
    neden_metni="Kara para aklama yasa disidir; proje yasaklar listesi dahilinde yapilmaz.", kanit=f"{KK}:163", aile="diger",
    kisa_mantik="Nakit kaynagini gizlemeye yonelik islem anlatisi (strateji degil).", **{"not": "Kendi durum sutunu: yasak."})

for i in (74, 77, 167, 168):
    pass

ML = {74: "Tek hissede KNN ile getiri tahmini.", 77: "Birden fazla alfa sinyalini model agirligiyla birlestirme.", 167: "Yapay sinir agi ile BTC getiri tahmini.",
      168: "Metin duyarliligini naive Bayes ile siniflandirma."}
for i, t in ML.items():
    put(i, eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="G_ML", neden_kodu="ml",
        neden_metni="Kaynak durumu 'ml': makine ogrenmesi/model tahmini; proje ML'yi elenen kategori sayiyor." + (" Ayrica metin verisi yok." if i == 168 else ""),
        kanit=f"{KK}:{i+1} ; {OZ}#ml", aile="diger", kisa_mantik=t, **{"not": ""})

# H / D varsayilan kurallari
OPS = {"3.5": "opsiyon zimni volatilite verisi", "6.3": "opsiyon", "6.3.1": "opsiyon"}
H_ORDERBOOK = {76: ("orderbook", "Piyasa yapiciligi emir defteri (L2) ve dusuk gecikme ister; bid/ask verisi yok, HFT."),
               104: ("hft", "Gun ici ETF arbitraji bid/ask tick verisi ve HFT altyapisi ister; ETF evreni de yok."),
               118: ("hft", "Ucgen FX arbitraji FX tick bid/ask ister; FX evreni yok, HFT/arbitraj.")}
D_VERI = {99: "CDS spreadleri ve tahvil verisi yok (CDS bazi arbitraji).", 58: "Bilanco EPS gecmisi yok (hisse temel verisi).", 59: "Bilanco defter degeri yok (temel veri).", 73: "M&A duyuru ve takas orani verisi yok.",
          101: "Endeks vadelisi, spot sepet ve temettu verisi yok; kripto karsiligi dis__funding-carry mantik olarak farkli (z-skor yonlu giris, arbitraj degil).",
          114: "Faiz/forward verisi yok; FX evreni yok.", 115: "Faiz/forward verisi yok; FX evreni yok.", 116: "Faiz/forward verisi yok; FX evreni yok.",
          117: "Faiz/forward verisi yok; FX evreni yok.", 119: "Vade yapisi (on/ikinci ay) yok; Dukascopy tek seri. Kripto karsiligi dis__funding-carry mantik olarak farkli.",
          120: "CFTC COT haftalik verisi yok.", 124: "Vade egrisi verisi yok.", 128: "Vade yapisi yok (takvim spreadi).",
          130: "Acik pozisyon (open interest) verisi yok; OHLCV var ama kural acik pozisyon suzgeci ister.",
          143: "Enflasyon swap/CPI verisi yok.", 144: "TIPS/CPI verisi yok.", 145: "Hava endeksi turevi verisi yok.",
          146: "Elektrik+gaz vadelisi yok (NATGAS tek seri).", 152: "Temerut olasiligi/bilanco verisi yok.", 153: "Temerut olasiligi/bilanco verisi yok.",
          169: "GDP/CPI/politika faizi makro verisi yok.", 170: "CPI ana/cekirdek verisi yok."}
H_KAPSAM_BOLUM = {"5": "tahvil/getiri egrisi verisi ve urunu yok", "10.1": "hedge ihtiyaci (korunma) yatirim sinyali degil; vadeli enstruman yok",
                  "11": "CDO/MBS/CDS yapilandirilmis urun verisi yok", "12": "donusturulebilir tahvil+opsiyon yok", "13": "vergi arbitraji; tahvil/vergi verisi yok",
                  "15": "sikintili borc yatirimi evren disi", "16": "gayrimenkul evren disi", "17": "nakit/repo/rehin evren disi", "19.4": "devlet tahvili+makro verisi yok",
                  "20": "altyapi fonlari evren disi", "4.5": "kaldiracli ETF evrende yok"}

BOLUM_KISA = {
    "3": "Hisse stratejisi", "4": "ETF stratejisi", "5": "Sabit getirili (tahvil) stratejisi", "6": "Endeks stratejisi", "7": "Volatilite (VIX) stratejisi",
    "8": "FX stratejisi", "9": "Emtia stratejisi", "10": "Vadeli islem stratejisi", "11": "Yapilandirilmis urun stratejisi", "12": "Donusturulebilir tahvil stratejisi",
    "13": "Vergi arbitraji", "14": "Cesitli (enflasyon/hava/enerji) strateji", "15": "Sikintili varlik stratejisi", "16": "Gayrimenkul stratejisi",
    "17": "Nakit yonetimi islemi", "19": "Kuresel makro strateji", "20": "Altyapi yatirimi"}


def bolum_kok(b):
    return b.split(".")[0]


def h_kapsam(b):
    for k in sorted(H_KAPSAM_BOLUM, key=len, reverse=True):
        if b == k or b.startswith(k + ".") or b.startswith(k):
            return H_KAPSAM_BOLUM[k]
    return None


def varsayilan(i, x):
    b = x["bolum"]
    ad = x["ad"]
    k = f"{KK}:{i+1}"
    base = dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", aile="diger", **{"not": f"Kaynak durum={x['durum']}; veri_ihtiyaci: {x['veri_ihtiyaci'][:80]}"})
    if b.startswith("2."):
        base.update(on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ", neden_kodu="opsiyon",
                    neden_metni="Opsiyon payoff semasi: opsiyon zinciri/zimni vol verisi yok, perp evreninde opsiyon yok; yonsuz sinyal kurali da yok.",
                    kanit=f"{k} ; {OZ}#Bolum bazinda sayi ve durum", kisa_mantik=f"Opsiyon payoff yapisi: {ad[:60]}; kazanc/kayip semasi, sinyal yok.")
        return base
    if i in H_ORDERBOOK:
        kod, m = H_ORDERBOOK[i]
        base.update(on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ", neden_kodu=kod, neden_metni=m, kanit=f"{k} ; {OZ}#Kapsam disi / veri yok bolumler",
                    kisa_mantik=f"Kisa vadeli emir/tick tabanli islem: {ad[:60]}.")
        return base
    if b in OPS or bolum_kok(b) == "7":
        n = "opsiyon" if b in OPS or True else "vix"
        kod = "opsiyon" if b in OPS else "vix"
        neden = ("Opsiyon/zimni volatilite verisi yok; evrende opsiyon yok." if b in OPS else "VIX/VXX/vol swap veri ve urunu yok; evrende volatilite urunu yok.")
        base.update(on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ", neden_kodu=kod, neden_metni=neden, kanit=f"{k} ; {OZ}#Kapsam disi / veri yok bolumler",
                    kisa_mantik=f"{'Opsiyon' if kod=='opsiyon' else 'Volatilite urunu'} tabanli islem: {ad[:60]}.")
        return base
    if i in D_VERI:
        base.update(on_durum="D_KODLANMADI_NEDENLI", neden_kodu="veri_yok", neden_metni=D_VERI[i], kanit=f"{k} ; {OZ}#Kapsam disi / veri yok bolumler",
                    kisa_mantik=f"{BOLUM_KISA.get(bolum_kok(b), 'Strateji')}: {ad[:70]}.")
        return base
    kap = h_kapsam(b)
    if x["durum"] == "kapsam_disi" and kap:
        base.update(on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ", neden_kodu="kapsam_disi", neden_metni=f"Evren disi: {kap}.",
                    kanit=f"{k} ; {OZ}#Kapsam disi / veri yok bolumler", kisa_mantik=f"{BOLUM_KISA.get(bolum_kok(b), 'Strateji')}: {ad[:70]}.")
        return base
    base.update(on_durum="BELIRSIZ", neden_kodu="kural_belirsiz", neden_metni="Otomatik kural eslesmedi; elle bakilmali.", kanit=k,
                kisa_mantik=ad[:100])
    return base


# --- son1ay
S1_KARAR = {
    1: dict(eslesme="KOD", hedef="dis__son1ay-donchian-adx", ayar_id="son1ay:delta-strategy.py-varsayilan", ayar_dosyasi="stratejiler/dis_ayarlari/dis__son1ay-donchian-adx.json",
            fark="", on_durum="KOD", neden_kodu="", neden_metni="", aile="trend",
            kanit=f"{kr('dis__son1ay-donchian-adx')} ; motor/strateji/dis/d7_son1ay.py (DonchianAdx) ; DURUM.md:338",
            kisa_mantik="Kanal(40) kirilimi + EMA200 yonu + ADX>=20 ile long/short; kanal ve ATR izleyen stop.",
            **{"not": "Kullanici onayli 4 adaydan 1. Ek dis ayar: kaynagin eski 20/10/ATR2.0 varsayilani. Akibet G0'da (WF+karar13+saglamlik gecti, kilit PF 0.94, sette degil)."}),
    2: dict(eslesme="KOD", hedef="dis__son1ay-kanal-20-10", ayar_id="son1ay:H1Sensitivity-10-5 ; son1ay:H1Sensitivity-55-20",
            ayar_dosyasi="stratejiler/dis_ayarlari/dis__son1ay-kanal-20-10.json", fark="", on_durum="KOD", neden_kodu="", neden_metni="", aile="trend",
            kanit=f"{kr('dis__son1ay-kanal-20-10')} ; motor/strateji/dis/d7_son1ay.py (KanalKirilim) ; DURUM.md:338", kisa_mantik="4s kapanis onceki 20 gunun tepesini asarsa long, 10 gunun dibinin altinda cikis; %20 felaket stopu.",
            **{"not": "Onayli aday 2. Spot BTC/EUR yerine USDT perp. Akibet G0: islem sayisi yetersiz."}),
    3: dict(eslesme="KOD", hedef="pf__son1ay_trendrider", ayar_id="", ayar_dosyasi="", fark="", on_durum="KOD", neden_kodu="", neden_metni="", aile="trend",
            kanit=f"{kr('pf__son1ay_trendrider')} ; motor/portfoy/stratejiler/son1ay.py (SonBirAyTrendRider) ; DURUM.md:338",
            kisa_mantik="Gunluk kapanis SMA50 ustundeyse coin dilimini tut, degilse nakit; sabit kademeli dilimler.",
            **{"not": "Onayli aday 3; 'esit' kolu pf__trend_sepet ile ayni (sinif docstring'i), katki kademeli agirlik + %15 stop. Evren BTC/ETH/SOL (kaynak 6 coin). Akibet G0: OOS 15 gun kisa, al-tut alti."}),
    4: dict(eslesme="KOD", hedef="pf__son1ay_e014", ayar_id="", ayar_dosyasi="", fark="", on_durum="KOD", neden_kodu="", neden_metni="", aile="trend",
            kanit=f"{kr('pf__son1ay_e014')} ; motor/portfoy/stratejiler/son1ay.py (SonBirAyE014) ; DURUM.md:338",
            kisa_mantik="SPY/TLT/GLD vekillerinden 25 haftalik getirisi en yuksek olani haftalik tut.",
            **{"not": "Onayli aday 4; kaynakta kod yok, yalniz README kurali; vekil DK_SPX/DK_UST/DK_XAU, mutlak filtre izgarada. Akibet G0: dusus %29.9 karar 24'ten kaldi."}),
    5: dict(eslesme="BENZER", hedef="swing__ma-kesisim", ayar_id="", ayar_dosyasi="",
            fark="Kaynak yalniz BTC gunluk EMA30>EMA90 long / degilse nakit; sinif ema 30/90 destekler ama izgara disi (hizli {5,9,14}, yavas {21,34,50}), short=True varsayilan (kapatilmali), ATR stop eklenir",
            on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var", neden_metni="Karar 'izle': tek enstruman, al-tut altinda; kod yazilmadi, sinif kurali yakin.",
            aile="trend", kanit=f"{S1}:5 ; {S1MD}#5. BTC gunluk EMA30/90 ; {kr('swing__ma-kesisim')} ; motor/strateji/ma_kesisim.py", kisa_mantik="BTC gunluk EMA30 EMA90 ustundeyse tut, degilse USDT nakit.",
            **{"not": "Elle karar: sinif docstring/parametre okundu; dis ayari yok."}),
    6: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kod_incelenmedi", aile="diger",
            neden_metni="Ders kaynagi: 748 stratejilik denetim, kod incelenmedi; 10 gecen katı yeniden taramayi gecemedi, scalp 5m (karar 11).",
            kanit=f"{S1}:6 ; {S1MD}#6. 748 strateji denetimi", kisa_mantik="Acik denetimden gecen 5m kripto stratejileri ve baglam aileleri uzerine bulgular.", **{"not": "Strateji degil, arastirma bulgusu; 10 gecen MIT kod istege bagli incelenebilir."}),
    7: dict(eslesme="BENZER", hedef="pf__kesit_ls", ayar_id="", ayar_dosyasi="",
            fark="Sinif skor='beta' (referans BTC) mod=notr ile ayni fikir; kaynak 90g beta, en dusuk/en yuksek %30 (k=4/13), gunluk dengeleme: lookback 90 izgarada var ama takvim='D' izgarada yok (7/14/30); k=4 izgara disi",
            on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var", neden_metni="Sonuc yok (varsayilan veri sentetik); sinif beta skoru yakin, ayar yazilmamis.",
            aile="diger", kanit=f"{S1}:7 ; {S1MD}#7. Kripto dusuk beta ; {kr('pf__kesit_ls')} ; motor/portfoy/stratejiler/kesit.py (skor beta) ; stratejiler/portfoy_adaylari.csv:41 (awesome BAB, 365g/aylik ayari)",
            kisa_mantik="90 gunluk BTC betasi en dusuk %30 long, en yuksek %30 short, esit agirlik, gunluk dengeleme.", **{"not": "Kaynak sonuc vermiyor; lisans yok."}),
    8: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz", aile="trend",
            neden_metni="Sonuc yok, kilitli test kapali; H-009 haftalik kirilim kuralinin ayrintisi sayfada yok (yalniz SMA20/50+SMA200+%10 stop baseline).",
            kanit=f"{S1}:8 ; {S1MD}#8. H-009", kisa_mantik="1s BTC/ETH/BNB haftalik kirilim rejimi; baseline SMA20/50 + SMA200 filtre + %10 stop.", **{"not": "izle"}),
    9: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz", aile="MR",
            neden_metni="Kural tam yazilmamis (kod ayri klasorde), sonuc yok; scalp 5m/1m karar 11 (scalp kapali).",
            kanit=f"{S1}:9 ; {S1MD}#9. 5m/1m RSI+Bollinger scalp", kisa_mantik="5m/1m RSI ve Bollinger ile scalp, risk/stop mesafesi boyutlu.", **{"not": "izle (scalp)"}),
    10: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="coklu_test", aile="trend",
             neden_metni="Sonuc yok; 2304 konfigurasyon coklu test riski cok yuksek, pencere/tampon degerleri yazilmamis.",
             kanit=f"{S1}:10 ; {S1MD}#10. Kirilim arastirmasi 2304 konfig", kisa_mantik="1s kirilim kanali + ATR tampon, kanal cikisi ve ATR izleyen stop, yalniz long/nakit.", **{"not": "izle; dis__son1ay-kanal-20-10 ve swing__donchian-kirilim ayni aile ama bu satirin kurali ayrintisiz."}),
    11: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz", aile="diger",
             neden_metni="Elendi: kapali kaynak, kural yok, +%1951/+%5569 asiri deger ve hayatta kalma yanliligi.", kanit=f"{S1}:11 ; {S1MD}#Sonucsuz / elenen kayitlar",
             kisa_mantik="4 Freqtrade stratejisi vitrini; kurallar kapali.", **{"not": ""}),
    12: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="G_ML", neden_kodu="ml", aile="diger",
             neden_metni="Ridge (ML) modeli + MA48; ML elenen kategori, sonuc harici raporda.", kanit=f"{S1}:12 ; {S1MD}#Sonucsuz / elenen kayitlar",
             kisa_mantik="BTC spot Ridge model tahmini ile MA48 filtresi.", **{"not": ""}),
    13: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz", aile="diger",
             neden_metni="Elendi: yalniz uc isim (Trend, Mean Reversion, Breakout), kural ve sonuc yok.", kanit=f"{S1}:13 ; {S1MD}#Sonucsuz / elenen kayitlar",
             kisa_mantik="Uc stratejinin adi var, kurali yok.", **{"not": ""}),
    14: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz", aile="diger",
             neden_metni="Izle/elendi: kisisel Cince yazi, sermaye ve pozisyon varsayimi belirsiz, kural alinamadi.", kanit=f"{S1}:14 ; {S1MD}#Sonucsuz / elenen kayitlar",
             kisa_mantik="2011-2026 ETF (159915) yazisi; DD %55.5, kural ayrintisiz.", **{"not": ""}),
    15: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="arac_sablon", aile="diger",
             neden_metni="Strateji degil: Freqtrade 2026.10 surum notlari (arac).", kanit=f"{S1}:15 ; {S1MD}#Sonucsuz / elenen kayitlar",
             kisa_mantik="Freqtrade surumu; parametre ve --export-params degisikligi.", **{"not": "Mevcut kodu etkileyip etkilemedigi ayrica kontrol edilmeli (md)."}),
    16: dict(eslesme="YOK", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="okunmadi", aile="diger",
             neden_metni="Listedeki 6 depo (ai_trader, regime-trading-bot, crypto-bot, Trade, trading-agents, quant-alpha-desktop) okunmadi; izin verilirse okunabilir.",
             kanit=f"{S1}:16 ; {S1MD}#Sonucsuz / elenen kayitlar", kisa_mantik="Okunmayan alti depo; icerikleri bilinmiyor.", **{"not": "6 depo tek satir; ayrica kendi karari yok (okunmadi). Bir tanesi LLM veto, biri NSE."}),
}


def main():
    kk = list(csv.DictReader(open(KOK / KK, encoding="utf-8")))
    s1 = list(csv.DictReader(open(KOK / S1, encoding="utf-8")))
    cols = ["ham_id", "kaynak_id", "kaynak_satir_no", "kaynaktaki_ad", "kisa_mantik", "aile", "eslesme", "hedef", "ayar_id", "ayar_dosyasi", "fark",
            "on_durum", "neden_kodu", "neden_metni", "kanit", "not"]
    rows = []
    elle_idx = {}
    for n, x in enumerate(kk, 1):
        if n in E:
            d = dict(E[n])
            elle_idx[f"Q001:{n}"] = d
        else:
            d = varsayilan(n, x)
        d["kisa_mantik"] = d["kisa_mantik"][:160]
        d.update(ham_id=f"Q001:{n}", kaynak_id="Q001", kaynak_satir_no=n, kaynaktaki_ad=f"{x['bolum']} {x['ad']}"[:120])
        rows.append(d)
    for n, x in enumerate(s1, 1):
        d = dict(S1_KARAR[n])
        d.update(ham_id=f"Q004:{n}", kaynak_id="Q004", kaynak_satir_no=n, kaynaktaki_ad=x["ad"][:120])
        d["kisa_mantik"] = d["kisa_mantik"][:160]
        rows.append(d)
        elle_idx[f"Q004:{n}"] = S1_KARAR[n]
    with open(ARA / "G5_151_SON1AY_ham.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for d in rows:
            w.writerow({c: d.get(c, "") for c in cols})
    with open(ARA / "G5_151_SON1AY_elle_kararlar.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ham_id", "eslesme", "hedef", "ayar_id", "on_durum", "neden_kodu", "fark", "kanit", "not"])
        w.writeheader()
        for h, d in elle_idx.items():
            w.writerow({"ham_id": h, **{c: d.get(c, "") for c in ["eslesme", "hedef", "ayar_id", "on_durum", "neden_kodu", "fark", "kanit", "not"]}})
    print(len(rows), collections.Counter(r["on_durum"] for r in rows), collections.Counter(r["eslesme"] for r in rows))
    print([r["ham_id"] for r in rows if r["on_durum"] == "BELIRSIZ"])


if __name__ == "__main__":
    main()
