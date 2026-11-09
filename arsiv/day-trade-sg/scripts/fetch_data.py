"""Tüm evren için veriyi çeker ve data/cache altına yazar.

Kullanım: python scripts/fetch_data.py [--days 365] [--tfs 5m 15m 1h 4h]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daytrade import data as D  # noqa: E402
from daytrade import universe as U  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365, help="kripto için geçmiş gün sayısı")
    ap.add_argument("--tfs", nargs="+", default=["5m", "15m", "1h", "4h"])
    ap.add_argument("--only", nargs="*", help="yalnızca bu varlık sınıfları")
    ap.add_argument("--symbols", nargs="*", help="yalnızca bu semboller (BTCUSDT, AAPL ...)")
    ap.add_argument("--workers", type=int, default=1, help="paralel indirme sayısı")
    ap.add_argument("--start", help="yalnız bu tarihten (YYYY-AA-GG) itibaren (kripto, önbelleği ezer)")
    ap.add_argument("--end", help="bu tarihe kadar (YYYY-AA-GG)")
    ap.add_argument("--ekstra", nargs="*", default=[],
                    help="evrene eklenecek ek kripto sembolleri (ör. LUNA FTT; stres testi)")
    a = ap.parse_args()

    conn = D.check_connectivity()
    print("Bağlantı:", conn)
    crypto_list, bist_list = None, None
    if conn["coingecko"] and conn["binance"]:
        try:
            crypto_list = U.refresh_crypto_top25(D._session())
        except Exception as e:
            print("Kripto listesi yenilenemedi:", e)
    if conn["yahoo"]:
        try:
            bist_list = U.refresh_bist_top10(D._session())
        except Exception as e:
            print("BIST listesi yenilenemedi:", e)
    insts = U.build_universe(crypto_list, bist_list) + [U.crypto(x) for x in a.ekstra]
    if a.only:
        insts = [i for i in insts if i.asset_class in a.only]
    Path("data").mkdir(exist_ok=True)
    Path("data/universe.json").write_text(json.dumps(
        [i.__dict__ for i in insts], ensure_ascii=False, indent=1))
    if a.symbols:
        insts = [i for i in insts if i.symbol in a.symbols]
    todo = [i for i in insts if conn["binance" if i.source == "binance" else "yahoo"]]
    for i in insts:
        if i not in todo:
            print(f"ATLA {i.symbol}: {i.source} erişilemiyor")

    def one(inst):
        for tf in a.tfs:
            days = a.days if tf != "5m" else min(a.days, 180)
            try:
                if a.start and inst.source == "binance":
                    import pandas as pd
                    t0 = pd.Timestamp(a.start, tz="UTC")
                    t1 = pd.Timestamp(a.end, tz="UTC") if a.end else pd.Timestamp.now(tz="UTC")
                    df = D.fetch_binance_arsiv(inst.symbol, tf, t0, t1)   # delist edilenler dahil
                    D.save(inst, tf, df)
                else:
                    df = D.update(inst, tf, days=days)
                print(f"{inst.symbol:12s} {tf:4s} {len(df):7d} mum  "
                      f"{df.index[0] if len(df) else '-'} → {df.index[-1] if len(df) else '-'}", flush=True)
            except Exception as e:
                print(f"HATA {inst.symbol} {tf}: {e}", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, todo))


if __name__ == "__main__":
    main()
