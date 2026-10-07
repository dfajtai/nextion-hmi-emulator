// ---------- scenario folder sync (only when served by `nextion_parser serve`) ----------
const srvSeen={};
async function syncServer(first){
  if(!/^https?:$/.test(location.protocol))return;
  try{
    const r=await fetch('api/scenarios',{cache:'no-store'});if(!r.ok)return;
    const items=await r.json();DATA.server=true;applyItems(items,first);
  }catch(e){/* no server: file:// or static hosting */}
}
function applyItems(items,first){
  let ch=false;
  items.forEach(it=>{
    const key=JSON.stringify(it.data);if(srvSeen[it.name]===key)return;srvSeen[it.name]=key;
    const d=it.data;ch=addScenarios(Array.isArray(d)?d:(d.scenarios||[d]),it.name)>0||ch;
  });
  if(ch){const had=$('scn').value;refreshScnSelect();if(first||!had)selectScn();}
}
