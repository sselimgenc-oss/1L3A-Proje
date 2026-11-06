"""Pine'ı sıkıştırılmış okuma: python3 -m tv.oku <id>... — yorum/çizim/tablo/uyarı satırları atılır, input'lar 'ad=varsayılan' olarak tek satırda."""
import re, sys, pathlib
K = pathlib.Path(__file__).parent
DROP = re.compile(r"^\s*((?:string|color|var string|var color|int|float)\s+\w*(?:Tip|col\w*|Col\w*|S\d|P\d|A\d|GRP\d)\s*=|//|plot|plotshape|plotchar|plotcandle|bgcolor|barcolor|fill|hline|label\.|line\.|box\.|table\.|alert|alertcondition|var\s+table|var\s+label|var\s+line|var\s+box)|table\.cell|label\.new|line\.new|box\.new|alert\(")
def oku(i):
    s = (K/"pine"/f"{i}.pine").read_text().replace("\r", "")
    out, ins = [], []
    for ln in s.split("\n"):
        t = ln.rstrip()
        if not t.strip() or DROP.search(t): continue
        m = re.match(r"\s*(?:(?:var|float|int|bool|string|color|simple|const)\s+)*(\w+)\s*=\s*input(?:\.\w+)?\((.*)", t)
        if m:
            d = re.match(r"\s*(?:defval\s*=\s*)?([^,]+)", m.group(2)); ins.append(f"{m.group(1)}={d.group(1).strip()[:30] if d else '?'}"); continue
        out.append(t[:170])
    print(f"===== {i} ({len(out)} satır kod)")
    print("INPUT:", "; ".join(ins)[:900])
    print("\n".join(out))
if __name__ == "__main__":
    for i in sys.argv[1:]: oku(i)
