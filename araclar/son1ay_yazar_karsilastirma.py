"""Son 1 ay adayları: KAYNAK DEFAULT ayarlarının bizim motorda (maliyet dahil) KİLİT ÖNCESİ verideki sonucu, yazarın
beyan ettiği dönemin kilit öncesi kısmıyla. Seçim/eleme için KULLANILMAZ (yalnız yazar beyanıyla yan yana kıyas).
Kullanım: python araclar/son1ay_yazar_karsilastirma.py  -> sonuclar/son1ay_yazar_karsilastirma.csv
"""
from pathlib import Path

import pandas as pd

from motor.arastirma import tarama, wf_portfoy as wfp, wf_tarama as wf
from motor.arastirma.kilit_testi import KILIT, _tek_veri
from motor.backtest.motor import backtest
from motor.portfoy import veri as pveri
from motor.portfoy.motor import portfoy_backtest
from motor.strateji import funding, kayit

KOK = Path(__file__).resolve().parents[1]


def tek(strateji, sembol, tf, bas, **par):
    mumlar, fund = _tek_veri(sembol, tf, None, KILIT)            # kilit kapalı
    st = kayit.al(strateji)(**par)
    ay = wf.maliyet_ayarlari(tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL))
    r = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st, ay, fund, islem_baslangic=pd.Timestamp(bas, tz="UTC"))
    isl = r.islemler
    isl = isl[pd.DatetimeIndex(isl["giris_zamani"]) >= pd.Timestamp(bas, tz="UTC")] if len(isl) else isl
    m = wf.oos_metrikleri(isl, pd.Timestamp(bas, tz="UTC"), KILIT)
    m.update(wf.al_tut_metrikleri(mumlar, pd.Timestamp(bas, tz="UTC"), KILIT))
    return {"aday": f"{strateji} {sembol} {tf}", "donem": f"{bas} .. 2025-10-31", "islem": m["islem_sayisi"],
            "net": m["net_getiri"], "pf": m["profit_factor"], "max_dusus": m["max_dusus"], "al_tut": m["bh_getiri"]}


def portfoy(strateji, evren, bas, **par):
    sembs = wfp.EVRENLER[evren]
    veriler, fund = pveri.veri_yukle(sembs, "1d", None, KILIT)
    st = wfp.tum_portfoy_stratejileri()[strateji](semboller=tuple(sembs), **par)
    r = portfoy_backtest(veriler, st, wfp.maliyet_ayarlari(), fund, islem_baslangic=pd.Timestamp(bas, tz="UTC"))
    g = r.gunluk_ozsermaye.pct_change().fillna(0.0)
    g.index = pd.DatetimeIndex(g.index).floor("D")
    g = g.groupby(level=0).last()
    g = g[g.index >= pd.Timestamp(bas, tz="UTC")].astype(float)
    bh = wfp.al_tut_getirisi(veriler, tuple(sembs), pd.Timestamp(bas, tz="UTC"), KILIT)
    return {"aday": f"{strateji} {evren}", "donem": f"{bas} .. 2025-10-31", "islem": len(r.islemler),
            "net": float((1 + g).prod() - 1), "sharpe": wfp.sharpe_gunluk(g.to_numpy()), "max_dusus": wfp.max_dusus(g.to_numpy()),
            "al_tut": wfp.al_tut_metrikleri(bh)["bh_getiri"]}


if __name__ == "__main__":
    s = [
        tek("dis__son1ay-donchian-adx", "ETHUSDT", "4h", "2024-02-01"),
        tek("dis__son1ay-donchian-adx", "ETHUSDT", "4h", "2025-04-01"),      # yazarın "son %40" OOS'una yakın (kilit öncesi kısmı)
        tek("dis__son1ay-donchian-adx", "BTCUSDT", "4h", "2024-02-01"),
        tek("dis__son1ay-kanal-20-10", "BTCUSDT", "4h", "2024-07-01"),
        tek("dis__son1ay-kanal-20-10", "ETHUSDT", "4h", "2024-07-01"),
        portfoy("pf__son1ay_trendrider", "kripto", "2024-03-01"),
        portfoy("pf__son1ay_trendrider", "kripto", "2024-03-01", agirlik="esit"),
        portfoy("pf__son1ay_e014", "makro", "2024-01-01"),
        portfoy("pf__son1ay_e014", "makro", "2020-01-05"),          # WF OOS aralığında sabit kaynak-default (bilgi)
        portfoy("pf__son1ay_trendrider", "kripto", "2022-09-15"),   # WF OOS aralığında sabit kaynak-default (bilgi)
    ]
    df = pd.DataFrame(s)
    df.to_csv(KOK / "sonuclar" / "son1ay_yazar_karsilastirma.csv", index=False)
    print(df.round(3).to_string())
