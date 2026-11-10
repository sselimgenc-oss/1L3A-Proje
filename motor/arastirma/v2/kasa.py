"""v2 ortak: tek kasa yeniden oynatma + günlük MTM getirisi (ON_KAYIT_V2 3, 5.5, 6.2).

Tek kasa oynatması v1 `secim.yeniden_oyna` ile yapılır (sıra = giriş zamanı, eşitlikte strateji sırası, sonra evren sırası).
Günlük MTM özsermaye (gün sonu, UTC): 1 + Σ_kabul [ açık işlem: rk · kum_r(gün) ; kapanmış işlem: gerçekleşen K/Z ].
rk = işlemin oynatmadaki fiyat-riski tutarı (K/Z / R); `kum_r` ham aşamadaki günlük MTM yolu (mtm/x1). Zorla kapanan
(kill / günlük limit) işlemde yol kapanış gününe kadar kullanılır, sonra gerçekleşen K/Z. R tam 0 olan işlemin ara günleri
0 sayılır (rk bilinemez; K/Z zaten 0).

Gelişme aşamaları yazma engeli: set mührü varsa test/saglamlik/set aşamaları çalışmaz (6.3).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, secim
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import eleme, ham as hm, sabit


class MuhurEngeli(RuntimeError):
    """Set mühürlendi: geliştirme aşamaları artık yazamaz."""


def yazma_engeli(cikti: Path) -> None:
    if (Path(cikti) / sabit.SET_MUHRU).exists():
        raise MuhurEngeli(f"{sabit.SET_MUHRU} var: set mühürlendi, geliştirme aşamaları yazamaz (6.3)")


def sha256(yol) -> str:
    import hashlib
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def atomik_yaz_json(yol: Path, veri) -> None:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    g = yol.with_suffix(".jtmp")
    g.write_text(json.dumps(veri, ensure_ascii=False, default=str, sort_keys=True))
    g.replace(yol)


def atomik_yaz_parquet(df: pd.DataFrame, yol: Path) -> None:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    g = yol.with_suffix(".tmp")
    df.to_parquet(g, index=False)
    g.replace(yol)


# ============================================================================ devam önbelleği: girdi damgası (B16b)
DAMGA_ANAHTARI = "girdi_damgasi"
SATIR_BITTI = ("tamam", "hata", "rnd_desteklenmeyen")


def asama_kodu_ozeti(modul: str) -> str:
    """Aşama modülünün (test.py / saglamlik.py / kasa.py) import kapanışının içerik özeti: aşama kodu değişince önbellek bayatlar."""
    from motor.arastirma import wf_evren_holdout as v1h
    from motor.arastirma.v2 import kapsam
    return hm._sha_json({y: v1h._sha(we.KOK / y) for y in kapsam.kapanis([modul])})


def girdi_damgasi(cikti: Path, row: dict, carpanlar: tuple, asama_modulu: str) -> str:
    """Bir satırın önbellekli sonucunun GİRDİ kimliği. İçerik: (1) satırın ham yan dosyalarının damgaları (her çarpan x sembol:
    strateji_hash, motor_hash, veri_sha256, git_commit, maliyet_hash, hata/veri_yok/n_islem), (2) ŞİMDİKİ kod damgası (strateji_hash,
    motor_hash), (3) ŞİMDİKİ verinin özeti (sembol başına), (4) aşama kodu. Herhangi biri değişirse damga değişir => önbellek bayat.
    Ham yan dosya yoksa damgada None (ham_yukle sonra 'ham koşu bitmemiş' ile satırı erteler). HoldoutSizintisi yukarı çıkar."""
    ad, tf, evren, stil = row["strateji"], row["tf"], row["evren"], row["stil_v2"]
    pf = stil == "portfoy"
    semboller = (hm.PF_SEMBOL,) if pf else sabit.evren_listesi(evren)
    tfx = "1d" if pf else tf
    yanlar = {}
    for c in carpanlar:
        hd = Path(cikti) / "ham" / hm.carpan_adi(c)
        for sm in semboller:
            yan = hm.dosya_yolu(hd, ad, tfx, sm).with_suffix(".json")
            if not yan.exists():                          # eksik ham: damgada "yok"; asıl hatayı (bitmemiş) ham_yukle verir
                yanlar[f"{hm.carpan_adi(c)}/{sm}"] = None
                continue
            m = json.loads(yan.read_text())
            yanlar[f"{hm.carpan_adi(c)}/{sm}"] = {a: m.get(a) for a in (*hm.DAMGA_ALANLARI, "maliyet_hash", "hata", "veri_yok", "n_islem")}
    kod = hm.kimlik_damgasi(ad, stil)
    veri = (hm.pf_veri_ozeti_simdi(hm.pf_veri_oku, evren) if pf else
            {sm: hm.veri_ozeti_simdi(hm.veri_oku, sm, tf) for sm in semboller})
    return hm._sha_json({"yan": yanlar, "kod": {k: kod[k] for k in ("strateji_hash", "motor_hash")}, "veri": veri,
                         "asama": [asama_modulu, asama_kodu_ozeti(asama_modulu)]})


def onbellek_gecerli_mi(kayit: dict, damga: str, bitti_durumlari: tuple, eski_kabul=None) -> bool:
    """Önbellekteki satır kaydı bu damgayla üretilmiş mi? True = geçerli (atla); False = bayat/yarım (yeniden koş).
    Damga alanı yok: bitmiş kayıt (tarihsel/mühürlü çıktı) yalnız eski_kabul / V2_ESKI_YAN_DOSYA ile geçerli sayılır, yoksa
    DamgaUyusmazligi (sessizce atlanmaz, üzerine de yazılmaz); bitmemiş damgasız kayıt yarımdır -> False."""
    if DAMGA_ANAHTARI in kayit:
        return kayit[DAMGA_ANAHTARI] == damga
    if kayit.get("durum") in bitti_durumlari:
        if hm.eski_kabul_mu(eski_kabul):
            return True
        raise hm.DamgaUyusmazligi(f"{kayit.get('strateji')} {kayit.get('tf')}: önbellek satırında girdi damgası yok (eski çıktı). "
                                  f"Tarihsel kayıt olarak okumak için {hm.ESKI_ORTAM}=1 / --eski-yan-dosya verin")
    return False


def satir_bitti_mi(cikti: Path, yol: Path, row: dict, carpanlar: tuple, asama_modulu: str, bitti_durumlari: tuple, eski_kabul=None) -> bool:
    """Planlama kararı: satır dosyası var, bitmiş VE damgası şimdiki girdiyle uyumlu. Ham yan dosya yoksa damga uyuşmaz -> False (görev kuyruğa girer, worker erteler)."""
    if not Path(yol).exists():
        return False
    kayit = json.loads(Path(yol).read_text())
    if DAMGA_ANAHTARI not in kayit:
        return onbellek_gecerli_mi(kayit, "", bitti_durumlari, eski_kabul) and kayit.get("durum") in bitti_durumlari
    damga = girdi_damgasi(cikti, row, carpanlar, asama_modulu)
    return onbellek_gecerli_mi(kayit, damga, bitti_durumlari, eski_kabul) and kayit.get("durum") in bitti_durumlari


def temizle(*yollar) -> None:
    """Bayat önbellek parçalarını (kısmi sonuç dizin/dosyaları) siler: eski p-değerleri yeni girdiyle birleşmesin."""
    for y in yollar:
        y = Path(y)
        if y.is_dir():
            shutil.rmtree(y)
        elif y.exists():
            y.unlink()


# ============================================================================ tablo kurma
def donem_sinirlari(bilgi: dict) -> tuple:
    """(analiz_bas, oos_bit): eleme.tek_metrikler ile AYNI kural."""
    return we.analiz_bas_hesapla(bilgi["veri_bas"]), max(bilgi["veri_bit"].values()) + pd.Timedelta(1, "ns")


def oos_birlestir(ham_strateji: dict, sembol_sirasi: dict, analiz_bas, carpan: float, tablo_yolu) -> pd.DataFrame:
    """ham_strateji: {strateji_adi: {sembol: ham df}} (sıra = sözlük sırası). Analiz başlangıcından önce girilenler atılır.
    Çıktı: strateji, sembol, islem_no (ham satır konumu), giris_zamani, cikis_zamani, yon, r, sf, stop_mesafe, maliyet_payi;
    sıralı: (giriş, strateji sırası, evren sırası)."""
    parcalar = []
    for sk, (ad, ham) in enumerate(ham_strateji.items()):
        sira = sembol_sirasi[ad]
        ordn = {s: i for i, s in enumerate(sira)}
        for s in sira:
            df = ham.get(s)
            if df is None or not len(df):
                continue
            d = df.reset_index(drop=True).copy()
            d["islem_no"] = np.arange(len(d), dtype=np.int64)
            d = d[pd.DatetimeIndex(d["giris_zamani"]) >= analiz_bas].copy()
            if not len(d):
                continue
            d["strateji"], d["sembol"], d["_sk"], d["_ek"] = ad, s, sk, ordn[s]
            parcalar.append(d)
    if not parcalar:
        return pd.DataFrame()
    oos = pd.concat(parcalar, ignore_index=True)
    oos["maliyet_payi"] = eleme.maliyet_payi_v2(oos, carpan, tablo_yolu)
    oos["_g"] = pd.DatetimeIndex(oos["giris_zamani"]).as_unit("ns").asi8
    oos = oos.sort_values(["_g", "_sk", "_ek"], kind="stable").drop(columns=["_g"]).reset_index(drop=True)
    return oos


def oynatma_tablosu(oos: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"kol": oos["strateji"].to_numpy() + "|" + oos["sembol"].to_numpy(), "sembol": oos["sembol"].to_numpy(),
                         "yon": oos["yon"].to_numpy(), "giris": pd.DatetimeIndex(oos["giris_zamani"]),
                         "cikis": pd.DatetimeIndex(oos["cikis_zamani"]), "r": oos["r"].to_numpy(dtype=float),
                         "sf": oos["sf"].to_numpy(dtype=float), "stop_mesafe": oos["stop_mesafe"].to_numpy(dtype=float),
                         "maliyet_payi": oos["maliyet_payi"].to_numpy(dtype=float)})


def oynat(oos: pd.DataFrame, bas, bit, ayar=None) -> tuple:
    """-> (tablo, secim.yeniden_oyna sonucu). bit = max(bit, son çıkış)."""
    tablo = oynatma_tablosu(oos)
    bit = max(pd.Timestamp(bit), pd.DatetimeIndex(tablo["cikis"]).max())
    return tablo, secim.yeniden_oyna(tablo, ayar or we.SINIRLAR, bas=bas, bit=bit)


# ============================================================================ günlük MTM
class MtmOnbellek:
    """(strateji, sembol) -> {islem_no: (gun_ns dizisi, kum_r dizisi)}; mtm/x1 dosyalarından."""

    def __init__(self, cikti: Path, tf_of: dict, carpan: float = 1.0):
        self.cikti, self.tf_of, self.carpan, self._d = Path(cikti), tf_of, carpan, {}

    def al(self, strateji: str, sembol: str):
        k = (strateji, sembol)
        if k not in self._d:
            d = hm.mtm_yukle(self.cikti, self.carpan, strateji, self.tf_of[strateji], sembol).sort_values(
                ["islem_no", "gun"], kind="stable")
            no = d["islem_no"].to_numpy()
            gun = pd.DatetimeIndex(d["gun"]).as_unit("ns").asi8
            kum = d["kum_r"].to_numpy(dtype=float)
            bas = np.flatnonzero(np.r_[True, no[1:] != no[:-1]]) if len(no) else np.array([], dtype=int)
            bit = np.r_[bas[1:], len(no)] if len(no) else np.array([], dtype=int)
            self._d[k] = {int(no[b]): (gun[b:e], kum[b:e]) for b, e in zip(bas, bit)}
        return self._d[k]


def gunluk_mtm_getiri(oos: pd.DataFrame, tablo: pd.DataFrame, res: dict, mtm: MtmOnbellek, bas, bit) -> pd.Series:
    """Kabul edilen işlemlerin günlük MTM özsermaye getirisi (UTC gün indeksli)."""
    gun_ns = pd.Timedelta(1, "D").value
    g0 = pd.Timestamp(bas).tz_convert("UTC").floor("D")
    g1 = pd.Timestamp(bit).tz_convert("UTC").floor("D")
    gunler = pd.date_range(g0, g1, freq="D", tz="UTC")
    n = len(gunler)
    a = np.zeros(n)
    delta = np.zeros(n + 1)
    t0 = g0.as_unit("ns").value
    gi = pd.DatetimeIndex(tablo["giris"]).as_unit("ns").asi8
    ci = pd.DatetimeIndex(tablo["cikis"]).as_unit("ns").asi8
    r = tablo["r"].to_numpy(dtype=float)
    for i in res["kabul"]:
        if i not in res["islem_pnl"]:
            continue
        t, pnl = res["islem_pnl"][i]
        d = ci[i] - gi[i]
        f = 1.0 if d <= 0 else min(max((t - gi[i]) / d, 0.0), 1.0)
        gercek_gun = int((t - t0) // gun_ns)
        gercek_gun = min(max(gercek_gun, 0), n - 1)
        rk = pnl / (r[i] * f) if abs(r[i] * f) > sabit.EPS else 0.0
        yol = mtm.al(oos["strateji"].iat[i], oos["sembol"].iat[i]).get(int(oos["islem_no"].iat[i]))
        if yol is not None and rk != 0.0:
            gn = ((yol[0] - t0) // gun_ns).astype(np.int64)
            m = (gn >= 0) & (gn < min(gercek_gun, n))
            a[gn[m]] += rk * yol[1][m]
        delta[gercek_gun] += pnl
    ozs = 1.0 + a + np.cumsum(delta)[:n]
    onceki = np.r_[1.0, ozs[:-1]]
    return pd.Series(ozs / onceki - 1.0, index=gunler)


def haftalik(getiri: pd.Series) -> pd.Series:
    """Pazar kapanışlı (UTC) haftalık bileşik getiri."""
    return (1.0 + getiri).resample(sabit.HAFTA_FREKANS).prod() - 1.0


# ============================================================================ satır düzeyinde oynatma
def satir_oynat(cikti: Path, row: dict, tablo_yolu, tablo_hash: str, carpan: float = 1.0) -> dict:
    """Havuz satırının (tek-grafik) ham sonuçlarından tek kasa oynatması. -> {oos, tablo, res, analiz_bas, oos_bit, bilgi}.
    Ham koşu bitmemişse RuntimeError('ham koşu bitmemiş')."""
    ad, tf, evren = row["strateji"], row["tf"], row["evren"]
    evren_t = sabit.evren_listesi(evren)
    ham, bilgi = hm.ham_yukle(cikti, carpan, ad, tf, evren_t, tablo_hash, veri_al=hm.veri_oku)
    if bilgi["hatali"]:
        raise RuntimeError(f"{ad} {tf}: {len(bilgi['hatali'])} sembolde koşu hatası: {bilgi['hata_ornegi']}")
    if not ham:
        raise RuntimeError(f"{ad} {tf}: ham sonuç yok (veri yok)")
    analiz_bas, oos_bit = donem_sinirlari(bilgi)
    oos = oos_birlestir({ad: ham}, {ad: evren_t}, analiz_bas, carpan, tablo_yolu)
    if not len(oos):
        raise RuntimeError(f"{ad} {tf}: analiz döneminde işlem yok")
    tablo, res = oynat(oos, analiz_bas, oos_bit)
    return {"oos": oos, "tablo": tablo, "res": res, "analiz_bas": analiz_bas, "oos_bit": oos_bit, "bilgi": bilgi}


def satir_gunluk(cikti: Path, row: dict, tablo_yolu, tablo_hash: str, onbellekle: bool = True) -> pd.Series:
    """Satırın tek kasa x1 günlük MTM getirisi (portföy satırında günlük özsermaye getirisi). Önbellek: gunluk/<ad>--<tf>.parquet
    (kısmi yazma yok: atomik)."""
    cikti = Path(cikti)
    ad, tf = row["strateji"], row["tf"]
    yol = cikti / "gunluk" / f"{ad}--{tf}.parquet"
    yan = yol.with_suffix(".json")
    damga = girdi_damgasi(cikti, row, (1.0,), "motor/arastirma/v2/kasa.py") if onbellekle else None
    if onbellekle and yol.exists():
        if yan.exists():
            gecerli = json.loads(yan.read_text()).get(DAMGA_ANAHTARI) == damga          # bayat damga: aşağıda yeniden hesaplanır
        elif hm.eski_kabul_mu():
            gecerli = True                                                              # damgasız tarihsel önbellek: yalnız açık bayrakla
        else:
            raise hm.DamgaUyusmazligi(f"{yol.name}: günlük önbellekte girdi damgası yok (eski çıktı); "
                                      f"{hm.ESKI_ORTAM}=1 / --eski-yan-dosya ile okuyun")
        if gecerli:
            d = pd.read_parquet(yol)
            return pd.Series(d["getiri"].to_numpy(dtype=float), index=pd.DatetimeIndex(d["gun"]))
    if row["stil_v2"] == "portfoy":
        g1, m1 = hm.pf_yukle(cikti, 1.0, ad, tablo_hash, pf_veri_al=hm.pf_veri_oku, evren_adi=row["evren"])
        if g1 is None:
            raise RuntimeError(f"{ad}: portföy koşusu hata: {m1.get('hata')}")
        analiz_bas = we.analiz_bas_hesapla({s: pd.Timestamp(t) for s, t in m1["veri_bas_sembol"].items()})
        x = g1[pd.DatetimeIndex(g1["gun"]) >= analiz_bas]
        s = pd.Series(x["getiri"].to_numpy(dtype=float), index=pd.DatetimeIndex(x["gun"]))
    else:
        o = satir_oynat(cikti, row, tablo_yolu, tablo_hash)
        mtm = MtmOnbellek(cikti, {ad: tf})
        s = gunluk_mtm_getiri(o["oos"], o["tablo"], o["res"], mtm, o["analiz_bas"], o["oos_bit"])
    if onbellekle:
        atomik_yaz_parquet(pd.DataFrame({"gun": pd.DatetimeIndex(s.index).as_unit("ns"), "getiri": s.to_numpy(dtype=float)}), yol)
        atomik_yaz_json(yan, {DAMGA_ANAHTARI: damga})
    return s
