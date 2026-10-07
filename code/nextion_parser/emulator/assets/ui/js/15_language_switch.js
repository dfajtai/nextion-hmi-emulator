// ---------- language switch ----------
function applyLang(l){
  setLang(l);lsSet('nx_lang',LANG);
  applyStatic();buildReportsMenu();
  refreshScnSelect();buildOutline();$('scndesc').textContent=play.scn?loc(play.scn.description):'';
  renderCaption();warn();renderRec();render();
  if(cap.open)renderHist();else $('capexp').textContent=histLabel();
}
$('lang').onchange=e=>applyLang(e.target.value);
