"""Kaynak, eski surum, karar ve sonuc kayitlarini sayimda ayirir; satir silmez."""
import csv,re,json
from collections import Counter
from pathlib import PurePosixPath
from envanter import ROOT,OUT,write

CATALOG_NAMES={'dis_envanter.csv','github_g1_freqtrade.csv','github_g2_kripto_bot.csv','github_g3_cerceve.csv','github_g4_platform.csv','github_g5_mt_pine.csv','github_g6_liste_notebook.csv','github_g7_kutuphane.csv','kakushadze_151.csv','repo_kodlari.csv','repo_raporlari.csv','son1ay_2026-11.csv','ek_77_strateji.md'}
def role(rel):
    p=PurePosixPath(rel)
    if re.search(r'/ajan1/tur[123]/',rel):return 'surum_gecmisi','Kullanici: eski tur yeni kaynak/ham strateji sayilmaz'
    if rel.startswith(('veri/kartlar_ham/','stratejiler/v3_adaylar/kartlar/')) and p.suffix=='.json':return 'asli_kart','Her JSON karti; varyant listesi ayrica korunur'
    if rel=='stratejiler/v3_adaylar/yeni_aday_taramasi_tur5.md':return 'asli_katalog','Kataloglara yazilmamis bes arastirma maddesi ve iki toplu ret paragrafi'
    if rel.startswith('stratejiler/v3_adaylar/ham/') and p.suffix=='.csv':return 'asli_katalog','Alt liste kopyalari mantik/provenans denetimiyle tekillestirilecek'
    if rel.startswith('stratejiler/') and p.name in CATALOG_NAMES:return 'asli_katalog','Getirilen kaynak strateji/aday/tool satirlari'
    if rel.startswith('arsiv/') and p.suffix=='.xlsx':return 'asli_katalog','Eski Excel turleri, kurallar ayniysa kopya; bilinmeyenler birlestirilmez'
    if rel=='arsiv/codex-algo/config/pdf_candidates.csv':return 'asli_katalog','Eski proje PDF adaylari'
    if rel.endswith('/ajan2/derin_arastirma_26_kayit_raporu.md'):return 'asli_katalog','Tekil CSVsi olmayan 26 beyanli toplu kaynak; 26 yapay strateji sayilmaz'
    if rel.endswith('/ajan1/strateji_listesi.csv'):return 'asli_katalog','906 son liste'
    if rel.endswith('2026-11_freqtrade_robotic/dosya_listesi.csv'):return 'asli_katalog','909 dosya; 540 kume mantik denklesmesi varsayilmaz'
    if rel.startswith('motor/strateji/') or rel.startswith('motor/portfoy/'):return 'kod_kaniti','AST ad tanimlari P2; moduller import edilmez'
    if rel.startswith('arsiv/') and p.suffix in ('.py','.pine','.ipynb'):return 'arsiv_kod_kaniti','Eski kod; ana uygulamaya ait test sonucu gibi kullanilmaz'
    if re.search(r'/(tv|tv_eleme_dali)/sonuclar/.*\.json$',rel):return 'arsiv_sonuc','135 Pine kimligi; tarihsel rapor, modern 1L3A sonucu degil'
    if rel.startswith('sonuclar/') and not rel.startswith('sonuclar/dis_arastirma/'):return 'sonuc_ve_yontem_kaniti','Ayni stratejinin asama/ayar tekraridir; yeni kaynak strateji sayilmaz'
    if rel.startswith('stratejiler/') or rel=='veri/kart_dizini.csv' or rel.startswith('sonuclar/dis_arastirma/'):
        return 'karar_eslestirme_veya_belge','Asli kaynak stratejisini gosteren surec kaydi; kendi basina yeni strateji sayilmaz'
    return 'diger_basvuru','Kaynak envanterinde korunur; bagimsiz strateji oldugu iddia edilmez'

def main():
    inv=list(csv.DictReader((OUT/'kaynaklar.csv').open()));rows=[]
    for r in inv:
        rol,why=role(r['dosya']);rows.append(dict(kaynak_id=r['kaynak_id'],dosya=r['dosya'],rol=rol,ana_ham_sayima_dahil='evet' if rol in ('asli_kart','asli_katalog') else 'hayir',gerekce=why,kaynak_sayim_degeri=r['kayit_sayisi'],fiziksel_satir=r['satir']))
    assert len(rows)==len(inv)
    write('ara/P1_kaynak_rolleri.csv',rows,list(rows[0]));print(dict(Counter(r['rol'] for r in rows)))
if __name__=='__main__':main()
