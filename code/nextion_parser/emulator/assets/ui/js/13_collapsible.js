// ---------- collapsible blocks ----------
document.querySelectorAll('.card').forEach((card,i)=>{
  const hd=card.querySelector(':scope > h2');if(!hd)return;
  const key='nx_card_'+(card.id||i);
  const saved=lsGet(key);
  const collapsed=saved!==null?saved==='1':card.dataset.collapsed==='1';
  card.classList.toggle('collapsed',collapsed);
  hd.tabIndex=0;hd.setAttribute('role','button');
  const toggle=()=>{const c=card.classList.toggle('collapsed');lsSet(key,c?'1':'0');};
  hd.addEventListener('click',toggle);
  hd.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}});
});
