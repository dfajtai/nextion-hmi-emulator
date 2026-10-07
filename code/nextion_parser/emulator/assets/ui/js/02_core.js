// ---------- core ----------
const logEl=$('log');
let pressed=null;
const nx=createCore(DATA,{
  log(m,c){const d=document.createElement('div');if(c)d.className=c;d.textContent=m;logEl.appendChild(d);logEl.scrollTop=1e9;},
  t:(k,v)=>t(k,v),
  render(){render();},changed(){updVars();const g=$('goto');if(g&&nx.cur())g.value=nx.cur();const rp=$('recpage');if(rp&&nx.cur()&&typeof rec!=='undefined'&&!rec.on&&!rec.steps.length)rp.value=nx.cur();}
});
const pages=nx.pages,picmap=nx.picmap,fonts=nx.fonts;
const rgb=v=>{v=+v||0;const r=(v>>11)&31,g=(v>>5)&63,b=v&31;return `rgb(${r*255/31|0},${g*255/63|0},${b*255/31|0})`;};
function fmtVal(o){
  if(o.type==59){const d=o.vvs1||0,v=o.val||0;let s=String(Math.abs(v)).padStart(d+1,'0');if(d)s=s.slice(0,-d)+'.'+s.slice(-d);return(v<0?'-':'')+s;}
  let s=String(o.val||0);if(o.lenth)s=s.padStart(o.lenth,'0');return s;
}
const typeName=ty=>I18N.hu['type.'+ty]!==undefined?t('type.'+ty):t('type.unknown',{t:ty});
function fontPx(o,text){
  const f=fonts[o.font];
  if(f)return Math.max(8,f.height*0.78);
  return Math.max(8,Math.min(o.h*(text.includes('\n')?0.4:0.55),26));
}
