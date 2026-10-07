// ---------- rendering ----------
let lastSig='';
const SIG_KEYS=['x','y','w','h','txt','val','pic','pic2','bco','bco2','pco','pco2','sta','xcen','ycen','font','isbr','minval','maxval','lenth','vvs1','ch','dis','@hidden'];
function visSig(){   // only the state that affects the picture: do not redraw if nothing visible changed
  const cur=nx.cur();if(!cur)return '';
  const S=nx.S()[cur];let s=cur+'|'+pressed+'|'+LANG+'|';
  for(const k in S){const o=S[k];if(o.w===undefined&&k!=='@page')continue;
    s+=k+':';for(const f of SIG_KEYS)if(o[f]!==undefined)s+=o[f]+',';
    if(o['@wave'])s+='w'+o['@wave'].map(a=>a.length+':'+(a[0]||0)+':'+(a[a.length-1]||0)).join('/');s+=';';}
  return s;
}
function uiTick(){nx.tick(50);if(nx.hasQueue())nx.flush();else if(visSig()!==lastSig)render();}
function render(){
  const cur=nx.cur();if(!cur)return;
  lastSig=visSig();
  const S=nx.S(),scr=$('screen');scr.innerHTML='';
  const pg=pages.find(p=>p.name==cur),P=S[cur]['@page'];
  scr.style.background=P.sta==1?rgb(P.bco):'#000';
  if(P.sta==2&&picmap[P.pic]){const im=document.createElement('img');im.src=picmap[P.pic];im.style.cssText='position:absolute;inset:0;width:100%;height:100%';scr.appendChild(im);}
  pg.comps.forEach(c=>{
    const o=S[cur][c.objname];if(!o||o.w===undefined||o['@hidden'])return;
    const el=document.createElement('div');el.className='c'+(c.code&&(c.code.down&&c.code.down.length||c.code.up&&c.code.up.length)?' hit':'');
    el.style.cssText=`left:${o.x}px;top:${o.y}px;width:${o.w}px;height:${o.h}px;`;
    el.dataset.n=c.objname;el.dataset.t=typeName(o.type);
    const isP=pressed===c.objname,ty=o.type;
    let bg=null,img=null,fg=rgb(o.pco);
    if(ty==98||ty==116){
      if(o.sta==1)bg=rgb(isP&&ty==98?o.bco2:o.bco);
      else if(o.sta==2||o.sta==0){img=picmap[isP&&ty==98&&o.pic2!==undefined?o.pic2:o.pic];if(!img&&o.sta==2)bg=rgb(isP&&ty==98?o.bco2:o.bco);}
      if(ty==98&&isP&&o.pco2!==undefined&&o.pco2!=65535)fg=rgb(o.pco2);
    }else if(ty==54||ty==59){if(o.sta==1)bg=rgb(o.bco);else if(o.sta==2)img=picmap[o.pic];}
    else if(ty==112){img=picmap[o.pic];if(!img)bg='rgba(120,120,120,.35)';}
    else if(ty==0||ty==1||ty==106)bg=rgb(o.bco);
    if(bg)el.style.background=bg;
    if(img){const im=document.createElement('img');im.src=img;el.appendChild(im);}
    if(ty==1||ty==106){const lo=o.minval||0,hi=o.maxval||100;const f=Math.max(0,Math.min(1,((o.val||0)-lo)/Math.max(1,hi-lo)));
      const d=document.createElement('div');d.style.cssText=`position:absolute;left:0;top:0;height:100%;width:${f*100}%;background:${rgb(o.pco)}`;el.appendChild(d);}
    if(ty==0){
      const cv=document.createElement('canvas');cv.width=o.w;cv.height=o.h;cv.style.cssText='position:absolute;left:0;top:0';
      const g=cv.getContext('2d');
      const gw=o.gdw||40,gh=o.gdh||40;
      if(o.gdc!==undefined){g.strokeStyle=rgb(o.gdc);g.lineWidth=1;g.beginPath();
        for(let x=gw;x<o.w;x+=gw){g.moveTo(x+.5,0);g.lineTo(x+.5,o.h);}for(let y=gh;y<o.h;y+=gh){g.moveTo(0,y+.5);g.lineTo(o.w,y+.5);}g.stroke();}
      const cols=[o.pco0,o.pco1,o.pco2,o.pco3],scale=(o.dis||100)/100;
      (o['@wave']||[]).forEach((d,ch)=>{if(!d||!d.length||ch>=(o.ch||1))return;
        g.strokeStyle=rgb(cols[ch]);g.lineWidth=1;g.beginPath();
        d.forEach((v,i)=>{const x=d.length>o.w?i*(o.w/d.length):i;
          const y=o.h-1-(Math.max(0,Math.min(255,v))/255)*(o.h-1)*scale;i?g.lineTo(x,y):g.moveTo(x,y);});
        g.stroke();});
      el.appendChild(cv);}
    if(ty==57||ty==56){const sz=Math.min(o.w,o.h),r=document.createElement('div');
      r.style.cssText=`width:${sz}px;height:${sz}px;border:2px solid ${rgb(o.pco)};background:${rgb(o.bco)};border-radius:${ty==57?'50%':'3px'};position:relative`;
      if(o.val){const k=document.createElement('div');k.style.cssText=`position:absolute;inset:25%;background:${rgb(o.pco)};border-radius:${ty==57?'50%':'2px'}`;r.appendChild(k);}el.appendChild(r);}
    let text=null;
    if(ty==98||ty==116)text=(o.txt||'').replace(/\\r/g,'\n').replace(/\r/g,'\n');
    else if(ty==54||ty==59)text=fmtVal(o);
    if(text){
      const sp=document.createElement('span');sp.textContent=text;
      el.style.fontSize=fontPx(o,text)+'px';el.style.color=fg;
      el.style.justifyContent=o.xcen==0?'flex-start':o.xcen==2?'flex-end':'center';
      el.style.alignItems=o.ycen==0?'flex-start':o.ycen==2?'flex-end':'center';
      el.style.textAlign=o.xcen==0?'left':o.xcen==2?'right':'center';
      if(o.isbr)el.classList.add('wrapt');
      el.appendChild(sp);
    }
    scr.appendChild(el);
    const sp2=el.querySelector('span');
    if(sp2&&!o.isbr){let f=parseFloat(el.style.fontSize);while(f>7&&sp2.offsetWidth>o.w-2){f-=1;el.style.fontSize=f+'px';}}
  });
}
const scr=$('screen');
scr.addEventListener('mousedown',e=>{
  if(play.state==='play')pauseScn();                 // touching the display takes over: the playback stops
  const el=document.elementsFromPoint(e.clientX,e.clientY).find(x=>x.classList&&x.classList.contains('hit'));
  if(!el)return;
  pressed=el.dataset.n;markDirty();render();recPush({click:pressed});nx.fire(pressed,'down');
});
window.addEventListener('mouseup',e=>{
  if(pressed===null)return;const n=pressed;pressed=null;render();
  if(document.elementsFromPoint(e.clientX,e.clientY).some(x=>x.dataset&&x.dataset.n===n))nx.fire(n,'up');
});
