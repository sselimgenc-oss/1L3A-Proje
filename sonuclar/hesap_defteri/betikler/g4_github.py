#!/usr/bin/env python3
"""G4_GITHUB hesap defteri: 1198 GitHub tarama satırı -> ham satır + eşleme (salt okunur; yalnız ara/ altına yazar).

Girdi : stratejiler/ek_kaynaklar/github_g1..g7_*.csv, kodlama_kuyrugu_github.csv, stratejiler/kodlama_github_d11f..j.csv,
        kodlama_2026-11-07_*.csv (yeni__ ad çözümü), ayarlar_d11j_ek.json, dis_ayarlari/*.json, kart_ayarlari/*.json,
        sonuclar/hesap_defteri/ara/kod_kaydi.csv, sonuclar/evren/2017_gelistirme/wf_evren.csv
Çıktı : sonuclar/hesap_defteri/ara/G4_GITHUB_ham.csv  (+ NOTLAR üretimi için G4_GITHUB_ozet.json)
Elle kararlar (kısmi aileler): ara/G4_GITHUB_elle_kararlar.csv (bu betik de yazar).
Çalıştırma: python3 sonuclar/hesap_defteri/betikler/g4_github.py   (kök dizinden)
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[3]
os.chdir(KOK)
sys.path.insert(0, str(KOK))
EK = "stratejiler/ek_kaynaklar/"
ARA = Path("sonuclar/hesap_defteri/ara")
GRUP_ID = {"g1": "H001", "g2": "H002", "g3": "H003", "g4": "H004", "g5": "H005", "g6": "H006", "g7": "H007"}

# --------------------------------------------------------------------------- yükleme
dosyalar = sorted(glob.glob(EK + "github_g?_*.csv"))
frames = []
for f in dosyalar:
    d = pd.read_csv(f, dtype=str).fillna("")
    d["gdosya"] = os.path.basename(f)[:-4]          # github_g1_freqtrade
    d["g"] = d["gdosya"].str[7:9]                   # g1
    d["no"] = range(1, len(d) + 1)
    d["yol"] = f
    frames.append(d)
A = pd.concat(frames, ignore_index=True)

kod = pd.read_csv(ARA / "kod_kaydi.csv")
KODSET = set(kod.ad)
KODDOSYA = dict(zip(kod.ad, kod.dosya))
KODSINIF = dict(zip(kod.ad, kod.sinif))

Q = pd.read_csv(EK + "kodlama_kuyrugu_github.csv", dtype=str).fillna("")
QI = Q.set_index("yeni_aile")

D11 = {}   # yeni_aile -> dict
for n in "fghi":
    x = pd.read_csv(f"stratejiler/kodlama_github_d11{n}.csv", dtype=str).fillna("")
    for _, r in x.iterrows():
        D11[r.yeni_aile] = dict(ad=r.yeni_strateji_adi, durum=r.durum, gerekce=r.gerekce, dosya=f"stratejiler/kodlama_github_d11{n}.csv")
D11J = {}
xj = pd.read_csv("stratejiler/kodlama_github_d11j.csv", dtype=str).fillna("")
for _, r in xj.iterrows():
    D11J["yeni__" + r.yeni_aile] = dict(hedef=r.hedef_sinif, degisiklik=r.degisiklik, gerekce=r.gerekce)

# eski kodlama dosyaları: yeni__ ad çözümü
ESKI = {}
for f in sorted(glob.glob("stratejiler/kodlama_2026-11-07_*.csv")):
    x = pd.read_csv(f, dtype=str).fillna("")
    if "yeni_aile" not in x.columns or "yeni_strateji_adi" not in x.columns:
        continue
    for _, r in x.iterrows():
        ESKI[r.yeni_aile] = dict(ad=r.yeni_strateji_adi, durum=r.durum, gerekce=r.gerekce, dosya=f)

# ayar dizini
AYARLAR = []     # (hedef, ayar_id, kaynak_dosya_metni, yol)
for f in glob.glob("stratejiler/dis_ayarlari/*.json"):
    for x in json.load(open(f, encoding="utf-8")):
        AYARLAR.append((os.path.basename(f)[:-5], x["dis_id"], x["kaynak_dosya"].lower(), f))
EKJ = json.load(open("stratejiler/ayarlar_d11j_ek.json", encoding="utf-8"))
EKJ_IDS = {x["ayar_id"] for x in EKJ}
EKJ_HEDEF = {x["ayar_id"]: x["hedef"] for x in EKJ}

# wf_evren
WF = pd.read_csv("sonuclar/evren/2017_gelistirme/wf_evren.csv")
WF["_s"] = WF["secimler"].astype(str) + "|" + WF["en_sik_ayar"].astype(str)

# sınıf kaynak metinleri / özellikleri
_src = {}


def kaynak_metni(yol):
    if yol not in _src:
        _src[yol] = open(yol, encoding="utf-8").read().lower() if yol and os.path.exists(yol) else ""
    return _src[yol]


_SIN = None
_PF = None


def sinif_bilgi(ad):
    """(varsayilan, izgara) - motor/strateji kaydından ya da portföy kaydından (salt okunur import)."""
    global _SIN, _PF
    try:
        if ad.startswith("pf__"):
            if _PF is None:
                from motor.portfoy.stratejiler import tum_portfoy_stratejileri
                _PF = tum_portfoy_stratejileri()
            c = _PF[ad]
        else:
            if _SIN is None:
                from motor.strateji import kayit
                _SIN = kayit.tum_stratejiler()
            c = _SIN[ad]
        return dict(c.varsayilan_parametreler), dict(c.parametre_izgarasi)
    except Exception:
        return {}, {}


def kisa_par(ad, n=7):
    v, iz = sinif_bilgi(ad)
    ks = list(v.items())[:n]
    return "varsayılan{" + ", ".join(f"{k}={w}" for k, w in ks) + "}; ızgara anahtarları=" + ",".join(iz.keys())


# --------------------------------------------------------------------------- yardımcılar
def aile_of(kat):
    if kat in ("trend_takip", "momentum", "kirilim"):
        return "trend"
    if kat == "ortalamaya_donus":
        return "MR"
    return "diger"


def kisa(s, n):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def tok_norm(s):
    return s.replace(";", ",")


# kuyruk token eşlemesi (yalnız durum=yeni satırlar)
TOKEN2FAM = defaultdict(list)
for _, r in Q.iterrows():
    for t in r.kaynak_satirlar.split(";"):
        TOKEN2FAM[t].append(r.yeni_aile)
TOK_KULLANILAN = Counter()


def kuyruk_aile(r):
    for adx in (r.ad, tok_norm(r.ad)):
        t = f"{r.gdosya}:{adx}"
        if t in TOKEN2FAM:
            TOK_KULLANILAN[t] += 1
            return TOKEN2FAM[t][0], t
    return None, None


# --------------------------------------------------------------------------- elle kararlar (kısmi aileler)
# anahtar: (g, ad'ın başlangıcı)  ->  (eslesme, on_durum, neden_kodu, neden_metni, hedef, kanit_eki)
ELLE = {}


def elle(g, ad_basi, eslesme, on_durum, neden_kodu, metin, hedef="", kanit=""):
    ELLE[(g, ad_basi)] = (eslesme, on_durum, neden_kodu, metin, hedef, kanit)


D = "D_KODLANMADI_NEDENLI"
elle("g7", "RSRS rotasyonu", "YOK", D, "kod_yok", "tek-sembol RSRS kodlandı; rotasyon sürümü kodlanmadı (pf__rotasyon'a skor='rsrs' önerisi uygulanmadı)", "", "stratejiler/kodlama_github_d11f.csv:yeni__rsrs-egim-esigi")
elle("g2", "RSI_BB_ADX_Peak", "YOK", D, "kod_yok", "BB/ADX varyantları kodlanmadı (d11g sınıf docstring: BB/Combination/STC varyantları KODLANMADI)", "", "motor/strateji/dis/d11g_github.py (dis__rsi-boga-ayi-rejim docstring)")
elle("g2", "Combination-1/2/3", "YOK", D, "kod_yok", "Combination varyantları kodlanmadı (d11g docstring)", "", "motor/strateji/dis/d11g_github.py (dis__rsi-boga-ayi-rejim docstring)")
elle("g2", "STC_Bull_Bear_Adx", "YOK", D, "kod_yok", "STC varyantı kodlanmadı (d11g docstring)", "", "motor/strateji/dis/d11g_github.py (dis__rsi-boga-ayi-rejim docstring)")
elle("g2", "RSI_BULL_BEAR_ADX", "BENZER", D, "benzer_var", "çıplak 3 rejimli RSI kodlandı; ADX(3) eşik kaydırması / stop / pingpong varyantları kodlanmadı", "dis__rsi-boga-ayi-rejim", "motor/strateji/dis/d11g_github.py (docstring)")
elle("g2", "saichovsky", "YOK", D, "veri_yok", "'son işlem fiyatı' (işlem geçmişi) gerekir, kodlanmadı (dis__tepeden-dusus-dip docstring)", "", "motor/strateji/dis/d11g_github.py (dis__tepeden-dusus-dip docstring)")
elle("g5", "AFAOSMD", "YOK", D, "kural_belirsiz", "EA'ya özgü ters sinyal + Average Force; kodlanmadı (dis__andean-osilator docstring)", "", "motor/strateji/dis/d11g_github.py (dis__andean-osilator docstring)")
elle("g5", "DHLAOS", "YOK", D, "kural_belirsiz", "Günlük yüksek/düşük çizgileri + ters sinyal EA'ya özgü; kodlanmadı (dis__andean-osilator docstring)", "", "motor/strateji/dis/d11g_github.py (dis__andean-osilator docstring)")
elle("g2", "RSI-PHA", "YOK", D, "kural_belirsiz", "EMA koşulları kaynakta eksik, kodlanmadı (dis__asiri-bolge-osilator-kesisimi docstring)", "", "motor/strateji/dis/d11g_github.py (dis__asiri-bolge-osilator-kesisimi docstring)")
elle("g2", "L1-Scalping / gekko-custom", "BENZER", D, "benzer_var", "3 MACD histogramı + EMA dizilimi varyantı kodlanmadı; docstring dizilim için dis__ema-serit-yelpaze diyor (o sınıf açılmadı: doğrulanmadı)", "dis__ema-serit-yelpaze", "motor/strateji/dis/d11h_github.py (dis__cok-gosterge-teyit docstring)")
elle("g5", "EA31337 Retracement", "YOK", D, "kural_belirsiz", "en yakın pivota uzaklık oranı eşiği pip cinsinden; ATLANDI (dis__ma-gunluk-pivot docstring)", "", "motor/strateji/dis/d11h_github.py (dis__ma-gunluk-pivot docstring)")
elle("g1", "BBMod: r_deadfish", "YOK", D, "kural_belirsiz", "özet kesik; r_deadfish kolu kodlanmadı (dis__ewo-ema-ofset docstring)", "", "motor/strateji/dis/d11i_github.py (dis__ewo-ema-ofset docstring)")
elle("g1", "BBMod: gumbo", "YOK", D, "kural_belirsiz", "T3 tanımı belirsiz; gumbo kolu kodlanmadı (dis__ewo-ema-ofset docstring)", "", "motor/strateji/dis/d11i_github.py (dis__ewo-ema-ofset docstring)")
elle("g2", "Strat (tik momentum)", "YOK", D, "kapsam_disi", "0.01% tik eşiği 15m'de gürültü; kodlanmadı (dis__getiri-oynaklik-momentum docstring)", "", "motor/strateji/dis/d11i_github.py (dis__getiri-oynaklik-momentum docstring)")
# gosterge-egim-esik: GOSTERGELER (21) dışında kalanlar
for ad_ in ("EA31337 ASI", "EA31337 BWMFI", "EA31337 SAWA", "EA31337 ElliottWave", "EA31337 Oscillator", "EA31337 Oscillator Multi",
            "EA31337 Oscillator Overlay", "EA31337 Oscillator Trend"):
    elle("g5", ad_, "YOK", D, "kod_yok", "gösterge dis__gosterge-egim-esik.GOSTERGELER (21) listesinde yok; sınıfa alınmadı (d11h gerekçe: ASI/SAWA/BWMFI/genel osilatör hariç)", "", "motor/strateji/dis/d11h_github.py (GOSTERGELER); stratejiler/kodlama_github_d11h.csv:yeni__gosterge-egim-yuzde-esik")

# d11j: ayar eşlemesi (token -> ayar son ekleri) ; yoksa D kararı
# anahtar: (g, ad_basi) -> ("AYAR", [ayar son ekleri]) | ("D", neden_kodu, metin) | ("H", neden_kodu, metin)
J = {}
fam = lambda s: "d11j:" + s  # noqa: E731
J[("g2", "ta_srsi_bollinger")] = ("AYAR", "bant-dokunusu-stokastik-onayi", ["stochrsi"])
J[("g2", "ta_stoch_bollinger")] = ("AYAR", "bant-dokunusu-stokastik-onayi", ["stokastik"])
J[("g3", "BBMomentumEvaluator")] = ("AYAR", "bant-dokunusu-stokastik-onayi", ["stokastik", "stochrsi"])
J[("g2", "ta_trix")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["trix14_sma9", "trix30_sifir"])
J[("g2", "ta_ultosc")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["uo_esik65"])
J[("g4", "EMV")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["emv14_sifir"])
J[("g5", "Price Volume Trend")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["pvt_sma21"])
J[("g5", "MFI / sinyal")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["mfi14_ema9"])
J[("g5", "TRIX / sinyal")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["trix14_sma9", "trix30_sifir"])
J[("g5", "TSI / sinyal")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["tsi25_13_ema13"])
J[("g5", "Ehlers Decycler")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["decycler_sifir"])
J[("g5", "Ehlers Triple Delay-Line")] = ("D", "kural_belirsiz", "Triple Delay-Line Detrender kodlanmadı: tanım yok (d11j gerekçe)")
J[("g5", "Klinger Volume Oscillator")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["kvo34_55_ema13"])
J[("g5", "OBV / sinyal")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["obv_sma21"])
J[("g5", "Accumulation/Distribution")] = ("AYAR", "gosterge-sinyal-sifir-kesisimi", ["ad_sma21"])
J[("g3", "Risk ayarlı momentum + 3 bar")] = ("AYAR", "kesit-skor-kombinasyonu-momentum-carry", ["kombine_07_03"])
J[("g3", "Momentum + fonlama taşıma")] = ("D", "veri_yok", "carry (fonlama z-skoru) KODLANMADI: pf arayüzü fonlama verisi taşımıyor (d11j gerekçe)")
J[("g2", "STC / SchaffTrendCycle")] = ("AYAR", "osilator-esik-donusu-gosterge-modlari", ["stc_25_75"])
J[("g2", "TSI (Gekko)")] = ("AYAR", "osilator-esik-donusu-gosterge-modlari", ["tsi13_25"])
J[("g2", "UO (Ultimate")] = ("AYAR", "osilator-esik-donusu-gosterge-modlari", ["uo_30_70"])
J[("g5", "Schaff Trend Cycle")] = ("AYAR", "osilator-esik-donusu-gosterge-modlari", ["stc_25_75"])
J[("g5", "EA31337 MFI")] = ("AYAR", "osilator-esik-donusu-gosterge-modlari", ["mfi22_30"])
J[("g5", "EA31337 Oscillator Range")] = ("D", "kod_yok", "'Oscillator Range' (orta çizgi altı yükselen) kodlanmadı (d11j gerekçe)")
J[("g5", "EA31337 WPR")] = ("AYAR", "osilator-esik-donusu-gosterge-modlari", ["wpr18_90"])
J[("g7", "Triple RSI aylık rotasyon")] = ("AYAR", "rotasyon-skor-modlari-triplersi-bb", ["triple_rsi_hacim_top5"])
J[("g7", "Çoklu Bollinger üst bant")] = ("AYAR", "rotasyon-skor-modlari-triplersi-bb", ["bb_uzaklik_k1"])
J[("g2", "ATR_ADX")] = ("D", "kural_belirsiz", "ATR_ADX çarpan formülü belirsiz, kodlanmadı (d11j gerekçe)")
J[("g2", "ATR_MA")] = ("AYAR", "atr-chandelier-nrtr-donus", ["ha_atr_ma"])
J[("g5", "CEZLSMA")] = ("AYAR", "atr-chandelier-nrtr-donus", ["chandelier22_3"])
J[("g5", "Chandelier Exit")] = ("AYAR", "atr-chandelier-nrtr-donus", ["chandelier22_3"])
J[("g5", "NRTR")] = ("AYAR", "atr-chandelier-nrtr-donus", ["nrtr_2yuzde"])
J[("g5", "EA31337 ATR MA Trend")] = ("AYAR", "atr-chandelier-nrtr-donus", ["ha_atr_ma"])
J[("g5", "EA31337 Bands")] = ("AYAR", "bant-dokunusu-orta-cizgi-egimi", ["bb24"])
J[("g5", "EA31337 Envelopes")] = ("AYAR", "bant-dokunusu-orta-cizgi-egimi", ["envelope"])
J[("g5", "EA31337 SVE Bollinger")] = ("D", "kod_yok", "SVE özel bandı kodlanmadı (d11j gerekçe)")
J[("g5", "EA31337 TMAT SVEBB")] = ("D", "kod_yok", "SVE özel bandı kodlanmadı (d11j gerekçe)")
J[("g5", "EA31337 TMA True")] = ("AYAR", "bant-dokunusu-orta-cizgi-egimi", ["tma"])
J[("g2", "ichimoku_score")] = ("AYAR", "ichimoku-puan-skoru", ["skor50_49"])
J[("g2", "ehlers_mama")] = ("AYAR", "mama-fama-itrend-cma-ma-turleri", ["mama_fama"])
J[("g2", "ehlers_trend")] = ("AYAR", "mama-fama-itrend-cma-ma-turleri", ["itrend"])
J[("g5", "Corrected Moving Average")] = ("AYAR", "mama-fama-itrend-cma-ma-turleri", ["cma_35"])
J[("g5", "EA31337 Oscillator Cross Shift")] = ("AYAR", "osilator-cizgi-kesisimi-genel", ["adx_di_kaydirma10"])
J[("g5", "EA31337 Oscillator Cross Timeframe")] = ("D", "kod_yok", "farklı zaman diliminden osilatör (H6) kodlanmadı (d11j gerekçe)")
J[("g5", "EA31337 Oscillator Cross Zero")] = ("D", "kod_yok", "bu kaynağın (adx_di sıfır modu) ayar kaydı yok; 'hızlı çizgi yükseliyor, yüzde artış>seviye' koşulu da yok (d11j gerekçe)")
J[("g5", "EA31337 Oscillator Cross")] = ("AYAR", "osilator-cizgi-kesisimi-genel", ["adx_di"])
J[("g4", "Edge: rejim kayması")] = ("AYAR", "piyasa-rejim-filtreleri-genislik-ftd-dagitim", ["genislik_hisse"])
J[("g4", "Follow-Through Day")] = ("AYAR", "piyasa-rejim-filtreleri-genislik-ftd-dagitim", ["ftd_spx"])
J[("g4", "IBD dağıtım günü")] = ("AYAR", "piyasa-rejim-filtreleri-genislik-ftd-dagitim", ["dagitim_spx"])
J[("g4", "Kripto rejim analizcisi")] = ("D", "veri_yok", "dominans/funding/alt genişliği bileşenleri veri_yok, atıldı (d11j gerekçe)")
J[("g3", "Hiyerarşik Risk Paritesi")] = ("AYAR", "portfoy-agirlik-semalari-hrp-minvar-mvo", ["hrp"])
J[("g3", "Long-only minimum varyans")] = ("AYAR", "portfoy-agirlik-semalari-hrp-minvar-mvo", ["min_var"])
J[("g4", "Kümeleme ile çeşitlendirilmiş")] = ("D", "kod_yok", "korelasyon kümeleme temsilcisi kodlanmadı (d11j gerekçe)")
J[("g4", "Ortalama-varyans ve Sharpe")] = ("AYAR", "portfoy-agirlik-semalari-hrp-minvar-mvo", ["mvo"])
J[("g2", "rsidyn")] = ("AYAR", "rsi-dinamik-esik-tepe-dip-medyani", ["rsidyn"])
J[("g2", "RSI_Autotune")] = ("D", "kural_belirsiz", "RSI_Autotune kodlanmadı (d11j gerekçe)")
J[("g5", "Self-Adjusting RSI")] = ("AYAR", "rsi-uyarlanir-esik-ve-periyot", ["uyarlanir_std"])
J[("g7", "Adaptif RSI")] = ("AYAR", "rsi-uyarlanir-esik-ve-periyot", ["arsi_8_28"])
J[("g7", "AlphaRSI Pro")] = ("AYAR", "rsi-uyarlanir-esik-ve-periyot", ["alpharsi_atr"])
J[("g7", "Hibrit AlphaRSI")] = ("AYAR", "rsi-uyarlanir-esik-ve-periyot", ["alpharsi_atr"])
J[("g2", "bryanbeck")] = ("AYAR", "ardisik-mum-degisimi-al-sat", ["3_2"])
J[("g2", "AtrRsiStrategy")] = ("AYAR", "atr-rsi-momentum-yeni-periyot", ["atr22_rsi5"])
J[("g2", "BollChannelStrategy")] = ("AYAR", "bant-ust-alt-kirilim-stop-giris", ["boll18_3_4_cci"])
J[("g2", "KingKeltnerStrategy")] = ("AYAR", "bant-ust-alt-kirilim-stop-giris", ["keltner11_1_6"])
J[("g2", "Martingale V1 giris")] = ("AYAR", "bant-ust-alt-kirilim-stop-giris", ["boll18_3_4_cci", "keltner11_1_6", "trend_bollinger_100_0_5"])
J[("g4", "Bollinger bandı dışı kapanış trendi")] = ("AYAR", "bant-ust-alt-kirilim-stop-giris", ["trend_bollinger_100_0_5", "boll18_3_4_cci", "keltner11_1_6"])
J[("g4", "Trend Bollinger bandı")] = ("AYAR", "bant-ust-alt-kirilim-stop-giris", ["trend_bollinger_100_0_5"])
J[("g4", "Güçlü hisse + dinamik MA")] = ("AYAR", "guclu-hisse-dinamik-ma-egimi", ["stop4_8"])
J[("g1", "NFI: Pump/Dump")] = ("AYAR", "hacim-patlamali-48-mum-zirve-kirilimi", ["nfi_pump_dump"])
J[("g2", "HL_Scalp")] = ("AYAR", "kapanis-kanali-min-dip-alim", ["pencere15_zirve_cikis"])
J[("g2", "HL (gekko-strat-hl")] = ("AYAR", "kapanis-kanali-min-dip-alim", ["pencere15_zirve_cikis"])
J[("g2", "customPivotJbk")] = ("AYAR", "pivot-onayli-ters-stop", ["sol4_sag2_olusum"])
J[("g2", "renko")] = ("AYAR", "renko-tugla-donusu-basit", ["basit_donus"])
J[("g2", "trailing-trade giris kapilari")] = ("AYAR", "rsi-zskor-ma-sapma-giris-kapisi", ["z2_rsi30"])
J[("g3", "DoubleMovingAverageTrendEvaluator")] = ("AYAR", "sma2-sapma-skoru", ["sma2_sma5"])
J[("g5", "Didi Index")] = ("AYAR", "sma2-sapma-skoru", ["didi_sma3_sma20"])
J[("g5", "EA31337 Pivot")] = ("AYAR", "camarilla-bolgesi-ea31337", ["s1_s2", "s2_s3"])
J[("g3", "Fonlama oranı pozitifse short")] = ("AYAR", "funding-pozitif-short", ["esik0_short"])
J[("g5", "EA31337 HeikenAshi")] = ("AYAR", "heiken-ashi-ea31337", ["aralik_yuzde"])
J[("g6", "ETF gün içi momentumu")] = ("AYAR", "ilk-30dk-son-30dk-r12", ["r1_gece", "r1_r12"])
J[("g1", "NFI: Çöküş sonrası sıçrama")] = ("AYAR", "kapitulasyon-hacimli-dip", ["nfi_capitulation"])
J[("g4", "Edge: panic_reversal")] = ("AYAR", "kapitulasyon-hacimli-dip", ["edge_panic_reversal"])
J[("g1", "NFI: Yutan mum devamı")] = ("AYAR", "marubozu-yutan-mum-devam", ["yutan_devam"])
J[("g1", "NFI: Marubozu momentum")] = ("AYAR", "marubozu-yutan-mum-devam", ["marubozu_devam"])
J[("g5", "EA31337 Oscillator Divergence")] = ("AYAR", "osilator-diverjansi-ea31337", ["cci_4bar"])
J[("g1", "BBMod: Squeeze momentum")] = ("AYAR", "sqz-momentum-dip-donusu-ewo", ["nfi_ewo_wr"])
J[("g1", "NFI (X v11/Next): Squeeze")] = ("AYAR", "sqz-momentum-dip-donusu-ewo", ["nfi_ewo_wr"])
J[("g5", "3MAF")] = ("AYAR", "uc-ema-dizilim-geri-cekilme-fraktal", ["3maf"])
J[("g6", "Long-only çift işlemi KO/PEP")] = ("AYAR", "uzun-yonlu-cift-dunku-getiri", ["dunku_getiri"])
J[("g4", "Tongdaxin yukarı boşluk")] = ("H", "seans_gap", "aday SEÇİCİ (tarama): giriş/çıkış/stop kuralı yok; tam boşluk 7/24 kriptoda neredeyse hiç oluşmaz (d11j gerekçe; hedef swing__gap-devam: kurala_dokulemez)")


def j_bul(g, ad, fam_adi):
    """d11j satırı için J eşlemesi (ad başlangıcı, aile uyumlu en uzun anahtar)."""
    en = None
    for (gg, bas), v in J.items():
        if gg == g and ad.startswith(bas) and v[1 if v[0] == "AYAR" else 0] is not None:
            if v[0] == "AYAR" and v[1] != fam_adi:
                continue
            if en is None or len(bas) > len(en[0]):
                en = (bas, v)
    return en[1] if en else None


# ma-kesişim ESDEGER (elle doğrulanmış: periyot çifti ayar kümesinde var; sınıf kodu motor/strateji/ma_kesisim.py açıldı)
MA_ESD = {
    ("g3", 1): ("kural:kurallar:MA5/20 long", "SMA5/20; L/S; sınıf ATR stop ekler (kaynak stopsuz)"),
    ("g3", 19): ("kural:kurallar:MA5/20 long", "SMA5/20 long-only (short=False)"),
    ("g4", 141): ("kural:kurallar:MA5/20 long", "MA5/20 kesişim"),
    ("g7", 3): ("kural:kurallar:EMA10/20 kesişim + %2 stop", "EMA10/20 + %2 stop (aynı kural ayar kaydında var)"),
    ("g7", 1): ("kural:kurallar:SMA 10/20 dur-ve-dön; SMA 10/30 long-short (dön); SMA 13/50 kesişim long; SMA 15/50 kesişim long", "10/20,10/30,15/50,13/50 hepsi ayar kümesinde"),
    ("g7", 12): ("kural:kurallar:SMA 10/20 dur-ve-dön", "SMA 10/20 dön"),
    ("g7", 2): ("kural:kurallar:Kapanış SMA10 long; Kapanış SMA15 long; Kapanış SMA30 long", "kapanış-SMA kesişimi = hizli=1"),
    ("g7", 28): ("kural:kurallar:Kapanış SMA15 long", "kapanış SMA15 long"),
    ("g6", 287): ("kural:kurallar:TechIndicator SMA2 (20/50) L/S", "SMA20/50 L/S (durum yerine kesişim; ilk kesişimden sonra aynı pozisyon)"),
    ("g6", 330): ("kural:kurallar:SMA 10/30 kesişim long", "SMA10/30 long-only"),
}

# --------------------------------------------------------------------------- neden eşlemeleri
YASAK_KOD = [("martingale", "martingale"), ("dca", "dca"), ("ortalama d", "ortalama_dusurme"), ("ortalama dusur", "ortalama_dusurme"),
             ("averaj", "ortalama_dusurme"), ("stopsuz", "stopsuz_grid"), ("hedge", "martingale"), ("ızgara", "stopsuz_grid"), ("izgara", "stopsuz_grid")]


def yasak_neden(txt):
    t = txt.lower()
    for k, v in YASAK_KOD:
        if k in t:
            return v
    return "stopsuz_grid"


def veri_yok_neden(txt, kat):
    t = txt.lower()
    if "kural_metni_yok" in t or t.strip() == "":
        return "D", "kural_belirsiz", "veri_yok denmiş ama kaynakta kural metni de yok"
    if "opsiyon" in t:
        return "H", "opsiyon", "opsiyon verisi gerekir"
    if "emir defteri" in t or "tick" in t or "orderbook" in t:
        return "H", "orderbook", "emir defteri / tick verisi gerekir (OHLCV evreninde yok)"
    if "borsa" in t or "arbitraj" in t:
        return "H", "arbitraj", "çok borsa verisi / arbitraj"
    if any(k in t for k in ("temel", "mali tablo", "pazar değeri", "roe", "kazanç", "龙虎榜", "üyelik")):
        return "H", "hisse_kesitsel", "hisse temel/kesit verisi gerekir"
    if "vade yapısı" in t or "faiz" in t and "fx" in t:
        return "H", "veri_yok", "vadeli vade yapısı / FX faiz verisi yok"
    if "tahmin piyasası" in t or "polymarket" in t:
        return "H", "veri_yok", "tahmin piyasası verisi (evrende yok)"
    if "haber" in t or "makro" in t or "sosyal" in t or "dış" in t:
        return "H", "veri_yok", "haber/makro/dış veri gerekir"
    if "fonlama" in t or "funding" in t:
        return "D", "veri_yok", "fonlama/OI/likidasyon verisi gerekir (kaynak satırda 'veri_yok')"
    return "D", "veri_yok", "gerekli veri evrende yok (kaynak satır durumu: veri_yok)"


def kural_yok_neden(txt):
    t = txt.lower()
    if "lookahead" in t:
        return "lookahead", "lookahead (tüm veri min/max normalize)"
    if any(k in t for k in ("strateji değil", "altyapi", "yalniz gosterge", "iskelet", "bildirim", "şablon", "sablon", "tavsiye", "hedef fonksiyonu", "kod degil", "tahsis")):
        return "arac_sablon", "strateji değil: araç/şablon/iskelet"
    if "kod yarim" in t or "kod_yok" in t:
        return "kod_yok", "kod çalışmıyor / gösterge dosyası"
    if "elle" in t or "kullanici girdili" in t or "mutlak fiyat" in t:
        return "kapsam_disi", "elle girilen / mutlak seviye; evrene taşınamaz"
    return "kural_belirsiz", "kaynakta işlem kuralı metni yok"


def ayar_ara(hedef, r):
    """dis_ayarlari içinde satırın adı/dosya adıyla anılan ayarlar."""
    stem = os.path.splitext(os.path.basename(r.dosya.split(" ")[0].split(";")[0]))[0].lower()
    nm = r.ad.lower().split(" (")[0]
    sonuc = []
    for h, i, k, y in AYARLAR:
        if h != hedef or not k:
            continue
        if (len(stem) >= 6 and stem not in ("strategy", "sample") and stem in k) or (len(nm) >= 8 and nm in k):
            sonuc.append((i, y))
    return sonuc


# --------------------------------------------------------------------------- satır üretimi
def d11j_not(hedef, ayar_ids, fam_adi):
    """AYAR satırı için araştırma hattı notu (kanıtlı)."""
    parcalar = []
    wf = WF[WF.strateji == hedef]
    ek_ids = [i for i in ayar_ids if i in EKJ_IDS]
    dis_ids = [i for i in ayar_ids if i not in EKJ_IDS]
    for i in dis_ids:
        n = int(WF["_s"].str.contains("dis:" + i, regex=False).sum())
        if len(wf):
            parcalar.append(f"koşuldu: {hedef} wf_evren.csv'de {len(wf)} satır (n_aday<= {int(wf.n_aday.max())}); dis:{i} seçimlerde "
                            + (f"{n} satırda geçiyor" if n else "geçmiyor (aday ama seçilmedi)"))
        else:
            parcalar.append(f"{hedef} wf_evren.csv'de yok")
    for i in ek_ids:
        v, iz = sinif_bilgi(hedef)
        parcalar.append("araştırma hattında okunmuyor → koşulmadı (kanıt: ayarlar_d11j_ek.json yalnız testler/test_d11j_modlar.py:253'te okunuyor; "
                        "motor/arastirma/tarama.py::_ayar_listesi ve wf_tarama.aday_listesi yalnız varsayılan+kart+dis+izgara; "
                        "wf_portfoy.aday_listesi (267-278) yalnız BAGLAMA+varsayılan+izgara; "
                        f"{hedef} parametre_izgarasi={list(iz.keys())} mod anahtarı içermiyor; wf_evren.csv'de 'd11j:{fam_adi}' geçmiyor)")
    return " | ".join(parcalar)


satirlar = []
kanit_ozet = []
fam_sonuc = defaultdict(list)       # kuyruk ailesi -> [(eslesme,on_durum)]
bulgu = []

onceki_ham = {}   # (g, ad) -> ilk ham_id (TEKRAR için)

for _, r in A.iterrows():
    hid = f"{GRUP_ID[r.g]}:{r.no}"
    row = dict(ham_id=hid, kaynak_id=GRUP_ID[r.g], kaynak_satir_no=r.no, kaynaktaki_ad=kisa(r.ad, 120), kisa_mantik=kisa(r.mekanik_ozet, 160),
               aile=aile_of(r.kategori), eslesme="", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="", neden_kodu="", neden_metni="", kanit="", **{"not": ""})
    kaynak_kanit = f"{r.yol}:{r.no + 1}"           # CSV satırı (başlık 1. satır)
    durum = r.durum
    tip = durum.split(":")[0]
    anahtar = (r.g, r.ad)

    # --- TEKRAR (aynı makale başlığı, README + paper_meta.json)
    if anahtar in onceki_ham and r.durum == "kural_yok":
        row.update(eslesme="TEKRAR", hedef=onceki_ham[anahtar], on_durum="TEKRAR", kanit=kaynak_kanit,
                   **{"not": "aynı makale başlığı: README.md bölümü + scripts/paper_meta.json; ikisinde de kural metni yok"})
        satirlar.append(row)
        continue
    onceki_ham.setdefault(anahtar, hid)

    # --- durum=yeni -> kuyruk
    if durum == "yeni":
        fa, tok = kuyruk_aile(r)
        if fa is None:
            row.update(eslesme="YOK", on_durum="E_KODLANMADI_NEDENSIZ", kanit=kaynak_kanit, **{"not": "kuyrukta eşleşme yok"})
            bulgu.append(f"{hid} kuyrukta bulunamadı")
            satirlar.append(row)
            continue
        qr = QI.loc[fa]
        kq = f"{EK}kodlama_kuyrugu_github.csv#{fa}"
        # elle (kısmi) kararlar
        el = None
        for (gg, bas), v in ELLE.items():
            if gg == r.g and (r.ad.startswith(bas) or tok_norm(r.ad).startswith(bas)):
                el = v
                break
        if fa in D11:
            d = D11[fa]
            if el:
                es, od, nk, nm, hd, kn = el
                row.update(eslesme=es, hedef=hd, on_durum=od, neden_kodu=nk, neden_metni=nm, kanit=f"{kn} ; {d['dosya']}:{fa} ; {kq}")
                if es == "BENZER":
                    row["fark"] = nm
                fam_sonuc[fa].append((es, od))
                satirlar.append(row)
                continue
            if d["durum"] == "kodlandi":
                var = d["ad"] in KODSET
                row.update(eslesme="KOD" if var else "YOK", hedef=d["ad"], on_durum="KOD" if var else "BELIRSIZ",
                           kanit=f"{d['dosya']}:{fa} ; sonuclar/hesap_defteri/ara/kod_kaydi.csv#{d['ad']} ({KODDOSYA.get(d['ad'], 'KAYITTA YOK')}) ; {kq}",
                           **{"not": kisa(d["gerekce"], 200)})
                if not var:
                    bulgu.append(f"{hid}: {d['ad']} kod kaydında yok")
            else:   # kurala_dokulemez / veri_yok / cikis_modulu
                if d["durum"].startswith("cikis_modulu"):
                    row.update(eslesme="YOK", on_durum=D, neden_kodu="arac_sablon",
                               neden_metni="giriş stratejisi değil, çıkış/koruma modülü: " + kisa(d["gerekce"], 120),
                               kanit=f"{d['dosya']}:{fa} ; motor/strateji/cikislar.py:23-45 ; DURUM.md (2026-11-07 'Çıkış modülleri eklendi')",
                               **{"not": "sonradan CikisAyarlari alanı olarak eklendi (stop_basamaklari/azalan_roi/kar_rsi_esikleri/stop_sonrasi_bekleme_mum); strateji sınıfı değil"})
                elif d["durum"] == "veri_yok":
                    od = "H_BIZIM_EVRENDE_UYGULANAMAZ"
                    row.update(eslesme="YOK", on_durum=od, neden_kodu="hisse_kesitsel" if "gainer" in d["gerekce"] or "öncü" in d["gerekce"] else "veri_yok",
                               neden_metni=kisa(d["gerekce"], 200), kanit=f"{d['dosya']}:{fa} ; {kq}")
                else:   # kurala_dokulemez (elder)
                    row.update(eslesme="YOK", on_durum=D, neden_kodu="arac_sablon", neden_metni=kisa(d["gerekce"], 200),
                               kanit=f"{d['dosya']}:{fa} ; motor/strateji/cikislar.py:37 (elder_guvenli_bolge_k sonradan eklendi)",
                               **{"not": "giriş kuralı yok; Elder güvenli bölge stopu CikisAyarlari.elder_guvenli_bolge_k olarak kodlu (DURUM.md 2026-11-07)"})
            fam_sonuc[fa].append((row["eslesme"], row["on_durum"]))
            satirlar.append(row)
            continue
        if fa in D11J:
            j = D11J[fa]
            fam_adi = fa[6:]
            res = j_bul(r.g, r.ad, fam_adi) or j_bul(r.g, tok_norm(r.ad), fam_adi)
            hedef = j["hedef"]
            if res is None:
                row.update(eslesme="BELIRSIZ", on_durum="BELIRSIZ", kanit=f"stratejiler/kodlama_github_d11j.csv:{fa} ; {kq}",
                           neden_metni="d11j ailesi ama satır-ayar eşlemesi çıkarılamadı")
                bulgu.append(f"{hid}: d11j satır eşlemesi yok")
            elif res[0] == "AYAR":
                ids = [f"d11j:{fam_adi}:{s}" for s in res[2]] if len(res) > 2 else [f"d11j:{res[1]}:{s}" for s in res[2]]
                ids = [f"d11j:{res[1]}:{s}" for s in res[2]]
                ek = [i for i in ids if i in EKJ_IDS]
                yok = [i for i in ids if i not in EKJ_IDS and not any(a[1] == i for a in AYARLAR)]
                dosya = []
                for i in ids:
                    if i in EKJ_IDS:
                        dosya.append("stratejiler/ayarlar_d11j_ek.json")
                    else:
                        for a in AYARLAR:
                            if a[1] == i:
                                dosya.append(a[3])
                                break
                row.update(eslesme="AYAR" if not yok else "BELIRSIZ", hedef=hedef, ayar_id=" ; ".join(ids), ayar_dosyasi=" ; ".join(dict.fromkeys(dosya)),
                           on_durum="KOD" if not yok else "BELIRSIZ",
                           kanit=f"{dosya[0] if dosya else ''}#{ids[0]} ; stratejiler/kodlama_github_d11j.csv:{fa} ; {kq}")
                v, iz = sinif_bilgi(hedef)
                notu = d11j_not(hedef, ids, res[1])
                if j["degisiklik"] == "mod_eklendi":
                    notu += f" | MOD izgarada yok (izgara={list(iz.keys())}); sınıf varsayılanı değişmedi (kodlar d11j: 'varsayılanlar eskisiyle aynı'); yalnız ayar kaydıyla denenir"
                row["not"] = kisa(notu, 900)
                if yok:
                    bulgu.append(f"{hid}: ayar kaydı yok {yok}")
            elif res[0] == "D":
                row.update(eslesme="YOK", hedef="", on_durum=D, neden_kodu=res[1], neden_metni=res[2],
                           kanit=f"stratejiler/kodlama_github_d11j.csv:{fa} ; {kq}", **{"not": f"aile ({hedef}) kodlandı, bu kaynak satırı kapsanmadı"})
            else:   # H
                row.update(eslesme="YOK", on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ", neden_kodu=res[1], neden_metni=res[2],
                           kanit=f"stratejiler/kodlama_github_d11j.csv:{fa} ; {kq}")
            fam_sonuc[fa].append((row["eslesme"], row["on_durum"]))
            satirlar.append(row)
            continue
        # kuyrukta olup d11f-j'de olmayan: C aileleri / mevcut
        qd = qr.durum
        if qd.startswith("mevcut:"):
            hd = qd.split(":", 1)[1]
            if fa == "yeni__sabit-yuzde-stop-hedef-sure-cikisi":
                row.update(eslesme="YOK", on_durum=D, neden_kodu="arac_sablon",
                           neden_metni="giriş kuralı yok: sabit %3 stop / %20 hedef / 5 gün zaman çıkışı; çıkış modülü olarak mevcut (CikisAyarlari)",
                           kanit=f"{kq} ; motor/strateji/cikislar.py:15-16", **{"not": "kuyruk 'mevcut:cikislar' (stop_yuzde/hedef_yuzde dis__ standart parametre); sınıf açılmadı, çıkış alanları doğrulandı"})
            else:
                v, iz = sinif_bilgi(hd)
                row.update(eslesme="BENZER", hedef=hd, on_durum=D, neden_kodu="benzer_var",
                           fark=kisa(f"kuyruk: {qr['not'][:120]} | {kisa_par(hd, 5)}", 330), neden_metni="kuyruk 'mevcut' dedi; bit alanı/hangi desenlerin seçileceği kaynakta yok (C)",
                           kanit=f"{kq} ; {KODDOSYA.get(hd, '')}")
        else:
            nm = re.split(r"\s*Lisans:", qr["not"])[0]
            nk = "kural_belirsiz"
            tl = nm.lower()
            if "meta" in tl and "strateji değil" in tl:
                nk = "arac_sablon"
            elif "martingale" in tl or "grind" in tl:
                nk = "martingale"
            elif "çapraz-sembol" in tl or "tek-grafik" in tl or "kesit" in tl or "çok-pozisyonlu" in tl:
                nk = "kapsam_disi"
            elif "veri" in tl and "yok" in tl:
                nk = "veri_yok"
            elif "api örneği" in tl:
                nk = "arac_sablon"
            row.update(eslesme="YOK", on_durum=D, neden_kodu=nk, neden_metni=kisa(nm, 220),
                       kanit=f"{kq} (öncelik {qr.kodlanabilirlik_oncelik}: kodlanamaz/kural eksik)",
                       **{"not": "kuyrukta C öncelikli; d11f-j kodlama dosyalarında yok (kodlanmadı)"})
        fam_sonuc[fa].append((row["eslesme"], row["on_durum"]))
        satirlar.append(row)
        continue

    # --- durum=kural_yok
    if tip == "kural_yok":
        nk, nm = kural_yok_neden(r.ayar_durumu)
        row.update(eslesme="YOK", on_durum=D, neden_kodu=nk, neden_metni=nm + (f": {kisa(r.ayar_durumu, 90)}" if r.ayar_durumu else ""),
                   kanit=kaynak_kanit)
        if r.benzer_1l3a_aile:
            row["not"] = f"ilk tarama benzer_1l3a_aile={r.benzer_1l3a_aile} (kural metni olmadığından karşılaştırılamadı)"
        satirlar.append(row)
        continue
    if tip == "ml":
        row.update(eslesme="YOK", on_durum="G_ML", neden_kodu="ml", neden_metni=kisa(r.ayar_durumu or "model eğitimi/ML/LLM", 150), kanit=kaynak_kanit)
        satirlar.append(row)
        continue
    if tip == "yasak":
        row.update(eslesme="YOK", on_durum="F_YASAK_TIP", neden_kodu=yasak_neden(r.ayar_durumu + " " + r.mekanik_ozet),
                   neden_metni=kisa(r.ayar_durumu, 150), kanit=kaynak_kanit)
        satirlar.append(row)
        continue
    if tip == "veri_yok":
        od, nk, nm = veri_yok_neden(r.ayar_durumu, r.kategori)
        if r.kategori == "pairs_arbitraj" and od == "D":
            od, nk = "H", "pairs"
        row.update(eslesme="YOK", on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ" if od == "H" else D, neden_kodu=nk,
                   neden_metni=kisa(nm + (f" ({r.ayar_durumu})" if r.ayar_durumu else ""), 200), kanit=kaynak_kanit)
        satirlar.append(row)
        continue

    # --- durum=mevcut:/ayar:
    hedef = durum.split(":", 1)[1]
    yeni_ad = None
    if hedef.startswith("yeni__"):
        e = ESKI.get(hedef) or D11.get(hedef)
        yeni_ad = e["ad"] if e else ""
        hedef_ad = yeni_ad
        kan_ek = f" ; {e['dosya']}:{hedef}" if e else ""
    else:
        hedef_ad = hedef
        kan_ek = ""
    if not hedef_ad:
        # yeni__ ailesi hiç kodlanmamış (ör. gecelik-gunici-etki: kurala_dokulemez)
        e = ESKI.get(hedef)
        row.update(eslesme="YOK", on_durum=D, neden_kodu="kapsam_disi", neden_metni=kisa("ilk tarama 'ayar:%s' dedi; aile kodlanmadı: %s" % (hedef, e["gerekce"] if e else "kayıt yok"), 220),
                   kanit=(f"{e['dosya']}:{hedef} ; " if e else "") + kaynak_kanit)
        satirlar.append(row)
        continue
    if hedef_ad not in KODSET:
        row.update(eslesme="BELIRSIZ", on_durum="BELIRSIZ", kanit=kaynak_kanit, neden_metni=f"hedef {hedef_ad} kod kaydında yok")
        bulgu.append(f"{hid}: hedef {hedef_ad} kod kaydında yok")
        satirlar.append(row)
        continue
    kd = KODDOSYA[hedef_ad]
    # 1) ma-kesişim elle doğrulanan ESDEGER
    if hedef_ad == "swing__ma-kesisim" and (r.g, r.no) in MA_ESD:
        ay, nt = MA_ESD[(r.g, r.no)]
        row.update(eslesme="ESDEGER", hedef=hedef_ad, fark="yok", on_durum="KOD",
                   kanit=f"{kd} (MaKesisim: hizli/yavas/ma_tipi/short parametreli kesişim) ; stratejiler/dis_ayarlari/swing__ma-kesisim.json#{ay} ; {kaynak_kanit}",
                   **{"not": nt})
        satirlar.append(row)
        continue
    # 2) ayar kaydı eşleşmesi
    ay = ayar_ara(hedef_ad, r)
    if ay:
        ids = [a[0] for a in ay][:4]
        row.update(eslesme="AYAR", hedef=hedef_ad, ayar_id=" ; ".join(ids), ayar_dosyasi=" ; ".join(dict.fromkeys(a[1] for a in ay)), on_durum="KOD",
                   kanit=f"{ay[0][1]}#{ids[0]} ; {kaynak_kanit}",
                   **{"not": f"ayar kaydı kaynak dosyası bu satırın adı/dosyasını anıyor; {hedef_ad} dis_ayarlari ile aday kümesinde (tarama._ayar_listesi)"})
        satirlar.append(row)
        continue
    # 3) sınıf kaynağında satır adı/dosya adı geçiyor -> KOD ; 4) ilk tarama 'kodlandi'
    txt = kaynak_metni(kd)
    stem = os.path.splitext(os.path.basename(r.dosya.split(" ")[0].split(";")[0]))[0].lower()
    nm = r.ad.lower().split(" (")[0]
    e2 = (len(stem) >= 7 and stem in txt) or (len(nm) >= 12 and nm in txt)
    if e2 or (tip == "mevcut" and r.ayar_durumu.strip().lower() == "kodlandi"):
        row.update(eslesme="KOD", hedef=hedef_ad, on_durum="KOD",
                   kanit=f"{kaynak_kanit} (durum={durum}) ; {kd} ; kod_kaydi.csv#{hedef_ad}",
                   **{"not": "sınıf kaynağında ad/dosya adı geçiyor" if e2 else "ilk tarama 'kodlandi'; sınıf kayıtta var (docstring'de ad geçmiyor)"})
        satirlar.append(row)
        continue
    # 5) doğrulanamadı -> BENZER
    fark = f"ilk tarama '{tip}:{hedef}' dedi; sınıf {KODSINIF.get(hedef_ad)} ({kd}) açıldı, satırın kuralı birebir karşılaştırılamadı. " \
           f"Satır notu: {kisa(r.ayar_durumu, 110) or '-'} | {kisa_par(hedef_ad, 5)}"
    row.update(eslesme="BENZER", hedef=hedef_ad, fark=kisa(fark, 400), on_durum=D, neden_kodu="benzer_var",
               neden_metni="aynı aileye işaret ediliyor ama mantık/parametre farkı doğrulanmadı",
               kanit=f"{kaynak_kanit} (durum={durum}) ; {kd}")
    satirlar.append(row)

# --------------------------------------------------------------------------- yaz
cols = ["ham_id", "kaynak_id", "kaynak_satir_no", "kaynaktaki_ad", "kisa_mantik", "aile", "eslesme", "hedef", "ayar_id", "ayar_dosyasi", "fark",
        "on_durum", "neden_kodu", "neden_metni", "kanit", "not"]
with open(ARA / "G4_GITHUB_ham.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    for s in satirlar:
        w.writerow({c: s.get(c, "") for c in cols})

with open(ARA / "G4_GITHUB_elle_kararlar.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["tur", "kaynak_g", "ad_basi", "eslesme", "on_durum", "neden_kodu", "hedef", "gerekce"])
    for (g, b), v in ELLE.items():
        w.writerow(["kismi_aile", g, b, v[0], v[1], v[2], v[4], v[3]])
    for (g, b), v in J.items():
        if v[0] == "AYAR":
            w.writerow(["d11j_ayar_esleme", g, b, "AYAR", "KOD", "", v[1], "ayar: " + ",".join(v[2])])
        else:
            w.writerow(["d11j_satir_karari", g, b, "YOK", "D/H", v[1], "", v[2]])
    for (g, n), v in MA_ESD.items():
        w.writerow(["ma_kesisim_esdeger", g, str(n), "ESDEGER", "KOD", "", "swing__ma-kesisim", v[0] + " | " + v[1]])

ozet = dict(n=len(satirlar), esl=Counter(s["eslesme"] for s in satirlar), od=Counter(s["on_durum"] for s in satirlar),
            fam={k: v for k, v in fam_sonuc.items()}, bulgu=bulgu, tok_kullanilan=len(TOK_KULLANILAN),
            tok_toplam=sum(len(t) for t in TOKEN2FAM.values()))
json.dump({"n": ozet["n"], "esl": dict(ozet["esl"]), "od": dict(ozet["od"]), "bulgu": bulgu,
           "fam": {k: v for k, v in fam_sonuc.items()}}, open(ARA / "G4_GITHUB_ozet.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(satirlar), dict(ozet["esl"]), dict(ozet["od"]))
print("bulgu:", bulgu[:20])
print("token kullanılan", len(TOK_KULLANILAN), "/ kuyruk token", sum(1 for _ in TOKEN2FAM))
