"""Pano (Aşama 3): durum dosyalarını okuyup TEK DOSYALIK statik HTML + terminal özeti + Telegram kısa metni üretir.

İLKE (DURUM.md Aşama 3): PANO YENİ HESAP YAPMAZ. Gösterilen her sayı durum dosyasında (motorun yazdığı) olduğu gibi vardır;
burada yalnız biçimlendirme (yüzde işareti, binlik ayraç), sıralama, ilk-N kesme ve çizim ölçekleme yapılır. Tek istisna ZAMAN karşılaştırmasıdır:
dosya yaşı (şimdi - durum zamanı) motor ölmüşse eski dosyanın 'sağlıklı' görünmemesi için eşikle (saglik.json'daki
`dosya_esik_dk`) karşılaştırılır. Durum dosyası yok/bozuksa açık hata gösterilir; uydurma değer yazılmaz.
Gösterim saatleri Türkiye saatidir (TSİ, Europe/Istanbul); terminal/Telegram metni UTC kalır. Tarayıcı JS'i yalnız
yazildi_zaman bayatlık bandını açar (gösterim kontrolü; JS yoksa sayfa yine çalışır).
Telegram: bu modül MESAJ GÖNDERMEZ, yalnız metin üretir (`telegram_metni`).

CLI: python -m motor.canli.pano [--durum durum] [--cikti durum/pano.html] [--simdi 2026-11-07T12:00:00Z]
Çıkış kodu: 0 sorunsuz, 1 durum sorunu (dosya eksik/bozuk), 2 kritik uyarı (bayat veri / kill / alarm) — HTML her durumda yazılır.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from html import escape as esc
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

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
    """Zorunlu 5 dosya + ek dosyalar (maruziyet, maliyet, reddedilen, olaylar, icgoruler). Ek dosya YOKSA değeri None (eski motor: ilgili
    kart 'veri yok' der, sorun sayılmaz); BOZUKSA None + sorun metni."""
    veri, sorunlar = d.oku_hepsi(dizin)
    for ad in d.EK_DOSYALAR:
        try:
            veri[ad] = d.ek_oku(dizin, ad)
        except d.DurumHatasi as e:
            veri[ad] = None
            sorunlar.append(str(e))
    return veri, sorunlar


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
:root{--bg:#0a0a0b;--kart:#111113;--yazi:#e9e9ee;--sessiz:#8a8a94;--cizgi:#25252a;--iyi:#3ddc84;--uyari:#f5d90a;--kotu:#ff5d5d;--bilgi:#5b9dff;--vurgu:#f5a524;--bar:#1c1c21;--yan:#000}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0a0a0b;--kart:#111113;--yazi:#e9e9ee;--sessiz:#8a8a94;--cizgi:#25252a;--iyi:#3ddc84;--uyari:#f5d90a;--kotu:#ff5d5d;--bilgi:#5b9dff;--vurgu:#f5a524;--bar:#1c1c21;--yan:#000}}
:root[data-theme="dark"]{--bg:#0a0a0b;--kart:#111113;--yazi:#e9e9ee;--sessiz:#8a8a94;--cizgi:#25252a;--iyi:#3ddc84;--uyari:#f5d90a;--kotu:#ff5d5d;--bilgi:#5b9dff;--vurgu:#f5a524;--bar:#1c1c21;--yan:#000}
:root[data-theme="light"]{--bg:#f1f2f5;--kart:#fff;--yazi:#15171c;--sessiz:#5f6673;--cizgi:#d6d9e0;--iyi:#0d7a4c;--uyari:#8a6a00;--kotu:#c62828;--bilgi:#1f5fbf;--vurgu:#a85f00;--bar:#e6e9ef;--yan:#fff}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--yazi);font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;overflow-wrap:anywhere;padding:12px}
main{max-width:1400px;margin:0 auto;padding-bottom:28px}
h1{font-size:15px;letter-spacing:.06em;margin:0}
button{white-space:nowrap;background:var(--kart);color:var(--yazi);border:1px solid var(--cizgi);border-radius:3px;padding:3px 10px;font:inherit;font-size:11px;cursor:pointer}
button:hover{border-color:var(--vurgu);color:var(--vurgu)}
.ust{display:flex;justify-content:space-between;align-items:center;gap:8px 14px;flex-wrap:wrap;margin-bottom:10px;padding-bottom:9px;border-bottom:1px solid var(--cizgi)}
.mk{display:flex;align-items:center;gap:9px}.lg0{background:var(--vurgu);color:#000;font-weight:800;padding:2px 7px;border-radius:3px}
.un{display:flex;align-items:center;gap:6px 12px;flex-wrap:wrap;font-size:11px}.so{color:var(--sessiz)}
.rozet{border:1px solid var(--vurgu);border-radius:3px;padding:1px 9px;color:var(--vurgu);font-size:11px;font-weight:700;letter-spacing:.06em}
.rozet.r-backtest{border-color:var(--bilgi);color:var(--bilgi)}.rozet.r-canli{border-color:var(--kotu);color:var(--kotu)}
.alt{color:var(--sessiz);font-size:11px}
.uyari{border-radius:3px;padding:8px 12px;margin:0 0 8px;border:1px solid var(--cizgi);background:var(--kart);border-left-width:4px}
.uyari.kritik{border-left-color:var(--kotu);background:color-mix(in srgb,var(--kotu) 13%,var(--kart));font-weight:700}
.uyari.uyari{border-left-color:var(--uyari)}.uyari.bilgi{border-left-color:var(--bilgi)}
.uyari.bayat-bant{background:var(--kotu);color:#fff;border-color:var(--kotu);font-weight:800}
.iyi{color:var(--iyi)}.kotu{color:var(--kotu)}.uyarir{color:var(--uyari)}
.izgara{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.izgara.c2{grid-template-columns:repeat(2,minmax(0,1fr))}.izgara.oto{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
@media (min-width:640px){.izgara.c4{grid-template-columns:repeat(4,minmax(0,1fr))}.izgara.oto{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:3px;padding:8px 11px;min-width:0}
.kart .e{font-size:10px;letter-spacing:.09em;color:var(--sessiz);text-transform:uppercase}.kart .d{font-size:18px;font-weight:700;margin:2px 0;font-variant-numeric:tabular-nums}
.p .kart{background:var(--bg)}
.serit{gap:1px;background:var(--cizgi);border:1px solid var(--cizgi);margin-bottom:10px}
.serit .kart{border:0;border-radius:0;background:var(--kart);padding:9px 11px}.serit .d{font-size:17px}
.cubuk{height:7px;background:var(--bar);border-radius:4px;overflow:hidden;margin:5px 0 4px}.cubuk>i{display:block;height:100%;background:var(--vurgu)}.cubuk.k>i{background:var(--kotu)}
.sat{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid var(--bar)}
.sat:last-child{border-bottom:0}.sat>span{color:var(--sessiz)}.sat>span b{color:var(--yazi)}.sat b{font-variant-numeric:tabular-nums;text-align:right}.sat b.nw{white-space:nowrap;flex:none;overflow-wrap:normal}
.kolonlar{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}
.cip{border:1px solid var(--cizgi);border-radius:3px;padding:1px 7px;font-size:11px;white-space:nowrap}
.cip.iyi{border-color:var(--iyi)}.cip.uyari{border-color:var(--uyari);color:var(--uyari)}.cip.kotu{border-color:var(--kotu);color:var(--kotu);font-weight:700}
.ig{display:grid;grid-template-columns:minmax(0,1fr);gap:8px;margin-top:8px}.sag{display:contents}
.p{background:var(--kart);border:1px solid var(--cizgi);border-radius:3px;min-width:0}
.pb{font-size:10px;letter-spacing:.09em;color:var(--vurgu);text-transform:uppercase;padding:8px 11px;border-bottom:1px solid var(--cizgi);display:flex;justify-content:space-between;gap:10px}
.pb span{color:var(--sessiz);text-transform:none;letter-spacing:0;font-size:11px;text-align:right}
.pi{padding:10px 11px}.pi.duz{padding:0}.pi.duz>.kart{border:0;background:transparent}
.bol{margin-top:8px}.mr{padding:6px 0;border-bottom:1px solid var(--bar)}.mr:last-child{border-bottom:0}.mr .sat{border:0;padding:0}.mr .cubuk{margin:4px 0 2px}
svg{display:block;width:100%;height:auto}
.gk{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:7px}
.gk svg{height:130px}.yt{display:flex;flex-direction:column;justify-content:space-between;text-align:right;font-size:10px;color:var(--sessiz);font-variant-numeric:tabular-nums;padding:1px 0}
.gk .ek{grid-column:2;display:flex;justify-content:space-between;gap:8px;font-size:10px;color:var(--sessiz);margin-top:4px}
.gk.kz svg{height:110px}
.izg{stroke:var(--cizgi);stroke-width:1;vector-effect:non-scaling-stroke;opacity:.8}.baz{stroke:var(--sessiz);stroke-width:1;stroke-dasharray:4 3;vector-effect:non-scaling-stroke}
.cizgi{stroke:var(--vurgu);fill:none;stroke-width:1.8;vector-effect:non-scaling-stroke}.alan{fill:var(--vurgu);opacity:.14}
.cizgi.k{stroke:var(--kotu)}.alan.k{fill:var(--kotu);opacity:.18}
.bi{fill:var(--iyi)}.bk{fill:var(--kotu)}.taban{stroke:var(--sessiz);stroke-width:1;vector-effect:non-scaling-stroke;opacity:.6}
.grlej{margin-top:6px;text-align:center}
.is{padding:5px 0;border-bottom:1px solid var(--bar)}.is:last-child{border-bottom:0}
.ic>div{padding:5px 0 5px 14px;border-bottom:1px solid var(--bar);position:relative;font-size:12px}.ic>div:last-child{border-bottom:0}.ic>div:before{content:"›";color:var(--vurgu);position:absolute;left:0}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%;border:1px solid var(--cizgi);border-radius:3px;background:var(--kart)}
.p .tw{border:0;border-radius:0;background:transparent}.kay{max-height:420px;overflow:auto}.kay>.tw{overflow:visible}.kay th{position:sticky;top:0;z-index:1}
table{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}
th,td{padding:6px 10px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--bar)}
th{font-size:10px;color:var(--sessiz);text-transform:uppercase;letter-spacing:.08em;font-weight:600;background:color-mix(in srgb,var(--bg) 55%,var(--kart))}
td.sg,th.sg{text-align:right}tbody tr:last-child td{border-bottom:0}tbody tr:hover td{background:color-mix(in srgb,var(--vurgu) 6%,transparent)}
.sekme-kok{margin-top:2px;position:relative}
input[name=t]{position:absolute;opacity:0;pointer-events:none}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--cizgi);overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:thin}
.tabs label{flex:0 0 auto;padding:9px 14px 8px;font-size:11px;font-weight:600;letter-spacing:.09em;color:var(--sessiz);cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent}
.tabs label:hover{color:var(--yazi)}
.tabs em{font-style:normal;background:var(--bar);border-radius:9px;padding:0 6px;margin-left:4px;color:var(--yazi)}.tabs em.k{background:var(--kotu);color:#fff}
.sekmeler section{display:none}
#t1:checked~.tabs label[for=t1],#t2:checked~.tabs label[for=t2],#t3:checked~.tabs label[for=t3],#t4:checked~.tabs label[for=t4],#t5:checked~.tabs label[for=t5],#t6:checked~.tabs label[for=t6]{color:var(--vurgu);border-bottom-color:var(--vurgu)}
#t1:focus-visible~.tabs label[for=t1],#t2:focus-visible~.tabs label[for=t2],#t3:focus-visible~.tabs label[for=t3],#t4:focus-visible~.tabs label[for=t4],#t5:focus-visible~.tabs label[for=t5],#t6:focus-visible~.tabs label[for=t6]{outline:2px solid var(--vurgu);outline-offset:-2px}
#t1:checked~.sekmeler .n1,#t2:checked~.sekmeler .n2,#t3:checked~.sekmeler .n3,#t4:checked~.sekmeler .n4,#t5:checked~.sekmeler .n5,#t6:checked~.sekmeler .n6{display:block}
details.kd{border-bottom:1px solid var(--bar);min-width:0}details.kd:last-child{border-bottom:0}
details.kd>summary{cursor:pointer;list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 10px;align-items:start;padding:10px 12px}details.kd>summary::-webkit-details-marker{display:none}
details.kd>summary:hover{background:color-mix(in srgb,var(--vurgu) 6%,transparent)}
details.kd>summary [data-e]:before{content:attr(data-e);display:block;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--sessiz)}
.ad{grid-column:1/-1}.ad:before{content:"▸";color:var(--sessiz);display:inline-block;width:14px}details.kd[open] .ad:before{content:"▾"}
.sh{display:none}
details.kd .govde{padding:6px 12px 12px;background:var(--bg);border-top:1px solid var(--cizgi)}.govde .alt{margin-top:4px}.govde .sat>span{flex:0 0 auto;max-width:48%;overflow-wrap:normal}
details.ince>summary{cursor:pointer;color:var(--vurgu);font-size:11px;padding:6px 0}
.ayak{margin:14px 0 4px}
@media (min-width:900px){
body{padding:16px 20px}
.serit{grid-template-columns:repeat(6,minmax(0,1fr))}.serit .d{font-size:20px}
.ig{grid-template-columns:repeat(3,minmax(0,1fr))}.g2{grid-column:span 2}.g3{grid-column:1/-1}
.sag{display:grid;gap:8px;grid-column:3;grid-row:1 / span 2;align-content:start;min-width:0}.sag.s1{grid-row:auto}
.p.yuk{display:flex;flex-direction:column}.yuk>.pi{flex:1;display:flex;flex-direction:column}.yuk .gk{flex:1;grid-template-rows:minmax(0,1fr) auto}.yuk .gk svg{height:100%;min-height:210px;max-height:340px}
.gk svg{height:210px}.gk.kz svg{height:150px}.gk.dus svg{height:150px}
.stw{min-width:1020px}
.sh,details.kd>summary{display:grid;grid-template-columns:minmax(270px,2.6fr) minmax(70px,.9fr) minmax(110px,1.2fr) minmax(110px,1.3fr) minmax(48px,.55fr) minmax(64px,.75fr) minmax(48px,.55fr) minmax(190px,2.2fr) minmax(40px,.5fr);gap:10px;align-items:center;padding:9px 12px}
.sh{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--sessiz);border-bottom:1px solid var(--cizgi);background:color-mix(in srgb,var(--bg) 55%,var(--kart))}
details.kd>summary [data-e]:before{display:none}.ad{grid-column:auto}
.stw .sg{text-align:right}
.govde{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 32px}.govde .alt{grid-column:1/-1}
}
"""

JS = """
var K='1l3a-sekme';try{var s=localStorage.getItem(K),r=s&&/^t[1-6]$/.test(s)&&document.getElementById(s);if(r)r.checked=true}catch(e){}
Array.prototype.forEach.call(document.querySelectorAll('input[name=t]'),function(i){i.addEventListener('change',function(){try{localStorage.setItem(K,i.id)}catch(e){}})});
(function(){var k='1l3a-tema',h=document.documentElement;try{var t=localStorage.getItem(k);if(t)h.setAttribute('data-theme',t)}catch(e){}
document.getElementById('tema').addEventListener('click',function(){var m=h.getAttribute('data-theme');var koyu=m?m==='dark':true;var y=koyu?'light':'dark';h.setAttribute('data-theme',y);try{localStorage.setItem(k,y)}catch(e){}})})();
(function(){var b=document.getElementById('bayat');if(!b)return;var t=Date.parse(b.getAttribute('data-zaman')),e=Number(b.getAttribute('data-esik-dk'));
if(!isFinite(t)||!isFinite(e))return;var dk=Math.floor((Date.now()-t)/60000);if(dk>e){var x=document.getElementById('bayat-dk');if(x)x.textContent=String(dk);b.hidden=false}})();
"""

BAYATLIK_ESIK_DK = 60                      # tarayıcı tarafı gösterim eşiği (iş hesabı değil: "sistem durmuş olabilir" uyarısı)
try:
    TSI = ZoneInfo("Europe/Istanbul")
except Exception:                          # noqa: BLE001 — tzdata yoksa: Türkiye 2016'dan beri kalıcı UTC+3
    TSI = timezone(timedelta(hours=3), "TSİ")


def tsi(s: Optional[str]) -> str:
    """Durum dosyasındaki UTC zaman metni -> Türkiye saati metni (yalnız saat dilimi dönüşümü). Gün metni ('2026-10-01') aynen döner."""
    if not s:
        return "—"
    try:
        return d.zaman_oku(s).astimezone(TSI).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(s)


def _h(metin, sinif: str = "") -> str:
    """Kaçışlı metin (isteğe bağlı renk sınıfı ile)."""
    return f'<span class="{sinif}">{esc(str(metin))}</span>' if sinif else esc(str(metin))


def _sat(ad: str, deger: str, sinif: str = "") -> str:
    return f'<div class="sat"><span>{esc(ad)}</span><b class="{sinif}">{esc(deger)}</b></div>'


def _isaret_sinifi(x) -> str:
    """Renk sınıfı: sayı ya da para metni (işaretine bakar; değer değişmez)."""
    if x is None:
        return ""
    try:
        v = Decimal(x) if isinstance(x, str) else x
    except Exception:  # noqa: BLE001
        return ""
    return "" if v == 0 else ("iyi" if v > 0 else "kotu")


def _guvenli(f):
    """Ek veri bölümü beklenmedik biçimde gelirse sayfa kırılmaz: o bölüm 'biçim uyumsuz' der, değer uydurulmaz."""
    def sar(*a, **k):
        try:
            return f(*a, **k)
        except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError, IndexError):
            return '<div class="kart alt">Bu bölümün verisi beklenen biçimde değil; gösterilemiyor.</div>'
    return sar



def _kutu(etiket: str, deger: str, sinif: str = "", alt: str = "") -> str:
    return (f'<div class="kart"><div class="e">{esc(etiket)}</div><div class="d {sinif}">{esc(deger)}</div>'
            + (f'<div class="alt">{esc(alt)}</div>' if alt else "") + "</div>")


def _kullanim_cubugu(ad: str, deger: Optional[float], limit_metin: str, kullanim: Optional[float], deger_metin: str,
                     alt_metin: Optional[str] = None) -> str:
    gen = 0.0 if kullanim is None else max(0.0, min(1.0, kullanim)) * 100        # çizim ölçeği (kırpma yalnız genişlik için)
    sinif = "k" if kullanim is not None and kullanim >= 0.8 else ""
    kul = alt_metin if alt_metin is not None else ("ölçülmedi" if kullanim is None else f"kullanım {f_yuzde(kullanim, ondalik=1)}")
    return (f'<div class="kart"><div class="e">{esc(ad)}</div><div class="d">{esc(deger_metin)} <span class="alt">/ {esc(limit_metin)}</span></div>'
            f'<div class="cubuk {sinif}"><i style="width:{gen:.1f}%"></i></div><div class="alt">{esc(kul)}</div></div>')


def _kullanim_satiri(ad: str, limit_metin: str, kullanim: Optional[float], deger_metin: str, alt_metin: Optional[str] = None) -> str:
    """Panel içi kompakt kullanım satırı (kart değil): ad, değer / limit, çubuk, kullanım yüzdesi."""
    gen = 0.0 if kullanim is None else max(0.0, min(1.0, kullanim)) * 100
    sinif = "k" if kullanim is not None and kullanim >= 0.8 else ""
    kul = alt_metin if alt_metin is not None else ("ölçülmedi" if kullanim is None else f"kullanım {f_yuzde(kullanim, ondalik=1)}")
    return (f'<div class="mr"><div class="sat"><span>{esc(ad)} <span class="alt">· {esc(kul)}</span></span><b>{esc(deger_metin)} <span class="alt">/ {esc(limit_metin)}</span></b></div>'
            f'<div class="cubuk {sinif}"><i style="width:{gen:.1f}%"></i></div></div>')


def _tablo(basliklar: list, satirlar: list, sag: tuple = (), sinif: str = "") -> str:
    """Kendi kutusunda yatay kayan tablo. Hücreler HAZIR (kaçışlı) HTML'dir; `sag`: sağa hizalı sütun numaraları."""
    b = "".join(f'<th{" class=sg" if i in sag else ""}>{esc(x)}</th>' for i, x in enumerate(basliklar))
    r = "".join("<tr>" + "".join(f'<td{" class=sg" if i in sag else ""}>{c}</td>' for i, c in enumerate(s)) + "</tr>" for s in satirlar)
    t = f'<div class="tw"><table><thead><tr>{b}</tr></thead><tbody>{r}</tbody></table></div>'
    return f'<div class="{sinif}">{t}</div>' if sinif else t


def _p(baslik: str, icerik: str, sag: str = "", sinif: str = "", duz: bool = False) -> str:
    """Panel: başlık şeridi (.pb) + içerik (.pi). `icerik` HAZIR HTML'dir; `sag`: başlığın sağındaki sönük not."""
    return (f'<div class="p{" " + sinif if sinif else ""}"><div class="pb">{esc(baslik)}' + (f"<span>{esc(sag)}</span>" if sag else "")
            + f'</div><div class="pi{" duz" if duz else ""}">{icerik}</div></div>')


def _ig(icerik: str) -> str:
    return f'<div class="ig">{icerik}</div>'


def _sag(icerik: str, sinif: str = "") -> str:
    return f'<div class="sag{" " + sinif if sinif else ""}">{icerik}</div>'


def _neden(o: dict, alan: str) -> str:
    """Null alanın yanındaki açıklama: `<alan>_neden` ya da `olculmedi_neden` (varsa)."""
    return str((o or {}).get(f"{alan}_neden") or (o or {}).get("olculmedi_neden") or "")


# ----------------------------------------------------------------------------------------------- grafikler (inline SVG; ölçekleme dışında hesap yok)
def _eksen(ust: str, alt: str, svg: str, x0: str, x1: str, sinif: str = "") -> str:
    """Grafik kutusu: solda y ekseni uç değerleri (dosyadaki değerler), altta ilk/son tarih."""
    return (f'<div class="gk {sinif}"><div class="yt"><span>{esc(ust)}</span><span>{esc(alt)}</span></div>{svg}'
            f'<span></span><div class="ek"><span>{esc(x0)}</span><span>{esc(x1)}</span></div></div>')


@_guvenli
def _egri(gecmis: dict, baz: Optional[str] = None) -> str:
    """Özsermaye eğrisi: alan grafiği + min/max etiketi + (varsa) başlangıç baz çizgisi. Yalnız çizim ölçeği."""
    n = gecmis["noktalar"]
    if len(n) < 2:
        return '<div class="alt">Özsermaye geçmişi için yeterli nokta yok.</div>'
    cift = [(float(x["ozsermaye"]), x["ozsermaye"]) for x in n]
    havuz = cift + ([(float(baz), baz)] if baz is not None else [])
    (hi, hi_s), (lo, lo_s) = max(havuz, key=lambda c: c[0]), min(havuz, key=lambda c: c[0])
    ar = (hi - lo) or 1.0
    y = lambda v: 76 - (v - lo) / ar * 72                                       # noqa: E731
    pts = " ".join(f"{i * 300 / (len(cift) - 1):.1f},{y(v):.1f}" for i, (v, _) in enumerate(cift))
    izgara = "".join(f'<line class="izg" x1="0" y1="{yy}" x2="300" y2="{yy}"/>' for yy in (4, 40, 76))
    baz_c = f'<line class="baz" x1="0" y1="{y(float(baz)):.1f}" x2="300" y2="{y(float(baz)):.1f}"/>' if baz is not None else ""
    svg = (f'<svg viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="özsermaye eğrisi">{izgara}'
           f'<polygon class="alan" points="0,80 {pts} 300,80"/>{baz_c}<polyline class="cizgi" points="{pts}"/></svg>')
    return (_eksen(f_para(hi_s), f_para(lo_s), svg, n[0]["gun"], n[-1]["gun"])
            + f'<div class="alt grlej">ilk {esc(f_para(n[0]["ozsermaye"]))} · son {esc(f_para(n[-1]["ozsermaye"]))}'
            + (f' · kesikli çizgi: başlangıç {esc(f_para(baz))}' if baz is not None else "") + "</div>")


@_guvenli
def _dusus_grafigi(seri: list) -> str:
    """dusus_serisi [{gun, dusus}] -> aşağı sarkan alan grafiği (0 üstte; dosyadaki değerler aynen)."""
    if len(seri) < 2:
        return '<div class="alt">Zirveden düşüş serisi için yeterli nokta yok.</div>'
    ys = [float(x["dusus"]) for x in seri]
    tepe = max(ys) or 1.0                                                      # yalnız çizim ölçeği
    pts = " ".join(f"{i * 300 / (len(ys) - 1):.1f},{4 + v / tepe * 72:.1f}" for i, v in enumerate(ys))
    izgara = "".join(f'<line class="izg" x1="0" y1="{yy}" x2="300" y2="{yy}"/>' for yy in (40, 76))
    svg = (f'<svg viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="zirveden düşüş">{izgara}'
           f'<polygon class="alan k" points="0,4 {pts} 300,4"/><polyline class="cizgi k" points="{pts}"/>'
           f'<line class="taban" x1="0" y1="4" x2="300" y2="4"/></svg>')
    return (_eksen(f_yuzde(0.0), f_yuzde(tepe), svg, seri[0]["gun"], seri[-1]["gun"], "dus")
            + f'<div class="alt grlej">ilk {esc(f_yuzde(seri[0]["dusus"]))} · son {esc(f_yuzde(seri[-1]["dusus"]))}</div>')


@_guvenli
def _kz_grafigi(seri: list) -> str:
    """gunluk_kz [{gun, pnl, getiri}] -> günlük K/Z çubukları (yeşil kâr / kırmızı zarar) + ayrıntı listesi (<details>)."""
    if not seri:
        return '<div class="alt">Günlük K/Z serisi boş.</div>'
    ys = [float(x["pnl"]) for x in seri]
    hi, lo = max(max(ys), 0.0), min(min(ys), 0.0)                              # yalnız çizim ölçeği (sıfır çizgisi dahil)
    ar = (hi - lo) or 1.0
    y = lambda v: 4 + (hi - v) / ar * 72                                       # noqa: E731
    gen = 300 / max(len(ys), 10)                                               # tek çubuk ekranı kaplamasın
    cubuklar = []
    for i, (x, v) in enumerate(zip(seri, ys)):
        ust, alt = y(max(v, 0.0)), y(min(v, 0.0))
        cubuklar.append(f'<rect class="{"bi" if v >= 0 else "bk"}" x="{i * gen + gen * 0.12:.2f}" y="{ust:.2f}" width="{gen * 0.76:.2f}" '
                        f'height="{max(alt - ust, 0.8):.2f}"><title>{esc(x["gun"])}: {esc(f_para(x["pnl"], True))}</title></rect>')
    en_ust = f_para(seri[ys.index(hi)]["pnl"], True) if hi > 0 else f_para("0")
    en_alt = f_para(seri[ys.index(lo)]["pnl"], True) if lo < 0 else f_para("0")
    svg = (f'<svg viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="günlük K/Z">'
           f'<line class="izg" x1="0" y1="4" x2="300" y2="4"/><line class="izg" x1="0" y1="76" x2="300" y2="76"/>'
           f'<line class="taban" x1="0" y1="{y(0.0):.2f}" x2="300" y2="{y(0.0):.2f}"/>{"".join(cubuklar)}</svg>')
    satir = [[esc(x["gun"]), _h(f_para(x["pnl"], True), _isaret_sinifi(x["pnl"])), _h(f_yuzde(x.get("getiri"), True), _isaret_sinifi(x.get("getiri")))]
             for x in reversed(seri)]
    return (_eksen(en_ust, en_alt, svg, seri[0]["gun"], seri[-1]["gun"], "kz")
            + f'<div class="sat"><span class="alt">son gün</span><b class="{_isaret_sinifi(seri[-1]["pnl"])}">{esc(f_para(seri[-1]["pnl"], True))}</b></div>'
            f'<details class="ince"><summary>Günlük değerler ({len(seri)} gün)</summary>{_tablo(["Gün", "K/Z", "Getiri"], satir, sag=(1, 2), sinif="kay")}</details>')


# ----------------------------------------------------------------------------------------------- bölümler
def _cip(etiket: str, b: dict) -> str:
    n = b["net_getiri"]
    sev = BANT_SEVIYE[n["bant"]]
    return f'<span class="cip {sev}">{esc(etiket)} net {esc(f_yuzde(n["deger"], True))} · {esc(BANT_ADI[n["bant"]])}</span>'


def _veri_yok(dosya: str) -> str:
    return f'<div class="uyari kritik">{esc(dosya)} okunamadığı için bu bölüm gösterilemiyor; değer uydurulmaz.</div>'


def _ek_yok(dosya: str) -> str:
    return f'<div class="kart alt">Veri yok: {esc(dosya)} bulunamadı (motor henüz yazmıyor olabilir).</div>'


def _sirali(b: dict):
    return sorted(b.items(), key=lambda kv: int(kv[0]))


def _poz_satiri(p: dict) -> str:
    """Strateji içindeki açık pozisyon -> tek satır (yalnız dosyadaki alanlar)."""
    if "sembol" in p and "yon" in p:
        parca = [f"{p['sembol']} {p['yon']}"]
        if p.get("nominal") is not None:
            parca.append(f"tutar {f_para(p['nominal'])}")
        if p.get("kz") is not None:
            parca.append(f"K/Z {f_para(p['kz'], True)}" + (f" ({f_yuzde(p.get('kz_oran'), True)})" if p.get("kz_oran") is not None else ""))
        if p.get("stop") is not None:
            parca.append(f"stop {p['stop']}")
        if len(parca) > 1:
            return " · ".join(parca)
    return " ".join(f"{k}={v}" for k, v in p.items())


@_guvenli
def _strateji_html(x: dict) -> str:
    """Strateji satırı: tablo görünümlü özet satırı + tıklayınca açılan <details> (JS gerekmez; mobilde kart gibi yığılır)."""
    b = x["beklenti"]
    perf = x.get("performans")
    kol = esc(x["kol"]) + (f' · {esc(f_yuzde(x["kol_payi"], ondalik=0))}' if x.get("kol_payi") is not None else "")
    durum = f' <span class="cip uyari">{esc(x["durum"])}</span>' if x.get("durum") and x["durum"] != "calisiyor" else ""
    konum = "".join(_cip(f"{hf} hf", v) for hf, v in _sirali(b)) or '<span class="alt">—</span>'
    ust = (f'<span class="ad"><b>{esc(kisa_kimlik(x["kimlik"]))}</b>{durum}</span>'
           f'<span class="h" data-e="Stil">{esc(x["ajan"])}</span><span class="h" data-e="Kol">{kol}</span>'
           f'<span class="h sg {_isaret_sinifi(x["katki_getiri"])}" data-e="Katkı">{esc(f_para(x["ozsermaye_katkisi"], True))} <span class="alt">({esc(f_yuzde(x["katki_getiri"], True))})</span></span>'
           f'<span class="h sg" data-e="İşlem">{esc(str(x["islem_sayisi"]))}</span>'
           f'<span class="h sg" data-e="Kazanma">{esc(f_yuzde(x["kazanma_orani"], ondalik=1))}</span>'
           f'<span class="h sg" data-e="PF">{esc(f_sayi(perf["pf"]) if perf else "—")}</span>'
           f'<span class="h" data-e="Beklenti konumu"><span class="kolonlar" style="margin:0">{konum}</span></span>'
           f'<span class="h sg" data-e="Açık">{len(x["acik_pozisyonlar"])}</span>')
    g = []
    if perf:
        g.append(_sat("Ort. kâr / ort. zarar", f"{f_para(perf['ort_kar'], True)} / {f_para(perf['ort_zarar'], True)}"))
        g.append(_sat("Net · PF", f"{f_para(perf['net'], True)} · {f_sayi(perf['pf'])}", _isaret_sinifi(perf["net"])))
    if x.get("ayar") is not None:
        g.append(_sat("Ayar", str(x["ayar"])))
    if "sonraki_yenileme" in x:
        g.append(_sat("Sonraki ayar yenileme (TSİ)", tsi(x["sonraki_yenileme"])))
    if x["acik_pozisyonlar"]:
        for p in x["acik_pozisyonlar"]:
            g.append(_sat("Açık pozisyon", _poz_satiri(p)))
    else:
        g.append(_sat("Açık pozisyon", "yok"))
    s = x["son_islem"]
    g.append(_sat("Son işlem (TSİ)", "—" if not s else f"{tsi(s['zaman'])} {s['sembol']} {s['yon']} R {f_sayi(s['r'])}"))
    for hf, v in _sirali(b):
        n, m = v["net_getiri"], v["max_dusus"]
        g.append(f'<div class="alt">{esc(hf)} hf aralık (net %5/%50/%95): {esc(f_yuzde(n["p05"], True))} / {esc(f_yuzde(n["p50"], True))} / {esc(f_yuzde(n["p95"], True))}'
                 f' · düşüş {esc(f_yuzde(m["deger"]))} (%95: {esc(f_yuzde(m["p95"]))})</div>')
    return f'<details class="kd"><summary>{ust}</summary><div class="govde">{"".join(g)}</div></details>'


SEKMELER = (("t1", "ÖZET"), ("t2", "STRATEJİLER"), ("t3", "POZİSYON"), ("t4", "İŞLEMLER"), ("t5", "RİSK"), ("t6", "SAĞLIK"))


def _serit(oz: dict, mr) -> str:
    """Sabit üst rakam şeridi (her sekmede görünür). Hepsi dosyadaki alanlar; null -> '—' + neden."""
    if oz.get("hafta_pnl") is not None:
        hafta = _kutu("Bu hafta", f_para(oz["hafta_pnl"], True), _isaret_sinifi(oz["hafta_pnl"]))
    else:
        hafta = _kutu("Bu hafta", "—", "", _neden(oz, "hafta_pnl") or ("ölçülmedi" if "hafta_pnl" in oz else "motor bu alanı yazmıyor"))
    bas = oz.get("baslangictan_pnl", oz["toplam_pnl"])
    brut = f"brüt {f_para(mr['toplam_brut_nominal'])}" if mr and mr.get("toplam_brut_nominal") is not None else ""
    return ('<div class="izgara serit">'
            + _kutu("Özsermaye", f_para(oz["ozsermaye"]), "", f"başlangıç {f_para(oz['baslangic_ozsermaye'])}")
            + _kutu("Bugün", f_para(oz["gun_pnl"], True), _isaret_sinifi(oz["gun_pnl"]), f_yuzde(oz["gun_getiri"], True))
            + hafta
            + _kutu("Başlangıçtan beri", f_para(bas, True), _isaret_sinifi(bas), f_yuzde(oz["toplam_getiri"], True))
            + _kutu("Zirveden düşüş", f_yuzde(oz["zirveden_dusus"]), "kotu" if oz["zirveden_dusus"] else "", f"zirve {f_para(oz['zirve_ozsermaye'])}")
            + _kutu("Açık pozisyon", str(oz["sayaclar"]["acik_pozisyon"]), "", brut)
            + "</div>")


@_guvenli
def _risk_payi(oz: dict) -> str:
    r = oz["risk"]
    gk, kl, ks, ar = r["gunluk_kayip"], r["kaldirac"], r["kill_switch"], r["acik_stop_riski"]
    return (_kullanim_satiri("Günlük kayıp", f_yuzde(gk["limit"], ondalik=0), gk["kullanim"], f_yuzde(gk["deger"]))
            + _kullanim_satiri("Kaldıraç", f_sayi(kl["limit"], 1) + "x", kl["kullanim"], f_sayi(kl["deger"]) + ("x" if kl["deger"] is not None else ""))
            + _kullanim_satiri("Açık stop riski", f_yuzde(ar["limit"], ondalik=0), ar["kullanim"], f_yuzde(ar["deger"]))
            + _kullanim_satiri("Kill switch (zirveden düşüş)", f_yuzde(ks["limit"], ondalik=0), None, f_yuzde(ks["dusus"]),
                               alt_metin=f"mesafe {f_yuzde(ks['mesafe'])}" + (" — TETİKLENDİ" if ks["tetiklendi"] else "")))


@_guvenli
def _saglik_ozet(sg: dict) -> str:
    sv = sg["servis"]
    g = [_sat("Durum", sg["durum"], "iyi" if sg["durum"] == "ok" else "kotu"), _sat("Son çalışma (TSİ)", tsi(sg["son_calisma"])),
         _sat("Servis", {True: "çalışıyor", False: "ÇALIŞMIYOR", None: "yok (backtest)"}[sv["calisiyor"]], "kotu" if sv["calisiyor"] is False else "")]
    for v in sg["veri"][:4]:
        g.append(_sat(f"{v['sembol']} {v['tf']}", f"{v['bayatlik_dk']} dk" + (" · BAYAT" if v["bayat"] else ""), "kotu" if v["bayat"] else ""))
    if len(sg["veri"]) > 4:
        g.append(f'<div class="alt">+{len(sg["veri"]) - 4} veri akışı daha: SAĞLIK sekmesi</div>')
    return "".join(g)


@_guvenli
def _beklenti_tablosu(st: dict) -> str:
    satir = []
    for hf, b in _sirali(st["set"]["beklenti"]):
        n, m = b["net_getiri"], b["max_dusus"]
        satir.append([esc(f"{hf} hf"), _h(f_yuzde(n["deger"], True), _isaret_sinifi(n["deger"])), f'<span class="cip {BANT_SEVIYE[n["bant"]]}">{esc(BANT_ADI[n["bant"]])}</span>',
                      esc(f_yuzde(n["p05"], True)), esc(f_yuzde(n["p50"], True)), esc(f_yuzde(n["p95"], True)),
                      esc(f_yuzde(m["deger"])), esc(f_yuzde(m["p95"]))])
    if not satir:
        return '<div class="alt" style="padding:10px 11px">Beklenti aralığı kaydı yok (pencere henüz dolmamış olabilir).</div>'
    return _tablo(["Pencere", "Net getiri", "Konum", "Net %5", "Net %50", "Net %95", "Düşüş", "Alarm üstü (%95)"], satir, sag=(1, 3, 4, 5, 6, 7))


def _sekme_ozet(oz, st, gc, ic, sg) -> str:
    if not oz:
        return _veri_yok("ozet.json")
    ds, kz = oz.get("dusus_serisi"), oz.get("gunluk_kz")
    yok = lambda a: f'<div class="alt">Veri yok: {a} ozet.json içinde yok.</div>'          # noqa: E731
    hesap = ('<div class="izgara c4">' + _kutu("Max düşüş", f_yuzde(oz["max_dusus"])) + _kutu("Başlangıç", f_para(oz["baslangic_ozsermaye"]))
             + _kutu("Zirve özsermaye", f_para(oz["zirve_ozsermaye"])) + _kutu("Kapanan işlem", str(oz["sayaclar"]["kapanan_islem"])) + "</div>")
    egri = _egri(gc, oz["baslangic_ozsermaye"]) if gc else _veri_yok("ozsermaye_gecmisi.json")
    g = [_p("Özsermaye eğrisi", egri + '<div class="bol">' + hesap + "</div>", f_para(oz["ozsermaye"]), "g2 yuk"),
         _sag(_p("Risk payı", _risk_payi(oz), "sınıra göre") + _p("Sağlık", _saglik_ozet(sg) if sg else _ek_yok("saglik.json"), sg["durum"] if sg else ""), "s1"),
         _p("Zirveden düşüş", _dusus_grafigi(ds) if ds is not None else yok("dusus_serisi"), f_yuzde(oz["zirveden_dusus"])),
         _p("Günlük K/Z", _kz_grafigi(kz) if kz is not None else yok("gunluk_kz"), f_para(kz[-1]["pnl"], True) if kz else ""),
         _p("İçgörüler", _icgoruler(ic))]
    g.append(_p("Beklenti aralığına göre konum", _beklenti_tablosu(st) if st else _veri_yok("stratejiler.json"), "SET (tüm stratejiler)", "g3", duz=bool(st)))
    return _ig("".join(g))


@_guvenli
def _icgoruler(ic) -> str:
    if ic is None:
        return _ek_yok("icgoruler.json")
    c = ic["cumleler"]
    return '<div class="ic">' + ("".join(f"<div>{esc(x)}</div>" for x in c) if c else '<div class="alt">İçgörü yok.</div>') + "</div>"


def _sekme_stratejiler(st) -> str:
    if not st:
        return _veri_yok("stratejiler.json")
    bas = ["Strateji", "Stil", "Kol", "Katkı", "İşlem", "Kazanma", "PF", "Beklenti konumu", "Açık"]
    sag = (3, 4, 5, 6, 8)
    sh = '<div class="sh">' + "".join(f'<span{" class=sg" if i in sag else ""}>{esc(x)}</span>' for i, x in enumerate(bas)) + "</div>"
    tablo = f'<div class="tw"><div class="stw">{sh}{"".join(_strateji_html(x) for x in st["stratejiler"])}</div></div>'
    return _ig(_p(f"Stratejiler ({len(st['stratejiler'])})", tablo, "satıra dokun / tıkla: ayrıntı", "g3", duz=True))


@_guvenli
def _poz_tablosu(mr: dict) -> str:
    satir = []
    for p in mr["pozisyonlar"]:
        kz = "—" if p.get("kz") is None else f_para(p["kz"], True) + (f" ({f_yuzde(p.get('kz_oran'), True)})" if p.get("kz_oran") is not None else "")
        satir.append([f"<b>{esc(p['sembol'])}</b>", _h(p["yon"], "iyi" if p["yon"] == "long" else "kotu"), esc(f_para(p.get("nominal"))),
                      _h(kz, _isaret_sinifi(p.get("kz"))), esc(kisa_kimlik(p["kimlik"])), esc(p.get("giris_fiyati") or "—"),
                      esc(p.get("mark_fiyat") or "—"), esc(p.get("stop") or "—"), esc(tsi(p.get("giris_zamani")))])
    if not satir:
        return '<div class="kart alt">Açık pozisyon yok.</div>'
    return _tablo(["Sembol", "Yön", "Tutar", "K/Z", "Strateji", "Giriş", "Mark", "Stop", "Giriş zamanı (TSİ)"], satir, sag=(2, 3, 5, 6, 7))


@_guvenli
def _poz_tablosu_stratejiden(st: dict) -> str:
    """maruziyet.json yoksa: stratejiler.json'daki açık pozisyon nesneleri (eski görünüm)."""
    satir = [[f"<b>{esc(kisa_kimlik(x['kimlik']))}</b>", esc(_poz_satiri(p))] for x in st["stratejiler"] for p in x["acik_pozisyonlar"]]
    return _tablo(["Strateji", "Pozisyon"], satir) if satir else '<div class="kart alt">Açık pozisyon yok.</div>'


@_guvenli
def _maruziyet_sag(mr: dict, oz: dict) -> str:
    """Pozisyon sekmesi sağ kolonu: maruziyet kartları + sembol başına para dağılımı."""
    ar = mr["acik_stop_riski"]
    kul = oz["risk"]["acik_stop_riski"].get("kullanim")
    kartlar = ('<div class="izgara c2">'
               + _kutu("Brüt nominal", f_para(mr["toplam_brut_nominal"])) + _kutu("Net nominal", f_para(mr["toplam_net_nominal"], True))
               + _kutu("Kaldıraç", f_sayi(mr["kaldirac"]) + ("x" if mr["kaldirac"] is not None else ""))
               + _kutu("Kullanılan teminat", f_para(mr["kullanilan_teminat"]), "", mr.get("teminat_notu") or "")
               + "</div>"
               + '<div class="bol">' + _kullanim_cubugu("Açık stop riski", ar.get("oran"), f_yuzde(ar.get("limit"), ondalik=0), kul,
                                                        f"{f_para(ar['deger'])} ({f_yuzde(ar.get('oran'))})") + "</div>")
    g = [_p("Maruziyet", kartlar)]
    sem = mr["semboller"]
    if sem:
        enb = max([float(s["brut_oran"]) for s in sem if s.get("brut_oran") is not None] or [0.0]) or 1.0     # yalnız çubuk ölçeği
        satir = []
        for s in sem:
            gen = 0.0 if s.get("brut_oran") is None else float(s["brut_oran"]) / enb * 100
            satir.append(f'<div class="mr"><div class="sat"><span><b>{esc(s["sembol"])}</b></span><b>brüt {esc(f_para(s["brut_nominal"]))} · kasanın {esc(f_yuzde(s.get("brut_oran")))}</b></div>'
                         f'<div class="cubuk"><i style="width:{gen:.1f}%"></i></div>'
                         f'<div class="alt">net {esc(f_para(s["net_nominal"], True))} (kasanın {esc(f_yuzde(s.get("net_oran"), True))})</div></div>')
        g.append(_p("Para dağılımı", "".join(satir), "sembol başına, kasaya oran"))
    return "".join(g)


@_guvenli
def _stop_riski(mr: dict) -> str:
    poz = sorted(mr["pozisyonlar"], key=lambda p: Decimal(p["stop_riski"] or "0"), reverse=True)
    if not poz:
        return '<div class="alt">Açık pozisyon yok.</div>'
    enr = max(Decimal(p["stop_riski"] or "0") for p in poz) or Decimal(1)                                  # yalnız çubuk ölçeği
    satir = []
    for p in poz:
        gen = 0.0 if p.get("stop_riski") is None else float(Decimal(p["stop_riski"]) / enr * 100)
        satir.append(f'<div class="mr"><div class="sat"><span><b>{esc(p["sembol"])}</b> {esc(p["yon"])} <span class="alt">{esc(kisa_kimlik(p["kimlik"]))}</span></span>'
                     f'<b class="nw">{esc(f_para(p.get("stop_riski")))}</b></div><div class="cubuk k"><i style="width:{gen:.1f}%"></i></div></div>')
    return "".join(satir)


def _sekme_pozisyon(oz, st, mr) -> str:
    if not oz:
        return _veri_yok("ozet.json")
    n = oz["sayaclar"]["acik_pozisyon"]
    if mr is not None:
        return _ig(_p(f"Açık pozisyonlar ({n})", _poz_tablosu(mr), "", "g2", duz=True) + _sag(_maruziyet_sag(mr, oz))
                   + _p("Açık stop riski", _stop_riski(mr), "pozisyon başına", "g2"))
    return _ig(_p(f"Açık pozisyonlar ({n})", _poz_tablosu_stratejiden(st) if st else _veri_yok("stratejiler.json"), "", "g2", duz=True)
               + _sag(_p("Maruziyet", _ek_yok("maruziyet.json"))))


@_guvenli
def _performans_tablosu(st: dict) -> str:
    def anahtar(x):
        p = x.get("performans")
        return Decimal(p["net"]) if p and p.get("net") is not None else Decimal("-Infinity")
    satir = []
    for x in sorted(st["stratejiler"], key=anahtar, reverse=True):
        p = x.get("performans")
        if not p:
            satir.append([esc(kisa_kimlik(x["kimlik"]))] + ["—"] * 6)
            continue
        satir.append([esc(kisa_kimlik(x["kimlik"])), esc(str(p["islem"])), esc(f_yuzde(p["kazanma_orani"], ondalik=1)),
                      _h(f_para(p["ort_kar"], True), "iyi" if p["ort_kar"] is not None else ""),
                      _h(f_para(p["ort_zarar"], True), "kotu" if p["ort_zarar"] is not None else ""),
                      _h(f_para(p["net"], True), _isaret_sinifi(p["net"])), esc(f_sayi(p["pf"]))])
    return _tablo(["Strateji", "İşlem", "Kazanma", "Ort. kâr", "Ort. zarar", "Net", "PF"], satir, sag=(1, 2, 3, 4, 5, 6))


@_guvenli
def _maliyet_toplam(ml: dict) -> str:
    def satir(ad, b):
        return [esc(ad), esc(f_para(b["ucret"])), esc(f_para(b["kayma"])), esc(f_para(b["funding"], True)), f"<b>{esc(f_para(b['toplam']))}</b>"]
    t = ml["toplam"]
    g = [_tablo(["", "Ücret", "Kayma", "Funding", "Toplam"], [satir("Son 24 sa", t["son24s"]), satir("Tüm dönem", t["tum"])], sag=(1, 2, 3, 4))]
    return "".join(g)


@_guvenli
def _maliyet_strateji(ml: dict) -> str:
    g = []
    if ml.get("stratejiler"):
        sr = [[esc(kisa_kimlik(k)), esc(f_para(v["son24s"]["toplam"])), esc(f_para(v["tum"]["ucret"])), esc(f_para(v["tum"]["kayma"])),
               esc(f_para(v["tum"]["funding"], True)), f"<b>{esc(f_para(v['tum']['toplam']))}</b>"]
              for k, v in sorted(ml["stratejiler"].items(), key=lambda kv: Decimal(kv[1]["tum"]["toplam"]), reverse=True)]
        g.append(_tablo(["Strateji", "24 sa toplam", "Ücret (tüm)", "Kayma (tüm)", "Funding (tüm)", "Toplam (tüm)"], sr, sag=(1, 2, 3, 4, 5)))
    if ml.get("not"):
        g.append(f'<div class="alt" style="padding:8px 11px">{esc(ml["not"])}</div>')
    return "".join(g) or '<div class="alt" style="padding:8px 11px">Strateji başına maliyet kaydı yok.</div>'


def _neden_metni(k: str) -> str:
    tur, _, neden = k.partition(":")
    return f"{tur} · {neden}" if neden else k


@_guvenli
def _reddedilen_neden(rd: dict) -> str:
    s24, tum = rd.get("son24s") or {}, rd.get("tum") or {}
    anahtarlar = sorted(set(s24) | set(tum), key=lambda k: (-int(tum.get(k, 0)), k))
    if not anahtarlar:
        return '<div class="alt" style="padding:8px 11px">Atlanan ya da küçültülen sinyal kaydı yok.</div>'
    return _tablo(["Neden", "Son 24 sa", "Tüm dönem"], [[esc(_neden_metni(k)), esc(str(s24.get(k, 0))), esc(str(tum.get(k, 0)))] for k in anahtarlar], sag=(1, 2))


@_guvenli
def _reddedilen_son(rd: dict) -> str:
    son = sorted(rd.get("son") or [], key=lambda r: r["zaman"], reverse=True)
    g = []
    if son:
        g.append(_tablo(["Zaman (TSİ)", "Tür", "Neden", "Strateji", "Sembol"],
                        [[esc(tsi(r["zaman"])), esc(r["tur"]), esc(r["neden"]), esc(kisa_kimlik(r["kimlik"])), esc(r["sembol"])] for r in son], sinif="kay"))
    else:
        g.append('<div class="alt" style="padding:8px 11px">Son reddedilen / küçültülen kayıt yok.</div>')
    if rd.get("not"):
        g.append(f'<div class="alt" style="padding:8px 11px">{esc(rd["not"])}</div>')
    return "".join(g)


@_guvenli
def _son_islemler(isl: list) -> str:
    son = sorted(isl, key=lambda s: s["zaman"], reverse=True)[:20]
    if not son:
        return '<div class="alt" style="padding:8px 11px">Kapanan işlem yok.</div>'
    satir = [[f"<b>{esc(tsi(s['zaman']))}</b>", esc(s["sembol"]), _h(s["yon"], "iyi" if s["yon"] == "long" else "kotu"), esc(f_sayi(s["r"])),
              esc(f_para(s["set_katki_usd"], True) if s["set_katki_usd"] is not None else "katkı: kol düzeyinde"),
              esc(kisa_kimlik(s["kimlik"])), esc(s["cikis_nedeni"])] for s in son]
    return _tablo(["Zaman (TSİ)", "Sembol", "Yön", "R", "Set katkısı", "Strateji", "Çıkış nedeni"], satir, sag=(3, 4), sinif="kay")


def _sekme_islemler(isl, st, ml, rd) -> str:
    perf = _p("Strateji performansı", _performans_tablosu(st) if st else _veri_yok("stratejiler.json"), "net kâr/zarara göre", "g2", duz=bool(st))
    sag = _sag(_p("Maliyet dökümü", _maliyet_toplam(ml) if ml is not None else _ek_yok("maliyet.json"), "ücret · kayma · funding", duz=ml is not None)
               + _p("Atlanan / reddedilen sinyaller", _reddedilen_neden(rd) if rd is not None else _ek_yok("reddedilen.json"), "neden başına", duz=rd is not None), "s1")
    if isl is None:
        son = _p("Son kapanan işlemler", _veri_yok("islemler.jsonl"), "", "g3")
    else:
        son = _p("Son kapanan işlemler", _son_islemler(isl), f"{min(len(isl), 20)} / {len(isl)} · saat TSİ", "g3", duz=True)
    alt = (_p("Maliyet — strateji başına", _maliyet_strateji(ml), "", "g3", duz=True) if ml is not None else "")
    alt += (_p("Son atlanan / küçültülen sinyaller", _reddedilen_son(rd), "saat TSİ", "g3", duz=True) if rd is not None else "")
    return _ig(perf + sag + son + alt)


@_guvenli
def _olaylar_html(ol: list) -> str:
    son = sorted(ol, key=lambda o: o["zaman"], reverse=True)[:50]
    if not son:
        return '<div class="kart alt">Kayıtlı risk olayı yok.</div>'
    return _tablo(["Zaman (TSİ)", "Tür", "Mesaj"], [[f"<b>{esc(tsi(o['zaman']))}</b>", f'<span class="cip">{esc(o["tur"])}</span>', f'<span style="white-space:normal">{esc(o["mesaj"])}</span>']
                                                     for o in son], sinif="kay")


def _sekme_risk(oz, ol) -> str:
    if not oz:
        return _veri_yok("ozet.json")
    r = oz["risk"]
    gk, kl, ks, ar = r["gunluk_kayip"], r["kaldirac"], r["kill_switch"], r["acik_stop_riski"]
    kartlar = ('<div class="izgara c4">'
               + _kullanim_cubugu("Günlük kayıp", gk["deger"], f_yuzde(gk["limit"], ondalik=0), gk["kullanim"], f_yuzde(gk["deger"]))
               + _kullanim_cubugu("Kaldıraç", kl["deger"], f_sayi(kl["limit"], 1) + "x", kl["kullanim"], f_sayi(kl["deger"]) + ("x" if kl["deger"] is not None else ""))
               + _kullanim_cubugu("Açık stop riski", ar["deger"], f_yuzde(ar["limit"], ondalik=0), ar["kullanim"], f_yuzde(ar["deger"]))
               + _kullanim_cubugu("Kill switch (zirveden düşüş)", ks["dusus"], f_yuzde(ks["limit"], ondalik=0), None, f_yuzde(ks["dusus"]),
                                  alt_metin=f"mesafe {f_yuzde(ks['mesafe'])}")
               + "</div>")
    notlar = [_sat("Kill switch mesafesi", f_yuzde(ks["mesafe"]) + (" — TETİKLENDİ" if ks["tetiklendi"] else ""), "kotu" if ks["tetiklendi"] else "")]
    if kl.get("not"):
        notlar.append(f'<div class="alt" style="margin-top:6px">{esc(kl["not"])}</div>')
    for n in oz["notlar"]:
        notlar.append(f'<div class="alt" style="margin-top:6px">{esc(n)}</div>')
    return _ig(_p("Risk limitleri", kartlar, "limite göre kullanım", "g3")
               + _p("Risk olayları (son 50)", _olaylar_html(ol) if ol is not None else _ek_yok("olaylar.jsonl"), "saat TSİ", "g2", duz=ol is not None)
               + _p("Kill switch ve notlar", "".join(notlar)))


def _sekme_saglik(sg) -> str:
    if not sg:
        return _veri_yok("saglik.json")
    sv = sg["servis"]
    motor = ('<div class="izgara oto">'
             + _kutu("Durum", sg["durum"], "iyi" if sg["durum"] == "ok" else "kotu") + _kutu("Son çalışma (TSİ)", tsi(sg["son_calisma"]))
             + _kutu("Servis", {True: "çalışıyor", False: "ÇALIŞMIYOR", None: "yok (backtest)"}[sv["calisiyor"]], "kotu" if sv["calisiyor"] is False else "", f"sürüm {sv['surum']}")
             + "</div>")
    veri = ('<div class="izgara oto">' + "".join(
        _kutu(f"{v['sembol']} {v['tf']} son mum (TSİ)", tsi(v["son_mum_zamani"]), "kotu" if v["bayat"] else "", f"{v['bayatlik_dk']} dk" + (" · BAYAT" if v["bayat"] else ""))
        for v in sg["veri"]) + "</div>") if sg["veri"] else '<div class="alt">Veri akışı kaydı yok.</div>'
    return _ig(_p("Motor", motor, "", "g3") + _p("Veri akışları", veri, "son mum zamanı ve gecikme", "g3"))


def html_olustur(veri: dict, sorunlar: list, simdi: datetime) -> str:
    oz, st, sg, isl, gc = (veri.get(k) for k in ("ozet", "stratejiler", "saglik", "islemler", "gecmis"))
    mr, ml, rd, ol, ic = (veri.get(k) for k in ("maruziyet", "maliyet", "reddedilen", "olaylar", "icgoruler"))
    u = uyarilar(veri, sorunlar, simdi)
    canli_mi = bool(oz and oz["kaynak"] != "backtest")
    g = []
    if canli_mi and oz.get("yazildi_zaman"):           # tarayıcı tarafı bayatlık bandı: JS yoksa gizli kalır (sunucu tarafı uyarılar yine geçerli)
        g.append(f'<div id="bayat" class="uyari bayat-bant" role="alert" hidden data-zaman="{esc(oz["yazildi_zaman"])}" data-esik-dk="{BAYATLIK_ESIK_DK}">'
                 '⚠ VERİ BAYAT: son güncelleme <span id="bayat-dk">?</span> dk önce, sistem durmuş olabilir</div>')
    g.append('<header class="ust"><div class="mk"><span class="lg0">1L</span><h1>1L3A PANO</h1></div><div class="un">'
             + (f'<span class="rozet r-{esc(oz["kaynak"])}">{esc(KAYNAK_ADI[oz["kaynak"]])}</span>' if oz else "")
             + f'<span class="so">üretildi {esc(tsi(d.zaman_str(simdi)))} TSİ</span>'
             + (f'<span class="so">durum zamanı {esc(tsi(oz["zaman"]))} TSİ' + (" · ~15 dakikada bir yenilenir" if canli_mi else "") + "</span>" if oz else "")
             + '<button id="tema" type="button">Tema</button></div></header>')
    for sev, m in u:                                   # uyarılar sekmelerin ÜSTÜNDE: hangi sekmede olursan ol görünür
        g.append(f'<div class="uyari {sev}" role="{"alert" if sev == "kritik" else "note"}">{esc(m)}</div>')
    if not oz:
        g.append('<div class="uyari kritik">Özet dosyası (ozet.json) okunamadığı için hesap bilgisi gösterilemiyor; değer uydurulmaz.</div>')
    else:
        g.append(_serit(oz, mr))
    # rozetler: durum dosyasındaki sayılar (hesap değil)
    rozet = {"t2": str(len(st["stratejiler"])) if st else None, "t3": str(oz["sayaclar"]["acik_pozisyon"]) if oz else None,
             "t4": str(len(isl)) if isl is not None else None}
    sorun_var = bool(sg and (sg["durum"] != "ok" or any(v["bayat"] for v in sg["veri"])))
    g.append('<div class="sekme-kok">')
    g.append("".join(f'<input type="radio" name="t" id="{i}"' + (" checked" if i == "t1" else "") + ' aria-label="' + esc(ad) + '">' for i, ad in SEKMELER))
    g.append('<div class="tabs" role="tablist">' + "".join(
        f'<label for="{i}">{esc(ad)}' + (f' <em>{esc(rozet[i])}</em>' if rozet.get(i) is not None else "")
        + (' <em class="k">!</em>' if i == "t6" and sorun_var else "") + "</label>" for i, ad in SEKMELER) + "</div>")
    icerik = (_sekme_ozet(oz, st, gc, ic, sg), _sekme_stratejiler(st), _sekme_pozisyon(oz, st, mr), _sekme_islemler(isl, st, ml, rd),
              _sekme_risk(oz, ol), _sekme_saglik(sg))
    g.append('<div class="sekmeler">' + "".join(f'<section class="n{k}">{c}</section>' for k, c in enumerate(icerik, 1)) + "</div></div>")
    g.append('<div class="alt ayak">Pano yeni hesap yapmaz: sayılar durum dosyalarından aynen gösterilir. Saatler TSİ (Türkiye saati).</div>')
    return ('<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="dark light"><title>1L3A pano</title><style>' + CSS + "</style></head><body><main>"
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
