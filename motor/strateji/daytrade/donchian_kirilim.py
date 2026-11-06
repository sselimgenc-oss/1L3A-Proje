"""daytrade__donchian-kirilim: 10/20 mumluk Donchian kırılımı, SMA50 trend filtreli; gün sonunda kapanır (1h).

Çekirdek swing `DonchianKirilim` ile aynıdır (türetildi): kapanış önceki `giris_n` mumun en yükseğini/en düşüğünü İLK
kez aşarsa yönde giriş; trend_ma (SMA) filtresi; stop kapanış -/+ stop_atr*ATR (backtest önerisi 2 ATR) veya karşı
kanal; çıkış: karşı `cikis_n` mum kanalının kırılması. Day trade'e özgü: 1h varsayılanları (trend_ma 50) ve UTC gün
sonu zorunlu çıkışı (seansın son mumunda giriş yok).
Kaynak kartlar: daytrade__fraktal-williams-sma50__singhal (herhangi TF; SMA50 üstünde Williams fraktal (4/4)
  tepesinin kırılımı; stop swing dibi; hedef 1:2-1:3) ve daytrade__donchian-geri-cekilme-kirilim__singhal (Donchian
  üst banda iki temas + geri çekilme sonrası kırılım; stop orta bant) — İKİ KART DA ifade edilemez (fraktal seviyesi /
  iki temas tetiği sınıfta yok) -> kart ayarı verilmedi. Aile kanonik kuralı (Donchian N=10/20 kırılımı) esas alındı.
Varsayımlar: kapanış bazlı kırılım; kanal mevcut mum hariç; N=10-40 ızgarası (kanon 10-55).
Negatif kanıt: arşivde 1S Donchian başarısız (arsiv/OZET.md §3); gün içi kırılımların çoğu sahte (Scheier).
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.swing.donchian_kirilim import DonchianKirilim as _Swing


class DonchianKirilim(GunSonu, _Swing):
    ad = "daytrade__donchian-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "giris_n": 20, "cikis_n": 10, "trend_ma": 50,
                               "seans_saat": 0.0}
    parametre_izgarasi = {
        "giris_n": [10, 20, 40],
        "cikis_n": [5, 10],
        "stop_atr": [1.5, 2.0, 3.0],
    }
