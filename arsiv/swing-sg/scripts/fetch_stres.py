"""Hayatta kalma yanlılığı stres testi için, bugün ilk 25'te olmayan / çöken / listeden çıkan coinler (Yahoo) → data/stres."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from fetch_data import yahoo  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "stres")
STRES = ["LUNA1-USD", "FTT-USD", "EOS-USD", "XMR-USD", "MATIC-USD", "WAVES-USD", "ALGO-USD", "THETA-USD",
         "XTZ-USD", "VET-USD", "ATOM-USD", "FIL-USD", "EGLD-USD", "AXS-USD", "SAND-USD", "MANA-USD",
         "CRV-USD", "SNX-USD", "COMP-USD", "MKR-USD", "ZEC-USD", "DASH-USD", "NEO-USD", "IOTA-USD", "KSM-USD"]


def main():
    os.makedirs(OUT, exist_ok=True)
    for t in STRES:
        df = yahoo(t)
        if df is not None and len(df):
            df.to_csv(os.path.join(OUT, t.replace("-USD", "") + ".csv"), index=False, float_format="%.10g")
            print("OK", t, len(df))
        else:
            print("YOK", t)
        time.sleep(0.3)


if __name__ == "__main__":
    main()
