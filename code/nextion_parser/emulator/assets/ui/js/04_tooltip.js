// ---------- hover tooltip (expert mode): the element name ----------
(function(){
  const tip=$('tip');
  const hide=()=>{tip.style.display='none';};
  scr.addEventListener('mousemove',e=>{
    if(!document.body.classList.contains('mode-expert')){hide();return;}
    const els=document.elementsFromPoint(e.clientX,e.clientY).filter(x=>x.classList&&x.classList.contains('c'));
    if(!els.length){hide();return;}
    const top=els[0];
    tip.innerHTML='<b></b><i></i>';
    tip.firstChild.textContent=top.dataset.n;tip.lastChild.textContent=top.dataset.t+(els.length>1?' · '+t('tip.below',{n:els.length-1}):'');
    tip.style.display='block';
    const w=tip.offsetWidth,h=tip.offsetHeight;
    tip.style.left=Math.min(window.innerWidth-w-6,e.clientX+14)+'px';
    tip.style.top=(e.clientY+h+22>window.innerHeight?e.clientY-h-12:e.clientY+18)+'px';
  });
  scr.addEventListener('mouseleave',hide);
  window.addEventListener('blur',hide);
})();
