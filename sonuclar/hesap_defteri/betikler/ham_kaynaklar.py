"""P4-P7 kaynaklarini kayipsiz satir kimlikleriyle cikarir. Akibet atamaz."""
import csv,hashlib,json,re,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from envanter import ROOT,OUT,write

NAME_KEYS=('ad','strateji_adi','strateji_ad','Strateji Adı','strateji','kart_id','aile_id','yeni_aile','candidate','hedef_kart_id','hedef_strateji','arsiv_id','id','no','modul','hedef_id','hedef_sinif','kimlik','URL','url','kaynak','kume_id','dosya','fikir_grubu','dis_id')

def ident(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def main():
    sources=list(csv.DictReader((OUT/'kaynaklar.csv').open(encoding='utf-8')))
    groups={p:[] for p in ('P4','P5','P6','P7')}; checks=[]; pending=[]
    def add(part,path,locator,row,name=None,kind='strateji_kaydi'):
        row={('_fazla_sutunlar' if k is None else k):v for k,v in row.items()}
        if path.endswith('2026-11_freqtrade_robotic/dosya_listesi.csv'):
            name=row.get('dosya')
        name=name or next((str(row[k]) for k in NAME_KEYS if row.get(k)), '(ad alani yok)')
        groups[part].append(dict(ham_id='H'+ident(path+'#'+locator),kaynak_id='K'+hashlib.sha256(path.encode()).hexdigest()[:12],kaynaktaki_ad=name,kaynak_satir_no=locator,tekil_id='',dosya=path,kayit_turu=kind,kaynak_kimligi=str(row.get('kart_id') or row.get('id') or row.get('kimlik') or ''),veri_json=json.dumps(row,ensure_ascii=False,sort_keys=True)))
    def count(part,path,n,before,unit):
        got=len(groups[part])-before
        checks.append(dict(parca=part,dosya=path,kaynak_kayit=n,ham_kayit=got,fark=got-n,birim=unit))
        assert n==got,(path,n,got)
    for src in sources:
        rel=src['dosya']; p=ROOT/rel
        if re.search(r'/ajan1/tur[123]/', rel): continue  # Kullanici: eski turlar ana ham sayimina katilmaz.
        if not p.is_file() or p.is_symlink(): continue
        part=None
        if rel.startswith('veri/kartlar_ham/') or rel=='veri/kart_dizini.csv' or rel.startswith('stratejiler/kart_ayarlari/') or rel in ('stratejiler/aileler.json','stratejiler/elenenler.json','stratejiler/ek_kaynaklar/kitap_kartlari_eslesme.csv','stratejiler/ek_kaynaklar/tam_okuma_guncelleme_ozet.csv'): part='P4'
        elif rel.startswith('stratejiler/v3_adaylar/'): part='P6'
        elif rel.startswith('sonuclar/dis_arastirma/'): part='P7'
        elif rel.startswith('stratejiler/') or (rel.startswith('arsiv/') and (p.suffix=='.xlsx' or rel=='arsiv/codex-algo/config/pdf_candidates.csv' or re.search(r'/(tv|tv_eleme_dali)/sonuclar/', rel))): part='P5'
        if part is None: continue
        before=len(groups[part])
        if p.suffix=='.csv':
            with p.open(encoding='utf-8-sig',newline='') as f:
                rd=csv.DictReader(f); n=0
                for n,row in enumerate(rd,1):
                    kind='strateji_kaydi'
                    if any(t in rel for t in ('kodlama','on_eleme','eslesme','etiketler','fikir_grup','karsilastirma','kanit_ekleri','yazar_denetimi','kaynak_dogrulama','kod_kontrol','on_kayit_girdi','cikis_modulleri','tam_okuma_guncelleme','benzeri_derin','oncelik','yeni_199','kume_listesi','ewo_aile','e0v1e_karsilastirma','aile_kapsami','denetim_ornek')): kind='eslestirme_veya_karar'
                    add(part,rel,'kayit:'+str(n)+';bitis_satiri:'+str(rd.line_num),row,kind=kind)
            count(part,rel,n,before,'CSV baslik haric mantiksal kayit; fiziksel bitis satiri ayrica')
        elif p.suffix=='.json':
            obj=json.loads(p.read_text(encoding='utf-8-sig')); entries=[]
            if isinstance(obj,list): entries=[('/'+str(i),r) for i,r in enumerate(obj)]
            elif isinstance(obj,dict) and ('kart_id' in obj or 'long_giris' in obj or ('pine_id' in obj and 'ad' in obj)): entries=[('/',obj)]
            elif isinstance(obj,dict):
                for key,val in obj.items():
                    if isinstance(val,list) and key in ('stratejiler','tek_grafik','portfoy','secimler','adaylar'):
                        entries += [('/'+key+'/'+str(i),r) for i,r in enumerate(val)]
            for loc,row in entries:
                if not isinstance(row,dict): row={'deger':row}
                add(part,rel,'json:'+loc,row,kind='ayar_kaydi' if '/kart_ayarlari/' in rel or '/dis_ayarlari/' in rel else 'strateji_kaydi')
            if entries or isinstance(obj,list): count(part,rel,len(entries),before,'JSON listesi/kart nesnesi')
            else: pending.append(dict(parca=part,dosya=rel,neden='JSON strateji disi veya semasi elle incelenecek'))
        elif p.suffix=='.xlsx':
            with zipfile.ZipFile(p) as z:
                ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                ss=[]
                if 'xl/sharedStrings.xml' in z.namelist():
                    ss=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
                n=0
                for name in sorted(z.namelist()):
                    if not (name.startswith('xl/worksheets/sheet') and name.endswith('.xml')):continue
                    rows=ET.fromstring(z.read(name)).findall('.//m:row',ns); headers=None
                    for row in rows:
                        cells={}
                        for c in row.findall('m:c',ns):
                            v=c.find('m:v',ns); val=v.text if v is not None else ''.join(c.itertext())
                            if c.get('t')=='s': val=ss[int(val)]
                            col=re.sub('[0-9]','',c.get('r','')); cells[col]=val or ''
                        if headers is None:headers=cells;continue
                        # Yalniz strateji tablosu; kapsam/not sayfalari kaynak inceleme kuyrugunda.
                        if not any(h in ('Strateji Adı','Strateji','Strategy') for h in headers.values()): continue
                        data={headers.get(k,k):v for k,v in cells.items()};n+=1
                        add(part,rel,name+':satir:'+row.get('r',''),data)
            count(part,rel,n,before,'Excel strateji sayfalarinda baslik haric satir')
        elif p.suffix in ('.md','.txt'):
            lines=p.read_text(encoding='utf-8-sig').splitlines();n=0
            if rel.endswith('/ajan2/derin_arastirma_26_kayit_raporu.md'):
                add(part,rel,'satir:5',{'ad':'26 stratejilik liste beyanı; tekil CSV mevcut değil','beyan_edilen_kayit':26,'eksik':'Rapordaki sandbox:/mnt/data/strateji_listesi.csv bu depoda mevcut değil; satır kimliklerinin ad/kural/link eşlemesi yeniden üretilemiyor'},kind='toplu_beyan')
                count(part,rel,1,before,'tekil satirlari olmayan bir toplu beyan; 26 uydurma satir uretilmedi')
            elif rel=='stratejiler/v3_adaylar/yeni_aday_taramasi_tur5.md':
                section=''
                for i,line in enumerate(lines,1):
                    if line.startswith('## '):section=line[3:]
                    if section not in ('Tam metni açılıp okunanlar (hiçbiri aday değil)','Yalnız özetten okunanlar (aday SAYILMADI)','Elenenler'):continue
                    if not line.strip() or line.startswith('#'):continue
                    n+=1;add(part,rel,'satir:'+str(i),{'ad':line.removeprefix('- ').split(':',1)[0], 'kural_ozeti':line.removeprefix('- '),'belgeli_karar':'Yeni kart/kod adayı yapılmadı; '+section,'toplu_kayit':'evet' if not line.startswith('- ') else 'hayir'},kind='belgeli_arastirma_satiri')
                count(part,rel,n,before,'bes madde ve iki toplu ret paragrafi; paragraf uyeleri bagimsiz tekil sayilmadi')
            elif p.name.startswith('REDDEDILENLER'):
                for i,line in enumerate(lines,1):
                    if not line.strip():continue
                    n+=1;bits=line.split('|',1); add(part,rel,'satir:'+str(i),{'ad':bits[0].strip(),'gerekce':bits[1].strip() if len(bits)>1 else ''},kind='ret_kaydi')
                count(part,rel,n,before,'bos olmayan ret satiri')
            elif rel=='stratejiler/ek_kaynaklar/ek_77_strateji.md':
                sections={};starts=[(i,re.match(r'^### (\d+)\.',line)) for i,line in enumerate(lines)];starts=[(i,m[1]) for i,m in starts if m]
                for ix,(start,num) in enumerate(starts):
                    end=starts[ix+1][0] if ix+1<len(starts) else len(lines)
                    section='\n'.join(lines[start:end]);data={'ayrinti_konumu':f'satir:{start+1}-{end}'}
                    for label,key in (('Mantık','kural_ozeti'),('Güvenilirlik','kaynak_kanit_beyani')):
                        m=re.search(r'\*\*'+label+r':\*\*\s*(.*?)(?=\n\*\*|\n---|\Z)',section,re.S)
                        if m:data[key]=m[1].strip()
                    for line in lines[start:end]:
                        if line.startswith('|'):
                            cells=[c.strip() for c in line.strip('|').split('|')]
                            if len(cells)>1 and cells[0] in ('Repo','Piyasa / zaman dilimi','Lisans'):data[cells[0]]=cells[1]
                    sections[num]=data
                assert len(sections)==77
                for i,line in enumerate(lines,1):
                    m=re.match(r'\|\s*(\d+)\s*\|\s*([^|]+)\|',line)
                    if m:
                        n+=1;add(part,rel,'satir:'+str(i),dict(sira=m[1],ad=m[2].strip(),**sections[m[1]]),kind='strateji_kaydi')
                count(part,rel,n,before,'numarali ozet tablo satiri')
            else: pending.append(dict(parca=part,dosya=rel,neden='Belge anlatimi: strateji atiflari/tablolar elle taranacak; CSV/JSON ile kapsandigi henuz kanitlanmadi'))
    for part,rows in groups.items():
        if rows:write('ara/'+part+'_ham.csv',rows,list(rows[0]))
    write('ara/P4_P7_sayi_kontrolu.csv',checks,list(checks[0]))
    write('ara/P4_P7_belge_inceleme_kuyrugu.csv',pending,list(pending[0]))
    summary={k:len(v) for k,v in groups.items()};summary['belge_kuyrugu']=len(pending);summary['sayi_kontrolu']=len(checks)
    (OUT/'ara/P4_P7_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
