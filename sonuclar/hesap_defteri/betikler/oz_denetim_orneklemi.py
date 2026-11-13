"""Kullanicinin istedigi sabit tohumlu 40 satir denetim orneklemini uretir; hukmu otomatik yazmaz."""
import csv,json,random
from envanter import ROOT,OUT,write

def main():
    with (OUT/'tekil_stratejiler.csv').open() as f:rows=list(csv.DictReader(f))
    picked=random.Random(20261113).sample(sorted(rows,key=lambda r:r['tekil_id']),40)
    out=[]
    for i,r in enumerate(picked,1):out.append(dict(ornek_no=i,tekil_id=r['tekil_id'],ad=r['ad'],atanan_durum=r['durum'],asama=r['asama'],kapi_ve_deger=r['kapi_ve_deger'],kanit=r['kanit_dosyasi'],kod=r['kod_dosyasi'],denetim_hukmu='bekliyor',hata='',gerekce=''))
    write('ara/P9_oz_denetim_orneklemi.csv',out,list(out[0]));print('Tohum 20261113: 40 satir secildi, hukum bekliyor.')
if __name__=='__main__':main()
