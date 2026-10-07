// ---------- size / zoom ----------
function applySize(){
  const w=Math.max(64,+$('sw').value||DATA.screen.w),h=Math.max(64,+$('sh').value||DATA.screen.h);
  let z=$('zoom').value;
  if(z==='fit'){
    const colW=($('left').clientWidth||window.innerWidth-60)-24;          // width of the display column (without the frame)
    const byW=colW/w,byH=Math.max(220,window.innerHeight-210)/h;           // not taller than what fits on the screen
    z=Math.max(.5,Math.min(3,byW,byH));
  }
  const r=document.documentElement.style;
  r.setProperty('--w',w);r.setProperty('--h',h);r.setProperty('--z',+z);
}
