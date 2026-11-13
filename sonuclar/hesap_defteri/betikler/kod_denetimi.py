"""P2: miras ve kayit kapsam denetimi; strateji kodunu calistirmaz."""
import ast,csv,hashlib,json
from collections import Counter,defaultdict
from envanter import ROOT,OUT,write

def main():
    rows=list(csv.DictReader((OUT/'ara/P2_kod_siniflari.csv').open())); trees={}; declarations={}; byname=defaultdict(list)
    for r in rows:
        rel=r['dosya']
        if rel in trees:continue
        tree=ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'));trees[rel]=tree
        for node in ast.walk(tree):
            if isinstance(node,ast.ClassDef): declarations[rel,node.name]=node;byname[node.name].append((rel,node.name))
    def style(key,visited=()):
        if key in visited:return '',''
        node=declarations[key]
        for stmt in node.body:
            if isinstance(stmt,ast.Assign):
                for target in stmt.targets:
                    if isinstance(target,ast.Name) and target.id=='stil' and isinstance(stmt.value,ast.Constant):return stmt.value.value,f'{key[0]}:{stmt.lineno}'
                    if isinstance(target,ast.Tuple) and isinstance(stmt.value,ast.Tuple):
                        for t,v in zip(target.elts,stmt.value.elts):
                            if isinstance(t,ast.Name) and t.id=='stil' and isinstance(v,ast.Constant):return v.value,f'{key[0]}:{stmt.lineno}'
        for base in node.bases:
            if isinstance(base,ast.Name):
                candidate=(key[0],base.id)
                if candidate not in declarations:
                    options=byname[base.id]
                    if len(options)!=1:continue
                    candidate=options[0]
                answer=style(candidate,visited+(key,))
                if answer[0]:return answer
        return '',''
    for r in rows:
        key=(r['dosya'],r['sinif']);node=declarations[key]
        r['stil'],r['stil_kaniti']=style(key)
        r['kayit_durumu']='kayit_disinda_ornek' if r['dosya']=='motor/portfoy/ornek.py' else 'kayit_taranan_modul'
        r['kayit_kaniti']='motor/portfoy/stratejiler/__init__.py' if r['kayit_kapsami']=='portfoy' else 'motor/strateji/kayit.py:25'
        r['sinif_ast_sha256']=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
        r['metotlar']=';'.join(n.name for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))
    assert len({r['strateji_id'] for r in rows})==len(rows),'Yinelenen ad'
    assert not [r for r in rows if r['kayit_kapsami']=='tek_grafik' and not r['stil']],'Cozulmeyen stil'
    write('ara/P2_kod_denetimli.csv',rows,list(rows[0]))
    summary=dict(ad_tanimi=len(rows),tek_grafik=sum(r['kayit_kapsami']=='tek_grafik' for r in rows),tek_grafik_stil=dict(Counter(r['stil'] for r in rows if r['kayit_kapsami']=='tek_grafik')),portfoy_tanimi=sum(r['kayit_kapsami']=='portfoy' for r in rows),kayit_disinda_ornek=sum(r['kayit_durumu']=='kayit_disinda_ornek' for r in rows),v3_tanimi=sum('v3' in r['strateji_id'] for r in rows),yinelenen_ad=0)
    (OUT/'ara/P2_denetim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
