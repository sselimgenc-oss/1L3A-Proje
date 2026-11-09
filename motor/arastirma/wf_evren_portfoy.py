"""Portföy (hedef-ağırlık) stratejilerinin evren testi (ON_KAYIT Güncelleme 3 + 5; lider kararı 2026-11-08).

19 pf__ stratejisi, tek-grafik stratejilerle AYNI kapı mantığı ve AYNI listelerle ("portfoy" stili) değerlendirilir; mevcut
parçalar yeniden kullanılır (wf_portfoy: AdayHesap, secim_ve_oos, oos_metrikleri; saglamlik_portfoy: rastgele ağırlık,
komşu ayarlar). Farklar (sonuca bakılmadan sabit):
  - Evren = swing/daytrade evreni (EVREN_GENEL), tf = 1d, dönem = geliştirme dönemi (holdout kesilir; veri `we._veri` ile aynı kural).
  - Pencereler 730/180 gün, seçim skoru eğitim günlük Sharpe'ı (wf_portfoy), analiz başlangıcı we.analiz_bas_hesapla.
  - WF kapısı = karar 24 (OOS >= 1095 gün, >= 20 yeniden dengeleme, net > 0, Sharpe >= 0.5, düşüş <= %20); iyiye yakın
    kıl payı: Sharpe >= 0.4, düşüş <= %25 (en çok bir ölçüt kaçar). Genişlik ölçütleri portföy için yok.
  - Maliyet: evren maliyet tablosu SEMBOL BAŞINA (PortfoyAyarlari.maliyet_sembol); K1: x2, x3 ve ağırlık tablosu 1 bar
    gecikmeli (GecikmePf); kapı büyüklüğü PF(R) (OOS işlemlerinden), diğer stratejilerle aynı eşikler.
  - K2 rastgele: aynı yeniden dengeleme takviminde, aynı ağırlık kümesiyle rastgele semboller (RastgeleAgirlik, aynı stop
    kuralı); 500 simülasyon; istatistik OOS günlük Sharpe'ı; p = (1 + #{sim >= gerçek}) / 501.
  - K3: blok bootstrap OOS Sharpe alt ucu > 0 (`boot_sharpe_alt`); K4: komşu ayarların >= %60'ında OOS Sharpe > 0 (>= 2 geçerli).
  - K5 DSR ve PBO (stil 'portfoy' x tf '1d' grubu: tüm aday ayarların OOS günlük getirisiyle) diğerleriyle aynı.
  - Holdout: WF'nin son seçilen ayarı, holdout'ta tek koşu; net > 0 ve PF(R) >= 1.1.
Çıktılar: sonuclar/evren/<donem>/pf/<strateji>--{gunluk,islemler,adaylar}.parquet; satırlar wf_evren.parquet /
saglamlik.parquet içine stil='portfoy' olarak eklenir (listeler, seçim, mühür, holdout, rapor aynı akıştan geçer).
"""
from __future__ import annotations

import json
import math
import time
import zlib
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet
from motor.arastirma import saglamlik_portfoy as sp
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_portfoy as wp
from motor.backtest import eleme
from motor.backtest.walk_forward import pencereler_uret
from motor.portfoy import veri as pveri
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.veri import depo

STIL = "portfoy"
TF = "1d"
YAKIN_ESIK = eleme.PortfoyEsikleri(min_sharpe=0.4, max_dusus=0.25)
_VERI: dict = {}


class GecikmePf:
    """K1c: hedef ağırlık ve stop tablolarını 1 bar geciktirir (sarılan stratejinin geri kalanı aynen)."""

    def __init__(self, ic, bar: int = 1):
        self._ic, self._bar = ic, int(bar)

    def __getattr__(self, ad):
        return getattr(self._ic, ad)

    def sinyaller(self, veriler: dict):
        h, s = self._ic.sinyaller(veriler)
        return h.shift(self._bar), s.shift(self._bar)


def pf_stratejileri() -> list:
    return sorted(tum_portfoy_stratejileri())


def maliyet_pf(semboller, carpan: float = 1.0) -> PortfoyAyarlari:
    ms = {s: evren_maliyet.sembol_maliyeti(s, carpan) for s in semboller}
    en = max(v[0] for v in ms.values())
    return PortfoyAyarlari(limit_modu="olc", maliyet_sembol=ms, komisyon_taker_yuzde=en,
                           komisyon_maker_yuzde=max(v[1] for v in ms.values()),
                           kayma_bps=max(v[2] for v in ms.values()), stop_kayma_bps=max(v[3] for v in ms.values()))


def veri_yukle(evren=None, tf: str = TF):
    """(veriler, fundingler, dışarıda) — dönem ayarına (we._CFG) göre; dönemin bit sınırı okumada uygulanır."""
    evren = tuple(evren or we.EVREN_GENEL)
    d = we.DONEMLER[we._CFG["donem"]]
    k = (evren, tf, we._CFG["donem"], str(we._CFG["veri_dizini"]))
    if k not in _VERI:
        _VERI.clear()
        dizin = we._CFG["veri_dizini"]
        kl = {"kilit_ac": d["kilit_ac"], "gerekce": we.donem_gerekce(we._CFG["donem"])}
        v, f, dis = {}, {}, []
        for s in evren:
            try:
                df = pveri.mum_yukle(s, tf, d["bas"], d["bit"], dizin, **kl)
            except (FileNotFoundError, ValueError):
                dis.append(s)
                continue
            if not len(df):
                dis.append(s)
                continue
            v[s] = df.drop(columns="eksik") if "eksik" in df.columns else df
            if depo.funding_yolu(s, dizin).exists():
                f[s] = depo.funding_oku(s, d["bas"], d["bit"], dizin=dizin, **kl)
        if d["bit"] is not None and any(len(x) and x.index.max() >= d["bit"] for x in v.values()):
            raise RuntimeError("portföy verisi dönem sınırını aştı")
        _VERI[k] = (v, f, dis)
    return _VERI[k]


def _kos(st, v, f, evren, ay, gecikme: int = 0):
    sec = wp.gerekli_semboller(st, evren)
    stx = GecikmePf(st, gecikme) if gecikme else st
    return portfoy_backtest({s: v[s] for s in sec}, stx, ay, {s: f[s] for s in sec if s in f})


def aday_hesap(r) -> wp.AdayHesap:
    gunluk = r.gunluk_ozsermaye.pct_change().fillna(0.0)
    q = r.pozisyon_gecmisi
    degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
    return wp.AdayHesap(gunluk, r.islemler, float(r.maruziyet["brut"].mean()), [o["zaman"] for o in r.limit_olaylari],
                        q.index[degisti.to_numpy()])


def pf_gorev(ad: str, carpan: float = 1.0, gecikme: int = 0, evren=None, tf: str = TF, egitim_gun: int = wp.EGITIM_GUN,
             test_gun: int = wp.TEST_GUN, min_islem: int = wp.MIN_ISLEM_EGITIM, min_gun: int = wp.MIN_GUN_EGITIM) -> dict:
    """Tek pf stratejisi, geliştirme dönemi walk-forward. -> {'satir', 'getiri', 'oos', 'hesaplar'}. Hata satıra yazılır."""
    t0 = time.perf_counter()
    satir = {"strateji": ad, "stil": STIL, "tf": tf, "hata": "", "kisa_gecmis": "", "hatali_sembol": "", "spot_vekil": "{}",
             "bist_kisa_donem": "", "maliyet_hash": evren_maliyet.tablo_hash(), "carpan": carpan, "gecikme": int(gecikme)}
    cikti = {"satir": satir, "getiri": None, "oos": None, "hesaplar": {}}
    try:
        v, f, dis = veri_yukle(evren, tf)
        evren_t = tuple(v)
        satir.update(n_enstruman_evren=len(tuple(evren or we.EVREN_GENEL)), n_enstruman=len(v), disarida=",".join(dis))
        adaylar, atlanan = wp.aday_listesi(ad, evren_t, True)
        satir.update(n_aday=len(adaylar), n_atlanan=len(atlanan))
        if not adaylar:
            satir.update(gecti=False, yakin_wf=False, nedenler="bu evrende uygun aday yok", basarisiz_sayi=9)
            return cikti
        ay = maliyet_pf(evren_t, carpan)
        hesaplar, hatalar = {}, []
        for etiket, st in adaylar:
            try:
                hesaplar[etiket] = aday_hesap(_kos(st, v, f, evren_t, ay, gecikme))
            except Exception as e:  # noqa: BLE001
                hatalar.append(f"{etiket}: {type(e).__name__}: {e}"[:160])
        satir.update(n_kosu=len(hesaplar), n_aday_hata=len(hatalar), hata_ornegi=hatalar[0] if hatalar else "")
        if not hesaplar:
            raise RuntimeError(f"hiç aday koşulamadı: {hatalar[0] if hatalar else 'aday yok'}")
        bas = we.analiz_bas_hesapla({s: v[s].index[0] for s in v})
        bit = max(df.index[-1] for df in v.values()) + pd.Timedelta(1, "ns")
        pencereler = pencereler_uret(bas, bit, egitim_gun, test_gun)
        satir.update(analiz_bas=str(bas), n_pencere=len(pencereler))
        if not pencereler:
            satir.update(gecti=False, yakin_wf=False, nedenler="veri pencereye yetmiyor", basarisiz_sayi=9)
            return cikti
        oos_bas, oos_bit = pencereler[0][2], pencereler[-1][3]
        getiri, oos, secimler = wp.secim_ve_oos(hesaplar, pencereler, min_islem, min_gun)
        for s in secimler:
            s["ayar"] = s["secilen"]                      # evren_wf ile aynı alan adı (holdout / K2 okur)
        satir.update(oos_bas=str(oos_bas), oos_bit=str(oos_bit), secimler=json.dumps(secimler, ensure_ascii=False, default=str),
                     n_islemli_pencere=sum(s["secilen"] is not None for s in secimler))
        ist = wp.istikrar(secimler)
        satir.update(n_farkli_ayar=ist["n_farkli_ayar"], en_sik_ayar=ist["en_sik_ayar"], en_sik_pay=ist["en_sik_pay"])
        m = wp.oos_metrikleri(getiri, oos, int(sum(s.get("dengeleme", 0) for s in secimler)))
        satir.update(m)
        satir["profit_factor"] = m.get("profit_factor", math.nan)
        satir["pf_en_iyi5_haric"] = m.get("en_iyi_yuzde5_haric_pf", math.nan)
        k = eleme.portfoy_degerlendir({"metrikler": m})
        ky = eleme.portfoy_degerlendir({"metrikler": m}, YAKIN_ESIK)
        satir.update(gecti=bool(k["gecti"]), nedenler="; ".join(k["nedenler"]), basarisiz_sayi=len(k["nedenler"]),
                     yakin_wf=bool(ky["gecti"] and len(k["nedenler"]) <= 1), enstruman_adet="{}", enstruman_net="{}",
                     sinif_net="{}", n_enstruman_islemli=0)
        cikti.update(getiri=getiri, oos=oos, hesaplar=hesaplar)
    except Exception as e:  # noqa: BLE001
        satir.update(hata=f"{type(e).__name__}: {e}"[:300], gecti=False, yakin_wf=False, nedenler="hata", basarisiz_sayi=99)
    satir["sure_sn"] = time.perf_counter() - t0
    return cikti


def _kaydet(cikti: Path, ad: str, g: dict):
    d = Path(cikti) / "pf"
    d.mkdir(parents=True, exist_ok=True)
    s = g["satir"]
    if g["getiri"] is None:
        return
    g["getiri"].rename("oos_getiri").to_frame().to_parquet(d / f"{ad}--gunluk.parquet")
    if g["oos"] is not None and len(g["oos"]):
        g["oos"].to_parquet(d / f"{ad}--islemler.parquet", index=False)
    bas, bit = pd.Timestamp(s["oos_bas"]), pd.Timestamp(s["oos_bit"])
    kolon = {e: h.test_getirisi(bas, bit) for e, h in g["hesaplar"].items()}
    pd.DataFrame(kolon).astype("float32").to_parquet(d / f"{ad}--adaylar.parquet")


def _wf_isci(g: dict):
    r = pf_gorev(g["strateji"])
    _kaydet(g["cikti"], g["strateji"], r)
    return r["satir"]


def _satirlari_yaz(cikti: Path, ad_dosya: str, yeni: list):
    yol = Path(cikti) / f"{ad_dosya}.parquet"
    onceki = pd.read_parquet(yol) if yol.exists() else pd.DataFrame()
    if len(onceki):
        anah = {(s["strateji"], s["tf"]) for s in yeni}
        onceki = onceki[[(a, t) not in anah for a, t in zip(onceki["strateji"], onceki["tf"])]]
    tum = pd.concat([onceki, pd.DataFrame(yeni)], ignore_index=True)
    we._csv_yaz(tum, Path(cikti) / ad_dosya)


def pf_wf_asamasi(cikti: Path, donem: str = "2017_gelistirme", stratejiler=None, surec: int = 4,
                  butce_sn: Optional[float] = None, ilerleme: bool = True, veri_dizini=None) -> dict:
    """pf stratejilerinin geliştirme dönemi WF'si -> wf_evren.parquet'e stil='portfoy' satırları (aynı strateji yeniden koşulursa ezilir)."""
    cikti = Path(cikti)
    we.holdout_kilidi(cikti, "portfoy")
    cikti.mkdir(parents=True, exist_ok=True)
    gorevler = [{"strateji": s, "cikti": cikti} for s in (stratejiler or pf_stratejileri())]
    sonuc = we.havuz_calistir(_wf_isci, gorevler, surec, we._isci_ham, {"veri_dizini": veri_dizini, "donem": donem}, butce_sn, ilerleme, "pf-wf")
    yeni = [s for s in sonuc if not s.get("ertelendi")]
    if yeni:
        _satirlari_yaz(cikti, "wf_evren", yeni)
        for s in yeni:
            if s.get("hata", "") == "" and s.get("n_kosu"):      # çift kayıt önlenir (wf_evren.evren_deneme_kaydet)
                we.evren_deneme_kaydet(s, donem, we.EVREN_GENEL)
    return {"yeni": len(yeni), "gecen": int(sum(bool(s.get("gecti")) for s in yeni)),
            "hatali": int(sum(bool(s.get("hata")) for s in yeni))}


# ============================================================================ sağlamlık
def pf_sag_icerik(g: dict, satir: dict):
    cikti, ad, tf = Path(g["cikti"]), g["strateji"], g["tf"]
    w = g["wf"]
    v, f, _ = veri_yukle(None, tf)
    evren_t = tuple(v)
    oos_bas, oos_bit = pd.Timestamp(w["oos_bas"]), pd.Timestamp(w["oos_bit"])
    r_oos = pd.read_parquet(cikti / "pf" / f"{ad}--gunluk.parquet")["oos_getiri"].astype(float)
    satir.update(wf_islem=int(w["islem_sayisi"]), wf_pf=float(w["profit_factor"]), wf_sharpe=float(w["sharpe"]),
                 en_sik_ayar=w["en_sik_ayar"])
    for onek, carpan, gecikme in (("m2", 2.0, 0), ("m3", 3.0, 0), ("g1", 1.0, 1)):
        s_ = pf_gorev(ad, carpan, gecikme)["satir"]
        if s_["hata"]:
            raise RuntimeError(f"K1 {onek}: {s_['hata']}")
        satir.update({f"{onek}_islem": s_.get("islem_sayisi", 0), f"{onek}_pf": s_.get("profit_factor", math.nan),
                      f"{onek}_net": s_.get("net_getiri", math.nan), f"{onek}_sharpe": s_.get("sharpe", math.nan),
                      f"{onek}_kill_olayi": 0, f"{onek}_islem_ham": s_.get("islem_sayisi", 0), f"{onek}_pf_limitsiz": math.nan})
    # K2: rastgele ağırlık (aynı takvim / ağırlık kümesi / stop kuralı), istatistik OOS günlük Sharpe
    secimler = json.loads(w["secimler"])
    pencere = sp.secim_pencereleri(secimler)
    etiketler = sorted({p[0] for p in pencere})
    adaylar = dict(wp.aday_listesi(ad, evren_t, True)[0])
    ay = maliyet_pf(evren_t, 1.0)
    hazir = {}
    for e in etiketler:
        st = adaylar[e]
        sec = wp.gerekli_semboller(st, evren_t)
        vv, ff = {s: v[s] for s in sec}, {s: f[s] for s in sec if s in f}
        hazir[e] = (st, vv, ff, sp.RastgeleHazirlik(st, vv))
    temel = zlib.crc32(f"{ad}|{tf}|evren-pf".encode()) ^ g["tohum"]
    sims = []
    for sim in range(g["n_sim"]):
        gl = {}
        for k, e in enumerate(etiketler):
            st, vv, ff, hz = hazir[e]
            gl[e] = sp._gunluk(portfoy_backtest(vv, sp.RastgeleAgirlik(st, hz, [temel, sim, k]), ay, ff))
        sims.append(sp.sharpe(sp.dik(gl, pencere, r_oos.index).to_numpy()))
    gercek = sp.sharpe(r_oos.to_numpy())
    rp = sp.rastgele_p(gercek, sims)
    satir.update(rnd_n_sim=g["n_sim"], rnd_p=rp["rnd_p"], rnd_gercek_r=gercek, rnd_ort_r=rp["rnd_ort"], rnd_std_r=rp["rnd_std"],
                 rnd_yuzdelik=rp["rnd_yuzdelik"], rnd_gecersiz=0.0,
                 rnd_cikis_kurallari="agirlik: aynı takvim ve ağırlık kümesi, rastgele sembol (istatistik = OOS Sharpe)",
                 rnd_desteklenmeyen="")
    # K3: bootstrap Sharpe alt ucu
    b = sp.blok_bootstrap_sharpe(r_oos.to_numpy())
    satir.update(boot_sharpe_alt=b["boot_alt"], pf_boot_alt=math.nan, pf_boot_ust=b["boot_ust"])
    # K4: komşu ayarlar (tam geliştirme verisinde sabit ayar; OOS aralığı Sharpe > 0)
    taban = adaylar[w["en_sik_ayar"]]
    sinif = tum_portfoy_stratejileri()[ad]
    gecerli = olumlu = hata = 0
    gorulen, detay = set(), []
    for oyna in sp.komsu_ayarlari(sinif, taban.parametreler):
        try:
            st = taban.yeni(**oyna)
            kimlik = wp._json(st.parametreler)
            if kimlik in gorulen:
                continue
            gorulen.add(kimlik)
            if not st.uygun_mu(evren_t):
                raise ValueError("evrende uygun değil")
            gl = sp._gunluk(_kos(st, v, f, evren_t, ay))
            sh = sp.sharpe(gl[(gl.index >= oos_bas) & (gl.index < oos_bit)].to_numpy())
            if not np.isfinite(sh):
                raise ValueError("Sharpe hesaplanamadı")
        except Exception:  # noqa: BLE001
            hata += 1
            continue
        gecerli += 1
        olumlu += int(sh > 0)
        detay.append(f"{oyna}:{sh:.2f}")
    satir.update(par_n_gecerli=gecerli, par_n_pf_gt1=olumlu, par_hata=hata, par_detay=" | ".join(detay),
                 par_oran=(olumlu / gecerli) if gecerli >= sp.KOMSU_MIN_GECERLI else math.nan)
    satir.update(we.dsr_sutunlari(r_oos.to_numpy(), g["dsr"]))         # GÜNCELLEME 6 (A): grup N/V


# ============================================================================ PBO, holdout
def pbo_matrisi_pf(cikti: Path, wf_grup: pd.DataFrame, bas, bit) -> tuple:
    """Tüm pf adaylarının (strateji x ayar) [bas, bit) günlük getirileri (UTC günü). -> (M float32 (T,N), etiketler)."""
    gunler = pd.date_range(pd.Timestamp(bas).floor("D"), pd.Timestamp(bit).floor("D"), freq="D", tz="UTC")
    kol, et = [], []
    for ad in wf_grup["strateji"]:
        yol = Path(cikti) / "pf" / f"{ad}--adaylar.parquet"
        if not yol.exists():
            continue
        d = pd.read_parquet(yol).reindex(gunler).fillna(0.0)
        for c in d.columns:
            kol.append(d[c].to_numpy(dtype=np.float32))
            et.append((ad, c))
    return (np.stack(kol, axis=1) if kol else np.zeros((len(gunler), 0), dtype=np.float32)), et


def holdout_kos(ad: str, etiket: str, tf: str = TF, dislanan=(), ayar=None) -> dict:
    """WF'nin son seçilen ayarı, holdout'ta tek koşu (veri_ayarla(..., 'holdout') kurulu). Girişi >= HOLDOUT_BAS."""
    v, f, _ = veri_yukle(None, tf)
    evren_t = tuple(s for s in v if s not in set(dislanan))
    st = dict(wp.aday_listesi(ad, evren_t, True)[0]).get(etiket)
    if st is None:
        raise KeyError(f"aday bulunamadı: {etiket}")
    r = _kos(st, v, f, evren_t, maliyet_pf(evren_t, 1.0))
    g = sp._gunluk(r)
    g = g[g.index >= we.HOLDOUT_BAS]
    t = r.islemler
    t = t[pd.DatetimeIndex(t["giris_zamani"]) >= we.HOLDOUT_BAS] if len(t) else t
    rr = np.nan_to_num(t["r"].to_numpy(dtype=float), nan=0.0) if len(t) else np.array([])
    x = g.to_numpy(dtype=float)
    return {"n_enstruman_veri": len(evren_t), "islem_sayisi": int(len(t)),
            "net_getiri": float(np.prod(1.0 + x) - 1.0) if len(x) else 0.0,
            "profit_factor": wp.pf_hesapla(rr) if len(rr) else math.nan, "sharpe": wp.sharpe_gunluk(x),
            "max_dusus": wp.max_dusus(x) if len(x) else math.nan, "holdout_gun": int(len(x))}
