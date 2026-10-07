// ---------- click highlight (magenta marker during playback) ----------
let fxTimers=[];
function showClick(name,ms,rippleOnly){
  const cur=nx.cur();const o=cur&&nx.S()[cur]&&nx.S()[cur][name];
  if(!o||o.w===undefined)return;
  const fx=$('fx');
  const dot=document.createElement('div');dot.className='fxdot';dot.style.cssText=`left:${o.x+o.w/2}px;top:${o.y+o.h/2}px`;fx.appendChild(dot);
  const els=[dot];
  if(!rippleOnly){
    const box=document.createElement('div');box.className='fxbox'+(o.y<26?' low':'');
    box.style.cssText=`left:${o.x-3}px;top:${o.y-3}px;width:${o.w+6}px;height:${o.h+6}px`;
    if(document.body.classList.contains('mode-expert')){const lab=document.createElement('b');lab.textContent=name;box.appendChild(lab);}   // the name label only in expert mode
    fx.appendChild(box);els.push(box);
  }
  fxTimers.push(setTimeout(()=>els.forEach(e=>e.remove()),ms||600));
}
function clearFx(){fxTimers.forEach(clearTimeout);fxTimers=[];$('fx').innerHTML='';}
