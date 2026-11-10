"""v2 Aşama 1 — ham koşu (ON_KAYIT_V2 bölüm 3, 1.1, 1.2; P1-1).

Her havuz_v2 satırı: yalnız VARSAYILAN ayar (1.1; ızgara yok), beyan ettiği evrenin her enstrümanında, geliştirme döneminin
tamamında (okuma `bit` = HOLDOUT_BAS ile kesilir; v1 yükleyicisi `wf_evren._veri`), maliyet ×1 ve ×2. Tek-grafik satırlarda
her işlem için GÜNLÜK piyasa-değeri (MTM) yolu yazılır; portföy (pf__) satırlarında yol = günlük özsermaye getirisidir.

Çıktı (sonuclar/evren/v2/):
  ham/x1|x2/<strateji>--<tf>--<sembol>.parquet  : ayar_no, giris_zamani, cikis_zamani, yon, r, sf, stop_mesafe, fonlama_r
                                                  (r = funding dahil net R; v1 `islem_ozet` ile uyumlu sütunlar)
  ham/x1|x2/<...>.json                          : yan dosya, EN SON yazılır = "bitti" işareti (devam ettirilebilir)
  mtm/x1|x2/<...>.parquet                       : islem_no (ham satır sırası), gun (UTC), kum_r (birikimli R)
  portföy: ham/x*/<pf__ad>--1d--_PORTFOY.parquet (gun, getiri, dengeleme) + .json

MTM tanımı: işlemin açık olduğu her UTC gün sonu d (giriş günü dahil, çıkış günü hariç) için
    kum_r(d) = yon·(kapanış_d − giriş_fiyatı)/stop_mesafe − giriş_komisyonu_R − funding_R·pay(d)
(kapanış_d = o günün sonunda KAPANMIŞ son mum; pay(d) = geçen süre oranı; ileri doldurma yalnız geçmişten) ve çıkış gününde
kum_r = işlemin R'si (maliyetler girişte ve çıkışta). Böylece yolun son değeri işlemin R'sine EŞİTTİR ve nokta sayısı =
giriş günü ile çıkış günü arası takvim günü sayısı (uçlar dahil). Yaklaşıklıklar (tutucu, raporlanır): kısmi çıkışlarda ara
günler ilk miktarla değerlenir; gerçek funding (kripto) süreye doğrusal yayılır; çıkış maliyeti yalnız çıkış gününde.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, secim
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import maliyet, sabit
from motor.backtest.motor import backtest
from motor.strateji import funding, kayit
from motor.veri import depo

PF_SEMBOL = "_PORTFOY"


class HoldoutSizintisi(RuntimeError):
    """Geliştirme okumasında HOLDOUT_BAS ve sonrası veri göründü. ASLA yutulmaz; aşama durur."""


# ============================================================================ yardımcılar
def zaman_utc(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def carpan_adi(carpan: float) -> str:
    return f"x{carpan:g}"


def dosya_yolu(dizin: Path, ad: str, tf: str, sembol: str) -> Path:
    return Path(dizin) / f"{ad}--{tf}--{sembol}.parquet"


def havuz_oku(yol=None) -> pd.DataFrame:
    d = pd.read_csv(yol or sabit.HAVUZ_CSV)
    for c in ("strateji", "stil_v2", "tf", "evren"):
        if c not in d.columns:
            raise ValueError(f"havuz dosyasında sütun yok: {c}")
    if d["strateji"].duplicated().any():
        raise ValueError("havuzda tekrarlı strateji")
    return d


def havuz_muhru_dogrula(havuz_yolu=None, muhur_yolu=None) -> dict:
    """Önceki aşamanın (havuz) mührü yoksa / havuz dosyası mühürle uyuşmuyorsa AÇIK HATA."""
    import hashlib
    hy, my = Path(havuz_yolu or sabit.HAVUZ_CSV), Path(muhur_yolu or sabit.HAVUZ_MUHRU)
    if not my.exists():
        raise RuntimeError(f"havuz mührü yok: {my} (önce havuz aşaması)")
    m = json.loads(my.read_text())
    if hashlib.sha256(hy.read_bytes()).hexdigest() != m.get("havuz_csv_sha256"):
        raise RuntimeError("havuz_v2.csv mühürle uyuşmuyor (havuz koşudan sonra değiştirilemez)")
    return m


def varsayilan_strateji(ad: str) -> tuple:
    """1.1: -> (etiket, strateji). Kart ayarı dosyası varsa İLK kaydı, yoksa sınıfın varsayılanı. Izgara/dış ayar ASLA."""
    kartlar = kayit.kart_ayarlari(ad)
    if kartlar:
        kid = kartlar[0]["kart_id"]
        return f"kart:{kid}", kayit.kart_ayarli_strateji(ad, kid)
    return "varsayilan", kayit.al(ad)()


def veri_oku(sembol: str, tf: str) -> tuple:
    """(mumlar, funding) — v1 yükleyicisi (dönem 2017_gelistirme: okuma `bit` = HOLDOUT_BAS ile kesilir). HOLDOUT_BAS ve
    sonrası herhangi bir mum/funding satırı varsa HoldoutSizintisi (kesin hata)."""
    mumlar, fund = we._veri(sembol, tf)
    sizinti_kontrol(sembol, tf, mumlar, fund)
    return mumlar, fund


def sizinti_kontrol(sembol: str, tf: str, mumlar, fund) -> None:
    for ad, df in (("mum", mumlar), ("funding", fund)):
        if df is not None and len(df) and pd.Timestamp(df.index.max()) >= sabit.HOLDOUT_BAS:
            raise HoldoutSizintisi(f"{sembol} {tf}: {ad} verisi HOLDOUT_BAS ({sabit.HOLDOUT_BAS}) ve sonrasına uzanıyor")


def gunluk_kapanis(mumlar: pd.DataFrame, tf: str) -> pd.Series:
    """UTC günü sonunda KAPANMIŞ son mumun kapanışı (mum günü = kapanış anının son nanosaniyesinin günü); veri olmayan
    takvim günleri geçmişten ileri doldurulur (gelecek bilgisi yok). İndeks: kesintisiz UTC takvim günleri."""
    dur = depo.aralik_suresi(tf)
    idx = pd.DatetimeIndex(mumlar.index).as_unit("ns")
    gun = (idx + dur - pd.Timedelta(1, "ns")).floor("D")
    s = pd.Series(mumlar["kapanis"].to_numpy(dtype=float), index=gun).groupby(level=0).last()
    return s.reindex(pd.date_range(s.index[0], s.index[-1], freq="D")).ffill()


def mtm_yolu(giris, cikis, yon, giris_fiyati, stop_mesafe, r_son, giris_maliyet_r, funding_r,
             kapanis_gun: pd.Series) -> pd.DataFrame:
    """İşlem başına günlük MTM yolu (modül belgesi). Girdiler işlem sırasında hizalı dizilerdir; stop_mesafe fiyat birimidir
    (risk$/miktar). -> DataFrame(islem_no int32, gun UTC, kum_r float32)."""
    giris = pd.DatetimeIndex(giris).as_unit("ns")
    cikis = pd.DatetimeIndex(cikis).as_unit("ns")
    yon = np.asarray(yon, dtype=float)
    gf = np.asarray(giris_fiyati, dtype=float)
    sm = np.asarray(stop_mesafe, dtype=float)
    r_son = np.asarray(r_son, dtype=float)
    gm = np.asarray(giris_maliyet_r, dtype=float)
    fr = np.asarray(funding_r, dtype=float)
    kap = kapanis_gun.to_numpy(dtype=float)
    kidx = pd.DatetimeIndex(kapanis_gun.index).as_unit("ns")
    t0 = kidx[0]
    gun_ns = pd.Timedelta(1, "D").value
    g0 = np.floor_divide(giris.floor("D").asi8 - t0.value, gun_ns)
    g1 = np.floor_divide(cikis.floor("D").asi8 - t0.value, gun_ns)
    no, gunler, deger = [], [], []
    for i in range(len(giris)):
        a, b = int(g0[i]), int(g1[i])
        if a < 0 or b >= len(kap) + 1 or b < a:
            raise ValueError(f"MTM: işlem {i} gün aralığı kapanış serisi dışında ({a}, {b}, {len(kap)})")
        if b > a:
            gn = np.arange(a, b)
            gun_sonu = t0.value + (gn + 1) * gun_ns
            sure = float(cikis.asi8[i] - giris.asi8[i])
            pay = np.clip((gun_sonu - giris.asi8[i]) / sure, 0.0, 1.0)
            v = yon[i] * (kap[gn] - gf[i]) / sm[i] - gm[i] - fr[i] * pay
            no.append(np.full(len(gn), i, dtype=np.int32))
            gunler.append(gn)
            deger.append(v)
        no.append(np.array([i], dtype=np.int32))
        gunler.append(np.array([b]))
        deger.append(np.array([r_son[i]]))
    if not no:
        return _MTM_BOS.copy()
    g = np.concatenate(gunler)
    return pd.DataFrame({"islem_no": np.concatenate(no),
                         "gun": pd.DatetimeIndex(t0 + pd.to_timedelta(g, unit="D")),
                         "kum_r": np.concatenate(deger).astype(np.float32)})


_MTM_BOS = pd.DataFrame({"islem_no": np.array([], dtype=np.int32),
                         "gun": pd.DatetimeIndex([], tz="UTC").as_unit("ns"), "kum_r": np.array([], dtype=np.float32)})
_HAM_BOS = we._BOSLUK.assign(fonlama_r=np.array([], dtype=np.float32))


def islem_hazirla(islemler: pd.DataFrame, sembol: str, tf: str, carpan: float, mumlar: pd.DataFrame,
                  tablo_yolu, kapanis_gun: Optional[pd.Series] = None) -> tuple:
    """Motor işlem tablosu -> (ham DataFrame, mtm DataFrame). TradFi funding (1.2) burada uygulanır: r funding dahil."""
    d = islemler.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
    if not len(d):
        return _HAM_BOS.copy(), _MTM_BOS.copy()
    r0 = d["r"].to_numpy(dtype=float)
    if not np.isfinite(r0).all():
        raise ValueError("işlem R'si NaN/sonsuz (stop riski 0?)")
    net = d["net_pnl"].to_numpy(dtype=float)
    miktar = d["miktar"].to_numpy(dtype=float)
    gf = d["giris_fiyati"].to_numpy(dtype=float)
    nominal = miktar * gf
    with np.errstate(divide="ignore", invalid="ignore"):
        risk = np.where(r0 != 0.0, net / r0, np.nan)             # r = net/risk$ -> risk$ (r != 0'da tam; float duyarlığı)
    bos = ~(np.isfinite(risk) & (risk > 0))
    if bos.any():                                                 # r == 0 tam: komşu satırın stop oranı (v1 islem_ozet ile aynı kural)
        sf_k = pd.Series(np.where(bos, np.nan, risk / nominal)).ffill().bfill().fillna(sabit.SF_YEDEK).to_numpy()
        risk = np.where(bos, sf_k * nominal, risk)
    oran = evren_maliyet.funding_long_8s_oran(sembol, tablo_yolu)
    fon_usd = maliyet.funding_maliyeti_usd(d["yon"], miktar, gf, d["giris_zamani"], d["cikis_zamani"], oran)
    fon_r = fon_usd / risk
    r = r0 - fon_r
    taker = evren_maliyet.sembol_maliyeti(sembol, carpan, tablo_yolu)[0] / 100.0
    giris_kom_r = nominal * taker / risk
    gercek_fon_r = d["funding"].to_numpy(dtype=float) / risk                # motorun gerçek (kripto) funding'i, zaten r0 içinde
    toplam_fon_r = fon_r + gercek_fon_r
    stop_fiyat = risk / miktar
    sf = np.clip(risk / nominal, sabit.SF_TABAN, None)
    ham = pd.DataFrame({
        "ayar_no": np.zeros(len(d), dtype=np.int16),
        "giris_zamani": pd.DatetimeIndex(d["giris_zamani"]).as_unit("ns"),
        "cikis_zamani": pd.DatetimeIndex(d["cikis_zamani"]).as_unit("ns"),
        "yon": d["yon"].to_numpy(dtype=np.int8), "r": r.astype(np.float32), "sf": sf.astype(np.float32),
        "stop_mesafe": stop_fiyat.astype(np.float32), "fonlama_r": fon_r.astype(np.float32)})
    kg = kapanis_gun if kapanis_gun is not None else _kapanis_onbellekli(sembol, tf, mumlar)
    mtm = mtm_yolu(d["giris_zamani"], d["cikis_zamani"], d["yon"], gf, stop_fiyat, r, giris_kom_r, toplam_fon_r, kg)
    return ham, mtm


_KG: dict = {}


def _kapanis_onbellekli(sembol: str, tf: str, mumlar: pd.DataFrame) -> pd.Series:
    """Aynı (sembol, tf, mum nesnesi) için günlük kapanış serisi bir kez hesaplanır (grup içi çok strateji)."""
    k = (sembol, tf, id(mumlar))
    if k not in _KG:
        if len(_KG) >= sabit.ONBELLEK_BOYUT:
            _KG.clear()
        _KG[k] = (mumlar, gunluk_kapanis(mumlar, tf))        # mumlar nesnesi tutulur: id yeniden kullanımı önlenir
    return _KG[k][1]


def _yaz_atomik(df: pd.DataFrame, yol: Path):
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol)


def _yan_yaz(yol: Path, meta: dict):
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".jtmp")
    gecici.write_text(json.dumps(meta, ensure_ascii=False, default=str))
    gecici.replace(yol)


# ---------------------------------------------------------------------------- kimlik damgası (B16)
# Yan dosya yalnız maliyet_hash tutuyordu: veri, strateji kodu ya da ortak motor değişse de eski sonuç sessizce okunurdu.
# Damga: veri_sha256 (okunan mum+funding içeriği), strateji_hash (kaynak+kart/ayar dosyaları), motor_hash (paylaşılan motor modülleri),
# git_commit. Okumada strateji/motor/(isteğe bağlı veri) uyuşmazlığı RuntimeError; commit yalnız "mühürdeki şimdikinin atası mı"
# diye bakılır (her commit'te sonuç geçersiz olmasın; muhur_kontrol ile aynı kural).
# ESKİ (damgasız) v2 yan dosyaları tarihsel kayıttır: yalnız AÇIK bayrakla (eski_kabul=True ya da V2_ESKI_YAN_DOSYA=1) okunur.
ESKI_ORTAM = "V2_ESKI_YAN_DOSYA"
DAMGA_ALANLARI = ("veri_sha256", "strateji_hash", "motor_hash", "git_commit")
_DAMGA_ONBELLEK: dict = {}
_YOK = object()                       # "veri özeti verilmedi" işareti (None = veri yok, geçerli bir özet değeridir)
# motor_hash kapsamı: v1 mührünün ortak modülleri (ORTAK_MODULLER; mühür biçimi değişmesin diye ona dokunulmaz) + ham çıktıyı
# doğrudan belirleyen ek modüller (B16 kapsam genişletme: htf/gösterge/yeniden örnekleme/çıkış/funding/depo/ham).
MOTOR_EK_MODULLER = ("motor/strateji/htf.py", "motor/strateji/gostergeler.py", "motor/veri/yeniden_ornekle.py",
                     "motor/strateji/cikislar.py", "motor/strateji/funding.py", "motor/veri/depo.py", "motor/arastirma/v2/ham.py")


def motor_hash_girdisi() -> dict:
    """{göreli yol: sha256} — motor_hash'in girdisi (ortak modüller + ek modüller). Testte sahtelenebilir."""
    from motor.arastirma import wf_evren_holdout as v1h
    return {**v1h.ortak_modul_hashleri(), **{y: v1h._sha(we.KOK / y) for y in MOTOR_EK_MODULLER}}


def damga_onbellegini_sifirla() -> None:
    _DAMGA_ONBELLEK.clear()


def _sha_json(o) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def veri_sha256(*cerceveler) -> Optional[str]:
    """Mum/funding DataFrame'lerinin içerik özeti (indeks + değerler, sıralı). Hepsi None/boşsa None."""
    import hashlib
    h = hashlib.sha256()
    var = False
    for df in cerceveler:
        if df is None or not len(df):
            h.update(b"-")
            continue
        var = True
        h.update(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes())
        h.update(("|".join(map(str, df.columns))).encode())
    return h.hexdigest() if var else None


def kimlik_damgasi(ad: str, stil: str = "swing", veri: Optional[str] = None) -> dict:
    """Bu sürecin kodu için damga (süreç ömrü boyunca önbellekli: git/hash hesabı pahalı)."""
    from motor.arastirma import wf_evren_holdout as v1h
    if "motor" not in _DAMGA_ONBELLEK:
        _DAMGA_ONBELLEK["motor"] = _sha_json(motor_hash_girdisi())
        _DAMGA_ONBELLEK["git"] = v1h.git_commit()
    k = ("strateji", ad, stil)
    if k not in _DAMGA_ONBELLEK:
        try:
            _DAMGA_ONBELLEK[k] = _sha_json(v1h.strateji_hashleri([{"strateji": ad, "stil": stil}]))
        except (KeyError, ImportError):                        # kayıtlı olmayan strateji (yalnız sentetik test): sabit işaret
            _DAMGA_ONBELLEK[k] = "kayitsiz"
    return {"veri_sha256": veri, "strateji_hash": _DAMGA_ONBELLEK[k], "motor_hash": _DAMGA_ONBELLEK["motor"],
            "git_commit": _DAMGA_ONBELLEK["git"]}


def eski_kabul_mu(eski_kabul: Optional[bool] = None) -> bool:
    import os
    return bool(eski_kabul) if eski_kabul is not None else os.environ.get(ESKI_ORTAM, "") not in ("", "0")


def kimlik_farki(meta: dict, ad: str, stil: str, eski_kabul: Optional[bool] = None, veri_simdi=_YOK) -> tuple:
    """meta damgasını şimdiki kodla/veriyle karşılaştırır. -> (tur, mesaj): (None, "") uyumlu; ("damgasiz", ..) damga alanı hiç yok ve
    eski_kabul de yok; ("bayat", ..) damga var ama uyuşmuyor (yeniden üretilmeli). Damgalı dosyada veri_simdi (şimdiki verinin
    veri_sha256'sı; veri yoksa None) ZORUNLU: verilmezse ValueError (veri özeti sessizce atlanmaz)."""
    if not any(a in meta for a in DAMGA_ALANLARI):
        if eski_kabul_mu(eski_kabul):
            return None, ""
        return "damgasiz", (f"kimlik damgası yok (eski v2 yan dosyası, yalnız maliyet_hash içerir). Tarihsel kayıt olarak okumak için "
                            f"eski_kabul=True ya da {ESKI_ORTAM}=1 verin; yeni koşular damgalıdır")
    if veri_simdi is _YOK:
        raise ValueError("veri özeti (veri_al / veri_simdi) verilmedi: damgalı yan dosya veri_sha256 karşılaştırması olmadan okunamaz (B16)")
    from motor.arastirma import wf_evren_holdout as v1h
    simdi = kimlik_damgasi(ad, stil)
    for alan in ("strateji_hash", "motor_hash"):
        if meta.get(alan) != simdi[alan]:
            return "bayat", (f"{alan} uyuşmuyor (kayıtlı {str(meta.get(alan))[:12]}, şimdi {simdi[alan][:12]}): sonuç başka kod "
                             f"sürümüyle üretilmiş; yeniden üretin ya da tarihsel kayıt olarak eski_kabul ile okuyun")
    if not v1h._commit_ata_mi(str(meta.get("git_commit", "yok")), simdi["git_commit"]):
        return "bayat", f"kayıtlı git_commit {meta.get('git_commit')} şimdiki HEAD'in atası değil"
    if meta.get("veri_sha256") != veri_simdi:
        return "bayat", (f"veri_sha256 uyuşmuyor (kayıtlı {str(meta.get('veri_sha256'))[:12]}, şimdi {str(veri_simdi)[:12]}): "
                         f"veri değişmiş")
    return None, ""


def kimlik_dogrula(meta: dict, ad: str, stil: str, kaynak: str, eski_kabul: Optional[bool] = None, veri_simdi=_YOK) -> None:
    """kimlik_farki'nin sert hali: uyuşmazlıkta RuntimeError (açık mesaj). Damga alanı hiç yoksa (v2 tarihsel dosya): yalnız eski_kabul
    (ya da V2_ESKI_YAN_DOSYA=1) ile geçer."""
    tur, mesaj = kimlik_farki(meta, ad, stil, eski_kabul, veri_simdi)
    if tur is not None:
        raise RuntimeError(f"{kaynak}: {mesaj}")


def veri_ozeti_simdi(veri_al, sembol: str, tf: str) -> Optional[str]:
    """Şimdiki verinin özeti; veri yoksa (ham_gorev'in 'veri_yok' koşulları: dosya yok / geçersiz) None. HoldoutSizintisi yukarı çıkar."""
    try:
        mumlar, fund = veri_al(sembol, tf)
    except (FileNotFoundError, ValueError):
        return None
    return veri_sha256(mumlar, fund)


def pf_veri_ozeti(v: dict, f: dict) -> str:
    return _sha_json({s: veri_sha256(v[s], f.get(s)) for s in sorted(v)})


def pf_veri_oku(evren_adi: str = "genel") -> tuple:
    """Portföy görevinin okuduğu veri (pf_gorev ile AYNI yükleyici) -> (v, f, dis). veri_ayarla(..., DONEM) kurulu olmalı."""
    from motor.arastirma import wf_evren_portfoy as wep
    return wep.veri_yukle(sabit.evren_listesi(evren_adi), "1d")


def pf_veri_ozeti_simdi(pf_veri_al, evren_adi: str) -> str:
    v, f, _ = pf_veri_al(evren_adi)
    for s, df in v.items():
        sizinti_kontrol(s, "1d", df, f.get(s))
    return pf_veri_ozeti(v, f)


def _meta_taslak(ad, tf, sembol, carpan, tablo_hash, etiket="", stil="swing") -> dict:
    return {"strateji": ad, "tf": tf, "sembol": sembol, "carpan": carpan, "ayar": etiket, "veri_yok": False, "hata": "",
            "donem": sabit.DONEM, "maliyet_hash": tablo_hash, **kimlik_damgasi(ad, stil)}


def _bayat_mi(yan: Path, ad: str, stil: str, tablo_hash: str, veri_simdi_fn, eski_kabul: Optional[bool] = None) -> bool:
    """Devam kararı (B16): bitti işareti VAR diye atlanmaz. True = bayat (yeniden koşulmalı); False = geçerli. Damgasız eski yan
    dosya: eski_kabul/V2_ESKI_YAN_DOSYA yoksa RuntimeError (yeniden üretilmez: tarihsel çıktının üzerine yazılmasın); varsa geçerli."""
    m = json.loads(yan.read_text())
    if not any(a in m for a in DAMGA_ALANLARI):
        tur, mesaj = kimlik_farki(m, ad, stil, eski_kabul)
        if tur is not None:
            raise RuntimeError(f"{yan.name}: {mesaj}")
        return False
    if m.get("maliyet_hash") != tablo_hash:
        return True
    tur, _ = kimlik_farki(m, ad, stil, eski_kabul, veri_simdi_fn())
    return tur is not None


# ============================================================================ tek-grafik görev
def ham_gorev(ad: str, tf: str, sembol: str, carpan: float, cikti: Path, tablo_yolu, tablo_hash: str,
              yeniden: bool = False, _veri=None) -> dict:
    """Tek (strateji, tf, sembol, çarpan). Yan dosya en son yazılır; biten atlanır. veri_ayarla(...) kurulu olmalı.
    HoldoutSizintisi yukarı fırlar (yan dosya YAZILMAZ). Diğer hatalar yan dosyaya 'hata' olarak yazılır (sayılır)."""
    cd = carpan_adi(carpan)
    hd, md = Path(cikti) / "ham" / cd, Path(cikti) / "mtm" / cd
    yol = dosya_yolu(hd, ad, tf, sembol)
    yan = yol.with_suffix(".json")
    veri_al = _veri or veri_oku
    if yan.exists() and not yeniden:
        if not _bayat_mi(yan, ad, "swing", tablo_hash, lambda: veri_ozeti_simdi(veri_al, sembol, tf)):
            return {"atlandi": True}
        # bayat (damga/maliyet/veri uyuşmuyor): atlanmaz, yeniden koşulur (yan dosya en sonda üzerine yazılır)
    t0 = time.perf_counter()
    meta = _meta_taslak(ad, tf, sembol, carpan, tablo_hash)
    try:
        mumlar, fund = veri_al(sembol, tf)
    except (FileNotFoundError, ValueError) as e:                  # bu tf'de verisi olmayan enstrüman dışarıda (v1 K-B)
        meta.update(veri_yok=True, hata=f"{type(e).__name__}: {e}"[:200])
        _yan_yaz(yan, meta)
        return meta
    sizinti_kontrol(sembol, tf, mumlar, fund)
    meta["veri_sha256"] = veri_sha256(mumlar, fund)
    if not len(mumlar):
        meta.update(veri_yok=True, hata="dönem içinde mum yok")
        _yan_yaz(yan, meta)
        return meta
    try:
        etiket, st = varsayilan_strateji(ad)
        meta["ayar"] = etiket
        kurallar = we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
        ay = evren_maliyet.maliyet_ayarlari(sembol, kurallar, carpan, tablo_yolu)
        hazir = funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf)
        res = backtest(hazir, st, ay, fund)
        ham, mtm = islem_hazirla(res.islemler, sembol, tf, carpan, mumlar, tablo_yolu)
    except Exception as e:  # noqa: BLE001  (sayılır: yan dosyada 'hata'; eleme aşaması satırı 'hata' yapar)
        meta.update(hata=f"{type(e).__name__}: {e}"[:300], sure_sn=round(time.perf_counter() - t0, 2))
        _yan_yaz(yan, meta)
        return meta
    _yaz_atomik(ham, yol)
    _yaz_atomik(mtm, dosya_yolu(md, ad, tf, sembol))
    meta.update(n_islem=int(len(ham)), n_mtm=int(len(mtm)), veri_bas=str(mumlar.index[0]), veri_bit=str(mumlar.index[-1]),
                sure_sn=round(time.perf_counter() - t0, 2))
    _yan_yaz(yan, meta)
    return meta


# ============================================================================ portföy görevi
def varsayilan_pf(ad: str, evren_t: tuple):
    """1.1 (portföy): sınıfın varsayılan ayarı (csv bağlamaları/ızgara DEĞİL). Evrene uygun değilse None."""
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    st = tum_portfoy_stratejileri()[ad]()
    etkin = st.etkin_semboller(evren_t)
    st = st.yeni(semboller=etkin) if etkin else st
    return st if st.uygun_mu(evren_t) else None


def maliyet_pf(semboller, carpan: float, tablo_yolu):
    from motor.portfoy.motor import PortfoyAyarlari
    ms = {s: evren_maliyet.sembol_maliyeti(s, carpan, tablo_yolu) for s in semboller}
    return PortfoyAyarlari(limit_modu="olc", maliyet_sembol=ms, komisyon_taker_yuzde=max(v[0] for v in ms.values()),
                           komisyon_maker_yuzde=max(v[1] for v in ms.values()),
                           kayma_bps=max(v[2] for v in ms.values()), stop_kayma_bps=max(v[3] for v in ms.values()))


def pf_fonlama_duzeltmesi(getiri: pd.Series, ozsermaye: pd.Series, poz: pd.DataFrame, veriler: dict, tablo_yolu) -> tuple:
    """Portföy günlük getirisine TradFi funding (1.2): DK_ sembolünde net LONG miktar × kapanış × oran × (24/8) / önceki gün
    özsermayesi her gün getiriden düşer (short geliri yok). Yaklaşık (motor değişmedi): fonlama özsermayeye geri beslenmez.
    -> (düzeltilmiş getiri, toplam fonlama maliyeti (özsermaye oranı toplamı))."""
    gun_ps = sabit.GUN_SAAT / sabit.FUNDING_PERIYOT_SAAT
    ozs = ozsermaye.copy()
    ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
    ozs = ozs.groupby(level=0).last()
    onceki = ozs.shift(1).fillna(ozs)                  # ilk gün: kendi özsermayesi
    maliyet_oran = pd.Series(0.0, index=getiri.index)
    for s in poz.columns:
        oran = evren_maliyet.funding_long_8s_oran(s, tablo_yolu)
        if oran <= 0 or s not in veriler:
            continue
        q = poz[s].copy()
        q.index = pd.DatetimeIndex(q.index).floor("D")
        q = q.groupby(level=0).last().clip(lower=0.0)
        kap = veriler[s]["kapanis"].copy()
        kap.index = pd.DatetimeIndex(kap.index).floor("D")
        kap = kap.groupby(level=0).last()
        usd = (q * kap.reindex(q.index)).fillna(0.0) * oran * gun_ps
        maliyet_oran = maliyet_oran.add((usd / onceki).reindex(getiri.index).fillna(0.0), fill_value=0.0)
    return getiri - maliyet_oran, float(maliyet_oran.sum())


def pf_gorev(ad: str, carpan: float, cikti: Path, tablo_yolu, tablo_hash: str, evren_adi: str = "genel",
             yeniden: bool = False) -> dict:
    """Portföy (pf__) satırı: varsayılan ayar, geliştirme dönemi tek koşu. Yol = günlük özsermaye getirisi (+ yeniden dengeleme
    günü bayrağı); meta: kill_olayi, n_dengeleme, veri_bas (sembol başına, analiz başlangıcı için)."""
    from motor.arastirma import wf_evren_portfoy as wep
    from motor.arastirma import wf_portfoy as wp
    from motor.portfoy.motor import portfoy_backtest   # noqa: F401  (wep._kos kullanır)
    cd = carpan_adi(carpan)
    hd = Path(cikti) / "ham" / cd
    yol = dosya_yolu(hd, ad, "1d", PF_SEMBOL)
    yan = yol.with_suffix(".json")
    if yan.exists() and not yeniden:
        if not _bayat_mi(yan, ad, "portfoy", tablo_hash, lambda: pf_veri_ozeti_simdi(pf_veri_oku, evren_adi)):
            return {"atlandi": True}
    t0 = time.perf_counter()
    meta = _meta_taslak(ad, "1d", PF_SEMBOL, carpan, tablo_hash, "varsayilan", stil="portfoy")
    meta["portfoy"] = True
    try:
        evren = sabit.evren_listesi(evren_adi)
        v, f, dis = wep.veri_yukle(evren, "1d")
        for s, df in v.items():
            sizinti_kontrol(s, "1d", df, f.get(s))
        meta["disarida"] = list(dis)
        meta["veri_sha256"] = pf_veri_ozeti(v, f)
        evren_t = tuple(v)
        st = varsayilan_pf(ad, evren_t)
        if st is None:
            raise RuntimeError("varsayılan ayar bu evrende uygun değil (yeterli sembol/çift yok)")
        ay = maliyet_pf(evren_t, carpan, tablo_yolu)
        r = wep._kos(st, v, f, evren_t, ay, 0)
        ozs = r.gunluk_ozsermaye.copy()
        ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
        ozs = ozs.groupby(level=0).last().astype(float)
        getiri = ozs.pct_change().fillna(0.0)
        getiri, fon_toplam = pf_fonlama_duzeltmesi(getiri, r.gunluk_ozsermaye, r.pozisyon_gecmisi, v, tablo_yolu)
        q = r.pozisyon_gecmisi
        degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
        deng_gunleri = set(pd.DatetimeIndex(q.index[degisti.to_numpy()]).floor("D")) if len(q) else set()
        out = pd.DataFrame({"gun": pd.DatetimeIndex(getiri.index).as_unit("ns"), "getiri": getiri.to_numpy(dtype=float),
                            "dengeleme": [g in deng_gunleri for g in getiri.index]})
        kill = sum(1 for o in r.limit_olaylari if o.get("tur") == "kill_switch")
        veri_bas = {s: str(v[s].index[0]) for s in v}
        meta.update(kill_olayi=int(kill), n_dengeleme=int(len(deng_gunleri)), n_islem=int(len(r.islemler)),
                    n_enstruman=len(v), veri_bas_sembol=veri_bas,
                    veri_bas=min(veri_bas.values()), veri_bit=str(max(df.index[-1] for df in v.values())),
                    fonlama_toplam=fon_toplam, gun=int(len(out)))
    except HoldoutSizintisi:
        raise
    except Exception as e:  # noqa: BLE001  (sayılır)
        meta.update(hata=f"{type(e).__name__}: {e}"[:300], sure_sn=round(time.perf_counter() - t0, 2))
        _yan_yaz(yan, meta)
        return meta
    _yaz_atomik(out, yol)
    meta["sure_sn"] = round(time.perf_counter() - t0, 2)
    _yan_yaz(yan, meta)
    return meta


# ============================================================================ aşama: görev listesi, havuz
_AYAR: dict = {}


def _baslat(ayar: dict):
    we.veri_ayarla(ayar.get("veri_dizini"), sabit.DONEM)
    _AYAR.clear()
    _AYAR.update(ayar)


def _isci(g: dict):
    """Bir grup: (tf, sembol, carpan) için sıralı strateji listesi (tek veri yüklemesi) ya da bir portföy görevi."""
    a = _AYAR
    cikti, tablo_yolu, tablo_hash = Path(a["cikti"]), a["tablo_yolu"], a["tablo_hash"]
    son = a.get("son")
    sonuc = []
    if g["tur"] == "portfoy":
        if son is not None and time.time() > son:
            return {"ertelendi": 1, "sonuc": []}
        return {"ertelendi": 0, "sonuc": [pf_gorev(g["strateji"], g["carpan"], cikti, tablo_yolu, tablo_hash, g["evren"],
                                                   a.get("yeniden", False))]}
    erte = 0
    cache = {}

    def veri(s, t):
        if (s, t) not in cache:
            cache[(s, t)] = veri_oku(s, t)
        return cache[(s, t)]
    for ad in g["stratejiler"]:
        if son is not None and time.time() > son:
            erte += 1
            continue
        sonuc.append(ham_gorev(ad, g["tf"], g["sembol"], g["carpan"], cikti, tablo_yolu, tablo_hash,
                               a.get("yeniden", False), _veri=veri))
    return {"ertelendi": erte, "sonuc": sonuc}


def gorevleri_uret(havuz: pd.DataFrame, cikti: Path, stratejiler=None, semboller=None, carpanlar=sabit.MALIYET_CARPANLARI,
                   hatalari_yeniden: bool = False, veri_al=None, tablo_hash: Optional[str] = None) -> tuple:
    """-> (gruplar, toplam_gorev, kalan_gorev). Biten görev listeye girmez; biten = yan dosya VAR ve damgası (strateji/motor/commit/
    maliyet/VERİ) şimdikiyle uyuşuyor (B16). Bayat (damgalı ama uyuşmayan) görev yeniden kuyruğa girer; damgasız eski yan dosya
    eski_kabul/V2_ESKI_YAN_DOSYA yoksa RuntimeError. `hatalari_yeniden` ile hatalı (veri_yok olmayan) yan dosya silinip yeniden
    kuyruğa alınır. veri_al(sembol, tf) -> (mumlar, funding) varsayılan veri_oku (veri_ayarla kurulu olmalı); tablo_hash verilmezse
    maliyet tablosu kontrolü bu planlamada yapılmaz (ham_gorev çalışırken yapar)."""
    veri_al = veri_al or veri_oku
    onb: dict = {}

    def vs(s, t):
        if (s, t) not in onb:
            onb[(s, t)] = veri_ozeti_simdi(veri_al, s, t)
        return onb[(s, t)]
    gruplar, toplam, kalan = [], 0, 0
    sec = set(stratejiler) if stratejiler else None
    grup: dict = {}
    for _, row in havuz.iterrows():
        ad = row["strateji"]
        if sec is not None and ad not in sec:
            continue
        for c in carpanlar:
            hd = Path(cikti) / "ham" / carpan_adi(c)
            if row["stil_v2"] == "portfoy":
                toplam += 1
                if _bitti_mi(dosya_yolu(hd, ad, row["tf"], PF_SEMBOL).with_suffix(".json"), hatalari_yeniden, ad, "portfoy", tablo_hash,
                             lambda: pf_veri_ozeti_simdi(pf_veri_oku, row["evren"])):
                    continue
                kalan += 1
                gruplar.append({"tur": "portfoy", "strateji": ad, "tf": row["tf"], "carpan": c, "evren": row["evren"],
                                "sembol": PF_SEMBOL})
                continue
            for s in sabit.evren_listesi(row["evren"]):
                if semboller and s not in set(semboller):
                    continue
                toplam += 1
                if _bitti_mi(dosya_yolu(hd, ad, row["tf"], s).with_suffix(".json"), hatalari_yeniden, ad, "swing", tablo_hash,
                             lambda s=s, tf=row["tf"]: vs(s, tf)):
                    continue
                kalan += 1
                grup.setdefault((row["tf"], s, c), []).append(ad)
    for (tf, s, c), adlar in sorted(grup.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        gruplar.append({"tur": "tek", "tf": tf, "sembol": s, "carpan": c, "stratejiler": sorted(adlar)})
    gruplar.sort(key=lambda g: (g["tur"] != "tek", g.get("tf", ""), g["sembol"], g["carpan"], g.get("strateji", "")))
    return gruplar, toplam, kalan


def _bitti_mi(yan: Path, hatalari_yeniden: bool, ad: str, stil: str, tablo_hash: Optional[str], veri_simdi_fn) -> bool:
    """Yan dosya var VE bayat değil (B16: yalnız var olması 'bitti' sayılmaz)."""
    if not yan.exists():
        return False
    if hatalari_yeniden:
        m = json.loads(yan.read_text())
        if m.get("hata") and not m.get("veri_yok"):
            yan.unlink()
            return False
    m = json.loads(yan.read_text())
    if any(a in m for a in DAMGA_ALANLARI) and tablo_hash is None:
        tablo_hash = m.get("maliyet_hash")                        # tablo kontrolü bu planlamada yok; ham_gorev yapar
    return not _bayat_mi(yan, ad, stil, tablo_hash, veri_simdi_fn)


def ham_asamasi(cikti: Path = None, surec: int = sabit.SUREC_VARSAYILAN, butce_sn: Optional[float] = None, veri_dizini=None, stratejiler=None,
                semboller=None, hatalari_yeniden: bool = False, havuz_yolu=None, muhur_yolu=None, ilerleme: bool = True) -> dict:
    """P1-1. Sonuçlar görev bitince diske yazılır (yan dosya en sonda): süreç herhangi bir anda öldürülse biten kaybolmaz;
    yeniden çalıştırınca kaldığı yerden sürer. `butce_sn` dolunca yeni görev BAŞLATILMAZ (süren görev biter)."""
    cikti = Path(cikti or sabit.CIKTI)
    havuz_muhru_dogrula(havuz_yolu, muhur_yolu)
    havuz = havuz_oku(havuz_yolu)
    tablo = maliyet.tabloyu_hazirla(cikti)
    tablo_hash = evren_maliyet.tablo_hash(tablo)
    we.veri_ayarla(veri_dizini, sabit.DONEM)                      # planlama de veri özetini bu dönemden hesaplar (B16)
    gruplar, toplam, kalan = gorevleri_uret(havuz, cikti, stratejiler, semboller, hatalari_yeniden=hatalari_yeniden,
                                            tablo_hash=tablo_hash)
    if ilerleme:
        print(f"[v2 ham] toplam {toplam} görev, kalan {kalan} ({len(gruplar)} grup); maliyet tablosu {tablo.name} {tablo_hash[:12]}",
              flush=True)
    ayar = {"veri_dizini": veri_dizini, "cikti": str(cikti), "tablo_yolu": str(tablo), "tablo_hash": tablo_hash,
            "yeniden": False}
    sonuclar: list = []

    def topla(s):
        sonuclar.extend(s["sonuc"])
    ham_sonuc = we.havuz_calistir(_isci, gruplar, surec, _baslat, ayar, butce_sn, ilerleme, "v2 ham", her_sonuc=topla)
    erte = sum(s["ertelendi"] for s in ham_sonuc)
    yap = [m for m in sonuclar if not m.get("atlandi")]
    hata = [m for m in yap if m.get("hata") and not m.get("veri_yok")]
    ozet = {"toplam": toplam, "kalan_basta": kalan, "yapilan": len(yap), "ertelenen": erte,
            "veri_yok": sum(1 for m in yap if m.get("veri_yok")), "hata": len(hata),
            "hata_ornegi": hata[0]["hata"] if hata else ""}
    if ilerleme:
        print(f"[v2 ham] {ozet}", flush=True)
    return ozet


# ============================================================================ okuma (eleme/sonraki aşamalar için)
def ham_yan_denetle(cikti: Path, carpan: float, ad: str, tf: str, evren: tuple, tablo_hash: str, eski_kabul: Optional[bool] = None,
                    veri_al=None) -> dict:
    """Parquet okumadan yalnız yan dosyaları denetler (var mı, maliyet, holdout, kimlik damgası + VERİ özeti). -> {sembol: meta}.
    veri_al(sembol, tf) -> (mumlar, funding) ZORUNLU (damgalı yan dosya için; yoksa kimlik_farki ValueError atar). Damgasız eski
    v2 yan dosyasında veri özeti yoktur: yalnız eski_kabul=True / V2_ESKI_YAN_DOSYA=1 ile okunur, veri_al gerekmez."""
    hd = Path(cikti) / "ham" / carpan_adi(carpan)
    metalar = {}
    for s in evren:
        yan = dosya_yolu(hd, ad, tf, s).with_suffix(".json")
        if not yan.exists():
            raise RuntimeError(f"ham koşu bitmemiş: {yan.name} ({carpan_adi(carpan)})")
        m = json.loads(yan.read_text())
        if m.get("maliyet_hash") != tablo_hash:
            raise RuntimeError(f"{yan.name}: başka bir maliyet tablosuyla yapılmış")
        if not m.get("veri_yok") and m.get("veri_bit") and zaman_utc(m["veri_bit"]) >= sabit.HOLDOUT_BAS:
            raise HoldoutSizintisi(f"{yan.name}: veri_bit {m['veri_bit']} HOLDOUT_BAS ve sonrası")
        vs = _YOK
        if veri_al is not None and any(a in m for a in DAMGA_ALANLARI):
            vs = veri_ozeti_simdi(veri_al, s, tf)
        kimlik_dogrula(m, ad, "swing", yan.name, eski_kabul, vs)
        metalar[s] = m
    return metalar


def veri_ozetleri_ozeti(metalar: dict) -> dict:
    """{sembol: veri_sha256} — yalnız veri olan ve hatasız semboller (ham_yukle bilgisindeki 'veri_sha256' ile aynı küme)."""
    return {s: m.get("veri_sha256") for s, m in metalar.items() if not m.get("veri_yok") and not m.get("hata")}


def ham_yukle(cikti: Path, carpan: float, ad: str, tf: str, evren: tuple, tablo_hash: str, eski_kabul: Optional[bool] = None,
              veri_al=None) -> tuple:
    """-> ({sembol: ham df}, bilgi). Yan dosyası olmayan görev varsa RuntimeError('ham koşu bitmemiş'). Bilgi: disarida (veri
    yok), hatali (hata veren semboller), veri_bas/veri_bit, n_hata, ornek. Maliyet hash'i / kimlik damgası (strateji, motor, commit,
    VERİ) / holdout sızıntısı kontrol edilir. veri_al(sembol, tf) -> (mumlar, funding) ZORUNLU (B16: veri özeti yeniden hesaplanıp
    karşılaştırılır; verilmezse ValueError). Yalnız damgasız eski v2 dosyası eski_kabul=True / V2_ESKI_YAN_DOSYA=1 ile veri_al'sız okunur."""
    metalar = ham_yan_denetle(cikti, carpan, ad, tf, evren, tablo_hash, eski_kabul, veri_al)
    hd = Path(cikti) / "ham" / carpan_adi(carpan)
    ham, bilgi = {}, {"disarida": [], "hatali": [], "veri_bas": {}, "veri_bit": {}, "hata_ornegi": "", "ayar": ""}
    for s in evren:
        m = metalar[s]
        if m.get("veri_yok"):
            bilgi["disarida"].append(s)
            continue
        if m.get("hata"):
            bilgi["hatali"].append(s)
            bilgi["hata_ornegi"] = bilgi["hata_ornegi"] or m["hata"]
            continue
        ham[s] = pd.read_parquet(dosya_yolu(hd, ad, tf, s))
        bilgi["veri_bas"][s] = zaman_utc(m["veri_bas"])
        bilgi["veri_bit"][s] = zaman_utc(m["veri_bit"])
        bilgi.setdefault("veri_sha256", {})[s] = m.get("veri_sha256")
        bilgi["ayar"] = m.get("ayar", "")
    return ham, bilgi


def pf_yukle(cikti: Path, carpan: float, ad: str, tablo_hash: str, eski_kabul: Optional[bool] = None, pf_veri_al=None,
             evren_adi: str = "genel") -> tuple:
    """-> (günlük DataFrame(gun, getiri, dengeleme) | None, meta). Hata/yan dosya yoksa: (None, meta) / RuntimeError.
    pf_veri_al(evren_adi) -> (v, f, dis) ZORUNLU (damgalı yan dosya için; veri özeti yeniden hesaplanır, B16)."""
    yol = dosya_yolu(Path(cikti) / "ham" / carpan_adi(carpan), ad, "1d", PF_SEMBOL)
    yan = yol.with_suffix(".json")
    if not yan.exists():
        raise RuntimeError(f"ham koşu bitmemiş: {yan.name} ({carpan_adi(carpan)})")
    m = json.loads(yan.read_text())
    if m.get("maliyet_hash") != tablo_hash:
        raise RuntimeError(f"{yan.name}: başka bir maliyet tablosuyla yapılmış")
    if m.get("veri_bit") and zaman_utc(m["veri_bit"]) >= sabit.HOLDOUT_BAS:
        raise HoldoutSizintisi(f"{yan.name}: veri_bit {m['veri_bit']} HOLDOUT_BAS ve sonrası")
    vs = _YOK
    if pf_veri_al is not None and any(a in m for a in DAMGA_ALANLARI):
        vs = pf_veri_ozeti_simdi(pf_veri_al, evren_adi)
    kimlik_dogrula(m, ad, "portfoy", yan.name, eski_kabul, vs)
    if m.get("hata"):
        return None, m
    return pd.read_parquet(yol), m


def mtm_yukle(cikti: Path, carpan: float, ad: str, tf: str, sembol: str) -> pd.DataFrame:
    return pd.read_parquet(dosya_yolu(Path(cikti) / "mtm" / carpan_adi(carpan), ad, tf, sembol))
