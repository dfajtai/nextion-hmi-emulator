// ---------- screenshot of the emulated display ----------
// The visible screen (#screen) is rendered at its native resolution into a PNG without any library: the live DOM is cloned with
// its computed styles inlined, pictures are replaced by data URIs (images.js, so it also works from file://) and the result is
// drawn through an SVG <foreignObject> onto a canvas. Overlays (hitboxes, the click highlight) are not part of #screen.
const SHOT_PROPS=['position','left','top','right','bottom','width','height','display','flex-direction','justify-content','align-items',
  'text-align','white-space','overflow','box-sizing','font-family','font-size','font-weight','font-style','line-height','color',
  'background-color','background-image','border','border-radius','padding','margin','opacity','transform','transform-origin','inset',
  'word-break','overflow-wrap'];
function shotImgData(path){
  const d=window.NX_IMG&&window.NX_IMG[path];if(d)return Promise.resolve(d);
  if(!/^https?:$/.test(location.protocol))return Promise.resolve(null);       // from file:// only the embedded copies are usable
  return fetch(path).then(r=>r.blob()).then(b=>new Promise(ok=>{const f=new FileReader();f.onload=()=>ok(f.result);f.readAsDataURL(b);})).catch(()=>null);
}
function shotInline(src,dst){   // copy the computed style of every element from the live tree onto the clone
  const cs=getComputedStyle(src);let css='';
  SHOT_PROPS.forEach(p=>{css+=p+':'+cs.getPropertyValue(p)+';';});
  dst.setAttribute('style',css);
  for(let i=0;i<src.children.length;i++)shotInline(src.children[i],dst.children[i]);
}
async function shotCanvas(){
  const live=$('screen'),w=live.offsetWidth,h=live.offsetHeight;
  const clone=live.cloneNode(true);
  shotInline(live,clone);
  clone.style.transform='none';clone.style.width=w+'px';clone.style.height=h+'px';
  // the waveform canvases hold the current picture only in the live tree
  const liveCv=live.querySelectorAll('canvas'),cloneCv=clone.querySelectorAll('canvas');
  cloneCv.forEach((c,i)=>{const im=document.createElement('img');im.setAttribute('style',c.getAttribute('style'));im.setAttribute('src',liveCv[i].toDataURL('image/png'));c.replaceWith(im);});
  let missing=false;
  for(const im of clone.querySelectorAll('img')){
    const s=im.getAttribute('src')||'';if(s.startsWith('data:'))continue;
    const d=await shotImgData(s);if(d)im.setAttribute('src',d);else{missing=true;im.remove();}
  }
  if(missing){cap.extra=[{key:'shot.err',vars:{x:t('shot.noimg')}}];warn();}
  const xhtml=new XMLSerializer().serializeToString(clone);
  const svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'" height="'+h+'"><foreignObject width="100%" height="100%">'+
    '<div xmlns="http://www.w3.org/1999/xhtml" style="width:'+w+'px;height:'+h+'px">'+xhtml+'</div></foreignObject></svg>';
  const img=new Image();
  await new Promise((ok,bad)=>{img.onload=ok;img.onerror=()=>bad(new Error('render'));img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);});
  const cv=document.createElement('canvas');cv.width=w;cv.height=h;
  cv.getContext('2d').drawImage(img,0,0);
  return new Promise((ok,bad)=>cv.toBlob(b=>b?ok(b):bad(new Error('toBlob')),'image/png'));
}
function shotName(){
  const d=new Date(),z=n=>String(n).padStart(2,'0');
  return PROJECT.replace(/[^\w.-]+/g,'_')+'_'+nx.cur()+'_'+d.getFullYear()+z(d.getMonth()+1)+z(d.getDate())+'-'+z(d.getHours())+z(d.getMinutes())+z(d.getSeconds())+'.png';
}
async function saveScreenshot(){
  const name=shotName();
  try{
    const blob=await shotCanvas();
    if(window.showSaveFilePicker){      // a real "Save as" window (Chromium based browsers)
      const fh=await window.showSaveFilePicker({suggestedName:name,types:[{description:'PNG',accept:{'image/png':['.png']}}]});
      const w=await fh.createWritable();await w.write(blob);await w.close();
      setCaption({key:'shot.saved',vars:{name:fh.name||name}},null,'info');
    }else{                              // other browsers: the normal download (the browser decides whether it asks where)
      const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(a.href),4000);setCaption({key:'shot.saved',vars:{name}},null,'info');
    }
  }catch(e){
    if(e&&e.name==='AbortError')return;   // the user closed the save window
    cap.extra=[{key:'shot.err',vars:{x:String(e&&e.message||e)}}];warn();
  }
}
async function copyScreenshot(){
  try{    // the promise goes straight into the ClipboardItem so that the click's permission is kept while the picture is rendered
    await navigator.clipboard.write([new ClipboardItem({'image/png':shotCanvas()})]);
    setCaption({key:'shot.copied'},null,'info');
  }catch(e){cap.extra=[{key:'shot.err',vars:{x:String(e&&e.message||e)}}];warn();}
}
$('shot').onclick=saveScreenshot;
if(navigator.clipboard&&window.ClipboardItem)$('shotcopy').onclick=copyScreenshot;
else $('shotcopy').hidden=true;      // not supported by this browser / context
