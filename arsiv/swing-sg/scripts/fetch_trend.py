"""Trend kağıt botunun ihtiyaç duyduğu seriler (BTC, S&P 500, ABD 50 hisse, emtia ETF'leri) → data/genis."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from fetch_data import yahoo  # noqa: E402
from fetch_genis import EMTIA_ETF, OUT, US, dosya_adi  # noqa: E402


def main():
    os.makedirs(OUT, exist_ok=True)
    hatali = []
    for t in ["BTC-USD", "^GSPC"] + US + EMTIA_ETF:
        df = yahoo(t)
        if df is None or not len(df):
            hatali.append(t)
            continue
        df = df[df["Date"] >= "2014-01-01"]
        df.to_csv(os.path.join(OUT, dosya_adi(t) + ".csv"), index=False, float_format="%.10g")
        time.sleep(0.2)
    print("Başarısız:", hatali)
    if len(hatali) > 5:
        sys.exit(1)


if __name__ == "__main__":
    main()
