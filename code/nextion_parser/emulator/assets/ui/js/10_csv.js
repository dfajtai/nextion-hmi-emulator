// ---------- CSV import ----------
let csvState=null;
function allRefs(){const s=new Set();(DATA.variables||[]).forEach(v=>s.add(v.ref));pages.forEach(p=>p.comps.forEach(c=>{if(c.type===59||c.type===54||c.type===116||c.type===52||c.type===0)s.add(p.name+'.'+c.objname+(c.type===0?'':(c.type===116?'.txt':'.val')));}));return [...s];}
function scaleFor(ref){const m=/^([^.]+)\.([^.]+)\./.exec(ref);if(!m)return 1;const pg=pages.find(p=>p.name===m[1]);const c=pg&&pg.comps.find(c=>c.objname===m[2]);return c&&c.type===59?Math.pow(10,c.vvs1||0):1;}
function csvEnv(){return {variables:DATA.variables||[],scale:scaleFor,lang:LANG};}
function fillSelect(sel,header,withNone){sel.innerHTML='';if(withNone){const o=document.createElement('option');o.value='';o.textContent=t('csv.none');sel.appendChild(o);}header.forEach(h=>{const o=document.createElement('option');o.value=h;o.textContent=h;sel.appendChild(o);});}
function openCsv(name,text){
  const tb=NXTools.parseCSV(text,LANG);
  if(!tb.header.length){cap.extra=[{key:'warn.csvempty',vars:{name}}];warn();return;}
  csvState={name,table:tb};
  $('csvfile').textContent=name;$('csvname').value='CSV: '+name.replace(/\.[^.]+$/,'');
  fillSelect($('csvcol'),tb.header,false);fillSelect($('csvgrp'),tb.header,true);
  // the default value column is the first one that mostly holds numbers
  const numCol=tb.header.find((h,i)=>NXTools.numeric(tb,i).values.length>tb.rows.length/2&&!/^(id|t_ms|wait_ms)$/i.test(h));if(numCol)$('csvcol').value=numCol;
  const grp=tb.header.find(h=>/csoport|group|ketrec|cage/i.test(h));if(grp)$('csvgrp').value=grp;
  const dl=$('reflist');dl.innerHTML='';allRefs().concat(pages.map(p=>p.name)).forEach(r=>{const o=document.createElement('option');o.value=r;dl.appendChild(o);});
  const pf=(DATA.csvProfiles&&DATA.csvProfiles.stats)||{};
  $('pf_page').value=pf.page||'';$('pf_path').value=(pf.path||[]).join(',');
  ['quantity','mean','sd','cv','group'].forEach(k=>$('pf_'+k).value=pf[k]||'');
  $('pf_wave').value=pf.wave?pf.wave.ref:'';$('pf_waveclick').value=pf.wave?pf.wave.click||'':'';
  $('sr_page').value=DATA.start;
  const hasSeries=tb.header.some(h=>NXTools.resolveHeader(h,csvEnv()).kind==='set');
  $('csvmode').value=(!pf.mean&&hasSeries)||(hasSeries&&tb.header.some(h=>/^t_ms$/i.test(h)))?'series':'stats';
  csvModeUi();renderCsvPreview();$('csvdlg').showModal();
}
function csvModeUi(){const s=$('csvmode').value==='stats';$('csvstats').style.display=s?'':'none';$('csvseries').style.display=s?'none':'';}
function renderCsvPreview(){
  const tb=csvState.table,rows=tb.rows.slice(0,4);
  let html='<table><tr>'+tb.header.map(h=>{const r=NXTools.resolveHeader(h,csvEnv());const mark=$('csvmode').value==='series'?(r.kind==='set'?' ✓':(r.kind==='unknown'?' ?':'')):'';return '<th title="'+r.kind+(r.ref?': '+r.ref:'')+'">'+h+mark+'</th>';}).join('')+'</tr>';
  rows.forEach(r=>{html+='<tr>'+r.map(c=>'<td>'+String(c).replace(/</g,'&lt;')+'</td>').join('')+'</tr>';});
  html+='</table><div class="note">'+t('csv.rows',{n:tb.rows.length,d:tb.delimiter==='\t'?t('csv.tab'):tb.delimiter})+(tb.warnings.length?t('csv.warn',{w:tb.warnings.slice(0,2).join('; ')}):'')+'</div>';
  $('csvprev').innerHTML=html;
}
function buildCsvScenario(){
  const tb=csvState.table,env=csvEnv();
  if($('csvmode').value==='series')
    return NXTools.buildSeriesScenario(tb,{name:$('csvname').value,defaultWaitMs:+$('sr_wait').value||1000,startPage:$('sr_page').value||null},env);
  const prof={page:$('pf_page').value.trim()||undefined,path:$('pf_path').value.split(',').map(s=>s.trim()).filter(Boolean),
    quantity:$('pf_quantity').value.trim(),mean:$('pf_mean').value.trim(),sd:$('pf_sd').value.trim(),cv:$('pf_cv').value.trim(),group:$('pf_group').value.trim()};
  if($('pf_wave').value.trim())prof.wave={ref:$('pf_wave').value.trim(),click:$('pf_waveclick').value.trim()||undefined};
  if(!prof.mean&&!prof.sd&&!prof.cv&&!prof.quantity)throw new Error(t('csv.needtarget'));
  return NXTools.buildStatsScenario(tb,{column:$('csvcol').value,groupColumn:$('csvgrp').value,profile:prof,waitMs:+$('pf_wait').value||4000,name:$('csvname').value,startPage:DATA.start},env);
}
$('csvmode').onchange=()=>{csvModeUi();renderCsvPreview();};
$('csvok').onclick=()=>{try{const sc=buildCsvScenario();sc.id=slug($('csvname').value);addScenarioObj(sc);$('csvdlg').close();
  setCaption({key:'cap.csvcreated',vars:{name:sc.name,desc:sc.description}},null,'info');
  cap.extra=sc.unknownColumns&&sc.unknownColumns.length?[{key:'warn.csvunknown',vars:{cols:sc.unknownColumns.join(', ')}}]:[];warn();}
  catch(e){$('csvmsg').textContent=t('csv.err',{m:e.message});}};
$('csvjson').onclick=()=>{try{const sc=buildCsvScenario();download(slug($('csvname').value)+'.json',JSON.stringify({name:sc.name,description:sc.description,page:sc.page,steps:sc.steps},null,2));}catch(e){$('csvmsg').textContent=t('csv.err',{m:e.message});}};
$('csvcancel').onclick=()=>$('csvdlg').close();
