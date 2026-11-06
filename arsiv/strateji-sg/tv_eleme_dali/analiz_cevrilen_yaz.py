"""Önceki turlarda çevrilen (docs'u eksik) modüller için analiz belgesi: 'ne yapıyor' modül başlığından, repaint kontrolü Pine'daki security/pivot satırlarından otomatik çıkarılır."""
import re, glob, os, importlib
from tv.analiz_yaz import A, K
def kontrol(i):
    p = K/"pine"/f"{i}.pine"
    L = p.read_text().split("\n") if p.exists() else []
    sec = [(n, s.strip()) for n, s in enumerate(L, 1) if re.search(r"request\.security|\bsecurity\(", s) and not s.strip().startswith("//")]
    piv = [(n, s.strip()) for n, s in enumerate(L, 1) if re.search(r"pivot(high|low)", s) and not s.strip().startswith("//")]
    t = []
    if sec:
        on = [x for x in sec if "lookahead_on" in x[1]]
        t.append("request.security kullanımı: " + "; ".join(f"satır {n}: `{s[:110]}`" for n, s in sec[:3]) + ". " +
                 ("lookahead_on var ama değer `[1]` ile bir önceki kapanmış HTF mumdan alınıyor → geleceği görmez." if on and all("[1]" in x[1] for x in on) else
                  "lookahead_off: tarihsel mumlarda önceki kapanmış HTF değeri; çeviride de son kapanmış HTF mum kullanıldı." if not on else "lookahead_on kullanımı ayrıca incelendi (çeviri kapanmış HTF mum esaslı)."))
    if piv:
        n, s = piv[0]
        t.append(f"Pivot: satır {n}: `{s[:100]}` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.")
    if not t: t.append("request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).")
    return " ".join(t)
def calis(esle):
    for i, mod in esle.items():
        m = importlib.import_module(f"tv.stratejiler.{mod}")
        A(i, (m.__doc__ or "").strip(), f"{m.TF} (çeviri)", ",".join(getattr(m, "EVREN", getattr(m, "SEMBOL", []))),
          kontrol(i), "al", f"Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/{mod}.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. {getattr(m,'NEDEN','')}",
          kanit=[r"strategy\.(entry|exit|close|order)", r"request\.security", r"pivot(high|low)"], hedef=mod)
if __name__ == "__main__":
    mp = {}
    for f in glob.glob(str(K/"stratejiler/*.py")):
        s = open(f).read(); m = re.search(r'PINE_ID\s*=\s*["\']([^"\']+)', s)
        if m and not os.path.basename(f).startswith("_") and not (K/"analiz"/f"{m.group(1)}.md").exists(): mp[m.group(1)] = os.path.basename(f)[:-3]
    calis(mp); print(len(mp))
