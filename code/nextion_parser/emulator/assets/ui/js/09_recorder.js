// ---------- macro recorder ----------
const rec={on:false,steps:[],last:0,page:null};
const isDelay=st=>st.wait!==undefined&&Object.keys(st).every(k=>k==='wait'||k==='say');
function baseDesc(st){const c={...st};delete c.say;return Object.keys(c).length?describe(c):t('rec.row.capstep');}
function setSay(st,v){   // edit the caption in the current language, keeping the other language of a localized caption
  if(st.say&&typeof st.say==='object'){if(v)st.say[LANG]=v;else delete st.say[LANG];if(!Object.values(st.say).some(Boolean))delete st.say;}
  else{if(v)st.say=v;else delete st.say;}
}
function renderRec(){
  const ol=$('recsteps');ol.innerHTML='';
  const mv=(i,d)=>{const j=i+d;if(j<0||j>=rec.steps.length)return;[rec.steps[i],rec.steps[j]]=[rec.steps[j],rec.steps[i]];renderRec();};
  rec.steps.forEach((st,i)=>{
    const li=document.createElement('li');li.title=JSON.stringify(st);
    const kind=isDelay(st)?'wait':st.click!==undefined?'click':st.set!==undefined?'set':st.goto!==undefined?'goto':st.cmd!==undefined?'cmd':(Object.keys(st).length===1&&st.say!==undefined)?'say':'other';
    li.className='k-'+kind;
    const ICON={wait:'⏱',click:'👆',set:'＝',goto:'➜',cmd:'⌨',say:'💬',other:'▸'};
    const ic=document.createElement('span');ic.className='ic';ic.textContent=ICON[kind];li.appendChild(ic);
    const act=document.createElement('div');act.className='act';
    if(kind==='wait'){
      const lb=document.createElement('span');lb.textContent=t('rec.row.waitlbl');
      const sec=document.createElement('input');sec.type='number';sec.min='0.1';sec.step='0.5';sec.value=(st.wait/1000);sec.title=t('rec.row.delay');
      sec.onchange=()=>{st.wait=Math.max(100,Math.round((+sec.value||1)*1000));renderRec();};
      const u=document.createElement('span');u.textContent=t('rec.sec');
      act.append(lb,sec,u);
    }else{
      const nn=document.createElement('small');nn.textContent=(i+1);act.appendChild(nn);
      const d=document.createElement('span');d.textContent=kind==='say'?t('rec.row.capstep'):baseDesc(st);act.appendChild(d);
    }
    li.appendChild(act);
    const cp=document.createElement('label');cp.className='cap';cp.append(document.createTextNode('💬'));
    const ci=document.createElement('input');ci.type='text';ci.placeholder=t('rec.cap.ph');ci.value=loc(st.say);
    ci.onchange=()=>{setSay(st,ci.value.trim());if(!Object.keys(st).length)rec.steps.splice(i,1);renderRec();};
    cp.appendChild(ci);li.appendChild(cp);
    const tl=document.createElement('div');tl.className='tools';
    const ed=document.createElement('button');ed.textContent='✎';ed.title=t('rec.row.edit');ed.onclick=()=>openStepEdit(i);tl.appendChild(ed);
    [['↑',-1,'rec.row.up'],['↓',1,'rec.row.down']].forEach(([x,dl,tk])=>{const b=document.createElement('button');b.textContent=x;b.title=t(tk);b.onclick=()=>mv(i,dl);tl.appendChild(b);});
    const x=document.createElement('button');x.textContent='✕';x.title=t('rec.row.del');x.onclick=()=>{rec.steps.splice(i,1);renderRec();};tl.appendChild(x);
    li.appendChild(tl);
    ol.appendChild(li);
  });
  ol.scrollTop=1e9;
  const real=rec.steps.filter(s=>!isDelay(s)).length;
  $('recstate').innerHTML='';
  if(rec.on){$('recstate').innerHTML='<span class="recdot"></span>';$('recstate').appendChild(document.createTextNode(t('rec.state.on',{n:real})));}
  else if(rec.steps.length)$('recstate').textContent=t('rec.state.items',{n:rec.steps.length});
  $('recdiscard').disabled=!rec.on&&!rec.steps.length;$('recsaybtn').disabled=!rec.on;
  $('recdelaybtn').disabled=!(rec.on||rec.steps.length);
  $('recsave').disabled=rec.on||!rec.steps.length;
  $('recappend').disabled=rec.on||!rec.steps.length;
  const eb=$('recedit');eb.hidden=!rec.editId;if(rec.editId)eb.textContent=t('rec.editbanner',{name:rec.editName,id:rec.editId});
  const b=$('recstart');
  b.textContent=t(rec.on?'rec.stop':(rec.steps.length?'rec.start2':'rec.start'));
  b.className=rec.on?'recording':'primary';
  const phase=rec.on?1:(rec.steps.length?(rec.saved?3:2):0);
  ['rf1','rf2','rf3'].forEach((id,i)=>{const e=$(id);e.className=(phase===i+1)?'on':(phase>i+1?'ok':'');});
  $('recbadge').textContent=rec.on?t('rec.badge'):'';
  $('rechint').textContent=t('rec.hint'+phase);
}
function recPush(step){
  if(!rec.on)return;
  const now=performance.now(),dt=now-rec.last;
  if($('recreal').checked&&rec.steps.length&&dt>=300){const w=Math.min(30000,Math.round(dt/100)*100);const prev=rec.steps[rec.steps.length-1];
    if(prev.wait!==undefined&&!prev.say)prev.wait+=w;else rec.steps.push({wait:w});}
  rec.steps.push(step);rec.last=now;renderRec();
}
function recAddDelay(){
  const sec=Math.max(0.1,+$('recdelay').value||1),c=$('recdelaycap').value.trim();
  const st={wait:Math.round(sec*1000)};if(c)st.say=c;
  rec.steps.push(st);rec.last=performance.now();$('recdelaycap').value='';renderRec();
}
function recStart(){
  markDirty();pauseScn();clearInterval(tmr);
  nx.boot($('recpage').value);tmr=setInterval(uiTick,50);
  rec.on=true;rec.saved=false;rec.steps=[];rec.editId=null;rec.page=$('recpage').value;rec.last=performance.now();
  $('recname').value=$('recname').value||t('rec.defname',{time:new Date().toLocaleTimeString()});
  $('recinfo').textContent=t('rec.info.started',{page:rec.page});renderRec();
  setCaption({key:'cap.recstart',vars:{page:rec.page}},null,'info');
}
function slug(s){return (s||'recording').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')||'recording';}
function download(name,text,mime){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:mime||'application/json'}));a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500);}
function addScenarioObj(sc){
  DATA.scenarios=DATA.scenarios||[];
  const ix=DATA.scenarios.findIndex(s=>s.id===sc.id);if(ix>=0)DATA.scenarios[ix]=sc;else DATA.scenarios.push(sc);
  refreshScnSelect(sc.id);selectScn();
}
function recStop(){rec.on=false;renderRec();}
function recDiscard(){rec.on=false;rec.saved=false;rec.steps=[];rec.editId=null;$('recinfo').textContent='';renderRec();}
function recAppend(){   // replay the existing steps immediately, then continue recording from the end state
  if(!rec.steps.length||rec.on)return;
  markDirty();pauseScn();cancelPending();clearFx();
  nx.startScenario({page:rec.page,steps:[]});
  rec.steps.forEach(st=>runTopSim(st));
  nx.flush();
  rec.on=true;rec.saved=false;rec.last=performance.now();$('recinfo').textContent=t('rec.info.append');renderRec();
}
function editScenario(){   // load the selected scenario into the recorder
  const sc=scnById($('scn').value);if(!sc)return;
  pauseScn();cancelPending();clearFx();rec.on=false;
  rec.steps=JSON.parse(JSON.stringify(sc.steps));rec.page=sc.page||DATA.start;rec.saved=false;rec.editId=sc.id;rec.editName=loc(sc.name);
  rec.editOrig={name:sc.name,description:sc.description};
  $('recname').value=loc(sc.name);$('recdesc').value=loc(sc.description);
  if([...$('recpage').options].some(o=>o.value===rec.page))$('recpage').value=rec.page;
  const card=$('reccard');card.classList.remove('collapsed');lsSet('nx_card_reccard','0');
  $('recinfo').textContent='';renderRec();card.scrollIntoView({behavior:'smooth',block:'nearest'});
}
let stepEditIx=-1;
function openStepEdit(i){stepEditIx=i;$('stepjson').value=JSON.stringify(rec.steps[i],null,2);$('stepmsg').textContent='';$('stepdlg').showModal();}
$('stepok').onclick=()=>{
  try{const v=JSON.parse($('stepjson').value);if(!v||typeof v!=='object'||Array.isArray(v))throw new Error(t('step.notobj'));
    if(!Object.keys(v).length)throw new Error(t('step.empty'));rec.steps[stepEditIx]=v;$('stepdlg').close();renderRec();}
  catch(e){$('stepmsg').textContent=t('step.err',{m:e.message});}
};
$('stepcancel').onclick=()=>$('stepdlg').close();
$('recappend').onclick=recAppend;$('scnedit').onclick=editScenario;
function recSave(){
  if(!rec.steps.length)return;
  const typedName=$('recname').value.trim()||t('rec.defsave'),typedDesc=$('recdesc').value.trim();
  const keep=rec.editId&&typedName===rec.editName;                 // when editing, an unchanged name keeps the id (file name) and the localized fields
  const sc={id:keep?rec.editId:slug(typedName),
    name:keep?rec.editOrig.name:typedName,
    description:(keep&&typedDesc===loc(rec.editOrig.description))?rec.editOrig.description:typedDesc,
    page:rec.page,steps:JSON.parse(JSON.stringify(rec.steps))};
  addScenarioObj(sc);rec.saved=true;if(keep)rec.editName=typedName;renderRec();
  const body=JSON.stringify({name:sc.name,description:sc.description,page:sc.page,steps:sc.steps},null,2);
  if(DATA.server){   // served by `nextion_parser serve`: write straight into the scenarios folder
    fetch('api/scenarios/'+encodeURIComponent(sc.id)+'.json',{method:'POST',body}).then(r=>{
      if(!r.ok)throw new Error(r.status);$('recinfo').textContent=t('rec.info.saved.server',{id:sc.id});
    }).catch(()=>{download(sc.id+'.json',body);$('recinfo').textContent=t('rec.info.saved',{id:sc.id});});
    return;
  }
  download(sc.id+'.json',body);
  $('recinfo').textContent=t('rec.info.saved',{id:sc.id});
}
$('recstart').onclick=()=>rec.on?recStop():recStart();$('recdiscard').onclick=recDiscard;$('recsave').onclick=recSave;
$('recdelaybtn').onclick=recAddDelay;
$('recsaybtn').onclick=()=>{const v=$('recsay').value.trim();if(v){recPush({say:v});$('recsay').value='';}};
$('recsay').addEventListener('keydown',e=>{if(e.key==='Enter')$('recsaybtn').click();});
$('recdelaycap').addEventListener('keydown',e=>{if(e.key==='Enter'&&!$('recdelaybtn').disabled)recAddDelay();});
