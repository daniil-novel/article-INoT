from pathlib import Path
import hashlib, json, re, subprocess

BASE='23ea109'
OUT=Path('reviews/2026-09-11-readability')
OUT.mkdir(parents=True,exist_ok=True)
def old(name):
    return subprocess.check_output(['git','show',f'{BASE}:{name}']).decode('utf-8').replace('\r\n','\n')
def squash(s):
    s=s.replace(r'\textless{}','<').replace(r'\textgreater{}','>').replace(r'\_','_')
    return re.sub(r'\s+','',s).replace(r'\small','')
def quotes(s):
    return [squash(x) for x in re.findall(r'\\begin\{quote\}(.*?)\\end\{quote\}',s,re.S)]
def walk(p,seen):
    if p in seen:return
    seen.add(p)
    for child in re.findall(r'\\input\{([^}]+)\}',p.read_text(encoding='utf-8')):
        walk(Path(child if child.endswith('.tex') else child+'.tex'),seen)

report={'base_revision':BASE,'scope':'Presentation changes; no new experimental outcomes','languages':{}}
all_paths=set()
for lang,suffix in [('en',''),('ru','_ru')]:
    paths=set(); walk(Path('converted_article_springer'+suffix+'.tex'),paths)
    all_paths.update(paths)
    joined='\n'.join(p.read_text(encoding='utf-8') for p in paths)
    labels=re.findall(r'\\label\{([^}]+)\}',joined)
    refs=re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',joined)
    cites={x for group in re.findall(r'\\cite\{([^}]+)\}',joined) for x in group.split(',')}
    bib=set(re.findall(r'\\bibitem\{([^}]+)\}',joined))
    prompt_name=f'sections/exact_prompts_{lang}.tex'
    current=Path(prompt_name).read_text(encoding='utf-8')
    old_quotes=quotes(old(prompt_name)); new_quotes=quotes(current)
    listing=re.search(r'\\begin\{lstlisting\}\[[^\n]*\]\n(.*?)\\end\{lstlisting\}',current,re.S).group(1)
    other_name=f'sections/segregation80_prompts_{lang}.tex'
    dep_name=f'sections/task_dependence_{lang}.tex'
    prior_groups=[tuple(re.findall(r'/([0-9]+)',g)) for g in re.findall(r'\\\{([^{}]*)\\\}',old(dep_name))]
    new_groups=[]
    for line in Path(dep_name).read_text(encoding='utf-8').splitlines():
        if re.match(r'^[1-7] & ',line):
            cells=line.split('&'); members=tuple(re.findall(r'\d+',cells[1])); size=int(cells[2].split('\\')[0].strip())
            assert size==len(members)
            new_groups.append(members)
    aux=Path('converted_article_springer'+suffix+'.aux').read_text(encoding='utf-8')
    anchors={}
    for label in ['fig:hybrid-core','alg:hybrid-core','fig:inot-instruction','tab:source-groups','app:inot-instruction']:
        match=re.search(r'\\newlabel\{'+re.escape(label)+r'\}\{\{([^}]+)\}\{([^}]+)\}',aux)
        assert match, label
        anchors[label]={'number':match[1],'page':int(match[2])}
    result={'included_sources':len(paths),'unresolved_labels':sorted(set(refs)-set(labels)),
        'unresolved_citations':sorted(cites-bib),'duplicate_labels':sorted(x for x in set(labels) if labels.count(x)>1),
        'unchanged_common_and_factorial_quotes':old_quotes[:-1]==new_quotes,
        'unchanged_inot_non_whitespace_characters':old_quotes[-1]==squash(listing),
        'unchanged_boundary_quotes':quotes(old(other_name))==quotes(Path(other_name).read_text(encoding='utf-8')),
        'unchanged_seven_source_groups':prior_groups==new_groups and len(new_groups)==7,
        'source_groups':new_groups,'anchors':anchors,
        'repository_dependencies':bool(re.search(r'(?i)github\.com|\bcommits?\b|коммит|sha-?256|reproducibility/|hashes are published|хеши опубликованы',joined)),
        'overfull_boxes':re.findall(r'Overfull[^\n]*',Path('converted_article_springer'+suffix+'.log').read_text(encoding='utf-8',errors='replace'))}
    assert not any(result[k] for k in ['unresolved_labels','unresolved_citations','duplicate_labels','repository_dependencies','overfull_boxes']),result
    assert all(result[k] for k in ['unchanged_common_and_factorial_quotes','unchanged_inot_non_whitespace_characters','unchanged_boundary_quotes','unchanged_seven_source_groups']),result
    report['languages'][lang]=result
prior=json.loads(Path('reviews/2026-09-11-standalone/source_checks.json').read_text())
report['unchanged_outcome_tables']={name:old(name)==Path(name).read_text(encoding='utf-8') for name in prior['outcome_table_checks']}
assert all(report['unchanged_outcome_tables'].values())
report['tex_sha256']={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(all_paths)}
(OUT/'source_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ok':True,'languages':{lang:{'sources':v['included_sources'],'anchors':v['anchors']} for lang,v in report['languages'].items()},'unchanged_tables':len(report['unchanged_outcome_tables'])},ensure_ascii=False))
