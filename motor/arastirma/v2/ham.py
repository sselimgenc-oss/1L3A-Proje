"""v2 Aşama 1 — ham koşu (ON_KAYIT_V2 bölüm 3, 1.1, 1.2; P1-1).

Her havuz_v2 satırı: yalnız VARSAYILAN ayar (1.1; ızgara yok), beyan ettiği evrenin her enstrümanında, geliştirme döneminin
tamamında (okuma `bit` = HOLDOUT_BAS ile kesilir; v1 yükleyicisi `wf_evren._veri`), maliyet ×1 ve ×2. Tek-grafik satırlarda
her işlem için GÜNLÜK piyasa-değeri (MTM) yolu yazılır; portföy (pf__) satırlarında yol = günlük özsermaye getirisidir.

Çıktı (sonuclar/evren/v2/):
  ham/x1|x2/<strateji>--<tf>--<sembol>.parquet  : ayar_no, giris_zamani, cikis_zamani, yon, r, sf, stop_mesafe, fonlama_r
                                                  (r = funding dahil net R; v1 `islem_ozet` ile uyumlu sütunlar)
  ham/x1|x2/<...>.json                          : yan dosya, EN SON yazılır = "bitti" işareti (devam ettirilebilir)
  mtm/x1|x2/<...>.parquet                       : islem_no (ham satır sırası), gun (UTC), kum_r (birikimli R)
  portföy: ham/x*/<pf__ad>--1d--_PORTFOY.parquet (gun, getiri, dengeleme) + .json

MTM tanımı: işlemin açık olduğu her UTC gün sonu d (giriş günü dahil, çıkış günü hariç) için
    kum_r(d) = yon·(kapanış_d − giriş_fiyatı)/stop_mesafe − giriş_komisyonu_R − funding_R·pay(d)
(kapanış_d = o günün sonunda KAPANMIŞ son mum; pay(d) = geçen süre oranı; ileri doldurma yalnız geçmişten) ve çıkış gününde
kum_r = işlemin R'si (maliyetler girişte ve çıkışta). Böylece yolun son değeri işlemin R'sine EŞİTTİR ve nokta sayısı =
giriş günü ile çıkış günü arası takvim günü sayısı (uçlar dahil). Yaklaşıklıklar (tutucu, raporlanır): kısmi çıkışlarda ara
günler ilk miktarla değerlenir; gerçek funding (kripto) süreye doğrusal yayılır; çıkış maliyeti yalnız çıkış gününde.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, secim
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import maliyet, sabit
from motor.backtest.motor import backtest
from motor.strateji import funding, kayit
from motor.veri import depo

PF_SEMBOL = "_PORTFOY"


class HoldoutSizintisi(RuntimeError):
    """Geliştirme okumasında HOLDOUT_BAS ve sonrası veri göründü. ASLA yutulmaz; aşama durur."""


# ============================================================================ yardımcılar
def zaman_utc(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def carpan_adi(carpan: float) -> str:
    return f"x{carpan:g}"


def dosya_yolu(dizin: Path, ad: str, tf: str, sembol: str) -> Path:
    return Path(dizin) / f"{ad}--{tf}--{sembol}.parquet"


def havuz_oku(yol=None) -> pd.DataFrame:
    d = pd.read_csv(yol or sabit.HAVUZ_CSV)
    for c in ("strateji", "stil_v2", "tf", "evren"):
        if c not in d.columns:
            raise ValueError(f"havuz dosyasında sütun yok: {c}")
    if d["strateji"].duplicated().any():
        raise ValueError("havuzda tekrarlı strateji")
    return d


def havuz_muhru_dogrula(havuz_yolu=None, muhur_yolu=None) -> dict:
    """Önceki aşamanın (havuz) mührü yoksa / havuz dosyası mühürle uyuşmuyorsa AÇIK HATA."""
    import hashlib
    hy, my = Path(havuz_yolu or sabit.HAVUZ_CSV), Path(muhur_yolu or sabit.HAVUZ_MUHRU)
    if not my.exists():
        raise RuntimeError(f"havuz mührü yok: {my} (önce havuz aşaması)")
    m = json.loads(my.read_text())
    if hashlib.sha256(hy.read_bytes()).hexdigest() != m.get("havuz_csv_sha256"):
        raise RuntimeError("havuz_v2.csv mühürle uyuşmuyor (havuz koşudan sonra değiştirilemez)")
    return m


def varsayilan_strateji(ad: str) -> tuple:
    """1.1: -> (etiket, strateji). Kart ayarı dosyası varsa İLK kaydı, yoksa sınıfın varsayılanı. Izgara/dış ayar ASLA."""
    kartlar = kayit.kart_ayarlari(ad)
    if kartlar:
        kid = kartlar[0]["kart_id"]
        return f"kart:{kid}", kayit.kart_ayarli_strateji(ad, kid)
    return "varsayilan", kayit.al(ad)()


def veri_oku(sembol: str, tf: str) -> tuple:
    """(mumlar, funding) — v1 yükleyicisi (dönem 2017_gelistirme: okuma `bit` = HOLDOUT_BAS ile kesilir). HOLDOUT_BAS ve
    sonrası herhangi bir mum/funding satırı varsa HoldoutSizintisi (kesin hata)."""
    mumlar, fund = we._veri(sembol, tf)
    sizinti_kontrol(sembol, tf, mumlar, fund)
    return mumlar, fund


def sizinti_kontrol(sembol: str, tf: str, mumlar, fund) -> None:
    for ad, df in (("mum", mumlar), ("funding", fund)):
        if df is not None and len(df) and pd.Timestamp(df.index.max()) >= sabit.HOLDOUT_BAS:
            raise HoldoutSizintisi(f"{sembol} {tf}: {ad} verisi HOLDOUT_BAS ({sabit.HOLDOUT_BAS}) ve sonrasına uzanıyor")


def gunluk_kapanis(mumlar: pd.DataFrame, tf: str) -> pd.Series:
    """UTC günü sonunda KAPANMIŞ son mumun kapanışı (mum günü = kapanış anının son nanosaniyesinin günü); veri olmayan
    takvim günleri geçmişten ileri doldurulur (gelecek bilgisi yok). İndeks: kesintisiz UTC takvim günleri."""
    dur = depo.aralik_suresi(tf)
    idx = pd.DatetimeIndex(mumlar.index).as_unit("ns")
    gun = (idx + dur - pd.Timedelta(1, "ns")).floor("D")
    s = pd.Series(mumlar["kapanis"].to_numpy(dtype=float), index=gun).groupby(level=0).last()
    return s.reindex(pd.date_range(s.index[0], s.index[-1], freq="D")).ffill()


def mtm_yolu(giris, cikis, yon, giris_fiyati, stop_mesafe, r_son, giris_maliyet_r, funding_r,
             kapanis_gun: pd.Series) -> pd.DataFrame:
    """İşlem başına günlük MTM yolu (modül belgesi). Girdiler işlem sırasında hizalı dizilerdir; stop_mesafe fiyat birimidir
    (risk$/miktar). -> DataFrame(islem_no int32, gun UTC, kum_r float32)."""
    giris = pd.DatetimeIndex(giris).as_unit("ns")
    cikis = pd.DatetimeIndex(cikis).as_unit("ns")
    yon = np.asarray(yon, dtype=float)
    gf = np.asarray(giris_fiyati, dtype=float)
    sm = np.asarray(stop_mesafe, dtype=float)
    r_son = np.asarray(r_son, dtype=float)
    gm = np.asarray(giris_maliyet_r, dtype=float)
    fr = np.asarray(funding_r, dtype=float)
    kap = kapanis_gun.to_numpy(dtype=float)
    kidx = pd.DatetimeIndex(kapanis_gun.index).as_unit("ns")
    t0 = kidx[0]
    gun_ns = pd.Timedelta(1, "D").value
    g0 = np.floor_divide(giris.floor("D").asi8 - t0.value, gun_ns)
    g1 = np.floor_divide(cikis.floor("D").asi8 - t0.value, gun_ns)
    no, gunler, deger = [], [], []
    for i in range(len(giris)):
        a, b = int(g0[i]), int(g1[i])
        if a < 0 or b >= len(kap) + 1 or b < a:
            raise ValueError(f"MTM: işlem {i} gün aralığı kapanış serisi dışında ({a}, {b}, {len(kap)})")
        if b > a:
            gn = np.arange(a, b)
            gun_sonu = t0.value + (gn + 1) * gun_ns
            sure = float(cikis.asi8[i] - giris.asi8[i])
            pay = np.clip((gun_sonu - giris.asi8[i]) / sure, 0.0, 1.0)
            v = yon[i] * (kap[gn] - gf[i]) / sm[i] - gm[i] - fr[i] * pay
            no.append(np.full(len(gn), i, dtype=np.int32))
            gunler.append(gn)
            deger.append(v)
        no.append(np.array([i], dtype=np.int32))
        gunler.append(np.array([b]))
        deger.append(np.array([r_son[i]]))
    if not no:
        return _MTM_BOS.copy()
    g = np.concatenate(gunler)
    return pd.DataFrame({"islem_no": np.concatenate(no),
                         "gun": pd.DatetimeIndex(t0 + pd.to_timedelta(g, unit="D")),
                         "kum_r": np.concatenate(deger).astype(np.float32)})


_MTM_BOS = pd.DataFrame({"islem_no": np.array([], dtype=np.int32),
                         "gun": pd.DatetimeIndex([], tz="UTC").as_unit("ns"), "kum_r": np.array([], dtype=np.float32)})
_HAM_BOS = we._BOSLUK.assign(fonlama_r=np.array([], dtype=np.float32))


def islem_hazirla(islemler: pd.DataFrame, sembol: str, tf: str, carpan: float, mumlar: pd.DataFrame,
                  tablo_yolu, kapanis_gun: Optional[pd.Series] = None) -> tuple:
    """Motor işlem tablosu -> (ham DataFrame, mtm DataFrame). TradFi funding (1.2) burada uygulanır: r funding dahil."""
    d = islemler.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
    if not len(d):
        return _HAM_BOS.copy(), _MTM_BOS.copy()
    r0 = d["r"].to_numpy(dtype=float)
    if not np.isfinite(r0).all():
        raise ValueError("işlem R'si NaN/sonsuz (stop riski 0?)")
    net = d["net_pnl"].to_numpy(dtype=float)
    miktar = d["miktar"].to_numpy(dtype=float)
    gf = d["giris_fiyati"].to_numpy(dtype=float)
    nominal = miktar * gf
    with np.errstate(divide="ignore", invalid="ignore"):
        risk = np.where(r0 != 0.0, net / r0, np.nan)             # r = net/risk$ -> risk$ (r != 0'da tam; float duyarlığı)
    bos = ~(np.isfinite(risk) & (risk > 0))
    if bos.any():                                                 # r == 0 tam: komşu satırın stop oranı (v1 islem_ozet ile aynı kural)
        sf_k = pd.Series(np.where(bos, np.nan, risk / nominal)).ffill().bfill().fillna(sabit.SF_YEDEK).to_numpy()
        risk = np.where(bos, sf_k * nominal, risk)
    oran = evren_maliyet.funding_long_8s_oran(sembol, tablo_yolu)
    fon_usd = maliyet.funding_maliyeti_usd(d["yon"], miktar, gf, d["giris_zamani"], d["cikis_zamani"], oran)
    fon_r = fon_usd / risk
    r = r0 - fon_r
    taker = evren_maliyet.sembol_maliyeti(sembol, carpan, tablo_yolu)[0] / 100.0
    giris_kom_r = nominal * taker / risk
    gercek_fon_r = d["funding"].to_numpy(dtype=float) / risk                # motorun gerçek (kripto) funding'i, zaten r0 içinde
    toplam_fon_r = fon_r + gercek_fon_r
    stop_fiyat = risk / miktar
    sf = np.clip(risk / nominal, sabit.SF_TABAN, None)
    ham = pd.DataFrame({
        "ayar_no": np.zeros(len(d), dtype=np.int16),
        "giris_zamani": pd.DatetimeIndex(d["giris_zamani"]).as_unit("ns"),
        "cikis_zamani": pd.DatetimeIndex(d["cikis_zamani"]).as_unit("ns"),
        "yon": d["yon"].to_numpy(dtype=np.int8), "r": r.astype(np.float32), "sf": sf.astype(np.float32),
        "stop_mesafe": stop_fiyat.astype(np.float32), "fonlama_r": fon_r.astype(np.float32)})
    kg = kapanis_gun if kapanis_gun is not None else _kapanis_onbellekli(sembol, tf, mumlar)
    mtm = mtm_yolu(d["giris_zamani"], d["cikis_zamani"], d["yon"], gf, stop_fiyat, r, giris_kom_r, toplam_fon_r, kg)
    return ham, mtm


_KG: dict = {}


def _kapanis_onbellekli(sembol: str, tf: str, mumlar: pd.DataFrame) -> pd.Series:
    """Aynı (sembol, tf, mum nesnesi) için günlük kapanış serisi bir kez hesaplanır (grup içi çok strateji)."""
    k = (sembol, tf, id(mumlar))
    if k not in _KG:
        if len(_KG) >= sabit.ONBELLEK_BOYUT:
            _KG.clear()
        _KG[k] = (mumlar, gunluk_kapanis(mumlar, tf))        # mumlar nesnesi tutulur: id yeniden kullanımı önlenir
    return _KG[k][1]


def _yaz_atomik(df: pd.DataFrame, yol: Path):
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol)


def _yan_yaz(yol: Path, meta: dict):
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".jtmp")
    gecici.write_text(json.dumps(meta, ensure_ascii=False, default=str))
    gecici.replace(yol)


def _meta_taslak(ad, tf, sembol, carpan, tablo_hash, etiket="") -> dict:
    return {"strateji": ad, "tf": tf, "sembol": sembol, "carpan": carpan, "ayar": etiket, "veri_yok": False, "hata": "",
            "donem": sabit.DONEM, "maliyet_hash": tablo_hash}


# ============================================================================ tek-grafik görev
def ham_gorev(ad: str, tf: str, sembol: str, carpan: float, cikti: Path, tablo_yolu, tablo_hash: str,
              yeniden: bool = False, _veri=None) -> dict:
    """Tek (strateji, tf, sembol, çarpan). Yan dosya en son yazılır; biten atlanır. veri_ayarla(...) kurulu olmalı.
    HoldoutSizintisi yukarı fırlar (yan dosya YAZILMAZ). Diğer hatalar yan dosyaya 'hata' olarak yazılır (sayılır)."""
    cd = carpan_adi(carpan)
    hd, md = Path(cikti) / "ham" / cd, Path(cikti) / "mtm" / cd
    yol = dosya_yolu(hd, ad, tf, sembol)
    yan = yol.with_suffix(".json")
    if yan.exists() and not yeniden:
        return {"atlandi": True}
    t0 = time.perf_counter()
    meta = _meta_taslak(ad, tf, sembol, carpan, tablo_hash)
    try:
        mumlar, fund = (_veri or veri_oku)(sembol, tf)
    except (FileNotFoundError, ValueError) as e:                  # bu tf'de verisi olmayan enstrüman dışarıda (v1 K-B)
        meta.update(veri_yok=True, hata=f"{type(e).__name__}: {e}"[:200])
        _yan_yaz(yan, meta)
        return meta
    sizinti_kontrol(sembol, tf, mumlar, fund)
    if not len(mumlar):
        meta.update(veri_yok=True, hata="dönem içinde mum yok")
        _yan_yaz(yan, meta)
        return meta
    try:
        etiket, st = varsayilan_strateji(ad)
        meta["ayar"] = etiket
        kurallar = we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
        ay = evren_maliyet.maliyet_ayarlari(sembol, kurallar, carpan, tablo_yolu)
        hazir = funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf)
        res = backtest(hazir, st, ay, fund)
        ham, mtm = islem_hazirla(res.islemler, sembol, tf, carpan, mumlar, tablo_yolu)
    except Exception as e:  # noqa: BLE001  (sayılır: yan dosyada 'hata'; eleme aşaması satırı 'hata' yapar)
        meta.update(hata=f"{type(e).__name__}: {e}"[:300], sure_sn=round(time.perf_counter() - t0, 2))
        _yan_yaz(yan, meta)
        return meta
    _yaz_atomik(ham, yol)
    _yaz_atomik(mtm, dosya_yolu(md, ad, tf, sembol))
    meta.update(n_islem=int(len(ham)), n_mtm=int(len(mtm)), veri_bas=str(mumlar.index[0]), veri_bit=str(mumlar.index[-1]),
                sure_sn=round(time.perf_counter() - t0, 2))
    _yan_yaz(yan, meta)
    return meta


# ============================================================================ portföy görevi
def varsayilan_pf(ad: str, evren_t: tuple):
    """1.1 (portföy): sınıfın varsayılan ayarı (csv bağlamaları/ızgara DEĞİL). Evrene uygun değilse None."""
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    st = tum_portfoy_stratejileri()[ad]()
    etkin = st.etkin_semboller(evren_t)
    st = st.yeni(semboller=etkin) if etkin else st
    return st if st.uygun_mu(evren_t) else None


def maliyet_pf(semboller, carpan: float, tablo_yolu):
    from motor.portfoy.motor import PortfoyAyarlari
    ms = {s: evren_maliyet.sembol_maliyeti(s, carpan, tablo_yolu) for s in semboller}
    return PortfoyAyarlari(limit_modu="olc", maliyet_sembol=ms, komisyon_taker_yuzde=max(v[0] for v in ms.values()),
                           komisyon_maker_yuzde=max(v[1] for v in ms.values()),
                           kayma_bps=max(v[2] for v in ms.values()), stop_kayma_bps=max(v[3] for v in ms.values()))


def pf_fonlama_duzeltmesi(getiri: pd.Series, ozsermaye: pd.Series, poz: pd.DataFrame, veriler: dict, tablo_yolu) -> tuple:
    """Portföy günlük getirisine TradFi funding (1.2): DK_ sembolünde net LONG miktar × kapanış × oran × (24/8) / önceki gün
    özsermayesi her gün getiriden düşer (short geliri yok). Yaklaşık (motor değişmedi): fonlama özsermayeye geri beslenmez.
    -> (düzeltilmiş getiri, toplam fonlama maliyeti (özsermaye oranı toplamı))."""
    gun_ps = sabit.GUN_SAAT / sabit.FUNDING_PERIYOT_SAAT
    ozs = ozsermaye.copy()
    ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
    ozs = ozs.groupby(level=0).last()
    onceki = ozs.shift(1).fillna(ozs)                  # ilk gün: kendi özsermayesi
    maliyet_oran = pd.Series(0.0, index=getiri.index)
    for s in poz.columns:
        oran = evren_maliyet.funding_long_8s_oran(s, tablo_yolu)
        if oran <= 0 or s not in veriler:
            continue
        q = poz[s].copy()
        q.index = pd.DatetimeIndex(q.index).floor("D")
        q = q.groupby(level=0).last().clip(lower=0.0)
        kap = veriler[s]["kapanis"].copy()
        kap.index = pd.DatetimeIndex(kap.index).floor("D")
        kap = kap.groupby(level=0).last()
        usd = (q * kap.reindex(q.index)).fillna(0.0) * oran * gun_ps
        maliyet_oran = maliyet_oran.add((usd / onceki).reindex(getiri.index).fillna(0.0), fill_value=0.0)
    return getiri - maliyet_oran, float(maliyet_oran.sum())


def pf_gorev(ad: str, carpan: float, cikti: Path, tablo_yolu, tablo_hash: str, evren_adi: str = "genel",
             yeniden: bool = False) -> dict:
    """Portföy (pf__) satırı: varsayılan ayar, geliştirme dönemi tek koşu. Yol = günlük özsermaye getirisi (+ yeniden dengeleme
    günü bayrağı); meta: kill_olayi, n_dengeleme, veri_bas (sembol başına, analiz başlangıcı için)."""
    from motor.arastirma import wf_evren_portfoy as wep
    from motor.arastirma import wf_portfoy as wp
    from motor.portfoy.motor import portfoy_backtest   # noqa: F401  (wep._kos kullanır)
    cd = carpan_adi(carpan)
    hd = Path(cikti) / "ham" / cd
    yol = dosya_yolu(hd, ad, "1d", PF_SEMBOL)
    yan = yol.with_suffix(".json")
    if yan.exists() and not yeniden:
        return {"atlandi": True}
    t0 = time.perf_counter()
    meta = _meta_taslak(ad, "1d", PF_SEMBOL, carpan, tablo_hash, "varsayilan")
    meta["portfoy"] = True
    try:
        evren = sabit.evren_listesi(evren_adi)
        v, f, dis = wep.veri_yukle(evren, "1d")
        for s, df in v.items():
            sizinti_kontrol(s, "1d", df, f.get(s))
        meta["disarida"] = list(dis)
        evren_t = tuple(v)
        st = varsayilan_pf(ad, evren_t)
        if st is None:
            raise RuntimeError("varsayılan ayar bu evrende uygun değil (yeterli sembol/çift yok)")
        ay = maliyet_pf(evren_t, carpan, tablo_yolu)
        r = wep._kos(st, v, f, evren_t, ay, 0)
        ozs = r.gunluk_ozsermaye.copy()
        ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
        ozs = ozs.groupby(level=0).last().astype(float)
        getiri = ozs.pct_change().fillna(0.0)
        getiri, fon_toplam = pf_fonlama_duzeltmesi(getiri, r.gunluk_ozsermaye, r.pozisyon_gecmisi, v, tablo_yolu)
        q = r.pozisyon_gecmisi
        degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
        deng_gunleri = set(pd.DatetimeIndex(q.index[degisti.to_numpy()]).floor("D")) if len(q) else set()
        out = pd.DataFrame({"gun": pd.DatetimeIndex(getiri.index).as_unit("ns"), "getiri": getiri.to_numpy(dtype=float),
                            "dengeleme": [g in deng_gunleri for g in getiri.index]})
        kill = sum(1 for o in r.limit_olaylari if o.get("tur") == "kill_switch")
        veri_bas = {s: str(v[s].index[0]) for s in v}
        meta.update(kill_olayi=int(kill), n_dengeleme=int(len(deng_gunleri)), n_islem=int(len(r.islemler)),
                    n_enstruman=len(v), veri_bas_sembol=veri_bas,
                    veri_bas=min(veri_bas.values()), veri_bit=str(max(df.index[-1] for df in v.values())),
                    fonlama_toplam=fon_toplam, gun=int(len(out)))
    except HoldoutSizintisi:
        raise
    except Exception as e:  # noqa: BLE001  (sayılır)
        meta.update(hata=f"{type(e).__name__}: {e}"[:300], sure_sn=round(time.perf_counter() - t0, 2))
        _yan_yaz(yan, meta)
        return meta
    _yaz_atomik(out, yol)
    meta["sure_sn"] = round(time.perf_counter() - t0, 2)
    _yan_yaz(yan, meta)
    return meta


# ============================================================================ aşama: görev listesi, havuz
_AYAR: dict = {}


def _baslat(ayar: dict):
    we.veri_ayarla(ayar.get("veri_dizini"), sabit.DONEM)
    _AYAR.clear()
    _AYAR.update(ayar)


def _isci(g: dict):
    """Bir grup: (tf, sembol, carpan) için sıralı strateji listesi (tek veri yüklemesi) ya da bir portföy görevi."""
    a = _AYAR
    cikti, tablo_yolu, tablo_hash = Path(a["cikti"]), a["tablo_yolu"], a["tablo_hash"]
    son = a.get("son")
    sonuc = []
    if g["tur"] == "portfoy":
        if son is not None and time.time() > son:
            return {"ertelendi": 1, "sonuc": []}
        return {"ertelendi": 0, "sonuc": [pf_gorev(g["strateji"], g["carpan"], cikti, tablo_yolu, tablo_hash, g["evren"],
                                                   a.get("yeniden", False))]}
    erte = 0
    cache = {}

    def veri(s, t):
        if (s, t) not in cache:
            cache[(s, t)] = veri_oku(s, t)
        return cache[(s, t)]
    for ad in g["stratejiler"]:
        if son is not None and time.time() > son:
            erte += 1
            continue
        sonuc.append(ham_gorev(ad, g["tf"], g["sembol"], g["carpan"], cikti, tablo_yolu, tablo_hash,
                               a.get("yeniden", False), _veri=veri))
    return {"ertelendi": erte, "sonuc": sonuc}


def gorevleri_uret(havuz: pd.DataFrame, cikti: Path, stratejiler=None, semboller=None, carpanlar=sabit.MALIYET_CARPANLARI,
                   hatalari_yeniden: bool = False) -> tuple:
    """-> (gruplar, toplam_gorev, kalan_gorev). Biten (yan dosyası olan) görev listeye girmez; `hatalari_yeniden` ile hatalı
    (veri_yok olmayan) yan dosya silinip yeniden kuyruğa alınır."""
    gruplar, toplam, kalan = [], 0, 0
    sec = set(stratejiler) if stratejiler else None
    grup: dict = {}
    for _, row in havuz.iterrows():
        ad = row["strateji"]
        if sec is not None and ad not in sec:
            continue
        for c in carpanlar:
            hd = Path(cikti) / "ham" / carpan_adi(c)
            if row["stil_v2"] == "portfoy":
                toplam += 1
                if _bitti_mi(dosya_yolu(hd, ad, row["tf"], PF_SEMBOL).with_suffix(".json"), hatalari_yeniden):
                    continue
                kalan += 1
                gruplar.append({"tur": "portfoy", "strateji": ad, "tf": row["tf"], "carpan": c, "evren": row["evren"],
                                "sembol": PF_SEMBOL})
                continue
            for s in sabit.evren_listesi(row["evren"]):
                if semboller and s not in set(semboller):
                    continue
                toplam += 1
                if _bitti_mi(dosya_yolu(hd, ad, row["tf"], s).with_suffix(".json"), hatalari_yeniden):
                    continue
                kalan += 1
                grup.setdefault((row["tf"], s, c), []).append(ad)
    for (tf, s, c), adlar in sorted(grup.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        gruplar.append({"tur": "tek", "tf": tf, "sembol": s, "carpan": c, "stratejiler": sorted(adlar)})
    gruplar.sort(key=lambda g: (g["tur"] != "tek", g.get("tf", ""), g["sembol"], g["carpan"], g.get("strateji", "")))
    return gruplar, toplam, kalan


def _bitti_mi(yan: Path, hatalari_yeniden: bool) -> bool:
    if not yan.exists():
        return False
    if hatalari_yeniden:
        m = json.loads(yan.read_text())
        if m.get("hata") and not m.get("veri_yok"):
            yan.unlink()
            return False
    return True


def ham_asamasi(cikti: Path = None, surec: int = sabit.SUREC_VARSAYILAN, butce_sn: Optional[float] = None, veri_dizini=None, stratejiler=None,
                semboller=None, hatalari_yeniden: bool = False, havuz_yolu=None, muhur_yolu=None, ilerleme: bool = True) -> dict:
    """P1-1. Sonuçlar görev bitince diske yazılır (yan dosya en sonda): süreç herhangi bir anda öldürülse biten kaybolmaz;
    yeniden çalıştırınca kaldığı yerden sürer. `butce_sn` dolunca yeni görev BAŞLATILMAZ (süren görev biter)."""
    cikti = Path(cikti or sabit.CIKTI)
    havuz_muhru_dogrula(havuz_yolu, muhur_yolu)
    havuz = havuz_oku(havuz_yolu)
    tablo = maliyet.tabloyu_hazirla(cikti)
    tablo_hash = evren_maliyet.tablo_hash(tablo)
    gruplar, toplam, kalan = gorevleri_uret(havuz, cikti, stratejiler, semboller, hatalari_yeniden=hatalari_yeniden)
    if ilerleme:
        print(f"[v2 ham] toplam {toplam} görev, kalan {kalan} ({len(gruplar)} grup); maliyet tablosu {tablo.name} {tablo_hash[:12]}",
              flush=True)
    ayar = {"veri_dizini": veri_dizini, "cikti": str(cikti), "tablo_yolu": str(tablo), "tablo_hash": tablo_hash,
            "yeniden": False}
    sonuclar: list = []

    def topla(s):
        sonuclar.extend(s["sonuc"])
    ham_sonuc = we.havuz_calistir(_isci, gruplar, surec, _baslat, ayar, butce_sn, ilerleme, "v2 ham", her_sonuc=topla)
    erte = sum(s["ertelendi"] for s in ham_sonuc)
    yap = [m for m in sonuclar if not m.get("atlandi")]
    hata = [m for m in yap if m.get("hata") and not m.get("veri_yok")]
    ozet = {"toplam": toplam, "kalan_basta": kalan, "yapilan": len(yap), "ertelenen": erte,
            "veri_yok": sum(1 for m in yap if m.get("veri_yok")), "hata": len(hata),
            "hata_ornegi": hata[0]["hata"] if hata else ""}
    if ilerleme:
        print(f"[v2 ham] {ozet}", flush=True)
    return ozet


# ============================================================================ okuma (eleme/sonraki aşamalar için)
def ham_yukle(cikti: Path, carpan: float, ad: str, tf: str, evren: tuple, tablo_hash: str) -> tuple:
    """-> ({sembol: ham df}, bilgi). Yan dosyası olmayan görev varsa RuntimeError('ham koşu bitmemiş'). Bilgi: disarida (veri
    yok), hatali (hata veren semboller), veri_bas/veri_bit, n_hata, ornek. Maliyet hash'i / holdout sızıntısı kontrol edilir."""
    hd = Path(cikti) / "ham" / carpan_adi(carpan)
    ham, bilgi = {}, {"disarida": [], "hatali": [], "veri_bas": {}, "veri_bit": {}, "hata_ornegi": "", "ayar": ""}
    for s in evren:
        yol = dosya_yolu(hd, ad, tf, s)
        yan = yol.with_suffix(".json")
        if not yan.exists():
            raise RuntimeError(f"ham koşu bitmemiş: {yan.name} ({carpan_adi(carpan)})")
        m = json.loads(yan.read_text())
        if m.get("maliyet_hash") != tablo_hash:
            raise RuntimeError(f"{yan.name}: başka bir maliyet tablosuyla yapılmış")
        if not m.get("veri_yok") and m.get("veri_bit") and zaman_utc(m["veri_bit"]) >= sabit.HOLDOUT_BAS:
            raise HoldoutSizintisi(f"{yan.name}: veri_bit {m['veri_bit']} HOLDOUT_BAS ve sonrası")
        if m.get("veri_yok"):
            bilgi["disarida"].append(s)
            continue
        if m.get("hata"):
            bilgi["hatali"].append(s)
            bilgi["hata_ornegi"] = bilgi["hata_ornegi"] or m["hata"]
            continue
        ham[s] = pd.read_parquet(yol)
        bilgi["veri_bas"][s] = zaman_utc(m["veri_bas"])
        bilgi["veri_bit"][s] = zaman_utc(m["veri_bit"])
        bilgi["ayar"] = m.get("ayar", "")
    return ham, bilgi


def pf_yukle(cikti: Path, carpan: float, ad: str, tablo_hash: str) -> tuple:
    """-> (günlük DataFrame(gun, getiri, dengeleme) | None, meta). Hata/yan dosya yoksa: (None, meta) / RuntimeError."""
    yol = dosya_yolu(Path(cikti) / "ham" / carpan_adi(carpan), ad, "1d", PF_SEMBOL)
    yan = yol.with_suffix(".json")
    if not yan.exists():
        raise RuntimeError(f"ham koşu bitmemiş: {yan.name} ({carpan_adi(carpan)})")
    m = json.loads(yan.read_text())
    if m.get("maliyet_hash") != tablo_hash:
        raise RuntimeError(f"{yan.name}: başka bir maliyet tablosuyla yapılmış")
    if m.get("veri_bit") and zaman_utc(m["veri_bit"]) >= sabit.HOLDOUT_BAS:
        raise HoldoutSizintisi(f"{yan.name}: veri_bit {m['veri_bit']} HOLDOUT_BAS ve sonrası")
    if m.get("hata"):
        return None, m
    return pd.read_parquet(yol), m


def mtm_yukle(cikti: Path, carpan: float, ad: str, tf: str, sembol: str) -> pd.DataFrame:
    return pd.read_parquet(dosya_yolu(Path(cikti) / "mtm" / carpan_adi(carpan), ad, tf, sembol))
