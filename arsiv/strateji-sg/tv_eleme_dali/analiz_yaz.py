"""Betik analiz dosyası üreticisi: A(id, ...) -> tv/analiz/<id>.md ve tv/analiz/_kararlar.json (karar kaydı).
Her dosya: künye, strateji() bildirimi (Pine'dan), yazılan kanıt satırları (satır no + kod), ne yapıyor, repaint/lookahead kontrolü, karar ve gerekçe."""
import json, re, pathlib, html
K = pathlib.Path(__file__).parent
AD = K/"analiz"; AD.mkdir(exist_ok=True)
def _meta():
    m = {}
    for f in ("ham/meta.json", "ham/meta3.json"):
        p = K/f
        if p.exists():
            for x in json.load(open(p)): m[x["id"]] = x
    return m
META = _meta()
def _kanit(src_lines, desenler, maks=14):
    out = []
    for n, s in enumerate(src_lines, 1):
        if s.strip().startswith("//"): continue
        if any(re.search(d, s) for d in desenler):
            out.append(f"{n}: {s.strip()[:150]}")
            if len(out) >= maks: break
    return out
def A(i, ne, tf, pazar, kontrol, karar, gerekce, kanit=(), tur="strategy", hedef=None, tur_no=None):
    """karar: 'al' (çevrilecek/çevrildi) | 'ele'. kanit: Pine'da aranacak regex listesi (satır numarasıyla yazılır)."""
    m = META.get(i, {}); p = K/"pine"/f"{i}.pine"
    L = p.read_text().split("\n") if p.exists() else []
    d = KARARLAR.get(i, {})
    d.update(dict(karar=karar, gerekce=gerekce, tf=tf, pazar=pazar, tur=tur, hedef=hedef or d.get("hedef"), tur_no=tur_no or d.get("tur_no")))
    KARARLAR[i] = d; _kaydet()
    kn = _kanit(L, list(kanit)) if kanit else []
    deklar = ""
    for n, s in enumerate(L, 1):
        if re.match(r"\s*strategy\s*\(", s):
            b = s; j = n
            while b.count("(") > b.count(")") and j < len(L): b += " " + L[j].strip(); j += 1
            deklar = f"{n}: {re.sub(r'\\s+', ' ', b)[:420]}"; break
    t = [f"# {html.unescape(m.get('ad', i))} (`{i}`)", "",
         f"- Yazar: {m.get('yazar', '?')} · Link: {m.get('link', '')}", f"- Kaynak: {len(L)} satır Pine" if L else "- Kaynak: **kapalı / alınamadı**",
         f"- Zaman dilimi / pazar: {tf} · {pazar}", f"- **Karar: {karar.upper()}**", ""]
    if deklar: t += ["## strategy() bildirimi", "```", deklar, "```", ""]
    t += ["## Ne yapıyor", ne.strip(), ""]
    if kn: t += ["## Koddan kanıt (satır: kod)", "```"] + kn + ["```", ""]
    t += ["## Repaint / lookahead kontrolü", kontrol.strip(), "", "## Karar ve gerekçe", gerekce.strip(), ""]
    (AD/f"{i}.md").write_text("\n".join(t))
import os
KF = AD/(os.environ.get("KARAR_DOSYA") or "_kararlar.json")
KARARLAR = json.load(open(KF)) if KF.exists() else {}
def _kaydet(): KF.write_text(json.dumps(KARARLAR, ensure_ascii=False, indent=1, sort_keys=True))
