"""B4 formasyon / fiyat eylemi aileleri için ortak çekirdekler (taban sınıflar) ve yardımcılar.

Tasarım: her taban sınıf yalnız LONG çekirdeği (`_uzun`) yazar; short, fiyatı aynalanmış (yüksek <-> -dusuk,
kapanis -> -kapanis ...) mum tablosunda aynı çekirdeği çalıştırıp sonucu geri çevirerek elde edilir. Böylece
long/short simetrik ve tek kodla test edilir. Stil sınıfları (swing/daytrade/scalp dosyaları) yalnız ad, stil ve
varsayılan/ızgara parametrelerini verir; daytrade'de gün sonu çıkışı taban sınıfta uygulanır.

Hepsi nedensel: t. satırdaki sinyal yalnız t. mum KAPANIŞINA kadar olan veriye dayanır (pivotlar onay mumundan
sonra, üst TF mumları kapandıktan sonra kullanılır).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import gun_sonu_uygula, onceki_seans_hlc, seans_kimligi
from motor.strateji.htf import ust_zaman
from motor.strateji.pivotlar import pivot_tablosu
from motor.strateji.temel import Strateji


# ------------------------------------------------------------------ yardımcılar
def ayna(m: pd.DataFrame) -> pd.DataFrame:
    """Fiyat aynası: long çekirdeği short için yeniden kullanmak üzere."""
    d = pd.DataFrame({"acilis": -m["acilis"], "yuksek": -m["dusuk"], "dusuk": -m["yuksek"],
                      "kapanis": -m["kapanis"]}, index=m.index)
    for c in m.columns:
        if c not in d.columns:
            d[c] = m[c]
    return d


def atr_serisi(m: pd.DataFrame, periyot: int = 14) -> pd.Series:
    return g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(periyot))


def hacim_gecerli(m: pd.DataFrame, pencere: int, k: float) -> pd.Series:
    """hacim > k * önceki `pencere` mumun ortalama hacmi. k<=0, hacim yok veya hep 0 ise filtre yok (True)."""
    bos = pd.Series(True, index=m.index)
    if k <= 0 or "hacim" not in m.columns or not (m["hacim"] > 0).any():
        return bos
    ort = m["hacim"].shift(1).rolling(int(pencere), min_periods=int(pencere)).mean()
    return (m["hacim"] > k * ort).fillna(False)


def ust_trend_uzun(m: pd.DataFrame, ust_tf: str, ema_periyot: int) -> pd.Series:
    """Üst TF'de kapanış > EMA ise True (lookahead'siz). ust_tf boş ise hep True.
    Alt TF üst TF'nin tam katı değilse ValueError (lider kararı: filtre asla sessizce kapanmaz)."""
    bos = pd.Series(True, index=m.index)
    if not ust_tf:
        return bos
    r = ust_zaman(m, ust_tf, lambda u: pd.DataFrame(
        {"d": (u["kapanis"] > g.ema(u["kapanis"], int(ema_periyot))).astype(float)
         .where(g.ema(u["kapanis"], int(ema_periyot)).notna())}))
    return (r["d"] == 1.0)


def heikin_ashi(m: pd.DataFrame):
    o, h, l, c = (m[x].to_numpy(float) for x in ("acilis", "yuksek", "dusuk", "kapanis"))
    hc = (o + h + l + c) / 4.0
    ho = np.empty(len(m))
    if len(m):
        ho[0] = (o[0] + c[0]) / 2.0
    for i in range(1, len(m)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2.0
    return ho, hc


def bekleyen_tetik(kurulum, seviye, iptal, kap, gecerlilik):
    """Kurulum mumunda (j) bir tetik `seviye[j]` belirlenir; sonraki `gecerlilik` mum içinde kapanış seviyenin
    üstüne çıkarsa tetik (ilk kez), kapanış `iptal[j]` altına inerse kurulum iptal. Yeni kurulum eskiyi değiştirir.
    -> (tetik bool[n], kaynak int[n] kurulum indeksi veya -1)"""
    n = len(kap)
    tetik = np.zeros(n, dtype=bool)
    kaynak = np.full(n, -1, dtype=np.int64)
    j = -1
    for t in range(n):
        if j >= 0:
            if t - j > gecerlilik or kap[t] < iptal[j]:
                j = -1
            elif kap[t] > seviye[j]:
                tetik[t] = True
                kaynak[t] = j
                j = -1
        if kurulum[t] and not np.isnan(seviye[t]) and not np.isnan(iptal[t]):
            j = t
    return tetik, kaynak


def _calisma_uzunlugu(b: np.ndarray) -> np.ndarray:
    """Ardışık True sayısı (her konumda biten seri uzunluğu)."""
    r = np.zeros(len(b), dtype=np.int64)
    sayac = 0
    for i, x in enumerate(b):
        sayac = sayac + 1 if x else 0
        r[i] = sayac
    return r


# ------------------------------------------------------------------ taban
class B4Taban(Strateji):
    """Ortak: long çekirdeği + ayna short + doğrulama + (daytrade) gün sonu."""
    atr_ortak = {"atr_periyot": 14, "long": True, "short": True}

    def _uzun(self, m: pd.DataFrame):
        """-> (ok bool[n], stop float[n], hedef float[n]) yalnız LONG için."""
        raise NotImplementedError

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        n = len(mumlar)
        kap = mumlar["kapanis"].to_numpy(float)
        ok_l = np.zeros(n, dtype=bool)
        ok_s = np.zeros(n, dtype=bool)
        st_l = st_s = h_l = h_s = np.full(n, np.nan)
        if p.get("long", True):
            ok_l, st_l, h_l = self._uzun(mumlar)
        if p.get("short", True):
            ok_s, st_s, h_s = self._uzun(ayna(mumlar))
            st_s, h_s = -st_s, -h_s
        with np.errstate(invalid="ignore"):
            ok_l = ok_l & np.isfinite(st_l) & (st_l < kap) & (np.isnan(h_l) | (h_l > kap))
            ok_s = ok_s & np.isfinite(st_s) & (st_s > kap) & (np.isnan(h_s) | (h_s < kap)) & ~ok_l
        yon = np.where(ok_l, 1, np.where(ok_s, -1, 0)).astype("int64")
        stop = np.where(ok_l, st_l, np.where(ok_s, st_s, np.nan))
        hedef = np.where(ok_l, h_l, np.where(ok_s, h_s, np.nan))
        sig = pd.DataFrame({"yon": yon, "stop": stop, "hedef": hedef,
                            "cikis": np.zeros(n, dtype=bool)}, index=mumlar.index)
        if self.stil == "daytrade":
            sig = gun_sonu_uygula(sig, p.get("seans_saat", 0.0))
        return sig

    def cikis_var_mi(self) -> bool:
        """Hedef (R, karşı uç veya ölçü) her işlemde var; daytrade'de ayrıca gün sonu."""
        return True


# ------------------------------------------------------------------ 1. sahte kırılım
class SahteKirilimTaban(B4Taban):
    """Aralık dışına delme, `geri_don_mum` mum içinde içeri kapanış -> ters yön (long çekirdeği: alt sınır sahte kırılımı)."""
    varsayilan_parametreler = {
        "pencere": 40, "geri_don_mum": 3, "min_genislik_atr": 3.0, "maks_genislik_atr": 20.0,
        "kir_atr": 0.0, "kapanis_disi": False, "onay_mumu": True, "min_dokunus": 0, "bant": 0.15,
        "adx_esik": 0.0, "adx_periyot": 14, "tampon_atr": 0.25, "hedef_modu": "karsi", "hedef_r": 2.0,
        "min_rr": 1.0, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        ac, yu, du, kap = (m[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        W, M = int(p["pencere"]), int(p["geri_don_mum"])
        atr = atr_serisi(m, p["atr_periyot"])
        ust = yu.shift(1).rolling(W, min_periods=W).max()
        alt = du.shift(1).rolling(W, min_periods=W).min()
        gen = ust - alt
        uygun = (gen >= p["min_genislik_atr"] * atr) & (gen <= p["maks_genislik_atr"] * atr)
        if p["adx_esik"] > 0:
            uygun = uygun & (g.adx(yu, du, kap, int(p["adx_periyot"]))["adx"] < p["adx_esik"])
        tamp = p["tampon_atr"] * atr
        onay = (kap > ac) if p["onay_mumu"] else pd.Series(True, index=m.index)
        ok = np.zeros(n, dtype=bool)
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        dsec = np.zeros(n, dtype=np.int64)
        for d in range(1, M + 1):
            alt_j, ust_j, atr_j = alt.shift(d), ust.shift(d), atr.shift(d)
            delik = du.shift(d) < alt_j - p["kir_atr"] * atr_j
            if p["kapanis_disi"]:
                delik = delik & (kap.shift(d) < alt_j)
            c = uygun.shift(d, fill_value=False) & delik & (kap > alt_j) & onay
            st = du.rolling(d + 1, min_periods=d + 1).min() - tamp
            risk = kap - st
            h = ust_j if p["hedef_modu"] == "karsi" else kap + p["hedef_r"] * risk
            c = c & (risk > 0) & ((h - kap) >= p["min_rr"] * risk)
            sel = c.to_numpy() & ~ok
            ok[sel] = True
            stop[sel] = st.to_numpy()[sel]
            hedef[sel] = h.to_numpy()[sel]
            dsec[sel] = d
        # bekleme (aynı sahte kırılım tekrar sinyal vermesin) ve dokunuş sayısı
        du_n, alt_n, gen_n = du.to_numpy(), alt.to_numpy(), gen.to_numpy()
        son = -10 ** 9
        for t in np.flatnonzero(ok):
            if t - son <= M:
                ok[t] = False
                continue
            if p["min_dokunus"] > 0:
                j = t - dsec[t]
                temas = du_n[j - W:j] <= alt_n[j] + p["bant"] * gen_n[j]
                sayi = int(temas[0]) + int(np.sum(temas[1:] & ~temas[:-1]))
                if sayi < p["min_dokunus"]:
                    ok[t] = False
                    continue
            son = t
        return ok, stop, hedef


# ------------------------------------------------------------------ 2. seviye tepki
class SeviyeTepkiTaban(B4Taban):
    """Destek seviyesine temas + red mumu / Heikin Ashi dönüşü -> long (short aynası: direnç).
    seviye_tipi: onceki_seans (önceki seans dibi), pivot (>=2 dokunuşlu yatay dip), yuvarlak (50/100 tipi)."""
    varsayilan_parametreler = {
        "seviye_tipi": "pivot", "tolerans_atr": 0.3, "delik_atr": 0.5, "tepki_modu": "red", "tepki_pencere": 1,
        "fitil_oran": 0.4, "pivot_yontemi": "fraktal", "pivot_k": 3, "zigzag_esik_k": 2.0, "cift_tol_atr": 1.0,
        "yuvarlak_carpan": 1.0, "seans_saat": 0.0, "tampon_atr": 0.25, "hedef_r": 2.0, "maks_risk_atr": 4.0,
        **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        ac, yu, du, kap = (m[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = atr_serisi(m, p["atr_periyot"])
        pen = max(1, int(p["tepki_pencere"]))
        if p["tepki_modu"] == "ha":
            pen = max(pen, 3)          # HA dönüşü seviyeye temastan 1-2 mum sonra gelebilir
        tmin = du.rolling(pen, min_periods=pen).min()
        tip = p["seviye_tipi"]
        if tip == "onceki_seans":
            lvl = onceki_seans_hlc(m, seans_kimligi(m.index, p["seans_saat"]))["l"]
        elif tip == "pivot":
            pv = pivot_tablosu(m, p["pivot_yontemi"], int(p["pivot_k"]), int(p["atr_periyot"]), p["zigzag_esik_k"])
            sf, of = pv["son_dip_fiyat"], pv["onceki_dip_fiyat"]
            lvl = np.minimum(sf, of).where((sf - of).abs() <= p["cift_tol_atr"] * atr)
        elif tip == "yuvarlak":
            adim = 10.0 ** (np.floor(np.log10(kap.abs().clip(lower=1e-12))) - 1.0) * p["yuvarlak_carpan"]
            lvl = np.rint(tmin / adim) * adim
        else:
            raise ValueError(f"Bilinmeyen seviye_tipi: {tip}")
        yakin = (tmin <= lvl + p["tolerans_atr"] * atr) & (tmin >= lvl - p["delik_atr"] * atr)
        if p["tepki_modu"] == "ha":
            ho, hc = heikin_ashi(m)
            hs = pd.Series(hc > ho, index=m.index)
            tepki = hs & ~hs.shift(1, fill_value=True)
        else:
            rng = yu - du
            alt_fitil = np.minimum(ac, kap) - du
            tepki = (kap > ac) & (rng > 0) & (alt_fitil >= p["fitil_oran"] * rng)
        ok = (yakin & (kap > lvl) & tepki).fillna(False)
        stop = np.minimum(tmin, lvl) - p["tampon_atr"] * atr
        risk = kap - stop
        ok = ok & (risk > 0) & (risk <= p["maks_risk_atr"] * atr)
        hedef = kap + p["hedef_r"] * risk
        return ok.to_numpy(), stop.to_numpy(), hedef.to_numpy()


# ------------------------------------------------------------------ 3. talep / arz bölgesi
def talep_bolgeleri(m: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Her mum kapanışında aktif TALEP bölgesi (en son oluşan, kırılmamış, süresi dolmamış): prox, dist, id."""
    n = len(m)
    ac, yu, du, kap = (m[c].to_numpy(float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
    atr = atr_serisi(m, p["atr_periyot"]).to_numpy()
    rng = yu - du
    with np.errstate(invalid="ignore", divide="ignore"):
        oran = np.where(rng > 0, np.abs(kap - ac) / rng, 0.0)
    heyecan = pd.Series((oran >= p["heyecan_govde"]).astype(float))
    baz = pd.Series(((oran <= p["baz_govde"]) & (rng > 0)).astype(float))
    atr_onc = np.r_[np.nan, atr[:-1]]
    with np.errstate(invalid="ignore"):
        cikis = (heyecan.to_numpy() == 1.0) & (kap > ac) & (rng >= p["itki_atr"] * atr_onc)
    ust_g = pd.Series(np.maximum(ac, kap))
    du_s = pd.Series(du)
    olustu = np.zeros(n, dtype=bool)
    prox_f = np.full(n, np.nan)
    dist_f = np.full(n, np.nan)
    for b in range(1, int(p["baz_maks"]) + 1):
        bazb = baz.shift(1).rolling(b, min_periods=b).min().to_numpy() == 1.0
        girdi = heyecan.shift(b + 1).to_numpy() == 1.0
        prx = ust_g.shift(1).rolling(b, min_periods=b).max().to_numpy()
        dst = du_s.shift(1).rolling(b, min_periods=b).min().to_numpy()
        with np.errstate(invalid="ignore"):
            sel = cikis & bazb & girdi & (prx > dst) & ~olustu
        olustu[sel] = True
        prox_f[sel], dist_f[sel] = prx[sel], dst[sel]
    o_prox = np.full(n, np.nan)
    o_dist = np.full(n, np.nan)
    o_id = np.full(n, np.nan)
    aktif = False
    prox = dist = np.nan
    dogum = 0
    zid = 0
    omur = int(p["omur"])
    for t in range(n):
        if aktif and (kap[t] < dist or t - dogum > omur):
            aktif = False
        if olustu[t]:
            aktif, prox, dist, dogum = True, prox_f[t], dist_f[t], t
            zid += 1
        if aktif:
            o_prox[t], o_dist[t], o_id[t] = prox, dist, zid
    return pd.DataFrame({"prox": o_prox, "dist": o_dist, "id": o_id}, index=m.index)


class TalepArzBolgesiTaban(B4Taban):
    """DBR/RBR talep bölgesi (baz mumu + heyecan verici çıkış), bölgeye dönüşte tuzak mum kırılımı / tepki mumu -> long."""
    varsayilan_parametreler = {
        "heyecan_govde": 0.7, "baz_govde": 0.4, "baz_maks": 2, "itki_atr": 2.0, "omur": 150,
        "giris_modu": "tuzak", "hacim_onay": True, "stop_modu": "bolge", "tampon_atr": 0.25,
        "hedef_r": 2.0, "maks_risk_atr": 5.0, "ust_tf": "", **B4Taban.atr_ortak,
    }

    def _bolgeler(self, m):
        p = self.parametreler
        if p["ust_tf"]:
            return ust_zaman(m, p["ust_tf"], lambda u: talep_bolgeleri(u, p))
        return talep_bolgeleri(m, p)

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        ac, yu, du, kap = (m[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = atr_serisi(m, p["atr_periyot"])
        z = self._bolgeler(m)
        tamp = p["tampon_atr"] * atr
        if p["giris_modu"] == "tuzak":
            prox, dist, zid = z["prox"].shift(2), z["dist"].shift(2), z["id"].shift(2)
            kirmizi = kap.shift(1) < ac.shift(1)
            temas = (du.shift(1) <= prox) & (kap.shift(1) >= dist)
            ok = kirmizi & temas & (kap > yu.shift(1))
            if p["hacim_onay"] and "hacim" in m.columns and (m["hacim"] > 0).any():
                ok = ok & (m["hacim"].shift(1) > m["hacim"].shift(2))
            alt_u = pd.concat([du, du.shift(1)], axis=1).min(axis=1)
            stop = (dist if p["stop_modu"] == "bolge" else alt_u) - tamp
        else:
            prox, dist, zid = z["prox"].shift(1), z["dist"].shift(1), z["id"].shift(1)
            ok = (du <= prox) & (kap >= dist) & (kap > ac)
            if p["hacim_onay"] and "hacim" in m.columns and (m["hacim"] > 0).any():
                ok = ok & (m["hacim"] > m["hacim"].shift(1))
            stop = dist - tamp
        risk = kap - stop
        ok = (ok & (risk > 0) & (risk <= p["maks_risk_atr"] * atr)).fillna(False).to_numpy().copy()
        hedef = (kap + p["hedef_r"] * risk).to_numpy()
        zid_n = zid.to_numpy()
        kullanilan = set()
        for t in np.flatnonzero(ok):       # bölge başına tek işlem
            if zid_n[t] in kullanilan:
                ok[t] = False
            else:
                kullanilan.add(zid_n[t])
        return ok, stop.to_numpy(), hedef


# ------------------------------------------------------------------ 4. trend çizgisi / kanal
def regresyon_kanal(kap: pd.Series, W: int):
    """Kayan lineer regresyon: (uc_deger, egim, sd, r2) — hepsi pencere sonunda, nedensel."""
    y = kap.to_numpy(float)
    n = len(y)
    x = np.arange(W) - (W - 1) / 2.0
    sxx = float(np.sum(x * x))
    sxy = np.full(n, np.nan)
    if n >= W:
        sxy[W - 1:] = np.correlate(y, x, mode="valid")
    egim = sxy / sxx
    ort = kap.rolling(W, min_periods=W).mean().to_numpy()
    uc = ort + egim * (W - 1) / 2.0
    syy = kap.rolling(W, min_periods=W).var().to_numpy() * (W - 1)
    sse = np.maximum(syy - egim * sxy, 0.0)
    sd = np.sqrt(sse / W)
    with np.errstate(invalid="ignore", divide="ignore"):
        r2 = np.where(syy > 0, 1.0 - sse / syy, 0.0)
    return uc, egim, sd, r2


class TrendCizgisiKanalTaban(B4Taban):
    """Regresyon kanalı. mod 'tepki': yükselen kanalın alt çizgisine temas + tepki -> long; hedef üst çizgi.
    mod 'kirilim': düşen kanalın üst çizgisini yukarı kapanışla kırma -> long (trend çizgisi kırılımı)."""
    varsayilan_parametreler = {
        "mod": "tepki", "regresyon": 50, "kanal_sd": 2.0, "r2_esik": 0.5, "min_egim_atr": 1.0,
        "egim_sart": True, "tolerans_atr": 0.3, "min_kanal_atr": 2.0, "tampon_atr": 0.25,
        "hedef_r": 2.0, "min_rr": 1.0, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        ac, yu, du, kap = (m[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = atr_serisi(m, p["atr_periyot"])
        W = int(p["regresyon"])
        uc, egim, sd, r2 = regresyon_kanal(kap, W)
        uc, egim, sd, r2 = (pd.Series(a, index=m.index) for a in (uc, egim, sd, r2))
        alt = uc - p["kanal_sd"] * sd
        ust = uc + p["kanal_sd"] * sd
        egim_atr = egim * W / atr
        temiz = (r2 >= p["r2_esik"]) & ((ust - alt) >= p["min_kanal_atr"] * atr)
        tamp = p["tampon_atr"] * atr
        if p["mod"] == "tepki":
            trend = (egim_atr >= p["min_egim_atr"]) if p["egim_sart"] else pd.Series(True, index=m.index)
            ok = temiz & trend & (du <= alt + p["tolerans_atr"] * atr) & (kap > ac) & (kap > alt)
            stop = np.minimum(du, alt) - tamp
            risk = kap - stop
            hedef = ust
            ok = ok & (risk > 0) & ((hedef - kap) >= p["min_rr"] * risk)
        else:
            trend = egim_atr <= -p["min_egim_atr"]
            once = kap.shift(1) <= ust.shift(1)
            ok = temiz & trend & (kap > ust) & once & (kap > ac)
            stop = uc - tamp
            risk = kap - stop
            hedef = kap + p["hedef_r"] * risk
            ok = ok & (risk > 0)
        return ok.fillna(False).to_numpy(), stop.to_numpy(), hedef.to_numpy()


# ------------------------------------------------------------------ 5. üçgen / dikdörtgen
class UcgenDikdortgenTaban(B4Taban):
    """Son iki onaylı tepe ve iki dipten çizilen sınır çizgileri; yükselen üçgen / simetrik üçgen / dikdörtgen
    üst sınırının yukarı kırılımı -> long (aynası: alçalan üçgen / simetrik / dikdörtgen alt sınır -> short).
    `ucgen` yükselen (long) / alçalan (short) üçgeni açar."""
    varsayilan_parametreler = {
        "pivot_yontemi": "fraktal", "pivot_k": 3, "zigzag_esik_k": 2.0, "pencere": 45, "yatay_tol_atr": 1.0,
        "ucgen": True, "simetrik": True, "dikdortgen": True, "tampon_atr": 0.1, "hacim_k": 0.0, "hacim_pencere": 20,
        "stop_modu": "karsi_uc", "stop_tampon_atr": 0.25, "min_risk_atr": 1.0, "hedef_olcu": 1.0, "min_rr": 1.0,
        "min_genislik_atr": 1.0, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        kap = m["kapanis"].to_numpy(float)
        atr = atr_serisi(m, p["atr_periyot"]).to_numpy()
        pv = pivot_tablosu(m, p["pivot_yontemi"], int(p["pivot_k"]), int(p["atr_periyot"]), p["zigzag_esik_k"])
        stf, sti, otf, oti = (pv[c].to_numpy() for c in
                              ("son_tepe_fiyat", "son_tepe_idx", "onceki_tepe_fiyat", "onceki_tepe_idx"))
        sdf, sdi, odf, odi = (pv[c].to_numpy() for c in
                              ("son_dip_fiyat", "son_dip_idx", "onceki_dip_fiyat", "onceki_dip_idx"))
        t = np.arange(n, dtype=float)
        with np.errstate(invalid="ignore", divide="ignore"):
            yat = p["yatay_tol_atr"] * atr
            up_flat = np.abs(stf - otf) <= yat
            up_fall = (stf - otf) < -yat
            lo_flat = np.abs(sdf - odf) <= yat
            lo_rise = (sdf - odf) > yat
            i0 = np.minimum(oti, odi)
            taze = i0 >= t - p["pencere"]

            def ust_c(tt):
                return np.where(up_flat, np.maximum(stf, otf), stf + (stf - otf) / (sti - oti) * (tt - sti))

            def alt_c(tt):
                return np.where(lo_flat, np.minimum(sdf, odf), sdf + (sdf - odf) / (sdi - odi) * (tt - sdi))

            ust_t, alt_t = ust_c(t), alt_c(t)
            ust_p = ust_c(t - 1)
            yuk0 = ust_c(i0) - alt_c(i0)
            tip = ((up_flat & lo_rise & bool(p["ucgen"])) | (up_fall & lo_rise & bool(p["simetrik"]))
                   | (up_flat & lo_flat & bool(p["dikdortgen"])))
            tamp = p["tampon_atr"] * atr
            onc_kap = np.r_[np.nan, kap[:-1]]
            ok = (tip & taze & (ust_t - alt_t >= p["min_genislik_atr"] * atr) & (yuk0 > 0)
                  & (kap > ust_t + tamp) & (onc_kap <= ust_p + tamp))
            ok &= hacim_gecerli(m, p["hacim_pencere"], p["hacim_k"]).to_numpy()
            alt_stop = alt_t if p["stop_modu"] == "karsi_uc" else (ust_t + alt_t) / 2.0
            stop = np.minimum(alt_stop - p["stop_tampon_atr"] * atr, kap - p["min_risk_atr"] * atr)
            risk = kap - stop
            hedef = ust_t + p["hedef_olcu"] * yuk0
            ok &= (risk > 0) & ((hedef - kap) >= p["min_rr"] * risk)
        return np.nan_to_num(ok, nan=0).astype(bool), stop, hedef


# ------------------------------------------------------------------ 6. witch hat
class WitchHatTaban(B4Taban):
    """Witch Hat (Landry) long çekirdeği = kitabın short kuralının aynası: yükseliş trendinde pivot DİP, yukarı
    sert hareket (tepe M), fiyat pivot dibine geri döner ('brim'), kırılan dünkü yükseğin üstü -> long.
    Short (kitabın asıl kuralı): trend aşağı, pivot tepe, sert düşüş, tepeye dönüş, dünkü düşüğün altı."""
    varsayilan_parametreler = {
        "hareket_atr": 5.0, "yakin_atr": 0.5, "min_mesafe": 4, "maks_mesafe": 40, "pivot_k": 1,
        "trend_ema": 50, "ema_egim_bak": 10, "tampon_atr": 0.1, "min_rr": 1.0, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        yu, du, kap = (m[c].to_numpy(float) for c in ("yuksek", "dusuk", "kapanis"))
        atr = atr_serisi(m, p["atr_periyot"]).to_numpy()
        pv = pivot_tablosu(m, "fraktal", int(p["pivot_k"]))
        pf, pi = pv["son_dip_fiyat"].to_numpy(), pv["son_dip_idx"].to_numpy()
        ok = np.zeros(n, dtype=bool)
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        if int(p["trend_ema"]) > 0:
            e = g.ema(m["kapanis"], int(p["trend_ema"]))
            trend = ((m["kapanis"] > e) & (e > e.shift(int(p["ema_egim_bak"])))).to_numpy()
        else:
            trend = np.ones(n, dtype=bool)
        yu_s = yu
        kullanilan = -1
        for t in range(2, n):
            P = pf[t - 1]
            if np.isnan(P) or np.isnan(atr[t - 1]) or not trend[t - 1]:
                continue
            j = int(pi[t - 1])
            mesafe = (t - 1) - j
            if mesafe < p["min_mesafe"] or mesafe > p["maks_mesafe"] or j == kullanilan:
                continue
            if not (du[t - 1] <= P + p["yakin_atr"] * atr[t - 1] and kap[t - 1] >= P - p["yakin_atr"] * atr[t - 1]):
                continue
            if not kap[t] > yu[t - 1]:
                continue
            M = np.max(yu_s[j:t - 1])
            if M - P < p["hareket_atr"] * atr[t - 1]:
                continue
            st = min(P, du[t - 1]) - p["tampon_atr"] * atr[t - 1]
            risk = kap[t] - st
            if risk <= 0 or (M - kap[t]) < p["min_rr"] * risk:
                continue
            ok[t], stop[t], hedef[t] = True, st, M
            kullanilan = j
        return ok, stop, hedef


# ------------------------------------------------------------------ 7. geri çekilme fiyat eylemi
class GeriCekilmeTaban(B4Taban):
    """Güçlü yükseliş trendinde (ADX + EMA) 2-3 ardışık karşı (kapanış<açılış) mumdan oluşan zayıf geri çekilme;
    ilk yeşil mum önceki (karşı) mumun yükseğini kapanışla aşınca long. Stop geri çekilme dibi."""
    varsayilan_parametreler = {
        "geri_min": 2, "geri_maks": 5, "adx_esik": 25.0, "adx_periyot": 14, "trend_ema": 50, "ema_egim_bak": 10,
        "zayif": True, "maks_derinlik_atr": 4.0, "geri_bak": 10, "tampon_atr": 0.25, "hedef_modu": "r",
        "hedef_r": 2.0, "min_rr": 1.0, "ust_tf": "", "ust_ema": 50, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        ac, yu, du, kap = (m[c].to_numpy(float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = atr_serisi(m, p["atr_periyot"]).to_numpy()
        adx = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], int(p["adx_periyot"]))["adx"].to_numpy()
        e = g.ema(m["kapanis"], int(p["trend_ema"]))
        guclu = (m["kapanis"] > e) & (e > e.shift(int(p["ema_egim_bak"]))) & (adx >= p["adx_esik"])
        guclu = pd.Series(guclu.to_numpy(), index=m.index) & ust_trend_uzun(m, p["ust_tf"], p["ust_ema"])
        guclu = guclu.fillna(False).to_numpy()
        karsi = kap < ac
        rl = _calisma_uzunlugu(karsi)
        rng = yu - du
        tb = karsi & (np.abs(kap - ac) > 0.5 * rng)
        iki_tb = np.cumsum(tb & np.r_[False, tb[:-1]])
        ok = np.zeros(n, dtype=bool)
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        gb = int(p["geri_bak"])
        for t in range(2, n):
            r = rl[t - 1]
            if not (p["geri_min"] <= r <= p["geri_maks"]) or not guclu[t - 1] or np.isnan(atr[t]):
                continue
            if not (kap[t] > ac[t] and kap[t] > yu[t - 1]):
                continue
            a = t - r                              # geri çekilmenin ilk mumu
            if p["zayif"] and iki_tb[t - 1] - iki_tb[a] > 0:
                continue
            pb_dip = np.min(du[a:t + 1])
            tepe = np.max(yu[max(0, a - gb):a + 1]) if a > 0 else yu[0]
            if tepe - pb_dip > p["maks_derinlik_atr"] * atr[t]:
                continue
            st = pb_dip - p["tampon_atr"] * atr[t]
            risk = kap[t] - st
            if risk <= 0:
                continue
            h = tepe if p["hedef_modu"] == "tepe" else kap[t] + p["hedef_r"] * risk
            if h - kap[t] < p["min_rr"] * risk:
                continue
            ok[t], stop[t], hedef[t] = True, st, h
        return ok, stop, hedef


# ------------------------------------------------------------------ 8. yeni dip sonrası dönüş
class YeniDipDonusTaban(B4Taban):
    """Landry 'ilk itiş' / Bulkowski 'ilk itiş modeli': N-mumluk yeni dipten sonra >=itis_mum ardışık yüksek
    tepe+yüksek dip, ardından tek mumluk düzeltme (daha düşük tepe ve dip); düzeltme mumunun yükseğinin üstünde
    kapanış (gecerlilik mum içinde) -> long. Stop düzeltme dibi. Short: aynası (yeni tepe)."""
    varsayilan_parametreler = {
        "dip_pencere": 120, "maks_sure": 30, "itis_mum": 2, "itki_atr": 3.0, "gecerlilik": 2,
        "tampon_atr": 0.25, "hedef_r": 2.0, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        yu, du, kap = m["yuksek"], m["dusuk"], m["kapanis"]
        atr = atr_serisi(m, p["atr_periyot"])
        hh = ((yu > yu.shift(1)) & (du > du.shift(1))).to_numpy()
        rr = _calisma_uzunlugu(hh)
        rr_onc = np.r_[0, rr[:-1]]
        pull = ((yu < yu.shift(1)) & (du < du.shift(1))).to_numpy() & (rr_onc >= int(p["itis_mum"]))
        l_son = du.shift(1).rolling(int(p["maks_sure"]), min_periods=1).min()
        l_n = du.shift(1).rolling(int(p["dip_pencere"]), min_periods=int(p["dip_pencere"])).min()
        yeni_dip = (l_son <= l_n)
        yuksel = (yu.shift(1) - l_son) >= p["itki_atr"] * atr.shift(1)
        kurulum = (pull & (yeni_dip & yuksel).fillna(False).to_numpy())
        tetik, kay = bekleyen_tetik(kurulum, yu.to_numpy(), du.to_numpy(), kap.to_numpy(), int(p["gecerlilik"]))
        du_n, atr_n, kap_n = du.to_numpy(), atr.to_numpy(), kap.to_numpy()
        stop = np.full(len(m), np.nan)
        hedef = np.full(len(m), np.nan)
        idx = np.flatnonzero(tetik)
        st = du_n[kay[idx]] - p["tampon_atr"] * atr_n[idx]
        stop[idx] = st
        hedef[idx] = kap_n[idx] + p["hedef_r"] * (kap_n[idx] - st)
        return tetik, stop, hedef


# ------------------------------------------------------------------ 9. yuvarlak dip / fincan-sap
class YuvarlakDipFincanTaban(B4Taban):
    """Fincan-sap: zigzag pivotlarıyla sol kenar (tepe), taban (dip), sağ kenar (tepe) ve sap dibi; kenarlar
    birbirine yakın, sap sığ, fincan paraboliğe uyuyor. Sağ kenarın üstünde kapanış -> long; stop sap dibi;
    hedef = kenar + hedef_olcu * fincan derinliği. Short: aynası (ters fincan / yuvarlak tepe)."""
    varsayilan_parametreler = {
        "pivot_yontemi": "zigzag", "pivot_k": 3, "zigzag_esik_k": 3.0, "min_derinlik_atr": 3.0,
        "min_genislik": 15, "maks_genislik": 150, "kenar_tol": 0.25, "sap_maks": 0.5, "yuvarlaklik": 0.6,
        "gecerlilik": 20, "tampon_atr": 0.25, "hedef_olcu": 1.0, "min_rr": 1.0, **B4Taban.atr_ortak,
    }

    def _uzun(self, m):
        p = self.parametreler
        n = len(m)
        kap = m["kapanis"].to_numpy(float)
        atr = atr_serisi(m, p["atr_periyot"]).to_numpy()
        pv = pivot_tablosu(m, p["pivot_yontemi"], int(p["pivot_k"]), int(p["atr_periyot"]), p["zigzag_esik_k"])
        c = {k: pv[k].to_numpy() for k in pv.columns}
        kurulum = np.zeros(n, dtype=bool)
        seviye = np.full(n, np.nan)
        iptal = np.full(n, np.nan)
        derinlik = np.full(n, np.nan)
        for t in np.flatnonzero(c["yeni_dip"]):
            if np.isnan(c["onceki_tepe_idx"][t]) or np.isnan(c["onceki_dip_idx"][t]) or np.isnan(atr[t]):
                continue
            a, b = int(c["onceki_tepe_idx"][t]), int(c["onceki_dip_idx"][t])
            r, s = int(c["son_tepe_idx"][t]), int(c["son_dip_idx"][t])
            if not (a < b < r < s):
                continue
            sol, taban, sag, sap = (c["onceki_tepe_fiyat"][t], c["onceki_dip_fiyat"][t],
                                    c["son_tepe_fiyat"][t], c["son_dip_fiyat"][t])
            D = sol - taban
            if D < p["min_derinlik_atr"] * atr[t] or not (p["min_genislik"] <= r - a <= p["maks_genislik"]):
                continue
            if abs(sag - sol) > p["kenar_tol"] * D or not (0 < sag - sap <= p["sap_maks"] * D) or sap <= taban:
                continue
            if p["yuvarlaklik"] > 0:
                y = kap[a:r + 1]
                x = np.linspace(-1.0, 1.0, len(y))
                kat = np.polyfit(x, y, 2)
                sst = float(np.sum((y - y.mean()) ** 2))
                if kat[0] <= 0 or sst <= 0:
                    continue
                r2 = 1.0 - float(np.sum((y - np.polyval(kat, x)) ** 2)) / sst
                if r2 < p["yuvarlaklik"]:
                    continue
            kurulum[t], seviye[t], iptal[t], derinlik[t] = True, sag, sap, D
        tetik, kay = bekleyen_tetik(kurulum, seviye, iptal, kap, int(p["gecerlilik"]))
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        idx = np.flatnonzero(tetik)
        st = iptal[kay[idx]] - p["tampon_atr"] * atr[idx]
        h = seviye[kay[idx]] + p["hedef_olcu"] * derinlik[kay[idx]]
        gecer = (kap[idx] - st > 0) & ((h - kap[idx]) >= p["min_rr"] * (kap[idx] - st))
        stop[idx], hedef[idx] = st, h
        tetik = tetik & np.isin(np.arange(n), idx[gecer])
        return tetik, stop, hedef
