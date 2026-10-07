// ---------- variable panels ----------
function updVars(){
  const box=$('vars');box.innerHTML='';
  const S=nx.S(),G=nx.G(),cur=nx.cur();if(!cur)return;
  const add=(label,o,a,target)=>{const d=document.createElement('div'),l=document.createElement('label'),i=document.createElement('input');
    l.textContent=label;i.value=o[a];
    i.onchange=()=>{markDirty();o[a]=typeof o[a]=='number'?(parseInt(i.value)||0):i.value;render();
      if(o===G)recPush({cmd:label+'='+(typeof o[a]=='string'?'"'+o[a]+'"':o[a])});else recPush({set:{[cur+'.'+label]:o[a]}});};d.append(l,i);(target||box).appendChild(d);};
  const gbox=$('globvars');gbox.innerHTML='';
  Object.keys(G).forEach(k=>add(k,G,k,gbox));
  pages.find(p=>p.name==cur).comps.forEach(c=>{const o=S[cur][c.objname];if(!o)return;
    if(c.type==116)add(c.objname+'.txt',o,'txt');
    if([54,59,52,1,57,56,106].includes(c.type))add(c.objname+'.val',o,'val');
    if(c.type==51)add(c.objname+'.en',o,'en');});
}
