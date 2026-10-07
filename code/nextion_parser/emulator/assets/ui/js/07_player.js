// ---------- scenario player (step by step + automatic) ----------
const play={scn:null,k:0,t:null,state:'stop',dirty:false};
function markDirty(){play.dirty=true;}   // after a manual intervention (click, value, jump, restart) we re-sync before playing
function scnById(id){return (DATA.scenarios||[]).find(s=>s.id===id);}
function btnText(name){   // the text shown on a button (current runtime text, else the static one), not its object name
  let v=null;
  try{const o=nx.S()[nx.cur()][name];if(o&&typeof o.txt==='string')v=o.txt;}catch(e){}
  if(v===null)for(const p of pages){const c=p.comps.find(c=>c.objname===name);if(c){if(typeof c.txt==='string')v=c.txt;break;}}
  return v&&v.trim()?v.trim():name;
}
const silentStep=st=>st.wait!==undefined&&!st.say&&Object.keys(st).length===1;   // a pause without a caption shows nothing
function stepCap(st,n){if(!silentStep(st))setCaption({st},null,capKind(st),n);}
function varLabel(ref){const v=(DATA.variables||[]).find(x=>x.ref===ref);return v&&v.label?loc(v.label):ref.split('.').slice(1).join('.');}
function describe(st){
  if(st.say)return loc(st.say);
  if(st.set)return t('desc.set',{x:Object.entries(st.set).map(([k,v])=>varLabel(k)+' = '+v).join(', ')});
  if(st.ramp)return t('desc.ramp',{v:varLabel(st.ramp.ref),a:st.ramp.from,b:st.ramp.to});
  if(st.click)return t('desc.click',{n:btnText(st.click)});
  if(st.goto)return t('desc.goto',{p:st.goto});
  if(st.cmd)return t('desc.cmd',{c:Array.isArray(st.cmd)?st.cmd.join('; '):st.cmd});
  if(st.wave)return t('desc.wave',{r:st.wave.ref});
  if(st.wait)return t('desc.wait',{s:(st.wait/1000).toFixed(1)});
  if(st.repeat)return t('desc.repeat',{n:st.repeat});
  return t('desc.step');
}
function stepCaption(st){return st.say?loc(st.say):describe(st);}
function capKind(st){return st.say?'step':'aux';}
// lazy message descriptors: a plain string, {key,vars} (translated when shown), {st} (a scenario step) or {txt} (a localized field)
function R(d){
  if(d===null||d===undefined)return '';
  if(typeof d==='string')return d;
  if(d.st)return stepCaption(d.st);
  if(d.key)return t(d.key,d.vars);
  if(d.txt!==undefined)return loc(d.txt);
  return loc(d);
}
const cap={log:[],extra:[],open:false,cur:null};
function pushLog(d,kind,n){const l=cap.log[cap.log.length-1];if(l&&R(l.d)===R(d)&&l.n===n)return;cap.log.push({d,kind,n});if(cap.log.length>500)cap.log.shift();if(cap.open)renderHist();}
function renderCaption(){
  const c=cap.cur;
  if(!c){$('captext').textContent=t((DATA.scenarios||[]).length?'cap.hint':(DATA.portable?'cap.noscn.basic':'cap.noscn'));$('captext').className='cap-info';
    $('capbadge').textContent=t('cap.badge.info');$('capbadge').className='info';$('capstep').textContent='';return;}
  $('captext').textContent=R(c.d);$('captext').className='cap-'+c.kind;
  $('capbadge').textContent=t('cap.badge.'+c.kind);$('capbadge').className=c.kind==='info'?'info':'';
  $('capstep').textContent=(c.kind!=='info'&&c.n&&play.scn)?t('cap.stepn',{n:c.n,N:play.scn.steps.length}):'';
}
// kind: 'step' (the scenario's caption) | 'aux' (description of a step without caption) | 'info' (system message); n: step number
function setCaption(d,pct,kind,n){
  if(d!==null&&d!==undefined){
    kind=kind||'info';cap.cur={d,kind,n};renderCaption();pushLog(d,kind,n);
  }
  $('prog').firstChild.style.width=(pct||0)+'%';
}
function lens(){const s=nx.stats;return {se:s.scenarioErrors.length,er:s.errors.length,unk:s.unknown.length};}
function collectWarns(){
  const b=play.base||{se:0,er:0,unk:0},s=nx.stats;
  return cap.extra.map(R).concat(s.scenarioErrors.slice(b.se).map(e=>t('warn.scn',{msg:e.msg})),s.errors.slice(b.er).map(e=>e.where+': '+e.msg),s.unknown.slice(b.unk).map(u=>t('warn.unknown',{line:u.line})));
}
function warn(){   // errors in a separate small bubble, only when there are any
  const w=collectWarns(),bub=$('capwarn');
  if(!w.length){bub.hidden=true;bub.textContent='';}
  else{const last=w[w.length-1];bub.hidden=false;bub.textContent=t('cap.warn',{n:w.length,msg:last.length>70?last.slice(0,70)+'…':last});}
  if(cap.open)renderHist();
}
function histLabel(){return (cap.open?t('cap.hist.open'):t('cap.hist'))+' ('+cap.log.length+')';}
function renderHist(){
  const ol=$('caphist');ol.innerHTML='';
  collectWarns().forEach(m=>{const li=document.createElement('li');li.className='err';li.innerHTML='<b>⚠</b><span></span>';li.lastChild.textContent=m;ol.appendChild(li);});
  cap.log.forEach((e,i)=>{const li=document.createElement('li');li.className=e.kind+(i===cap.log.length-1?' cur':'');
    li.innerHTML='<b></b><span></span>';li.firstChild.textContent=e.n?e.n+'.':'•';li.lastChild.textContent=R(e.d);ol.appendChild(li);});
  ol.scrollTop=ol.scrollHeight;
  $('capexp').textContent=histLabel();
}
function toggleHist(force){cap.open=force===undefined?!cap.open:force;$('caphist').hidden=!cap.open;if(cap.open)renderHist();else $('capexp').textContent=histLabel();}
$('capexp').onclick=()=>toggleHist();
$('capwarn').onclick=()=>toggleHist(true);
function buildOutline(){
  const ol=$('outline');ol.innerHTML='';
  if(!play.scn)return;
  play.scn.steps.forEach((st,i)=>{const li=document.createElement('li');li.textContent=(i+1)+'. '+stepCaption(st);li.onclick=()=>{pauseScn();gotoStep(i+1);};ol.appendChild(li);});
  markOutline();
}
function markOutline(){
  const n=play.scn?play.scn.steps.length:0;
  [...$('outline').children].forEach((li,i)=>{li.classList.toggle('done',i<play.k-1);li.classList.toggle('cur',i===play.k-1);});
  $('stepno').textContent=play.scn?t('scn.stepno',{k:play.k,n}):'';
  $('prog').firstChild.style.width=(n?100*play.k/n:0)+'%';
}
function runTopSim(st,fx){   // execute a step immediately; the timers tick during the simulated waits too
  nx.expandSteps([st]).forEach(p=>{if(fx&&p.click)showClick(p.click,450);const r=nx.applyStep(p);for(let w=0;w<Math.min(r.wait,600000);w+=50){nx.tick(50);if(nx.hasQueue())nx.flush();}});
}
function scnIntro(scn){return scn.description?{key:'cap.scn',vars:{name:scn.name,desc:scn.description}}:{txt:scn.name};}
function selectScn(){
  cancelPending();pauseScn();play.scn=scnById($('scn').value)||null;play.k=0;play.base=lens();cap.extra=[];cap.log=[];cap.cur=null;
  $('scndesc').textContent=play.scn?loc(play.scn.description):'';
  buildOutline();
  if(play.scn){nx.startScenario({page:play.scn.page,steps:[]});nx.flush();play.dirty=false;setCaption(scnIntro(play.scn),0,'info');}
  else renderCaption();
}
function gotoStep(k){      // replay the first k steps from the beginning (deterministic)
  if(!play.scn)return;cancelPending();clearFx();play.base=lens();
  nx.startScenario({page:play.scn.page,steps:[]});
  for(let i=0;i<k;i++)runTopSim(play.scn.steps[i]);
  nx.flush();play.k=k;play.dirty=false;markOutline();warn();
  cap.log=[];for(let i=0;i<k;i++){const st=play.scn.steps[i];if(!silentStep(st))cap.log.push({d:{st},kind:capKind(st),n:i+1});}
  if(k){let j=k-1;while(j>0&&silentStep(play.scn.steps[j]))j--;stepCap(play.scn.steps[j],j+1);}else setCaption({txt:play.scn.name},null,'info');
  if(cap.open)renderHist();
}
const PREROLL=1100;   // ms: at the start of playback the initial state is shown this long before the first action
function startNote(){return {key:'cap.start',vars:{page:play.scn&&play.scn.page||DATA.start}};}
function simApply(p){const r=nx.applyStep(p);for(let w=0;w<Math.min(r.wait,600000);w+=50){nx.tick(50);if(nx.hasQueue())nx.flush();}}
function cancelPending(){clearTimeout(play.stepT);play.pending=null;}
function finishPending(){if(play.pending){const f=play.pending;play.pending=null;f();}}   // finishes a half-done step immediately
function nextStep(){
  if(!play.scn)return false;
  finishPending();
  if(play.dirty||play.k===0&&play.state!=='play')gotoStep(play.k);   // bring a manually modified state back to the scenario state
  if(play.k>=play.scn.steps.length)return false;
  const st=play.scn.steps[play.k];
  const prims=nx.expandSteps([st]);let i=0;
  const done=()=>{nx.flush();play.pending=null;play.k++;markOutline();warn();};
  const go=()=>{
    while(i<prims.length){
      const p=prims[i];
      if(p.click){   // highlight first, the click happens ~0.5 s later, then the highlight disappears
        showClick(p.click,900);
        play.stepT=setTimeout(()=>{i++;clearFx();showClick(p.click,350,true);simApply(p);go();},500);
        return;
      }
      i++;simApply(p);
    }
    done();
  };
  const begin=()=>{clearFx();stepCap(st,play.k+1);go();};
  play.pending=()=>{clearTimeout(play.stepT);clearFx();while(i<prims.length)simApply(prims[i++]);done();};
  if(play.k===0){   // before the first step show the configured start page, so one can see where the first click happens
    clearFx();setCaption(startNote(),null,'info');
    play.stepT=setTimeout(begin,Math.round(PREROLL*0.7));
  }else begin();
  return true;
}
function prevStep(){pauseScn();if(play.scn)gotoStep(Math.max(0,play.k-1));}
function playTop(){   // automatic, real-time playback: one top-level step = elementary steps with delays
  if(play.state!=='play'||!play.scn)return;
  if(play.k>=play.scn.steps.length){play.state='stop';setCaption({key:'cap.end'},null,'info');return;}
  const st=play.scn.steps[play.k];stepCap(st,play.k+1);
  const prims=nx.expandSteps([st]);let i=0;
  const fixed=$('speed').value==='fixed',fixMs=Math.max(300,(+$('fixsec').value||2)*1000);   // even pace: the same pause after every step
  const adv=()=>{if(play.state!=='play')return;play.k++;markOutline();warn();playTop();};
  const run=()=>{
    if(play.state!=='play')return;
    if(i>=prims.length){if(fixed&&!silentStep(st))play.t=setTimeout(adv,fixMs);else adv();return;}
    const p=prims[i++],sp=+$('speed').value||1;
    if(p.click){showClick(p.click,900/sp);                         // the highlight stays until the click, then disappears
      play.t=setTimeout(()=>{if(play.state!=='play')return;clearFx();showClick(p.click,350,true);nx.applyStep(p);play.t=setTimeout(run,300/sp);},550/sp);return;}
    const r=nx.applyStep(p);
    play.t=setTimeout(run,(fixed&&st.wait!==undefined?0:Math.max(0,r.wait))/sp);
  };
  run();
}
function playScn(){
  finishPending();
  if(!play.scn)selectScn();
  if(!play.scn)return;
  const n=play.scn.steps.length;
  if(play.state==='pause'&&!play.dirty){play.state='play';playTop();return;}      // resume after a pause
  // otherwise always start from the scenario's own state: from the beginning (k=0 or the end), or by replaying the steps so far
  gotoStep(play.k>=n?0:play.k);
  play.state='play';
  if(play.k===0){   // first the initial state is visible, only then the first highlight/click
    setCaption(startNote(),0,'info');
    play.t=setTimeout(playTop,Math.round(PREROLL/(+$('speed').value||1)));
  }else playTop();
}
function pauseScn(){clearTimeout(play.t);clearFx();if(play.state==='play')play.state='pause';}
function stopScn(){clearTimeout(play.t);play.state='stop';gotoStep(0);}
function stepForward(){pauseScn();nextStep();}
