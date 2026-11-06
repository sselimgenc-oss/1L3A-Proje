"""scalp__talep-arz-bolgesi — saatlik talep/arz bölgesinde 15m tuzak mum kırılımı.

Kural (çekirdek `formasyon_b4.TalepArzBolgesiTaban`):
  Talep bölgesi: leg-in (heyecan verici mum: gövde >= heyecan_govde*aralık) + 1..baz_maks baz mumu (gövde <= baz_govde*aralık)
  + leg-out (yeşil heyecan verici mum, aralık >= itki_atr*ATR). Proximal = baz gövdelerinin en yükseği, distal = baz
  dipleri en düşüğü (DBR ve RBR aynı kural). Bölge kapanış distalın altına inerse veya `omur` mum geçerse ölür; her bölgede
  en fazla bir işlem. giris_modu='tuzak': bölgeye (proximal) temas eden kırmızı mum (satıcı tuzak mumu, hacmi önceki
  mumdan büyük: hacim_onay) ve bir sonraki mumun kapanışı onun yükseğini aşar -> long; 'tepki': mum proximale dokunur,
  distal üstünde yeşil kapanır. Stop = distal (stop_modu='bolge') veya tuzak mum dibi ('tuzak') - tampon_atr*ATR; hedef =
  hedef_r*R (risk <= maks_risk_atr*ATR). ust_tf doluysa bölgeler üst TF'de bulunur (htf.ust_zaman, lookahead'siz) ve
  alt TF'de giriş aranır; alt TF üst TF'nin tam katı değilse üst TF atlanıp kendi TF kullanılır. Short: arz (ayna).
Stil (scalp): 15m giriş + 1h bölge (kart: 1h bölge, 5m tuzak -> min 15m'ye çıkarıldı); stop tuzak mum dibi; hedef >= 2R (kart: en az 1:2).
Kaynak kartlar: scalp__talep-arz-tuzak-mum__christopher; scalp__5sma-bosluk-hacim-tuzak__christopher (1m, NSE opsiyon hacmi; ayrı bir 5-SMA boşluk mantığı, kodlanmadı); daytrade__smc-emir-blogu-adil-deger__singhal (kodlanmadı).
Varsayımlar / ölçülebilir yaklaşık tanım: DBR/RBR/RBD/DBD 'görme' işi: mum oran eşikleri (%70/%40; kitap %75/%25-40, %5-10 tolerans), tek bazlı bölge tercih (baz_maks 1-3). Baz mumsuz istisna tipleri (Tip-1/2/3) ve 'bir sonraki arz bölgesi' hedefi KODLANMADI (sabit R). Hacim yoksa/sıfırsa hacim filtresi uygulanmaz. Bölge süresi kitapta yok -> omur=150 mum. 5m bölge/1h bölge içinde-dokunma kuralı: 15m girişin 1h bölgesine dokunması ile yaklaşıldı.
Çelişkiler: Hacim kartı 'Vaka-1 (son kırmızı mum hacmi önceki mumdan büyük)' ve 'Vaka-2 (düşük)' ikisini de long sayar; Vaka-1 (hacim > önceki) seçildi. Tuzak mum stop'u: kart 'distal biraz altı veya tuzak dibi'.
Negatif kanıt: Ailede kanıt yok; tek yazar (Christopher) iddiaları, kitaplarda hisse/endeks örnekleri (kripto doğrulaması yok).
"""
from motor.strateji.formasyon_b4 import TalepArzBolgesiTaban


class TalepArzBolgesi(TalepArzBolgesiTaban):
    ad = "scalp__talep-arz-bolgesi"
    stil = "scalp"
    varsayilan_parametreler = {**TalepArzBolgesiTaban.varsayilan_parametreler,
                               "giris_modu": 'tuzak',
                               "stop_modu": 'tuzak',
                               "ust_tf": '1h',
                               "hedef_r": 2.0,
                               "omur": 200,
                               "baz_maks": 1,
                               }
    parametre_izgarasi = {
        "itki_atr": [1.5, 2.0, 2.5],
        "baz_maks": [1, 3],
        "hedef_r": [2.0, 3.0],
        "ust_tf": ['1h', ''],
    }
