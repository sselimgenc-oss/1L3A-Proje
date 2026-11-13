"""Sinif govdesindeki acik URL ve Pine dosya atiflari. Bunlar kural denklesmesi DEGILDIR."""
import ast,csv,re
from envanter import ROOT,OUT,write

def main():
    with (OUT/'ara/P2_kod_denetimli.csv').open() as f:classes=list(csv.DictReader(f))
    trees={};texts={};rows=[]
    for r in classes:
        rel=r['dosya']
        if rel not in texts:
            texts[rel]=(ROOT/rel).read_text();trees[rel]=ast.parse(texts[rel])
        node=next(n for n in ast.walk(trees[rel]) if isinstance(n,ast.ClassDef) and n.name==r['sinif'])
        body='\n'.join(texts[rel].splitlines()[node.lineno-1:node.end_lineno]);refs=set()
        for url in re.findall(r'https?://[^\s<>`"\)]+',body):refs.add(('URL',url.rstrip('.,;')))
        for pine in re.findall(r'(?:[\w/-]+/)?([A-Za-z0-9_-]+)\.pine',body):refs.add(('PINE_ID',pine))
        for typ,value in sorted(refs):rows.append(dict(strateji_id=r['strateji_id'],tip=typ,deger=value,kod_kaniti=rel+':'+str(node.lineno),sinir='Sinif kendi kaynagina atif yapiyor; kaynagin tum mantigi uygulandi sonucu cikmaz'))
    write('ara/P8_kod_kaynak_atiflari.csv',rows,list(rows[0]));print('Acik sinif ici kaynak atfi',len(rows))
if __name__=='__main__':main()
