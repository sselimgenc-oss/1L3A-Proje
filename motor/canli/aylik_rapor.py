"""Aylık rapor + paper kabul kontrol listesi (pano öncelik 3). Hesap BURADA (motor tarafı); pano yalnız biçimler.

Ay = TSİ takvim ayı (Europe/Istanbul, gün kesimi `durum_ek`); işlem ayı çıkış zamanının TSİ günündendir. Aylık özet yalnız kapanmış
işlemler ve günlük özsermaye serisinden gelir (lookahead yok). Dönem getirisi/K-Z `ozet.aylik_kz_ajan` ile AYNI sayıdır (aynı kaynak).

KABUL KONTROL LİSTESİ ölçütleri (eski panonunkiler — %10 DD, PSR>%95, 30 işlem, 60 gün — KULLANILMAZ). Her kalemin `kaynak` alanı dayanağı gösterir:
  sure         DURUM.md Aşama 4 "Süre ≥ 8 hafta" + lider günlüğü 2026-11-07 (başlangıç + 56 gün). KULLANICI KARARI 2026-11-08: toplam kesinti 24 saati
               aşarsa kabul reddedilmez, en erken değerlendirme aşan kesinti kadar ileri kayar (`en_erken_degerlendirme`).
  set_beklenti DURUM.md Aşama 4 "Bitiş: ... sonuçların beklenti aralığında olması"; set 8 hafta net getiri/düşüş alarm eşiği
               (sonuclar/final/OZET.md "Alarm eşiği (set, 8 hafta)"; stratejiler.json set.beklenti alarm).
  sert_limit   DURUM.md karar 14 + 25. KULLANICI KARARI 2026-11-08: kill switch ve kaldıraç / açık stop riski tavanı aşımı ihlaldir; günlük %3 kayıp
               limitinin TETİKLENMESİ ihlal sayılmaz (bilgi kalemi `gunluk_limit_olayi` sayıyı gösterir). Denetim O14 (2026-11-08): ihlal MOTORUN uyguladığı
               tanımla ölçülür = motorun kayıtlı olayları (kill_switch; dolum anı aşım olayları DOLUM_ASIM_OLAYLARI). Red/kırpma limitin çalıştığını gösterir
               (bilgi). Anlık (MTM) kaldıraç / stop riski aşımı ayrı UYARI kalemidir (`sert_limit_anlik`, durum "bilgi", kabulü bozmaz).
  asgari_islem KULLANICI KARARI 2026-11-08: set toplamında ≥ 30 kapanan işlem. Geçti/kaldı verir; birikimli olduğu için süre dolmadan "bekliyor", süre dolunca
               30'un altı "kaldı".
  kesinti      Bilgi kalemi (geçti/kaldı vermez): ölçüm `kesinti_olc` ile olay kayıtlarından; ölçülemezse null + neden (uydurma yok). Etkisi yalnız `sure`'dedir.
  Bilgi kalemleri (geçti/kaldı vermez): kesinti, günlük limit olayı sayısı, strateji bazlı beklenti alarmı, dersler durum sayımı.
`stratejiler` (kabul listesi): strateji başına `canliya_uygun` + `neden`. KULLANICI KARARI 2026-11-08: Dersler'de "altında" kabulü bozmaz ama strateji canlıya
geçmez; "örnek az" da canlıya uygun sayılmaz (ayrı neden). Yalnız "içinde" ve "üstünde" uygundur.
`genel_durum`: "kaldi" (bir kalem kaldı) | "bekliyor" (kaldı yok, bir kalem bekliyor) | "tamam" (tanımlı kalemlerin hepsi geçti). "tamam" kabul KARARI değildir:
son söz kullanıcınındır; açık kalan tek soru `tanimsiz` listesindedir.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd

from motor.canli import dersler as ders
from motor.canli import durum as d
from motor.canli import durum_ek as ek

PAPER_MIN_GUN = 56                      # 8 hafta (DURUM.md Aşama 4)
EN_ERKEN_DEGERLENDIRME = "2027-01-02"   # DURUM.md lider günlüğü 2026-11-07 (kesinti yokken; gerçeği kabul listesindeki `en_erken_degerlendirme`)
ASGARI_ISLEM = 30                       # kullanıcı kararı 2026-11-08: set toplamında kapanan işlem
KESINTI_LIMIT_SAAT = 24.0               # kullanıcı kararı 2026-11-08: aşan kısım değerlendirme süresini uzatır
OLAY_KAPASITE = 200                     # Paper.olay_ekle en çok 200 olay tutar; dolduysa eski olaylar silinmiş olabilir
# veri_yok burada YOK: strateji verisinin baştan olmaması çalışma kesintisi değildir.
# Dolum anında sert tavan aşımı (motor bunu engeller; olay yazarsa ihlaldir). Şu an paper motoru bu türleri ÜRETMİYOR (dolumda engelliyor);
# kayıtlı olmadıkça ihlal 'kill_switch'ten ibarettir. Tür adları sözleşmede (DURUM_SOZLESMESI.md, aylik_rapor) belgelidir.
DOLUM_ASIM_OLAYLARI = {"dolum_kaldirac_asimi": "dolum anında kaldıraç tavanı aşıldı", "dolum_stop_riski_asimi": "dolum anında toplam stop riski tavanı aşıldı"}
KESINTI_OLAYLARI = ("veri_bosluk", "ws_koptu", "yeniden_baslatma", "binance_hata")
TANIMSIZ = [
    {"ad": "strateji_alarmi_kabulu", "soru": "'Sonuçların beklenti aralığında olması' yalnız set için mi, her strateji için mi aranır? (şimdi: set kabul kalemi, "
                                              "strateji bazı bilgi; 'altında' ders durumu kabulü bozmaz ama stratejiyi canlıdan eler: kullanıcı kararı 2026-11-08)"},
]
_BOSLUK_RE = re.compile(r"\(([^()]+?) -> ([^()]+?)\)")
_EKSIK_RE = re.compile(r"(\d+) mum eksik")
_WS_SN_RE = re.compile(r"WS (\d+(?:\.\d+)?) sn mesaj vermedi")


def kesinti_olc(olaylar: list, olay_kapasite: int = OLAY_KAPASITE) -> dict:
    """Motorun mevcut olay kayıtlarından (paper_state.json olaylar: {zaman, tur, mesaj}) toplam kesinti süresi.

    Süresi kayıttan okunabilenler: `veri_bosluk` ve `yeniden_baslatma` mesajındaki "(A -> B)" aralığı (veri_bosluk'ta A ve B mum AÇILIŞLARIDIR:
    "N mum eksik" ile mum süresi (B-A)/(N+1) bulunur ve kesinti [A + mum süresi, B) = N mum süresi sayılır) (yeniden başlatmada A = motorun SON KALP ATIŞI,
    B = başlangıç; kalp_atisi.py — kalp atışından önceki eski olaylarda aralık yoktur, ölçülemeyen sayılır); `ws_koptu` mesajındaki "WS N sn mesaj vermedi" ([zaman-N sn, zaman]).
    Çakışan aralıklar birleştirilir (aynı süre iki kez sayılmaz). Süresi kayıtta olmayan kesinti olayları (aralıksız yeniden_baslatma, binance_hata, aralıksız veri_bosluk,
    'WS koptu') veya dolu olay kaydı (eski olaylar silinmiş olabilir) varsa toplam ÖLÇÜLEMEZ: `saat` None, `neden` yazılı, `alt_sinir_saat` yalnız ölçülen kısımdır.
    -> {saat, alt_sinir_saat, olculen_olay, olculemeyen_olay, neden}."""
    araliklar, olculemeyen = [], 0
    for o in olaylar or []:
        tur_, msg = o.get("tur"), o.get("mesaj") or ""
        if tur_ not in KESINTI_OLAYLARI:
            continue
        aralik = None
        try:
            if tur_ in ("veri_bosluk", "yeniden_baslatma") and (mm := _BOSLUK_RE.search(msg)):
                a_, b_ = (ek._utc(pd.Timestamp(mm.group(i))) for i in (1, 2))
                if tur_ == "veri_bosluk" and (me := _EKSIK_RE.search(msg)):
                    # "(A -> B)" mum AÇILIŞLARIDIR (son bilinen mum -> ilk yeni mum); A mumu kendi süresi boyunca veri taşır.
                    # Gerçek boşluk [A + mum süresi, B) = eksik x mum süresi; mum süresi = (B - A) / (eksik + 1).
                    a_ = a_ + (b_ - a_) / (int(me.group(1)) + 1)
                aralik = (a_, b_)
            elif tur_ == "ws_koptu" and (mm := _WS_SN_RE.search(msg)):
                bit = ek._utc(pd.Timestamp(o["zaman"]))
                aralik = (bit - timedelta(seconds=float(mm.group(1))), bit)
        except (ValueError, TypeError, KeyError):
            aralik = None
        if aralik is None or aralik[1] < aralik[0]:
            olculemeyen += 1
        else:
            araliklar.append(aralik)
    araliklar.sort()
    toplam, cur_a, cur_b = timedelta(0), None, None
    for a_, b_ in araliklar:
        if cur_b is None or a_ > cur_b:
            if cur_b is not None:
                toplam += cur_b - cur_a
            cur_a, cur_b = a_, b_
        else:
            cur_b = max(cur_b, b_)
    if cur_b is not None:
        toplam += cur_b - cur_a
    alt = toplam.total_seconds() / 3600.0
    nedenler = []
    if olculemeyen:
        nedenler.append(f"{olculemeyen} kesinti olayının süresi kayıtta yok (yeniden başlatma / Binance hatası / aralıksız boşluk / bağlantı kopması)")
    if len(olaylar or []) >= olay_kapasite:
        nedenler.append(f"olay kaydı dolu ({olay_kapasite}): eski olaylar silinmiş olabilir")
    return {"saat": None if nedenler else alt, "alt_sinir_saat": alt, "olculen_olay": len(araliklar), "olculemeyen_olay": olculemeyen,
            "neden": "; ".join(nedenler) if nedenler else None}


def canliya_uygunluk(dersler: Optional[dict]) -> list:
    """Dersler durumundan strateji başına canlıya uygunluk (kullanıcı kararı 2026-11-08). İçinde/üstünde: uygun; altında: değil; örnek az: değil (ayrı neden)."""
    out = []
    for x in (dersler or {}).get("stratejiler", []):
        dur = x.get("durum")
        if dur in ("icinde", "ustunde"):
            uygun, neden = True, f"Dersler: {ders.DURUM_ETIKET[dur]}"
        elif dur == "altinda":
            uygun, neden = False, "Dersler: beklentinin altında"
        elif dur == "ornek_az":
            uygun, neden = False, f"örnek az ({x.get('islem')} işlem < {ders.MIN_ISLEM_DERS})"
        else:
            uygun, neden = False, "ölçülmedi: " + (x.get("durum_neden") or "Dersler durumu yok")
        out.append({"kimlik": x["kimlik"], "dersler_durumu": dur, "canliya_uygun": uygun, "neden": neden})
    return out


def _kalem(id_: str, ad: str, olcut: str, kaynak: str, durum: str, deger: Optional[str], neden: Optional[str] = None) -> dict:
    return {"id": id_, "ad": ad, "olcut": olcut, "kaynak": kaynak, "durum": durum, "deger": deger, "neden": neden}


def kabul_listesi(*, simdi, donem_bas, risk: dict, sayaclar: dict, set_konum: dict, strat_konum: dict, dersler: dict,
                  saglik_durum: Optional[str], olaylar: list, limit_olaylari: list) -> dict:
    """Paper kabul kontrol listesi (anlık durum, birikimli). -> {'kalemler': [...], 'genel_durum', 'sayim', 'tanimsiz'}."""
    k = []
    # --- kesinti (kullanıcı kararı 2026-11-08: > 24 saat reddetmez, değerlendirme süresini uzatır)
    kes = kesinti_olc(olaylar)
    bilinen = kes["saat"] if kes["saat"] is not None else kes["alt_sinir_saat"]      # ölçülen kısım kesin; ölçülemeyen kısım için tahmin YOK
    uzama = max(0.0, bilinen - KESINTI_LIMIT_SAAT)
    # --- süre
    en_erken = None
    if donem_bas is None:
        k.append(_kalem("sure", "Paper süresi ≥ 8 hafta", f"≥ {PAPER_MIN_GUN} gün", "DURUM.md Aşama 4 + lider günlüğü 2026-11-07", "bekliyor", None, "başlangıç günü yok"))
    else:
        bas, su = ek._utc(donem_bas), ek._utc(simdi)
        gun = (su - bas).days
        hedef = bas + timedelta(days=PAPER_MIN_GUN) + timedelta(hours=uzama)
        en_erken = str(hedef.date())
        neden = f"başlangıç + {PAPER_MIN_GUN} gün = {str((bas + timedelta(days=PAPER_MIN_GUN)).date())}"
        if uzama > 0:
            neden += (f" + 24 saati aşan kesinti {uzama:.1f} sa" + (" (ölçülen alt sınır)" if kes["saat"] is None else "") + f" = {en_erken}")
        k.append(_kalem("sure", "Paper süresi ≥ 8 hafta", f"≥ {PAPER_MIN_GUN} gün + 24 saati aşan kesinti (en erken değerlendirme {en_erken})",
                        "DURUM.md Aşama 4 (Süre ≥ 8 hafta) + lider günlüğü 2026-11-07 + kullanıcı kararı 2026-11-08 (kesinti uzatır)",
                        "gecti" if su >= hedef else "bekliyor", f"{gun} / {PAPER_MIN_GUN} gün", neden))
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
    # --- sert limit (O14): ihlal MOTORUN UYGULADIĞI tanımla, motorun kayıtlı olaylarından ölçülür (anlık MTM değil)
    kill_ev = sum(1 for o in limit_olaylari if o["tur"] == "kill_switch")
    dolum_ev = defaultdict(int)
    for o in limit_olaylari:
        if o["tur"] in DOLUM_ASIM_OLAYLARI:
            dolum_ev[o["tur"]] += 1
    kill = bool(risk["kill_switch"]["tetiklendi"]) or kill_ev > 0 or sayaclar.get("kill_olayi", 0) > 0
    sorun = (["kill switch tetiklendi"] if kill else []) + [f"{DOLUM_ASIM_OLAYLARI[t]} ({n} olay)" for t, n in sorted(dolum_ev.items())]
    red, kirp = sayaclar.get("reddedilen_giris"), sayaclar.get("kirpilan_giris")
    uygulama = ("motor tavanı uyguladı: " + ", ".join(x for x in ((f"{red} giriş reddedildi" if red else ""), (f"{kirp} giriş kırpıldı" if kirp else "")) if x)
                + " (red/kırpma limitin ÇALIŞTIĞINI gösterir, ihlal değildir)") if (red or kirp) else None
    k.append(_kalem("sert_limit", "Sert limit ihlali yok",
                    "kill switch tetiklenmedi; dolum anında kaldıraç/toplam stop riski tavanı aşılmadı (motor olay kaydı). Günlük %3 kayıp limitinin tetiklenmesi ihlal değil",
                    "DURUM.md karar 14, 25 + kullanıcı kararı 2026-11-08; tanım: motorun dolum anında uyguladığı limit (portfoy/motor.py, paper_motor.py)",
                    "kaldi" if sorun else "gecti", "; ".join(sorun) if sorun else "ihlal yok",
                    "; ".join(x for x in (uygulama, "ölçüm: motorun kill switch ve dolum anı aşım olayları (limit_olaylari); anlık (MTM) değerler ayrı uyarı kalemindedir") if x)))
    # --- anlık (MTM) aşım: UYARI, kabulü bozmaz (motor limitleri dolum anında uygular; kapanışta kaldıraç bir bar tavanı aşabilir, açık kârdaki pozisyonun
    #     stopa kadar riski %5'i geçebilir — bunlar kural ihlali değildir)
    asimlar = []
    for ad, anahtar in (("kaldıraç", "kaldirac"), ("açık stop riski", "acik_stop_riski")):
        b = risk[anahtar]
        if b["deger"] is not None and b["deger"] > b["limit"]:
            asimlar.append(f"{ad} {b['deger']:.3f} > {b['limit']:.3f}")
    k.append(_kalem("sert_limit_anlik", "Uyarı: anlık (MTM) kaldıraç / açık stop riski limit üstünde", "bilgi (kabulü bozmaz): son fiyatlarla anlık değer ≤ limit",
                    "denetim O14 (2026-11-08): motor limiti dolum anında uygular; anlık aşım fiyat hareketinden doğabilir", "bilgi",
                    "uyarı: " + "; ".join(asimlar) if asimlar else "limit altında",
                    "anlık değer: kapanışta kaldıraç bir bar tavanı aşabilir (ertesi açılışta kaldirac_azalt), kârdaki pozisyonun stopa kadar riski açık kârı da kapsar"
                    if asimlar else None))
    # --- bilgi kalemleri
    gl = sum(1 for o in limit_olaylari if o["tur"] == "gunluk_kayip")
    k.append(_kalem("gunluk_limit_olayi", "Günlük kayıp limiti olayı sayısı", "bilgi (ihlal sayılmaz)", "kullanıcı kararı 2026-11-08: günlük limit tetiklenmesi ihlal değil",
                    "bilgi", str(max(gl, sayaclar.get("gunluk_limit_olayi", 0)))))
    alarmli = sorted(k_ for k_, kon in (strat_konum or {}).items() if "8" in kon and (kon["8"]["net_getiri"]["alarm"] or kon["8"]["max_dusus"]["alarm"]))
    olcen = [k_ for k_, kon in (strat_konum or {}).items() if "8" in kon]
    k.append(_kalem("strateji_alarmlari", "Strateji bazında 8 hf beklenti alarmı", "bilgi (kabul kalemi değil)", "tanımsız: kullanıcıya sorulacak", "bilgi",
                    f"{len(alarmli)} / {len(olcen)} strateji alarmda" + (": " + ", ".join(alarmli) if alarmli else "") if olcen else None,
                    None if olcen else "8 haftalık pencere henüz dolmadı"))
    sy = (dersler or {}).get("sayim")
    k.append(_kalem("dersler_ozeti", "Dersler: strateji durumları", "bilgi (kabul kalemi değil)", "kullanıcı kararı 2026-11-08: altında = kabulü bozmaz, strateji canlıya geçmez", "bilgi",
                    (f"içinde {sy['icinde']}, altında {sy['altinda']}, üstünde {sy['ustunde']}, örnek az {sy['ornek_az']}" + (f", ölçülmedi {sy['olculmedi']}" if sy.get("olculmedi") else "")) if sy else None,
                    None if sy else "dersler hesaplanmadı"))
    # --- kesinti (bilgi) ve asgari işlem (geçti/kaldı)
    if kes["saat"] is not None:
        kdeger, kneden = f"toplam {kes['saat']:.1f} saat ({kes['olculen_olay']} aralık; sınır {KESINTI_LIMIT_SAAT:.0f} saat)", None
    else:
        kdeger, kneden = None, "ölçülemedi: " + kes["neden"] + f"; ölçülebilen kısım {kes['alt_sinir_saat']:.1f} saat (alt sınır). Servis durumu {saglik_durum or '—'}."
    k.append(_kalem("kesinti_suresi", "Toplam kesinti süresi", f"bilgi: {KESINTI_LIMIT_SAAT:.0f} saati aşan kısım değerlendirme süresini uzatır (reddetmez)",
                    "kullanıcı kararı 2026-11-08; ölçüm: paper_state olay kayıtları (veri_bosluk aralığı, ws_koptu süresi)", "bilgi", kdeger, kneden))
    kapanan = sayaclar.get("kapanan_islem", 0)
    sure_gecti = k[0]["durum"] == "gecti"
    ai_durum = "gecti" if kapanan >= ASGARI_ISLEM else ("kaldi" if sure_gecti else "bekliyor")
    k.append(_kalem("asgari_islem", "Asgari kapanan işlem (set toplamı)", f"≥ {ASGARI_ISLEM} kapanan işlem", "kullanıcı kararı 2026-11-08", ai_durum,
                    f"{kapanan} / {ASGARI_ISLEM} kapanan işlem",
                    None if ai_durum == "gecti" else ("süre dolunca hâlâ eksikse kaldı" if ai_durum == "bekliyor" else "süre doldu, işlem sayısı yetersiz")))
    say = defaultdict(int)
    for x in k:
        say[x["durum"]] += 1
    genel = "kaldi" if say["kaldi"] else ("bekliyor" if say["bekliyor"] else "tamam")
    return {"kalemler": k, "genel_durum": genel, "sayim": {a: say.get(a, 0) for a in ("gecti", "kaldi", "bekliyor", "tanimsiz", "bilgi")},
            "genel_not": "'tamam' tanımlı kalemlerin hepsinin geçtiği demektir; kabul kararı kullanıcınındır (açık soru: tanimsiz listesi)." if genel == "tamam" else None,
            "en_erken_degerlendirme": en_erken, "kesinti": {**kes, "limit_saat": KESINTI_LIMIT_SAAT, "uzama_saat": uzama},
            "stratejiler": canliya_uygunluk(dersler), "tanimsiz": TANIMSIZ}


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
