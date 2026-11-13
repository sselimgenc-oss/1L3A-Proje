"""40 ornegi ara veri_json yerine asil kaynak dosyasindan tekrar acar."""
import ast,csv,json,re,zipfile
import xml.etree.ElementTree as ET
from envanter import ROOT,OUT

def clean(s):return re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}','[EPOSTA_MASKELENDI]',s)
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    sample=read_csv(OUT/'ara/P9_oz_denetim_orneklemi.csv');result=[]
    for r in sample:
        if r['tekil_id'].startswith('KOD:'):
            rel,lineno,cls=r['kod'].split(':');p=ROOT/rel;tree=ast.parse(p.read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name==cls)
            evidence={'sinif':cls,'satir':node.lineno,'kod_ozet':ast.get_docstring(node),'sonuc_kaniti':r['kanit']}
        else:
            primary=r['kanit'].split(';',1)[0];rel,loc=primary.split('#',1);p=ROOT/rel
            if loc.startswith('kayit:'):evidence=read_csv(p)[int(loc.split(':')[1])-1]
            elif loc.startswith('json:'):
                loc=loc[5:];evidence=json.loads(p.read_text())
                for key in loc.strip('/').split('/') if loc.strip('/') else []:evidence=evidence[int(key)] if isinstance(evidence,list) else evidence[key]
            elif loc.startswith('xl/'):
                sheet,rowno=loc.split(':satir:');ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                with zipfile.ZipFile(p) as z:
                    ss=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
                    sheetrows=ET.fromstring(z.read(sheet)).findall('.//m:row',ns)
                    def cells(rr):
                        out={}
                        for c in rr.findall('m:c',ns):
                            v=c.find('m:v',ns);s=v.text if v is not None else ''.join(c.itertext())
                            out[re.sub('[0-9]','',c.get('r',''))]=ss[int(s)] if c.get('t')=='s' else s
                        return out
                    headers=cells(sheetrows[0]);data=cells(next(x for x in sheetrows if x.get('r')==rowno));evidence={headers.get(k,k):v for k,v in data.items()}
            elif loc.startswith('satir:'):evidence={'satir':p.read_text().splitlines()[int(loc.split(':')[1])-1]}
            else:raise ValueError((rel,loc))
        result.append(dict(ornek_no=r['ornek_no'],tekil_id=r['tekil_id'],ad=r['ad'],atanan_durum=r['atanan_durum'],akibet_gerekcesi=r['kapi_ve_deger'],asil_kaynak=evidence))
    assert len(result)==40
    (OUT/'ara/P9_asli_kaynak_kanitlari.json').write_text(clean(json.dumps(result,ensure_ascii=False,indent=2)))
    print('40 asil kaynak yeniden okundu; semantik denetim hukmu ayrica yazilacak.')
if __name__=='__main__':main()
