"""Güncel sinyal taraması: son kapanışa göre ertesi gün uygulanacak emirleri ve sistemin
backtest'e göre hâlen açık tuttuğu pozisyonları listeler. Çıktı: sinyaller/GUNCEL.md"""
import os

import pandas as pd

from .ayarlar import RISK, SECILI, SINIFLAR
from .motor import calistir
from .stratejiler import STRATEJILER, haftalik_yon
from .veri import ENDEKS_VERI, KOK, MALIYET, tum_veriler

YON_AD = {1: "YUKARI", 0: "NÖTR", -1: "AŞAĞI"}


def tara():
    yeni, acik, yonler = [], [], []
    for ad, (df, sinif) in tum_veriler().items():
        yonler.append({"varlik": ad, "sinif": sinif, "son_tarih": df.index[-1].date(),
                       "kapanis": df["Close"].iloc[-1],
                       "haftalik_HA": YON_AD[int(haftalik_yon(df, "ha").iloc[-1])],
                       "haftalik_EMA10/30": YON_AD[int(haftalik_yon(df, "ema10_30").iloc[-1])]})
        for st, p in SECILI.items():
            if sinif not in SINIFLAR[st]:
                continue
            sig = STRATEJILER[st](df, {**p, "_endeks": ENDEKS_VERI.get(sinif)})
            son = sig.iloc[-1]
            if son["long"]:
                lim = son.get("limit_long", float("nan"))
                stop = son["stop_long"]
                ref = lim if pd.notna(lim) else df["Close"].iloc[-1]
                yeni.append({"strateji": st, "varlik": ad, "sinif": sinif, "emir": "AL",
                             "giris": "limit %.6g" % lim if pd.notna(lim) else "açılışta piyasa",
                             "stop": float("%.6g" % stop), "stop_%": f"{(ref - stop) / ref:.1%}",
                             "kismi_kar": (float("%.6g" % (ref + p["kismi_R"] * (ref - stop))) if p.get("kismi_R") else "-"),
                             "agirlik_%": f"{min(RISK / ((ref - stop) / ref), 0.20):.1%}"})
            for t in calistir(ad, sinif, df, sig, MALIYET[sinif], st):
                if t.neden == "acik":
                    acik.append({"strateji": st, "varlik": ad, "giris_tarih": t.giris_tarih.date(),
                                 "giris": float("%.6g" % t.giris), "ilk_stop": float("%.6g" % t.stop0),
                                 "son": float("%.6g" % t.cikis), "getiri": f"{t.getiri:+.1%}"})
    return pd.DataFrame(yeni), pd.DataFrame(acik), pd.DataFrame(yonler)


def _tablo(df):
    if df.empty:
        return "_yok_\n"
    return df.to_markdown(index=False) + "\n"


if __name__ == "__main__":
    yeni, acik, yonler = tara()
    os.makedirs(os.path.join(KOK, "sinyaller"), exist_ok=True)
    yol = os.path.join(KOK, "sinyaller", "GUNCEL.md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("# Güncel Sinyaller\n\n")
        f.write(f"_Son veri: {yonler['son_tarih'].max()} — emirler bir sonraki işlem günü açılışında geçerlidir._\n\n")
        f.write("## Yeni giriş sinyalleri\n\n" + _tablo(yeni) + "\n")
        f.write("## Sistemin açık pozisyonları (backtest kurallarına göre)\n\n" + _tablo(acik) + "\n")
        f.write("## Haftalık yön tablosu\n\n" + _tablo(yonler) + "\n")
    print(open(yol, encoding="utf-8").read()[:3000])
