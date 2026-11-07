"""Pano (Aşama 3): durum dosyalarını okuyup TEK DOSYALIK statik HTML + terminal özeti + Telegram kısa metni üretir.

İLKE (DURUM.md Aşama 3): PANO YENİ HESAP YAPMAZ. Gösterilen her sayı durum dosyasında (motorun yazdığı) olduğu gibi vardır;
burada yalnız biçimlendirme (yüzde işareti, binlik ayraç) ve çizim ölçekleme yapılır. Tek istisna ZAMAN karşılaştırmasıdır:
dosya yaşı (şimdi - durum zamanı) motor ölmüşse eski dosyanın 'sağlıklı' görünmemesi için eşikle (saglik.json'daki
`dosya_esik_dk`) karşılaştırılır. Durum dosyası yok/bozuksa açık hata gösterilir; uydurma değer yazılmaz.
Telegram: bu modül MESAJ GÖNDERMEZ, yalnız metin üretir (`telegram_metni`).

CLI: python -m motor.canli.pano [--durum durum] [--cikti durum/pano.html] [--simdi 2026-11-07T12:00:00Z]
Çıkış kodu: 0 sorunsuz, 1 durum sorunu (dosya eksik/bozuk), 2 kritik uyarı (bayat veri / kill / alarm) — HTML her durumda yazılır.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from decimal import Decimal
from html import escape as esc
from pathlib import Path
from typing import Optional

from motor.canli import durum as d

BANT_ADI = {"p05_alti": "%5 altı", "p05_p25": "%5–%25", "p25_p50": "%25–%50", "p50_p75": "%50–%75", "p75_p95": "%75–%95",
            "p95_ustu": "%95 üstü"}
BANT_SEVIYE = {"p05_alti": "kotu", "p05_p25": "uyari", "p25_p50": "iyi", "p50_p75": "iyi", "p75_p95": "iyi", "p95_ustu": "uyari"}
KAYNAK_ADI = {"backtest": "BACKTEST (canlı değil)", "paper": "PAPER", "canli": "CANLI"}


# ----------------------------------------------------------------------------------------------- biçimleyiciler
def f_yuzde(x: Optional[float], isaretli: bool = False, ondalik: int = 2) -> str:
    if x is None:
        return "—"
    return f"{x * 100:+.{ondalik}f}%" if isaretli else f"{x * 100:.{ondalik}f}%"


def f_para(s: Optional[str], isaretli: bool = False) -> str:
    """Durum dosyasındaki para metni -> binlik ayraçlı metin (değer değişmez)."""
    if s is None:
        return "—"
    v = Decimal(s)
    return f"{v:+,.2f}" if isaretli else f"{v:,.2f}"


def f_sayi(x: Optional[float], ondalik: int = 2) -> str:
    return "—" if x is None else f"{x:.{ondalik}f}"


def kisa_kimlik(k: str) -> str:
    """'strateji|SEMBOL|tf' -> 'strateji · SEMBOL · tf' (ön ek __ öncesi kısaltılmaz; yalnız ayraç)."""
    return k.replace("|", " · ")


# ----------------------------------------------------------------------------------------------- uyarılar (durum dosyasındaki bayraklar)
def uyarilar(veri: dict, sorunlar: list, simdi: datetime) -> list:
    """-> [(seviye 'kritik'|'uyari'|'bilgi', metin)]. Hesap değil: dosyadaki bayrakların ve zamanların okunması."""
    u = [("kritik", f"Durum sorunu: {s}") for s in sorunlar]
    oz, sg, st = veri.get("ozet"), veri.get("saglik"), veri.get("stratejiler")
    if oz and oz["kaynak"] == "backtest":
        u.append(("bilgi", f"BACKTEST görünümü — dönem {oz['donem']['bas'][:10]} → {oz['donem']['bit'][:10]}; canlı/paper verisi değildir."))
    if oz and sg and oz["kaynak"] != "backtest":
        esik = sg.get("dosya_esik_dk")
        yas_dk = (simdi - d.zaman_oku(oz["zaman"])).total_seconds() / 60
        if esik is None:
            u.append(("uyari", "saglik.json: dosya_esik_dk tanımsız; durum dosyası yaşı denetlenemedi."))
        elif yas_dk > esik:
            u.append(("kritik", f"VERİ BAYAT: durum dosyası {yas_dk:.0f} dk önce yazıldı (eşik {esik} dk) — motor durmuş olabilir."))
    if sg:
        for v in sg["veri"]:
            if v["bayat"]:
                u.append(("kritik", f"VERİ BAYAT: {v['sembol']} {v['tf']} son mum {v['son_mum_zamani']} ({v['bayatlik_dk']} dk, eşik {v['esik_dk']} dk)"))
        if sg["durum"] != "ok":
            u.append(("kritik", f"Motor durumu: {sg['durum']}"))
        for m in sg["uyarilar"]:
            u.append(("bilgi" if oz and oz["kaynak"] == "backtest" else "uyari", m))
    if oz:
        r = oz["risk"]
        if r["kill_switch"]["tetiklendi"]:
            u.append(("kritik", "KILL SWITCH tetiklendi: tüm işlemler durdu."))
        if r["gunluk_kayip"].get("tetiklendi"):
            u.append(("kritik", "Günlük kayıp limiti tetiklendi: yeni işlem yok."))
    if st:
        for x in st["stratejiler"]:
            for hf, b in x["beklenti"].items():
                for m in ("net_getiri", "max_dusus"):
                    if b[m]["alarm"]:
                        u.append(("kritik", f"BEKLENTİ ALARMI: {kisa_kimlik(x['kimlik'])} {hf} hafta {m.replace('_', ' ')} {f_yuzde(b[m]['deger'], True)}"))
        for hf, b in st["set"]["beklenti"].items():
            for m in ("net_getiri", "max_dusus"):
                if b[m]["alarm"]:
                    u.append(("kritik", f"BEKLENTİ ALARMI: SET {hf} hafta {m.replace('_', ' ')} {f_yuzde(b[m]['deger'], True)}"))
    return u


def yukle(dizin) -> tuple:
    return d.oku_hepsi(dizin)


# ----------------------------------------------------------------------------------------------- terminal / telegram
def _beklenti_satiri(ad: str, b: dict) -> str:
    n = b["net_getiri"]
    return f"{ad}: net {f_yuzde(n['deger'], True)} [{BANT_ADI[n['bant']]}] (p50 {f_yuzde(n['p50'], True)}), düşüş {f_yuzde(b['max_dusus']['deger'])}"


def terminal_ozet(veri: dict, sorunlar: list, simdi: datetime) -> str:
    L = [f"1L3A PANO — {simdi:%Y-%m-%d %H:%M} UTC"]
    for sev, m in uyarilar(veri, sorunlar, simdi):
        L.append(f"[{sev.upper()}] {m}")
    oz = veri.get("ozet")
    if oz:
        r = oz["risk"]
        L += [f"Kaynak {KAYNAK_ADI[oz['kaynak']]} · durum zamanı {oz['zaman']}",
              f"Özsermaye {f_para(oz['ozsermaye'])} (başlangıç {f_para(oz['baslangic_ozsermaye'])}) · toplam {f_para(oz['toplam_pnl'], True)} "
              f"({f_yuzde(oz['toplam_getiri'], True)}) · gün {f_para(oz['gun_pnl'], True)} ({f_yuzde(oz['gun_getiri'], True)})",
              f"Zirveden düşüş {f_yuzde(oz['zirveden_dusus'])} · max düşüş {f_yuzde(oz['max_dusus'])} · kill mesafesi {f_yuzde(r['kill_switch']['mesafe'])}",
              f"Risk: günlük kayıp {f_yuzde(r['gunluk_kayip']['deger'])}/{f_yuzde(r['gunluk_kayip']['limit'], ondalik=0)} · "
              f"kaldıraç {f_sayi(r['kaldirac']['deger'])}/{f_sayi(r['kaldirac']['limit'], 1)} · açık stop riski "
              f"{f_yuzde(r['acik_stop_riski']['deger'])}/{f_yuzde(r['acik_stop_riski']['limit'], ondalik=0)}",
              f"Açık pozisyon {oz['sayaclar']['acik_pozisyon']} · kapanan işlem {oz['sayaclar']['kapanan_islem']}"]
    st = veri.get("stratejiler")
    if st:
        L.append("Stratejiler (katkı | işlem | 8 hafta konum):")
        for x in st["stratejiler"]:
            b8 = x["beklenti"].get("8")
            L.append(f"  {kisa_kimlik(x['kimlik'])}: {f_para(x['ozsermaye_katkisi'], True)} | {x['islem_sayisi']} | "
                     + (f"{f_yuzde(b8['net_getiri']['deger'], True)} [{BANT_ADI[b8['net_getiri']['bant']]}]" if b8 else "—"))
        for hf, b in sorted(st["set"]["beklenti"].items(), key=lambda kv: int(kv[0])):
            L.append("  " + _beklenti_satiri(f"SET {hf} hafta", b))
    return "\n".join(L)


def telegram_metni(veri: dict, sorunlar: list, simdi: datetime) -> str:
    """Telegram'a gidecek KISA düz metin (bu modül göndermez)."""
    oz, st = veri.get("ozet"), veri.get("stratejiler")
    L = []
    kritik = [m for s, m in uyarilar(veri, sorunlar, simdi) if s == "kritik"]
    if not oz:
        return "1L3A DURUM YOK\n" + "\n".join(kritik or ["ozet.json okunamadı"])
    r = oz["risk"]
    L.append(f"1L3A · {KAYNAK_ADI[oz['kaynak']]} · {oz['zaman'][:16].replace('T', ' ')}Z")
    L.append(f"Özsermaye {f_para(oz['ozsermaye'])} · gün {f_para(oz['gun_pnl'], True)} ({f_yuzde(oz['gun_getiri'], True)}) · toplam {f_yuzde(oz['toplam_getiri'], True)}")
    L.append(f"Düşüş {f_yuzde(oz['zirveden_dusus'])} (kill mesafesi {f_yuzde(r['kill_switch']['mesafe'])}) · gün kaybı {f_yuzde(r['gunluk_kayip']['deger'])}/{f_yuzde(r['gunluk_kayip']['limit'], ondalik=0)}")
    L.append(f"Açık {oz['sayaclar']['acik_pozisyon']} · kapanan {oz['sayaclar']['kapanan_islem']}")
    if st and "8" in st["set"]["beklenti"]:
        b = st["set"]["beklenti"]["8"]["net_getiri"]
        L.append(f"Set 8 hafta: {f_yuzde(b['deger'], True)} [{BANT_ADI[b['bant']]}]")
    for m in kritik:
        L.append("⚠ " + m)
    return "\n".join(L)


# ----------------------------------------------------------------------------------------------- HTML
CSS = """
:root{--bg:#f6f7f9;--kart:#fff;--yazi:#16181d;--sessiz:#5d6573;--cizgi:#dfe3ea;--iyi:#12805c;--uyari:#a15c00;--kotu:#c62828;--bilgi:#1f5fbf;--vurgu:#1f5fbf;--bar:#e9edf3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1115;--kart:#181b21;--yazi:#e8eaef;--sessiz:#9aa3b2;--cizgi:#2a2f3a;--iyi:#3ddc97;--uyari:#f5a524;--kotu:#ff6b6b;--bilgi:#6ea8ff;--vurgu:#6ea8ff;--bar:#262b35}}
:root[data-theme="dark"]{--bg:#0f1115;--kart:#181b21;--yazi:#e8eaef;--sessiz:#9aa3b2;--cizgi:#2a2f3a;--iyi:#3ddc97;--uyari:#f5a524;--kotu:#ff6b6b;--bilgi:#6ea8ff;--vurgu:#6ea8ff;--bar:#262b35}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--yazi);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overflow-wrap:anywhere}
main{max-width:860px;margin:0 auto;padding:12px 16px 40px}
h1{font-size:18px;margin:6px 0 2px}h2{font-size:15px;margin:22px 0 8px;color:var(--sessiz);text-transform:uppercase;letter-spacing:.04em}
.ust{display:flex;justify-content:space-between;align-items:center;gap:8px}
button{white-space:nowrap;background:var(--kart);color:var(--yazi);border:1px solid var(--cizgi);border-radius:8px;padding:6px 10px;font:inherit}
.alt{color:var(--sessiz);font-size:13px}
.uyari{border-radius:10px;padding:10px 12px;margin:8px 0;border:1px solid var(--cizgi);background:var(--kart);border-left-width:6px}
.uyari.kritik{border-left-color:var(--kotu);background:color-mix(in srgb,var(--kotu) 12%,var(--kart));font-weight:600}
.uyari.uyari{border-left-color:var(--uyari)}.uyari.bilgi{border-left-color:var(--bilgi)}
.izgara{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
@media (min-width:640px){.izgara{grid-template-columns:repeat(4,minmax(0,1fr))}}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:10px 12px;min-width:0}
.kart .e{font-size:12px;color:var(--sessiz)}.kart .d{font-size:20px;font-weight:650;font-variant-numeric:tabular-nums}
.iyi{color:var(--iyi)}.kotu{color:var(--kotu)}.uyarir{color:var(--uyari)}
.cubuk{height:8px;background:var(--bar);border-radius:5px;overflow:hidden;margin-top:6px}.cubuk>i{display:block;height:100%;background:var(--vurgu)}
.cubuk.k>i{background:var(--kotu)}
.sat{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid var(--cizgi)}
.sat:last-child{border-bottom:0}.sat b{font-variant-numeric:tabular-nums;text-align:right}
.kolonlar{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.cip{border:1px solid var(--cizgi);border-radius:999px;padding:2px 9px;font-size:12px}
.cip.iyi{border-color:var(--iyi)}.cip.uyari{border-color:var(--uyari);color:var(--uyari)}.cip.kotu{border-color:var(--kotu);color:var(--kotu);font-weight:700}
svg{width:100%;height:auto;display:block}
.cizgi{stroke:var(--vurgu);fill:none;stroke-width:2;vector-effect:non-scaling-stroke}.alan{fill:var(--vurgu);opacity:.12}
.is{padding:6px 0;border-bottom:1px solid var(--cizgi);font-size:14px}.is:last-child{border-bottom:0}
.sekme-kok{margin-top:10px;position:relative}
input[name=t]{position:absolute;opacity:0;pointer-events:none}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--cizgi);overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:thin}
.tabs label{flex:0 0 auto;padding:10px 13px;font-size:12px;font-weight:600;letter-spacing:.06em;color:var(--sessiz);cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent}
.tabs em{font-style:normal;background:var(--bar);border-radius:9px;padding:0 6px;margin-left:4px;color:var(--yazi)}.tabs em.k{background:var(--kotu);color:#fff}
.sekmeler section{display:none}.sekmeler section>h2:first-child{margin-top:14px}
#t1:checked~.tabs label[for=t1],#t2:checked~.tabs label[for=t2],#t3:checked~.tabs label[for=t3],#t4:checked~.tabs label[for=t4],#t5:checked~.tabs label[for=t5],#t6:checked~.tabs label[for=t6]{color:var(--vurgu);border-bottom-color:var(--vurgu)}
#t1:focus-visible~.tabs label[for=t1],#t2:focus-visible~.tabs label[for=t2],#t3:focus-visible~.tabs label[for=t3],#t4:focus-visible~.tabs label[for=t4],#t5:focus-visible~.tabs label[for=t5],#t6:focus-visible~.tabs label[for=t6]{outline:2px solid var(--vurgu);outline-offset:-2px}
#t1:checked~.sekmeler .n1,#t2:checked~.sekmeler .n2,#t3:checked~.sekmeler .n3,#t4:checked~.sekmeler .n4,#t5:checked~.sekmeler .n5,#t6:checked~.sekmeler .n6{display:block}
"""

JS = """
var K='1l3a-sekme';try{var s=localStorage.getItem(K),r=s&&/^t[1-6]$/.test(s)&&document.getElementById(s);if(r)r.checked=true}catch(e){}
Array.prototype.forEach.call(document.querySelectorAll('input[name=t]'),function(i){i.addEventListener('change',function(){try{localStorage.setItem(K,i.id)}catch(e){}})});
(function(){var k='1l3a-tema',h=document.documentElement;try{var t=localStorage.getItem(k);if(t)h.setAttribute('data-theme',t)}catch(e){}
document.getElementById('tema').addEventListener('click',function(){var m=h.getAttribute('data-theme');var koyu=m?m==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;var y=koyu?'light':'dark';h.setAttribute('data-theme',y);try{localStorage.setItem(k,y)}catch(e){}})})();
"""


def _sat(ad: str, deger: str, sinif: str = "") -> str:
    return f'<div class="sat"><span>{esc(ad)}</span><b class="{sinif}">{esc(deger)}</b></div>'


def _isaret_sinifi(x: Optional[float]) -> str:
    return "" if x is None or x == 0 else ("iyi" if x > 0 else "kotu")


def _kutu(etiket: str, deger: str, sinif: str = "") -> str:
    return f'<div class="kart"><div class="e">{esc(etiket)}</div><div class="d {sinif}">{esc(deger)}</div></div>'


def _kullanim_cubugu(ad: str, deger: Optional[float], limit_metin: str, kullanim: Optional[float], deger_metin: str,
                     alt_metin: Optional[str] = None) -> str:
    gen = 0.0 if kullanim is None else max(0.0, min(1.0, kullanim)) * 100        # çizim ölçeği (kırpma yalnız genişlik için)
    sinif = "k" if kullanim is not None and kullanim >= 0.8 else ""
    kul = alt_metin if alt_metin is not None else ("ölçülmedi" if kullanim is None else f"kullanım {f_yuzde(kullanim, ondalik=1)}")
    return (f'<div class="kart"><div class="e">{esc(ad)}</div><div class="d">{esc(deger_metin)} <span class="alt">/ {esc(limit_metin)}</span></div>'
            f'<div class="cubuk {sinif}"><i style="width:{gen:.1f}%"></i></div><div class="alt">{esc(kul)}</div></div>')


def _egri(gecmis: dict) -> str:
    n = gecmis["noktalar"]
    if len(n) < 2:
        return '<div class="alt">Özsermaye geçmişi için yeterli nokta yok.</div>'
    ys = [float(x["ozsermaye"]) for x in n]                                   # yalnız çizim ölçeği
    lo, hi = min(ys), max(ys)
    ar = (hi - lo) or 1.0
    pts = " ".join(f"{i * 300 / (len(ys) - 1):.1f},{58 - (y - lo) / ar * 52:.1f}" for i, y in enumerate(ys))
    return (f'<svg viewBox="0 0 300 64" preserveAspectRatio="none" role="img" aria-label="özsermaye eğrisi">'
            f'<polygon class="alan" points="0,64 {pts} 300,64"/><polyline class="cizgi" points="{pts}"/></svg>'
            f'<div class="sat"><span class="alt">{esc(n[0]["gun"])}</span><span class="alt">{esc(n[-1]["gun"])}</span></div>'
            f'<div class="sat"><span class="alt">ilk {esc(f_para(n[0]["ozsermaye"]))}</span><span class="alt">son {esc(f_para(n[-1]["ozsermaye"]))}</span></div>')


def _cip(etiket: str, b: dict) -> str:
    n = b["net_getiri"]
    sev = BANT_SEVIYE[n["bant"]]
    return f'<span class="cip {sev}">{esc(etiket)} net {esc(f_yuzde(n["deger"], True))} · {esc(BANT_ADI[n["bant"]])}</span>'


def _strateji_html(x: dict) -> str:
    h = [f'<div class="kart"><b>{esc(kisa_kimlik(x["kimlik"]))}</b><div class="alt">{esc(x["ajan"])} · kol: {esc(x["kol"])}</div>']
    h.append(_sat("Özsermaye katkısı", f"{f_para(x['ozsermaye_katkisi'], True)} ({f_yuzde(x['katki_getiri'], True)})", _isaret_sinifi(x["katki_getiri"])))
    h.append(_sat("İşlem · kazanma oranı", f"{x['islem_sayisi']} · {f_yuzde(x['kazanma_orani'], ondalik=1)}"))
    if x["acik_pozisyonlar"]:
        for p in x["acik_pozisyonlar"]:
            h.append(_sat("Açık pozisyon", " ".join(f"{k}={v}" for k, v in p.items())))
    else:
        h.append(_sat("Açık pozisyon", "yok"))
    s = x["son_islem"]
    h.append(_sat("Son işlem", "—" if not s else f"{s['zaman'][:10]} {s['sembol']} {s['yon']} R {f_sayi(s['r'])}"))
    h.append('<div class="kolonlar">' + "".join(_cip(f"{hf} hf", b) for hf, b in sorted(x["beklenti"].items(), key=lambda kv: int(kv[0]))) + "</div>")
    for hf, b in sorted(x["beklenti"].items(), key=lambda kv: int(kv[0])):
        n, m = b["net_getiri"], b["max_dusus"]
        h.append(f'<div class="alt">{esc(hf)} hf aralık (net %5/%50/%95): {esc(f_yuzde(n["p05"], True))} / {esc(f_yuzde(n["p50"], True))} / {esc(f_yuzde(n["p95"], True))}'
                 f' · düşüş {esc(f_yuzde(m["deger"]))} (%95: {esc(f_yuzde(m["p95"]))})</div>')
    h.append("</div>")
    return "".join(h)


SEKMELER = (("t1", "ÖZET"), ("t2", "STRATEJİLER"), ("t3", "POZİSYON"), ("t4", "İŞLEMLER"), ("t5", "RİSK"), ("t6", "SAĞLIK"))


def _bolum(h2: str, icerik: str) -> str:
    return f"<h2>{esc(h2)}</h2>{icerik}"


def _veri_yok(dosya: str) -> str:
    return f'<div class="uyari kritik">{esc(dosya)} okunamadığı için bu bölüm gösterilemiyor; değer uydurulmaz.</div>'


def _sirali(b: dict):
    return sorted(b.items(), key=lambda kv: int(kv[0]))


def _sekme_ozet(oz, st, gc) -> str:
    if not oz:
        return _veri_yok("ozet.json")
    g = [_bolum("Hesap", '<div class="izgara">'
                + _kutu("Özsermaye", f_para(oz["ozsermaye"])) + _kutu("Toplam PnL", f_para(oz["toplam_pnl"], True) + f" ({f_yuzde(oz['toplam_getiri'], True)})", _isaret_sinifi(oz["toplam_getiri"]))
                + _kutu("Gün PnL", f_para(oz["gun_pnl"], True) + f" ({f_yuzde(oz['gun_getiri'], True)})", _isaret_sinifi(oz["gun_getiri"]))
                + _kutu("Zirveden düşüş", f_yuzde(oz["zirveden_dusus"]), "kotu" if oz["zirveden_dusus"] else "")
                + _kutu("Max düşüş", f_yuzde(oz["max_dusus"])) + _kutu("Başlangıç", f_para(oz["baslangic_ozsermaye"]))
                + _kutu("Açık pozisyon", str(oz["sayaclar"]["acik_pozisyon"])) + _kutu("Kapanan işlem", str(oz["sayaclar"]["kapanan_islem"]))
                + "</div>")]
    if gc:
        g.append('<div class="kart" style="margin-top:8px">' + _egri(gc) + "</div>")
    if st:
        g.append(_bolum("Beklenti aralığına göre konum", '<div class="kart"><b>SET (tüm stratejiler)</b><div class="kolonlar">'
                        + "".join(_cip(f"{hf} hf", b) for hf, b in _sirali(st["set"]["beklenti"])) + "</div>"
                        + "".join(f'<div class="alt">{esc(hf)} hf: net %5/%50/%95 {esc(f_yuzde(b["net_getiri"]["p05"], True))} / {esc(f_yuzde(b["net_getiri"]["p50"], True))} / {esc(f_yuzde(b["net_getiri"]["p95"], True))}'
                                  f' · düşüş {esc(f_yuzde(b["max_dusus"]["deger"]))} (alarm üstü {esc(f_yuzde(b["max_dusus"]["p95"]))})</div>'
                                  for hf, b in _sirali(st["set"]["beklenti"])) + "</div>"))
    else:
        g.append(_veri_yok("stratejiler.json"))
    return "".join(g)


def _sekme_stratejiler(st) -> str:
    if not st:
        return _veri_yok("stratejiler.json")
    return _bolum("Stratejiler", '<div style="display:grid;gap:8px">' + "".join(_strateji_html(x) for x in st["stratejiler"]) + "</div>")


def _sekme_pozisyon(oz, st) -> str:
    if not oz:
        return _veri_yok("ozet.json")
    satir = []
    for x in (st["stratejiler"] if st else []):
        for p in x["acik_pozisyonlar"]:
            satir.append(f'<div class="is"><b>{esc(kisa_kimlik(x["kimlik"]))}</b>'
                         f'<div class="alt">{esc(" ".join(f"{k}={v}" for k, v in p.items()))}</div></div>')
    ic = "".join(satir) if satir else '<div class="alt">Açık pozisyon yok.</div>'
    ek = "" if st else _veri_yok("stratejiler.json")
    return _bolum(f"Açık pozisyonlar ({oz['sayaclar']['acik_pozisyon']})", '<div class="kart">' + ic + "</div>") + ek


def _sekme_islemler(isl) -> str:
    if isl is None:
        return _veri_yok("islemler.jsonl")
    son = sorted(isl, key=lambda s: s["zaman"], reverse=True)[:20]
    return _bolum(f"Son kapanan işlemler ({len(son)} / {len(isl)})", '<div class="kart">' + "".join(
        f'<div class="is"><b>{esc(s["zaman"][:16].replace("T", " "))}</b> {esc(s["sembol"])} {esc(s["yon"])} · R {esc(f_sayi(s["r"]))}'
        f' · {esc(f_para(s["set_katki_usd"], True) if s["set_katki_usd"] is not None else "katkı: kol düzeyinde")}'
        f'<div class="alt">{esc(kisa_kimlik(s["kimlik"]))} · {esc(s["cikis_nedeni"])}</div></div>' for s in son)
        + ("" if son else '<div class="alt">Kapanan işlem yok.</div>') + "</div>")


def _sekme_risk(oz) -> str:
    if not oz:
        return _veri_yok("ozet.json")
    r = oz["risk"]
    gk, kl, ks, ar = r["gunluk_kayip"], r["kaldirac"], r["kill_switch"], r["acik_stop_riski"]
    g = ['<div class="izgara">'
         + _kullanim_cubugu("Günlük kayıp", gk["deger"], f_yuzde(gk["limit"], ondalik=0), gk["kullanim"], f_yuzde(gk["deger"]))
         + _kullanim_cubugu("Kaldıraç", kl["deger"], f_sayi(kl["limit"], 1) + "x", kl["kullanim"], f_sayi(kl["deger"]) + ("x" if kl["deger"] is not None else ""))
         + _kullanim_cubugu("Açık stop riski", ar["deger"], f_yuzde(ar["limit"], ondalik=0), ar["kullanim"], f_yuzde(ar["deger"]))
         + _kullanim_cubugu("Kill switch (zirveden düşüş)", ks["dusus"], f_yuzde(ks["limit"], ondalik=0), None, f_yuzde(ks["dusus"]),
                            alt_metin=f"mesafe {f_yuzde(ks['mesafe'])}")
         + "</div>",
         '<div class="kart" style="margin-top:8px">' + _sat("Kill switch mesafesi", f_yuzde(ks["mesafe"]) + (" — TETİKLENDİ" if ks["tetiklendi"] else ""), "kotu" if ks["tetiklendi"] else "") + "</div>"]
    if kl.get("not"):
        g.append(f'<div class="alt">{esc(kl["not"])}</div>')
    for n in oz["notlar"]:
        g.append(f'<div class="alt">{esc(n)}</div>')
    return _bolum("Risk limitleri", "".join(g))


def _sekme_saglik(sg) -> str:
    if not sg:
        return _veri_yok("saglik.json")
    g = ['<div class="kart">', _sat("Son çalışma", sg["son_calisma"]) + _sat("Durum", sg["durum"], "iyi" if sg["durum"] == "ok" else "kotu")]
    sv = sg["servis"]
    g.append(_sat("Servis", {True: "çalışıyor", False: "ÇALIŞMIYOR", None: "yok (backtest)"}[sv["calisiyor"]] + f" · {sv['surum']}", "kotu" if sv["calisiyor"] is False else ""))
    for v in sg["veri"]:
        g.append(_sat(f"{v['sembol']} {v['tf']} son mum", f"{v['son_mum_zamani'][:16].replace('T', ' ')} · {v['bayatlik_dk']} dk" + (" · BAYAT" if v["bayat"] else ""), "kotu" if v["bayat"] else ""))
    g.append("</div>")
    return _bolum("Sağlık", "".join(g))


def html_olustur(veri: dict, sorunlar: list, simdi: datetime) -> str:
    oz, st, sg, isl, gc = (veri.get(k) for k in ("ozet", "stratejiler", "saglik", "islemler", "gecmis"))
    u = uyarilar(veri, sorunlar, simdi)
    g = []
    g.append(f'<div class="ust"><div><h1>1L3A pano</h1><div class="alt">{esc(f"{simdi:%Y-%m-%d %H:%M} UTC")}'
             + (f' · {esc(KAYNAK_ADI[oz["kaynak"]])}' if oz else "") + '</div></div><button id="tema" type="button">Tema</button></div>')
    for sev, m in u:                                   # uyarılar sekmelerin ÜSTÜNDE: hangi sekmede olursan ol görünür
        g.append(f'<div class="uyari {sev}" role="{"alert" if sev == "kritik" else "note"}">{esc(m)}</div>')
    if not oz:
        g.append('<div class="uyari kritik">Özet dosyası (ozet.json) okunamadığı için hesap bilgisi gösterilemiyor; değer uydurulmaz.</div>')
    # rozetler: durum dosyasındaki sayılar (hesap değil)
    rozet = {"t2": str(len(st["stratejiler"])) if st else None, "t3": str(oz["sayaclar"]["acik_pozisyon"]) if oz else None,
             "t4": str(len(isl)) if isl is not None else None}
    sorun_var = bool(sg and (sg["durum"] != "ok" or any(v["bayat"] for v in sg["veri"])))
    g.append('<div class="sekme-kok">')
    g.append("".join(f'<input type="radio" name="t" id="{i}"' + (" checked" if i == "t1" else "") + ' aria-label="' + esc(ad) + '">' for i, ad in SEKMELER))
    g.append('<div class="tabs" role="tablist">' + "".join(
        f'<label for="{i}">{esc(ad)}' + (f' <em>{esc(rozet[i])}</em>' if rozet.get(i) is not None else "")
        + (' <em class="k">!</em>' if i == "t6" and sorun_var else "") + "</label>" for i, ad in SEKMELER) + "</div>")
    icerik = (_sekme_ozet(oz, st, gc), _sekme_stratejiler(st), _sekme_pozisyon(oz, st), _sekme_islemler(isl), _sekme_risk(oz), _sekme_saglik(sg))
    g.append('<div class="sekmeler">' + "".join(f'<section class="n{k}">{c}</section>' for k, c in enumerate(icerik, 1)) + "</div></div>")
    return ('<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light dark"><title>1L3A pano</title><style>' + CSS + "</style></head><body><main>"
            + "".join(g) + "</main><script>" + JS + "</script></body></html>")


def uret(dizin, cikti=None, simdi: Optional[datetime] = None) -> tuple:
    """Durumu okur, HTML'i atomik yazar. -> (html_yolu, terminal metni, sorunlar, uyarılar)."""
    simdi = simdi or datetime.now(timezone.utc)
    veri, sorunlar = yukle(dizin)
    yol = Path(cikti) if cikti else Path(dizin) / "pano.html"
    d.atomik_yaz_metin(yol, html_olustur(veri, sorunlar, simdi))
    return yol, terminal_ozet(veri, sorunlar, simdi), sorunlar, uyarilar(veri, sorunlar, simdi)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Durum dosyalarından statik HTML pano + terminal özeti")
    ap.add_argument("--durum", default=str(d.DURUM_DIZINI))
    ap.add_argument("--cikti", default=None, help="HTML yolu (varsayılan: <durum>/pano.html)")
    ap.add_argument("--simdi", default=None, help="test için sabit zaman (YYYY-MM-DDTHH:MM:SSZ)")
    ap.add_argument("--telegram", action="store_true", help="Telegram kısa metnini de yazdır (göndermez)")
    a = ap.parse_args(argv)
    simdi = d.zaman_oku(a.simdi) if a.simdi else None
    yol, metin, sorunlar, u = uret(a.durum, a.cikti, simdi)
    print(metin)
    print(f"\nHTML: {yol}")
    if a.telegram:
        veri, s = yukle(a.durum)
        print("\n--- Telegram metni ---\n" + telegram_metni(veri, s, simdi or datetime.now(timezone.utc)))
    return 1 if sorunlar else (2 if any(s == "kritik" for s, _ in u) else 0)


if __name__ == "__main__":
    sys.exit(main())
