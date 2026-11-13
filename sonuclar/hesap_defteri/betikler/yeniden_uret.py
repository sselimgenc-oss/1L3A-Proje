"""Depo kokunden: python sonuclar/hesap_defteri/betikler/yeniden_uret.py
Yalniz stdlib belge/CSV/AST denetimleri. Strateji importu, test/backtest veya ag yok.
Manuel hukumler yalniz mevcut kaynak tabani ve sabit 40 kimlikle gecerlidir.
"""
import subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
ORDER=('envanter','ham_kaynaklar','kod_denetimi','sonuclar','kitap_izleri','v3_izleri','dis_kaynak_denetimi','belge_atiflari','arsiv_sonuclari','kaynak_rolleri','kapsam_denetimi','asli_tekillestirme','kod_kaynak_atiflari','manuel_mantik_notlari','p5_kodlama_izleri','kod_akibeti','akibet_atama','ek_iz_kontrolleri','son_tablolar','oz_denetim_orneklemi','oz_denetim_kanitlari','oz_denetim_hukumleri','capraz_ve_butunluk','raporla')
if __name__=='__main__':
    for name in ORDER:
        print(name,flush=True)
        subprocess.run([sys.executable,str(BASE/(name+'.py'))],check=True,cwd=BASE.parents[2])
