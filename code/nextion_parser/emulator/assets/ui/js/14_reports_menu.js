// ---------- reports menu ----------
function buildReportsMenu(){
  const rep=DATA.reports||[];if(!rep.length)return;
  const box=$('replist');box.innerHTML='';
  rep.forEach(r=>{const a=document.createElement('a');a.href=r.href;a.target='_blank';a.rel='noopener';a.textContent=t('rep.'+r.key)+' ↗';box.appendChild(a);});
  $('repmenu').hidden=false;
}
// every header menu (.hmenu): close on a click outside, and after choosing an entry
document.addEventListener('click',e=>{document.querySelectorAll('.hmenu[open]').forEach(m=>{if(!m.contains(e.target))m.open=false;});});
document.querySelectorAll('.hmenu .menubox').forEach(b=>b.addEventListener('click',()=>{b.closest('.hmenu').open=false;}));
