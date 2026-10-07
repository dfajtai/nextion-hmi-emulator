// ---------- go ----------
applyStatic();buildReportsMenu();
refreshScnSelect();
applySize();boot();renderRec();
if(window.NX_SCENARIOS)applyItems(window.NX_SCENARIOS,true);
const q=new URLSearchParams(location.search);
setMode(DATA.portable?'simple':(q.get('mode')||((DATA.scenarios||[]).length?'simple':'expert')));
if(q.get('scn')){$('scn').value=q.get('scn');}
selectScn();
$('capexp').textContent=histLabel();
syncServer(true).then(()=>{if(DATA.server){window.addEventListener('focus',()=>syncServer(false));if(DATA.portable)setInterval(()=>{if(!document.hidden)syncServer(false);},3000);}});
if(q.has('autoplay'))playScn();
