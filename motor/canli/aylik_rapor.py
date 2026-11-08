"""Aylık rapor + paper kabul kontrol listesi (pano öncelik 3). Hesap BURADA (motor tarafı); pano yalnız biçimler.

Ay = TSİ takvim ayı (Europe/Istanbul, gün kesimi `durum_ek`); işlem ayı çıkış zamanının TSİ günündendir. Aylık özet yalnız kapanmış
işlemler ve günlük özsermaye serisinden gelir (lookahead yok). Dönem getirisi/K-Z `ozet.aylik_kz_ajan` ile AYNI sayıdır (aynı kaynak).

KABUL KONTROL LİSTESİ ölçütleri (eski panonunkiler — %10 DD, PSR>%95, 30 işlem, 60 gün — KULLANILMAZ). Her kalemin `kaynak` alanı dayanağı gösterir:
  sure         DURUM.md Aşama 4 "Süre ≥ 8 hafta" + lider günlüğü 2026-11-07 "en erken değerlendirme 2027-01-02" (başlangıç + 56 gün).
  set_beklenti DURUM.md Aşama 4 "Bitiş: ... sonuçların beklenti aralığında olması"; set 8 hafta net getiri/düşüş alarm eşiği
               (sonuclar/final/OZET.md "Alarm eşiği (set, 8 hafta)"; stratejiler.json set.beklenti alarm).
  sert_limit   DURUM.md karar 14 + 25 (sert limitler kesin) ve kullanıcının 2026-11-08 görevi "sert limit ihlali olmaması": kill switch
               tetiklenmedi; anlık kaldıraç / açık stop riski / günlük kayıp limiti aşılmadı.
  Bilgi kalemleri (geçti/kaldı vermez): strateji bazlı beklenti alarmı, dersler durum sayımı, günlük limit olayı sayısı.
  Tanımsız kalemler (DURUM.md'de karşılığı yok; eşik UYDURULMAZ, durum "tanimsiz" + kullanıcıya soru): kesintisiz çalışma ölçütü, asgari işlem.
`genel_durum`: "kaldi" (bir kalem kaldı) | "bekliyor" (kaldı yok, bir kalem bekliyor) | "tamam" (tanımlı kalemlerin hepsi geçti;
tanımsız kalemler kullanıcı kararını bekler — bu bir kabul KARARI değildir).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from motor.canli import dersler as ders
from motor.canli import durum as d
from motor.canli import durum_ek as ek

PAPER_MIN_GUN = 56                      # 8 hafta (DURUM.md Aşama 4)
EN_ERKEN_DEGERLENDIRME = "2027-01-02"   # DURUM.md lider günlüğü 2026-11-07
KESINTI_OLAYLARI = ("veri_bosluk", "ws_koptu", "yeniden_baslatma", "binance_hata", "veri_yok")
TANIMSIZ = [
    {"ad": "kesintisiz_calisma", "soru": "'Kesintisiz çalışma' için kabul edilen en uzun kesinti ve sayı nedir (ör. veri boşluğu/yeniden başlatma kaç kez, kaç dk)? "
                                        "DURUM.md Aşama 4 yalnız 'kesintisiz çalışma' der; sayısal tanım yok."},
    {"ad": "asgari_islem", "soru": "Kabul için set/strateji bazında en az kaç kapanan işlem gerekir? (DURUM.md'de yok; Dersler'deki 'örnek az' sınırı "
                                    f"{ders.MIN_ISLEM_DERS} yalnız geçici)"},
    {"ad": "strateji_alarmi_kabulu", "soru": "'Sonuçların beklenti aralığında olması' yalnız set için mi, her strateji için mi aranır? (şimdi: set kabul kalemi, "
                                              "strateji bazı bilgi)"},
    {"ad": "gunluk_limit_olayi", "soru": "Günlük kayıp limitinin (%3) tetiklenmesi sert limit ihlali sayılır mı? (şimdi: sayılmaz, bilgi olarak sayılır; kill switch ve aşım kaldı)"},
    {"ad": "dersler_durumu", "soru": "Bir stratejinin Dersler durumunun 'altında' çıkması kabulü bozar mı? (şimdi: bilgi; eşikler de tanımsız: dersler.json tanimsiz_esikler)"},
]


def _kalem(id_: str, ad: str, olcut: str, kaynak: str, durum: str, deger: Optional[str], neden: Optional[str] = None) -> dict:
    return {"id": id_, "ad": ad, "olcut": olcut, "kaynak": kaynak, "durum": durum, "deger": deger, "neden": neden}


def kabul_listesi(*, simdi, donem_bas, risk: dict, sayaclar: dict, set_konum: dict, strat_konum: dict, dersler: dict,
                  saglik_durum: Optional[str], olaylar: list, limit_olaylari: list) -> dict:
    """Paper kabul kontrol listesi (anlık durum, birikimli). -> {'kalemler': [...], 'genel_durum', 'sayim', 'tanimsiz'}."""
    k = []
    # --- süre
    if donem_bas is None:
        k.append(_kalem("sure", "Paper süresi ≥ 8 hafta", f"≥ {PAPER_MIN_GUN} gün", "DURUM.md Aşama 4 + lider günlüğü 2026-11-07", "bekliyor", None, "başlangıç günü yok"))
    else:
        bas, su = ek._utc(donem_bas), ek._utc(simdi)
        gun = (su - bas).days
        erken = str((bas + timedelta(days=PAPER_MIN_GUN)).date())
        k.append(_kalem("sure", "Paper süresi ≥ 8 hafta", f"≥ {PAPER_MIN_GUN} gün (en erken değerlendirme {EN_ERKEN_DEGERLENDIRME})",
                        "DURUM.md Aşama 4 (Süre ≥ 8 hafta) + lider günlüğü 2026-11-07 (en erken 2027-01-02)",
                        "gecti" if gun >= PAPER_MIN_GUN else "bekliyor", f"{gun} / {PAPER_MIN_GUN} gün", f"başlangıç + {PAPER_MIN_GUN} gün = {erken}"))
    # --- set beklenti aralığı (8 hafta)
    s8 = (set_konum or {}).get("8")
    if s8 is None:
        k.append(_kalem("set_beklenti", "Set sonuçları beklenti aralığında (8 hafta)", "8 hf net getiri ≥ %5 yüzdeliği ve düşüş ≤ %95 yüzdeliği",
                        "DURUM.md Aşama 4 (beklenti aralığında) + sonuclar/final/OZET.md alarm eşiği", "bekliyor", None, "8 haftalık pencere henüz dolmadı"))
    else:
        nb, dd = s8["net_getiri"], s8["max_dusus"]
        bozuk = [ad for ad, b in (("net getiri", nb), ("düşüş", dd)) if b["alarm"]]
        k.append(_kalem("set_beklenti", "Set sonuçları beklenti aralığında (8 hafta)", "8 hf net getiri ≥ %5 yüzdeliği ve düşüş ≤ %95 yüzdeliği",
                        "DURUM.md Aşama 4 (beklenti aralığında) + sonuclar/final/OZET.md alarm eşiği", "kaldi" if bozuk else "gecti",
                        f"net {nb['deger'] * 100:+.2f}% ({nb['bant']}), düşüş {dd['deger'] * 100:.2f}% ({dd['bant']})",
                        ("alarm: " + ", ".join(bozuk)) if bozuk else None))
    # --- sert limit
    kill_ev = sum(1 for o in limit_olaylari if o["tur"] == "kill_switch")
    asimlar = []
    for ad, anahtar in (("kaldıraç", "kaldirac"), ("açık stop riski", "acik_stop_riski"), ("günlük kayıp", "gunluk_kayip")):
        b = risk[anahtar]
        if b["deger"] is not None and b["deger"] > b["limit"]:
            asimlar.append(f"{ad} {b['deger']:.3f} > {b['limit']:.3f}")
    kill = bool(risk["kill_switch"]["tetiklendi"]) or kill_ev > 0 or sayaclar.get("kill_olayi", 0) > 0
    sorun = (["kill switch tetiklendi"] if kill else []) + asimlar
    k.append(_kalem("sert_limit", "Sert limit ihlali yok", "kill switch tetiklenmedi; anlık kaldıraç/açık stop riski/günlük kayıp limiti aşılmadı",
                    "DURUM.md karar 14, 25 + kullanıcı görevi 2026-11-08", "kaldi" if sorun else "gecti",
                    "; ".join(sorun) if sorun else "ihlal yok",
                    "yalnız anlık değerler ve motorun limit olayları denetlenir; geçmiş an-an aşım kaydı tutulmaz (limitler kodda uygulanır)"))
    # --- bilgi kalemleri
    gl = sum(1 for o in limit_olaylari if o["tur"] == "gunluk_kayip")
    k.append(_kalem("gunluk_limit_olayi", "Günlük kayıp limiti olayı sayısı", "bilgi (kabul kalemi değil)", "tanımsız: kullanıcıya sorulacak",
                    "bilgi", str(max(gl, sayaclar.get("gunluk_limit_olayi", 0)))))
    alarmli = sorted(k_ for k_, kon in (strat_konum or {}).items() if "8" in kon and (kon["8"]["net_getiri"]["alarm"] or kon["8"]["max_dusus"]["alarm"]))
    olcen = [k_ for k_, kon in (strat_konum or {}).items() if "8" in kon]
    k.append(_kalem("strateji_alarmlari", "Strateji bazında 8 hf beklenti alarmı", "bilgi (kabul kalemi değil)", "tanımsız: kullanıcıya sorulacak", "bilgi",
                    f"{len(alarmli)} / {len(olcen)} strateji alarmda" + (": " + ", ".join(alarmli) if alarmli else "") if olcen else None,
                    None if olcen else "8 haftalık pencere henüz dolmadı"))
    sy = (dersler or {}).get("sayim")
    k.append(_kalem("dersler_ozeti", "Dersler: strateji durumları", "bilgi (kabul kalemi değil)", "tanımsız: kullanıcıya sorulacak", "bilgi",
                    (f"içinde {sy['icinde']}, altında {sy['altinda']}, üstünde {sy['ustunde']}, örnek az {sy['ornek_az']}" + (f", ölçülmedi {sy['olculmedi']}" if sy.get("olculmedi") else "")) if sy else None,
                    None if sy else "dersler hesaplanmadı"))
    # --- tanımsız kalemler (eşik uydurulmaz)
    kes = [o for o in olaylar if o.get("tur") in KESINTI_OLAYLARI]
    k.append(_kalem("kesintisiz_calisma", "Kesintisiz çalışma", "TANIMSIZ: kabul edilen kesinti sınırı DURUM.md'de yok", "DURUM.md Aşama 4 (yalnız 'kesintisiz çalışma')",
                    "tanimsiz", f"servis durumu {saglik_durum or '—'}; son 50 olayda {len(kes)} kesinti/veri olayı",
                    "kullanıcıya sorulacak: kesinti sınırı"))
    k.append(_kalem("asgari_islem", "Asgari kapanan işlem sayısı", "TANIMSIZ: DURUM.md'de yok", "—", "tanimsiz", f"{sayaclar.get('kapanan_islem', 0)} kapanan işlem",
                    "kullanıcıya sorulacak: asgari işlem"))
    say = defaultdict(int)
    for x in k:
        say[x["durum"]] += 1
    genel = "kaldi" if say["kaldi"] else ("bekliyor" if say["bekliyor"] else "tamam")
    return {"kalemler": k, "genel_durum": genel, "sayim": {a: say.get(a, 0) for a in ("gecti", "kaldi", "bekliyor", "tanimsiz", "bilgi")},
            "genel_not": "'tamam' kabul kararı değildir: tanımsız kalemler (tanimsiz) kullanıcı kararını bekler." if genel == "tamam" else None,
            "tanimsiz": TANIMSIZ}


def _ay_dusus(gunluk_tam: list, bas: str, bit: str) -> Optional[float]:
    """Ay içi zirveden düşüş (günlük getirilerden; ay başı = 1.0)."""
    ret = [float(x["getiri"]) for x in gunluk_tam if bas <= x["gun"] <= bit and x.get("getiri") is not None]
    if not ret:
        return None
    e, zirve, mx = 1.0, 1.0, 0.0
    for r in ret:
        e *= 1.0 + r
        zirve = max(zirve, e)
        mx = max(mx, (zirve - e) / zirve)
    return mx


def aylik(aylik_kz_ajan: list, gunluk_tam: list, satirlar: list, limit_olaylari: Optional[list], kazanma_olcutu: str = "net") -> list:
    """Her TSİ ayı için özet (aylik_kz_ajan'daki dönemler = son 12 ay). limit_olaylari None: kaynakta ölçülmez."""
    ay_islem = defaultdict(list)
    for s in satirlar:
        ay_islem[ek.ay_anahtari(ek.tsi_gun(s["zaman"]))].append(s)
    ay_limit = defaultdict(lambda: {"gunluk_kayip": 0, "kill_switch": 0})
    for o in (limit_olaylari or []):
        ay_limit[ek.ay_anahtari(ek.tsi_gun(o["zaman"]))][o["tur"]] += 1
    out = []
    for m in aylik_kz_ajan:
        ay = m["donem"]
        ls = ay_islem.get(ay, [])
        gunler = [x for x in gunluk_tam if m["bas_gun"] <= x["gun"] <= m["bit_gun"] and x.get("pnl") is not None]
        iyi = max(gunler, key=lambda x: Decimal(x["pnl"])) if gunler else None
        kotu = min(gunler, key=lambda x: Decimal(x["pnl"])) if gunler else None
        r = [float(s["r"]) for s in ls if s.get("r") is not None]
        kazanan = sum(1 for s in ls if ek._kazandi(s, kazanma_olcutu))
        kat = defaultdict(lambda: Decimal(0))
        eksik = set()
        for s in ls:
            if s.get("set_katki_usd") is None:
                eksik.add(s["kimlik"])
            else:
                kat[s["kimlik"]] += Decimal(s["set_katki_usd"])
        olculen = {k_: v for k_, v in kat.items() if k_ not in eksik}
        notlar = []
        if eksik:
            notlar.append("set katkısı ölçülmeyen strateji(ler) en iyi/en kötü sıralamasına girmedi: " + ", ".join(sorted(eksik)))
        out.append({
            "ay": ay, "bas_gun": m["bas_gun"], "bit_gun": m["bit_gun"], "gun_sayisi": m["gun_sayisi"], "tamamlandi": m["tamamlandi"],
            "getiri": m["toplam"]["getiri"], "pnl": m["toplam"]["pnl"], "max_dusus": d.sayi(_ay_dusus(gunluk_tam, m["bas_gun"], m["bit_gun"])),
            "yesil_gun_orani": d.sayi(sum(1 for x in gunler if Decimal(x["pnl"]) > 0) / len(gunler)) if gunler else None,
            "en_iyi_gun": {"gun": iyi["gun"], "pnl": iyi["pnl"]} if iyi else None, "en_kotu_gun": {"gun": kotu["gun"], "pnl": kotu["pnl"]} if kotu else None,
            "islem_sayisi": len(ls), "kazanan": kazanan, "kazanma_orani": d.sayi(kazanan / len(ls)) if ls else None,
            "ort_r": d.sayi(sum(r) / len(r)) if r else None,
            "en_iyi_strateji": ({"kimlik": (b := max(olculen, key=olculen.get)), "katki": d.para(olculen[b])} if olculen else None),
            "en_kotu_strateji": ({"kimlik": (w := min(olculen, key=olculen.get)), "katki": d.para(olculen[w])} if olculen else None),
            "ajanlar": m["ajanlar"], "limit_olaylari": ({"gunluk_kayip": ay_limit[ay]["gunluk_kayip"], "kill_switch": ay_limit[ay]["kill_switch"]}
                                                       if limit_olaylari is not None else None),
            "notlar": notlar})
    return out


def olustur(*, kaynak: str, zaman: str, simdi, donem_bas, aylik_kz_ajan: list, gunluk_tam: list, satirlar: list, risk: dict, sayaclar: dict,
            set_konum: dict, strat_konum: dict, dersler: dict, saglik_durum: Optional[str], olaylar: Optional[list],
            limit_olaylari: Optional[list], kazanma_olcutu: str = "net", gun_kesimi: str = ek.GUN_KESIMI_TSI) -> dict:
    """-> aylik_rapor.json. Backtest kaynağında kabul listesi hesaplanmaz (null + neden): paper kabulü canlı sürece aittir."""
    if kaynak == "backtest":
        kabul, kneden = None, "backtest kaynağında paper kabul listesi hesaplanmaz (süre, servis ve limit olayları paper'a özgüdür)"
    else:
        kabul, kneden = kabul_listesi(simdi=simdi, donem_bas=donem_bas, risk=risk, sayaclar=sayaclar, set_konum=set_konum, strat_konum=strat_konum,
                                      dersler=dersler, saglik_durum=saglik_durum, olaylar=olaylar or [], limit_olaylari=limit_olaylari or []), None
    return {**d._zarf("aylik_rapor", kaynak, zaman), "gun_kesimi": gun_kesimi,
            "aylar": aylik(aylik_kz_ajan, gunluk_tam, satirlar, limit_olaylari, kazanma_olcutu),
            "aylar_not": "Ay = TSİ takvim ayı (son 12). Getiri/K-Z ozet.aylik_kz_ajan ile aynı sayıdır; işlem ve strateji sıralaması yalnız kapanan işlemlerden "
                         "(açık pozisyonun anlık K/Z'si dahil değildir). Aya özgü beklenti aralığı yoktur (aralıklar 4/8 hafta penceresidir)."
                         + ("" if gun_kesimi == ek.GUN_KESIMI_TSI else " Gün/ay sınırı UTC araştırma ızgarasıdır (TSİ değil); işlemler TSİ ayına yazıldığı için ay kenarlarında birkaç saatlik kayma olabilir."),
            "kabul_listesi": kabul, "kabul_listesi_neden": kneden}
