// ---------- start-up ----------
let tmr;
function boot(){clearInterval(tmr);logEl.textContent='';nx.boot(DATA.start);tmr=setInterval(uiTick,50);}
const pn=pages.map(p=>p.name);
['recpage','goto'].forEach(id=>pn.forEach(n=>{const o=document.createElement('option');o.textContent=n;$(id).appendChild(o);}));
if(!pn.includes(DATA.start))DATA.start=pn[0];
$('recpage').value=DATA.start;$('goto').value=DATA.start;
$('sw').value=DATA.screen.w;$('sh').value=DATA.screen.h;
if(DATA.zoom)$('zoom').value=String(DATA.zoom);
$('scn').onchange=selectScn;
$('play').onclick=()=>{if(play.state==='play')pauseScn();else playScn();};   // one start/pause toggle
$('next').onclick=stepForward;$('prev').onclick=prevStep;$('first').onclick=stopScn;
function updTransport(){
  const k=play.state==='play'?'pause':(play.state==='pause'&&!play.dirty?'resume':'play'),b=$('play'),sig=k+LANG;
  if(b.dataset.sig!==sig){b.dataset.sig=sig;b.textContent=t('scn.btn.'+k);}
  $('fixwrap').hidden=$('speed').value!=='fixed';
  const n=play.scn?play.scn.steps.length:0;
  $('prev').disabled=!play.scn||play.k<=0;$('next').disabled=!play.scn||play.k>=n;   // nothing before the start / after the end
}
setInterval(updTransport,150);
$('loadbtn').onclick=()=>$('scnfile').click();
$('scnfile').onchange=e=>{loadFiles([...e.target.files]);e.target.value='';};
['dragenter','dragover'].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();document.body.classList.add('drag');}));
['dragleave','drop'].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();document.body.classList.remove('drag');}));
document.addEventListener('drop',e=>{const fs=[...(e.dataTransfer&&e.dataTransfer.files||[])].filter(f=>/\.(json|csv|txt)$/i.test(f.name));if(fs.length)loadFiles(fs);});
function setMode(m){document.body.classList.toggle('mode-simple',m==='simple');document.body.classList.toggle('mode-expert',m==='expert');$('mode').value=m;applySize();}
$('mode').onchange=e=>{pauseScn();setMode(e.target.value);};
if(DATA.portable){   // basic variant: locked to simple mode, scenarios come from a folder
  document.body.classList.add('portable');
  $('mode').closest('label').hidden=true;$('helplink').hidden=true;
  $('scnfile').accept='.json,application/json';
  if(window.showDirectoryPicker){
    $('folderbtn').hidden=false;
    $('folderbtn').onclick=async()=>{
      try{
        const dir=await window.showDirectoryPicker(),fs=[];
        for await(const [n,h] of dir.entries())if(h.kind==='file'&&/\.json$/i.test(n))fs.push(await h.getFile());
        fs.sort((a,b)=>a.name.localeCompare(b.name));loadFiles(fs);
      }catch(e){/* cancelled */}
    };
  }
}
$('goto').onchange=()=>{markDirty();nx.goto($('goto').value);recPush({goto:$('goto').value});};
$('reset').onclick=()=>{
  pauseScn();cancelPending();clearFx();
  if(play.scn&&!rec.on)stopScn();           // a scenario is loaded: reset it too (back to its own initial state, step 0, empty history)
  else{markDirty();boot();}                 // no scenario (or recording): just restart the display from the project's start page
};
$('dbg').onchange=e=>document.body.classList.toggle('dbg',e.target.checked);
['sw','sh','zoom'].forEach(id=>$(id).onchange=applySize);
nx.options.timerPageJumps=$('timerjump').checked;
$('timerjump').onchange=()=>{nx.options.timerPageJumps=$('timerjump').checked;};
$('sizereset').onclick=()=>{const n=DATA.screen.native||[DATA.screen.w,DATA.screen.h];$('sw').value=n[0];$('sh').value=n[1];$('zoom').value='fit';applySize();};
window.addEventListener('resize',()=>{if($('zoom').value==='fit')applySize();});
if(window.ResizeObserver)new ResizeObserver(()=>{if($('zoom').value==='fit')applySize();}).observe($('left'));
function sendMcu(){const v=$('rx').value.trim();if(!v)return;markDirty();
  logEl.appendChild(Object.assign(document.createElement('div'),{textContent:t('log.mcu',{v})}));
  nx.applyStep({cmd:v});nx.flush();recPush({cmd:v});$('rx').value='';warn();}
$('rxb').onclick=sendMcu;$('rx').addEventListener('keydown',e=>{if(e.key==='Enter')sendMcu();});
