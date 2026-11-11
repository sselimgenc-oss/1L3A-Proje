"""Destek ön şartı (ON_KAYIT_V3 bölüm 3 notu; bölüm 6): rastgele-giriş testi saat/seans tabanlı çıkışlı satırları (6-9) DESTEKLER mi?

Bulgu (kod incelemesi, v2 `test._sembol_k2` + `evren_k2.cikis_bilgisi`): v2 yolu stratejinin gerçek geçmişteki `cikis` / `cikis_long` /
`cikis_short` boolean dizilerini rastgele girişe de uygular ve tutma süresini `min(h, n-1-j)` ile kırpar. Saat/seans tabanlı çıkışlarda
bu, rastgele işlemin tutma süresini (mum sayısı) KORUMAZ (sabit saatli çıkış başka bir saatteki girişte erken tetiklenir; durumlu
`cikis_long` bandı gerçek girişin seviyesine bağlıdır). v3, `rastgele.py`'deki yerel değişkeni kullanır: enstrüman, yön, stop katı ve tutma
süresi (mum) korunur, çeyrek içinden tekdüze giriş, zaman çıkışı tam h mum sonra. Bu modül (a) çıkış türünü sentetik veride sinyallerden
tespit eder, (b) desteklenmeyen modül (kısmi, basamaklı stop, ... ) var mı bakar, (c) yerel değişkenin tutma süresini ve çeyreği gerçekten
koruduğunu sentetik veride doğrular. Gerçek veride YALNIZ zaman damgası/dosya kapsamı okunur; hiçbir performans değeri hesaplanmaz."""
from __future__ import annotations

import inspect
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_k2
from motor.arastirma.v3 import sabit



def _sentetik(tf: str, bas: str = "2024-01-02", gun: int = 56) -> pd.DataFrame:
    from motor.veri.depo import aralik_suresi
    dk = int(aralik_suresi(tf) / pd.Timedelta(minutes=1))
    idx = pd.date_range(bas, periods=int(pd.Timedelta(days=gun) / pd.Timedelta(minutes=dk)), freq=f"{dk}min", tz="UTC")
    rng = np.random.default_rng(11)
    k = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, len(idx))))
    o = np.r_[k[0], k[:-1]]
    return pd.DataFrame({"acilis": o, "yuksek": np.maximum(o, k) * 1.001, "dusuk": np.minimum(o, k) * 0.999, "kapanis": k,
                         "hacim": 1000.0 + rng.uniform(0, 100, len(idx))}, index=idx)


def _probe_strateji(ad: str):
    """Sentetik probe için strateji nesnesi (pre-FOMC: takvim enjekte edilir; gerçek takvim dosyası okunmaz)."""
    from motor.strateji import kayit
    sinif = kayit.al(ad)
    if "takvim" in inspect.signature(sinif.__init__).parameters:
        return sinif(takvim=[pd.Timestamp("2024-01-31 19:00", tz="UTC"), pd.Timestamp("2024-03-20 18:00", tz="UTC")])
    return sinif()


def cikis_turu(st, tf: str) -> dict:
    """Sentetik veride stratejinin sinyal çerçevesinden çıkış türü: hangi çıkış sütunları var/True."""
    s = st.sinyaller(_sentetik(tf))
    sut = [c for c in ("cikis", "cikis_long", "cikis_short", "gun_sonu_kapanis") if c in s.columns and bool(s[c].fillna(False).any())]
    return {"sinyal_cikis_sutunlari": sut, "hedef": "hedef" in s.columns and bool(s["hedef"].notna().any())}


def _yerel_degisken_testi(tf: str) -> Optional[str]:
    """Sentetik veride yerel değişkenin tutma süresini ve çeyreği koruduğunu doğrular. Hata metni ya da None."""
    from motor.arastirma.v3 import rastgele
    from motor.backtest.motor import MotorAyarlari
    m = _sentetik(tf, "2023-12-01", 150)
    idx = m.index
    gi = [int(x) for x in np.linspace(300, len(idx) - 400, 9)]
    hold = [3, 4, 7, 12, 21, 3, 5, 9, 4]
    d = pd.DataFrame({"giris_zamani": idx[gi], "cikis_zamani": [idx[g + h] for g, h in zip(gi, hold)], "yon": [1] * 9,
                      "stop_mesafe": [float(m["kapanis"].iloc[g]) * 0.02 for g in gi]})
    ayr: list = []
    rastgele.sembol_simule(d, m, MotorAyarlari(), 50, np.random.default_rng(1), ayrinti=ayr)
    if not ayr:
        return "hiç kabul edilen rastgele işlem yok"
    qb, qe = rastgele.v2test.ceyrek_sinirlari(d["giris_zamani"])
    for k, j, h in ayr:
        if h != hold[k]:
            return f"tutma süresi korunmadı (işlem {k}: {h} != {hold[k]})"
        if not (qb[k] <= idx[j] < qe[k]):
            return f"giriş çeyrek dışında (işlem {k}: {idx[j]})"
        if j + h > len(idx) - 1:
            return "tutma süresi veri sonunu aşıyor"
    return None


def satir_destek_st(satir, st) -> dict:
    """Bir satır + strateji nesnesi için destek kararı. ok: True/False; neden: metin."""
    out = {"no": satir.no, "strateji": satir.strateji, "tur": satir.tur}
    if satir.tur == "portfoy":
        out.update(ok=True, neden=("rastgele-ağırlık testi (sp.RastgeleAgirlik; saat tabanlı çıkış yok)" if satir.rastgele == "agirlik"
                                   else "rastgele test uygulanmaz (P4 yalnız kesitsel satırlar 2-4)"),
                   cikis="portfoy", v2_tutma_korur=None, kullanilan="yok" if satir.rastgele != "agirlik" else "rastgele-agirlik")
        return out
    dm = evren_k2.desteklenmeyen(st.cikis_ayarlari)
    ct = cikis_turu(st, satir.tf)
    saat_tabanli = bool(ct["sinyal_cikis_sutunlari"])
    out.update(cikis=",".join(ct["sinyal_cikis_sutunlari"]) or "yok", hedef=ct["hedef"], desteklenmeyen_modul=",".join(dm),
               v2_tutma_korur=not saat_tabanli, kullanilan="v3.rastgele (tutma süresi mum sayısı korunur)")
    if dm:
        out.update(ok=False, neden=f"desteklenmeyen çıkış modülü: {', '.join(dm)} (rastgele girişte uygulanamaz)")
        return out
    hata = _yerel_degisken_testi(satir.tf)
    if hata:
        out.update(ok=False, neden=f"v3 rastgele-giriş yerel değişkeni sentetik doğrulamada başarısız: {hata}")
        return out
    out.update(ok=True, neden=("saat/seans tabanlı çıkış var (v2 yolu tutma süresini korumaz); v3 yerel değişkeni tutma süresini ve çeyreği "
                               "korur (sentetik doğrulama geçti)" if saat_tabanli else
                               "çıkış sinyali yok; v3 yerel değişkeni (v2 ile aynı sonuç türü) sentetik doğrulamada geçti"))
    return out


def gercek_kapsam(satir) -> dict:
    """Gerçek verinin YALNIZ zaman damgası kapsamı (performans hesaplanmaz). Dosya yoksa ok=False."""
    from motor.arastirma.v3 import veri as v3veri
    from motor.veri import depo
    out = {}
    for s in tuple(satir.evren) + tuple(satir.rapor_evren):
        kaynaklar = [a for a in ("5m", "1h") if depo.mum_yolu(s, a).exists()]
        if not kaynaklar:
            out[s] = {"ok": False, "neden": "mum dosyası yok"}
            continue
        kay = kaynaklar[0]
        d = pd.read_parquet(depo.mum_yolu(s, kay), columns=["kapanis"])
        out[s] = {"ok": True, "kaynak": kay, "ilk": str(d.index.min()), "son": str(d.index.max()),
                  "veri_sonu_kesilir": bool(d.index.max() >= sabit.VERI_SONU)}
    if satir.strateji == "v3__pre-fomc-surunme":
        from motor.strateji.dis.v3_adaylar_5 import fomc_takvimi_yukle
        out["fomc_olay_sayisi"] = len(fomc_takvimi_yukle())
    return out


def destek_kontrol(satirlar=None, gercek: bool = False) -> list:
    """Her satır için {'no','strateji','ok','neden',...}. gercek=True: gerçek verinin zaman damgası kapsamı da eklenir (performans yok)."""
    from motor.arastirma.v3 import kos
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    out = []
    for s in (satirlar or sabit.satirlar()):
        if s.tur == "portfoy":
            if s.strateji not in tum_portfoy_stratejileri():
                out.append({"no": s.no, "strateji": s.strateji, "ok": False, "neden": "portföy stratejisi kayıtlı değil"})
                continue
            r = satir_destek_st(s, None)
        else:
            r = satir_destek_st(s, kos.strateji_uret(s.strateji))
        if gercek:
            r["kapsam"] = gercek_kapsam(s)
        out.append(r)
    return out
