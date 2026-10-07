// ---------- loading scenarios from JSON (no Python needed) ----------
function addScenarios(list,fname){
  const base=fname.replace(/\.json$/i,'');
  let added=0;
  list.forEach((it,i)=>{
    if(!it||!Array.isArray(it.steps))return;
    const id=(list.length>1?base+'-'+(i+1):base);
    const sc={id,name:it.name||id,description:it.description||'',page:it.page||null,steps:it.steps};
    const ix=(DATA.scenarios||[]).findIndex(s=>s.id===id);
    DATA.scenarios=DATA.scenarios||[];
    if(ix>=0)DATA.scenarios[ix]=sc;else DATA.scenarios.push(sc);
    added++;
  });
  return added;
}
function refreshScnSelect(selectId){
  const sel=$('scn');const keep=selectId||sel.value;sel.innerHTML='';
  (DATA.scenarios||[]).forEach(sc=>{const o=document.createElement('option');o.value=sc.id;o.textContent=loc(sc.name);sel.appendChild(o);});
  const has=(DATA.scenarios||[]).length>0;
  ['playrow','transport','pacerow','scndesc','stepno','outline'].forEach(id=>{const e=$(id);if(e)e.style.display=has?'':'none';});
  document.querySelectorAll('#scncard .row.expert').forEach(e=>e.style.display=has?'':'none');
  $('loadhint').textContent=t(has?(DATA.portable?'scn.hint.basic':'scn.hint'):(DATA.portable?'cap.noscn.basic':'cap.noscn'));
  if(keep)sel.value=keep;
}
async function loadFiles(files){
  let last=null,total=0,errs=[];
  for(const f of files){
    try{
      if(/^(variables|csv_profiles)(\.discovered)?\.json$/i.test(f.name))continue;
      if(DATA.portable&&!/\.json$/i.test(f.name))continue;      // basic variant: scenarios only
      if(/\.(csv|txt)$/i.test(f.name)){openCsv(f.name,await f.text());continue;}
      const raw=JSON.parse(await f.text());
      const list=Array.isArray(raw)?raw:(raw.scenarios||[raw]);
      const n=addScenarios(list,f.name);total+=n;
      if(n)last=list.length>1?f.name.replace(/\.json$/i,'')+'-1':f.name.replace(/\.json$/i,'');
      else errs.push({key:'warn.nosteps',vars:{f:f.name}});
    }catch(e){errs.push({key:'warn.loaderr',vars:{x:f.name+': '+e.message}});}
  }
  refreshScnSelect(last);selectScn();
  cap.extra=errs.map(x=>x.key==='warn.loaderr'?x:{key:'warn.loaderr',vars:{x:R(x)}});warn();
  if(total)setCaption({key:'cap.loaded',vars:{n:total}},null,'info');
}
