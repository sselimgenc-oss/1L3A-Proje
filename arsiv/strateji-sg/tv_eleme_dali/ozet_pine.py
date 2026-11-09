"""Pine özet aracı: python3 -m tv.ozet_pine <id> [<id>...] — strategy() bildirimi + anahtar satırlar (satır numarasıyla)."""
import re, sys, pathlib
K = pathlib.Path(__file__).parent
ANAHTAR = [("LOOKAHEAD", r"lookahead"), ("SECURITY", r"request\.security|\bsecurity\("), ("TICK", r"calc_on_every_tick|calc_on_order_fills|process_orders_on_close"),
 ("PYR", r"pyramiding"), ("PIVOT/ZZ", r"pivothigh|pivotlow|ta\.pivot|zigzag|ZigZag"), ("EMIR", r"strategy\.(entry|exit|order|close|close_all|cancel)"),
 ("DCA/GRID", r"dca|DCA|grid|Grid|martingale|safety|doubling|averag|multiplier|scale.?in|so_"), ("QTY", r"default_qty|qty\s*=|initial_capital|commission|slippage")]
def ozet(i, maks=60):
    p = K/"pine"/f"{i}.pine"
    if not p.exists(): print(f"== {i}: KAPALI"); return
    L = p.read_text().split("\n")
    print(f"== {i}: {len(L)} satır")
    for n, s in enumerate(L, 1):
        if re.search(r"^\s*(strategy|indicator)\(", s) or re.match(r"\s*//@version", s):
            blok = s
            j = n
            while blok.count("(") > blok.count(")") and j < len(L): blok += " " + L[j].strip(); j += 1
            print(f"  {n}: {blok[:400]}")
    g = 0
    for n, s in enumerate(L, 1):
        if s.strip().startswith("//"): continue
        for ad, pat in ANAHTAR:
            if re.search(pat, s):
                print(f"  {n:4d} [{ad}] {s.strip()[:170]}"); g += 1; break
        if g >= maks: print("  ..."); break
if __name__ == "__main__":
    for i in sys.argv[1:]: ozet(i)
