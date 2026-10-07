// ---------- reports menu ----------
function buildReportsMenu(){
  const rep=DATA.reports||[];if(!rep.length)return;
  const box=$('replist');box.innerHTML='';
  rep.forEach(r=>{const a=document.createElement('a');a.href=r.href;a.target='_blank';a.rel='noopener';a.textContent=t('rep.'+r.key)+' ↗';box.appendChild(a);});
  $('repmenu').hidden=false;
}
document.addEventListener('click',e=>{const m=$('repmenu');if(m.open&&!m.contains(e.target))m.open=false;});
$('replist').addEventListener('click',()=>{$('repmenu').open=false;});
