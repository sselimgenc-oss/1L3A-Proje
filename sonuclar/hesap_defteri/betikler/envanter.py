"""Salt okunur kaynak keşfi. Strateji modülü içe aktarmaz, test çalıştırmaz."""
import ast
import csv
import gzip
import hashlib
import io
import json
import os
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'sonuclar/hesap_defteri'
BASES = ('stratejiler', 'veri', 'arsiv', 'sonuclar', 'motor/strateji', 'motor/portfoy')

def write(name, rows, fields):
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for row in rows:
            cleaned={k:re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[EPOSTA_MASKELENDI]', str(v)) if isinstance(v,str) else v for k,v in row.items()}
            w.writerow(cleaned)

def paths():
    for q in ROOT.glob('*.md'):
        yield q
    for base in BASES:
        for folder, dirs, files in os.walk(ROOT / base, followlinks=False):
            p = Path(folder)
            dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__', 'hesap_defteri', 'mumlar') and not (p/d).is_symlink())
            if len(p.relative_to(ROOT).parts) >= 12:
                if dirs: raise RuntimeError(f'Derinlik siniri: {p}')
                dirs[:] = []
            for n in sorted(files):
                q = p/n
                if q.suffix.lower() in ('.csv','.json','.jsonl','.md','.txt','.py','.xlsx','.xls','.gz','.pine','.ipynb','.yaml','.yml','.toml','.ini','.cfg','.js','.ts'):
                    yield q

def dates():
    raw = subprocess.check_output(['git','log','--reverse','--diff-filter=A','--format=DATE:%aI','--name-only','--',*BASES],cwd=ROOT,text=True)
    result={}; date=''
    for s in raw.splitlines():
        if s.startswith('DATE:'): date=s[5:]
        elif s: result.setdefault(s,date)
    return result

def main():
    ds=dates(); inv=[]; classes=[]; schemas=[]
    for p in sorted(set(paths())):
        rel=p.relative_to(ROOT).as_posix()
        r=dict(kaynak_id='K'+hashlib.sha256(rel.encode()).hexdigest()[:12],dosya=rel,tur=p.suffix,satir=0,kayit_sayisi='',alanlar='',gelis_tarihi=ds.get(rel,''),tarih_kaniti='git log --reverse --diff-filter=A; ilk eklenme, kullanicidan gelis tarihi degil',sha256='',durum='ok',not_='')
        if p.is_symlink():
            r.update(durum='symlink_atlandi',not_='Hedef okunmadi'); inv.append(r); continue
        try:
            data=p.read_bytes(); r['sha256']=hashlib.sha256(data).hexdigest()
            if p.suffix in ('.xlsx','.xls'):
                r.update(durum='ikili_incelenecek'); inv.append(r); continue
            if p.suffix=='.gz': data=gzip.decompress(data)
            text=data.decode('utf-8-sig'); r['satir']=len(text.splitlines())
            if p.suffix=='.csv' or p.name.endswith('.csv.gz'):
                rd=csv.DictReader(io.StringIO(text)); rows=list(rd); r['kayit_sayisi']=len(rows); r['alanlar']=json.dumps(rd.fieldnames,ensure_ascii=False)
                schemas.append({'dosya':rel,'n':len(rows),'alanlar':rd.fieldnames,'ornek':[]})
            elif p.suffix=='.json':
                obj=json.loads(text); r['kayit_sayisi']=len(obj) if isinstance(obj,list) else 1
                r['alanlar']=json.dumps(list(obj) if isinstance(obj,dict) else list(obj[0]) if obj and isinstance(obj[0],dict) else [],ensure_ascii=False)
            elif p.suffix=='.jsonl': r['kayit_sayisi']=sum(bool(s.strip()) for s in text.splitlines())
            elif p.suffix=='.py':
                tree=ast.parse(text)
                for node in ast.walk(tree):
                    if not isinstance(node,ast.ClassDef): continue
                    attrs={}
                    for a in node.body:
                        if isinstance(a,ast.Assign):
                            for target in a.targets:
                                if isinstance(target, ast.Name):
                                    try: attrs[target.id]=ast.literal_eval(a.value)
                                    except (ValueError,TypeError): pass
                                elif isinstance(target, (ast.Tuple, ast.List)):
                                    try:
                                        values=ast.literal_eval(a.value)
                                        for sub, value in zip(target.elts, values):
                                            if isinstance(sub, ast.Name): attrs[sub.id]=value
                                    except (ValueError,TypeError): pass
                    if isinstance(attrs.get('ad'),str) and attrs['ad']:
                        classes.append(dict(strateji_id=attrs['ad'],sinif=node.name,dosya=rel,satir=node.lineno,stil=attrs.get('stil',''),kayit_kapsami='tek_grafik' if rel.startswith('motor/strateji/') else 'portfoy' if rel.startswith('motor/portfoy/') else 'arsiv',temel_siniflar=';'.join(ast.unparse(b) for b in node.bases),doc_var=bool(ast.get_docstring(node))))
        except (OSError,UnicodeError,ValueError,SyntaxError) as e:
            r.update(durum='okuma_hatasi',not_=str(e))
        inv.append(r)
    write('kaynaklar.csv',inv,list(inv[0]))
    write('ara/P2_kod_siniflari.csv',classes,list(classes[0]))
    (OUT/'ara/P1_csv_semalari.json').write_text(json.dumps(schemas,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'dosya':len(inv),'okuma_hatasi':[x['dosya'] for x in inv if x['durum']=='okuma_hatasi'],'symlink_atlandi':[x['dosya'] for x in inv if x['durum']=='symlink_atlandi'],'ikili':[x['dosya'] for x in inv if x['durum']=='ikili_incelenecek'],'sinif':len(classes),'aktif_tek_grafik':sum(x['kayit_kapsami']=='tek_grafik' for x in classes),'aktif_portfoy':sum(x['kayit_kapsami']=='portfoy' for x in classes)}
    (OUT/'ara/P1_P2_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__': main()
