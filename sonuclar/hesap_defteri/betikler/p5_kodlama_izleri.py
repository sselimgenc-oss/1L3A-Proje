"""P5 kodlama gunluklerinin acik kart/satir baglantilari. Isimden esdegerlik karari vermez."""
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path
from envanter import ROOT,OUT,write

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    op={r['strateji_id']:r for r in read(OUT/'ara/P2_kod_denetimli.csv')};book={r['kart_id'] for r in read(OUT/'ara/P4_kitap_izleri.csv')};raw=read(OUT/'ara/asli_ham_satirlar.csv');byfile=defaultdict(list)
    for r in raw:byfile[r['dosya']].append(r)
    rows=[];issues=[]
    for p in sorted((ROOT/'stratejiler').glob('kodlama_*.csv')):
        rel=p.relative_to(ROOT).as_posix()
        for n,d in enumerate(read(p),1):
            alltext=' '.join(str(x) for x in d.values());targets=sorted(set(re.findall(r'(?:dis|pf|swing|daytrade|scalp|v2|v3|onceki)__[\w-]+',str(d.get('yeni_strateji_adi') or d.get('pf_sinif') or d.get('hedef_sinif') or d.get('nerede') or '')))&set(op))
            cardfield=d.get('kaynak_kartlar','');kids=sorted(set(re.findall(r'(?:scalp|daytrade|swing)__[\w-]+',cardfield))&book)
            why=d.get('gerekce') or d.get('not') or d.get('degisiklik') or ''
            for kid in kids:
                rows.append(dict(kaynak_tipi='kart_id',kaynak_kimligi=kid,kaynak_ham_id='',hedef_kod=';'.join(targets),gunluk_durum=d.get('durum',''),varsayim_kapsam=why,kanit=rel+':kayit='+str(n),denetim='Kart-id mevcut; hedef adlar AST ile bulundu; mantik esdegerligi ayrica gerekli'))
            # dis_envanter icin acik 0 tabanli satir referansi, ad sadece referans butunlugu denetimi.
            idx=d.get('satir_indeksi') or d.get('satir_indeksi_veya_madde_no')
            source=d.get('kaynak_dosya','')
            if idx is not None and str(idx).isdigit() and (p.name.endswith('_a.csv') or source in ('dis_envanter','dis_envanter.csv')):
                data=byfile['stratejiler/dis_envanter.csv'];i=int(idx)
                if i<len(data):
                    r=data[i];rd=json.loads(r['veri_json']);nameok=rd['ad'].strip()==d.get('ad','').strip()
                    if nameok:rows.append(dict(kaynak_tipi='dis_envanter_satiri',kaynak_kimligi=rd['ad'],kaynak_ham_id=r['ham_id'],hedef_kod=';'.join(targets),gunluk_durum=d.get('durum',''),varsayim_kapsam=why,kanit=rel+':kayit='+str(n),denetim='Acik 0 tabanli konum ve ad ayni; hedef ad AST ile var; ad mantik denklesmesi icin kullanilmadi'))
                    else:issues.append(dict(dosya=rel,kayit=n,kaynak_indeks=idx,sorun='dis_envanter konumundaki ad farkli; otomatik baglanmadi'))
            if not targets and str(d.get('durum','')).startswith(('kodland','kodlandı')):
                issues.append(dict(dosya=rel,kayit=n,kaynak_indeks=idx or '',sorun='Kodlandi kaydinda tekil/ad hedefi ASTde dogrulanamadi; grup/mod olabilir'))
    write('ara/P5_kodlama_izleri.csv',rows,list(rows[0]));write('ara/P5_kodlama_baglanti_kuyrugu.csv',issues,['dosya','kayit','kaynak_indeks','sorun']);print('Acik baglanti',len(rows),'kontrol kuyrugu',len(issues))
if __name__=='__main__':main()
