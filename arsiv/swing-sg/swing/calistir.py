"""Tüm varlıklarda strateji backtest'i ve raporlama."""
import pandas as pd

from .motor import calistir, istatistik, portfoy
from .stratejiler import STRATEJILER
from .veri import ENDEKS_VERI, MALIYET, tum_veriler

OOS_BASLANGIC = pd.Timestamp("2023-01-01")
_VERI = None


def veriler():
    global _VERI
    if _VERI is None:
        _VERI = tum_veriler()
    return _VERI


def islemler(strateji, params=None, siniflar=None):
    f = STRATEJILER[strateji]
    out = []
    for ad, (df, sinif) in veriler().items():
        if siniflar and sinif not in siniflar:
            continue
        sig = f(df, {**(params or {}), "_endeks": ENDEKS_VERI.get(sinif)})
        out += calistir(ad, sinif, df, sig, MALIYET[sinif], strateji)
    return out


def ozet(trades, etiket=""):
    ist = istatistik(trades)
    ins = istatistik([t for t in trades if t.giris_tarih < OOS_BASLANGIC])
    oos = istatistik([t for t in trades if t.giris_tarih >= OOS_BASLANGIC])
    pf = portfoy(trades)
    return {"etiket": etiket, "tum": ist, "IS": ins, "OOS": oos, "portfoy": pf}


def yazdir(o):
    def f(s):
        if not s.get("islem"):
            return "işlem yok"
        return (f"n={s['islem']:4d} WR={s['kazanma_orani']:.1%} PF={s['kar_faktoru']:.2f} PF_R={s['kar_faktoru_R']:.2f} "
                f"ortR={s['ort_R']:+.2f} ort%={s['ort_getiri']:+.2%} gün={s['ort_gun']:.1f}")
    p = o["portfoy"]
    print(f"== {o['etiket']}")
    print(f"   TÜM : {f(o['tum'])}")
    print(f"   IS  : {f(o['IS'])}")
    print(f"   OOS : {f(o['OOS'])}")
    if p:
        print(f"   PORTFÖY: CAGR={p['yillik_getiri']:.1%} toplam={p['toplam_getiri']:.0%} "
              f"maxDD={p['max_dusus']:.1%} Sharpe={p['sharpe_aylik']:.2f} alınan={p['alinan_islem']}")


def sinif_kirilim(trades, anahtar="sinif"):
    rows = []
    for s in sorted({getattr(t, anahtar) for t in trades}):
        for per, f in (("IS", lambda t: t.giris_tarih < OOS_BASLANGIC), ("OOS", lambda t: t.giris_tarih >= OOS_BASLANGIC)):
            st = istatistik([t for t in trades if getattr(t, anahtar) == s and f(t)])
            if st.get("islem"):
                rows.append({anahtar: s, "donem": per,
                             **{k: round(st[k], 3) for k in ("islem", "kazanma_orani", "kar_faktoru_R", "ort_R")}})
    return pd.DataFrame(rows)


def yillik_kirilim(trades):
    rows = []
    for y in sorted({t.giris_tarih.year for t in trades}):
        st = istatistik([t for t in trades if t.giris_tarih.year == y])
        rows.append({"yil": y, **{k: round(st[k], 3) for k in ("islem", "kazanma_orani", "kar_faktoru_R", "ort_R")}})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    for ad in STRATEJILER:
        tr = islemler(ad)
        yazdir(ozet(tr, ad))
        print(sinif_kirilim(tr).to_string(index=False))
